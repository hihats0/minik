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

TEMIZ = "<h1>Minik karne</h1><table><tr><td>Test sayisi</td><td>201</td></tr></table>"
KIRLI_ORNEKLER = {
    "e-posta": "iletisim: biri@ornek.com",
    "soyad": "Yigit <yerel liste>",
    "isim": "<yerel liste>",
    "telefon": "0532 111 22 33",
    "yerel yol": r"C:\Users\x\defter",
    "gizli klasor": "bkz .secrets/anahtar",
    "jwt/supabase anahtari": "eyJhbGciOiJIUzI1NiIsInR5cCI6",
    "kisisel kart": "Sağlık notu",
}


class KarneYayinTesti(unittest.TestCase):
    def test_temiz_sayfa_yazilir(self):
        with tempfile.TemporaryDirectory() as tmp:
            yol = karne_yayin.yayinla(TEMIZ, tmp)
            self.assertEqual(yol.read_text(encoding="utf-8"), TEMIZ)

    def test_kirli_sayfa_durur(self):
        for ad, parca in KIRLI_ORNEKLER.items():
            with self.subTest(ad=ad), tempfile.TemporaryDirectory() as tmp:
                self.assertIn(ad, karne_yayin.tara(TEMIZ + parca))
                with self.assertRaises(karne_yayin.KisiselVeriHatasi):
                    karne_yayin.yayinla(TEMIZ + parca, tmp)
                self.assertFalse((Path(tmp) / karne_yayin.YAYIN_SAYFASI).exists())

    def test_gercek_karne_temiz(self):
        with tempfile.TemporaryDirectory() as tmp:
            metin = karne_yayin.karne.sayfa_uret(Path(tmp), 7)
            self.assertEqual(karne_yayin.tara(metin), [])


if __name__ == "__main__":
    unittest.main()
