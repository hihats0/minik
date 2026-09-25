"""f3-c3 perde kaldirma: istatistik modulu (isaret, permutasyon, Holm, kappa) ve kesik isaretleme testleri.
Cagiran: `python -m unittest discover -s tests`. Betik adi tire icerdigi icin importlib ile yuklenir."""

import importlib.util
import sys
import unittest
from pathlib import Path

ARACLAR = Path(__file__).resolve().parent.parent / "deneyler"
sys.path.insert(0, str(ARACLAR))
import f3c3_istatistik as ist  # noqa: E402

_OZ = importlib.util.spec_from_file_location("f3c3_perde", ARACLAR / "f3c3-perde-kaldir.py")
perde = importlib.util.module_from_spec(_OZ)
_OZ.loader.exec_module(perde)


class TestIstatistik(unittest.TestCase):

    def test_isaret_hepsi_arti(self):
        """5 arti, 0 eksi: p = 2 * (1/32) = 1/16; sifir fark atilir."""
        self.assertEqual(ist.isaret_testi_p([1, 1, 1, 1, 1, 0]), (5, 0, 2 / 32))

    def test_permutasyon_simetrik_bir(self):
        self.assertAlmostEqual(ist.permutasyon_p([1, -1], tur=200), 1.0)

    def test_permutasyon_guclu_etki_kucuk(self):
        self.assertLess(ist.permutasyon_p([1] * 20, tur=2000), 0.01)

    def test_holm(self):
        """p sirali 0.01,0.02,0.04 ve m=3: 0.03, 0.04, 0.04 (monoton)."""
        sonuc = ist.holm({"a": 0.04, "b": 0.01, "c": 0.02})
        self.assertAlmostEqual(sonuc["b"], 0.03)
        self.assertAlmostEqual(sonuc["c"], 0.04)
        self.assertAlmostEqual(sonuc["a"], 0.04)

    def test_kappa_tam_uyum_bir(self):
        self.assertEqual(ist.agirlikli_kappa([0, 1, 2, 2], [0, 1, 2, 2]), 1.0)

    def test_kappa_elle(self):
        """a=[0,2], b=[2,0]: gozlenen 8, beklenen (1*1*4+1*1*4)/2=4, kappa=1-2=-1."""
        self.assertEqual(ist.agirlikli_kappa([0, 2], [2, 0]), -1.0)

    def test_tam_uyum(self):
        self.assertEqual(float(ist.tam_uyum([0, 1, 2, 2], [0, 1, 1, 2])), 0.75)


class TestKesik(unittest.TestCase):

    def test_tavana_vuran_kesik(self):
        anahtar = {"A": {"token": 224, "ayarlar": {"max_tokens": 224}},
                   "B": {"token": 100, "ayarlar": {"max_tokens": 224}}}
        sonuc = perde.kesik_isaretle(anahtar)
        self.assertTrue(sonuc["A"]["kesik"])
        self.assertFalse(sonuc["B"]["kesik"])


if __name__ == "__main__":
    unittest.main()
