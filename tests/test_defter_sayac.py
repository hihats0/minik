"""Defter satir sayaci testi: sayacli kayit_no'larin eski (her seferinde sayan) hal ile ayni oldugunu
ve dosyaya disaridan satir eklenince dogru devam ettigini dogrular. Gecici klasor kullanir.
Cagiran: `python -m unittest discover -s tests`."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from yuvalar import defter

KAYIT_SAYISI = 20


class TestDefterSayac(unittest.TestCase):

    def setUp(self):
        self._gecici = tempfile.TemporaryDirectory()
        self._eski_klasor = defter.DEFTER_KLASORU
        defter.DEFTER_KLASORU = Path(self._gecici.name)
        defter._sayac.clear()

    def tearDown(self):
        defter.DEFTER_KLASORU = self._eski_klasor
        defter._sayac.clear()
        self._gecici.cleanup()

    def test_numaralar_eski_halle_ayni(self):
        for beklenen in range(1, KAYIT_SAYISI + 1):
            kayit_no = defter.yaz({"soru": str(beklenen)})
            self.assertEqual(kayit_no, defter._satir_sayisi(defter._bugunku_dosya()))
            self.assertEqual(kayit_no, beklenen)

    def test_disaridan_eklenen_satirdan_sonra_dogru_devam(self):
        defter.yaz({"soru": "bir"})
        defter.yaz({"soru": "iki"})
        with defter._bugunku_dosya().open("a", encoding="utf-8") as f:
            f.write(json.dumps({"soru": "baska surec"}) + "\n")
        self.assertEqual(defter.yaz({"soru": "dort"}), 4)

    def test_yeniden_baslayinca_dosyadan_sayar(self):
        defter.yaz({"soru": "bir"})
        defter._sayac.clear()
        self.assertEqual(defter.yaz({"soru": "iki"}), 2)


if __name__ == "__main__":
    unittest.main()
