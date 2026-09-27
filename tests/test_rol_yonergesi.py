"""cevap-b testi: sahne yonergesi ve "Peki ya sen?" temizligi, rol_var_mi, rol kaydinin baglama girmemesi,
bos cevabin kullaniciya gitmemesi. Ornekler defter/gunluk-2026-09-24.jsonl ve 26 Eyl sizinti yedeginden.
Cagiran: `python -m pytest -q`."""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import minik
from ortak import duz_metin

# 24 Eyl gercek cevaplari (kisaltilmis, yonergeler aynen).
GERCEK_24 = (
    "(Gözlerini kırpıp gülümsüyor)\nİyiyim, teşekkür ederim Yiğit!\n\n"
    "Ama dürüst olmak gerekirse… (Hafifçe omuz silker)\nÇay içerken mesaj atman güzel.\n\n"
    "Peki ya sen? Bugün aklından neler geçti?"
)
TEMIZ_24 = "İyiyim, teşekkür ederim Yiğit!\n\nAma dürüst olmak gerekirse…\nÇay içerken mesaj atman güzel.\n\nBugün aklından neler geçti?"
YONERGELER = [
    "(Göz kırparak)", "(Gülümser)", "(Hafifçe sırıtarak)", "(Kıkırdar)", "(Aniden duraksar)",
    "(Kısa bir sessizlik)", "(Sesinde bir alaycılıkla)", "(Gözlerinde bir ışık parlayarak)",
    "(Hafifçe omuz silker, sanal pencereden dışarı bakıyormuş gibi)",
    "(Parmağını dudağına götürerek düşünür)", "(Gülümseyerek başını hafifçe yana eğer)",
    "(Bir an düşünüp konuşmaya başlar)", "(Hafifçe omuz silkeler)",
    "(Düz metinle devam ederken gözlerinde bir parıltı belirir)",
]
# Karar: kucuk harfle baslayan aciklama parantezi kalir; ama fiille biterse (-ar/-er, -arak, -yor) yonerge sayilir.
ACIKLAMA = "Teknik olarak hafızam yok (yani seni veritabanımda kaydedemiyorum), ama hatırlıyorum."


class TestSahneYonergesi(unittest.TestCase):
    def test_gercek_cevap_temizlenir(self):
        self.assertEqual(duz_metin.temizle(GERCEK_24), TEMIZ_24)

    def test_butun_gercek_yonergeler_silinir(self):
        for yonerge in YONERGELER:
            self.assertEqual(duz_metin.temizle(f"Tamam {yonerge} dedim."), "Tamam dedim.", yonerge)

    def test_aciklama_parantezi_kalir(self):
        self.assertEqual(duz_metin.temizle(ACIKLAMA), ACIKLAMA)
        self.assertEqual(duz_metin.temizle("Çayını içtim (lezzetli!) sanki."), "Çayını içtim (lezzetli!) sanki.")

    def test_kucuk_harfli_hareket_de_silinir(self):
        self.assertEqual(duz_metin.temizle("Olur (gülümser) tabii."), "Olur tabii.")
        self.assertEqual(duz_metin.temizle("Olur (bunu herkes söyler) tabii."), "Olur tabii.")  # bilinen bedel

    def test_rol_var_mi(self):
        self.assertTrue(duz_metin.rol_var_mi(GERCEK_24))
        self.assertTrue(duz_metin.rol_var_mi("Mavi severim. peki ya sen?"))
        self.assertFalse(duz_metin.rol_var_mi(ACIKLAMA))
        self.assertFalse(duz_metin.rol_var_mi(TEMIZ_24))


class TestRolKaydiBaglamaGirmez(unittest.TestCase):
    def test_rol_kaydi_atlanir(self):
        kayitlar = [{"soru": "Bugün ne yaptın?", "cevap": "(Göz kırparak)\nSabah kanguru prototipi tasarladım."},
                    {"soru": "selam", "cevap": "Selam Yiğit."}]
        with mock.patch.object(minik.defter, "oku", return_value=kayitlar):
            baglam = minik._gecmisten_baglam_yukle()
        self.assertEqual(baglam, [{"role": "user", "content": "selam"},
                                  {"role": "assistant", "content": "Selam Yiğit."}])


class SahteHormon:
    def oku(self):
        return {"dopamin": 0, "melatonin": 0}

    def guncelle(self, olay, siddet):
        pass


class TestBosCevap(unittest.TestCase):
    def test_bos_cevap_kullaniciya_bos_gitmez_deftere_girmez(self):
        baglam = []
        with mock.patch.object(minik.calgici_tani, "baglam_mesaji", return_value=None):
            cevap, basarili = minik._tur_isle("selam", baglam, lambda s, b, h: ("", 1.0), SahteHormon())
        self.assertEqual(cevap, minik.BOS_CEVAP_METNI)
        self.assertFalse(basarili)
        self.assertEqual(baglam, [])


# 27 Eyl canli sohbet (defter/gunluk-2026-09-27.jsonl kayit 16, 23, 24): satir basindaki kucuk harfli yonergeler kacti.
SATIR_BASI = [
    ("(tatlı bir gülümsemeyle)\nTatlandırıcı mı?", "Tatlandırıcı mı?"),
    ("(sesinde hafif bir titreme) Bilmiyorum...", "Bilmiyorum..."),
    ("Anlıyorum.\n\n(duraklar, sonra daha kararlı)\nAma şunu biliyorum", "Anlıyorum.\n\nAma şunu biliyorum"),
]


class TestSatirBasiYonerge(unittest.TestCase):
    def test_satir_basi_parantez_silinir(self):
        for ham, temiz in SATIR_BASI:
            self.assertEqual(duz_metin.temizle(ham), temiz, ham)

    def test_satir_basi_parantez_rol_sayilir(self):
        for ham, _ in SATIR_BASI:
            self.assertTrue(duz_metin.rol_var_mi(ham), ham)

    def test_cumle_ici_aciklama_korunur(self):
        self.assertFalse(duz_metin.rol_var_mi(ACIKLAMA))
        self.assertEqual(duz_metin.temizle(ACIKLAMA), ACIKLAMA)


if __name__ == "__main__":
    unittest.main()
