"""emoji-a testi: duz_metin temizligi ve minik.py'nin Kafa'ya giden gecmisi temiz kurdugu.
Cagiran: `python -m unittest discover -s tests`."""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import minik
from ortak import duz_metin

KIRLI = "Merhaba Yiğit! 😊❤️\nBeni **unutmadığın** için *teşekkürler* — demek ki çay."
TEMIZ = "Merhaba Yiğit!\nBeni unutmadığın için teşekkürler, demek ki çay."


class SahteHormon:
    def oku(self):
        return {"dopamin": 0, "melatonin": 0}

    def guncelle(self, olay, siddet):
        pass


class TestDuzMetin(unittest.TestCase):
    def test_emoji_markdown_uzun_tire_gider(self):
        self.assertEqual(duz_metin.temizle(KIRLI), TEMIZ)

    def test_duz_metin_degismez(self):
        self.assertEqual(duz_metin.temizle(TEMIZ), TEMIZ)

    def test_defter_gecmisi_kafaya_temiz_gider(self):
        kayitlar = [{"soru": "selam", "cevap": KIRLI}]
        with mock.patch.object(minik.defter, "oku", return_value=kayitlar):
            baglam = minik._gecmisten_baglam_yukle()
        self.assertEqual(baglam[1], {"role": "assistant", "content": TEMIZ})

    def test_yeni_cevap_temizlenir_ve_baglama_temiz_girer(self):
        giden = []

        def sahte_dusun(soru, baglam, hormon):
            giden.append(list(baglam))
            return KIRLI, 1.0

        baglam = [{"role": "user", "content": "a"}, {"role": "assistant", "content": TEMIZ}]
        with mock.patch.object(minik.calgici_tani, "baglam_mesaji", return_value=None):
            cevap, basarili = minik._tur_isle("çay içtim", baglam, sahte_dusun, SahteHormon())
        self.assertTrue(basarili)
        self.assertEqual(cevap, TEMIZ)
        self.assertEqual(baglam[-1]["content"], TEMIZ)
        self.assertEqual(giden[0][1]["content"], TEMIZ)


if __name__ == "__main__":
    unittest.main()
