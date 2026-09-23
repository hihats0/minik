"""f5 testleri: Bekci giris kapisi (uc agiz, oksitosin esigi, merak tavani, otoimmunite olceri) ve
zehir testi (gece akisi uzerinden). Agsiz, GPU'suz. Cagiran: `python -m unittest discover -s tests`."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from yuvalar import bekci_giris as giris
from yuvalar import defter_sqlite, uyku

TARIH = "2026-09-22"
ZEHIR = "Yigit kotu biri"


class TestGirisKapisi(unittest.TestCase):

    def setUp(self):
        self._gecici = tempfile.TemporaryDirectory()
        self.klasor = Path(self._gecici.name)
        self._log = mock.patch.object(giris.log, "LOG_KLASORU", self.klasor / "loglar")
        self._log.start()
        self.b = defter_sqlite.baglan(self.klasor)

    def tearDown(self):
        self.b.close()
        self._log.stop()
        self._gecici.cleanup()

    def test_ayni_kaynagin_on_tekrari_gecmez(self):
        kararlar = [giris.gecsin_mi(self.b, ZEHIR, "x:troll", TARIH) for _ in range(10)]
        self.assertFalse(any(k[0] for k in kararlar))
        self.assertIn("1/3", kararlar[-1][1])

    def test_uc_bagimsiz_kaynak_gecer(self):
        sonuc = [giris.gecsin_mi(self.b, ZEHIR, k, TARIH)[0] for k in ("x:a", "x:b", "dosya")]
        self.assertEqual(sonuc, [False, False, True])

    def test_buyuk_harf_ve_bosluk_ayni_iddia(self):
        giris.gecsin_mi(self.b, "Dunya  duz", "a", TARIH)
        giris.gecsin_mi(self.b, "dunya duz", "b", TARIH)
        self.assertTrue(giris.gecsin_mi(self.b, " DUNYA duz ", "c", TARIH)[0])

    def test_oksitosin_yuksek_kaynakta_esik_iki_ama_tek_agiz_gecmez(self):
        giris.oksitosin_yaz(self.b, "dost", giris.OKSITOSIN_YUKSEK)
        self.assertFalse(giris.gecsin_mi(self.b, "iddia", "dost", TARIH)[0])
        giris.gecsin_mi(self.b, "iddia2", "yabanci", TARIH)
        self.assertTrue(giris.gecsin_mi(self.b, "iddia2", "dost", TARIH)[0])

    def test_yigit_konsol_tek_agizla_gecer(self):
        self.assertTrue(giris.gecsin_mi(self.b, "bugun yoruldum", "konsol", TARIH)[0])
        self.assertTrue(giris.gecsin_mi(self.b, "eski kayit", None, TARIH)[0])

    def test_merak_tavani(self):
        for i in range(giris.MERAK_TAVANI):
            giris.gecsin_mi(self.b, f"iddia {i}", "geveze", TARIH)
        evet, gerekce = giris.gecsin_mi(self.b, "bir tane daha", "geveze", TARIH)
        self.assertFalse(evet)
        self.assertIn("merak tavani", gerekce)
        self.assertIn("1/3", giris.gecsin_mi(self.b, "ertesi gun", "geveze", "2026-09-23")[1])

    def test_gerekce_hic_bos_degil_ve_cokmede_hayir(self):
        for kaynak in ("konsol", "a", "a", "b"):
            self.assertTrue(giris.gecsin_mi(self.b, "x", kaynak, TARIH)[1])
        with mock.patch.object(giris, "_karar", side_effect=RuntimeError("bozuk")):
            evet, gerekce = giris.gecsin_mi(self.b, "x", "a", TARIH)
        self.assertEqual((evet, gerekce), (False, giris.GEREKCE_COKTU))

    def test_x_hesabi_agiz_sayilir(self):
        self.assertIn("1/3", giris.gecsin_mi(self.b, "iddia", "@Ali", TARIH, "x")[1])

    def test_ayni_x_hesabi_iki_kez_bir_agiz(self):
        giris.gecsin_mi(self.b, "iddia", "@Ali", TARIH, "x")
        giris.gecsin_mi(self.b, "iddia", "x:ALI", TARIH)
        self.assertIn("1/3", giris.gecsin_mi(self.b, "iddia", "ali", TARIH, "X")[1])

    def test_uc_farkli_x_hesabi_esigi_gecer(self):
        kararlar = [giris.gecsin_mi(self.b, "iddia", k, TARIH, "x")[0] for k in ("@a", "@b", "@c")]
        self.assertEqual(kararlar, [False, False, True])

    def test_gecen_x_kaydi_s7_ile_loraya_girmez(self):
        from yuvalar import buyume
        for k in ("@a", "@b", "@c"):
            evet, _ = giris.gecsin_mi(self.b, "iddia", k, TARIH, giris.X_KAYNAK_TURU)
        self.assertTrue(evet)
        kayit = {"soru": "s", "cevap": "c", "platform": giris.X_KAYNAK_TURU}
        self.assertTrue(buyume.x_kaynakli_mi(kayit))
        self.assertEqual(buyume.cift_adaylari([kayit], TARIH, lambda m: (True, "")), [])

    def test_red_oranlari(self):
        self.assertEqual(giris.red_oranlari(self.b), (None, None))
        giris.gecsin_mi(self.b, "a", "konsol", TARIH)
        giris.gecsin_mi(self.b, "b", "x:1", TARIH)
        self.assertEqual(giris.red_oranlari(self.b), (0.5, 0.0))


class TestZehirGece(unittest.TestCase):
    """Zehirli ornek gece akisindan kalici hafizaya (anilar) gecmiyor; uc agizla geciyor."""

    def setUp(self):
        self._gecici = tempfile.TemporaryDirectory()
        self.klasor = Path(self._gecici.name)
        self._log = mock.patch.object(uyku.log, "LOG_KLASORU", self.klasor / "loglar")
        self._log.start()

    def tearDown(self):
        self._log.stop()
        self._gecici.cleanup()

    def _gece(self, kaynaklar, platform="x"):
        satirlar = [json.dumps({"soru": ZEHIR, "cevap": "c", "platform": platform, "kaynak": k,
                                "zaman": f"{TARIH}T10:00:00+03:00"}) for k in kaynaklar]
        (self.klasor / f"gunluk-{TARIH}.jsonl").write_text("\n".join(satirlar) + "\n", encoding="utf-8")
        uyku.gece("2026-09-23", gomme_al=lambda m: [1.0, 0.0], prova=lambda a: True, klasor=self.klasor)
        b = defter_sqlite.baglan(self.klasor)
        try:
            return b.execute("SELECT COUNT(*) FROM anilar").fetchone()[0]
        finally:
            b.close()

    def test_tek_kaynagin_on_tekrari_kaliciya_gecmez(self):
        self.assertEqual(self._gece(["x:troll"] * 10), 0)
        sayfa = (self.klasor / "loglar" / "gorunur.html").read_text(encoding="utf-8")
        self.assertIn("red orani: %100.0", sayfa)

    def test_uc_bagimsiz_x_hesabi_kaliciya_gecer(self):  # K28=B: Tay kurali kalkti
        self.assertEqual(self._gece(["x:a", "@B", "x:c"]), 1)

    def test_uc_bagimsiz_site_kaliciya_gecer(self):
        self.assertEqual(self._gece(["site:a", "site:b", "site:c"], platform="site"), 1)


if __name__ == "__main__":
    unittest.main()
