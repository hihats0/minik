"""f3-c2 analiz betiginin (isaret cevirme p, eslesmis fark, birlestirme) elle kurulmus ornek testleri.
Cagiran: `python -m unittest discover -s tests`. Betik adi tire icerdigi icin importlib ile yuklenir."""

import importlib.util
import unittest
from fractions import Fraction
from pathlib import Path

BETIK = Path(__file__).resolve().parent.parent / "araclar" / "f3c2-perde-kaldir.py"
OZELLIK = importlib.util.spec_from_file_location("f3c2_perde_kaldir", BETIK)
analiz = importlib.util.module_from_spec(OZELLIK)
OZELLIK.loader.exec_module(analiz)

UYANIK = analiz.MOD_UYANIK
YORGUN = analiz.MOD_YORGUN


def satir(soru_id, mod, genel):
    return {"soru_id": soru_id, "kategori": "x", "mod": mod, "genel": genel, "uzunluk": genel}


class TestIsaretCevirme(unittest.TestCase):

    def test_uc_pozitif_fark_p_dortte_bir(self):
        """[1,1,1]: gozlenen |3|; 8 kombinasyondan yalniz +++ ve --- 3'e ulasir, p = 2/8."""
        self.assertEqual(analiz.isaret_cevirme_p([Fraction(1)] * 3), Fraction(1, 4))

    def test_simetrik_ornekte_p_bir(self):
        """[1,-1]: gozlenen 0, her kombinasyon >= 0 oldugu icin p = 1."""
        self.assertEqual(analiz.isaret_cevirme_p([Fraction(1), Fraction(-1)]), Fraction(1))

    def test_sifir_fark_kombinasyona_dahil(self):
        """[2,1,0]: gozlenen 3; ilk ikisinden yalniz ++ ve -- 3'e ulasir, sifirun 2 isareti ile 4/8."""
        self.assertEqual(analiz.isaret_cevirme_p([Fraction(2), Fraction(1), Fraction(0)]), Fraction(1, 2))


class TestEslesmisFark(unittest.TestCase):

    def test_soru_basina_uc_tekrar_ortalamasi(self):
        """S1: uyanik [2,2,1] -> 5/3, yorgun [1,1,1] -> 1, fark 2/3. S2: uyanik [0,0,0], yorgun [2,1,0] -> -1."""
        satirlar = [satir("S1", UYANIK, g) for g in (2, 2, 1)] + [satir("S1", YORGUN, 1)] * 3
        satirlar += [satir("S2", UYANIK, 0)] * 3 + [satir("S2", YORGUN, g) for g in (2, 1, 0)]
        sonuc = analiz.soru_farklari(satirlar, "genel")
        self.assertEqual(sonuc["S1"], (Fraction(5, 3), Fraction(1), Fraction(2, 3)))
        self.assertEqual(sonuc["S2"], (Fraction(0), Fraction(1), Fraction(-1)))


class TestBirlestir(unittest.TestCase):

    def test_id_eslesince_perde_ve_puan_birlesir(self):
        sonuc = analiz.birlestir([{"id": "A", "genel": 2}], {"A": {"mod": UYANIK}})
        self.assertEqual(sonuc, [{"mod": UYANIK, "id": "A", "genel": 2}])

    def test_perdede_olmayan_id_hata_verir(self):
        with self.assertRaises(ValueError):
            analiz.birlestir([{"id": "A", "genel": 2}], {"B": {"mod": UYANIK}})


if __name__ == "__main__":
    unittest.main()
