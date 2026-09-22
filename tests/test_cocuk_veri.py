"""D4 cocuk deneyi veri hazirliginin testi: temizleme, dilim/ayrim, fertility, uint16 ikili yazim ve
sinav json'larinin yapisi kucuk ornekte dogrulanir; agsiz, GPU'suz.
Cagiran: `python -m unittest discover tests`."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import sentencepiece as spm

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from cocuk import ikili_yaz, tokenizer_egit, veri_hazirla

SINAV_DIZINI = KOK / "cocuk" / "sinav"
ORNEK_MAKALE = ("Kedi\n\nKedi evcil bir memeli hayvandır ve insanlarla yaşar.\n"
                "| 1990 | 12 | 45 | tablo satırı olan bir artık |\n"
                "Kediler genellikle geceleri daha hareketli olur, gündüz uyurlar.\n"
                "Kaynakça")


class TestTemizleme(unittest.TestCase):
    def test_duzgun_paragraf_kalir(self):
        self.assertTrue(veri_hazirla.temiz_mi("Kedi evcil bir memeli hayvandır ve insanlarla yaşar."))

    def test_baslik_tablo_ve_rakam_atilir(self):
        self.assertFalse(veri_hazirla.temiz_mi("Kaynakça"))
        self.assertFalse(veri_hazirla.temiz_mi("| a | b | c | d | e | f |."))
        self.assertFalse(veri_hazirla.temiz_mi("1990 1991 1992 1993 1994 1995 yil."))
        self.assertFalse(veri_hazirla.temiz_mi("Bu satır nokta ile bitmiyor ama uzun bir satır"))

    def test_makale_paragraflari(self):
        paragraflar = veri_hazirla.makale_paragraflari(ORNEK_MAKALE)
        self.assertEqual(len(paragraflar), 2)
        self.assertTrue(paragraflar[1].startswith("Kediler"))


class TestDilim(unittest.TestCase):
    def test_hedefte_durur_ve_yuzde_bir_ayirir(self):
        makaleler = [ORNEK_MAKALE] * 200  # Makale basina 2 temiz paragraf, 16 kelime.
        with tempfile.TemporaryDirectory() as dizin:
            egitim, dogrulama = Path(dizin, "e.txt"), Path(dizin, "d.txt")
            sayim = veri_hazirla.dilimi_yaz(makaleler, egitim, dogrulama, hedef_kelime=1_000)
            egitim_satir = egitim.read_text(encoding="utf-8").splitlines()
            dogrulama_satir = dogrulama.read_text(encoding="utf-8").splitlines()
        self.assertLess(sayim["makale"], 200)
        self.assertGreaterEqual(sayim["kelime"], 1_000)
        self.assertEqual(len(egitim_satir) + len(dogrulama_satir), sayim["paragraf"])
        self.assertEqual(len(dogrulama_satir), sayim["paragraf"] // 100)


class TestFertility(unittest.TestCase):
    def test_kelime_basina_token(self):
        cumleler = ["bir iki üç", "dört beş"]
        self.assertAlmostEqual(tokenizer_egit.fertility(cumleler, lambda c: 2 * len(c.split())), 2.0)

    def test_cumle_secimi_sabit_tohumlu(self):
        paragraflar = [f"Bu {i}. cümle burada. Kısa. Bu da ikinci cümle {i}." for i in range(50)]
        ilk = tokenizer_egit.cumleleri_sec(paragraflar, 10, tohum=1)
        self.assertEqual(ilk, tokenizer_egit.cumleleri_sec(paragraflar, 10, tohum=1))
        self.assertTrue(all(len(c.split()) >= 3 for c in ilk))


class TestIkiliYaz(unittest.TestCase):
    def test_uint16_geri_okuma(self):
        with tempfile.TemporaryDirectory() as dizin:
            metin = Path(dizin, "m.txt")
            metin.write_text("\n".join(veri_hazirla.makale_paragraflari(ORNEK_MAKALE) * 20),
                             encoding="utf-8")
            spm.SentencePieceTrainer.train(input=str(metin), model_prefix=str(Path(dizin, "t")),
                                           vocab_size=60, hard_vocab_limit=False)
            sp = spm.SentencePieceProcessor(model_file=str(Path(dizin, "t.model")))
            toplam = ikili_yaz.ikili_yaz(sp, metin, Path(dizin, "m.bin"))
            ids = np.fromfile(Path(dizin, "m.bin"), dtype=np.uint16)
        self.assertEqual(len(ids), toplam)
        self.assertEqual(int((ids == sp.eos_id()).sum()), 40)
        ilk_paragraf = ids[: list(ids).index(sp.eos_id())].tolist()
        self.assertTrue(sp.decode(ilk_paragraf).startswith("Kedi evcil"))


class TestSinavlar(unittest.TestCase):
    def oku(self, ad):
        return json.loads((SINAV_DIZINI / ad).read_text(encoding="utf-8"))

    def test_boyutlar(self):
        self.assertEqual(len(self.oku("dilbilgisi.json")["baslangiclar"]), 40)
        self.assertEqual(len(self.oku("dilbilgisi_ciftleri.json")["ciftler"]), 100)
        self.assertEqual(len(self.oku("eski_sinav.json")["sorular"]), 50)

    def test_ciftler_farkli_ve_sorular_bosluklu(self):
        for cift in self.oku("dilbilgisi_ciftleri.json")["ciftler"]:
            self.assertNotEqual(cift["dogru"], cift["bozuk"])
        for soru in self.oku("eski_sinav.json")["sorular"]:
            self.assertEqual(soru["soru"].count("___"), 1)
            self.assertEqual(len(soru["celdiriciler"]), 3)


if __name__ == "__main__":
    unittest.main()
