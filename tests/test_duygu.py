"""duygu-a testleri: duygu tablosu, Kafa sistem mesajindaki cumle, karakter dosyasi yasaklari,
sohbet sitesinin markdown temizligi (node ile). Cagiran: `python -m unittest discover -s tests`."""

import re
import shutil
import subprocess
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
SITE = KOK / "sohbet-site" / "index.html"
GEREKLI_KALIPLAR = ["nasıl yardımcı olabilirim", "peki ya sen", "emoji", "markdown", "hafızan var",
                  "Yiğit", "site_yigit", "konsol"]


def _cumle(ad, yon):
    return next(c for h, y, _, c in DUYGU_TABLOSU if h == ad and y == yon)


class DuyguTablosu(unittest.TestCase):
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


@unittest.skipUnless(shutil.which("node"), "node yok")
class MarkdownTemizleme(unittest.TestCase):
    def _duz(self, metin):
        html = SITE.read_text(encoding="utf-8")
        fonksiyon = re.search(r"function duzMetin\(metin\) \{.*?\n\}", html, re.S).group(0)
        betik = fonksiyon + "\nprocess.stdout.write(duzMetin(require('fs').readFileSync(0,'utf8')));"
        return subprocess.run(["node", "-e", betik], input=metin, capture_output=True,
                              text=True, encoding="utf-8", check=True).stdout

    def test_isaretler_silinir(self):
        girdi = "## Baslik\n- **kalin** ve *egik* `kod`\n[link](http://a.b)\nsite_yigit_ok"
        self.assertEqual(self._duz(girdi), "Baslik\nkalin ve egik kod\nlink (http://a.b)\nsite_yigit_ok")


if __name__ == "__main__":
    unittest.main()
