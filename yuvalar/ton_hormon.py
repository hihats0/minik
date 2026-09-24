"""Sohbet tonunu hormon olayina cevirir (spec 2.3 madde 11: gecikmeli, cevaptan sonra).
Cagiran: minik.py akisi (her basarili turdan sonra), testler."""

import time

from ortak import log
from yuvalar import ton

YUVA_ADI = "ton_hormon"
# Olay adlari yuvalar/hormonlar.py HORMONLAR tablosundaki gercek adlar.
# Siddetler TAHMIN: olculmedi; ovgu dopamin+oksitosin yukseltir, kortizolu yarim siddetle dusurur,
# sert yarim, hakaret tam ceza (kortizol). Gercek sohbet logu birikince ayarlanacak.
TON_OLAYLARI = {
    "ovgu": [("odul", 1.0), ("iyi_davranis", 1.0), ("iyi_sey", 0.5)],
    "sert": [("ceza", 0.5)],
    "hakaret": [("ceza", 1.0)],
    "notr": [],
}


def isle(metin, hormon_durumu, ton_oku=ton.ton_oku):
    """Tonu okur, tablodaki olaylari hormon_durumu'na uygular, loglar ve tonu dondurur."""
    basladi = time.perf_counter()
    okunan, kaynak = ton_oku(metin)
    olaylar = TON_OLAYLARI.get(okunan, [])
    for olay, siddet in olaylar:
        hormon_durumu.guncelle(olay, siddet)
    log.yaz(YUVA_ADI, "isle", int((time.perf_counter() - basladi) * 1000), "ok",
            {"ton": okunan, "kaynak": kaynak, "olaylar": [o for o, _ in olaylar]})
    return okunan
