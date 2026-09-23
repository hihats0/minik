"""f4-c: dopamin_degisimi kayda yaziliyor ve Uyku onceligine giriyor; uyku tetigi cift esikle
titremiyor; yas artiyor ve hormon.json ile korunuyor; uctan uca sahte gun + tetik + gece.
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
from ortak.ayar import HORMON_DOSYA_ADI, UYKU_ALT_ESIK, UYKU_UST_ESIK
from yuvalar import hormonlar, uyku, uyku_secim, uyku_tetik

CIKIS = minik.CIKIS_KELIMESI
GECE_SAATI = datetime(2026, 9, 23, 4, 0)  # saat egilimi en yuksek (+15)
TUR_SAYISI = 5


class OdulluHormonlar(hormonlar.Hormonlar):
    """Her "calisma" olayinda bir de "odul" gelir: gercekte ton siniflandiricinin yapacagi is."""

    def guncelle(self, olay=None, siddet=1.0):
        sonuc = super().guncelle(olay, siddet)
        return super().guncelle("odul", 1.0) if olay == "calisma" else sonuc


def _sorular(n):
    sorular = [f"soru {i}" for i in range(n)] + [CIKIS]
    return lambda: sorular.pop(0)


def _sahte_dusun(soru, baglam=None, hormon=None):
    return f"cevap: {soru}", 1.0


class TestF4c(unittest.TestCase):
    def setUp(self):
        self._gecici = tempfile.TemporaryDirectory()
        self.klasor = Path(self._gecici.name)
        self._eski = minik.defter.DEFTER_KLASORU
        minik.defter.DEFTER_KLASORU = self.klasor
        self._log_yamasi = mock.patch.object(uyku.log, "LOG_KLASORU", self.klasor / "loglar")
        self._log_yamasi.start()

    def tearDown(self):
        minik.defter.DEFTER_KLASORU = self._eski
        self._log_yamasi.stop()
        self._gecici.cleanup()

    def _kayitlar(self):
        dosya = next(self.klasor.glob("gunluk-*.jsonl"))
        return [json.loads(s) for s in dosya.read_text(encoding="utf-8").splitlines()]

    def test_dopamin_alani_yaziliyor_ve_oncelige_giriyor(self):
        minik.calistir(dinle=_sorular(2), soyle=lambda m, d: None, dusun=_sahte_dusun,
                       hormon_durumu=OdulluHormonlar(), gece=lambda *a, **k: None)
        kayitlar = self._kayitlar()
        self.assertTrue(all(k["dopamin_degisimi"] > 0 for k in kayitlar))
        self.assertGreater(uyku_secim.oncelik(kayitlar[0]), 0)
        self.assertEqual(uyku_secim.oncelik({"soru": "eski kayit"}), 0)

    def test_odulsuz_gunde_alan_sifir(self):
        minik.calistir(dinle=_sorular(1), soyle=lambda m, d: None, dusun=_sahte_dusun,
                       hormon_durumu=hormonlar.Hormonlar(), gece=lambda *a, **k: None)
        self.assertEqual(self._kayitlar()[0]["dopamin_degisimi"], 0)

    def test_tetik_cift_esikle_titremiyor(self):
        tetik = uyku_tetik.UykuTetigi()
        saat = 10.0  # cos(pi/2) = 0: egilim yok, basinc = melatonin
        tepe, orta = UYKU_UST_ESIK + 1, (UYKU_UST_ESIK + UYKU_ALT_ESIK) / 2
        ateslemeler = [tetik.uyumali_mi(m, saat) for m in [tepe, orta, tepe, orta, tepe]]
        self.assertEqual(ateslemeler, [True, False, False, False, False])
        tetik.uyumali_mi(UYKU_ALT_ESIK - 1, saat)
        self.assertTrue(tetik.uyumali_mi(tepe, saat))

    def test_saat_egilimi_gece_tutar_ogleden_sonra_tutmaz(self):
        self.assertAlmostEqual(uyku_tetik.saat_egilimi(4), 15.0)
        self.assertAlmostEqual(uyku_tetik.saat_egilimi(16), -15.0)
        melatonin = UYKU_UST_ESIK - 10
        self.assertTrue(uyku_tetik.UykuTetigi().uyumali_mi(melatonin, 4))
        self.assertFalse(uyku_tetik.UykuTetigi().uyumali_mi(melatonin, 16))

    def test_yas_artiyor_ve_yeniden_baslatmada_korunuyor(self):
        dosya = self.klasor / HORMON_DOSYA_ADI
        h = hormonlar.Hormonlar(dosya)
        h.guncelle("calisma", 1.0)
        h.guncelle("uyku", 1.0)
        yeniden = hormonlar.Hormonlar(dosya)
        self.assertEqual(yeniden.yas, 1)
        self.assertEqual(yeniden.oku(), h.oku())

    def test_hormon_json_silinir_ya_da_bozulursa_cokmuyor(self):
        dosya = self.klasor / HORMON_DOSYA_ADI
        dinlenme = {ad: t.dinlenme for ad, t in hormonlar.HORMONLAR.items()}
        self.assertEqual(hormonlar.Hormonlar(dosya).oku(), dinlenme)
        dosya.write_text("{bozuk", encoding="utf-8")
        h = hormonlar.Hormonlar(dosya)
        self.assertEqual((h.oku(), h.yas), (dinlenme, 0))

    def test_uctan_uca_gun_tetik_gece(self):
        """Yorgun Minik (melatonin 70) gece 04'te konusur: tetik tutar, gece isler, yas 1 olur,
        melatonin iner; ikinci calistir hormon.json'dan yas 1 ile acilir."""
        dosya = self.klasor / HORMON_DOSYA_ADI
        dosya.write_text(json.dumps({"deger": {**{a: t.dinlenme for a, t in
                         hormonlar.HORMONLAR.items()}, "melatonin": 70.0}, "yas": 0}), encoding="utf-8")
        geceler = []

        def gece(tarih, **ek):
            geceler.append(tarih)
            return uyku.gece(tarih, gomme_al=lambda m: None, prova=lambda a: True, **ek)

        minik.calistir(dinle=_sorular(TUR_SAYISI), soyle=lambda m, d: None, dusun=_sahte_dusun,
                       gece=gece, simdi=lambda: GECE_SAATI)
        self.assertEqual(geceler, ["2026-09-23"])
        sonra = hormonlar.Hormonlar(dosya)
        self.assertEqual(sonra.yas, 1)
        self.assertLess(sonra.oku()["melatonin"], UYKU_ALT_ESIK)
        # f4-b: bugunun kayitlari gun kapanmadan islenmez, bir sonraki uykuya kalir
        self.assertFalse((self.klasor / "sabah-ozet-2026-09-23.md").exists())
        self.assertTrue((self.klasor / "loglar" / "gorunur.html").exists())


if __name__ == "__main__":
    unittest.main()
