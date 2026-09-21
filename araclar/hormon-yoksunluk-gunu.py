"""K19'un bedelini sayiyla gosterir: susan Minik (kimseyle konusmuyor, uretmiyor) ile konusan
Minik (gunluk sosyal + uretim olayi alan) ayni sayida gunde karsilastirilir.
Cagiran: elle, `python araclar/hormon-yoksunluk-gunu.py`."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from yuvalar.hormonlar import HORMONLAR, Hormonlar

GUN_SAYISI = 30
ADIM_PER_GUN = 20  # gun icinde sonumlemenin isleyecegi bos adim sayisi


def gunleri_kos():
    """Iki bagimsiz Hormonlar orneğini ayni sayida gun boyunca calistirir, ikisini de dondurur."""
    konusan = Hormonlar()
    susan = Hormonlar()
    for _ in range(GUN_SAYISI):
        _gunu_isle(konusan, konusuyor=True)
        _gunu_isle(susan, konusuyor=False)
    return konusan.oku(), susan.oku()


def _gunu_isle(hormonlar, konusuyor):
    """Bir gunluk adimi gecirir: once zaman gecer (sonumleme), sonra gunun sonucu islenir.
    konusuyor=True ise normal sosyal/uretim gunu, degilse K19'un iki yoksunluk olayi."""
    for _ in range(ADIM_PER_GUN):
        hormonlar.guncelle()
    if konusuyor:
        hormonlar.guncelle("iyi_davranis")
        hormonlar.guncelle("yolunda")
    else:
        hormonlar.guncelle("kimseyle_konusulmadi")
        hormonlar.guncelle("hicbir_sey_uretilmedi")


def _raporu_bas(konusan, susan):
    """Yedi hormonu yan yana basar, konusan-susan farkini gosterir."""
    print(f"{GUN_SAYISI} gun sonra:\n")
    print(f"{'hormon':<14}{'konusan':>10}{'susan':>10}{'fark':>10}  dinlenme")
    print("-" * 52)
    for ad in konusan:
        fark = konusan[ad] - susan[ad]
        print(f"{ad:<14}{konusan[ad]:>10.1f}{susan[ad]:>10.1f}{fark:>10.1f}  {HORMONLAR[ad].dinlenme:.0f}")


if __name__ == "__main__":
    konusan_deger, susan_deger = gunleri_kos()
    _raporu_bas(konusan_deger, susan_deger)
