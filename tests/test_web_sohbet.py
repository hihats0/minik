"""Web sohbet agzi testi: sahte dusun/ton_oku/sunucu ile gercek HTTP (port 0). GPU'ya ve aga dokunmaz,
Defter gecici klasore baglanir. Cagiran: `python -m unittest discover -s tests`."""

import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agiz import web_sohbet  # noqa: E402
from agiz.web_sohbet_kafa import HAZIR, KAPALI, KafaYonetici  # noqa: E402
from yuvalar import defter, hormonlar  # noqa: E402

ANAHTAR = "gizli-test"


class TestWebSohbet(unittest.TestCase):
    def setUp(self):
        self._gecici = tempfile.TemporaryDirectory()
        self._eski = defter.DEFTER_KLASORU
        defter.DEFTER_KLASORU = Path(self._gecici.name)
        self.sunucu = web_sohbet.sunucu_kur(
            ANAHTAR, lambda s, b, h=None: ("merhaba " + s, 1.0), lambda: "hazir",
            hormonlar.Hormonlar(), ton_oku=lambda m: ("ovgu", "sahte"), port=0)
        threading.Thread(target=self.sunucu.serve_forever, daemon=True).start()
        self.kok = f"http://127.0.0.1:{self.sunucu.server_address[1]}"

    def tearDown(self):
        self.sunucu.shutdown()
        self.sunucu.server_close()
        defter.DEFTER_KLASORU = self._eski
        self._gecici.cleanup()

    def _istek(self, yol, govde=None, anahtar=ANAHTAR):
        veri = None if govde is None else json.dumps(govde).encode()
        istek = urllib.request.Request(self.kok + yol, data=veri, headers={"X-Anahtar": anahtar})
        try:
            with urllib.request.urlopen(istek, timeout=10) as y:
                return y.status, json.loads(y.read())
        except urllib.error.HTTPError as hata:
            return hata.code, json.loads(hata.read())

    def test_anahtarsiz_401(self):
        self.assertEqual(self._istek("/durum", anahtar="yanlis")[0], 401)

    def test_konus_cevap_ve_hormon(self):
        kod, govde = self._istek("/konus", {"mesaj": "selam"})
        self.assertEqual(kod, 200)
        self.assertEqual(govde["cevap"], "merhaba selam")
        self.assertIn("oksitosin", govde["hormonlar"])
        self.assertEqual(govde["yas"], 0)

    def test_durum(self):
        kod, govde = self._istek("/durum")
        self.assertEqual(kod, 200)
        self.assertEqual(govde["kafa"], "hazir")
        self.assertEqual(len(govde["hormonlar"]), 7)

    def test_uzun_ve_bos_mesaj_400(self):
        self.assertEqual(self._istek("/konus", {"mesaj": "a" * 501})[0], 400)
        self.assertEqual(self._istek("/konus", {"mesaj": "  "})[0], 400)


class SahteProc:
    def __init__(self):
        self.acik = True

    def poll(self):
        return None if self.acik else 0


class SahteBekci:
    kesildi = False

    def serinle(self):
        return 0.0

    def bitir(self):
        pass


class TestKafaYonetici(unittest.TestCase):
    def test_acar_ve_bosta_kapatir(self):
        acilan = []
        y = KafaYonetici(baslat=lambda: acilan.append(SahteProc()) or acilan[-1], hazir_bekle=lambda p: None,
                         durdur=lambda p: setattr(p, "acik", False), bekci_yap=lambda kes: SahteBekci(),
                         dusun_fn=lambda s, b, h: ("c", 1.0))
        self.assertEqual(y.dusun("s"), ("c", 1.0))
        self.assertEqual(y.durum, HAZIR)
        y.dusun("s")
        self.assertEqual(len(acilan), 1)
        self.assertTrue(y.bosta_kapat(simdi=y.son_istek + 3601))
        self.assertEqual(y.durum, KAPALI)
        y.dusun("s")
        self.assertEqual(len(acilan), 2)


if __name__ == "__main__":
    unittest.main()
