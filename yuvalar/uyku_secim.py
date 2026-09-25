"""Uyku'nun secim kurallari: oncelik, yakalama penceresi etiketi, SM-2 adimi, prova puani, kosinus.
Hepsi saf fonksiyon (dosya, ag, sqlite yok). Cagiran: yuvalar/uyku.py."""

import math
from datetime import date, datetime, timedelta

from ortak.ayar import (
    SM2_BASARILI_KALITE, SM2_BASLANGIC_EF, SM2_EN_IYI_KALITE, SM2_EN_KUCUK_EF,
    SM2_IKINCI_ARALIK_GUN, SM2_ILK_ARALIK_GUN, UYKU_HATIRLAMA_ORTUSME,
    UYKU_VARSAYILAN_YAKINLIK, UYKU_YAKALAMA_PENCERESI_DK, UYKU_YUKSEK_ONCELIK_ESIGI,
)

ETIKET_ONCELIKLI = "oncelikli"
ETIKET_YAKALANDI = "yakalandi"
ETIKET_SIRADAN = "siradan"
SANIYE_DAKIKA = 60


def oncelik(kayit):
    """oncelik = |dopamin_degisimi| * yakinlik_carpani (spec 2.4 adim 2)."""
    dopamin = abs(kayit.get("dopamin_degisimi", 0.0))
    return dopamin * kayit.get("yakinlik_carpani", UYKU_VARSAYILAN_YAKINLIK)


def etiketle(kayitlar):
    """Her kayda oncelik ve etiket verir. Yuksek oncelikli kaydin +-pencere dakikasindaki
    siradan kayitlar `yakalandi` olur (sinaptik etiketleme, spec 2.4 adim 3)."""
    oncelikler = [oncelik(k) for k in kayitlar]
    zamanlar = [datetime.fromisoformat(k["zaman"]) for k in kayitlar]
    yuksekler = [z for z, o in zip(zamanlar, oncelikler) if o >= UYKU_YUKSEK_ONCELIK_ESIGI]
    pencere_sn = UYKU_YAKALAMA_PENCERESI_DK * SANIYE_DAKIKA
    sonuc = []
    for kayit, puan, zaman in zip(kayitlar, oncelikler, zamanlar):
        if puan >= UYKU_YUKSEK_ONCELIK_ESIGI:
            etiket = ETIKET_ONCELIKLI
        elif any(abs((zaman - y).total_seconds()) <= pencere_sn for y in yuksekler):
            etiket = ETIKET_YAKALANDI
        else:
            etiket = ETIKET_SIRADAN
        sonuc.append({**kayit, "oncelik": puan, "etiket": etiket})
    return sonuc


def sm2_adimi(ani, kalite, tarih):
    """Tek gozden gecirme: yeni tekrar, ef, sonraki_gun ve ust_uste_basarisiz dondurur.
    Sayilar deneyler/aralikli-tekrar-olc.py'deki olcumle ayni kural."""
    fark = SM2_EN_IYI_KALITE - kalite
    ef = max(SM2_EN_KUCUK_EF, ani["ef"] + (0.1 - fark * (0.08 + fark * 0.02)))
    if kalite < SM2_BASARILI_KALITE:
        tekrar, aralik, basarisiz = 0, SM2_ILK_ARALIK_GUN, ani["ust_uste_basarisiz"] + 1
    else:
        tekrar, basarisiz = ani["tekrar"] + 1, 0
        aralik = _aralik(tekrar, ef)
    sonraki = date.fromisoformat(tarih) + timedelta(days=aralik)
    return {"id": ani["id"], "tekrar": tekrar, "ef": ef, "sonraki_gun": sonraki.isoformat(),
            "ust_uste_basarisiz": basarisiz}


def _aralik(tekrar, ef):
    """SM-2 aralik merdiveni: 1 gun, 6 gun, sonra her seferinde ef ile carpilir."""
    if tekrar <= 1:
        return SM2_ILK_ARALIK_GUN
    aralik = SM2_IKINCI_ARALIK_GUN
    for _ in range(tekrar - 2):
        aralik = int(round(aralik * ef))
    return aralik


def yeni_sm2_alanlari(tarih):
    """Ilk kez islenen aninin SM-2 baslangici: yarin gozden gecirilir."""
    sonraki = date.fromisoformat(tarih) + timedelta(days=SM2_ILK_ARALIK_GUN)
    return {"tekrar": 0, "ef": SM2_BASLANGIC_EF, "sonraki_gun": sonraki.isoformat(),
            "ust_uste_basarisiz": 0}


def hatirladi_mi(eski_cevap, yeni_cevap):
    """Eski cevabin kelimelerinin yeterli orani yeni cevapta varsa True (kaba prova puani)."""
    eski = set(eski_cevap.lower().split())
    if not eski:
        return True
    ortak = eski & set(yeni_cevap.lower().split())
    return len(ortak) / len(eski) >= UYKU_HATIRLAMA_ORTUSME


def en_yakin(vektor, adaylar, k):
    """Kaba kuvvet kosinus: (id, soru, vektor) listesinden en benzer k tanesini (skor, soru) verir."""
    skorlu = [(_kosinus(vektor, v), soru) for _, soru, v in adaylar]
    return sorted(skorlu, reverse=True)[:k]


def _kosinus(a, b):
    """Iki vektorun kosinus benzerligi; sifir vektorde 0."""
    boy = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return 0.0 if boy == 0 else sum(x * y for x, y in zip(a, b)) / boy
