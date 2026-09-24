"""Baglam butcesi testi (f3-f): agsiz, GPU'suz. 50 turluk sahte konusmada Kafa'ya giden mesajlarin
butceyi asmadigini, en yeni sorunun hep durdugunu ve dusurmenin loglandigini dogrular.
Cagiran: `python -m unittest discover tests`."""

import json
import sys
import tempfile
import unittest
from unittest import mock
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


def _konus():
    """50 turu gercek akistan gecirir; her dusun cagrisinda Kafa'ya gidecek listeyi saklar."""
    sorular = [f"soru {i}" for i in range(TUR_SAYISI)] + [minik.CIKIS_KELIMESI]
    gidenler = []

    def sahte_dusun(soru, baglam, hormon=None):
        gidenler.append(list(baglam) + [{"role": "user", "content": soru}])
        return "x" * CEVAP_KARAKTER, IS_SN

    minik.calistir(ton_oku=SAHTE_TON, dinle=lambda: sorular.pop(0), soyle=lambda metin, dis_id: None,
                   dusun=sahte_dusun)
    return gidenler


class TestBaglamButce(unittest.TestCase):
    """Defter ve log gecici klasorde; 50 tur bir kez konusulur, testler ayni sonucu denetler (hiz)."""

    @classmethod
    def setUpClass(cls):
        cls._gecici = tempfile.TemporaryDirectory()
        gecici = Path(cls._gecici.name)
        cls._yamalar = [mock.patch.object(minik.defter, "DEFTER_KLASORU", gecici / "defter"),
                        mock.patch.object(log, "LOG_KLASORU", gecici / "loglar")]
        for yama in cls._yamalar:
            yama.start()
        cls.gidenler = _konus()
        cls.log_satirlari = _bugunku_log_satirlari()

    @classmethod
    def tearDownClass(cls):
        for yama in cls._yamalar:
            yama.stop()
        cls._gecici.cleanup()

    def test_50_turda_butce_asilmaz(self):
        self.assertEqual(len(self.gidenler), TUR_SAYISI)
        for giden in self.gidenler:
            self.assertLessEqual(baglam_butce.token_tahmini(giden), BAGLAM_TOKEN_BUTCESI)

    def test_en_yeni_soru_hep_durur(self):
        for i, giden in enumerate(self.gidenler):
            self.assertEqual(giden[-1], {"role": "user", "content": f"soru {i}"})

    def test_dusurme_loglanir(self):
        dusurmeler = [s for s in self.log_satirlari if s["olay"] == "baglam_sinirla"]
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
