"""f10-c testleri, agsiz: kisa iddia cikarma, kurum eslemesi (K34 A) ve zaman asiminda bir kez yeniden deneme.
Cagiran: python -m unittest discover -s tests."""

import unittest
import urllib.error
from unittest import mock

from agiz import web, web_ek, web_iddia
from yuvalar import iddia_esle


class KisaIddia(unittest.TestCase):
    def test_ilk_cumle_ve_sayili_cumle(self):
        metin = ("Mount Everest is Earth's highest mountain above sea level. It lies in the Himalayas. "
                 "Its height is 8,849 m, set in 2020. Another line with 5 numbers.")
        self.assertEqual(web_iddia.kisa_iddia(metin), "Mount Everest is Earth's highest mountain above sea "
                         "level. Its height is 8,849 m, set in 2020.")

    def test_ilk_cumlede_sayi_varsa_tek_cumle(self):
        metin = "The speed of light is 299,792,458 m/s exactly. It is a constant of nature too."
        self.assertEqual(web_iddia.kisa_iddia(metin), "The speed of light is 299,792,458 m/s exactly.")

    def test_cumlesiz_metin_kendisi(self):
        self.assertEqual(web_iddia.kisa_iddia("  biyolojik   surec "), "biyolojik surec")

    def test_wikidata_etiketle_cumle(self):
        s = web_ek.wikidata_ayristir('{"search": [{"label": "light", "description": "visible radiation", "url": "//x"}]}')
        self.assertEqual(s[0]["ozet"], "light: visible radiation")


class Kurum(unittest.TestCase):
    def test_wikimedia_tek_kurum(self):
        alanlar = ["tr.wikipedia.org", "en.wikipedia.org", "wikidata.org"]
        self.assertEqual({iddia_esle.kurum(a) for a in alanlar}, {"wikimedia"})
        self.assertEqual(iddia_esle.kurum("nasa.gov"), "nasa.gov")
        self.assertEqual(iddia_esle.kurum("notwikipedia.org"), "notwikipedia.org")


class YenidenDeneme(unittest.TestCase):
    def test_zaman_asiminda_bir_kez_tekrar(self):
        cagri = []
        cevaplar = [urllib.error.URLError(TimeoutError("timed out")), "sayfa"]

        def getirici(adres):
            cagri.append(adres)
            c = cevaplar.pop(0)
            if isinstance(c, Exception):
                raise c
            return c
        with mock.patch.object(web.log, "yaz") as yaz:
            self.assertEqual(web._zaman_asiminda_tekrarla("q", "marginalia", "u", getirici), "sayfa")
        self.assertEqual(len(cagri), 2)
        self.assertEqual(yaz.call_args[0][1], "yeniden_dene")

    def test_ikinci_zaman_asimi_yukselir_baska_hata_tekrarlanmaz(self):
        sayac = []

        def zaman_asimi(_a):
            sayac.append(1)
            raise TimeoutError("timed out")
        with mock.patch.object(web.log, "yaz"):
            self.assertRaises(TimeoutError, web._zaman_asiminda_tekrarla, "q", "m", "u", zaman_asimi)
        self.assertEqual(len(sayac), 2)
        sayac.clear()

        def red(_a):
            sayac.append(1)
            raise urllib.error.URLError("connection refused")
        self.assertRaises(urllib.error.URLError, web._zaman_asiminda_tekrarla, "q", "m", "u", red)
        self.assertEqual(len(sayac), 1)


if __name__ == "__main__":
    unittest.main()
