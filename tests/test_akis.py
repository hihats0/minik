"""Akis sozlesme testi (K3): agsiz, GPU'suz. Akisin karar vermedigini (K6), Kafa hatasinda
comedigini ve agiz degisince kendisinin degismedigini dogrular.
Cagiran: `python -m unittest discover -s tests`."""

import json
import sys
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import minik
from ortak import log

CIKIS = minik.CIKIS_KELIMESI


class SahteAgiz:
    """Konsol yerine kullanilan sahte agiz: sirali sorulari verir, cevaplari listede tutar."""

    def __init__(self, sorular):
        self._sorular = list(sorular) + [CIKIS]
        self.soylenenler = []

    def dinle(self):
        return self._sorular.pop(0)

    def soyle(self, metin, dis_id):
        self.soylenenler.append((metin, dis_id))


def _son_log_satiri():
    """Bugunku log dosyasinin son satirini JSON olarak dondurur."""
    dosya = log.LOG_KLASORU / f"{datetime.now().astimezone():%Y-%m-%d}.log"
    with dosya.open(encoding="utf-8") as f:
        satirlar = [s for s in f.readlines() if s.strip()]
    return json.loads(satirlar[-1])


class TestAkis(unittest.TestCase):

    def test_akis_kafanin_cevabini_degistirmeden_iletir(self):
        """Akis Kafa'nin cevabini yorumlamiyor/filtrelemiyor (K6): oldugu gibi agiza iletir."""
        agiz = SahteAgiz(["selam"])
        minik.calistir(dinle=agiz.dinle, soyle=agiz.soyle, dusun=lambda soru, baglam: "cevap: " + soru)
        self.assertEqual(agiz.soylenenler[0], ("cevap: selam", minik.DIS_ID))

    def test_kafa_hata_yukseltince_akis_cokmez(self):
        """Kafa hata yukseltirse akis durmaz, kullaniciya haber verir ve hata satiri loglar."""
        agiz = SahteAgiz(["soru"])

        def patlayan_dusun(soru, baglam):
            raise RuntimeError("sunucu kapali")

        minik.calistir(dinle=agiz.dinle, soyle=agiz.soyle, dusun=patlayan_dusun)

        self.assertEqual(agiz.soylenenler[0][0], minik.DUSUNEMIYORUM_METNI)
        satir = _son_log_satiri()
        self.assertEqual(satir["yuva"], "akis")
        self.assertEqual(satir["sonuc"], "hata")
        self.assertTrue(satir["detay"]["hata"])

    def test_iki_farkli_agizla_ayni_akis_calisir(self):
        """Agiz adaptoru degisince akis dosyasi degismiyor: iki sahte agizla ayni sonuc cikar."""
        agiz1 = SahteAgiz(["ayni soru"])
        agiz2 = SahteAgiz(["ayni soru"])
        dusun = lambda soru, baglam: "yanit"

        minik.calistir(dinle=agiz1.dinle, soyle=agiz1.soyle, dusun=dusun)
        minik.calistir(dinle=agiz2.dinle, soyle=agiz2.soyle, dusun=dusun)

        self.assertEqual(agiz1.soylenenler, agiz2.soylenenler)

    def test_baglam_turler_arasinda_biriktiriliyor(self):
        """Akis, Kafa'ya verdigi baglami kendisi biriktirir (karar Kafa'nin, veri akisin isi)."""
        gorulen_baglamlar = []

        def kaydeden_dusun(soru, baglam):
            gorulen_baglamlar.append(list(baglam))
            return f"cevap-{len(baglam)}"

        agiz = SahteAgiz(["ilk", "ikinci"])
        minik.calistir(dinle=agiz.dinle, soyle=agiz.soyle, dusun=kaydeden_dusun)

        self.assertEqual(gorulen_baglamlar[0], [])
        self.assertEqual(len(gorulen_baglamlar[1]), 2)


if __name__ == "__main__":
    unittest.main()
