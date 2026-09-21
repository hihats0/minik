"""Kafa yuvasinin sozlesme testi (K3): GPU'suz, agsiz, sahte HTTP ile koser.
Cagiran: `python -m unittest discover -s tests`."""

import json
import os
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ortak.ayar import (
    ALT_ESIK,
    KAFA_SICAKLIK,
    KAFA_TOP_P,
    KAFA_ZAMAN_ASIMI_SN,
    MOD_UYANIK,
    MOD_YORGUN,
    MOD_ZORLA_DEGISKENI,
    UST_ESIK,
)
from yuvalar import kafa

HORMON_DINLENME = {"dopamin": 20, "noradrenalin": 20, "serotonin": 50, "kortizol": 10,
                    "oksitosin": 30, "melatonin": 10, "merak": 40}

SAHTE_CEVAP = {"choices": [{"message": {"content": "merhaba"}}], "usage": {"completion_tokens": 3}}


class SahteYanit:
    """urllib.request.urlopen'in dondurdugu context manager nesnesini taklit eder."""

    def __init__(self, govde_json):
        self._govde = json.dumps(govde_json).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return self._govde


def _sahte_urlopen_kur(yakalanan):
    """Giden istegi yakalayan sahte urlopen dondurur (govde ve timeout kaydedilir)."""
    def sahte_urlopen(istek, timeout):
        yakalanan["govde"] = json.loads(istek.data.decode("utf-8"))
        yakalanan["timeout"] = timeout
        return SahteYanit(SAHTE_CEVAP)
    return sahte_urlopen


class TestKafa(unittest.TestCase):

    def test_istek_alaninda_soru_var(self):
        """Giden istegin son mesaji sorulan soru olmali."""
        yakalanan = {}
        with patch("yuvalar.kafa.urllib.request.urlopen", side_effect=_sahte_urlopen_kur(yakalanan)):
            kafa.dusun("Bugun hava nasil?", [])
        self.assertEqual(yakalanan["govde"]["messages"][-1]["content"], "Bugun hava nasil?")

    def test_onceki_baglam_istege_giriyor(self):
        """dusun'a verilen onceki mesajlar govdede korunmali, sadece yeni soru eklenmeli."""
        yakalanan = {}
        onceki = [{"role": "user", "content": "ilk soru"}, {"role": "assistant", "content": "ilk cevap"}]
        with patch("yuvalar.kafa.urllib.request.urlopen", side_effect=_sahte_urlopen_kur(yakalanan)):
            kafa.dusun("ikinci soru", onceki)
        self.assertEqual(len(yakalanan["govde"]["messages"]), 3)
        self.assertEqual(yakalanan["govde"]["messages"][0]["content"], "ilk soru")

    def test_ornekleme_ayarlari_govdeye_giriyor(self):
        """Sicaklik ve top_p, ortak/ayar.py'daki sabitlerle birebir ayni gitmeli."""
        yakalanan = {}
        with patch("yuvalar.kafa.urllib.request.urlopen", side_effect=_sahte_urlopen_kur(yakalanan)):
            kafa.dusun("soru", [])
        self.assertEqual(yakalanan["govde"]["temperature"], KAFA_SICAKLIK)
        self.assertEqual(yakalanan["govde"]["top_p"], KAFA_TOP_P)

    def test_zaman_asimi_sabitten_geliyor(self):
        """urlopen'e gecen timeout, koddaki ciplak sayi degil ortak/ayar.py sabiti olmali."""
        yakalanan = {}
        with patch("yuvalar.kafa.urllib.request.urlopen", side_effect=_sahte_urlopen_kur(yakalanan)):
            kafa.dusun("soru", [])
        self.assertEqual(yakalanan["timeout"], KAFA_ZAMAN_ASIMI_SN)

    def test_sunucu_kapaliyken_hata_yukselir(self):
        """Sunucu erisilemezse hata yutulmaz, oldugu gibi yukselir."""
        def sahte_urlopen(istek, timeout):
            raise urllib.error.URLError("baglanti reddedildi")

        with patch("yuvalar.kafa.urllib.request.urlopen", side_effect=sahte_urlopen):
            with self.assertRaises(urllib.error.URLError):
                kafa.dusun("soru", [])

    def test_cevap_dogru_ayristiriliyor(self):
        """Sahte sunucunun dondurdugu icerik oldugu gibi geri gelmeli."""
        with patch("yuvalar.kafa.urllib.request.urlopen", side_effect=_sahte_urlopen_kur({})):
            cevap = kafa.dusun("soru", [])
        self.assertEqual(cevap, "merhaba")


class TestKafaHormonModu(unittest.TestCase):
    """Kademe 1 (f3-b): hormon -> ornekleme donusumu, cift esikli mod (spec 3.6.2, K6)."""

    def setUp(self):
        kafa.ONCEKI_MOD = MOD_UYANIK

    def tearDown(self):
        kafa.ONCEKI_MOD = MOD_UYANIK

    def test_ust_esigi_gecmeden_yorgun_moda_girilmez(self):
        """Tam esikte (UST_ESIK) moda girer, bir tik altinda girmez: sinir UST_ESIK'te."""
        self.assertEqual(kafa._mod_hesapla(UST_ESIK - 0.1, MOD_UYANIK), MOD_UYANIK)
        self.assertEqual(kafa._mod_hesapla(UST_ESIK, MOD_UYANIK), MOD_YORGUN)

    def test_histerezis_alt_esigin_altina_inmeden_mod_geri_donmez(self):
        """Asil test bu: iki esigin ARASINDA (UST_ESIK'in altinda ama ALT_ESIK'in ustunde)
        deger kalirsa mod yorgun kalmali. Tek esik olsaydi UST_ESIK'in hemen altina inince
        geri donerdi (araclar/histerezis-olc.py'nin olcttugu fark tam olarak bu)."""
        mod = kafa._mod_hesapla(UST_ESIK, MOD_UYANIK)
        self.assertEqual(mod, MOD_YORGUN)
        mod = kafa._mod_hesapla((UST_ESIK + ALT_ESIK) / 2, mod)
        self.assertEqual(mod, MOD_YORGUN, "iki esigin arasinda mod degismemeli (histerezis)")
        mod = kafa._mod_hesapla(ALT_ESIK + 0.1, mod)
        self.assertEqual(mod, MOD_YORGUN, "ALT_ESIK'in henuz ustunde, hala yorgun kalmali")
        mod = kafa._mod_hesapla(ALT_ESIK, mod)
        self.assertEqual(mod, MOD_UYANIK, "ALT_ESIK'e (ve altina) inince uyanik moda doner")

    def test_noradrenalin_sicakligi_ve_top_pyi_surekli_yukseltir(self):
        """SUREKLI ayar: esik yok, deger arttikca sicaklik ve top_p duzgun artar."""
        dusuk = {**HORMON_DINLENME, "noradrenalin": 0}
        yuksek = {**HORMON_DINLENME, "noradrenalin": 100}
        ayar_dusuk, _ = kafa._ornekleme_ayarlari(dusuk)
        ayar_yuksek, _ = kafa._ornekleme_ayarlari(yuksek)
        self.assertLess(ayar_dusuk["temperature"], ayar_yuksek["temperature"])
        self.assertLess(ayar_dusuk["top_p"], ayar_yuksek["top_p"])

    def test_serotonin_max_tokeni_kortizol_repeat_penaltyi_surekli_surer(self):
        dusuk = {**HORMON_DINLENME, "serotonin": 0, "kortizol": 0}
        yuksek = {**HORMON_DINLENME, "serotonin": 100, "kortizol": 100}
        ayar_dusuk, _ = kafa._ornekleme_ayarlari(dusuk)
        ayar_yuksek, _ = kafa._ornekleme_ayarlari(yuksek)
        self.assertLess(ayar_dusuk["max_tokens"], ayar_yuksek["max_tokens"])
        self.assertLess(ayar_dusuk["repeat_penalty"], ayar_yuksek["repeat_penalty"])

    def test_yorgun_modda_sicaklik_ve_max_token_dusurulur(self):
        """Rapor: 'melatonin -> n_predict asagi + sicaklik asagi (yorgun Minik kisa ve
        donuk konusur)'. Ayni noradrenalin/serotonin ile uyanik/yorgun karsilastirilir."""
        uyanik = {**HORMON_DINLENME, "melatonin": 10}
        yorgun = {**HORMON_DINLENME, "melatonin": UST_ESIK}
        ayar_uyanik, mod_uyanik = kafa._ornekleme_ayarlari(uyanik)
        kafa.ONCEKI_MOD = MOD_UYANIK
        ayar_yorgun, mod_yorgun = kafa._ornekleme_ayarlari(yorgun)
        self.assertEqual(mod_uyanik, MOD_UYANIK)
        self.assertEqual(mod_yorgun, MOD_YORGUN)
        self.assertLess(ayar_yorgun["temperature"], ayar_uyanik["temperature"])
        self.assertLess(ayar_yorgun["max_tokens"], ayar_uyanik["max_tokens"])

    def test_mod_zorlama_ortam_degiskeni_hesaplanani_ezer(self):
        """f3-c'nin 'ayni soru, iki mod' kosusu bu yolu kullanacak: dogal olarak uyanik
        cikacak bir hormon durumunu ortam degiskeniyle yorguna zorluyoruz."""
        with mock.patch.dict(os.environ, {MOD_ZORLA_DEGISKENI: MOD_YORGUN}):
            _, mod = kafa._ornekleme_ayarlari(HORMON_DINLENME)
        self.assertEqual(mod, MOD_YORGUN)

    def test_hormonsuz_cagri_f0_sabitlerini_kullanir(self):
        """hormon_degerleri verilmezse (eski cagiranlar, testler) f0'in olctugu sabit
        ayarlar degismeden kullanilir: geriye donuk uyumluluk."""
        ayarlar, mod = kafa._ornekleme_ayarlari(None)
        self.assertEqual(ayarlar["temperature"], KAFA_SICAKLIK)
        self.assertEqual(ayarlar["top_p"], KAFA_TOP_P)
        self.assertEqual(mod, MOD_UYANIK)


if __name__ == "__main__":
    unittest.main()
