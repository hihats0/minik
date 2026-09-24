"""Ton -> hormon baglantisi testi: agsiz, GPU'suz. Ovgu oksitosin+dopamin, hakaret kortizol, notr dokunmaz;
akista ton cevap soylendikten sonra islenir. Cagiran: `python -m unittest discover -s tests`."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import minik
from yuvalar import hormonlar, ton_hormon


def _sabit(ton_adi):
    return lambda metin: (ton_adi, "sahte")


class TestTonHormon(unittest.TestCase):
    def test_ovgu_oksitosin_dopamin(self):
        h = hormonlar.Hormonlar()
        once = h.oku()
        self.assertEqual(ton_hormon.isle("harikasin", h, _sabit("ovgu")), "ovgu")
        sonra = h.oku()
        self.assertGreater(sonra["oksitosin"], once["oksitosin"])
        self.assertGreater(sonra["dopamin"], once["dopamin"])

    def test_hakaret_kortizol(self):
        h = hormonlar.Hormonlar()
        once = h.oku()["kortizol"]
        ton_hormon.isle("aptal", h, _sabit("hakaret"))
        self.assertGreater(h.oku()["kortizol"], once)

    def test_notr_dokunmaz(self):
        h = hormonlar.Hormonlar()
        once = h.oku()
        ton_hormon.isle("saat kac", h, _sabit("notr"))
        for ad in ("oksitosin", "dopamin", "kortizol"):
            self.assertAlmostEqual(h.oku()[ad], once[ad], places=3)

    def test_olay_adlari_gercek(self):
        for olaylar in ton_hormon.TON_OLAYLARI.values():
            for olay, _ in olaylar:
                self.assertIn(olay, hormonlar.OLAYLAR)


class TestAkistaTon(unittest.TestCase):
    def setUp(self):
        self._gecici = tempfile.TemporaryDirectory()
        self._eski = minik.defter.DEFTER_KLASORU
        minik.defter.DEFTER_KLASORU = Path(self._gecici.name)

    def tearDown(self):
        minik.defter.DEFTER_KLASORU = self._eski
        self._gecici.cleanup()

    def test_ton_cevaptan_sonra(self):
        sira = []
        sorular = ["harikasin", minik.CIKIS_KELIMESI]

        def ton_oku(metin):
            sira.append("ton")
            return "ovgu", "sahte"
        minik.calistir(dinle=lambda: sorular.pop(0), soyle=lambda m, d: sira.append("soyle"),
                       dusun=lambda s, b, h=None: ("cevap", 1.0), hormon_durumu=hormonlar.Hormonlar(),
                       ton_oku=ton_oku)
        self.assertEqual(sira, ["soyle", "ton"])


if __name__ == "__main__":
    unittest.main()
