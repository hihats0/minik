"""Merak akisi (f10-b): merak edilen sorgu -> web.ara -> iddia esleme -> Bekci giris kapisi -> Defter.
Uc agiz dolmayan iddia Defter'e girmez, loglanir. Cagiran: araclar/f10b-merak-dene.py, testler."""

import time

from agiz import web
from ortak import log
from yuvalar import bekci_giris, defter, iddia_esle

YUVA_ADI = "merak"
PLATFORM = "web"


def ogren(baglanti, sorgu, tarih, ara=web.ara, ayni_mi=iddia_esle.basit_ayni_mi, yaz=defter.yaz):
    """Sorguyu arar, iddialari gruplar, her grubu Bekci'ye sorar; gecenleri Defter'e yazar, onlari dondurur."""
    basladi = time.perf_counter()
    gruplar = iddia_esle.grupla(ara(sorgu), ayni_mi)
    kabul = [g for g in gruplar if _bekci_gecirir_mi(baglanti, g, tarih)]
    for g in kabul:
        yaz({"soru": g["iddia"], "cevap": g["kayitlar"][0]["cevap"], "kaynak": ",".join(g["alanlar"]),
             "platform": PLATFORM, "sorgu": sorgu, "adresler": [k["adres"] for k in g["kayitlar"]]})
    log.yaz(YUVA_ADI, "ogren", _gecen_ms(basladi), "ok",
            {"sorgu": sorgu, "grup": len(gruplar), "kabul": len(kabul),
             "en_cok_alan": max((len(g["alanlar"]) for g in gruplar), default=0)})
    return kabul


def _bekci_gecirir_mi(baglanti, grup, tarih):
    """Grubun her alan adini ayri agiz olarak Bekci'ye sorar; son karar (hepsi sayildiktan sonra) gecerlidir."""
    karar, gerekce = False, ""
    for alan in grup["alanlar"]:
        karar, gerekce = bekci_giris.gecsin_mi(baglanti, grup["iddia"], alan, tarih, PLATFORM)
    if not karar:
        log.yaz(YUVA_ADI, "defter_disi", 0, "ok", {"iddia": grup["iddia"][:120], "alanlar": grup["alanlar"],
                                                   "gerekce": gerekce})
    return karar


def _gecen_ms(basladi):
    """Baslangictan bu yana gecen milisaniye."""
    return int((time.perf_counter() - basladi) * 1000)
