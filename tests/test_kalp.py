"""Kalp sozlesme testi (spec 3.2, 9): dogma (3 kez), sonme (M7), bozuk dosya, golge mod.
Cagiran: `python -m unittest discover -s tests`. Gecici klasor kullanir, gercek defter/'e dokunmaz."""

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import minik

SAHTE_TON = lambda metin: ("notr", "sahte")  # aga gitmesin
from ortak import log
from yuvalar import kalp

IS_SN = 1.0
KAFA_CEVABI = "kafanin cevabi"


def _son_kalp_logu():
    dosya = log.LOG_KLASORU / f"{datetime.now().astimezone():%Y-%m-%d}.log"
    satirlar = [json.loads(s) for s in dosya.read_text(encoding="utf-8").splitlines() if s.strip()]
    return [s for s in satirlar if s["yuva"] == kalp.YUVA_ADI][-1]


class TestKalp(unittest.TestCase):
    def setUp(self):
        self._gecici = tempfile.TemporaryDirectory()
        self._eski = kalp.defter.DEFTER_KLASORU
        kalp.defter.DEFTER_KLASORU = Path(self._gecici.name)

    def tearDown(self):
        kalp.defter.DEFTER_KLASORU = self._eski
        self._gecici.cleanup()

    def _kaliplar(self):
        veri = json.loads(kalp._dosya().read_text(encoding="utf-8"))
        return [r["kalip"] for r in veri["refleksler"]]

    def test_tohum_eslesir_ve_golge_loglanir(self):
        oneri, guven = kalp.refleks_ara({"soru": "Merhaba Minik!"})
        self.assertEqual(oneri["kalip"], "merhaba")
        self.assertEqual(guven, kalp.BASLANGIC_GUC)
        self.assertEqual(_son_kalp_logu()["detay"], {"eslesen": "merhaba", "guven": guven, "golge": True})

    def test_uc_kezden_az_gorulen_dogmaz_ucuncude_dogar(self):
        for _ in range(kalp.DOGMA_ESIGI - 1):
            kalp.tur_sonu("Saat kac?", "Bilmiyorum.", None, 0.0)
        self.assertNotIn("saat kac", self._kaliplar())
        self.assertEqual(kalp.refleks_ara({"soru": "saat kac"})[0], None)
        kalp.tur_sonu("saat kac", "Bilmiyorum.", None, 0.0)
        self.assertIn("saat kac", self._kaliplar())
        self.assertEqual(kalp.refleks_ara({"soru": "Saat kac?"})[0]["tepki"], "Bilmiyorum.")

    def test_odulsuz_kullanimda_soner_ve_duser(self):
        oneri, ilk = kalp.refleks_ara({"soru": "merhaba"})
        kalp.tur_sonu("merhaba", "x", oneri, 0.0)
        _, sonraki = kalp.refleks_ara({"soru": "merhaba"})
        self.assertLess(sonraki, ilk)
        for _ in range(10):
            oneri, _ = kalp.refleks_ara({"soru": "merhaba"})
            if oneri is None:
                break
            kalp.tur_sonu("merhaba", "x", oneri, -0.1)
        self.assertNotIn("merhaba", self._kaliplar())
        self.assertEqual(json.loads(kalp._dosya().read_text(encoding="utf-8"))["sayaclar"]["merhaba"], 1)  # dustugu turda yeniden 1 kez goruldu

    def test_odullu_kullanimda_guc_artar(self):
        oneri, ilk = kalp.refleks_ara({"soru": "merhaba"})
        kalp.tur_sonu("merhaba", "x", oneri, 0.2)
        self.assertGreater(kalp.refleks_ara({"soru": "merhaba"})[1], ilk)

    def test_bozuk_dosyada_none_ve_hata_logu(self):
        kalp._dosya().write_text("{bozuk json", encoding="utf-8")
        self.assertEqual(kalp.refleks_ara({"soru": "merhaba"}), (None, 0.0))
        self.assertEqual(_son_kalp_logu()["sonuc"], "hata")

    def test_eksik_alanli_refleks_bozuk_sayilir(self):
        kalp._dosya().write_text(json.dumps({"refleksler": [{"kalip": "a"}], "sayaclar": {}}), encoding="utf-8")
        self.assertEqual(kalp.refleks_ara({"soru": "a"}), (None, 0.0))

    def test_veto_yalniz_bayrak(self):
        veri = {"refleksler": [dict(kalp.TOHUM, kalip="kapat", tepki="dur")], "sayaclar": {}}
        kalp._dosya().write_text(json.dumps(veri), encoding="utf-8")
        kalp.refleks_ara({"soru": "kapat"})
        self.assertEqual(_son_kalp_logu()["detay"]["veto"], "dur")

    def test_golge_modda_akis_cevabi_degismez(self):
        """Kirmizi yanabilir: akis refleks tepkisini soylerse bu test duser."""
        veri = {"refleksler": [dict(kalp.TOHUM, kalip="selam", tepki="REFLEKS", guc=1.0)], "sayaclar": {}}
        kalp._dosya().write_text(json.dumps(veri), encoding="utf-8")
        sorular = ["selam", minik.CIKIS_KELIMESI]
        soylenen = []
        minik.calistir(ton_oku=SAHTE_TON, dinle=lambda: sorular.pop(0), soyle=lambda m, d: soylenen.append(m),
                       dusun=lambda s, b, h=None: (KAFA_CEVABI, IS_SN), gece=lambda *a, **k: None)
        self.assertEqual(soylenen, [KAFA_CEVABI])
        self.assertNotIn("REFLEKS", soylenen)


if __name__ == "__main__":
    unittest.main()
