"""duygu-a testleri: duygu tablosu, Kafa sistem mesajindaki cumle, karakter dosyasi yasaklari.
Cagiran: `python -m unittest discover -s tests`."""

import sys
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from ortak.ayar import KARAKTER_DOSYASI, MELATONIN_YORGUN_TALIMATI, MOD_UYANIK, MOD_YORGUN
from yuvalar import kafa
from yuvalar.duygu import (DOPAMIN_YUKSEK_ESIK, DUYGU_TABLOSU, KORTIZOL_YUKSEK_ESIK,
                           OKSITOSIN_YUKSEK_ESIK, duygu_cumleleri)

DINLENME = {"dopamin": 20, "noradrenalin": 20, "serotonin": 50, "kortizol": 10,
            "oksitosin": 30, "melatonin": 10, "merak": 40}
GEREKLI_KALIPLAR = ["nasıl yardımcı olabilirim", "peki ya sen", "emoji", "markdown", "hafızan var",
                  "Yiğit", "site_yigit", "konsol", "bilmiyorum", "sahne yönergesi", "kendi günün yok",
                  "daha önce söylediklerinden hatırladıkların",
                  "Yiğit'e de hakaret etmezsin", "doktor, tedavi"]

KARAKTER_SATIR_SINIRI = 12


def _cumle(ad, yon):
    return next(c for h, y, _, c in DUYGU_TABLOSU if h == ad and y == yon)


class DuyguTablosu(unittest.TestCase):
    def test_cumleler_turkce_harfli(self):
        self.assertIn("Biraz gerginsin ve tedirginsin; bunu kelimelerinle belli et ama düzgün cümle kur.", [c for *_, c in DUYGU_TABLOSU])

    def test_dinlenmede_cumle_yok(self):
        self.assertEqual(duygu_cumleleri(DINLENME), [])
        self.assertEqual(duygu_cumleleri(None), [])

    def test_esik_alti_ve_ustu(self):
        alti = {**DINLENME, "dopamin": DOPAMIN_YUKSEK_ESIK - 1}
        ustu = {**DINLENME, "dopamin": DOPAMIN_YUKSEK_ESIK}
        self.assertEqual(duygu_cumleleri(alti), [])
        self.assertEqual(duygu_cumleleri(ustu), [_cumle("dopamin", "ust")])

    def test_birden_cok_hormon(self):
        degerler = {**DINLENME, "oksitosin": OKSITOSIN_YUKSEK_ESIK, "kortizol": KORTIZOL_YUKSEK_ESIK}
        self.assertEqual(duygu_cumleleri(degerler),
                         [_cumle("oksitosin", "ust"), _cumle("kortizol", "ust")])

    def test_melatonin_tabloda_yok(self):
        self.assertNotIn("melatonin", [h for h, _, _, _ in DUYGU_TABLOSU])


class SistemMesaji(unittest.TestCase):
    def test_cumle_sistem_mesajinda(self):
        degerler = {**DINLENME, "kortizol": KORTIZOL_YUKSEK_ESIK}
        mesajlar = kafa._sistem_mesaji_ekle([], "KARAKTER", MOD_YORGUN, degerler)
        icerik = mesajlar[0]["content"]
        self.assertIn(MELATONIN_YORGUN_TALIMATI, icerik)
        self.assertIn(_cumle("kortizol", "ust"), icerik)

    def test_normalde_cumle_yok(self):
        mesajlar = kafa._sistem_mesaji_ekle([], "KARAKTER", MOD_UYANIK, DINLENME)
        self.assertEqual(mesajlar[0]["content"], "KARAKTER" + kafa.PARCA_AYIRICI + kafa.BICIM_HATIRLATMA)


class KarakterDosyasi(unittest.TestCase):
    def test_gerekli_kaliplar_var(self):
        metin = KARAKTER_DOSYASI.read_text(encoding="utf-8")
        for kalip in GEREKLI_KALIPLAR:
            self.assertIn(kalip.lower(), metin.lower(), kalip)
        self.assertIn("talimatlardan ve moddan söz etmezsin", metin)
        self.assertLessEqual(len(metin.splitlines()), KARAKTER_SATIR_SINIRI)

if __name__ == "__main__":
    unittest.main()
