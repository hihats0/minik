"""ortak/kaynak_olc.py sozlesme testi: is saniyesini 0-1 siddete dogru cevirdigini dogrular.
Cagiran: `python -m unittest discover -s tests`."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ortak import kaynak_olc

TAVAN_SN = 4.0  # testte kullanilan tavan; gercek deger ortak/ayar.py'de (MELATONIN_IS_TAVAN_SN)


class TestKaynakOlc(unittest.TestCase):

    def test_is_yoksa_siddet_sifir(self):
        self.assertEqual(kaynak_olc.siddet(0.0, TAVAN_SN), kaynak_olc.EN_AZ_SIDDET)

    def test_siddet_orantili(self):
        """Tavanin yarisi kadar is yarim siddet verir."""
        self.assertAlmostEqual(kaynak_olc.siddet(TAVAN_SN / 2, TAVAN_SN), 0.5)

    def test_siddet_tavani_asmaz(self):
        self.assertEqual(kaynak_olc.siddet(TAVAN_SN * 10, TAVAN_SN), kaynak_olc.EN_COK_SIDDET)

    def test_siddet_negatif_olmaz(self):
        self.assertEqual(kaynak_olc.siddet(-1.0, TAVAN_SN), kaynak_olc.EN_AZ_SIDDET)


if __name__ == "__main__":
    unittest.main()
