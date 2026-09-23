"""Kalp yuvasi (spec 3.2, f6): refleks onerir ama golge modda, oneri yalniz loglanir, uygulanmaz.
Cagiran: minik.py (her turda refleks_ara ve tur_sonu), araclar/f6-ayrisma-olc.py, tests/test_kalp.py."""

import json
import re
import time
from datetime import datetime

from ortak import log
from yuvalar import defter

YUVA_ADI = "kalp"
REFLEKS_DOSYA_ADI = "refleksler.json"
DOGMA_ESIGI = 3  # spec 3.2: 3 kez gorulmeyen oruntuden refleks dogmaz (Eser'in emniyeti)
BASLANGIC_GUC = 0.5  # tahmin: yeni refleks yarim guvenle baslar
SONME_ADIMI = 0.1  # tahmin: odulsuz her kullanimda guc bu kadar duser (M7 alisma)
ODUL_ADIMI = 0.1  # tahmin: odullu kullanimda guc bu kadar artar
GUC_TAVANI = 1.0
DUSME_ESIGI = 0.2  # tahmin: guc bunun altina inince refleks listeden duser
ODUL_ESIGI = 0.0  # dopamin_degisimi bundan buyukse kullanim odullu sayilir
VETO_TEPKILERI = ("dur", "sus")  # spec 3.2: veto yalniz bu yonde olabilir
# Basamak 1: elle yazilmis tek kural (tohum). Selamlasmaya selamla karsilik.
TOHUM = {"kalip": "merhaba", "tepki": "Merhaba!", "guc": BASLANGIC_GUC,
         "son_kullanim": None, "odul_sayaci": 0}
ALANLAR = set(TOHUM)


def _dosya():
    """Dosya yolu her cagrida kurulur: testler defter.DEFTER_KLASORU'nu gecici klasore baglar."""
    return defter.DEFTER_KLASORU / REFLEKS_DOSYA_ADI


def kalip_cikar(metin):
    """Oruntu = kucuk harf, noktalama silinmis, bosluklari teklenmis soru. Ayni soru ayni kalip."""
    temiz = re.sub(r"[^\w\s]", " ", metin.lower())
    return " ".join(temiz.split())


def _yukle():
    """Dosyayi okur. Yoksa tohumla baslar. Bozuksa ValueError yukseltir (cagiran loglar)."""
    yol = _dosya()
    if not yol.exists():
        return {"refleksler": [dict(TOHUM)], "sayaclar": {}}
    veri = json.loads(yol.read_text(encoding="utf-8"))
    if not isinstance(veri.get("refleksler"), list) or not isinstance(veri.get("sayaclar"), dict):
        raise ValueError("refleksler.json bicimi bozuk: refleksler liste, sayaclar sozluk olmali")
    for refleks in veri["refleksler"]:
        if not isinstance(refleks, dict) or not ALANLAR <= refleks.keys():
            raise ValueError(f"refleks alanlari eksik, gereken: {sorted(ALANLAR)}")
    return veri


def _kaydet(veri):
    yol = _dosya()
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")


def refleks_ara(durum):
    """Sozlesme: (oneri | None, guven). oneri {kalip, tepki}; hicbir zaman uygulanmaz, loglanir.
    Kalip sorunun icinde geciyorsa eslesir; birden fazla eslesirse en gucluusu secilir.
    Bozuk dosyada None doner, 'hata' loglar, akis durmaz (spec 3.2 Hata)."""
    basladi = time.perf_counter()
    try:
        veri = _yukle()
    except (ValueError, OSError, AttributeError) as hata:
        log.yaz(YUVA_ADI, "refleks_ara", _ms(basladi), "hata", {"hata": f"refleks dosyasi okunamadi: {hata}"})
        return None, 0.0
    soru = kalip_cikar(durum.get("soru", ""))
    adaylar = [r for r in veri["refleksler"] if r["kalip"] and r["kalip"] in soru]
    if not adaylar:
        log.yaz(YUVA_ADI, "refleks_ara", _ms(basladi), "ok", {"eslesen": None, "guven": 0.0, "golge": True})
        return None, 0.0
    secilen = max(adaylar, key=lambda r: r["guc"])
    detay = {"eslesen": secilen["kalip"], "guven": secilen["guc"], "golge": True}
    if secilen["tepki"].strip().lower() in VETO_TEPKILERI:
        detay["veto"] = secilen["tepki"]  # yalniz bayrak; akis durdurulmaz
    log.yaz(YUVA_ADI, "refleks_ara", _ms(basladi), "ok", detay)
    return {"kalip": secilen["kalip"], "tepki": secilen["tepki"]}, secilen["guc"]


def _gozlemle(veri, soru, cevap):
    """Basamak 2: oruntu sayaci artar; DOGMA_ESIGI'ne ulasinca refleks dogar, tepki son cevap."""
    kalip = kalip_cikar(soru)
    if not kalip or any(r["kalip"] == kalip for r in veri["refleksler"]):
        return None
    sayac = veri["sayaclar"].get(kalip, 0) + 1
    veri["sayaclar"][kalip] = sayac
    if sayac < DOGMA_ESIGI:
        return None
    veri["refleksler"].append({"kalip": kalip, "tepki": cevap, "guc": BASLANGIC_GUC,
                               "son_kullanim": None, "odul_sayaci": 0})
    return kalip


def _odullendir(veri, kalip, dopamin_degisimi):
    """Basamak 3: odulsuz kullanimda guc duser, DUSME_ESIGI altinda refleks listeden cikar (M7)."""
    for refleks in veri["refleksler"]:
        if refleks["kalip"] != kalip:
            continue
        refleks["son_kullanim"] = datetime.now().astimezone().isoformat(timespec="seconds")
        if dopamin_degisimi is not None and dopamin_degisimi > ODUL_ESIGI:
            refleks["odul_sayaci"] += 1
            refleks["guc"] = min(GUC_TAVANI, round(refleks["guc"] + ODUL_ADIMI, 3))
        else:
            refleks["guc"] = round(refleks["guc"] - SONME_ADIMI, 3)
    for refleks in veri["refleksler"]:
        if refleks["guc"] < DUSME_ESIGI:
            veri["sayaclar"][refleks["kalip"]] = 0  # yeniden dogmak icin yine 3 kez gorulmeli
    veri["refleksler"] = [r for r in veri["refleksler"] if r["guc"] >= DUSME_ESIGI]


def tur_sonu(soru, cevap, oneri, dopamin_degisimi):
    """Tur bitince: oneri varsa odul/sonme, sonra oruntu sayimi. Hata akisi durdurmaz, loglanir."""
    basladi = time.perf_counter()
    try:
        veri = _yukle()
        if oneri is not None:
            _odullendir(veri, oneri["kalip"], dopamin_degisimi)
        dogan = _gozlemle(veri, soru, cevap)
        _kaydet(veri)
    except (ValueError, OSError, AttributeError, KeyError, TypeError) as hata:
        log.yaz(YUVA_ADI, "tur_sonu", _ms(basladi), "hata", {"hata": f"refleks guncellenemedi: {hata}"})
        return
    log.yaz(YUVA_ADI, "tur_sonu", _ms(basladi), "ok", {"dogan": dogan, "refleks_sayisi": len(veri["refleksler"])})


def _ms(basladi):
    return int((time.perf_counter() - basladi) * 1000)
