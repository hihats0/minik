"""Uc finalist oyuncaginin (karalama_a/b/c) forward testi: <10 sn, cikti sekli, dokunulan pay < 1.
Cagiran: `python -m unittest tests.test_karalama`.
"""

import sys
import unittest
from pathlib import Path

import numpy as np

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))

import karalama_a
import karalama_b
import karalama_c
from mimari_karalama import olc

SURE_SINIRI_SN = 10.0


class KaralamaTesti(unittest.TestCase):
    def kos(self, modul, ad):
        ids = np.random.default_rng(0).integers(0, modul.SOZLUK, modul.TOKEN)
        sonuc = olc(ad, modul.forward, ids)
        self.assertLess(sonuc["sure_sn"], SURE_SINIRI_SN)
        self.assertEqual(sonuc["cikti_sekli"], (modul.TOKEN, modul.SOZLUK))
        self.assertGreater(sonuc["dokunulan_pay"], 0)
        self.assertLess(sonuc["dokunulan_pay"], 1)

    def test_a(self):
        self.kos(karalama_a, "A")

    def test_b(self):
        self.kos(karalama_b, "B")

    def test_c(self):
        self.kos(karalama_c, "C")


if __name__ == "__main__":
    unittest.main()
