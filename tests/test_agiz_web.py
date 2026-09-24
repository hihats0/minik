"""Web agzi testleri, agsiz: sahte DuckDuckGo HTML ve Vikipedi JSON ayristirma, hiz siniri, engel, Bekci kaydi.
Cagiran: python -m unittest discover -s tests."""

import json
import sqlite3
import unittest

from agiz import web
from yuvalar import bekci_giris

DDG_SAYFA = """<div><a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.ornek.com%2Fa">Fotosentez</a>
<a class="result__snippet" href="x">Bitkiler <b>isik</b> ile besin yapar.</a></div>
<div><a class="result__a" href="https://duckduckgo.com/y.js?ad=1">Reklam</a></div>"""
VIKI_JSON = json.dumps({"query": {"pages": {
    "9": {"index": 2, "title": "Klorofil", "extract": "Klorofil yesil bir pigmenttir."},
    "5": {"index": 1, "title": "Fotosentez", "extract": "Fotosentez  bitkilerin isikla besin yapmasidir. Ek cumle."}}}})
TARIH = "2026-09-23"


class Ayristirma(unittest.TestCase):
    def test_ddg(self):
        s = web.ddg_ayristir(DDG_SAYFA)
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0]["adres"], "https://www.ornek.com/a")
        self.assertEqual(s[0]["ozet"], "Bitkiler isik ile besin yapar.")

    def test_viki(self):
        s = web.viki_ayristir(VIKI_JSON)
        self.assertEqual(s[0]["ozet"], "Fotosentez bitkilerin isikla besin yapmasidir.")
        self.assertTrue(s[0]["adres"].startswith("https://tr.wikipedia.org/wiki/"))

    def test_engel(self):
        self.assertTrue(web.engel_mi(202, ""))
        self.assertTrue(web.engel_mi(200, '<div class="anomaly-modal">'))
        self.assertFalse(web.engel_mi(200, DDG_SAYFA))


class HizSiniri(unittest.TestCase):
    def test_ayni_alan_bekler_farkli_beklemez(self):
        web._son_istek.clear()
        uykular = []
        saat = iter([10.0, 10.2, 11.0, 10.3]).__next__
        web.bekle("a.com", saat, uykular.append)
        web.bekle("a.com", saat, uykular.append)
        web.bekle("b.com", lambda: 10.3, uykular.append)
        self.assertEqual(len(uykular), 1)
        self.assertAlmostEqual(uykular[0], 0.8)


class BekciKaydi(unittest.TestCase):
    def test_kayit_bicimi_ve_uc_agiz(self):
        k = web.kayda_cevir("fotosentez", {"baslik": "B", "ozet": " Bitki  isik ", "adres": "https://www.a.com/x"})
        self.assertEqual((k["soru"], k["kaynak"], k["platform"]), ("Bitki isik", "a.com", "web"))
        b = sqlite3.connect(":memory:")
        bekci_giris.kur(b)
        kararlar = [bekci_giris.gecsin_mi(b, k["soru"], alan, TARIH, "web")[0]
                    for alan in ("a.com", "a.com", "b.com", "c.com")]
        self.assertEqual(kararlar, [False, False, False, True])


if __name__ == "__main__":
    unittest.main()
