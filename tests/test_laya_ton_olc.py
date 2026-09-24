# araclar/laya_ton_olc.py için testler; model yüklemez, sahte ajan kullanır.
# python -m unittest tests.test_laya_ton_olc ile koşar.
import importlib.util
import unittest
from pathlib import Path

YOL = Path(__file__).resolve().parent.parent / "araclar" / "laya_ton_olc.py"
_spec = importlib.util.spec_from_file_location("laya_ton_olc", YOL)
olc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(olc)


class SahteAjan:
    """Her metne 'hakaret' der."""

    def predict_batch(self, metinler, sorular, batch_size=None):
        return [{"answers": {"ton": {"choice": "hakaret"}}} for _ in metinler]


class LayaTonOlcTest(unittest.TestCase):
    def test_sorular_yalniz_setteki_etiketler(self):
        s = olc.sorulari_kur(["hakaret", "notr"])
        self.assertEqual(set(s["ton"]["criteria"]), {"hakaret", "notr"})
        self.assertEqual(s["ton"]["type"], "choice")

    def test_ozet_sayilari(self):
        o = olc.ozetle(["hakaret", "notr", "notr"], ["hakaret", "hakaret", "notr"], 3.0)
        self.assertAlmostEqual(o["dogruluk"], 2 / 3)
        self.assertAlmostEqual(o["cogunluk_temeli"], 2 / 3)
        self.assertEqual(o["karisiklik"]["notr->hakaret"], 1)
        self.assertAlmostEqual(o["cumle_basi_sn"], 1.0)

    def test_sahte_ajanla_dis_set(self):
        o = olc.seti_olc(SahteAjan(), olc.DIS_SET)
        self.assertEqual(o["n"], 200)
        self.assertAlmostEqual(o["dogruluk"], 0.53)


if __name__ == "__main__":
    unittest.main()
