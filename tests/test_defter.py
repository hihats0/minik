"""Defter sozlesme testi (K3): agsiz, GPU'suz. Sona-ekleme, geri okuma, bozuk satirin tek
basina dusmesi ve yazim hatasinin yukselmesini dogrular. Gecici klasor kullanir, gercek
defter/ klasorune dokunmaz.
Cagiran: `python -m unittest discover -s tests`."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from yuvalar import defter


class TestDefter(unittest.TestCase):

    def setUp(self):
        self._gecici = tempfile.TemporaryDirectory()
        self._eski_klasor = defter.DEFTER_KLASORU
        defter.DEFTER_KLASORU = Path(self._gecici.name)

    def tearDown(self):
        defter.DEFTER_KLASORU = self._eski_klasor
        self._gecici.cleanup()

    def test_yazilan_satir_geri_okunuyor(self):
        defter.yaz({"soru": "merhaba", "cevap": "selam"})

        kayitlar = defter.oku()

        self.assertEqual(len(kayitlar), 1)
        self.assertEqual(kayitlar[0]["soru"], "merhaba")
        self.assertEqual(kayitlar[0]["cevap"], "selam")

    def test_oku_son_n_kayitla_sinirli(self):
        for i in range(5):
            defter.yaz({"soru": f"soru{i}", "cevap": f"cevap{i}"})

        kayitlar = defter.oku(kac_tane=2)

        self.assertEqual([k["soru"] for k in kayitlar], ["soru3", "soru4"])

    def test_jsonl_yalniz_sona_eklenir(self):
        """Var olan satirlar bayt bayt aynen kalir; yeni yazim yalniz sonuna eklenir."""
        defter.yaz({"soru": "ilk", "cevap": "birinci"})
        dosya = defter._bugunku_dosya()
        onceki_bayt = dosya.read_bytes()

        defter.yaz({"soru": "ikinci", "cevap": "ikincisi"})
        sonraki_bayt = dosya.read_bytes()

        self.assertTrue(sonraki_bayt.startswith(onceki_bayt))
        self.assertGreater(len(sonraki_bayt), len(onceki_bayt))

    def test_bozuk_satir_tek_basina_dusuyor(self):
        """Bozuk satir dosyanin tamamini degil, yalniz kendisini oku()'dan dusurur."""
        defter.yaz({"soru": "saglam1", "cevap": "cevap1"})
        dosya = defter._bugunku_dosya()
        with dosya.open("a", encoding="utf-8") as f:
            f.write("bu satir gecerli json degil\n")
        defter.yaz({"soru": "saglam2", "cevap": "cevap2"})

        kayitlar = defter.oku()

        self.assertEqual([k["soru"] for k in kayitlar], ["saglam1", "saglam2"])

    def test_bozuk_satir_atlamasi_loglaniyor(self):
        """Bozuk satir sessizce yutulmaz, atlama ayri bir 'hata' log satiri dusurur."""
        defter.yaz({"soru": "saglam", "cevap": "cevap"})
        dosya = defter._bugunku_dosya()
        with dosya.open("a", encoding="utf-8") as f:
            f.write("{bozuk\n")

        with mock.patch("yuvalar.defter.log.yaz") as sahte_log:
            defter.oku()

        atlama_cagrilari = [c for c in sahte_log.call_args_list if c.args[1] == "satir_atla"]
        self.assertEqual(len(atlama_cagrilari), 1)
        self.assertEqual(atlama_cagrilari[0].args[3], "hata")
        self.assertTrue(atlama_cagrilari[0].args[4]["hata"])

    def test_dosya_yoksa_bos_liste_doner(self):
        self.assertEqual(defter.oku(), [])

    def test_yazim_basarisiz_olunca_hata_yukselir(self):
        """DEFTER_KLASORU yerine bir DOSYA konursa mkdir/open patlar: izin hatasi yerine
        cross-platform garanti bir yazim-basarisizligi simulasyonu."""
        defter.DEFTER_KLASORU = Path(self._gecici.name) / "engel"
        defter.DEFTER_KLASORU.parent.mkdir(parents=True, exist_ok=True)
        defter.DEFTER_KLASORU.write_text("ben bir dosyayim, klasor degilim")

        with self.assertRaises(OSError):
            defter.yaz({"soru": "x", "cevap": "y"})

    def test_isle_ucuncu_ad_olarak_var_ve_patlamiyor(self):
        """R2 (K16): sozlesmedeki uc ad (yaz/oku/isle) acik. sqlite f4'te doguyor, bugun
        isle'nin gorevi sadece cagrilinca patlamamak (bkz. defter.py dosya ici gerekce)."""
        defter.isle()  # no-op, hata firlatmaz


if __name__ == "__main__":
    unittest.main()
