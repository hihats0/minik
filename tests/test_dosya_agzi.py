"""Dosya agzi testi (f8-a, spec 2.6): agiz degisince yuvalar ayni cagrilari aliyor mu, Defter'e
platform "dosya" mi yaziliyor. Sahte Kafa, GPU'suz; defter ve cikti gecici klasorde.
Cagiran: `python -m unittest discover -s tests`."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import minik
from agiz import dosya, konsol, secim
from yuvalar import defter, hormonlar

SORULAR = ["selam", "2+2 kac"]
IS_SN = 1.0


class KaydedenKafa:
    """Sahte Kafa: her cagrinin (soru, baglam) kopyasini tutar, sabit cevap verir."""

    def __init__(self):
        self.cagrilar = []

    def __call__(self, soru, baglam, hormon=None):
        self.cagrilar.append((soru, [dict(m) for m in baglam]))
        return "cevap: " + soru, IS_SN


class TestDosyaAgzi(unittest.TestCase):
    def setUp(self):
        self._gecici = tempfile.TemporaryDirectory()
        self.klasor = Path(self._gecici.name)
        self._eski = minik.defter.DEFTER_KLASORU

    def tearDown(self):
        minik.defter.DEFTER_KLASORU = self._eski
        self._gecici.cleanup()

    def _tur(self, ad, dinle, soyle, platform):
        """Taze gecici defterle bir oturum kosar; Kafa'nin aldigi cagrilari ve Defter'i dondurur."""
        minik.defter.DEFTER_KLASORU = self.klasor / ad
        kafa = KaydedenKafa()
        hormon = hormonlar.Hormonlar(self.klasor / ad / "hormon.json")
        minik.calistir(dinle=dinle, soyle=soyle, dusun=kafa, hormon_durumu=hormon,
                       gece=lambda *a, **k: None, platform=platform)
        return kafa.cagrilar, defter.oku()

    def _dosya_agzi(self):
        girdi = self.klasor / "girdi.txt"
        girdi.write_text("\n".join(SORULAR) + "\n\n", encoding="utf-8")
        return dosya.DosyaAgzi(girdi, self.klasor / "cikti.txt")

    def test_konsol_ve_dosya_yuvalara_ayni_cagrilari_yapar(self):
        with mock.patch("builtins.input", side_effect=SORULAR + [minik.CIKIS_KELIMESI]), \
                mock.patch("builtins.print"):
            konsol_cagri, _ = self._tur("konsol", konsol.dinle, konsol.soyle, "konsol")
        agiz = self._dosya_agzi()
        dosya_cagri, kayitlar = self._tur("dosya", agiz.dinle, agiz.soyle, dosya.PLATFORM)
        self.assertEqual(konsol_cagri, dosya_cagri)
        self.assertEqual(len(dosya_cagri), len(SORULAR))
        self.assertEqual({k["platform"] for k in kayitlar}, {"dosya"})

    def test_cevaplar_cikti_dosyasina_yazilir(self):
        agiz = self._dosya_agzi()
        self._tur("cikti", agiz.dinle, agiz.soyle, dosya.PLATFORM)
        satirlar = (self.klasor / "cikti.txt").read_text(encoding="utf-8").splitlines()
        self.assertEqual(satirlar, [f"Minik: cevap: {s}" for s in SORULAR])

    def test_secim_dosya_agzini_kurar(self):
        girdi = self.klasor / "g.txt"
        girdi.write_text("merhaba\n", encoding="utf-8")
        dinle, _, platform = secim.agiz_sec(["--agiz", "dosya", "--girdi", str(girdi),
                                             "--cikti", str(self.klasor / "c.txt")])
        self.assertEqual((platform, dinle(), dinle()), ("dosya", "merhaba", minik.CIKIS_KELIMESI))

    def test_secim_varsayilan_konsol(self):
        self.assertEqual(secim.agiz_sec([]), (konsol.dinle, konsol.soyle, "konsol"))


if __name__ == "__main__":
    unittest.main()
