"""Akisin Hormonlar'i olayla guncelledigini dogrular (R1, K10): f3-b, test_akis.py'den ayri
dosyada (200 satir siniri). Cagiran: `python -m unittest discover -s tests`."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import minik

CIKIS = minik.CIKIS_KELIMESI
IS_SN = 1.0  # sahte Kafa'nin bildirdigi is saniyesi (dusun (cevap, is_sn) dondurur)


class SahteAgiz:
    """Konsol yerine kullanilan sahte agiz: sirali sorulari verir, cevaplari listede tutar."""

    def __init__(self, sorular):
        self._sorular = list(sorular) + [CIKIS]
        self.soylenenler = []

    def dinle(self):
        return self._sorular.pop(0)

    def soyle(self, metin, dis_id):
        self.soylenenler.append((metin, dis_id))


class TestAkisHormon(unittest.TestCase):
    """Defter gercek yuva olarak calisir; testler kirlenmesin diye gecici klasore baglanir."""

    def setUp(self):
        self._gecici = tempfile.TemporaryDirectory()
        self._eski_klasor = minik.defter.DEFTER_KLASORU
        minik.defter.DEFTER_KLASORU = Path(self._gecici.name)

    def tearDown(self):
        minik.defter.DEFTER_KLASORU = self._eski_klasor
        self._gecici.cleanup()

    def test_hormon_degerleri_dusune_gecirilir(self):
        """Akis, Kafa'nin ornekleme hesaplayabilmesi icin o anki yedi hormonu dusun'e verir;
        donusumun kendisini yapmaz, sadece tasir (K6)."""
        gorulenler = []

        def kaydeden_dusun(soru, baglam, hormon=None):
            gorulenler.append(hormon)
            return "cevap", IS_SN

        agiz = SahteAgiz(["soru"])
        minik.calistir(dinle=agiz.dinle, soyle=agiz.soyle, dusun=kaydeden_dusun)
        self.assertEqual(set(gorulenler[0]),
                          {"dopamin", "noradrenalin", "serotonin", "kortizol",
                           "oksitosin", "melatonin", "merak"})

    def test_basarili_tur_calisma_olayiyla_melatonini_yukseltir(self):
        """R1: guncelleme akista yapilir. K10 (f3-e): siddet Kafa'nin bildirdigi is saniyesinden
        gelir. Tavan kadar is = siddet 1,0 -> melatonin 'calisma' yukselmesi kadar (1,5) cikar
        (dinlenme 10 -> 11,5)."""
        agiz = SahteAgiz(["soru"])
        hormon_durumu = minik.hormonlar.Hormonlar()
        minik.calistir(dinle=agiz.dinle, soyle=agiz.soyle,
                        dusun=lambda soru, baglam, hormon=None: ("cevap", minik.MELATONIN_IS_TAVAN_SN),
                        hormon_durumu=hormon_durumu)
        self.assertAlmostEqual(hormon_durumu.oku()["melatonin"], 11.5)

    def test_yarim_tavan_is_yarim_yukselme_verir(self):
        """Olcek gercek: tavanin yarisi kadar is 1,5'in yarisini ekler (10 -> 10,75)."""
        agiz = SahteAgiz(["soru"])
        hormon_durumu = minik.hormonlar.Hormonlar()
        minik.calistir(dinle=agiz.dinle, soyle=agiz.soyle,
                        dusun=lambda soru, baglam, hormon=None: ("cevap", minik.MELATONIN_IS_TAVAN_SN / 2),
                        hormon_durumu=hormon_durumu)
        self.assertAlmostEqual(hormon_durumu.oku()["melatonin"], 10.75)

    def test_kafa_hatasi_kortizolu_ceza_olayiyla_yukseltir(self):
        """Kafa 'dusunemedi' derse kortizol 'ceza' olayiyla yukselir (VARSAYIM, rapora
        yazildi): dinlenme 10 + yukselme 35 * siddet 1,0 = 45."""
        agiz = SahteAgiz(["soru"])
        hormon_durumu = minik.hormonlar.Hormonlar()

        def patlayan_dusun(soru, baglam, hormon=None):
            raise RuntimeError("sunucu kapali")

        minik.calistir(dinle=agiz.dinle, soyle=agiz.soyle, dusun=patlayan_dusun,
                        hormon_durumu=hormon_durumu)
        self.assertAlmostEqual(hormon_durumu.oku()["kortizol"], 45.0)


if __name__ == "__main__":
    unittest.main()
