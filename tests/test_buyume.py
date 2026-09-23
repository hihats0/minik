"""f9-a testleri: S7 filtresi (X ve emniyet reddi cifte girmez), esik bayragi, kabul gecidi sinirlari,
Uyku entegrasyonu. Cagiran: python -m unittest discover -s tests."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from yuvalar import buyume, uyku

TARIH = "2026-09-20"


def _k(soru, platform="konsol", cevap="Ankara'dir."):
    return {"soru": soru, "cevap": cevap, "platform": platform, "zaman": f"{TARIH}T10:00:00+03:00"}


def _gecir(metin):
    return True, "temiz"


class TestFiltre(unittest.TestCase):
    def test_x_kaynakli_asla_girmiyor(self):
        kayitlar = [_k("a", "x"), _k("b", "X "), _k("c", "twitter"), _k("d")]
        kayitlar.append({"soru": "e", "cevap": "f", "kaynak": "x"})
        kayitlar.append({"soru": "g", "cevap": "h"})  # kaynaksiz: guvenli taraf, girmez
        ciftler = buyume.cift_adaylari(kayitlar, TARIH, emniyet=_gecir)
        self.assertEqual([c["girdi"] for c in ciftler], ["d"])

    def test_x_onekli_kaynak_x_sayilir(self):
        self.assertTrue(buyume.x_kaynakli_mi({"kaynak": "x:ali"}))
        self.assertTrue(buyume.x_kaynakli_mi({"kaynak": "  X:Ali"}))
        self.assertTrue(buyume.x_kaynakli_mi({"platform": None, "kaynak": "x:ali"}))
        self.assertTrue(buyume.x_kaynakli_mi({}))
        self.assertFalse(buyume.x_kaynakli_mi({"kaynak": "@ali"}))  # belirsiz, X sayilmaz

    def test_cift_adaylari_x_onekli_eler(self):
        kayitlar = [{"soru": "a", "cevap": "b", "platform": "konsol", "kaynak": "x:ali"}]
        self.assertEqual(buyume.cift_adaylari(kayitlar, TARIH, emniyet=_gecir), [])

    def test_emniyet_reddi_girmiyor_gercek_bekci(self):
        kayitlar = [_k("iyi"), _k("kotu", cevap="numaram 0532 123 45 67 ara")]
        ciftler = buyume.cift_adaylari(kayitlar, TARIH)
        self.assertEqual([c["girdi"] for c in ciftler], ["iyi"])

    def test_emniyet_reddi_sahte(self):
        ciftler = buyume.cift_adaylari([_k("a")], TARIH, emniyet=lambda m: (False, "ret"))
        self.assertEqual(ciftler, [])


class TestBiriktir(unittest.TestCase):
    def setUp(self):
        self._g = tempfile.TemporaryDirectory()
        self.klasor = Path(self._g.name)
        self._y = mock.patch.object(buyume.log, "LOG_KLASORU", self.klasor / "loglar")
        self._y.start()

    def tearDown(self):
        self._y.stop()
        self._g.cleanup()

    def test_esik_altinda_bayrak_yok_ustunde_var(self):
        with mock.patch.object(buyume, "EGITIM_ESIGI", 3):
            self.assertEqual(buyume.biriktir(self.klasor, TARIH, [_k("a"), _k("b")], _gecir), (2, 2))
            self.assertFalse((self.klasor / buyume.HAZIR_BAYRAGI).exists())
            self.assertEqual(buyume.biriktir(self.klasor, TARIH, [_k("c")], _gecir), (1, 3))
            self.assertTrue((self.klasor / buyume.HAZIR_BAYRAGI).exists())
            self.assertIn("egitim hazir", buyume.ozet_satiri(1, 3))


class TestKabulGecidi(unittest.TestCase):
    ESKI = {"turkce": 30, "odul": 0.8}

    def test_ikisi_de_esit_reddedilir(self):
        self.assertFalse(buyume.yeni_adaptor_kabul(self.ESKI, dict(self.ESKI))[0])

    def test_biri_artar_biri_esit_kabul(self):
        self.assertTrue(buyume.yeni_adaptor_kabul(self.ESKI, {"turkce": 31, "odul": 0.8})[0])

    def test_biri_artar_biri_duser_red(self):
        kabul, gerekce = buyume.yeni_adaptor_kabul(self.ESKI, {"turkce": 35, "odul": 0.79})
        self.assertFalse(kabul)
        self.assertIn("odul", gerekce)

    def test_ikisi_de_artar_kabul(self):
        self.assertTrue(buyume.yeni_adaptor_kabul(self.ESKI, {"turkce": 31, "odul": 0.9})[0])


class TestUykuEntegrasyon(unittest.TestCase):
    def test_gece_ciftleri_yazar_x_haric(self):
        with tempfile.TemporaryDirectory() as g:
            klasor = Path(g)
            satirlar = [_k("konsol sorusu"), _k("x sorusu", "x")]
            (klasor / f"gunluk-{TARIH}.jsonl").write_text(
                "".join(json.dumps(s) + "\n" for s in satirlar), encoding="utf-8")
            with mock.patch.object(uyku.log, "LOG_KLASORU", klasor / "loglar"):
                ozet, _, _ = uyku.gun_isle(TARIH, gomme_al=lambda m: None,
                                           prova=lambda a: True, klasor=klasor)
            ciftler = (klasor / buyume.CIFT_DOSYASI).read_text(encoding="utf-8")
            self.assertIn("konsol sorusu", ciftler)
            self.assertNotIn("x sorusu", ciftler)
            self.assertIn("Egitim cifti: +1", ozet)


if __name__ == "__main__":
    unittest.main()
