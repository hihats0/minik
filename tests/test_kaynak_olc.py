"""ortak/kaynak_olc.py sozlesme testi: gercek CPU isini olcup 0-1 siddete cevirdigini dogrular.
Cagiran: `python -m unittest discover -s tests`."""

import hashlib
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ortak import kaynak_olc

TAVAN_SN = 0.05  # testte kullanilan kucuk tavan; gercek deger ortak/ayar.py'de (MELATONIN_CPU_TAVAN_SN)
BOS_IS_UST_SINIRI = 0.1  # is yapilmadan gecen siddet bu kadarin altinda kalmali


class TestKaynakOlc(unittest.TestCase):

    def test_is_yapilmazsa_siddet_sifira_yakin(self):
        baslangic = kaynak_olc.basla()
        self.assertLess(kaynak_olc.siddet(baslangic, TAVAN_SN), BOS_IS_UST_SINIRI)

    def test_gercek_cpu_isi_siddeti_yukseltir(self):
        baslangic = kaynak_olc.basla()
        _cpu_yak(TAVAN_SN * 2)  # tavanin iki kati kadar gercek CPU isi yap
        self.assertGreater(kaynak_olc.siddet(baslangic, TAVAN_SN), 0.5)

    def test_siddet_tavani_asmaz(self):
        baslangic = kaynak_olc.basla()
        _cpu_yak(TAVAN_SN * 10)  # tavanin cok uzerinde is
        self.assertLessEqual(kaynak_olc.siddet(baslangic, TAVAN_SN), kaynak_olc.EN_COK_SIDDET)

    def test_siddet_negatif_olmaz(self):
        # baslangic ileri bir zaman olsa bile (saat kaymasi gibi) siddet negatife dusmemeli
        ileri_baslangic = kaynak_olc.basla() + 10.0
        self.assertGreaterEqual(kaynak_olc.siddet(ileri_baslangic, TAVAN_SN), kaynak_olc.EN_AZ_SIDDET)

    def test_daha_uzun_is_daha_yuksek_siddet_verir(self):
        """Olcum orantili olmali: iki kati sure iki kati (tavana kadar) siddet vermeli."""
        b1 = kaynak_olc.basla()
        _cpu_yak(TAVAN_SN * 0.3)
        kisa = kaynak_olc.siddet(b1, TAVAN_SN)
        b2 = kaynak_olc.basla()
        _cpu_yak(TAVAN_SN * 0.9)
        uzun = kaynak_olc.siddet(b2, TAVAN_SN)
        self.assertGreater(uzun, kisa)


def _cpu_yak(hedef_sn):
    """Gercekten CPU harcayan kucuk bir is: hedef_sn kadar surene dek hash hesaplar. Sleep degil:
    sleep CPU harcamaz, time.process_time() onu gormez (olcumun tam da amaci bu ayrimi yapmak)."""
    baslangic = time.process_time()
    veri = b"minik"
    while time.process_time() - baslangic < hedef_sn:
        veri = hashlib.sha256(veri).digest()


if __name__ == "__main__":
    unittest.main()
