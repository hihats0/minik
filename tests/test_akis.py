"""Akis sozlesme testi (K3): agsiz, GPU'suz. Akisin karar vermedigini (K6), Kafa hatasinda
comedigini, Defter yazamayinca durdugunu ve agiz degisince kendisinin degismedigini dogrular.
Gecici klasor kullanir, gercek defter/ klasorune dokunmaz.
Cagiran: `python -m unittest discover -s tests`."""

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

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
    """Defter gercek yuva olarak calisir; testler kirlenmesin diye gecici klasore baglanir."""

    def setUp(self):
        self._gecici = tempfile.TemporaryDirectory()
        self._eski_klasor = minik.defter.DEFTER_KLASORU
        minik.defter.DEFTER_KLASORU = Path(self._gecici.name)

    def tearDown(self):
        minik.defter.DEFTER_KLASORU = self._eski_klasor
        self._gecici.cleanup()

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

    def test_defter_yazamazsa_akis_durur(self):
        """En pahali kayip kaydedilmeyen konusmadir (spec 3.4): Defter yazma hatasinda akis
        ikinci soruyu hic sormadan durur ve kullaniciya haber verir."""
        agiz = SahteAgiz(["soru1", "soru2"])

        with mock.patch.object(minik.defter, "yaz", side_effect=OSError("disk dolu")):
            minik.calistir(dinle=agiz.dinle, soyle=agiz.soyle,
                            dusun=lambda soru, baglam: "cevap")

        self.assertEqual(len(agiz.soylenenler), 2)
        self.assertEqual(agiz.soylenenler[1], (minik.DEFTER_HATASI_METNI, minik.DIS_ID))
        self.assertEqual(agiz._sorular, ["soru2", CIKIS])  # ikinci soru hic sorulmadi
        satir = _son_log_satiri()
        self.assertEqual(satir["yuva"], "akis")
        self.assertEqual(satir["sonuc"], "hata")
        self.assertIn("defter", satir["detay"]["hata"])

    def test_bekci_engelleyince_sabit_metin_soylenir_deftere_yazilmaz(self):
        """Bekci 'hayir' derse (K6: karari Bekci verir) Kafa'nin ham cevabi hic agiza gitmez,
        sabit bir engel metni soylenir ve Defter'e yazilmaz (spec 3.4: gercek olmayan konusma
        ham kayda girmemeli)."""
        agiz = SahteAgiz(["kufurlu soru"])

        with mock.patch.object(minik.bekci, "cikabilir_mi", return_value=(False, "test gerekcesi")):
            minik.calistir(dinle=agiz.dinle, soyle=agiz.soyle, dusun=lambda soru, baglam: "kufurlu cevap")

        self.assertEqual(agiz.soylenenler[0], (minik.ENGELLENDI_METNI, minik.DIS_ID))
        satir = _son_log_satiri()
        self.assertEqual(satir["yuva"], "akis")
        self.assertEqual(satir["sonuc"], "ok")
        self.assertEqual(satir["detay"]["bekci"], "engellendi")
        self.assertEqual(satir["detay"]["gerekce"], "test gerekcesi")
        self.assertEqual(minik.defter.oku(), [])

    def test_bekci_gecerse_akis_degismez(self):
        """Bekci 'evet' derse akis eskisi gibi calisir: cevap oldugu gibi agiza gider."""
        agiz = SahteAgiz(["temiz soru"])

        with mock.patch.object(minik.bekci, "cikabilir_mi", return_value=(True, "temiz")):
            minik.calistir(dinle=agiz.dinle, soyle=agiz.soyle, dusun=lambda soru, baglam: "temiz cevap")

        self.assertEqual(agiz.soylenenler[0], ("temiz cevap", minik.DIS_ID))
        self.assertEqual(len(minik.defter.oku()), 1)

    def test_gecmis_kayitlar_baglama_yuklenir(self):
        """Onceki oturumdan Defter'e yazilmis kayitlar yeni calistir() cagrisinin baglamina
        girer: 'kapat-ac hatirlama' bunun uzerine kurulu (f2 bitirme sarti 2)."""
        minik.defter.yaz({"soru": "dunku soru", "cevap": "dunku cevap", "platform": minik.DIS_ID})
        gorulen_baglamlar = []

        def kaydeden_dusun(soru, baglam):
            gorulen_baglamlar.append(list(baglam))
            return "yeni cevap"

        agiz = SahteAgiz(["yeni soru"])
        minik.calistir(dinle=agiz.dinle, soyle=agiz.soyle, dusun=kaydeden_dusun)

        self.assertEqual(gorulen_baglamlar[0], [
            {"role": "user", "content": "dunku soru"},
            {"role": "assistant", "content": "dunku cevap"},
        ])


if __name__ == "__main__":
    unittest.main()
