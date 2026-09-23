"""Uyku tur 1 testleri (kirmizi takim satiri): ham jsonl degismiyor, ayni gun iki kez calismiyor,
yarim islem geri aliniyor; budama, yakalama penceresi, SM-2, gommesiz calisma. Agsiz, GPU'suz.
Cagiran: `python -m unittest discover -s tests`."""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from yuvalar import defter_sqlite, hormonlar, uyku
from yuvalar import uyku_secim as secim

TARIH = "2026-09-20"


def _kayit(saat, soru, dopamin=0.0):
    return {"soru": soru, "cevap": f"{soru} cevabi burada", "platform": "konsol",
            "zaman": f"{TARIH}T{saat}:00+03:00", "dopamin_degisimi": dopamin}


def _sahte_gomme(metin):
    return [float(len(metin)), 1.0, 0.5]


class TestUyku(unittest.TestCase):

    def setUp(self):
        self._gecici = tempfile.TemporaryDirectory()
        self.klasor = Path(self._gecici.name)
        kayitlar = [_kayit("10:00", "kedi ne yer"), _kayit("10:20", "kopek havlar mi", 25.0),
                    _kayit("10:40", "kus ucar mi"), _kayit("14:00", "yagmur yagar mi")]
        self.jsonl = self.klasor / f"gunluk-{TARIH}.jsonl"
        self.jsonl.write_text("".join(json.dumps(k) + "\n" for k in kayitlar), encoding="utf-8")

    def tearDown(self):
        self._gecici.cleanup()

    def _gece(self, tarih=TARIH, prova=lambda ani: True, **ek):
        return uyku.gece(tarih, gomme_al=_sahte_gomme, prova=prova, klasor=self.klasor, **ek)

    def _ani_sayisi(self):
        baglanti = defter_sqlite.baglan(self.klasor)
        try:
            return baglanti.execute("SELECT COUNT(*) FROM anilar").fetchone()[0]
        finally:
            baglanti.close()

    def test_ham_jsonl_degismiyor(self):
        once = hashlib.sha256(self.jsonl.read_bytes()).hexdigest()
        self._gece()
        self.assertEqual(once, hashlib.sha256(self.jsonl.read_bytes()).hexdigest())

    def test_ayni_gun_iki_kez_calismiyor(self):
        self._gece()
        ozet, etiketlenen, budanan = self._gece()
        self.assertEqual((ozet, etiketlenen, budanan), (uyku.ZATEN_ISLENDI, 0, 0))
        self.assertEqual(self._ani_sayisi(), 4)

    def test_yarim_islem_geri_aliniyor(self):
        with mock.patch.object(defter_sqlite, "budama_yap", side_effect=RuntimeError("cokme")):
            with self.assertRaises(RuntimeError):
                self._gece()
        self.assertEqual(self._ani_sayisi(), 0)
        self._gece()  # ertesi gece ayni gun yeniden islenir
        self.assertEqual(self._ani_sayisi(), 4)

    def test_yakalama_penceresi(self):
        etiketli = secim.etiketle([json.loads(s) for s in self.jsonl.read_text().splitlines()])
        etiketler = [a["etiket"] for a in etiketli]
        self.assertEqual(etiketler, ["yakalandi", "oncelikli", "yakalandi", "siradan"])

    def test_sm2_basarili_ve_basarisiz(self):
        ani = {"id": 1, "tekrar": 1, "ef": 2.5, "ust_uste_basarisiz": 2}
        iyi = secim.sm2_adimi(ani, 4, TARIH)
        self.assertEqual((iyi["tekrar"], iyi["sonraki_gun"], iyi["ust_uste_basarisiz"]),
                         (2, "2026-09-26", 0))
        kotu = secim.sm2_adimi(ani, 2, TARIH)
        self.assertEqual((kotu["tekrar"], kotu["sonraki_gun"], kotu["ust_uste_basarisiz"]),
                         (0, "2026-09-21", 3))
        self.assertAlmostEqual(kotu["ef"], 2.18)

    def test_uc_kez_ust_uste_unutulan_budaniyor(self):
        self._gece()
        budananlar = [self._gece(f"2026-09-2{g}", prova=lambda ani: False)[2] for g in (1, 2, 3)]
        self.assertEqual(budananlar, [0, 0, 4])
        self.assertEqual(self._ani_sayisi(), 0)

    def test_arada_hatirlanan_budanmiyor(self):
        self._gece()
        for gun, sonuc in ((1, False), (2, True)):
            self._gece(f"2026-09-2{gun}", prova=lambda ani, s=sonuc: s)
        self.assertEqual(self._ani_sayisi(), 4)

    def test_gomme_ve_kafa_yokken_cokmuyor(self):
        hata = OSError("sunucu yok")
        with mock.patch.object(uyku, "vektor_al", side_effect=hata), \
             mock.patch.object(uyku.kafa, "dusun", side_effect=hata):
            uyku.gece(TARIH, klasor=self.klasor)
            ozet, _, _ = uyku.gece("2026-09-21", klasor=self.klasor)
        self.assertIn("Prova: 0 ani", ozet)
        self.assertEqual(self._ani_sayisi(), 4)

    def test_sabah_ozeti_ve_melatonin(self):
        durum = hormonlar.Hormonlar()
        durum._deger["melatonin"] = 90.0
        ozet, etiketlenen, _ = self._gece(hormon_durumu=durum)
        self.assertEqual(etiketlenen, 3)
        self.assertTrue((self.klasor / f"sabah-ozet-{TARIH}.md").exists())
        self.assertLess(durum.oku()["melatonin"], 20.0)
        self.assertIn("cagristirdi", ozet)


if __name__ == "__main__":
    unittest.main()
