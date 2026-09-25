"""Az-veri deneyinin testi: sade cumle suzgeci, enerji integrali, Muon parametre ayrimi, karisik
batch payi ve tamamlamada bosluk duzeltmesi. CPU, kucuk ayar. Cagiran: `python -m unittest`.
"""

import argparse
import sys
import unittest
from pathlib import Path

import numpy as np
import torch

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

sys.path.insert(0, str(KOK / "araclar"))

import az_analiz
from cocuk import ani_deposu, arsifonem, az_egit, az_olc, egit_araclari as ea, hece
from cocuk.guc_olcer import GucOlcer, enerji_wh
from cocuk.sade_veri import sade_mi

KUCUK = {"katman": 2, "boyut": 64, "kafa": 4, "ara_boyut": 128, "sozluk": 500}


class SahteSP:
    """Kelime basina bir id; decode bastaki boslugu dusurur (SentencePiece gibi)."""

    def __init__(self):
        self.kelimeler = ["<eos>", "Ben", "okula", "gitti."]

    def eos_id(self):
        return 0

    def encode(self, metin):
        return [self.kelimeler.index(k) for k in metin.split()]

    def decode(self, ids):
        return " ".join(self.kelimeler[i] for i in ids if i)


class SiraliModel(torch.nn.Module):
    """Her zaman 'gitti.' (id 3) uretir."""

    def forward(self, ids):
        logit = torch.zeros(1, ids.shape[1], 4)
        logit[..., 3] = 1.0
        return logit


class TestAzDeney(unittest.TestCase):
    def test_sade_suzgec(self):
        self.assertTrue(sade_mi("Kedi evde uyuyor."))
        for kotu in ("Kedi 1992 yilinda dogdu.", "kedi evde uyuyor.", "Kedi (evcil) uyur.",
                     "Kedi.", "Ali Veli Ayse Fatma geldi.", "Kedi evde uyuyor"):
            self.assertFalse(sade_mi(kotu), kotu)

    def test_enerji_integrali(self):
        # 100 W sabit, 36 sn -> 1 Wh
        self.assertAlmostEqual(enerji_wh([(0, 100.0), (18, 100.0), (36, 100.0)]), 1.0)

    def test_guc_olcer_okunamayani_sayar(self):
        okumalar = iter([50.0, None, 50.0] + [None] * 100)
        with GucOlcer(okuyucu=lambda: next(okumalar), aralik=0.01) as olcer:
            import time
            time.sleep(0.1)
        self.assertGreaterEqual(olcer.okunamayan, 1)
        self.assertEqual(olcer.ort_watt, 50.0)

    def test_muon_gommeyi_almaz(self):
        model = ea.model_kur("transformer", KUCUK)
        arg = argparse.Namespace(optimizer="muon", lr=1e-3)
        muon, adamw = az_egit.optimizerlar(model, arg)
        muon_idleri = {id(p) for g in muon.param_groups for p in g["params"]}
        self.assertNotIn(id(model.gomme.weight), muon_idleri)
        self.assertTrue(all(p.dim() == 2 for g in muon.param_groups for p in g["params"]))
        toplam = sum(len(g["params"]) for o in (muon, adamw) for g in o.param_groups)
        self.assertEqual(toplam, len(list(model.parameters())))

    def test_karisik_batch_payi(self):
        egitim = np.full(5000, 7, dtype=np.uint16)
        sade = np.full(5000, 9, dtype=np.uint16)
        arg = argparse.Namespace(batch=16, sade_oran=0.25, baglam=32, cihaz="cpu")
        x, _ = az_egit.karisik_pencere((egitim, sade), arg, np.random.default_rng(0))
        self.assertEqual(x.shape[0], 16)
        self.assertEqual(int((x[:, 0] == 9).sum()), 4)

    def test_tamamlama_boslugu_korur(self):
        cumle = az_olc.tamamla(SiraliModel(), SahteSP(), "Ben okula", "cpu")
        self.assertEqual(cumle, "Ben okula gitti.")

    def test_tamamlama_olculeri(self):
        o = az_olc.tamamlama_olculeri(["Kedi 1992 yil.", "Ben okulagitti"], ["Kedi", "Ben"],
                                      {"yil", "okula", "gitti"})
        self.assertEqual((o["rakamli"], o["cumle_bitti"]), (1, 1))
        self.assertAlmostEqual(o["gercek_kelime_orani"], 0.5)

    def test_welch_bilinen_deger(self):
        # t = 3,674, serbestlik 4 -> iki yonlu p = 0,0213 (t tablosu)
        self.assertAlmostEqual(az_analiz.welch_p([1, 2, 3], [4, 5, 6]), 0.0213, places=3)
        self.assertGreater(az_analiz.welch_p([1, 2, 3], [1, 2, 3.1]), 0.9)

    def test_holm_tekduze(self):
        d = az_analiz.holm({"x": 0.01, "y": 0.04, "z": 0.03})
        self.assertEqual((round(d["x"], 3), round(d["z"], 3), round(d["y"], 3)), (0.03, 0.06, 0.06))

    def test_ani_deposu_olasilik_ve_lambda0(self):
        torch.manual_seed(0)
        model = ea.model_kur("transformer", KUCUK).eval()
        ids = torch.randint(0, 500, (1, 12))
        anili = ani_deposu.AniliModel(model, lamda=0.25)
        anili.yaz(ids[0])
        with torch.no_grad():
            olasilik = anili(ids).exp().sum(-1)
            self.assertTrue(torch.allclose(olasilik, torch.ones_like(olasilik), atol=1e-4))
            anili.lamda = 0.0
            taban = torch.log_softmax(model(ids).float(), -1)
            self.assertTrue(torch.allclose(anili(ids), taban, atol=1e-5))

    def test_ani_deposu_hatirlar(self):
        # Depoya yazilan dizide ayni baglam gelince yazilan sonraki token daha olasi olmali.
        torch.manual_seed(0)
        model = ea.model_kur("transformer", KUCUK).eval()
        ids = torch.randint(0, 500, (1, 12))
        anili = ani_deposu.AniliModel(model, lamda=0.5)
        with torch.no_grad():
            once = anili(ids)[0, 5, ids[0, 6]].item()
            anili.yaz(ids[0])
            sonra = anili(ids)[0, 5, ids[0, 6]].item()
        self.assertGreater(sonra, once)

    def test_arsifonem_kural(self):
        self.assertEqual(arsifonem.soyutla("ler"), "lAr")
        self.assertEqual(arsifonem.soyutla("te"), "DA")
        self.assertEqual(arsifonem.gerceklestir("lAr", "kitap"), "lar")
        self.assertEqual(arsifonem.gerceklestir("lAr", "ev"), "ler")
        self.assertEqual(arsifonem.gerceklestir("DA", "kitap"), "ta")
        self.assertEqual(arsifonem.gerceklestir("DA", "okul"), "da")
        self.assertEqual(arsifonem.gerceklestir("I", "göz"), "ü")

    def test_arsifonem_gidis_donus_ve_istisna(self):
        import sentencepiece as spm
        sp = spm.SentencePieceProcessor(model_file=str(KOK / "cocuk/tokenizer/tr16k.model"))
        d = arsifonem.Donusturucu(sp)
        metin = "Kitaplarımızdan saatlerce okulda ders çalıştık."
        ids = sp.encode(metin)
        cevrilmis = d.cevir(ids)
        self.assertEqual(d.geri(cevrilmis), ids)
        self.assertGreater(sum(i >= sp.get_piece_size() for i in cevrilmis), 0)
        saat_sonrasi = cevrilmis[ids.index(sp.piece_to_id("▁saat")) + 1]
        self.assertLess(saat_sonrasi, sp.get_piece_size())  # alinti: kural "lerce"yi uretemez

    def test_minik_nedensel(self):
        torch.manual_seed(0)
        model = ea.model_kur("minik", {**KUCUK, "katman": 4}).eval()
        ids = torch.randint(0, 500, (2, 20))
        degisik = ids.clone()
        degisik[:, 12:] = torch.randint(0, 500, (2, 8))
        with torch.no_grad():
            self.assertTrue(torch.allclose(model(ids)[:, :12], model(degisik)[:, :12], atol=1e-5))
        self.assertTrue(0.0 <= model.gecis_orani <= 1.0)

    def test_kapi_hepsi_gecince_duz_blokla_ayni(self):
        from cocuk.model_minik import KapiliBlok
        from cocuk.model_transformer import Blok, rope_tablosu
        torch.manual_seed(0)
        kapili = KapiliBlok({**KUCUK, "baglam": 32})
        duz = Blok({**KUCUK, "baglam": 32})
        duz.load_state_dict({k: v for k, v in kapili.state_dict().items() if not k.startswith("kapi.")})
        torch.nn.init.constant_(kapili.kapi.bias, 30.0)  # p = 1: her token gecer, agirlik 1
        cos, sin = rope_tablosu(32, 16)
        x = torch.randn(2, 10, 64)
        with torch.no_grad():
            self.assertTrue(torch.allclose(kapili(x, cos, sin), duz(x, cos, sin), atol=1e-4))

    def test_kapiya_gradyan_ve_butce(self):
        torch.manual_seed(0)
        model = ea.model_kur("minik", {**KUCUK, "katman": 4})
        ids = torch.randint(0, 500, (2, 16))
        kayip = ea.kayip_hesapla(model, ids[:, :-1], ids[:, 1:]) + model.yan_kayip
        kayip.backward()
        kapi = model.bloklar[-1].kapi.weight.grad
        self.assertIsNotNone(kapi)
        self.assertGreater(kapi.abs().sum().item(), 0)

    def test_hece_kurali_ve_geri_donus(self):
        self.assertEqual(hece.hecele("kitaplarımızdan"), ["ki", "tap", "la", "rı", "mız", "dan"])
        self.assertEqual(hece.hecele("Türkçe"), ["Türk", "çe"])
        self.assertEqual(hece.hecele("saat"), ["sa", "at"])
        metin = "Kitaplarımızdan saatlerce okulda ders çalıştık."
        self.assertEqual(hece.birlestir(hece.metni_hecele(metin)), metin)

    def test_hece_tokenizer_gidis_donus(self):
        from cocuk.hece_token import HeceTokenizer
        tok = HeceTokenizer(["▁", "K", "i", "t", "a", "p", "▁ki", "tap", "▁kitap", "lar", "▁ev", "ler"])
        self.assertEqual(tok.eos_id(), 2)
        for metin in ("kitaplar evler", "Kitap"):
            self.assertEqual(tok.decode(tok.encode(metin)), metin)
        self.assertEqual(len(tok.encode("kitaplar")), 2)  # en uzun eslesme: ▁kitap + lar

    def test_bpc_birimi(self):
        # Rastgele (egitilmemis) modelin BPC'si log2(sozluk) x token/karakter civarinda, pozitif ve sonlu
        torch.manual_seed(0)
        model = ea.model_kur("transformer", KUCUK).eval()
        eski = az_olc.BPC_PARAGRAF
        try:
            az_olc.BPC_PARAGRAF = 3
            deger = az_olc.bpc(model, _SozlukSP(), "cpu")
        finally:
            az_olc.BPC_PARAGRAF = eski
        self.assertTrue(0 < deger < 20)

    def test_sohbet_ayiklama(self):
        from cocuk.sohbet_uret import sohbetleri_ayikla
        iyi = ["A: Merhaba!", "B: Merhaba, nasılsın?", "A: İyiyim.", "B: Ben de."]
        kotu_sira = ["A: Selam.", "A: Yine ben.", "B: Tamam.", "B: Peki."]
        kisa = ["A: Selam.", "B: Selam."]
        baslikli = ["Sohbet 1", "A: Selam.", "B: Selam.", "A: Naber?", "B: İyi."]
        metin = "###".join(chr(10).join(s) for s in (iyi, kotu_sira, kisa, baslikli))
        self.assertEqual(sohbetleri_ayikla(metin), [iyi])

    def test_merakli_kayip_sasirticiyi_secer(self):
        torch.manual_seed(0)
        model = ea.model_kur("transformer", KUCUK)
        x, y = torch.randint(0, 500, (2, 16)), torch.randint(0, 500, (2, 16))
        duz = az_egit.merakli_kayip(model, x, y, 1.0)
        merakli = az_egit.merakli_kayip(model, x, y, 0.5)
        self.assertGreater(merakli.item(), duz.item())  # en zor yari ortalamanin ustunde
        merakli.backward()
        self.assertIsNotNone(model.gomme.weight.grad)

    def test_mimari_hesap(self):
        import mimari_hesap
        h = mimari_hesap.hesapla(30.68e6, 1.0, 200e6, 16)
        self.assertAlmostEqual(h["egitim FLOP (6 x aktif x token)"], 6 * 30.68e6 * 200e6)
        self.assertAlmostEqual(h["laptop egitim saati (aktif hiz)"], 0.82, places=2)  # D4: 50 dk aktif
        seyrek = mimari_hesap.hesapla(30.68e6, 0.1, 200e6, 16)
        self.assertAlmostEqual(seyrek["token basina islem (cikarim)"], h["token basina islem (cikarim)"] / 10)
        self.assertEqual(seyrek["calisma bellegi GB (agirlik)"], h["calisma bellegi GB (agirlik)"])


class _SozlukSP:
    """bpc testi icin: her harf bir id (500'den kucuk)."""

    def eos_id(self):
        return 0

    def encode(self, metin):
        return [1 + ord(h) % 400 for h in metin]


if __name__ == "__main__":
    unittest.main()
