"""Baglam butcesi testi (f3-f): agsiz, GPU'suz. 50 turluk sahte konusmada Kafa'ya giden mesajlarin
butceyi asmadigini, en yeni sorunun hep durdugunu ve dusurmenin loglandigini dogrular.
Cagiran: `python -m unittest discover tests`."""

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import minik

SAHTE_TON = lambda metin: ("notr", "sahte")  # aga gitmesin
from ortak import baglam_butce, log
from ortak.ayar import BAGLAM_TOKEN_BUTCESI

TUR_SAYISI = 50
# f3-e'deki uzun cevaplar ~1.400 karakterdi; 50 turda butce kat kat asilsin diye bu boy.
CEVAP_KARAKTER = 1400
IS_SN = 1.0


def _bugunku_log_satirlari():
    dosya = log.LOG_KLASORU / f"{datetime.now().astimezone():%Y-%m-%d}.log"
    with dosya.open(encoding="utf-8") as f:
        return [json.loads(s) for s in f if s.strip()]


class TestBaglamButce(unittest.TestCase):

    def setUp(self):
        self._gecici = tempfile.TemporaryDirectory()
        self._eski_klasor = minik.defter.DEFTER_KLASORU
        minik.defter.DEFTER_KLASORU = Path(self._gecici.name)

    def tearDown(self):
        minik.defter.DEFTER_KLASORU = self._eski_klasor
        self._gecici.cleanup()

    def _konus(self):
        """50 turu gercek akistan gecirir; her dusun cagrisinda Kafa'ya gidecek listeyi saklar."""
        sorular = [f"soru {i}" for i in range(TUR_SAYISI)] + [minik.CIKIS_KELIMESI]
        gidenler = []

        def sahte_dusun(soru, baglam, hormon=None):
            gidenler.append(list(baglam) + [{"role": "user", "content": soru}])
            return "x" * CEVAP_KARAKTER, IS_SN

        minik.calistir(ton_oku=SAHTE_TON, dinle=lambda: sorular.pop(0), soyle=lambda metin, dis_id: None,
                       dusun=sahte_dusun)
        return gidenler

    def test_50_turda_butce_asilmaz(self):
        for giden in self._konus():
            self.assertLessEqual(baglam_butce.token_tahmini(giden), BAGLAM_TOKEN_BUTCESI)

    def test_en_yeni_soru_hep_durur(self):
        for i, giden in enumerate(self._konus()):
            self.assertEqual(giden[-1], {"role": "user", "content": f"soru {i}"})

    def test_dusurme_loglanir(self):
        baslangic = len(_bugunku_log_satirlari())
        self._konus()
        yeni = _bugunku_log_satirlari()[baslangic:]
        dusurmeler = [s for s in yeni if s["olay"] == "baglam_sinirla"]
        self.assertTrue(dusurmeler)
        self.assertGreaterEqual(dusurmeler[0]["detay"]["dusen_tur"], 1)

    def test_soru_tek_basina_buyukse_dusmez_ve_hata_loglar(self):
        baglam = [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}]
        dev_soru = "s" * 100
        dusen = baglam_butce.sinirla(baglam, dev_soru, butce=10)
        self.assertEqual((dusen, baglam), (1, []))
        self.assertEqual(_bugunku_log_satirlari()[-1]["sonuc"], "hata")


if __name__ == "__main__":
    unittest.main()
