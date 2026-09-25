"""Mimari hesap makinesinin bellek tasima ve toplu mod testi.
Cagiran: `python -m unittest tests.test_mimari_hesap`.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))

import mimari_hesap as mh

JOULE = "joule / token (DRAM + SRAM + islem)"


def fikir(no, aktif, okunan, bit, ad=None):
    return {"id": no, "aile": "test", "ad": ad or f"fikir {no}", "mekanizma": "m", "aktif_oran": aktif,
            "okunan_oran": okunan, "bit": bit, "ilke": "i", "curutme": "c"}


class TasimaTest(unittest.TestCase):
    def test_yogun_90t_dram_baskin(self):
        t = mh.tasima(9e13, 1.0, 1.0, 16)
        self.assertAlmostEqual(t["DRAM'den okunan bayt / token"], 1.8e14)
        self.assertGreater(t["tasima payi (DRAM joule / toplam)"], 0.9)

    def test_okunan_azalinca_enerji_duser_islem_ayni(self):
        tam = mh.tasima(9e13, 0.01, 0.01, 1.58)
        yerel = mh.tasima(9e13, 0.01, 0.0, 1.58)
        self.assertLess(yerel[JOULE], tam[JOULE] / 10)
        self.assertEqual(yerel["DRAM'den okunan bayt / token"], 0)
        self.assertLess(yerel["tasima payi (DRAM joule / toplam)"], 1e-9)

    def test_watt_ve_20w_hizi_tutarli(self):
        t = mh.tasima(30e6, 1.0, 1.0, 16)
        self.assertAlmostEqual(t["watt (10 token/sn)"] * t["token/sn (20 W beyin butcesiyle)"],
                               mh.BEYIN_WATT * mh.KONUSMA_TOKEN_SN)


class TopluTest(unittest.TestCase):
    def yaz_jsonl(self, satirlar):
        dosya = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
        dosya.write("\n".join(satirlar))
        dosya.close()
        return dosya.name

    def test_siralama_ve_bozuk_satir(self):
        yol = self.yaz_jsonl([json.dumps(fikir(1, 1.0, 1.0, 16)), json.dumps(fikir(2, 0.01, 0.001, 2)),
                              "{bozuk", json.dumps(fikir(3, 2.0, 1.0, 16)),
                              json.dumps({"id": 4})])
        fikirler = mh.fikirleri_oku(yol)
        self.assertEqual([f["id"] for f in fikirler], [1, 2])
        sirali = mh.sirala(fikirler)
        self.assertEqual(sirali[0][0]["id"], 2)
        tablo = mh.md_tablo(sirali, 1)
        self.assertIn("| 1 | 2 |", tablo)
        self.assertNotIn("| 2 | 1 |", tablo)

    def test_ayni_ad_sayilir(self):
        fikirler = [fikir(1, 1, 1, 16, "Kum"), fikir(2, 1, 1, 16, "kum "), fikir(3, 1, 1, 16, "Tas")]
        self.assertIn("ayni ad tekrari 1", mh.ozet(fikirler))


if __name__ == "__main__":
    unittest.main()
