"""k29-a testi: karne yayin taramasi temiz sayfayi yazar, kisisel veri iceren sayfada durur.
Cagiran: `python -m unittest discover -s tests`."""

import sys
import tempfile
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "araclar"))

import karne_yayin  # noqa: E402

# Gercek ad-soyad yerel listede; testte sahte kelime kullanilir.
SAHTE_LISTE = [("yerel liste", "ornekad")]
TEMIZ = "<h1>Minik karne</h1><table><tr><td>Test sayisi</td><td>201</td></tr></table>"
KIRLI_ORNEKLER = {
    "e-posta": "iletisim: biri@ornek.com",
    "yerel liste": "Yazan: ORNEKAD",
    "telefon": "0532 111 22 33",
    "yerel yol": r"C:\Users\x\defter",
    "gizli klasor": "bkz .secrets/anahtar",
    "jwt/supabase anahtari": "eyJhbGciOiJIUzI1NiIsInR5cCI6",
    "kisisel kart": "Sağlık notu",
}


class KarneYayinTesti(unittest.TestCase):
    def test_temiz_sayfa_yazilir(self):
        with tempfile.TemporaryDirectory() as tmp:
            yol = karne_yayin.yayinla(TEMIZ, tmp, SAHTE_LISTE)
            self.assertEqual(yol.read_text(encoding="utf-8"), TEMIZ)

    def test_kirli_sayfa_durur(self):
        for ad, parca in KIRLI_ORNEKLER.items():
            with self.subTest(ad=ad), tempfile.TemporaryDirectory() as tmp:
                self.assertIn(ad, karne_yayin.tara(TEMIZ + parca, SAHTE_LISTE))
                with self.assertRaises(karne_yayin.KisiselVeriHatasi):
                    karne_yayin.yayinla(TEMIZ + parca, tmp, SAHTE_LISTE)
                self.assertFalse((Path(tmp) / karne_yayin.YAYIN_SAYFASI).exists())

    def test_yerel_liste_yoksa_durur(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(karne_yayin.KisiselVeriHatasi):
                karne_yayin.yerel_desenler(Path(tmp) / "yok.txt")

    def test_gercek_karne_temiz(self):
        with tempfile.TemporaryDirectory() as tmp:
            metin = karne_yayin.karne.sayfa_uret(Path(tmp), 7)
            self.assertEqual(karne_yayin.tara(metin), [])


if __name__ == "__main__":
    unittest.main()
