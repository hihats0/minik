"""Cikis kapisi: Kafa'nin cevabi agiza gitmeden iki kapidan gecer. Emniyet kapisi (hakaret/nefret,
tehdit, kisisel veri, cinsel+cocuk) ENGELLER; karakter kapisi (siradan kufur) gecirir, loglar.
Cagiran: minik.py akisi."""

import re
import time

from ortak import log
from ortak.ayar import (BEKCI_EMNIYET_CINSEL, BEKCI_EMNIYET_COCUK, BEKCI_EMNIYET_HAKARET,
                        BEKCI_EMNIYET_KISISEL_VERI, BEKCI_EMNIYET_TEHDIT)
from yuvalar.ton_kural import kufur_var_mi, normalize

YUVA_ADI = "bekci"


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
        karakter = kufur_var_mi(metin)  # olculmus dogruluk (%80,5) ton_kural.normalize'a bagli
    except Exception as hata:
        log.yaz(YUVA_ADI, "cikabilir_mi", log.gecen_ms(basladi), "hata", {"hata": str(hata)})
        return False, GEREKCE_COKTU
    evet_hayir = emniyet is None
    if emniyet:
        gerekce = GEREKCE_EMNIYET + emniyet
    else:
        gerekce = GEREKCE_KARAKTER if karakter else GEREKCE_TEMIZ
    log.yaz(YUVA_ADI, "cikabilir_mi", log.gecen_ms(basladi), "ok",
            {"evet_hayir": evet_hayir, "gerekce": gerekce, "karakter_bayragi": karakter})
    return evet_hayir, gerekce


def _emniyet_ihlali(metin):
    """Ihlal turunun adini ya da None dondurur. Kisisel veri ham metinde, digerleri normalde aranir."""
    if KISISEL_VERI_REGEX.search(metin):
        return "kisisel veri"
    normal = normalize(metin)
    if HAKARET_REGEX.search(normal):
        return "hakaret/nefret"
    if TEHDIT_REGEX.search(normal):
        return "tehdit"
    if COCUK_REGEX.search(normal) and CINSEL_REGEX.search(normal):
        return "cinsel icerik + cocuk"
    return None

