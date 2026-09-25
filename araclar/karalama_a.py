"""Finalist A oyuncagi (gradyanli seyrek): morfem+hash gomme -> hizli/yavas iz -> ogrenilmis agac yaprak uzmani
-> cikis basi -> SSE duzeltmesi. Yalniz forward, egitim yok. Cagiran: tests/test_karalama.py, `python araclar/karalama_a.py`.
"""

import numpy as np

from mimari_karalama import TOHUM, olc

SOZLUK = 512
TOKEN = 2000
GENISLIK = 64
EK_SAYISI = 8  # oyuncak morfoloji: id = kok * EK_SAYISI + ek
HASH_SATIR = 1024
HASH_K = 3  # Bloom gomme: her token k hash satirinin toplami
HASH_CARPAN = (2654435761, 40503, 2246822519)
AGAC_DERINLIK = 6  # 64 yaprak, token basina bir yaprak okunur
HIZLI_UNUT = 0.5  # hizli iz: ek ve sozcuk olcegi
YAVAS_UNUT = 0.95  # yavas iz: cumle olcegi (F3-080); ogrenilmis matris yok, tasiyici degil
YAVAS_ADIM = 8  # yavas iz yalniz her 8 tokende guncellenir
SSE_KUTU = 33
SSE_BAGLAM = 64
BAYT = 4  # float32


def agirliklar():
    rng = np.random.default_rng(TOHUM)
    yaprak_sayisi = 2 ** AGAC_DERINLIK
    return {
        "kok": rng.standard_normal((SOZLUK // EK_SAYISI, GENISLIK)).astype(np.float32),
        "ek": rng.standard_normal((EK_SAYISI, GENISLIK)).astype(np.float32),
        "hash": rng.standard_normal((HASH_SATIR, GENISLIK)).astype(np.float32),
        "dugum": rng.standard_normal((yaprak_sayisi - 1, 3 * GENISLIK)).astype(np.float32),
        "yaprak": (rng.standard_normal((yaprak_sayisi, 3 * GENISLIK, GENISLIK)) * 0.1).astype(np.float32),
        "cikis": rng.standard_normal((SOZLUK, GENISLIK)).astype(np.float32),
        "sse": np.tile(np.linspace(0, 1, SSE_KUTU, dtype=np.float32), (SSE_BAGLAM, 1)),
    }


def gomme(w, ids):
    """Kok vektoru + ek vektorunun kaydirilmis (permutasyonlu) hali + k hash satiri (F3-053, F1-242)."""
    kok, ek = ids // EK_SAYISI, ids % EK_SAYISI
    x = w["kok"][kok] + np.roll(w["ek"][ek], 1, axis=1)
    for carpan in HASH_CARPAN[:HASH_K]:
        x = x + w["hash"][(ids * carpan) % HASH_SATIR]
    return x


def izler(x):
    """Token arasi durum: sabit katsayili iki iz. Parametresiz; yalniz gecmisin ortalamasini tasir."""
    hizli, yavas = np.zeros(GENISLIK, np.float32), np.zeros(GENISLIK, np.float32)
    hizli_iz, yavas_iz = np.empty_like(x), np.empty_like(x)
    for t in range(len(x)):
        hizli = HIZLI_UNUT * hizli + (1 - HIZLI_UNUT) * x[t]
        if t % YAVAS_ADIM == 0:
            yavas = YAVAS_UNUT * yavas + (1 - YAVAS_UNUT) * hizli
        hizli_iz[t], yavas_iz[t] = hizli, yavas
    return np.concatenate([x, hizli_iz, yavas_iz], axis=1)


def yaprak_bul(w, h):
    """Dengeli agac: her dugumde tek esik testi, derinlik kadar dugum okunur (F3-152, FFF)."""
    dugum = np.zeros(len(h), dtype=np.int64)
    for _ in range(AGAC_DERINLIK):
        sag = np.einsum("td,td->t", h, w["dugum"][dugum]) > 0
        dugum = 2 * dugum + 1 + sag
    return dugum - (2 ** AGAC_DERINLIK - 1)


def sse(w, olasilik, baglam):
    """Ikincil kestirim: en iyi tokenin olasiligi baglama gore 33 kutuda ara degerle duzeltilir (F3-019)."""
    konum = olasilik * (SSE_KUTU - 1)
    alt = np.minimum(konum.astype(np.int64), SSE_KUTU - 2)
    pay = konum - alt
    tablo = w["sse"][baglam % SSE_BAGLAM]
    return (1 - pay) * tablo[np.arange(len(alt)), alt] + pay * tablo[np.arange(len(alt)), alt + 1]


def dokunulan_bayt():
    """Token basina: kok+ek+k hash satiri, agac yolu, bir yaprak, butun cikis basi, iki SSE girisi."""
    satir = (2 + HASH_K) * GENISLIK
    agac = AGAC_DERINLIK * 3 * GENISLIK + 3 * GENISLIK * GENISLIK
    return (satir + agac + SOZLUK * GENISLIK + 2) * BAYT


def forward(ids):
    w = agirliklar()
    h = izler(gomme(w, ids))
    yaprak = yaprak_bul(w, h)
    y = np.tanh(np.einsum("td,tde->te", h, w["yaprak"][yaprak]))
    logit = y @ w["cikis"].T
    olasilik = np.exp(logit - logit.max(axis=1, keepdims=True))
    olasilik /= olasilik.sum(axis=1, keepdims=True)
    duzeltilmis = sse(w, olasilik.max(axis=1), ids)
    olasilik[np.arange(len(ids)), olasilik.argmax(axis=1)] = duzeltilmis
    toplam = sum(dizi.size for dizi in w.values()) * BAYT
    return olasilik, dokunulan_bayt(), toplam


if __name__ == "__main__":
    girdi = np.random.default_rng(TOHUM).integers(0, SOZLUK, TOKEN)
    olc("A gradyanli seyrek", forward, girdi)
