"""X okuma agzi testleri, agsiz ve tarayicisiz: sahte acici ile okundu, giris, oturum, kisitlama, CAPTCHA, profil kilidi, hiz siniri.
Cagiran: python -m pytest -q (ya da unittest discover -s tests)."""

import unittest
from unittest.mock import patch

from agiz import x_oku

EV = "https://x.com/home"
PROFIL_SAYFASI = "https://x.com/ornek"


def gozlem(url, metin="", tweetler=None):
    return {"url": url, "metin": metin, "tweetler": tweetler or []}


class XOku(unittest.TestCase):
    def setUp(self):
        x_oku._son_istek[0] = float("-inf")

    def test_tweetler_okundu_sayilir(self):
        sonuc = x_oku.oku(EV, acici=lambda a: gozlem(EV, "Ana sayfa", ["bir", "iki"]))
        self.assertEqual(sonuc["durum"], "okundu")
        self.assertEqual((sonuc["sayi"], sonuc["metinler"]), (2, ["bir", "iki"]))

    def test_giris_ekrani_giris_istedi(self):
        sonuc = x_oku.oku(PROFIL_SAYFASI, acici=lambda a: gozlem("https://x.com/i/flow/login", "Sign in to X"))
        self.assertEqual((sonuc["durum"], sonuc["tur"]), ("engel", "giris_istedi"))
        self.assertEqual(sonuc["isaret"], "/i/flow/login")

    def test_ev_istenip_girise_yonlenince_oturum_dusmus(self):
        sonuc = x_oku.oku(EV, acici=lambda a: gozlem("https://x.com/login?redirect_after_login=%2Fhome"))
        self.assertEqual(sonuc["tur"], "oturum_dusmus")

    def test_giris_yap_metni_oturum_dusmus(self):
        sonuc = x_oku.oku(PROFIL_SAYFASI, acici=lambda a: gozlem(PROFIL_SAYFASI, "Hesabın yok mu? Giriş yap"))
        self.assertEqual((sonuc["tur"], sonuc["isaret"]), ("oturum_dusmus", "giriş yap"))

    def test_kisitlama_turkce_ve_ingilizce(self):
        for metin in ["Giriş erişimin geçici olarak kısıtlandı.", "Your account is temporarily restricted"]:
            sonuc = x_oku.oku(EV, acici=lambda a: gozlem(EV, metin))
            self.assertEqual(sonuc["tur"], "kisitlandi", metin)
            x_oku._son_istek[0] = float("-inf")

    def test_captcha_url_ve_metin(self):
        sonuc = x_oku.oku(EV, acici=lambda a: gozlem("https://x.com/account/access"))
        self.assertEqual((sonuc["tur"], sonuc["isaret"]), ("captcha", "/account/access"))
        self.assertEqual(x_oku.siniflandir(EV, gozlem(EV, "Authenticate your account"))["tur"], "captcha")

    def test_profil_kilitli_zorla_kapatmaz(self):
        def kilitli(adres):
            raise RuntimeError("launch_persistent_context: The user data directory is already in use")
        sonuc = x_oku.oku(EV, acici=kilitli)
        self.assertEqual((sonuc["durum"], sonuc["tur"]), ("engel", "profil_kilitli"))

    def test_baska_tarayici_hatasi_bilinmeyen_ve_gorunur(self):
        def patlar(adres):
            raise RuntimeError("Chrome bulunamadi")
        sonuc = x_oku.oku(EV, acici=patlar)
        self.assertEqual(sonuc["tur"], "bilinmeyen")
        self.assertIn("Chrome bulunamadi", sonuc["isaret"])

    def test_isaretsiz_bos_sayfa_bilinmeyen(self):
        self.assertEqual(x_oku.siniflandir(EV, gozlem(EV, "Bir seyler ters gitti"))["tur"], "bilinmeyen")

    def test_ust_uste_istek_bekletilir(self):
        with patch.object(x_oku.time, "sleep") as uyu:
            x_oku.oku(EV, acici=lambda a: gozlem(EV, "", ["t"]))
            x_oku.oku(EV, acici=lambda a: gozlem(EV, "", ["t"]))
        self.assertEqual(uyu.call_count, 1)
        self.assertLessEqual(uyu.call_args[0][0], x_oku.ISTEK_ARALIGI_SN)

    def test_acici_tek_adres_ile_cagrilir(self):
        cagrilar = []
        x_oku.oku(PROFIL_SAYFASI, acici=lambda a: cagrilar.append(a) or gozlem(a, "", ["t"]))
        self.assertEqual(cagrilar, [PROFIL_SAYFASI])
