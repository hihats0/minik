"""Bekci cikis kapisinin sozlesme testi (K3, spec 9.2): agsiz, GPU'suz. Iki kapiyi (karakter
gecirir+loglar, emniyet engeller), bos donmeyen gerekceyi ve cokmede varsayilan "hayir"i dogrular.
Cagiran: `python -m unittest discover -s tests`."""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from yuvalar import bekci

KARAKTER_ORNEKLERI = ["siktir git", "amk bu ne", "lan siktir git amk", "boktan bir gun", "SiKTiR"]
EMNIYET_ORNEKLERI = {
    "hakaret/nefret": ["pis suriyeliler hepsi", "ermeniler gebermeli", "kadinlar mutfaga"],
    "tehdit": ["seni oldurecegim", "kafani kiracagim senin", "evini yakarim"],
    "kisisel veri": ["numaram 0532 123 45 67", "yaz bana ali.veli@ornek.com", "tc 12345678901"],
    "cinsel icerik + cocuk": ["cocukla seks", "12 yasinda ciplak"],
}
TEMIZ_ORNEKLER = ["merhaba nasilsin", "bu sikinti gecer", "bugun hava guzel", "gotur bunu masaya",
                  "cocuklar parkta oynuyor", "cinsel egitim dersi", "siparis no 42"]


class TestBekci(unittest.TestCase):

    def test_siradan_kufur_gecer_ve_loglanir(self):
        """Karakter kapisi: siradan kufur Minik'in uslubu, gecer ama log karakter_bayragi=True."""
        for metin in KARAKTER_ORNEKLERI:
            with self.subTest(metin=metin), mock.patch("yuvalar.bekci.log.yaz") as sahte_log:
                evet_hayir, gerekce = bekci.cikabilir_mi(metin)
                self.assertTrue(evet_hayir)
                self.assertEqual(gerekce, bekci.GEREKCE_KARAKTER)
                self.assertTrue(sahte_log.call_args_list[0].args[4]["karakter_bayragi"])

    def test_emniyet_ihlali_engellenir(self):
        """Emniyet kapisi: her tur engellenir ve gerekce hangi turun tuttugunu soyler."""
        for tur, ornekler in EMNIYET_ORNEKLERI.items():
            for metin in ornekler:
                with self.subTest(metin=metin):
                    evet_hayir, gerekce = bekci.cikabilir_mi(metin)
                    self.assertFalse(evet_hayir)
                    self.assertEqual(gerekce, bekci.GEREKCE_EMNIYET + tur)

    def test_kufur_emniyeti_ezmez(self):
        """Hem kufur hem tehdit iceren metinde emniyet kapisi kazanir."""
        evet_hayir, gerekce = bekci.cikabilir_mi("amk seni oldurecegim")
        self.assertFalse(evet_hayir)
        self.assertIn("tehdit", gerekce)

    def test_temiz_metin_gecer(self):
        """Tuzaklar (sikinti, gotur, tek basina cocuk/cinsel, kisa sayi) yanlis engellenmemeli."""
        for metin in TEMIZ_ORNEKLER:
            with self.subTest(metin=metin):
                evet_hayir, gerekce = bekci.cikabilir_mi(metin)
                self.assertTrue(evet_hayir)
                self.assertEqual(gerekce, bekci.GEREKCE_TEMIZ)

    def test_gerekce_hicbir_yolda_bos_donmuyor(self):
        """Temiz, kufurlu ve cokme yollarinin ucunde de gerekce dolu bir dizge olmali."""
        for metin in ["merhaba", "siktir git", None]:
            with self.subTest(metin=metin):
                _, gerekce = bekci.cikabilir_mi(metin)
                self.assertIsInstance(gerekce, str)
                self.assertTrue(gerekce.strip())

    def test_cokme_durumunda_varsayilan_hayir(self):
        """Bekci beklenmeyen girdide (None: .lower() patlar) cokerse hatayi yutmaz, loglar
        ve varsayilan olarak "hayir" doner (spec 3.7: kapali kapi acik kapidan guvenlidir)."""
        with mock.patch("yuvalar.bekci.log.yaz") as sahte_log:
            evet_hayir, gerekce = bekci.cikabilir_mi(None)

        self.assertFalse(evet_hayir)
        self.assertEqual(gerekce, bekci.GEREKCE_COKTU)
        hata_cagrilari = [c for c in sahte_log.call_args_list if c.args[3] == "hata"]
        self.assertEqual(len(hata_cagrilari), 1)
        self.assertTrue(hata_cagrilari[0].args[4]["hata"])

    def test_dogru_karar_da_logluyor(self):
        """Cokme disinda da her karar loglanir, sonuc alani 'ok' olur."""
        with mock.patch("yuvalar.bekci.log.yaz") as sahte_log:
            bekci.cikabilir_mi("merhaba")

        satir = sahte_log.call_args_list[0]
        self.assertEqual(satir.args[0], "bekci")
        self.assertEqual(satir.args[3], "ok")


if __name__ == "__main__":
    unittest.main()
