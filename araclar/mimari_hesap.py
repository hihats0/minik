"""Mimari hesap makinesi: bir mimarinin toplam ve token basina AKTIF parametresinden egitim hesabini,
laptop suresini, enerjisini, bellegini ve beyinle kiyasini cikarir. Olculmus laptop sayilariyla calisir.
Cagiran: yeni mimari oturumlari, `python araclar/mimari_hesap.py --parametre 30e6 --aktif-oran 0.02 ...`.
"""

import argparse

# Olculmus (reports/2026-09-24-az-veri-az-enerji.md): 30,7M transformer bf16 67.321 token/sn aktif
LAPTOP_AKTIF_FLOPS = 12.4e12
LAPTOP_DUVAR_FLOPS = 6.0e12  # 80 C duraklamalariyla
GPU_WATT = 91.0
GPU_VRAM_BAYT = 8e9
# Beyin (kaynak degerleri, yuvarlak): ~20 W, ~9e13 sinaps (Yigit'in "90 trilyon"u), ort. ~1 Hz atim
BEYIN_WATT = 20.0
BEYIN_SINAPS = 9e13
BEYIN_ATIM_HZ = 1.0
SAAT = 3600.0
EGITIM_CARPANI = 6  # ileri 2 + geri 4 islem / aktif parametre / token (6*N*D kurali)
CIKARIM_CARPANI = 2
ADAM_BAYT = 16  # egitimde parametre basina: agirlik + gradyan + iki Adam momenti (fp32)


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


def beyin_kiyasi() -> dict:
    olay = BEYIN_SINAPS * BEYIN_ATIM_HZ
    return {"beyin sinaptik olay / sn": olay, "beyin joule / olay": BEYIN_WATT / olay,
            "laptop GPU joule / islem": GPU_WATT / LAPTOP_AKTIF_FLOPS}


def yaz(baslik: str, tablo: dict):
    print(f"\n== {baslik}")
    for ad, deger in tablo.items():
        print(f"  {ad:48s} {deger:.3g}" if isinstance(deger, float) else f"  {ad:48s} {deger}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--parametre", type=float, required=True, help="toplam parametre, or. 30e6")
    p.add_argument("--aktif-oran", type=float, default=1.0, help="token basina calisan parametre payi (yogun=1)")
    p.add_argument("--token", type=float, default=50e6, help="egitim tokeni")
    p.add_argument("--bit", type=float, default=16, help="calisirken agirlik basina bit (1.58, 4, 16)")
    a = p.parse_args()
    yaz(f"mimari: {a.parametre:.3g} parametre, aktif %{100 * a.aktif_oran:g}, {a.token:.3g} token, "
        f"{a.bit:g} bit", hesapla(a.parametre, a.aktif_oran, a.token, a.bit))
    yaz("beyin ile kiyas", beyin_kiyasi())
