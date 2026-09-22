"""f3-c3 kor puanlama analizinin istatistik parcalari: isaret testi, permutasyon p, Holm, agirlikli kappa.
Cagiran: araclar/f3c3-perde-kaldir.py; tests/test_f3c3_istatistik.py. Sadece standart kutuphane.
"""

import random
from fractions import Fraction
from math import comb

PERMUTASYON_TUR = 20000
PERMUTASYON_TOHUM = 20260923
OLCEK = (0, 1, 2)


def isaret_testi_p(farklar):
    """Cift yonlu kesin isaret (binom) testi; sifir farklar atilir. Donus: (arti, eksi, p)."""
    arti = sum(1 for f in farklar if f > 0)
    eksi = sum(1 for f in farklar if f < 0)
    n = arti + eksi
    if n == 0:
        return arti, eksi, 1.0
    kuyruk = sum(comb(n, k) for k in range(min(arti, eksi) + 1))
    return arti, eksi, min(1.0, 2 * kuyruk / 2 ** n)


def permutasyon_p(farklar, tur=PERMUTASYON_TUR, tohum=PERMUTASYON_TOHUM):
    """Isaret cevirme permutasyonu, cift yonlu. 30 soruda 2^30 kombinasyon cok oldugu icin
    rastgele ornekleme; +1 duzeltmesi p'nin sifir cikmasini engeller (Phipson-Smyth)."""
    uretec = random.Random(tohum)
    degerler = [float(f) for f in farklar]
    gozlenen = abs(sum(degerler))
    say = 0
    for _ in range(tur):
        toplam = sum(d if uretec.random() < 0.5 else -d for d in degerler)
        if abs(toplam) >= gozlenen - 1e-12:
            say += 1
    return (say + 1) / (tur + 1)


def holm(p_sozluk):
    """Holm-Bonferroni duzeltmesi. {ad: p} -> {ad: duzeltilmis p}, monoton artan."""
    sirali = sorted(p_sozluk.items(), key=lambda kv: kv[1])
    m = len(sirali)
    sonuc, en_buyuk = {}, 0.0
    for sira, (ad, p) in enumerate(sirali):
        en_buyuk = max(en_buyuk, min(1.0, (m - sira) * p))
        sonuc[ad] = en_buyuk
    return sonuc


def tam_uyum(a, b):
    """Iki puan listesinin birebir ayni oldugu oran."""
    return Fraction(sum(1 for x, y in zip(a, b) if x == y), len(a))


def agirlikli_kappa(a, b, olcek=OLCEK):
    """Kuadratik agirlikli Cohen kappa: 1 - sum(w*gozlenen) / sum(w*beklenen), w=(i-j)^2."""
    n = len(a)
    gozlenen = sum((x - y) ** 2 for x, y in zip(a, b))
    say_a = {k: a.count(k) for k in olcek}
    say_b = {k: b.count(k) for k in olcek}
    beklenen = sum(say_a[i] * say_b[j] * (i - j) ** 2 for i in olcek for j in olcek) / n
    if beklenen == 0:
        return 1.0
    return 1 - gozlenen / beklenen
