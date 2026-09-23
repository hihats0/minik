"""f4-b testleri: gece kapanmis gunleri sirayla isler, bugunu birakir, bos gunlerde de prova eder;
her uyku loglar/gorunur.html'i yazar. Agsiz, GPU'suz. Cagiran: `python -m unittest discover -s tests`."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from yuvalar import defter_sqlite, gorunur, hormonlar, uyku


def _gun_yaz(klasor, tarih, soru):
    kayit = {"soru": soru, "cevap": "cevap", "zaman": f"{tarih}T10:00:00+03:00"}
    (klasor / f"gunluk-{tarih}.jsonl").write_text(json.dumps(kayit) + "\n", encoding="utf-8")


class TestGeceTarih(unittest.TestCase):

    def setUp(self):
        self._gecici = tempfile.TemporaryDirectory()
        self.klasor = Path(self._gecici.name)
        self._log_yamasi = mock.patch.object(uyku.log, "LOG_KLASORU", self.klasor / "loglar")
        self._log_yamasi.start()

    def tearDown(self):
        self._log_yamasi.stop()
        self._gecici.cleanup()

    def _gece(self, bugun, durum=None):
        return uyku.gece(bugun, hormon_durumu=durum, gomme_al=lambda m: [1.0, 0.0],
                         prova=lambda a: True, klasor=self.klasor)

    def _geceler(self):
        baglanti = defter_sqlite.baglan(self.klasor)
        try:
            return sorted(defter_sqlite.islenmis_geceler(baglanti))
        finally:
            baglanti.close()

    def test_bugun_islenmez_sonraki_uykuya_kalir(self):
        for tarih in ("2026-09-20", "2026-09-21", "2026-09-22"):
            _gun_yaz(self.klasor, tarih, f"soru {tarih}")
        self._gece("2026-09-22")
        self.assertEqual(self._geceler(), ["2026-09-20", "2026-09-21"])
        self._gece("2026-09-23")
        self.assertEqual(self._geceler(), ["2026-09-20", "2026-09-21", "2026-09-22"])

    def test_kayitsiz_gunler_de_islenir(self):
        _gun_yaz(self.klasor, "2026-09-20", "tek soru")
        self._gece("2026-09-23")
        self.assertEqual(self._geceler(), ["2026-09-20", "2026-09-21", "2026-09-22"])

    def test_islenecek_gun_yokken_yas_yine_artar(self):
        durum = hormonlar.Hormonlar()
        ozet, _, _ = self._gece("2026-09-23", durum)
        self.assertEqual((ozet, durum.yas), (uyku.ISLENECEK_GUN_YOK, 1))

    def test_gorunur_sayfa_yaziliyor(self):
        _gun_yaz(self.klasor, "2026-09-20", "kedi ne yer")
        durum = hormonlar.Hormonlar()
        self._gece("2026-09-21", durum)
        sayfa = (self.klasor / "loglar" / gorunur.SAYFA_ADI).read_text(encoding="utf-8")
        self.assertIn("Tutulan ani: 1", sayfa)
        self.assertIn("Yas (gece sayaci): 1", sayfa)
        self.assertIn("<td>melatonin</td>", sayfa)
        self.assertIn("# Sabah ozeti 2026-09-20", sayfa)

    def test_gorunur_ozeti_kacisla_yazar(self):
        yol = gorunur.yaz(self.klasor, None, "<b>kedi</b>", 0)
        sayfa = yol.read_text(encoding="utf-8")
        self.assertIn("&lt;b&gt;kedi", sayfa)
        self.assertIn("Yas (gece sayaci): bilinmiyor", sayfa)


if __name__ == "__main__":
    unittest.main()
