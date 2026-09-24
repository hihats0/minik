"""Merak akisi (f10-b): merak edilen sorgu -> web.ara -> iddia esleme -> Bekci giris kapisi -> Defter.
Uc agiz dolmayan iddia Defter'e girmez, loglanir; K34 revize: yalniz Wikimedia "vikipedi_okudum"
etiketiyle girer, Wikimedia + bir bagimsiz agiz tam kabul. Cagiran: araclar/f10b-merak-dene.py, testler."""

import time

from agiz import web
from ortak import log
from yuvalar import bekci_giris, defter, iddia_esle

YUVA_ADI = "merak"
PLATFORM = "web"
# K34 revize (Yigit, 24 Eyl): Vikipedi tek agiz ama guvenilir; tek basina etiketli girer.
WIKIMEDIA = "wikimedia"
GUVEN_TAM = "tam"
GUVEN_VIKIPEDI = "vikipedi_okudum"
VIKIPEDI_TEYIT_AGZI = 2  # Wikimedia + en az bir bagimsiz agiz


def ogren(baglanti, sorgu, tarih, ara=web.ara, ayni_mi=iddia_esle.basit_ayni_mi, yaz=defter.yaz):
    """Sorguyu arar, iddialari gruplar, her grubu Bekci'ye sorar; gecenleri Defter'e yazar, onlari dondurur."""
    basladi = time.perf_counter()
    gruplar = iddia_esle.grupla(ara(sorgu), ayni_mi)
    kabul = [g for g in gruplar if _guven_ata(g, _bekci_gecirir_mi(baglanti, g, tarih))]
    for g in kabul:
        yaz({"guven": g["guven"], "soru": g["iddia"], "cevap": g["kayitlar"][0]["cevap"], "kaynak": ",".join(g["alanlar"]),
             "platform": PLATFORM, "sorgu": sorgu, "adresler": [k["adres"] for k in g["kayitlar"]]})
    log.yaz(YUVA_ADI, "ogren", _gecen_ms(basladi), "ok",
            {"sorgu": sorgu, "grup": len(gruplar), "kabul": len(kabul),
             "en_cok_alan": max((len(g["alanlar"]) for g in gruplar), default=0),
             "en_cok_agiz": max((len(g["agizlar"]) for g in gruplar), default=0)})
    return kabul


def guven_duzeyi(agizlar, bekci_karari):
    """Grubun Defter guveni: Bekci gecirdiyse ya da Wikimedia + bagimsiz agiz varsa GUVEN_TAM,
    yalniz Wikimedia ise GUVEN_VIKIPEDI, degilse None (Defter'e girmez)."""
    wikimedia_var = WIKIMEDIA in agizlar
    if bekci_karari or (wikimedia_var and len(agizlar) >= VIKIPEDI_TEYIT_AGZI):
        return GUVEN_TAM
    return GUVEN_VIKIPEDI if wikimedia_var else None


def _guven_ata(grup, bekci_karari):
    """Gruba guven duzeyini yazar; Defter'e girecekse True."""
    grup["guven"] = guven_duzeyi(grup["agizlar"], bekci_karari)
    return grup["guven"] is not None


def _bekci_gecirir_mi(baglanti, grup, tarih):
    """Grubun her kurumunu (K34: ayni kurumun alanlari tek agiz) Bekci'ye sorar; son karar gecerlidir."""
    karar, gerekce = False, ""
    for agiz in grup["agizlar"]:
        karar, gerekce = bekci_giris.gecsin_mi(baglanti, grup["iddia"], agiz, tarih, PLATFORM)
    if not karar:
        log.yaz(YUVA_ADI, "defter_disi", 0, "ok", {"iddia": grup["iddia"][:120], "agizlar": grup["agizlar"],
                                                   "gerekce": gerekce})
    return karar


def _gecen_ms(basladi):
    """Baslangictan bu yana gecen milisaniye."""
    return int((time.perf_counter() - basladi) * 1000)
