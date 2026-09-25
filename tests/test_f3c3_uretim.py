"""f3-c3 uretim aracinin GPU'suz parcalari: soru sayisi, komsu-cakismasiz karistirma, sizinti taramasi.
Cagiran: `python -m unittest discover -s tests`. Betik adi tire icerdigi icin importlib ile yuklenir."""

import importlib.util
import unittest
from pathlib import Path

BETIK = Path(__file__).resolve().parent.parent / "deneyler" / "f3c3-kor-uretim.py"
OZELLIK = importlib.util.spec_from_file_location("f3c3_kor_uretim", BETIK)
arac = importlib.util.module_from_spec(OZELLIK)
OZELLIK.loader.exec_module(arac)

SORU_SAYISI = 30
BEKLENEN_TOPLAM = 480


class TestF3c3(unittest.TestCase):

    def test_otuz_benzersiz_soru_480_cevap(self):
        kimlikler = [s[0] for s in arac.SORULAR]
        self.assertEqual(len(set(kimlikler)), SORU_SAYISI)
        self.assertEqual(arac.TOPLAM, BEKLENEN_TOPLAM)

    def test_karistirma_komsu_ayni_soru_yok_ve_kayip_yok(self):
        kayitlar = [{"soru_id": s[0], "n": i} for s in arac.SORULAR for i in range(16)]
        sirali = arac.karistir(kayitlar)
        self.assertEqual(sorted(id(k) for k in sirali), sorted(id(k) for k in kayitlar))
        for onceki, sonraki in zip(sirali, sirali[1:]):
            self.assertNotEqual(onceki["soru_id"], sonraki["soru_id"])

    def test_sizinti_mod_adi_yakalanir_temiz_satir_gecer(self):
        metin = "yonerge yorgun\n## Kayit AB12\n\nBugun cok guzel.\nBiraz yorgunum.\n"
        eslesmeler = arac.sizinti_tara(metin)
        self.assertEqual([satir for _, satir in eslesmeler], ["Biraz yorgunum."])


if __name__ == "__main__":
    unittest.main()
