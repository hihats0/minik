"""K42-B: t15m transformer, her blogun SwiGLU'su yerine E uzmanli hash karisimi (Hash Layers, Roller 2021).
Cagiran: cocuk/egit_araclari.py (MODELLER["uzman"]), az_egit/az_olc uzerinden; tests/test_model_uzman.py.
"""
# Dikkat, norm, RoPE, gomme ve baslatma TransformerCocuk'tan gelir; yalniz MLP ve forward dongusu yeni.

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

from cocuk.model_seyrek import HASH_CARPAN
from cocuk.model_transformer import INIT_STD, TransformerCocuk

VARSAYILAN_AYAR = {  # t15m kolu (araclar/az_deney_kosu.py) + uzman sayisi
    "sozluk": 16_000, "boyut": 384, "katman": 6, "kafa": 6, "ara_boyut": 1024, "baglam": 512,
    "uzman": 4,
}


def yonlendir(ids, uzman_sayisi: int):
    """Token basina tek uzman: id * c % E. Sira ve grup boylari bir kez hesaplanir, butun katmanlar
    ayni tabloyu kullanir (id katmanda degismez); .tolist() tek GPU senkronudur."""
    uzman = ids.reshape(-1) * HASH_CARPAN % uzman_sayisi
    sira = uzman.argsort()
    sayilar = torch.bincount(uzman, minlength=uzman_sayisi).tolist()
    return sira, sayilar


class UzmanSwiGLU(nn.Module):
    """E tane t15m SwiGLU'su (kapi, yukari, asagi; bias yok), agirliklar (E, ...) tensorlerde."""

    def __init__(self, a):
        super().__init__()
        e, boyut, ara = a["uzman"], a["boyut"], a["ara_boyut"]
        kucuk_std = INIT_STD / math.sqrt(2 * a["katman"])  # GPT-2 kucultmesi, TransformerCocuk gibi
        self.kapi = nn.Parameter(torch.randn(e, boyut, ara) * INIT_STD)
        self.yukari = nn.Parameter(torch.randn(e, boyut, ara) * INIT_STD)
        self.asagi = nn.Parameter(torch.randn(e, ara, boyut) * kucuk_std)

    def forward(self, x, yol):
        """x: (b, uzunluk, boyut). Uzmana gore sirala, grupla, her grup kendi SwiGLU'su, geri yerlestir."""
        sira, sayilar = yol
        duz = x.reshape(-1, x.shape[-1])
        parcalar = []
        for j, grup in enumerate(duz[sira].split(sayilar)):
            if len(grup):
                gizli = F.silu(grup @ self.kapi[j]) * (grup @ self.yukari[j])
                parcalar.append(gizli @ self.asagi[j])
        birlesik = torch.cat(parcalar)
        return birlesik.new_empty(birlesik.shape).index_copy(0, sira, birlesik).view_as(x)


class UzmanCocuk(TransformerCocuk):
    def __init__(self, ayar=None):
        super().__init__({**VARSAYILAN_AYAR, **(ayar or {})})
        for blok in self.bloklar:
            blok.mlp = UzmanSwiGLU(self.ayar)

    def forward(self, ids):
        """ids: (b, uzunluk) -> logit (b, uzunluk, sozluk). Blok.forward yerine yol tablosunu gecirir."""
        yol = yonlendir(ids, self.ayar["uzman"])
        x = self.gomme(ids)
        for blok in self.bloklar:
            x = x + blok.dikkat(blok.norm1(x), self.cos, self.sin)
            x = x + blok.mlp(blok.norm2(x), yol).to(x.dtype)
        return F.linear(self.son_norm(x), self.gomme.weight)
