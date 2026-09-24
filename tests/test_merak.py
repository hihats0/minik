"""f10-b testleri, agsiz: ek kaynak ayristiricilari, iddia esleme (basit ve sahte Kafa), merak akisi ve uc agiz.
Cagiran: python -m unittest discover -s tests."""

import json
import sqlite3
import unittest

from agiz import web, web_ek
from yuvalar import bekci_giris, iddia_esle, merak

TARIH = "2026-09-24"
IDDIA = "Photosynthesis converts light energy into chemical energy in plants"


def kayit(soru, alan):
    return {"soru": soru, "cevap": "Fotosentez", "kaynak": alan, "adres": f"https://{alan}/x", "platform": "web"}


class EkKaynaklar(unittest.TestCase):
    def test_wikidata_ve_marginalia(self):
        wd = web_ek.wikidata_ayristir(json.dumps({"search": [
            {"label": "photosynthesis", "description": "biological process", "url": "//www.wikidata.org/wiki/Q1"}]}))
        self.assertEqual(web.alan_adi(wd[0]["adres"]), "wikidata.org")
        mg = web_ek.marginalia_ayristir(json.dumps({"results": [
            {"url": "https://ornek.edu/p", "title": "P", "description": "d"}]}))
        self.assertEqual(web.kayda_cevir("q", mg[0])["kaynak"], "ornek.edu")

    def test_en_viki(self):
        s = web_ek.en_viki_ayristir(json.dumps({"query": {"pages": {"1": {"index": 1, "title": "A B",
                                                                           "extract": "A B is a long thing."}}}}))
        self.assertEqual((s[0]["ozet"], s[0]["adres"]), ("A B is a long thing.", "https://en.wikipedia.org/wiki/A_B"))


class Esleme(unittest.TestCase):
    def test_basit_ayni_ve_farkli(self):
        self.assertTrue(iddia_esle.basit_ayni_mi(IDDIA, "In plants, photosynthesis turns light energy into chemical energy."))
        self.assertFalse(iddia_esle.basit_ayni_mi(IDDIA, "Paris is the capital city of France"))

    def test_grupla_alan_sayar(self):
        g = iddia_esle.grupla([kayit(IDDIA, "a.com"), kayit(IDDIA + ".", "a.com"), kayit(IDDIA, "b.org")])
        self.assertEqual((len(g), g[0]["alanlar"]), (1, ["a.com", "b.org"]))

    def test_sahte_kafa(self):
        sorulan = []
        sahte = iddia_esle.kafa_ayni_mi(lambda m: sorulan.append(m) or "Evet.")
        g = iddia_esle.grupla([kayit("bir", "a.com"), kayit("iki", "b.com")], sahte)
        self.assertEqual((len(g), len(sorulan)), (1, 1))


class Akis(unittest.TestCase):
    def calistir(self, alanlar):
        b = sqlite3.connect(":memory:")
        bekci_giris.kur(b)
        yazilan = []
        kabul = merak.ogren(b, "fotosentez", TARIH, ara=lambda s: [kayit(IDDIA, a) for a in alanlar],
                            yaz=yazilan.append)
        return kabul, yazilan

    def test_uc_alan_defter_e_girer(self):
        kabul, yazilan = self.calistir(["a.com", "b.org", "c.net"])
        self.assertEqual((len(kabul), len(yazilan)), (1, 1))
        self.assertEqual(yazilan[0]["kaynak"], "a.com,b.org,c.net")

    def test_ayni_kurum_tek_agiz(self):
        kabul, yazilan = self.calistir(["tr.wikipedia.org", "en.wikipedia.org", "wikidata.org"])
        self.assertEqual((kabul, yazilan), ([], []))
        kabul, _ = self.calistir(["tr.wikipedia.org", "wikidata.org", "b.org", "c.net"])
        self.assertEqual(kabul[0]["agizlar"], ["b.org", "c.net", "wikimedia"])

    def test_iki_alan_girmez(self):
        kabul, yazilan = self.calistir(["a.com", "a.com", "b.org"])
        self.assertEqual((kabul, yazilan), ([], []))


if __name__ == "__main__":
    unittest.main()
