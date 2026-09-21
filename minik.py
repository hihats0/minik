"""Akis: sirayi tutar, karar vermez (K6). Agizdan alir, Kafa'ya sorar, Defter'e yazar,
agiza soyler, loglar. Cagiran: elle `python minik.py` ile baslatilir."""

import time

from agiz import konsol
from ortak import log
from yuvalar import defter, kafa

YUVA_ADI = "akis"
DIS_ID = "konsol"
CIKIS_KELIMESI = "cik"
DUSUNEMIYORUM_METNI = "Su an dusunemiyorum."
DEFTER_HATASI_METNI = "Defter yazilamadi, Minik duruyor."


def calistir(dinle=konsol.dinle, soyle=konsol.soyle, dusun=kafa.dusun):
    """Sohbet dongusu: dinle -> dusun -> soyle -> Defter'e yaz -> logla. `cik` yazilinca
    durur; Defter yazamazsa da durur (kaydedilmeyen konusma en pahali kayiptir, spec 3.4).
    dinle/soyle/dusun disaridan verilebilir: agiz degisince bu dosya degismez (spec 2.6)."""
    baglam = _gecmisten_baglam_yukle()
    while True:
        soru = dinle()
        if soru == CIKIS_KELIMESI:
            break
        cevap, basarili = _tur_isle(soru, baglam, dusun)
        soyle(cevap, DIS_ID)
        if basarili and not _deftere_kaydet(soru, cevap, soyle):
            break


def _gecmisten_baglam_yukle():
    """Defter'deki son kayitlari Kafa'nin baglamina cevirir: f1'deki 'baglam sinirsiz
    buyuyor' acigini kapatir (f2, V14). Her kayit bir soru + bir cevap mesaji olur."""
    baglam = []
    for kayit in defter.oku():
        baglam.append({"role": "user", "content": kayit.get("soru", "")})
        baglam.append({"role": "assistant", "content": kayit.get("cevap", "")})
    return baglam


def _deftere_kaydet(soru, cevap, soyle):
    """Turu Defter'e yazar. Yazim basarisiz olursa akisi durdurur ve kullaniciya haber
    verir; hata burada yutulmaz, hem Defter kendi satirini hem akis kendi satirini loglar."""
    try:
        defter.yaz({"soru": soru, "cevap": cevap, "platform": DIS_ID})
        return True
    except OSError as hata:
        log.yaz(YUVA_ADI, "tur", 0, "hata", {"hata": f"defter yazilamadi: {hata}"})
        soyle(DEFTER_HATASI_METNI, DIS_ID)
        return False


def _tur_isle(soru, baglam, dusun):
    """Tek bir soru-cevap turunu isler, (cevap, basarili_mi) dondurur. Kafa hata yukseltirse
    akis cokmez, kullaniciya haber verir ve nedenini loglar (hata burada kasitli yakalanir,
    yutulmaz: loglanip haber verilir). basarili_mi=False ise Defter'e yazilmaz: "Su an
    dusunemiyorum" gercek bir konusma degil, ham kayda girmemeli."""
    basladi = time.perf_counter()
    try:
        cevap = dusun(soru, baglam)
    except Exception as hata:
        log.yaz(YUVA_ADI, "tur", _gecen_ms(basladi), "hata", {"hata": str(hata)})
        return DUSUNEMIYORUM_METNI, False
    baglam.append({"role": "user", "content": soru})
    baglam.append({"role": "assistant", "content": cevap})
    log.yaz(YUVA_ADI, "tur", _gecen_ms(basladi), "ok", {"soru_uzunlugu": len(soru)})
    return cevap, True


def _gecen_ms(basladi):
    """Olcum baslangicindan bu yana gecen sureyi tam sayi milisaniye verir."""
    return int((time.perf_counter() - basladi) * 1000)


if __name__ == "__main__":
    calistir()
