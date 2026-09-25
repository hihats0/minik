"""Yol (a) olcumu: odul_kural.sinifla'yi odul-testi.json test setinde kosar, dogruluk, sure ve RAM olcer.
Cagiran: elle, `python deneyler/odul-olc-kural.py [sonuc-adi]`. Sunucu ya da model gerekmez.
"""

import sys
from pathlib import Path
import time

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # kok: ortak/, yuvalar/
from yuvalar.ton_kural import sinifla
from odul_ortak import metrik_hesapla, sonuc_yaz, sure_ozeti, veri_yukle

TEKRAR_PER_CUMLE = 200  # tek cumle mikrosaniyeler suruyor; ortalama icin cok kez tekrar edilir


def sure_olc(metin):
    """Bir cumleyi TEKRAR_PER_CUMLE kez siniflar, tek cagrinin ortalama suresini ms dondurur."""
    basla = time.perf_counter()
    for _ in range(TEKRAR_PER_CUMLE):
        sinifla(metin)
    return (time.perf_counter() - basla) * 1000 / TEKRAR_PER_CUMLE


def main():
    testler, _ = veri_yukle()
    ram_baslangic_mb = psutil.Process().memory_info().rss / 2**20
    tahminler = [sinifla(t["metin"]) for t in testler]
    sureler = [sure_olc(t["metin"]) for t in testler]
    ram_mb = psutil.Process().memory_info().peak_wset / 2**20
    ek = {"ram_zirve_mb": round(ram_mb, 1), "ram_bos_python_mb": round(ram_baslangic_mb, 1),
          "not": "RAM tum Python sureci; kuralin kendi payi bos yorumlayicinin ustundeki fark."}
    sonuc_yaz(sys.argv[1] if len(sys.argv) > 1 else "kural", metrik_hesapla(testler, tahminler), sure_ozeti(sureler), ek)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
