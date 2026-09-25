"""araclar/k41b_depo_olc.py testi: depo karisiminin olasilik toplami 1, lambda=0'da BPC modelinki, sasirtan
seciminin orani, imza taramasinin Hamming ile ayni siralamasi. CPU. Cagiran: `python -m pytest`."""

import importlib.util
import math
import unittest
from pathlib import Path

import torch
import torch.nn.functional as F

YOL = Path(__file__).resolve().parent.parent / "araclar" / "k41b_depo_olc.py"
_spec = importlib.util.spec_from_file_location("k41b", YOL)
k41b = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(k41b)

SOZLUK, N, BOYUT = 50, 200, 16
TOLERANS = 1e-5


class TestK41b(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(0)
        self.logp = F.log_softmax(torch.randn(N, SOZLUK), -1)
        self.uzaklik = torch.rand(N, k41b.K) * 10
        self.deger = torch.randint(0, SOZLUK, (N, k41b.K))
        self.hedef = torch.randint(0, SOZLUK, (N,))

    def test_karisim_toplami_bir(self):
        p_depo = k41b.depo_dagilimi(self.uzaklik, self.deger, 3.0, SOZLUK)
        for lam in (0.0, 0.25, 1.0):
            toplam = ((1 - lam) * self.logp.exp() + lam * p_depo).sum(-1)
            self.assertTrue(torch.allclose(toplam, torch.ones(N), atol=TOLERANS))

    def test_hedef_olasiligi_tam_dagilimla_ayni(self):
        tam = k41b.depo_dagilimi(self.uzaklik, self.deger, 3.0, SOZLUK).gather(1, self.hedef[:, None])[:, 0]
        hizli = k41b.hedef_depo_olasiligi(self.uzaklik, self.deger, self.hedef, 3.0)
        self.assertTrue(torch.allclose(tam, hizli, atol=TOLERANS))

    def test_lambda_sifirda_bpc_modelinki(self):
        logp_h = self.logp.gather(1, self.hedef[:, None])[:, 0]
        p = k41b.hedef_depo_olasiligi(self.uzaklik, self.deger, self.hedef, 3.0)
        karakter = 3 * N
        beklenen = -logp_h.sum().item() / karakter / math.log(2)
        self.assertAlmostEqual(k41b.karisim_bpc(logp_h, p, 0.0, karakter), beklenen, places=6)
        # kucuk lambda da neredeyse ayni olmali (karisim formulu surekli)
        self.assertAlmostEqual(k41b.karisim_bpc(logp_h, p, 1e-9, karakter), beklenen, places=5)

    def test_sasirtan_orani(self):
        kayip = torch.rand(10_000)
        maske = k41b.sasirtan_maske(kayip)
        self.assertAlmostEqual(maske.float().mean().item(), k41b.SASIRTAN_ORAN, delta=0.002)
        self.assertGreater(kayip[maske].min(), kayip[~maske].max())

    def test_imza_hamming(self):
        a, b = torch.randn(30, BOYUT), torch.randn(1, BOYUT)
        ic = (torch.sign(b) @ k41b.imza_ac(k41b.imza(a)).float().T)[0]
        hamming = ((a > 0) != (b > 0)).sum(-1)
        self.assertTrue(torch.equal(ic, (BOYUT - 2 * hamming).float()))

    def test_ara_kendini_bulur(self):
        """Kirmizi deneme: depodaki bir anahtarla sorulunca en yakin komsu kendisi, uzaklik 0."""
        anahtar = torch.randn(k41b.ADAY * 3, BOYUT)
        depo = {"anahtar": anahtar.half(), "deger": torch.arange(len(anahtar)), "imza": k41b.imza(anahtar)}
        d, v = k41b.ara(anahtar[:5].half(), depo)
        self.assertTrue(torch.equal(v[:, 0], torch.arange(5)))
        self.assertTrue(torch.all(d[:, 0] < TOLERANS))


if __name__ == "__main__":
    unittest.main()
