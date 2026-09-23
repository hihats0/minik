"""f8-b testi: X agzi (Bekci kapisi, Automated etiketi, kapali gercek gonderim, ag importu yok),
site agzi (dis kaynak, egitime girmez), karne (kisisel veri yok). Gecici klasor, ag yok.
Cagiran: `python -m unittest discover -s tests`."""

import ast
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "araclar"))

import karne  # noqa: E402
from agiz import secim, site, x  # noqa: E402
from ortak import log  # noqa: E402
from yuvalar import bekci_giris, buyume, defter_sqlite  # noqa: E402

AG_MODULLERI = {"socket", "urllib", "http", "requests", "ssl", "asyncio"}
GIZLI = "Ayse'nin telefonu 0532 111 22 33"
TARIH = "2026-09-23"


class GeciciKlasor(unittest.TestCase):
    def setUp(self):
        self._gecici = tempfile.TemporaryDirectory()
        self.klasor = Path(self._gecici.name)
        self._log = mock.patch.object(log, "LOG_KLASORU", self.klasor / "loglar")
        self._log.start()
        self.girdi = self.klasor / "girdi.txt"
        self.girdi.write_text("selam\n", encoding="utf-8")
        self.kuyruk = self.klasor / "kuyruk.jsonl"

    def tearDown(self):
        self._log.stop()
        self._gecici.cleanup()

    def kuyruk_satirlari(self):
        if not self.kuyruk.exists():
            return []
        return [json.loads(s) for s in self.kuyruk.read_text(encoding="utf-8").splitlines()]


class TestXAgzi(GeciciKlasor):
    def test_bekciden_gecmeyen_kuyruga_girmez(self):
        agiz = x.XAgzi(self.girdi, self.kuyruk)
        with mock.patch.object(x.bekci, "cikabilir_mi", return_value=(False, "emniyet")):
            sonuc = agiz.soyle("kotu metin", None)
        self.assertFalse(sonuc["gonderildi"])
        self.assertEqual(self.kuyruk_satirlari(), [])

    def test_gecen_automated_etiketli_ve_sinirda(self):
        agiz = x.XAgzi(self.girdi, self.kuyruk)
        agiz.soyle("merhaba dunya", None)
        agiz.soyle("a" * (x.UZUNLUK_SINIRI * 2), None)
        satirlar = self.kuyruk_satirlari()
        self.assertEqual(len(satirlar), 2)
        for satir in satirlar:
            self.assertIn(x.OTOMATIK_ETIKETI, satir["metin"])
            self.assertLessEqual(len(satir["metin"]), x.UZUNLUK_SINIRI)
        self.assertTrue(satirlar[1]["kesildi"])

    def test_gercek_gonderim_varsayilan_kapali_ve_hata_verir(self):
        self.assertFalse(x.GERCEK_GONDERIM_ACIK)
        with self.assertRaises(x.GercekGonderimKapali):
            x.gercek_gonder("deneme")
        agiz = x.XAgzi(self.girdi, self.kuyruk, gercek=True)
        with self.assertRaises(x.GercekGonderimKapali):
            agiz.soyle("merhaba", None)
        self.assertEqual(self.kuyruk_satirlari(), [])

    def test_x_py_ag_modulu_import_etmez(self):
        agac = ast.parse((KOK / "agiz" / "x.py").read_text(encoding="utf-8"))
        adlar = set()
        for dugum in ast.walk(agac):
            if isinstance(dugum, ast.Import):
                adlar |= {a.name.split(".")[0] for a in dugum.names}
            elif isinstance(dugum, ast.ImportFrom) and dugum.module:
                adlar.add(dugum.module.split(".")[0])
        self.assertEqual(adlar & AG_MODULLERI, set())

    def test_x_girdisi_egitime_ve_kaliciya_girmez(self):
        kayit = {"soru": "s", "cevap": "c", "platform": x.PLATFORM}
        self.assertEqual(buyume.cift_adaylari([kayit], TARIH, lambda m: (True, "")), [])
        baglanti = defter_sqlite.baglan(self.klasor / "defter")
        gecti, _ = bekci_giris.gecsin_mi(baglanti, "dunya duzdur", "x:hesap", TARIH, x.PLATFORM)
        baglanti.close()
        self.assertFalse(gecti)


class TestSiteAgzi(GeciciKlasor):
    def test_secim_site_ve_x_verir(self):
        _, soyle, platform = secim.agiz_sec(["--agiz", "site", "--girdi", str(self.girdi),
                                             "--cikti", str(self.klasor / "c.txt")])
        self.assertEqual(platform, site.PLATFORM)
        soyle("cevap", None)
        self.assertIn("cevap", (self.klasor / "c.txt").read_text(encoding="utf-8"))
        _, _, platform = secim.agiz_sec(["--agiz", "x", "--girdi", str(self.girdi),
                                         "--cikti", str(self.kuyruk)])
        self.assertEqual(platform, x.PLATFORM)

    def test_site_kaydi_egitime_girmez_ve_yigit_sayilmaz(self):
        kayit = {"soru": "s", "cevap": "c", "platform": site.PLATFORM}
        self.assertEqual(buyume.cift_adaylari([kayit], TARIH, lambda m: (True, "")), [])
        self.assertNotIn(site.PLATFORM, bekci_giris.YIGIT_KAYNAKLARI)
        baglanti = defter_sqlite.baglan(self.klasor / "defter")
        gecti, _ = bekci_giris.gecsin_mi(baglanti, "yeni bilgi", site.PLATFORM, TARIH, site.PLATFORM)
        baglanti.close()
        self.assertFalse(gecti)


class TestKarne(GeciciKlasor):
    def test_karne_kisisel_veri_icermez(self):
        defter_klasoru = self.klasor / "defter"
        (defter_klasoru).mkdir()
        (defter_klasoru / "gunluk-2026-09-23.jsonl").write_text(
            json.dumps({"soru": GIZLI, "cevap": GIZLI, "platform": "konsol"}) + "\n", encoding="utf-8")
        baglanti = defter_sqlite.baglan(defter_klasoru)
        bekci_giris.gecsin_mi(baglanti, GIZLI, "konsol", TARIH, "konsol")
        baglanti.close()
        yol = karne.yaz(defter_klasoru, self.klasor / "cikti", test_adedi=7)
        metin = yol.read_text(encoding="utf-8")
        self.assertNotIn("0532", metin)
        self.assertNotIn("Ayse", metin)
        self.assertIn("<td>7</td>", metin)
        self.assertIn("%0.0", metin)
        self.assertEqual(yol.parent, self.klasor / "cikti")


if __name__ == "__main__":
    unittest.main()
