"""Sorudan beyaz listeli hesabi kaba duzenli ifadeyle tanir, Kafa'ya verilecek baglam mesajini kurar.
Cagiran: minik.py (_kafa_baglami), tests/test_calgicilar.py."""

import re

from ortak import log
from yuvalar import calgicilar

YUVA_ADI = "calgici_tani"
# Kaba tanima: yalniz rakamla yazilmis acik bicimler. "iki arti uc" taninmaz (raporda).
TARIH_KALIBI = re.compile(r"(\d{4}-\d{2}-\d{2})\D+(\d{4}-\d{2}-\d{2})")
BIRIM_ADI = r"(mm|cm|km|kg|saat|sn|dk|m|g)"
BIRIM_KALIBI = re.compile(r"(\d+(?:[.,]\d+)?)\s*" + BIRIM_ADI + r"\s+ka[cç]\s+" + BIRIM_ADI + r"\b")
ISLEM_KALIBI = re.compile(r"\d+(?:\.\d+)?(?:\s*[-+*/]\s*\d+(?:\.\d+)?)+")


def tani(soru):
    """(gorev_tipi, girdi) ya da None. Sira onemli: tarih '-' icerdigi icin once ona bakilir."""
    tarih = TARIH_KALIBI.search(soru)
    if tarih:
        return "tarih_farki", f"{tarih.group(1)} {tarih.group(2)}"
    birim = BIRIM_KALIBI.search(soru)
    if birim:
        return "birim_cevirme", " ".join(birim.groups())
    islem = ISLEM_KALIBI.search(soru)
    if islem:
        return "dort_islem", islem.group(0)
    return None


def baglam_mesaji(soru, hormon_durumu=None):
    """Hesap taninirsa Calgici'nin sonucunu sistem mesaji olarak dondurur, yoksa None.
    Calgici hata verirse akis durmaz: hata loglanir, Kafa hesapsiz devam eder."""
    gorev = tani(soru)
    if gorev is None:
        return None
    try:
        sonuc, iz = calgicilar.cal(gorev[0], gorev[1], hormon_durumu)
    except ValueError as hata:
        log.yaz(YUVA_ADI, "tani", 0, "hata", {"hata": str(hata), "gorev_tipi": gorev[0]})
        return None
    if sonuc is None:
        metin = f"Calgici: {gorev[1]} icin iki yol ayristi, sonuc guvenilmez. Iz: {'; '.join(iz)}"
    else:
        metin = f"Calgici hesapladi: {gorev[1]} = {sonuc}. Bu sayiyi kullan. Iz: {'; '.join(iz)}"
    return {"role": "system", "content": metin}
