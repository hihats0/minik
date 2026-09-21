"""Hormon sayisi bir ac/kapa karari surdugunde kac kez mod degistirdigini olcer: tek esik vs cift esik.
Cagiran: elle, `python araclar/histerezis-olc.py`. Kaynak: Schmitt tetikleyici (kontrol kurami, histerezis)."""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from yuvalar.hormonlar import HORMONLAR, OLAYLAR, Hormonlar

ADIM_SAYISI = 300
TOHUM = 20260921  # sabit tohum: ayni koşu ayni sayiyi versin
TOHUMLAR = (20260921, 1, 2, 3, 4, 5, 6, 7)  # tek tohum kanit degil: ayni olcum sekiz kez kosar
OLAY_OLASILIKLARI = (0.15, 0.35, 0.60, 0.90)  # olay yogunlugu suplemesi
OLAY_OLASILIGI = 0.35  # bir adimda olay olma sansi; kalan adimlar "calisma"
BOS_ADIM_OLAYI = "calisma"
TEK_ESIK = 50.0
ALT_ESIK = 42.0  # cift esikte asagi gecis siniri
UST_ESIK = 58.0  # cift esikte yukari gecis siniri


def gunu_uret(tohum=TOHUM, olay_olasiligi=OLAY_OLASILIGI):
    """Sabit tohumla ADIM_SAYISI uzunlugunda (olay, siddet) listesi uretir."""
    rastgele = random.Random(tohum)
    olaylar = sorted(OLAYLAR)
    plan = []
    for _ in range(ADIM_SAYISI):
        if rastgele.random() < olay_olasiligi:
            plan.append((rastgele.choice(olaylar), round(rastgele.uniform(0.3, 1.0), 2)))
        else:
            plan.append((BOS_ADIM_OLAYI, 1.0))
    return plan


def izleri_topla(plan):
    """Plani bir kez kosturur ve her hormon icin adim adim deger listesi dondurur."""
    hormonlar = Hormonlar()
    iz = {ad: [] for ad in HORMONLAR}
    for olay, siddet in plan:
        degerler = hormonlar.guncelle(olay, siddet)
        for ad in HORMONLAR:
            iz[ad].append(degerler[ad])
    return iz


def tek_esikle_say(degerler):
    """Tek esikli karsilastirici: deger esigin ustundeyse mod acik. Kac kez mod degisti."""
    mod = degerler[0] >= TEK_ESIK
    degisim = 0
    for deger in degerler[1:]:
        yeni = deger >= TEK_ESIK
        if yeni != mod:
            degisim += 1
            mod = yeni
    return degisim


def cift_esikle_say(degerler):
    """Schmitt tetikleyici: acmak icin UST_ESIK, kapatmak icin ALT_ESIK gerekir."""
    mod = degerler[0] >= UST_ESIK
    degisim = 0
    for deger in degerler:
        yeni = mod
        if not mod and deger >= UST_ESIK:
            yeni = True
        elif mod and deger <= ALT_ESIK:
            yeni = False
        if yeni != mod:
            degisim += 1
            mod = yeni
    return degisim


def _tabloyu_bas(iz):
    """Hormon basina tek esik ve cift esik mod degisim sayilarini basar."""
    print(f"{ADIM_SAYISI} adim, tohum {TOHUM}, tek esik {TEK_ESIK:.0f}, "
          f"cift esik {ALT_ESIK:.0f}/{UST_ESIK:.0f}")
    print(f"{'hormon':<16}{'en az':>8}{'en cok':>8}{'tek esik':>10}{'cift esik':>11}")
    print("-" * 53)
    toplam_tek = toplam_cift = 0
    for ad, degerler in iz.items():
        tek = tek_esikle_say(degerler)
        cift = cift_esikle_say(degerler)
        toplam_tek += tek
        toplam_cift += cift
        print(f"{ad:<16}{min(degerler):>8.1f}{max(degerler):>8.1f}{tek:>10}{cift:>11}")
    print("-" * 53)
    print(f"{'TOPLAM':<16}{'':>8}{'':>8}{toplam_tek:>10}{toplam_cift:>11}")
    return toplam_tek, toplam_cift


def _bir_kosu(tohum, olasilik):
    """Tek bir tohum ve olay yogunlugu icin (tek esik, cift esik) toplam mod degisimi."""
    iz = izleri_topla(gunu_uret(tohum, olasilik))
    tek = sum(tek_esikle_say(d) for d in iz.values())
    cift = sum(cift_esikle_say(d) for d in iz.values())
    return tek, cift


def _supurmeyi_bas():
    """Olay yogunlugunu ve tohumu degistirerek sonucun tek koşuya bagli olmadigini gosterir."""
    print(f"\nSupurme: {len(TOHUMLAR)} tohum x {len(OLAY_OLASILIKLARI)} olay yogunlugu")
    print(f"{'olay olasiligi':<16}{'tek esik top.':>15}{'cift esik top.':>16}")
    for olasilik in OLAY_OLASILIKLARI:
        sonuclar = [_bir_kosu(t, olasilik) for t in TOHUMLAR]
        tek = sum(s[0] for s in sonuclar)
        cift = sum(s[1] for s in sonuclar)
        print(f"{olasilik:<16.2f}{tek:>15}{cift:>16}")


def olc():
    """Olcumu kosturur ve ozet satirini basar. Hata yutulmaz, yukselir."""
    iz = izleri_topla(gunu_uret())
    toplam_tek, toplam_cift = _tabloyu_bas(iz)
    kazanc = toplam_tek - toplam_cift
    print(f"\nCift esik {kazanc} gereksiz mod degisimini onledi "
          f"({toplam_tek} -> {toplam_cift}).")
    _supurmeyi_bas()


if __name__ == "__main__":
    olc()
