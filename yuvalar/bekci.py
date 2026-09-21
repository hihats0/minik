"""Cikis kapisi: Kafa'nin cevabi agiza gitmeden burada sozluk kufur bayragiyla suzulur.
Cagiran: minik.py akisi."""

import re
import time

from ortak import log
from ortak.ayar import BEKCI_KUFUR_KALIPLARI

YUVA_ADI = "bekci"
# odul_kural.py'deki normalize() ile ayni adimlar: Turkce harfleri ASCII'ye indirir, boylece
# "sağol" ve "sagol" ayni token olur. Olculmus dogruluk (%80,5) bu adimlara bagli, sadelestirilmez.
ASCII_HARITA = str.maketrans("ışğüöç", "isguoc")
KUFUR_REGEX = re.compile("|".join(f"(?:{k})" for k in BEKCI_KUFUR_KALIPLARI))

GEREKCE_TEMIZ = "sozlukte kufur kalibiyla eslesme yok"
GEREKCE_KUFUR = "sozluk kufur bayragi tuttu"
GEREKCE_COKTU = "bekci hata verdi, varsayilan hayir (spec 3.7)"


def cikabilir_mi(metin):
    """(evet_hayir, gerekce) dondurur. Gerekce hicbir yolda bos donmez. Bekci kendi icinde
    cokerse (beklenmeyen tipte girdi vb.) hatayi yutmaz, loglar ve varsayilan "hayir" doner:
    kapali kapi acik kapidan guvenlidir (spec 3.7, K20: emniyet kapisi hicbir hormondan
    etkilenmez, eşiği sabittir)."""
    basladi = time.perf_counter()
    try:
        kufurlu = _kufur_var_mi(metin)
    except Exception as hata:
        log.yaz(YUVA_ADI, "cikabilir_mi", _gecen_ms(basladi), "hata", {"hata": str(hata)})
        return False, GEREKCE_COKTU
    evet_hayir = not kufurlu
    gerekce = GEREKCE_KUFUR if kufurlu else GEREKCE_TEMIZ
    log.yaz(YUVA_ADI, "cikabilir_mi", _gecen_ms(basladi), "ok",
            {"evet_hayir": evet_hayir, "gerekce": gerekce})
    return evet_hayir, gerekce


def _kufur_var_mi(metin):
    """Metni normallestirir, token'lara boler, herhangi biri kufur kalibiyla TAM eslesiyor mu
    bakar (bastan/sondan degil TAM: "sikinti" gibi yanlis eslesme olmasin diye, odul_kural.py)."""
    normal = _normalize(metin)
    tokenlar = re.findall(r"[a-z0-9]+", normal)
    return any(KUFUR_REGEX.fullmatch(t) for t in tokenlar)


def _normalize(metin):
    """Kucult (I/İ dahil), ASCII'ye indir, gizleme noktalarini sil, harf tekrarlarini teke indir."""
    s = metin.replace("İ", "i").replace("I", "ı").lower().translate(ASCII_HARITA)
    s = re.sub(r"(?<=[a-z])[.*](?=[a-z])", "", s)
    return re.sub(r"(.)\1+", r"\1", s)


def _gecen_ms(basladi):
    """Olcum baslangicindan bu yana gecen sureyi tam sayi milisaniye verir."""
    return int((time.perf_counter() - basladi) * 1000)
