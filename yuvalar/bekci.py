"""Cikis kapisi: Kafa'nin cevabi agiza gitmeden iki kapidan gecer. Emniyet kapisi (hakaret/nefret,
tehdit, kisisel veri, cinsel+cocuk) ENGELLER; karakter kapisi (siradan kufur) gecirir, loglar.
Cagiran: minik.py akisi."""

import re
import time

from ortak import log
from ortak.ayar import (BEKCI_EMNIYET_CINSEL, BEKCI_EMNIYET_COCUK, BEKCI_EMNIYET_HAKARET,
                        BEKCI_EMNIYET_KISISEL_VERI, BEKCI_EMNIYET_TEHDIT, BEKCI_KARAKTER_KALIPLARI)

YUVA_ADI = "bekci"
# odul_kural.py'deki normalize() ile ayni adimlar: Turkce harfleri ASCII'ye indirir, boylece
# "sağol" ve "sagol" ayni token olur. Karakter bayraginin olculmus dogrulugu (%80,5) bu adimlara bagli.
ASCII_HARITA = str.maketrans("ışğüöç", "isguoc")
KARAKTER_REGEX = re.compile("|".join(f"(?:{k})" for k in BEKCI_KARAKTER_KALIPLARI))


def _kelime_regex(kaliplar):
    """Kaliplari tek regex'e toplar, kelime sinirlariyla (kelime ortasinda eslesmesin)."""
    return re.compile(r"\b(?:" + "|".join(f"(?:{k})" for k in kaliplar) + r")\b")


HAKARET_REGEX = _kelime_regex(BEKCI_EMNIYET_HAKARET)
TEHDIT_REGEX = _kelime_regex(BEKCI_EMNIYET_TEHDIT)
COCUK_REGEX = _kelime_regex([BEKCI_EMNIYET_COCUK])
CINSEL_REGEX = _kelime_regex([BEKCI_EMNIYET_CINSEL])
KISISEL_VERI_REGEX = re.compile("|".join(f"(?:{k})" for k in BEKCI_EMNIYET_KISISEL_VERI))

GEREKCE_TEMIZ = "iki kapi da temiz"
GEREKCE_KARAKTER = "karakter kapisi: siradan kufur, gecti (loglandi)"
GEREKCE_EMNIYET = "emniyet kapisi engelledi: "
GEREKCE_COKTU = "bekci hata verdi, varsayilan hayir (spec 3.7)"


def cikabilir_mi(metin):
    """(evet_hayir, gerekce) dondurur; gerekce hangi kapinin tuttugunu soyler, hicbir yolda bos
    donmez. Emniyet kapisi once bakilir, esigi sabit (K20). Bekci cokerse hatayi loglar ve
    varsayilan "hayir" doner: kapali kapi acik kapidan guvenlidir (spec 3.7)."""
    basladi = time.perf_counter()
    try:
        emniyet = _emniyet_ihlali(metin)
        karakter = _karakter_bayragi(metin)
    except Exception as hata:
        log.yaz(YUVA_ADI, "cikabilir_mi", _gecen_ms(basladi), "hata", {"hata": str(hata)})
        return False, GEREKCE_COKTU
    evet_hayir = emniyet is None
    if emniyet:
        gerekce = GEREKCE_EMNIYET + emniyet
    else:
        gerekce = GEREKCE_KARAKTER if karakter else GEREKCE_TEMIZ
    log.yaz(YUVA_ADI, "cikabilir_mi", _gecen_ms(basladi), "ok",
            {"evet_hayir": evet_hayir, "gerekce": gerekce, "karakter_bayragi": karakter})
    return evet_hayir, gerekce


def _emniyet_ihlali(metin):
    """Ihlal turunun adini ya da None dondurur. Kisisel veri ham metinde, digerleri normalde aranir."""
    if KISISEL_VERI_REGEX.search(metin):
        return "kisisel veri"
    normal = _normalize(metin)
    if HAKARET_REGEX.search(normal):
        return "hakaret/nefret"
    if TEHDIT_REGEX.search(normal):
        return "tehdit"
    if COCUK_REGEX.search(normal) and CINSEL_REGEX.search(normal):
        return "cinsel icerik + cocuk"
    return None


def _karakter_bayragi(metin):
    """Herhangi bir token karakter kufur kalibiyla TAM eslesiyor mu (bastan/sondan degil TAM:
    "sikinti" gibi yanlis eslesme olmasin diye, odul_kural.py)."""
    tokenlar = re.findall(r"[a-z0-9]+", _normalize(metin))
    return any(KARAKTER_REGEX.fullmatch(t) for t in tokenlar)


def _normalize(metin):
    """Kucult (I/İ dahil), ASCII'ye indir, gizleme noktalarini sil, harf tekrarlarini teke indir."""
    s = metin.replace("İ", "i").replace("I", "ı").lower().translate(ASCII_HARITA)
    s = re.sub(r"(?<=[a-z])[.*](?=[a-z])", "", s)
    return re.sub(r"(.)\1+", r"\1", s)


def _gecen_ms(basladi):
    """Olcum baslangicindan bu yana gecen sureyi tam sayi milisaniye verir."""
    return int((time.perf_counter() - basladi) * 1000)
