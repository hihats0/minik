"""Calgicilar yuvasini (f7) ve akisa baglanmasini dogrular; Kafa sahte, model cagrilmaz.
Cagiran: `python -m unittest discover -s tests`."""

import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import minik
from yuvalar import calgici_tani, calgicilar, hormonlar

KAYNAKLAR = [Path(calgicilar.__file__), Path(calgici_tani.__file__)]
YASAK_KALIBI = re.compile(r"(?<![\w.])(eval|exec|compile|__import__)\s*\(")  # re.compile serbest


class TestGorevler(unittest.TestCase):
    def test_dort_islem(self):
        self.assertEqual(calgicilar.cal("dort_islem", "3 + 4 * 2 - 10 / 4")[0], 8.5)

    def test_tarih_farki(self):
        self.assertEqual(calgicilar.cal("tarih_farki", "2026-01-01 2026-09-23")[0], 265)

    def test_birim_cevirme(self):
        self.assertEqual(calgicilar.cal("birim_cevirme", "2.5 km m")[0], 2500.0)
        self.assertEqual(calgicilar.cal("birim_cevirme", "90 dk saat")[0], 1.5)

    def test_iki_yol_ayni_ve_iz_iki_satir(self):
        ornekler = {"dort_islem": "0.1 + 0.2", "tarih_farki": "2024-02-28 2024-03-01",
                    "birim_cevirme": "7 g kg"}
        for tip, girdi in ornekler.items():
            birinci, ikinci = calgicilar.YOLLAR[tip]
            self.assertAlmostEqual(float(birinci(girdi)), float(ikinci(girdi)))
            sonuc, iz = calgicilar.cal(tip, girdi)
            self.assertIsNotNone(sonuc)
            self.assertEqual(len(iz), 2)


class TestSasirma(unittest.TestCase):
    def test_yollar_ayrisinca_sasirma_dopamin_yukseltir(self):
        """Kirmizi yanabilen test: ikinci yol kasten 1 fazla verir."""
        bozuk = (calgicilar.tarih_cikar, lambda girdi: calgicilar.tarih_ordinal(girdi) + 1)
        durum = hormonlar.Hormonlar()
        once = durum.oku()["dopamin"]
        with mock.patch.dict(calgicilar.YOLLAR, {"tarih_farki": bozuk}), \
                mock.patch.object(calgicilar.log, "yaz") as log_yaz:
            sonuc, iz = calgicilar.cal("tarih_farki", "2026-01-01 2026-01-02", durum)
        self.assertIsNone(sonuc)
        self.assertIn("sasirma", iz[-1])
        self.assertGreater(durum.oku()["dopamin"], once)
        olaylar = [c.args[1] for c in log_yaz.call_args_list if c.args[0] == calgicilar.YUVA_ADI]
        self.assertEqual(olaylar, ["sasirma", "cal"])

    def test_log_detayi_sozlesmeye_uyar(self):
        with mock.patch.object(calgicilar.log, "yaz") as log_yaz:
            calgicilar.cal("dort_islem", "1+1")
        detay = log_yaz.call_args.args[4]
        self.assertEqual(detay, {"gorev_tipi": "dort_islem", "iz_uzunlugu": 2, "sonuc_tipi": "float"})


class TestGuvenlik(unittest.TestCase):
    def test_kaynakta_eval_exec_yok(self):
        for yol in KAYNAKLAR:
            metin = yol.read_text(encoding="utf-8")
            self.assertIsNone(YASAK_KALIBI.search(metin), f"{yol.name} icinde serbest kod calistirma")

    def test_hatali_girdide_hata(self):
        hatalilar = [("dort_islem", "__import__('os')"), ("dort_islem", "2 ** 3"),
                     ("dort_islem", "1 / 0"), ("dort_islem", "3 +"),
                     ("tarih_farki", "2026-13-01 2026-01-01"), ("tarih_farki", "dun"),
                     ("birim_cevirme", "5 km kg"), ("birim_cevirme", "5 parsek m"),
                     ("python", "print(1)")]
        for tip, girdi in hatalilar:
            with self.subTest(tip=tip, girdi=girdi), self.assertRaises(ValueError):
                calgicilar.cal(tip, girdi)


class TestTanima(unittest.TestCase):
    def test_tanir(self):
        self.assertEqual(calgici_tani.tani("12 * 3 kac eder?"), ("dort_islem", "12 * 3"))
        self.assertEqual(calgici_tani.tani("2026-01-01 ile 2026-02-01 arasi kac gun"),
                         ("tarih_farki", "2026-01-01 2026-02-01"))
        self.assertEqual(calgici_tani.tani("3 km kaç m"), ("birim_cevirme", "3 km m"))

    def test_hesap_yoksa_none(self):
        self.assertIsNone(calgici_tani.tani("bugun nasilsin"))


class TestAkis(unittest.TestCase):
    def setUp(self):
        self._gecici = tempfile.TemporaryDirectory()
        self._eski = minik.defter.DEFTER_KLASORU
        minik.defter.DEFTER_KLASORU = Path(self._gecici.name)

    def tearDown(self):
        minik.defter.DEFTER_KLASORU = self._eski
        self._gecici.cleanup()

    def _konus(self, soru):
        """Sahte Kafa hep yanlis sayi soyler; gordugu baglami kaydeder."""
        gorulen = []

        def sahte_kafa(soru, baglam, hormon=None):
            gorulen.append(list(baglam))
            return "Bence 999.", 0.0

        sorular = [soru, minik.CIKIS_KELIMESI]
        minik.calistir(dinle=lambda: sorular.pop(0), soyle=lambda metin, dis_id: None,
                       dusun=sahte_kafa, hormon_durumu=hormonlar.Hormonlar())
        return gorulen[0]

    def test_sonuc_calgicidan_gelir(self):
        baglam = self._konus("17 * 3 kac?")
        self.assertIn("17 * 3 = 51.0", baglam[-1]["content"])
        self.assertNotIn("999", baglam[-1]["content"])

    def test_hesap_yoksa_akis_eskisi_gibi(self):
        baglam = self._konus("merhaba")
        self.assertFalse(any(m["role"] == "system" and "Calgici" in m["content"] for m in baglam))


if __name__ == "__main__":
    unittest.main()
