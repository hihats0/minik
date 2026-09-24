"""Chrome'lu DDG kaynagi testleri, agsiz ve tarayicisiz: sahte acici ile okuma, hata cevirme, engel ve ara() baglantisi.
Cagiran: python -m unittest discover -s tests."""

import functools
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from agiz import web, web_chrome

DDG_SAYFA = """<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fwww.ornek.com%2Fa">Baslik</a>
<a class="result__snippet" href="x">Ozet cumlesi.</a>"""
CAPTCHA_SAYFA = '<form id="challenge-form">Select all squares containing a duck</form>'


class ChromeOku(unittest.TestCase):
    def test_sahte_acici_sonucu_doner(self):
        self.assertEqual(web_chrome.oku("u", acici=lambda a: (200, DDG_SAYFA)), (200, DDG_SAYFA))

    def test_tarayici_hatasi_urlerror_olur(self):
        def patlar(adres):
            raise RuntimeError("Chrome bulunamadi")
        with self.assertRaises(urllib.error.URLError):
            web_chrome.oku("u", acici=patlar)


class DdgChromeKaynagi(unittest.TestCase):
    def setUp(self):
        web._son_istek.clear()

    def test_ara_ddg_icin_chrome_okuyucu_kullanir(self):
        ac = MagicMock(return_value=(200, DDG_SAYFA))
        chrome_getir = functools.partial(web.getir, okuyucu=lambda a: web_chrome.oku(a, acici=ac))
        with patch.object(web, "DDG_GETIRICI", chrome_getir),                 patch.object(web, "getir", side_effect=urllib.error.URLError("agsiz")):
            kayitlar = web.ara("fotosentez")
        self.assertEqual([k["kaynak"] for k in kayitlar], ["ornek.com"])
        self.assertIn("html.duckduckgo.com", ac.call_args[0][0])

    def test_captcha_engel_sayilir_asilmaz(self):
        with self.assertRaises(web.Engellendi):
            web.getir("https://html.duckduckgo.com/html/?q=x", okuyucu=lambda a: (200, CAPTCHA_SAYFA))
