"""<think> ayiklama ve Gemma sunucu profili testleri (k26-a): modelsiz, GPU'suz.
Cagiran: `python -m unittest discover -s tests`."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ortak.ayar import GEMMA_SUNUCU_ARGUMANLARI, KAFA_MODEL_YOLU
from yuvalar.kafa_dusunce import dusunce_ayikla


@patch("yuvalar.kafa_dusunce.log.yaz")
class DusunceAyiklaTesti(unittest.TestCase):
    def test_tek_blok(self, yaz):
        self.assertEqual(dusunce_ayikla("<think>hmm</think>\nMerhaba!"), "Merhaba!")
        self.assertEqual(yaz.call_args.args[3], "ok")
        self.assertIn("hmm", yaz.call_args.args[4]["dusunce"])

    def test_coklu_blok(self, yaz):
        cevap = "<think>a</think>Bir <think>b</think>iki"
        self.assertEqual(dusunce_ayikla(cevap), "Bir iki")
        self.assertEqual(yaz.call_args.args[4]["blok"], 2)

    def test_kapanmamis_blok(self, yaz):
        self.assertEqual(dusunce_ayikla("Selam. <think>yarim kal"), "Selam.")
        self.assertTrue(yaz.call_args.args[4]["kesik"])

    def test_think_yok(self, yaz):
        self.assertEqual(dusunce_ayikla("Duz cevap"), "Duz cevap")
        yaz.assert_not_called()

    def test_yalniz_think_bos_cevap_loglanir(self, yaz):
        self.assertEqual(dusunce_ayikla("<think>sadece dusunce</think>"), "")
        self.assertEqual(yaz.call_args.args[3], "hata")


class GemmaProfilTesti(unittest.TestCase):
    def test_bayraklar(self):
        a = GEMMA_SUNUCU_ARGUMANLARI
        for bayrak, deger in (("-c", "4096"), ("--cache-type-k", "q8_0"),
                              ("--cache-type-v", "q8_0"), ("--device", "Vulkan1")):
            self.assertEqual(a[a.index(bayrak) + 1], deger)
        self.assertIn("Turkish-Gemma-9b-T1", a[a.index("-m") + 1])

    def test_varsayilan_kafa_gemma(self):
        self.assertIn("Turkish-Gemma-9b-T1", KAFA_MODEL_YOLU)

    def test_gemma_max_token_ve_butce(self):
        # k26-c: Gemma 1024 token; butce en uzun cevaba gore 4096 icinde.
        from ortak import ayar
        self.assertEqual(ayar.KAFA_MAX_TOKEN, ayar.GEMMA_MAX_TOKEN)
        toplam = ayar.BAGLAM_TOKEN_BUTCESI + ayar.BAGLAM_EN_UZUN_CEVAP_TOKEN + ayar.BAGLAM_PAY_TOKEN
        self.assertLessEqual(toplam, ayar.KAFA_BAGLAM)


if __name__ == "__main__":
    unittest.main()
