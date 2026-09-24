"""Akis: sirayi tutar, karar vermez (K6). Agizdan alir, Kafa'ya sorar, Bekci'den gecirir,
Defter'e yazar, agiza soyler, loglar. Kalp'in refleks onerisi golge modda yalniz loglanir (f6). Hesap taninirsa Calgici sonucu Kafa'ya baglam olur (f7). Tur sonunda Uyku tetigine sorar, "uyu" derse gece isini
cagirir (P5, A7: ayri surec degil). Her turda Hormonlar'i olayla gunceller (R1: akis
gunceller, ama hangi hormonun nasil degisecegine hormonlar.py karar verir).
Cagiran: elle `python minik.py` ile baslatilir."""

import time
from datetime import datetime

from agiz import konsol, secim
from ortak import baglam_butce, kaynak_olc, log
from ortak.ayar import HORMON_DOSYA_ADI, KORTIZOL_CEZA_SIDDETI, MELATONIN_IS_TAVAN_SN
from yuvalar import bekci, calgici_tani, defter, hormonlar, kafa, kalp, ton, ton_hormon, uyku, uyku_tetik

YUVA_ADI = "akis"
DIS_ID = "konsol"
CIKIS_KELIMESI = "cik"
DUSUNEMIYORUM_METNI = "Su an dusunemiyorum."
DEFTER_HATASI_METNI = "Defter yazilamadi, Minik duruyor."
ENGELLENDI_METNI = "Bunu boyle soyleyemem."
DAKIKA_SAAT = 60


def calistir(dinle=konsol.dinle, soyle=konsol.soyle, dusun=kafa.dusun, hormon_durumu=None,
             gece=uyku.gece, simdi=datetime.now, platform=DIS_ID, ton_oku=ton.ton_oku):
    """Sohbet dongusu: dinle -> dusun -> soyle -> Defter'e yaz -> uyku tetigi -> logla. `cik`
    yazilinca durur; Defter yazamazsa da durur (kaydedilmeyen konusma en pahali kayiptir, spec 3.4).
    dinle/soyle/dusun/gece/simdi disaridan verilebilir: agiz degisince bu dosya degismez (spec 2.6).
    hormon_durumu verilmezse defter/hormon.json'dan yuklenir, her olayda oraya yazilir (f4-c).
    platform Defter kaydina ve soyle'nin dis_id'sine gider (f8-a: dosya agzi "dosya" yazar).
    Ton gecikmeli islenir (spec 2.3 madde 11): cevap soylenip Defter'e yazildiktan sonra; sonraki cevaba girer."""
    baglam = _gecmisten_baglam_yukle()
    if hormon_durumu is None:
        hormon_durumu = hormonlar.Hormonlar(defter.DEFTER_KLASORU / HORMON_DOSYA_ADI)
    tetik = uyku_tetik.UykuTetigi()
    while True:
        soru = dinle()
        if soru == CIKIS_KELIMESI:
            break
        dopamin_once = hormon_durumu.oku()["dopamin"]
        oneri, _ = kalp.refleks_ara({"soru": soru})  # golge mod (f6): yalniz loglanir, cevaba girmez
        cevap, basarili = _tur_isle(soru, baglam, dusun, hormon_durumu)
        soyle(cevap, platform)
        degisim = hormon_durumu.oku()["dopamin"] - dopamin_once
        if basarili and not _deftere_kaydet(soru, cevap, soyle, degisim, platform):
            break
        if basarili:
            kalp.tur_sonu(soru, cevap, oneri, degisim)
            ton_hormon.isle(soru, hormon_durumu, ton_oku)
        _uyku_gerekirse(tetik, hormon_durumu, gece, simdi())


def _uyku_gerekirse(tetik, hormon_durumu, gece, an):
    """Karari uyku_tetik verir (K6); akis yalniz sorar ve "uyu" denirse gece isini cagirir.
    Gece isi hata verirse akis durmaz, hata loglanir (Minik ertesi yorgunlukta yeniden dener)."""
    saat = an.hour + an.minute / DAKIKA_SAAT
    if not tetik.uyumali_mi(hormon_durumu.oku()["melatonin"], saat):
        return
    tarih = an.date().isoformat()
    try:
        gece(tarih, hormon_durumu=hormon_durumu, klasor=defter.DEFTER_KLASORU)
    except Exception as hata:
        log.yaz(YUVA_ADI, "uyku", 0, "hata", {"hata": f"gece isi basarisiz: {hata}", "tarih": tarih})
        return
    log.yaz(YUVA_ADI, "uyku", 0, "ok", {"tarih": tarih, "yas": hormon_durumu.yas})


def _gecmisten_baglam_yukle():
    """Defter'deki son kayitlari Kafa'nin baglamina cevirir: f1'deki 'baglam sinirsiz
    buyuyor' acigini kapatir (f2, V14). Her kayit bir soru + bir cevap mesaji olur."""
    baglam = []
    for kayit in defter.oku():
        baglam.append({"role": "user", "content": kayit.get("soru", "")})
        baglam.append({"role": "assistant", "content": kayit.get("cevap", "")})
    return baglam


def _deftere_kaydet(soru, cevap, soyle, dopamin_degisimi, platform):
    """Turu Defter'e yazar; dopamin_degisimi Uyku'nun onceligine girer (spec 2.4 adim 2). Yazim basarisiz olursa akisi durdurur ve kullaniciya haber
    verir; hata burada yutulmaz, hem Defter kendi satirini hem akis kendi satirini loglar."""
    try:
        defter.yaz({"soru": soru, "cevap": cevap, "platform": platform,
                    "dopamin_degisimi": round(dopamin_degisimi, 3)})
        return True
    except OSError as hata:
        log.yaz(YUVA_ADI, "tur", 0, "hata", {"hata": f"defter yazilamadi: {hata}"})
        soyle(DEFTER_HATASI_METNI, platform)
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
        cevap, is_sn = dusun(soru, _kafa_baglami(soru, baglam, hormon_durumu), hormon_degerleri)
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


def _kafa_baglami(soru, baglam, hormon_durumu):
    """Hesap taninirsa Calgici sonucu bu tura ozel sistem mesaji olarak eklenir (f7), kalici
    baglama girmez. Hesap sonucu Kafa'nin metninden okunmaz, hep Calgici'dan gelir (spec 3.3)."""
    ek = calgici_tani.baglam_mesaji(soru, hormon_durumu)
    return baglam if ek is None else baglam + [ek]


def _gecen_ms(basladi):
    """Olcum baslangicindan bu yana gecen sureyi tam sayi milisaniye verir."""
    return int((time.perf_counter() - basladi) * 1000)


if __name__ == "__main__":
    dinle_, soyle_, platform_ = secim.agiz_sec()
    calistir(dinle=dinle_, soyle=soyle_, platform=platform_)
