"""f3-g perde kaldirma: cevap eslestirme, yorgunluk deseni ve nesnel tablo testleri.
Cagiran: `python -m unittest discover -s tests`. Betik adi tire icerdigi icin importlib ile yuklenir."""

import importlib.util
import unittest
from pathlib import Path

_YOL = Path(__file__).resolve().parent.parent / "deneyler" / "f3g-perde-kaldir.py"
_OZ = importlib.util.spec_from_file_location("f3g_perde", _YOL)
perde = importlib.util.module_from_spec(_OZ)
_OZ.loader.exec_module(perde)


def _satir(mod, cevap, genel=2):
    return {"mod": mod, "cevap": cevap, "token": 100, "think_token": 50, "kesik": False, "genel": genel}


class TestF3gPerde(unittest.TestCase):

    def test_cevaplari_ekle_hata_kaydini_atlar(self):
        anahtar = {"AB12": {"soru_id": "T1", "mod": "yorgun", "tohum": 1}}
        kayitlar = [{"soru_id": "T1", "mod": "yorgun", "tohum": 1, "cevap": "tamam", "think_token": 7},
                    {"soru_id": "T1", "mod": "yorgun", "tohum": 2, "hata": "zaman asimi"}]
        sonuc = perde.cevaplari_ekle(anahtar, kayitlar)
        self.assertEqual(sonuc["AB12"]["cevap"], "tamam")
        self.assertEqual(sonuc["AB12"]["think_token"], 7)

    def test_cevaplari_ekle_eksik_kayit_hata(self):
        with self.assertRaises(ValueError):
            perde.cevaplari_ekle({"A": {"soru_id": "T1", "mod": "yorgun", "tohum": 1}}, [])

    def test_yorgunluk_deseni(self):
        self.assertTrue(perde.YORGUNLUK_DESENI.search("Biraz Yorgunum ama olur"))
        self.assertTrue(perde.YORGUNLUK_DESENI.search("uykum var"))
        self.assertFalse(perde.YORGUNLUK_DESENI.search("Harika bir gun"))

    def test_nesnel_tablo_orani(self):
        satirlar = [_satir("uyanik", "selam"), _satir("yorgun", "uykum var"), _satir("yorgun", "tamam")]
        metin = perde.bolum_nesnel(satirlar, "deneme")
        self.assertIn("| yorgun | 2 | 100.0 | 50.0 | 0 (0.0%) | 1 (50.0%) |", metin)


if __name__ == "__main__":
    unittest.main()
