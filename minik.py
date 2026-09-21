"""Akis: sirayi tutar, karar vermez (K6). Agizdan alir, Kafa'ya sorar, agiza soyler, loglar.
Cagiran: elle `python minik.py` ile baslatilir."""

import time

from agiz import konsol
from ortak import log
from yuvalar import kafa

YUVA_ADI = "akis"
DIS_ID = "konsol"
CIKIS_KELIMESI = "cik"
DUSUNEMIYORUM_METNI = "Su an dusunemiyorum."


def calistir(dinle=konsol.dinle, soyle=konsol.soyle, dusun=kafa.dusun):
    """Sohbet dongusu: dinle -> dusun -> soyle -> logla. `cik` yazilinca durur.
    dinle/soyle/dusun disaridan verilebilir: agiz degisince bu dosya degismez (spec 2.6)."""
    baglam = []
    while True:
        soru = dinle()
        if soru == CIKIS_KELIMESI:
            break
        cevap = _tur_isle(soru, baglam, dusun)
        soyle(cevap, DIS_ID)


def _tur_isle(soru, baglam, dusun):
    """Tek bir soru-cevap turunu isler. Kafa hata yukseltirse akis cokmez, kullaniciya haber
    verir ve nedenini loglar (hata burada kasitli yakalanir, yutulmaz: loglanip haber verilir)."""
    basladi = time.perf_counter()
    try:
        cevap = dusun(soru, baglam)
    except Exception as hata:
        log.yaz(YUVA_ADI, "tur", _gecen_ms(basladi), "hata", {"hata": str(hata)})
        return DUSUNEMIYORUM_METNI
    baglam.append({"role": "user", "content": soru})
    baglam.append({"role": "assistant", "content": cevap})
    log.yaz(YUVA_ADI, "tur", _gecen_ms(basladi), "ok", {"soru_uzunlugu": len(soru)})
    return cevap


def _gecen_ms(basladi):
    """Olcum baslangicindan bu yana gecen sureyi tam sayi milisaniye verir."""
    return int((time.perf_counter() - basladi) * 1000)


if __name__ == "__main__":
    calistir()
