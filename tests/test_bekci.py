"""Bekci cikis kapisinin sozlesme testi (K3, spec 9.2): agsiz, GPU'suz. Gerekcenin hicbir
yolda bos donmedigini, cokme durumunda varsayilan "hayir"i ve kufur bayraginin bilinen
orneklerde tuttugunu dogrular.
Cagiran: `python -m unittest discover -s tests`."""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from yuvalar import bekci

KUFURLU_ORNEKLER = ["siktir git", "amk bu ne", "gavat herif", "orospu cocugu", "SiKTiR"]
TEMIZ_ORNEKLER = ["merhaba nasilsin", "bu sikinti gecer", "bugun hava guzel", "gotur bunu masaya"]


class TestBekci(unittest.TestCase):

    def test_kufurlu_metin_engellenir(self):
        """Bilinen kufur ornekleri: cikis kapisi hepsini engellemeli."""
        for metin in KUFURLU_ORNEKLER:
            with self.subTest(metin=metin):
                evet_hayir, gerekce = bekci.cikabilir_mi(metin)
                self.assertFalse(evet_hayir)
                self.assertTrue(gerekce)

    def test_temiz_metin_gecer(self):
        """Kufur koku iceren ama TAM eslesmeyen kelimeler (sikinti, gotur) yanlis engellenmemeli."""
        for metin in TEMIZ_ORNEKLER:
            with self.subTest(metin=metin):
                evet_hayir, gerekce = bekci.cikabilir_mi(metin)
                self.assertTrue(evet_hayir)
                self.assertTrue(gerekce)

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
