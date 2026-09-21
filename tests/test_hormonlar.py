"""Hormonlar yuvasinin sozlesme testi (K3): GPU'suz, agsiz, saniyeler icinde koser.
Cagiran: `python -m unittest discover -s tests` (pytest kurulu degil, stdlib kullaniliyor)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ortak import log
from yuvalar.hormonlar import EN_AZ, EN_COK, HORMONLAR, OLAYLAR, Hormonlar

SONUM_ICIN_ADIM = 1500  # en yavas hormon (sonum 0,01) icin bile dinlenmeye yeten adim sayisi
DINLENMEYE_YAKIN = 0.5  # bu kadar puan fark "dondu" sayilir
DAVRANIS_USTUNLUGU = 5  # davranisin indirdigi, on adim beklemenin indirdiginin en az bu kati olmali


class TestHormonlar(unittest.TestCase):

    def setUp(self):
        self.h = Hormonlar()

    def test_ceza_kortizolu_yukseltir(self):
        """Yigit'in karari: ceza Claude'dan gelir ve kortizolu yukseltir."""
        once = self.h.oku()["kortizol"]
        sonra = self.h.guncelle("ceza")["kortizol"]
        self.assertGreater(sonra, once)

    def test_kortizol_ancak_iyi_sey_olunca_iner(self):
        """Beklemek kortizolu indirmemeli; indiren sey davranis olmali."""
        self.h.guncelle("ceza")
        gergin = self.h.oku()["kortizol"]
        for _ in range(10):
            self.h.guncelle()  # on adim bos beklendi
        bekleyerek = self.h.oku()["kortizol"]
        iyi_seyden_sonra = self.h.guncelle("iyi_sey")["kortizol"]
        beklemenin_indirdigi = gergin - bekleyerek
        davranisin_indirdigi = bekleyerek - iyi_seyden_sonra
        # Tasarim iddiasi bu: beklemek de indiriyor ama davranis KAT KAT daha cok indiriyor.
        self.assertGreater(davranisin_indirdigi, beklemenin_indirdigi * DAVRANIS_USTUNLUGU,
                           "kortizolu indiren asil sey davranis olmali, beklemek degil")

    def test_merak_ogrenince_iner(self):
        """Ana motor merak: ancak ogrenince iner, beklemekle degil."""
        self.h.guncelle("ogrenilebilir_sasirma")
        merakli = self.h.oku()["merak"]
        sonra = self.h.guncelle("ogrendi")["merak"]
        self.assertLess(sonra, merakli - 20.0)

    def test_yalnizlik_oksitosini_dusurur(self):
        """K19: kimseyle konusulmayan gun oksitosini indirir (yoksunlugun bedeli)."""
        once = self.h.oku()["oksitosin"]
        sonra = self.h.guncelle("kimseyle_konusulmadi")["oksitosin"]
        self.assertLess(sonra, once)

    def test_uretim_yoklugu_serotonini_dusurur(self):
        """K19: hicbir sey uretilmeyen gun serotonini indirir (Yigit: 'serotonin dusmesi olur
        bunlar olmazsa')."""
        once = self.h.oku()["serotonin"]
        sonra = self.h.guncelle("hicbir_sey_uretilmedi")["serotonin"]
        self.assertLess(sonra, once)

    def test_yoksunluk_olaylari_da_tek_hormona_dokunur(self):
        """K19'un yeni iki olayi da bagimsizlik kuralini bozmamali: sadece kendi hormonuna dokunur."""
        for olay, hedef in (("kimseyle_konusulmadi", "oksitosin"), ("hicbir_sey_uretilmedi", "serotonin")):
            h = Hormonlar()
            h.guncelle(olay)
            for ad, deger in h.oku().items():
                if ad == hedef:
                    continue
                self.assertAlmostEqual(deger, HORMONLAR[ad].dinlenme, delta=0.001,
                                       msg=f"{olay} {ad} hormonunu da oynatti")

    def test_melatonin_ancak_uyuyunca_iner(self):
        """Uyku sabit saatte degil, yorulunca. Yorgunlugu indiren tek sey uyku."""
        for _ in range(30):
            self.h.guncelle("calisma")
        yorgun = self.h.oku()["melatonin"]
        uyandi = self.h.guncelle("uyku")["melatonin"]
        self.assertGreater(yorgun, HORMONLAR["melatonin"].dinlenme)
        self.assertLess(uyandi, HORMONLAR["melatonin"].dinlenme + 1.0)

    def test_sinir_disina_tasmaz(self):
        """Her olay en yuksek siddette yuzlerce kez gelse de hicbir sayi araligi asmaz."""
        for olay in sorted(OLAYLAR):
            for _ in range(200):
                degerler = self.h.guncelle(olay, siddet=1.0)
                for ad, deger in degerler.items():
                    self.assertGreaterEqual(deger, EN_AZ, f"{ad} alt siniri asti")
                    self.assertLessEqual(deger, EN_COK, f"{ad} ust siniri asti")

    def test_dinlenme_degerine_doner(self):
        """Olay gelmeyi kesince yedi hormon da kendi dinlenme degerine doner."""
        for olay in ("ceza", "odul", "ogrenilebilir_sasirma", "calisma", "belirsizlik"):
            self.h.guncelle(olay)
        for _ in range(SONUM_ICIN_ADIM):
            self.h.guncelle()
        for ad, deger in self.h.oku().items():
            self.assertAlmostEqual(deger, HORMONLAR[ad].dinlenme, delta=DINLENMEYE_YAKIN,
                                   msg=f"{ad} dinlenme degerine donmedi")

    def test_hata_yutulmaz(self):
        """Bilinmeyen olay ve gecersiz siddet sessizce yok sayilmaz, hata yukselir."""
        with self.assertRaises(ValueError):
            self.h.guncelle("boyle_bir_olay_yok")
        with self.assertRaises(ValueError):
            self.h.guncelle("ceza", siddet=5.0)
        with self.assertRaises(ValueError):
            log.yaz("hormonlar", "deneme", 1, "belkidir", {})
        with self.assertRaises(ValueError):
            log.yaz("hormonlar", "deneme", 1, "hata", {})  # gerekcesiz hata satiri gecemez

    def test_hatali_cagri_durumu_bozmaz(self):
        """Hata yukselse bile yedi sayi oldugu gibi kalir."""
        once = self.h.oku()
        with self.assertRaises(ValueError):
            self.h.guncelle("boyle_bir_olay_yok")
        self.assertEqual(once, self.h.oku())

    def test_hormonlar_birbirine_bagli_degil(self):
        """Ilk surumun tasarim karari: bir olay en fazla bir hormonu oynatir."""
        self.h.guncelle("ceza")
        for ad, deger in self.h.oku().items():
            if ad == "kortizol":
                continue
            self.assertAlmostEqual(deger, HORMONLAR[ad].dinlenme, delta=0.001,
                                   msg=f"ceza {ad} hormonunu da oynatti")

    def test_ayni_olay_dizisi_ayni_sonucu_verir(self):
        """Ayni ayarla iki kosu ayni sonucu vermeli (mimari-taslak sozlesme testi)."""
        dizi = ["ceza", "odul", None, "calisma", "ogrenilebilir_sasirma", None]
        ikinci = Hormonlar()
        for olay in dizi:
            self.h.guncelle(olay)
            ikinci.guncelle(olay)
        self.assertEqual(self.h.oku(), ikinci.oku())

    def test_her_guncelleme_log_dusurur(self):
        """Her yuva log tutar kurali: guncelle cagrisi log dosyasina satir yazar."""
        from datetime import datetime
        dosya = log.LOG_KLASORU / f"{datetime.now().astimezone():%Y-%m-%d}.log"
        onceki = dosya.stat().st_size if dosya.exists() else 0
        self.h.guncelle("odul")
        self.assertTrue(dosya.exists(), "log dosyasi olusmadi")
        self.assertGreater(dosya.stat().st_size, onceki, "log satiri yazilmadi")


if __name__ == "__main__":
    unittest.main()
