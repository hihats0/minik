"""k23-1 olcum aracinin GPU'suz parcalarinin testi: soru okuma, anonimlestirme, ozet.
Cagiran: `python -m unittest discover -s tests`."""

import sys
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "deneyler"))

import k23_ortak as ortak  # noqa: E402


class TestK23Ortak(unittest.TestCase):
    def test_gercek_sinav_20_soru(self):
        sorular = ortak.sorulari_oku((KOK / "deneyler/turkce-testi.md").read_text(encoding="utf-8"))
        self.assertEqual([no for no, _ in sorular], list(range(1, 21)))
        self.assertTrue(sorular[0][1].startswith("Bugün hava"))
        self.assertIn("sıcak", sorular[17][1])  # cok satirli soru birlesti
        self.assertNotIn("Beklenen", sorular[17][1])

    def test_anonim_metinde_model_adi_yok_anahtar_tam(self):
        bolumler = {"A": {1: {"soru": "s1", "cevaplar": {"trendyol": "x", "gemma": "y"}}},
                    "B": {1: {"soru": "s2", "cevaplar": {"trendyol": "z", "gemma": "w"}}}}
        metin, anahtar = ortak.anonimlestir(bolumler, 7)
        self.assertNotIn("trendyol", metin)
        self.assertNotIn("gemma", metin)
        self.assertEqual(len(anahtar), 4)
        for kimlik in anahtar:
            self.assertIn(kimlik, metin)

    def test_anonim_ayni_tohum_ayni_sonuc(self):
        bolumler = {"A": {1: {"soru": "s", "cevaplar": {"a": "1", "b": "2", "c": "3"}}}}
        self.assertEqual(ortak.anonimlestir(bolumler, 1), ortak.anonimlestir(bolumler, 1))

    def test_ozetle(self):
        self.assertEqual(ortak.ozetle([1, 3, 2]), {"ortanca": 2, "en_az": 1, "en_cok": 3, "ortalama": 2.0})


if __name__ == "__main__":
    unittest.main()
