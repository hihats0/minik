"""Mimari hesap makinesi: bir mimarinin toplam ve token basina AKTIF parametresinden egitim hesabini,
laptop suresini, enerjisini, bellegini, bellek TASIMA enerjisini ve beyinle kiyasini cikarir.
Cagiran: yeni mimari oturumlari, `python araclar/mimari_hesap.py --parametre 30e6 --aktif-oran 0.02 ...`
ya da toplu mod `python araclar/mimari_hesap.py --jsonl reports/mimari-1000.jsonl --ilk 50`.
"""

import argparse
import json
import sys
from collections import Counter

# Olculmus (reports/2026-09-24-az-veri-az-enerji.md): 30,7M transformer bf16 67.321 token/sn aktif
LAPTOP_AKTIF_FLOPS = 12.4e12
LAPTOP_DUVAR_FLOPS = 6.0e12  # 80 C duraklamalariyla
GPU_WATT = 91.0
GPU_VRAM_BAYT = 8e9
# Kaynak: NVIDIA RTX 4070 Laptop ozelligi (GDDR6, 128 bit, 16 Gbps); olculmedi
LAPTOP_BANT_BAYT_SN = 256e9
# Beyin (kaynak degerleri, yuvarlak): ~20 W, ~9e13 sinaps (Yigit'in "90 trilyon"u), ort. ~1 Hz atim
BEYIN_WATT = 20.0
BEYIN_SINAPS = 9e13
BEYIN_ATIM_HZ = 1.0
SAAT = 3600.0
EGITIM_CARPANI = 6  # ileri 2 + geri 4 islem / aktif parametre / token (6*N*D kurali)
CIKARIM_CARPANI = 2
ADAM_BAYT = 16  # egitimde parametre basina: agirlik + gradyan + iki Adam momenti (fp32)
BIT_BAYT = 8
# Tasima enerjisi, kaynak: Horowitz, "Computing's energy problem", ISSCC 2014 (45 nm).
# Yeni surecler islemi ucuzlatti ama DRAM/islem orani ~ayni kaldi; oranlar icin kullan, mutlak degil.
DRAM_J_BAYT = 640e-12 / 4  # 32 bit DRAM okuma 640 pJ
SRAM_J_BAYT = 10e-12 / 4  # 32 bit, 32 KB SRAM okuma 10 pJ
ISLEM_J = 0.75e-12  # 16 bit FP carpma 1,1 pJ + toplama 0,4 pJ = bir MAC (2 islem)
OLCEK_PARAMETRE = 9e13  # hedef: beyin kadar sinaps
KONUSMA_TOKEN_SN = 10  # sohbet hizi hedefi (tahmin: ~5 kelime/sn, ~2 token/kelime)
ALANLAR = ("id", "aile", "ad", "mekanizma", "aktif_oran", "okunan_oran", "bit", "ilke", "curutme")
EN_AZ_BIT, EN_COK_BIT = 1.0, 32.0
MEKANIZMA_KELIME = 8  # tekrar kontrolu: mekanizmanin bu kadar ilk kelimesi ayniysa ayni fikir sayilir


def hesapla(parametre: float, aktif_oran: float, token: float, bit: float) -> dict:
    aktif = parametre * aktif_oran
    egitim_flop = EGITIM_CARPANI * aktif * token
    return {
        "aktif parametre / token": aktif,
        "egitim FLOP (6 x aktif x token)": egitim_flop,
        "laptop egitim saati (aktif hiz)": egitim_flop / LAPTOP_AKTIF_FLOPS / SAAT,
        "laptop egitim saati (isiyla)": egitim_flop / LAPTOP_DUVAR_FLOPS / SAAT,
        "egitim enerjisi kWh (GPU)": egitim_flop / LAPTOP_AKTIF_FLOPS * GPU_WATT / SAAT / 1000,
        "egitim bellegi GB (Adam, fp32)": parametre * ADAM_BAYT / 1e9,
        "calisma bellegi GB (agirlik)": parametre * bit / 8 / 1e9,
        "token basina islem (cikarim)": CIKARIM_CARPANI * aktif,
        "laptop GPU'da token/sn (cikarim, ust sinir)": LAPTOP_AKTIF_FLOPS / (CIKARIM_CARPANI * aktif),
        "8 GB karta sigar mi (calisma)": parametre * bit / 8 < GPU_VRAM_BAYT,
    }


def tasima(parametre: float, aktif_oran: float, okunan_oran: float, bit: float) -> dict:
    """Cikarimda token basina enerji. Aktif agirlik yakin bellekten (SRAM) okunur; okunan_oran
    kadari her token uzak bellekten (DRAM) tasinir. Beyinde sinaps yerinde durur, tasima yok."""
    bayt = bit / BIT_BAYT
    dram = parametre * okunan_oran * bayt
    islem = CIKARIM_CARPANI * parametre * aktif_oran
    dram_j = dram * DRAM_J_BAYT
    joule = dram_j + parametre * aktif_oran * bayt * SRAM_J_BAYT + islem * ISLEM_J
    bant_siniri = LAPTOP_BANT_BAYT_SN / dram if dram else float("inf")
    return {
        "DRAM'den okunan bayt / token": dram,
        "joule / token (DRAM + SRAM + islem)": joule,
        "tasima payi (DRAM joule / toplam)": dram_j / joule,
        f"watt ({KONUSMA_TOKEN_SN} token/sn)": joule * KONUSMA_TOKEN_SN,
        "token/sn (20 W beyin butcesiyle)": BEYIN_WATT / joule,
        "laptop token/sn (bant ve islem siniri)": min(bant_siniri, LAPTOP_AKTIF_FLOPS / islem),
    }


def beyin_kiyasi() -> dict:
    olay = BEYIN_SINAPS * BEYIN_ATIM_HZ
    return {"beyin sinaptik olay / sn": olay, "beyin joule / olay": BEYIN_WATT / olay,
            "laptop GPU joule / islem": GPU_WATT / LAPTOP_AKTIF_FLOPS,
            f"beyin joule / token ({KONUSMA_TOKEN_SN} token/sn sayarsak)": BEYIN_WATT / KONUSMA_TOKEN_SN}


def gecerli_mi(fikir: dict) -> str:
    """Bos dizge: gecerli. Degilse sebebi."""
    eksik = [a for a in ALANLAR if a not in fikir]
    if eksik:
        return f"eksik alan {eksik}"
    try:
        aktif, okunan, bit = float(fikir["aktif_oran"]), float(fikir["okunan_oran"]), float(fikir["bit"])
    except (TypeError, ValueError) as hata:
        return f"sayi degil: {hata}"
    if not (0 < aktif <= 1 and 0 <= okunan <= 1 and EN_AZ_BIT <= bit <= EN_COK_BIT):
        return f"aralik disi: aktif {aktif}, okunan {okunan}, bit {bit}"
    return ""


def fikirleri_oku(yol: str) -> list:
    """JSONL'den gecerli fikirleri doner; bozuk satiri yutmaz, stderr'e sebebiyle yazar."""
    fikirler = []
    with open(yol, encoding="utf-8") as dosya:
        for no, satir in enumerate(dosya, 1):
            if not satir.strip():
                continue
            try:
                fikir = json.loads(satir)
            except json.JSONDecodeError as hata:
                print(f"satir {no}: JSON bozuk: {hata}", file=sys.stderr)
                continue
            sebep = gecerli_mi(fikir)
            if sebep:
                print(f"satir {no}: {sebep}", file=sys.stderr)
                continue
            fikirler.append(fikir)
    return fikirler


def sirala(fikirler: list, parametre: float = OLCEK_PARAMETRE) -> list:
    """(fikir, tasima tablosu) ciftleri, token basina joule artan sirada (en az enerji basta)."""
    ciftler = [(f, tasima(parametre, float(f["aktif_oran"]), float(f["okunan_oran"]), float(f["bit"])))
               for f in fikirler]
    return sorted(ciftler, key=lambda c: (c[1]["joule / token (DRAM + SRAM + islem)"], str(c[0]["id"])))


def md_tablo(sirali: list, ilk: int) -> str:
    satirlar = [f"| sira | id | aile | ad | aktif | okunan | bit | J/token | W@{KONUSMA_TOKEN_SN}tok/sn "
                "| tok/sn@20W | tasima payi |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for sira, (f, t) in enumerate(sirali[:ilk], 1):
        satirlar.append(
            f"| {sira} | {f['id']} | {f['aile']} | {f['ad']} | {f['aktif_oran']} | {f['okunan_oran']} "
            f"| {f['bit']} | {t['joule / token (DRAM + SRAM + islem)']:.3g} "
            f"| {t[f'watt ({KONUSMA_TOKEN_SN} token/sn)']:.3g} | {t['token/sn (20 W beyin butcesiyle)']:.3g} "
            f"| {t['tasima payi (DRAM joule / toplam)']:.2f} |")
    return "\n".join(satirlar)


def tekrar_sayisi(anahtarlar) -> int:
    sayac = Counter(anahtarlar)
    return sum(sayi - 1 for sayi in sayac.values() if sayi > 1)


def ozet(fikirler: list) -> str:
    """Ad tekrari ve mekanizma tekrari: ilk ajan ayni fikri ad ekiyle 5 kez yazdi, ad testi yakalamadi."""
    ad = tekrar_sayisi(f["ad"].strip().lower() for f in fikirler)
    govde = tekrar_sayisi(" ".join(f["mekanizma"].lower().split()[:MEKANIZMA_KELIME]) for f in fikirler)
    return (f"gecerli fikir {len(fikirler)}, ayni ad tekrari {ad} (%{100 * ad / max(len(fikirler), 1):.1f}), "
            f"ilk {MEKANIZMA_KELIME} kelimesi ayni mekanizma {govde}")


def yaz(baslik: str, tablo: dict):
    print(f"\n== {baslik}")
    for ad, deger in tablo.items():
        print(f"  {ad:48s} {deger:.3g}" if isinstance(deger, float) else f"  {ad:48s} {deger}")


def tekli(a):
    okunan = a.aktif_oran if a.okunan_oran is None else a.okunan_oran
    yaz(f"mimari: {a.parametre:.3g} parametre, aktif %{100 * a.aktif_oran:g}, {a.token:.3g} token, "
        f"{a.bit:g} bit", hesapla(a.parametre, a.aktif_oran, a.token, a.bit))
    yaz(f"bellek tasima, {a.parametre:.3g} parametre, okunan %{100 * okunan:g}",
        tasima(a.parametre, a.aktif_oran, okunan, a.bit))
    yaz(f"bellek tasima, {OLCEK_PARAMETRE:.3g} parametre (beyin olcegi)",
        tasima(OLCEK_PARAMETRE, a.aktif_oran, okunan, a.bit))
    yaz("beyin ile kiyas", beyin_kiyasi())


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--parametre", type=float, help="toplam parametre, or. 30e6 (tekli mod)")
    p.add_argument("--aktif-oran", type=float, default=1.0, help="token basina calisan parametre payi (yogun=1)")
    p.add_argument("--okunan-oran", type=float, help="token basina DRAM'den tasinan pay (varsayilan: aktif oran)")
    p.add_argument("--token", type=float, default=50e6, help="egitim tokeni")
    p.add_argument("--bit", type=float, default=16, help="calisirken agirlik basina bit (1.58, 4, 16)")
    p.add_argument("--jsonl", help="toplu mod: fikir dosyasi, 90T parametrede siralar, md tablo basar")
    p.add_argument("--ilk", type=int, default=10**6, help="toplu modda basilacak satir sayisi")
    a = p.parse_args()
    if a.jsonl:
        fikirler = fikirleri_oku(a.jsonl)
        print(ozet(fikirler) + f"; siralama {OLCEK_PARAMETRE:.3g} parametrede, token basina joule\n")
        print(md_tablo(sirala(fikirler), a.ilk))
    elif a.parametre:
        tekli(a)
    else:
        p.error("--parametre ya da --jsonl gerekli")
