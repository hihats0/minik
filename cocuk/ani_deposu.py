"""T2 deneyi (dil agirlikta, bilgi anida): D4 cocugunun agirligina dokunmadan gecenin derslerini bir
ani deposuna yazar (kNN-LM, Khandelwal 2019) ve D4'un 7 gecelik sabah sinavlarini ayni sorularla tekrarlar.
Cagiran: elle `python -m cocuk.ani_deposu`; sonuc cocuk/agirlik/t2-ani-deposu/karne.json.
"""

import json
import math
import time

import sentencepiece as spm
import torch
import torch.nn.functional as F

from cocuk import degerlendir as dg
from cocuk import egit_araclari as ea
from cocuk import sabah_sinavi as ss

K = 16  # en yakin ani sayisi (kNN-LM makalesinin dusuk ucu)
LAMBDA = 0.25  # ani payi; makalenin Wikitext degeri, bu deneyde ONCEDEN secildi
SICAKLIK = 0.1  # kosinus benzerligi / sicaklik -> ani agirligi
DUYARLILIK = (0.1, 0.5)  # ana sonuca girmez, yalniz "lambda sonucu ne kadar oynatiyor" icin
GECE_SAYISI = 7
TABAN = "d4-transformer"
CIKTI = ea.AGIRLIK_DIZINI / "t2-ani-deposu"


class AniliModel(torch.nn.Module):
    """Donmus model + ani deposu. forward log-olasilik dondurur; log_softmax'i degismez, bu yuzden
    degerlendir.py ve sabah_sinavi.py'nin olculeri aynen calisir."""

    def __init__(self, model, lamda=LAMBDA):
        super().__init__()
        self.model, self.lamda = model, lamda
        self.anahtar = None  # (n, boyut) birim vektor
        self.deger = None  # (n,) sonraki token

    def gizli(self, ids):
        x = self.model.gomme(ids)
        for blok in self.model.bloklar:
            x = blok(x, self.model.cos, self.model.sin)
        return self.model.son_norm(x)

    @torch.no_grad()
    def yaz(self, ids):
        """Bir cumlenin her konumundaki durumu ve ardindan gelen tokeni depoya ekler."""
        h = F.normalize(self.gizli(ids[None, :-1])[0].float(), dim=-1)
        deger = ids[1:]
        self.anahtar = h if self.anahtar is None else torch.cat([self.anahtar, h])
        self.deger = deger if self.deger is None else torch.cat([self.deger, deger])

    def forward(self, ids):
        h = self.gizli(ids)
        lm = F.log_softmax(F.linear(h, self.model.gomme.weight).float(), dim=-1)
        if self.anahtar is None or self.lamda == 0:
            return lm
        benzerlik = F.normalize(h.float(), dim=-1) @ self.anahtar.T  # (b, u, n)
        en_iyi, sira = benzerlik.topk(min(K, len(self.deger)), dim=-1)
        agirlik = F.softmax(en_iyi / SICAKLIK, dim=-1)
        ani = torch.zeros_like(lm).scatter_add_(-1, self.deger[sira], agirlik)
        karisim = [lm + math.log(1 - self.lamda), torch.log(ani + 1e-12) + math.log(self.lamda)]
        return torch.logsumexp(torch.stack(karisim), dim=0)


def gece_cumleleri(ders: dict) -> list[str]:
    """D4 gecesinin egitim metni: bilgiler, cumlelemeleri ve okul cumleleri."""
    cumleler = list(ders["okul"])
    for b in ders["bilgiler"]:
        cumleler += [b["bilgi"], *b["cumlelemeler"]]
    return cumleler


def gece_yaz(anili, sp, ders, cihaz):
    for cumle in gece_cumleleri(ders):
        anili.yaz(torch.tensor([sp.eos_id()] + sp.encode(cumle) + [sp.eos_id()], device=cihaz))


def sabah(anili, sp, dersler, gece, cihaz) -> dict:
    return {"gece": gece, "ani": 0 if anili.deger is None else len(anili.deger),
            "dun": ss.bilgi_sinavi(anili, sp, dersler[gece - 1:gece], cihaz),
            "onceki_geceler": ss.bilgi_sinavi(anili, sp, dersler[:gece - 1], cihaz),
            "eski_sinav": dg.eski_sinavi_puanla(anili, sp, cihaz),
            "dilbilgisi_ciftleri": dg.ciftleri_puanla(anili, sp, cihaz)}


def kos(lamda, cihaz) -> list[dict]:
    model, _ = dg.yukle(TABAN, cihaz)
    sp = spm.SentencePieceProcessor(model_file=str(dg.TOKENIZER_YOLU))
    dersler = [json.loads((ea.COCUK_DIZINI / "dersler" / f"gece_{g}.json").read_text("utf-8"))
               for g in range(1, GECE_SAYISI + 1)]
    anili, karne = AniliModel(model, lamda).eval(), []
    for gece in range(1, GECE_SAYISI + 1):
        baslangic = time.time()
        gece_yaz(anili, sp, dersler[gece - 1], cihaz)
        satir = sabah(anili, sp, dersler, gece, cihaz)
        satir["yazma_ve_sinav_sn"] = round(time.time() - baslangic, 1)
        karne.append(satir)
    return karne


if __name__ == "__main__":
    cihaz = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    CIKTI.mkdir(exist_ok=True)
    sonuc = {str(l): kos(l, cihaz) for l in (LAMBDA, *DUYARLILIK)}
    (CIKTI / "karne.json").write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    for l, karne in sonuc.items():
        print(l, [(s["dun"]["dogru"], s["eski_sinav"]["dogru"]) for s in karne])
