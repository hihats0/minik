"""Ton yuvasinin sahte sunucu testi (k27-a): dogru etiket, think'li cevap, kume disi cevap, sunucu kapali.
Cagiran: `python -m unittest discover -s tests`."""

import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from test_kafa import SahteYanit  # sahte sunucu duzeni Kafa testinden
from yuvalar import ton

URLOPEN = "yuvalar.ton.urllib.request.urlopen"
# Kural siniflandiricisinin "sert" dedigi cumle; Kafa baska dediginde kaynagin Kafa oldugu gorulur.
SERT_CUMLE = "Bu cevap tamamen sacma olmus."


def _cevap(icerik):
    return lambda istek, timeout: SahteYanit({"choices": [{"message": {"content": icerik}}]})


class TestTon(unittest.TestCase):

    def test_dogru_etiket_kafadan_gelir(self):
        with patch(URLOPEN, side_effect=_cevap("ovgu")), patch("yuvalar.ton.log.yaz"):
            self.assertEqual(ton.ton_oku(SERT_CUMLE), ("ovgu", ton.KAYNAK_KAFA))

    def test_thinkli_cevap_ayiklanir(self):
        with patch(URLOPEN, side_effect=_cevap("<think>kullanici elestiriyor</think>\nSert.")), \
                patch("yuvalar.ton.log.yaz"), patch("yuvalar.kafa_dusunce.log.yaz"):
            self.assertEqual(ton.ton_oku(SERT_CUMLE), ("sert", ton.KAYNAK_KAFA))

    def test_kume_disi_cevap_yedege_doner_ve_loglanir(self):
        with patch(URLOPEN, side_effect=_cevap("mutlu")), patch("yuvalar.ton.log.yaz") as log_yaz:
            self.assertEqual(ton.ton_oku(SERT_CUMLE), ("sert", ton.KAYNAK_KURAL))
        self.assertEqual(log_yaz.call_args.args[3], "hata")

    def test_sunucu_kapali_yedege_doner_ve_loglanir(self):
        with patch(URLOPEN, side_effect=urllib.error.URLError("baglanti reddedildi")), \
                patch("yuvalar.ton.log.yaz") as log_yaz:
            self.assertEqual(ton.ton_oku(SERT_CUMLE), ("sert", ton.KAYNAK_KURAL))
        self.assertIn("kafa cevap vermedi", log_yaz.call_args.args[4]["hata"])


if __name__ == "__main__":
    unittest.main()
