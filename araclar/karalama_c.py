"""Finalist C oyuncagi (gradyansiz, en ucuz): blok kodlu seyrek hipervektor baglam (son 3 token, konuma gore
kaydirma) -> blok basina sayma tablosu -> toplam oy -> SSE. Hata kapili Winnow guncellemesi. Cagiran: tests/test_karalama.py.
"""

import numpy as np

from mimari_karalama import TOHUM, olc

SOZLUK = 512
TOKEN = 2000
BLOK = 16  # hipervektor 16 bloktan olusur, her blokta tek aktif konum (F3-044)
BLOK_BOY = 32
PENCERE = 3  # baglam: son 3 token; tasiyici durum yok, kayan pencere
TABLO_SATIR = 4096  # blok basina sayma tablosu satiri (hash kovasi)
UST_LISTE = 8  # her satir yalniz en sik 8 (token, sayi) ciftini tutar
HASH_CARPAN = 2654435761
WINNOW_ARTIS = 1.5  # F3-201: hata varsa dogru tokenin sayisi carpimsal artar
SSE_KUTU = 33
BAYT_SAYI = 1  # 8 bit sayac
BAYT_TOKEN = 2  # 16 bit token id


def token_kodu(ids):
    """Her token her blokta hash ile tek konum secer: (T, BLOK) tamsayi dizisi, bit vektoru acilmaz."""
    blok_no = np.arange(BLOK)
    return (ids[:, None] * HASH_CARPAN + blok_no * 97) % BLOK_BOY


def baglam_kodu(kod):
    """Baglama: onceki i. token blok icinde i kadar dairesel kaydirilir, kodlar toplanir (mod blok boyu)."""
    baglam = np.zeros_like(kod)
    for gecikme in range(1, PENCERE + 1):
        onceki = np.roll(kod, gecikme, axis=0)
        onceki[:gecikme] = 0
        baglam = baglam * BLOK_BOY + (onceki + gecikme) % BLOK_BOY
    return baglam % TABLO_SATIR


def tablolar():
    rng = np.random.default_rng(TOHUM)
    return {"token": rng.integers(0, SOZLUK, (BLOK, TABLO_SATIR, UST_LISTE)),
            "sayi": rng.integers(0, 256, (BLOK, TABLO_SATIR, UST_LISTE)).astype(np.float32),
            "sse": np.linspace(0, 1, SSE_KUTU, dtype=np.float32)}


def oyla(t, satir):
    """Her blok kendi tablosunda tek satir okur; 16 satirin (token, sayi) listeleri oy olarak toplanir."""
    adet = len(satir)
    oy = np.zeros((adet, SOZLUK), np.float32)
    for b in range(BLOK):
        np.add.at(oy, (np.arange(adet)[:, None], t["token"][b, satir[:, b]]), t["sayi"][b, satir[:, b]])
    return oy / oy.sum(axis=1, keepdims=True)


def sse(t, olasilik):
    konum = olasilik * (SSE_KUTU - 1)
    alt = np.minimum(konum.astype(np.int64), SSE_KUTU - 2)
    pay = konum - alt
    return (1 - pay) * t["sse"][alt] + pay * t["sse"][alt + 1]


def winnow(t, satir, tahmin, hedef):
    """Yalniz yanlis tahmin edilen tokende ve yalniz o tokenin okundugu satirlarda sayi carpimsal artar."""
    yanlis = np.flatnonzero(tahmin != hedef)
    for b in range(BLOK):
        eslesen = t["token"][b, satir[yanlis, b]] == hedef[yanlis, None]
        t["sayi"][b, satir[yanlis, b]] *= np.where(eslesen, WINNOW_ARTIS, 1.0)
    return len(yanlis) / len(hedef)


def dokunulan_bayt():
    return BLOK * UST_LISTE * (BAYT_SAYI + BAYT_TOKEN) + 2 * BAYT_SAYI


def forward(ids):
    t = tablolar()
    satir = baglam_kodu(token_kodu(ids))
    olasilik = oyla(t, satir)
    tahmin = olasilik.argmax(axis=1)
    olasilik[np.arange(len(ids)), tahmin] = sse(t, olasilik.max(axis=1))
    hata = winnow(t, satir[:-1], tahmin[:-1], ids[1:])
    print(f"  C: hata payi (guncellenen token) {hata:.3f}")
    toplam = t["token"].size * BAYT_TOKEN + t["sayi"].size * BAYT_SAYI + SSE_KUTU * BAYT_SAYI
    return olasilik, dokunulan_bayt(), toplam


if __name__ == "__main__":
    girdi = np.random.default_rng(TOHUM).integers(0, SOZLUK, TOKEN)
    olc("C gradyansiz hipervektor", forward, girdi)
