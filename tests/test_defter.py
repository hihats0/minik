"""Defter sozlesme testi (K3): agsiz, GPU'suz. Sona-ekleme, geri okuma, bozuk satirin tek
basina dusmesi ve yazim hatasinin yukselmesini dogrular. Gecici klasor kullanir, gercek
defter/ klasorune dokunmaz.
Cagiran: `python -m unittest discover -s tests`."""

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
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

    def _gun_dosyasi_yaz(self, gun, satirlar):
        """Test yardimcisi: verilen tarih icin gun dosyasini elle yazar (defter.yaz'i
        bugunun disina zorlayamayiz, o yuzden dosyayi dogrudan olustururuz)."""
        dosya = defter.DEFTER_KLASORU / f"gunluk-{gun:%Y-%m-%d}.jsonl"
        dosya.parent.mkdir(parents=True, exist_ok=True)
        with dosya.open("w", encoding="utf-8") as f:
            for satir in satirlar:
                f.write(satir if isinstance(satir, str) else json.dumps(satir, ensure_ascii=False))
                f.write("\n")
        return dosya

    def test_oku_gun_dosyasini_asar_dunku_konu_geri_gelir(self):
        """Fazin gercek olcutu (spec 8.1): yeniden baslatmadan sonra dunku konu geri gelmeli.
        Dunku ve bugunku gun dosyalari birlikte, eskiden yeniye sirali dondurulmeli."""
        dun = datetime.now().astimezone() - timedelta(days=1)
        self._gun_dosyasi_yaz(dun, [
            {"soru": "dun1", "cevap": "cevapdun1"},
            {"soru": "dun2", "cevap": "cevapdun2"},
        ])
        defter.yaz({"soru": "bugun1", "cevap": "cevapbugun1"})

        kayitlar = defter.oku(kac_tane=3)

        self.assertEqual([k["soru"] for k in kayitlar], ["dun1", "dun2", "bugun1"])

    def test_oku_bugun_yetince_dunku_dosya_hic_acilmaz(self):
        """Istenen sayi bugunku dosyadan karsilaniyorsa dunku dosyaya hic dokunulmamali.
        Dunku dosyaya bozuk bir satir koyup okunmadigini (satir_atla loglanmadigini) dogrular."""
        dun = datetime.now().astimezone() - timedelta(days=1)
        self._gun_dosyasi_yaz(dun, ["BU_SATIR_OKUNMAMALI gecersiz json"])
        defter.yaz({"soru": "bugun1", "cevap": "cevap1"})
        defter.yaz({"soru": "bugun2", "cevap": "cevap2"})

        with mock.patch("yuvalar.defter.log.yaz") as sahte_log:
            kayitlar = defter.oku(kac_tane=2)

        self.assertEqual([k["soru"] for k in kayitlar], ["bugun1", "bugun2"])
        atlama_cagrilari = [c for c in sahte_log.call_args_list if c.args[1] == "satir_atla"]
        self.assertEqual(atlama_cagrilari, [])
        oku_cagrisi = [c for c in sahte_log.call_args_list if c.args[1] == "oku"][0]
        self.assertEqual(oku_cagrisi.args[4]["dosya_sayisi"], 1)


if __name__ == "__main__":
    unittest.main()
