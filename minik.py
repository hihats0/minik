"""Akis: sirayi tutar, karar vermez (K6). Agizdan alir, Kafa'ya sorar, Bekci'den gecirir,
Defter'e yazar, agiza soyler, loglar. Her turda Hormonlar'i olayla gunceller (R1: akis
gunceller, ama hangi hormonun nasil degisecegine hormonlar.py karar verir).
Cagiran: elle `python minik.py` ile baslatilir."""

import time

from agiz import konsol
from ortak import baglam_butce, kaynak_olc, log
from ortak.ayar import KORTIZOL_CEZA_SIDDETI, MELATONIN_IS_TAVAN_SN
from yuvalar import bekci, defter, hormonlar, kafa

YUVA_ADI = "akis"
DIS_ID = "konsol"
CIKIS_KELIMESI = "cik"
DUSUNEMIYORUM_METNI = "Su an dusunemiyorum."
DEFTER_HATASI_METNI = "Defter yazilamadi, Minik duruyor."
ENGELLENDI_METNI = "Bunu boyle soyleyemem."


def calistir(dinle=konsol.dinle, soyle=konsol.soyle, dusun=kafa.dusun, hormon_durumu=None):
    """Sohbet dongusu: dinle -> dusun -> soyle -> Defter'e yaz -> logla. `cik` yazilinca
    durur; Defter yazamazsa da durur (kaydedilmeyen konusma en pahali kayiptir, spec 3.4).
    dinle/soyle/dusun disaridan verilebilir: agiz degisince bu dosya degismez (spec 2.6).
    dusun (cevap, is_sn) dondurur (yuvalar/kafa.py sozlesmesi).
    hormon_durumu da disaridan verilebilir (testler icin); verilmezse taze bir Hormonlar()
    baslar, yani her calistir() cagrisi dinlenme degerleriyle acilir (defter/hormon.json gibi
    bir kalicilik bu kosunun kapsaminda degil, bkz. rapor)."""
    baglam = _gecmisten_baglam_yukle()
    hormon_durumu = hormon_durumu if hormon_durumu is not None else hormonlar.Hormonlar()
    while True:
        soru = dinle()
        if soru == CIKIS_KELIMESI:
            break
        cevap, basarili = _tur_isle(soru, baglam, dusun, hormon_durumu)
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


def _tur_isle(soru, baglam, dusun, hormon_durumu):
    """Tek bir soru-cevap turunu isler, (cevap, basarili_mi) dondurur. Kafa hata yukseltirse
    akis cokmez, kullaniciya haber verir, kortizolu "ceza" olayiyla yukseltir ve nedenini loglar
    (hata burada kasitli yakalanir, yutulmaz). Basarili cagri "calisma" olayiyla melatonini
    Kafa'nin llama-server'da harcadigi gercek is saniyesine gore yukseltir (K10, f3-e). Kafa'nin cevabi agiza gitmeden Bekci'den
    gecer (K6: karari Bekci verir, akis sadece uygular); Bekci "hayir" derse sabit metin soylenir.
    basarili_mi=False ise Defter'e yazilmaz: ne "Su an dusunemiyorum" ne de Bekci'nin engelledigi
    cevap gercek bir konusmadir, ham kayda girmemeli."""
    basladi = time.perf_counter()
    hormon_degerleri = hormon_durumu.oku()
    baglam_butce.sinirla(baglam, soru)  # f3-f: 8192'lik baglam ~21. turda tasiyordu
    try:
        cevap, is_sn = dusun(soru, baglam, hormon_degerleri)
    except Exception as hata:
        hormon_durumu.guncelle("ceza", KORTIZOL_CEZA_SIDDETI)
        log.yaz(YUVA_ADI, "tur", _gecen_ms(basladi), "hata", {"hata": str(hata)})
        return DUSUNEMIYORUM_METNI, False
    hormon_durumu.guncelle("calisma", kaynak_olc.siddet(is_sn, MELATONIN_IS_TAVAN_SN))
    gecebilir, gerekce = bekci.cikabilir_mi(cevap)
    if not gecebilir:
        log.yaz(YUVA_ADI, "tur", _gecen_ms(basladi), "ok", {"bekci": "engellendi", "gerekce": gerekce})
        return ENGELLENDI_METNI, False
    baglam.append({"role": "user", "content": soru})
    baglam.append({"role": "assistant", "content": cevap})
    log.yaz(YUVA_ADI, "tur", _gecen_ms(basladi), "ok", {"soru_uzunlugu": len(soru)})
    return cevap, True


def _gecen_ms(basladi):
    """Olcum baslangicindan bu yana gecen sureyi tam sayi milisaniye verir."""
    return int((time.perf_counter() - basladi) * 1000)


if __name__ == "__main__":
    calistir()
