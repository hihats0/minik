"""D4 cocuk modellerinin testi: ileri gecis, parametre butcesi, SSM taramasinin dogrulugu ve durum
tasima esitligi, tek egitim adiminda kayip dususu. CPU, kucuk ayar. Cagiran: `python -m unittest`.
"""

import sys
import unittest
from pathlib import Path

import numpy as np
import torch

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from cocuk import egit_araclari as ea
from cocuk.model_ssm import ssd_tarama

KUCUK = {"transformer": {"katman": 2, "boyut": 64, "kafa": 4, "ara_boyut": 128, "sozluk": 500},
         "ssm": {"katman": 2, "boyut": 64, "durum": 8, "kafa_boyutu": 16, "parca": 16,
                 "sozluk": 500},
         "minik": {"katman": 4, "boyut": 64, "kafa": 4, "ara_boyut": 128, "sozluk": 500},
         "seyrek": {"boyut": 32, "bloom": 64, "derinlik": 3, "yaprak_ara": 8, "sozluk": 500,
                    "baglam": 64},
         "uzman": {"katman": 2, "boyut": 64, "kafa": 4, "ara_boyut": 128, "sozluk": 500, "uzman": 4}}
PARAMETRE_ALT, PARAMETRE_UST = 25_000_000, 35_000_000
TOLERANS = 1e-4


class TestModeller(unittest.TestCase):
    def test_ileri_gecis_boyutu(self):
        for tur in ea.MODELLER:
            model = ea.model_kur(tur, KUCUK[tur])
            logit = model(torch.randint(0, 500, (2, 40)))
            self.assertEqual(tuple(logit.shape), (2, 40, 500), tur)

    def test_parametre_sayisi_butcede(self):
        for tur in ea.MODELLER.keys() - {"uzman"}:  # uzman: parametre E ile buyur, butce disi (K42-B)
            with torch.device("meta"):  # agirlik bellegi ayrilmaz, sayim ayni; 30M rastgele baslatma yok
                sayi = ea.parametre_sayisi(ea.model_kur(tur))
            self.assertTrue(PARAMETRE_ALT <= sayi <= PARAMETRE_UST, f"{tur}: {sayi}")

    def test_gomme_ve_cikis_bagli(self):
        for tur in ea.MODELLER.keys() - {"seyrek"}:  # seyrek: cikis bilerek bagli degil (Finalist A)
            model = ea.model_kur(tur, KUCUK[tur])
            sozluk_matrisleri = [ad for ad, p in model.named_parameters() if p.shape[0] == 500]
            self.assertEqual(sozluk_matrisleri, ["gomme.weight"], tur)

    def test_transformer_nedensel(self):
        """Gelecekteki token degisince gecmis konumlarin ciktisi degismemeli."""
        model = ea.model_kur("transformer", KUCUK["transformer"]).eval()
        ids = torch.randint(0, 500, (1, 30))
        degisik = ids.clone()
        degisik[0, 20:] = (degisik[0, 20:] + 1) % 500
        with torch.no_grad():
            fark = (model(ids)[0, :20] - model(degisik)[0, :20]).abs().max().item()
        self.assertLess(fark, TOLERANS)


class TestSSMDurum(unittest.TestCase):
    def test_tarama_sirali_donguyle_ayni(self):
        """Parcali tarama, h_t = exp(A_t) h_{t-1} + B_t X_t dongusunun aynisini vermeli."""
        torch.manual_seed(0)
        b, uzunluk, h, p, n = 2, 32, 3, 4, 5
        X, B, C = torch.randn(b, uzunluk, h, p), torch.randn(b, uzunluk, n), torch.randn(b, uzunluk, n)
        A, ilk = -torch.rand(b, uzunluk, h), torch.randn(b, h, p, n)
        y, son = ssd_tarama(X, A, B, C, 8, ilk)
        durum, beklenen = ilk.clone(), []
        for t in range(uzunluk):
            durum = torch.exp(A[:, t])[..., None, None] * durum + \
                X[:, t, :, :, None] * B[:, t, None, None, :]
            beklenen.append(torch.einsum("bhpn,bn->bhp", durum, C[:, t]))
        self.assertLess((y - torch.stack(beklenen, 1)).abs().max().item(), TOLERANS)
        self.assertLess((son - durum).abs().max().item(), TOLERANS)

    def test_parca_parca_vermek_tumuyle_ayni(self):
        """Minik'in 'surekli ic durum' iddiasi: metni parcalarla ve durumla vermek = tumunu vermek."""
        torch.manual_seed(1)
        model = ea.model_kur("ssm", KUCUK["ssm"]).eval()
        ids = torch.randint(0, 500, (2, 70))
        with torch.no_grad():
            tam, _ = model.durumla(ids)
            durum, parcalar = None, []
            for bas, son in ((0, 37), (37, 50), (50, 51), (51, 70)):  # parca boyuna denk gelmeyen kesimler
                cikti, durum = model.durumla(ids[:, bas:son], durum)
                parcalar.append(cikti)
        self.assertLess((torch.cat(parcalar, 1) - tam).abs().max().item(), TOLERANS)


class TestEgitim(unittest.TestCase):
    def test_bir_adimda_kayip_duser(self):
        for tur in ea.MODELLER:
            torch.manual_seed(2)
            model = ea.model_kur(tur, KUCUK[tur])
            veri = np.random.default_rng(0).integers(0, 500, 5000).astype(np.uint16)
            x, y = ea.rastgele_pencere(veri, 4, 32, np.random.default_rng(1), "cpu")
            opt = torch.optim.AdamW(model.parameters(), lr=1e-2)
            once = ea.kayip_hesapla(model, x, y)
            once.backward()
            opt.step()
            with torch.no_grad():
                sonra = ea.kayip_hesapla(model, x, y)
            self.assertLess(sonra.item(), once.item(), tur)

    def test_pencere_bir_kaydirilmis(self):
        veri = np.arange(1000, dtype=np.uint16)
        x, y = ea.rastgele_pencere(veri, 3, 16, np.random.default_rng(0), "cpu")
        self.assertTrue(torch.equal(x[:, 1:], y[:, :-1]))

    def test_ogrenme_orani_isinma_ve_kosinus(self):
        self.assertAlmostEqual(ea.ogrenme_orani(0, 100, 10, 1.0, 0.1), 0.1)
        self.assertAlmostEqual(ea.ogrenme_orani(10, 100, 10, 1.0, 0.1), 1.0)
        self.assertAlmostEqual(ea.ogrenme_orani(100, 100, 10, 1.0, 0.1), 0.1)


if __name__ == "__main__":
    unittest.main()
