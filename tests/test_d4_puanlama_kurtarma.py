"""D4 puanlama duzeltmesi testi: kesilmis ogretmen JSON'u kurtarilir, kurtarilamayan cumle
'puanlanamadi' sayilir ve kosu dusmez. Cagiran: `python -m unittest`.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cocuk import tamamlama_puanla as tp  # noqa: E402

KESIK = '{"puan": 0, "gerekce": "\'taşır\' değil, \'taşır\' değil, \'taş'
DONGU = '{"gerekce": "taşır değil, taşır değil'


class KurtarmaTesti(unittest.TestCase):
    def test_kesik_json_kurtarilir(self):
        sonuc = tp.ogretmen_puani(lambda m, s: KESIK, "yonerge", "cumle")
        self.assertEqual(sonuc, {"puan": 0, "gerekce": tp.KESILDI})

    def test_gecersiz_puan_kurtarilmaz(self):
        self.assertEqual(tp.kesik_kurtar('{"puan": 7, "gerekce": "ya'), '{"puan": 7, "gerekce": "ya')

    def test_kurtarilamayan_puanlanamadi(self):
        with self.assertLogs("tamamlama_puanla", "ERROR"):
            sonuc = tp.ogretmen_puani(lambda m, s: DONGU, "yonerge", "cumle")
        self.assertEqual(sonuc, {"puan": None, "gerekce": tp.PUANLANAMADI})

    def test_ozet_puanlanamayani_ayri_sayar(self):
        perde = {"C0": {"ad": "a", "gece": 1, "cumle": "bir iki üç dört"},
                 "C1": {"ad": "a", "gece": 1, "cumle": "bir iki üç"}}
        puanlar = {"C0": {"puan": 1}, "C1": {"puan": None}}
        hucre = tp.ozetle(perde, puanlar)["a"]["1"]
        self.assertEqual((hucre["toplam"], hucre["puan"], hucre[tp.PUANLANAMADI]), (1, 1, 1))


if __name__ == "__main__":
    unittest.main()
