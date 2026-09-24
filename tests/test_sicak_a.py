"""sicak-a testi: SicaklikBekcisi 80 C'de duraklar, 70 altina inince devam eder, beklerken loglar.
Cagiran: python -m unittest / pytest. Gercek bekleme yok, uyku sahte."""

import unittest
from unittest import mock

from ortak import gpu_sicaklik

SAHTE_DIZI = [75, 81, 78, 72, 69]


def bekci_kur(dizi):
    """Sahte okuyucu ve sahte uykulu bekci; her uyku bir arka plan okumasi gibi _adim() cagirir."""
    okumalar = iter(dizi)
    uykular = []
    bekci = gpu_sicaklik.SicaklikBekcisi(kes=lambda: None, okuyucu=lambda: next(okumalar),
                                         uyku=lambda sn: (uykular.append(sn), bekci._adim()))
    return bekci, uykular


class TestDurakDevam(unittest.TestCase):
    def test_80de_duraklar_70_altinda_devam_eder(self):
        with mock.patch.object(gpu_sicaklik.log, "yaz") as yaz:
            bekci, uykular = bekci_kur(SAHTE_DIZI)
            bekci._adim()  # istek surerken arka plan 81 gorur
            self.assertTrue(bekci.durak_gerek)
            bekci.serinle()
        self.assertEqual(bekci.son_c, 69)
        self.assertEqual(len(uykular), 3)
        self.assertFalse(bekci.durak_gerek)
        olaylar = [c.args[1] for c in yaz.call_args_list]
        self.assertIn("durak_esigi", olaylar)
        self.assertEqual(olaylar.count("bekliyor"), 3)
        self.assertEqual(olaylar[-1], "devam")

    def test_okuma_araligi_30_sn_asilmaz(self):
        bekci, uykular = bekci_kur(SAHTE_DIZI)
        with mock.patch.object(gpu_sicaklik.log, "yaz"):
            bekci._adim()
            bekci.serinle()
        self.assertTrue(all(sn <= gpu_sicaklik.EN_UZUN_OKUMA_ARALIGI_SN for sn in uykular))
        self.assertLessEqual(bekci.aralik_sn, gpu_sicaklik.EN_UZUN_OKUMA_ARALIGI_SN)
        with self.assertRaises(ValueError):
            gpu_sicaklik.SicaklikBekcisi(kes=lambda: None, okuyucu=lambda: 50, aralik_sn=31)

    def test_80_gorulmediyse_ve_serinse_beklemez(self):
        bekci, uykular = bekci_kur([60, 64])
        with mock.patch.object(gpu_sicaklik.log, "yaz"):
            bekci._adim()
            self.assertEqual(bekci.serinle(), 0.0)
        self.assertEqual(uykular, [])

    def test_esikler(self):
        self.assertEqual((gpu_sicaklik.DURAK_ESIGI_C, gpu_sicaklik.DEVAM_ESIGI_C), (80, 70))


if __name__ == "__main__":
    unittest.main()
