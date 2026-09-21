"""100 adimlik sahte bir gunu simule eder ve yedi hormonu metin tablo olarak basar. K10: bos
adimlarda artik gercekten CPU harcanir, melatonin bu olcume gore beslenir (elle 1,0 verilmez).
Cagiran: elle, `python araclar/hormon-gunu.py`. "Hormon durumu gorunur olacak" isteginin ilk hali."""

import hashlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ortak import kaynak_olc
from ortak.ayar import MELATONIN_CPU_TAVAN_SN
from yuvalar.hormonlar import EN_COK, HORMONLAR, Hormonlar

ADIM_SAYISI = 100
BASMA_ARALIGI = 5  # kac adimda bir satir basilacak
CUBUK_GENISLIGI = 20  # 0-100 araligi kac karakterle cizilecek
CUBUK_ISARETI = "#"

# Bos adimlarda Minik'in gercekte ne kadar CPU harcadigini taklit eder: kucuk model cagrisi
# hafif, Kafa cagrisi agir. Oran MELATONIN_CPU_TAVAN_SN'e gore, "agir" tavani asip 1,0'da kirpilir
# (gercek bir Kafa cagrisi da tek adimda tavani doldurabilir). TAHMIN: gercek dagilim olculmedi,
# f3-b'de gercek cagri sureleriyle degisecek.
IS_AGIRLIGI = {"hafif": 0.2, "orta": 0.5, "agir": 1.2}
IS_DONGUSU = ["hafif", "hafif", "orta", "hafif", "agir"]

# Sahte gun: (adim, olay, siddet). Arada bos adimlar var, orada sadece sonumleme calisir.
GUN_PLANI = [
    (3, "ogrenilebilir_sasirma", 1.0),  # sabah: anlamadigi ama anlasilabilir bir sey gordu
    (8, "belirsizlik", 0.8),
    (12, "ogrendi", 1.0),  # merak doydu, indi
    (16, "odul", 0.9),
    (20, "iyi_davranis", 1.0),  # biri iyi davrandi, oksitosin
    (25, "tanidik", 1.0),
    (30, "ceza", 1.0),  # Claude azarladi, kortizol tavana
    (34, "ogrenilebilir_sasirma", 0.7),
    (40, "yolunda", 1.0),
    (48, "iyi_sey", 1.0),  # kortizol ancak burada iner
    (55, "ogrendi", 0.8),
    (60, "belirsizlik", 1.0),
    (66, "odul", 0.5),
    (72, "ceza", 0.6),
    (78, "iyi_davranis", 0.9),
    (84, "iyi_sey", 0.8),
    (90, "ogrenilebilir_sasirma", 1.0),
    (95, "uyku", 1.0),  # gece: yorgunluk ancak burada siliniyor
]


def gunu_kos():
    """Plani adim adim isler, basma araliginda tablo satiri dokturur."""
    hormonlar = Hormonlar()
    plan = dict((adim, (olay, siddet)) for adim, olay, siddet in GUN_PLANI)
    _basligi_bas()
    for adim in range(1, ADIM_SAYISI + 1):
        # Planda olay yoksa Minik calismaya devam ediyor: bos adim yorgunluk biriktirir, ama
        # artik elle degil, GERCEKTEN harcanan CPU saniyesiyle (K10). Adim basina TEK guncelle
        # cagrilir, yoksa sonumleme iki kez isler ve gun kisalir.
        if adim in plan:
            olay, siddet = plan[adim]
        else:
            olay, siddet = "calisma", _bos_adimin_siddeti(adim)
        degerler = hormonlar.guncelle(olay, siddet)
        if adim % BASMA_ARALIGI == 0 or adim in plan:
            _satiri_bas(adim, olay, degerler)
    _cubuklari_bas(hormonlar.oku())


def _bos_adimin_siddeti(adim):
    """Bos adimda gercekten kisa bir CPU isi yapar (kucuk/Kafa cagrisini taklit eder), harcanan
    sureyi olcup siddete cevirir. kaynak_olc disinda hicbir yerde process_time cagrilmaz."""
    agirlik = IS_DONGUSU[adim % len(IS_DONGUSU)]
    hedef_sn = IS_AGIRLIGI[agirlik] * MELATONIN_CPU_TAVAN_SN
    baslangic = kaynak_olc.basla()
    _cpu_isi_yap(hedef_sn)
    return kaynak_olc.siddet(baslangic, MELATONIN_CPU_TAVAN_SN)


def _cpu_isi_yap(hedef_sn):
    """Gercekten CPU harcar (sleep degil): hedef_sn'e ulasana dek hash hesaplar."""
    baslangic = time.process_time()
    veri = b"minik"
    while time.process_time() - baslangic < hedef_sn:
        veri = hashlib.sha256(veri).digest()


def _basligi_bas():
    """Tablonun ust satirini basar."""
    basliklar = "".join(f"{ad[:6]:>7}" for ad in HORMONLAR)
    print(f"{'adim':>5} {'olay':<24}{basliklar}")
    print("-" * (5 + 1 + 24 + 7 * len(HORMONLAR)))


def _satiri_bas(adim, olay, degerler):
    """Tek bir adimin satirini basar."""
    sayilar = "".join(f"{degerler[ad]:>7.1f}" for ad in HORMONLAR)
    print(f"{adim:>5} {olay:<24}{sayilar}")


def _cubuklari_bas(degerler):
    """Gun sonundaki hormon durumunu cubuk olarak gosterir."""
    print("\nGun sonu hormon durumu:")
    for ad in HORMONLAR:
        deger = degerler[ad]
        uzunluk = int(deger / EN_COK * CUBUK_GENISLIGI)
        cubuk = CUBUK_ISARETI * uzunluk
        print(f"  {ad:<14}{deger:>6.1f}  {cubuk:<{CUBUK_GENISLIGI}}| dinlenme {HORMONLAR[ad].dinlenme:.0f}")


if __name__ == "__main__":
    gunu_kos()
