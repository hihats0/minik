"""D4-c: ogretmenin urettigi gece dersini dogrular (bicim, 3-6 kelime, cevap sizintisi) ve dersten
egitim cumlelerini / sabah sorularini cikarir. Cagiran: ders_uret, gece, sabah_sinavi, yedi_gece, testler.
"""

import re

BILGI_SAYISI = 10
CUMLELEME_SAYISI = 5
YANLIS_SAYISI = 3
CEVAP_EN_COK_KELIME = 2
OKUL_CUMLE_SAYISI = 50
OKUL_EN_AZ_KELIME, OKUL_EN_COK_KELIME = 3, 6
BOSLUK = "___"
# Turkcede ekler sona gelir; cevabin ilk 4 harfi cumlelemede geciyorsa kok ogretilmis sayilir
# ("Pamuk" -> "Pamuk'tur"). Kaba kural, amac cevabi hic icermeyen bilgiyi elemek.
KOK_UZUNLUGU = 4
NOKTALAMA = re.compile(r"[^\w\s]")


def normal(metin: str) -> str:
    """Kucuk harf (Turkce I/i dogru), noktalama bosluk, tek bosluk. Sizinti karsilastirmasi icin."""
    metin = metin.replace("İ", "i").replace("I", "ı").lower()
    return " ".join(NOKTALAMA.sub(" ", metin).split())


def kelime_say(metin: str) -> int:
    """Icinde harf/rakam olan bosluk parcalari; "Minik'in" tek kelime."""
    return sum(1 for parca in metin.split() if re.search(r"\w", parca))


def doldur(soru: str, cevap: str) -> str:
    return soru.replace(BOSLUK, cevap)


def bilgi_bicim_sorunu(b) -> str | None:
    """Tek bilginin bicim hatasini metin olarak dondurur; sorun yoksa None."""
    if not isinstance(b, dict):
        return "bilgi sozluk degil"
    cumleler, yanlislar, cevap = b.get("cumlelemeler"), b.get("yanlislar"), b.get("cevap")
    if not all(isinstance(b.get(k), str) and b[k].strip() for k in ("bilgi", "soru", "cevap")):
        return "bilgi/soru/cevap bos ya da metin degil"
    if not isinstance(cumleler, list) or not all(isinstance(c, str) for c in cumleler):
        return "cumlelemeler metin listesi degil"
    if len(cumleler) != CUMLELEME_SAYISI or len({normal(c) for c in cumleler}) != CUMLELEME_SAYISI:
        return f"{CUMLELEME_SAYISI} farkli cumleleme yok"
    if b["soru"].count(BOSLUK) != 1:
        return f"soruda tam bir {BOSLUK} yok"
    if kelime_say(cevap) > CEVAP_EN_COK_KELIME:
        return "cevap cok uzun"
    if not isinstance(yanlislar, list):
        return "yanlislar liste degil"
    if len({normal(str(y)) for y in yanlislar} - {normal(cevap)}) != YANLIS_SAYISI:
        return f"cevaptan farkli {YANLIS_SAYISI} yanlis sik yok"
    kok = normal(cevap)[:KOK_UZUNLUGU]
    if not any(kok in normal(c) for c in cumleler):
        return "cevap hicbir cumlelemede gecmiyor, bilgi ogretilmiyor"
    return None


def sizar_mi(dolu_soru: str, egitim_normal: list[str]) -> bool:
    """Cevapla doldurulmus soru, bir egitim cumlesinin icinde kelime sinirinda birebir geciyor mu."""
    aranan = f" {normal(dolu_soru)} "
    return any(aranan in f" {c} " for c in egitim_normal)


def egitim_cumleleri(ders: dict) -> list[str]:
    return [c for b in ders["bilgiler"] for c in b["cumlelemeler"]] + ders["okul"]


def sabah_sorulari(ders: dict) -> list[dict]:
    return [{"soru": b["soru"], "cevap": b["cevap"], "yanlislar": b["yanlislar"]}
            for b in ders["bilgiler"]]


def okul_uygunlari(cumleler: list) -> list[str]:
    """3-6 kelimelik, tekrarsiz cumleleri sirasiyla dondurur (sayi kontrolu yok)."""
    tutulan, gorulen = [], set()
    for c in cumleler:
        uygun = isinstance(c, str) and OKUL_EN_AZ_KELIME <= kelime_say(c) <= OKUL_EN_COK_KELIME
        if uygun and normal(c) not in gorulen:
            gorulen.add(normal(c))
            tutulan.append(c.strip())
    return tutulan


def okul_suz(cumleler) -> list[str]:
    """3-6 kelimelik, tekrarsiz cumleleri tutar; yeterli sayi yoksa ValueError."""
    if not isinstance(cumleler, list):
        raise ValueError("cumleler liste degil")
    tutulan = okul_uygunlari(cumleler)
    if len(tutulan) < OKUL_CUMLE_SAYISI:
        raise ValueError(f"{OKUL_EN_AZ_KELIME}-{OKUL_EN_COK_KELIME} kelimelik farkli cumle "
                         f"{len(tutulan)}, gereken {OKUL_CUMLE_SAYISI}")
    return tutulan[:OKUL_CUMLE_SAYISI]


def gecerli_bilgiler(bilgiler: list, onceki_dersler: list[dict], okul: list[str]) -> list[dict]:
    """Bicimi bozuk, onceki gecelerle ayni ya da cevabi egitim cumlesine sizan bilgileri atar
    (sayi kontrolu yok; biriktirici parti parti cagirir)."""
    eski_bilgi = {normal(b["bilgi"]) for d in onceki_dersler for b in d["bilgiler"]}
    eski_egitim = [normal(c) for d in onceki_dersler for c in egitim_cumleleri(d)]
    eski_sorular = [doldur(s["soru"], s["cevap"]) for d in onceki_dersler for s in sabah_sorulari(d)]
    saglam = [b for b in bilgiler if bilgi_bicim_sorunu(b) is None
              and normal(b["bilgi"]) not in eski_bilgi]
    yeni_egitim = [normal(c) for b in saglam for c in b["cumlelemeler"]] + [normal(c) for c in okul]
    tutulan = []
    for b in saglam:
        kendi = [normal(c) for c in b["cumlelemeler"]]
        if sizar_mi(doldur(b["soru"], b["cevap"]), eski_egitim + yeni_egitim):
            continue
        if any(sizar_mi(s, kendi) for s in eski_sorular):
            continue
        tutulan.append(b)
    return tutulan


def bilgileri_suz(bilgiler, onceki_dersler: list[dict], okul: list[str]) -> list[dict]:
    """gecerli_bilgiler + sayi kontrolu. Yeterli bilgi kalmazsa ValueError."""
    if not isinstance(bilgiler, list):
        raise ValueError("bilgiler liste degil")
    tutulan = gecerli_bilgiler(bilgiler, onceki_dersler, okul)
    if len(tutulan) < BILGI_SAYISI:
        sorunlar = sorted({s for s in map(bilgi_bicim_sorunu, bilgiler) if s})
        raise ValueError(f"gecerli bilgi {len(tutulan)}/{len(bilgiler)}, gereken {BILGI_SAYISI}; "
                         f"bicim sorunlari: {sorunlar or 'yok, sizinti ya da tekrar'}")
    return tutulan[:BILGI_SAYISI]


def sizinti_var(dersler: list[dict]) -> bool:
    """Butun gecelerin sabah sorularindan biri herhangi bir gecenin egitim cumlesinde geciyor mu."""
    egitim = [normal(c) for d in dersler for c in egitim_cumleleri(d)]
    return any(sizar_mi(doldur(s["soru"], s["cevap"]), egitim)
               for d in dersler for s in sabah_sorulari(d))
