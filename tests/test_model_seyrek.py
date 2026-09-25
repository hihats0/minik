"""Finalist A (SeyrekCocuk) testi: uc kolda cikti sekli, nedensellik, eval'de agacin tek yaprak
kullanmasi, varsayilan ayarda parametre butcesi. CPU, kucuk ayar. Cagiran: `python -m unittest`.
"""

import sys
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cocuk import egit_araclari as ea

KOLLAR = ("agac", "hash", "yogun")
KUCUK = {"boyut": 32, "bloom": 64, "derinlik": 3, "yaprak_ara": 8, "sozluk": 500, "baglam": 64}
PARAMETRE_ALT, PARAMETRE_UST = 27_000_000, 33_000_000
TOLERANS = 1e-5
KESIM = 20  # bu konumdan sonrasi degistirilir


def kur(kol):
    torch.manual_seed(0)
    return ea.model_kur("seyrek", {**KUCUK, "yonlendirici": kol})


class TestSeyrek(unittest.TestCase):
    def test_cikti_sekli(self):
        for kol in KOLLAR:
            for egitim in (True, False):
                model = kur(kol).train(egitim)
                logit = model(torch.randint(0, 500, (2, 40)))
                self.assertEqual(tuple(logit.shape), (2, 40, 500), kol)

    def test_nedensel(self):
        """t'den sonraki tokenlar degisince t ve oncesinin logiti degismemeli (egitim ve eval)."""
        ids = torch.randint(0, 500, (1, 40))
        degisik = ids.clone()
        degisik[0, KESIM:] = (degisik[0, KESIM:] + 1) % 500
        for kol in KOLLAR:
            for egitim in (True, False):
                model = kur(kol).train(egitim)
                with torch.no_grad():
                    fark = (model(ids)[0, :KESIM] - model(degisik)[0, :KESIM]).abs().max().item()
                self.assertLess(fark, TOLERANS, f"{kol} egitim={egitim}")

    def test_eval_agac_tek_yaprak(self):
        """Eval'de secilmeyen yapraklarin agirligi bozulunca cikti degismemeli."""
        model = kur("agac").eval()
        ids = torch.randint(0, 500, (1, 30))
        with torch.no_grad():
            once = model(ids)
            secilen = model.uzman.son_yapraklar
            self.assertEqual(secilen.shape, (30,))
            ara = model.uzman.ara
            for j in set(range(model.uzman.yaprak)) - set(secilen.tolist()):
                model.uzman.w1[:, j * ara:(j + 1) * ara] += 100.0
            self.assertLess((model(ids) - once).abs().max().item(), TOLERANS)

    def test_parametre_butcesi(self):
        for kol in KOLLAR:
            with torch.device("meta"):
                sayi = ea.parametre_sayisi(ea.model_kur("seyrek", {"yonlendirici": kol}))
            self.assertTrue(PARAMETRE_ALT <= sayi <= PARAMETRE_UST, f"{kol}: {sayi}")


if __name__ == "__main__":
    unittest.main()
