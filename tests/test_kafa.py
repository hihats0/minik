"""Kafa yuvasinin sozlesme testi (K3): GPU'suz, agsiz, sahte HTTP ile koser.
Cagiran: `python -m unittest discover -s tests`."""

import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ortak.ayar import KAFA_SICAKLIK, KAFA_TOP_P, KAFA_ZAMAN_ASIMI_SN
from yuvalar import kafa

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


if __name__ == "__main__":
    unittest.main()
