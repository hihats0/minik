"""UzmanCocuk (K42-B hash uzmanli transformer) testi: sekil, nedensellik, E=1'de t15m ile ayni parametre
ve ayni hesap, token basina tek uzman. CPU, kucuk ayar. Cagiran: `python -m unittest`.
"""

import sys
import unittest
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cocuk import egit_araclari as ea
from cocuk.model_uzman import VARSAYILAN_AYAR, yonlendir

KUCUK = {"sozluk": 300, "boyut": 32, "katman": 2, "kafa": 4, "ara_boyut": 48, "baglam": 64}
T15M = {k: v for k, v in VARSAYILAN_AYAR.items() if k != "uzman"}
UZUNLUK, KESIM = 40, 20
TOLERANS = 1e-5


def kur(e, ayar=KUCUK):
    torch.manual_seed(0)
    return ea.model_kur("uzman", {**ayar, "uzman": e}).eval()


def rastgele_ids():
    return torch.randint(0, KUCUK["sozluk"], (2, UZUNLUK), generator=torch.Generator().manual_seed(1))


class TestUzman(unittest.TestCase):
    def test_cikti_sekli(self):
        for e in (1, 4):
            cikti = kur(e)(rastgele_ids())
            self.assertEqual(cikti.shape, (2, UZUNLUK, KUCUK["sozluk"]))

    def test_nedensellik(self):
        model, ids = kur(4), rastgele_ids()
        degismis = ids.clone()
        degismis[:, KESIM:] = (degismis[:, KESIM:] + 7) % KUCUK["sozluk"]
        with torch.no_grad():
            fark = (model(ids)[:, :KESIM] - model(degismis)[:, :KESIM]).abs().max()
        self.assertLess(fark.item(), TOLERANS)

    def test_e1_parametre_t15m_ile_esit(self):
        uzman = ea.parametre_sayisi(kur(1, T15M))
        transformer = ea.parametre_sayisi(ea.model_kur("transformer", T15M))
        self.assertEqual(uzman, transformer)

    def test_e1_ayni_hesap(self):
        uzman = kur(1)
        transformer = ea.model_kur("transformer", KUCUK).eval()
        durum = {}
        for ad, p in transformer.state_dict().items():
            parca = ad.split(".")
            if "mlp" in parca:  # (ara, boyut) Linear agirligi -> (1, boyut, ara) uzman tensoru
                durum[".".join(parca[:-1])] = p.T.unsqueeze(0)
            else:
                durum[ad] = p
        uzman.load_state_dict(durum)
        ids = rastgele_ids()
        with torch.no_grad():
            fark = (uzman(ids) - transformer(ids)).abs().max()
        self.assertLess(fark.item(), 1e-4)

    def test_token_basina_tek_uzman(self):
        ids = rastgele_ids()
        sira, sayilar = yonlendir(ids, 4)
        self.assertEqual(sorted(sira.tolist()), list(range(ids.numel())))  # her token bir kez
        self.assertEqual(sum(sayilar), ids.numel())
        beklenen = ids.reshape(-1) * 2_654_435_761 % 4
        grup = torch.repeat_interleave(torch.arange(4), torch.tensor(sayilar))
        self.assertTrue(torch.equal(beklenen[sira], grup))

    def test_e4_farkli_idler_farkli_uzman(self):
        ids = torch.arange(8).view(1, -1)
        _, sayilar = yonlendir(ids, 4)
        self.assertGreater(sum(s > 0 for s in sayilar), 1)

    def test_bir_uzmani_bozmak_yalniz_onun_tokenlerini_etkiler(self):
        model, ids = kur(4), rastgele_ids()
        uzman = ids.reshape(-1) * 2_654_435_761 % 4
        with torch.no_grad():
            once = model.bloklar[-1].mlp(torch.ones(2, UZUNLUK, KUCUK["boyut"]), yonlendir(ids, 4))
            model.bloklar[-1].mlp.asagi[0].add_(1.0)
            sonra = model.bloklar[-1].mlp(torch.ones(2, UZUNLUK, KUCUK["boyut"]), yonlendir(ids, 4))
        degisen = (once - sonra).abs().amax(-1).reshape(-1) > TOLERANS
        self.assertTrue(torch.equal(degisen, uzman == 0))


if __name__ == "__main__":
    unittest.main()
