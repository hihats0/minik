"""D4 cocuk deneyi: ~30M parametreli GPT tarzi decoder (RoPE, pre-norm RMSNorm, SwiGLU, bagli gomme).
Cagiran: cocuk/egit.py ve cocuk/degerlendir.py (model_kur uzerinden), tests/test_cocuk_model.py.
"""

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

# Secim gerekcesi: RoPE ogrenilen konuma gore parametresiz ve uzunluga iyi genellenir; SwiGLU ayni
# parametreyle GELU'dan dusuk kayip verir (LLaMA/Qwen ailesi bunu kullanir, SSM ile adil kiyas icin
# "bugunun iyi transformer'i" secildi).
VARSAYILAN_AYAR = {
    "sozluk": 16_000,
    "boyut": 512,
    "katman": 7,
    "kafa": 8,
    "ara_boyut": 1408,  # SwiGLU: 8/3 * 512 = 1365, 64'un katina yuvarlandi.
    "baglam": 512,
}
ROPE_TABANI = 10_000.0
INIT_STD = 0.02


class RMSNorm(nn.Module):
    """Ortalama cikarmayan katman normu; LayerNorm'dan ucuz, kalitesi ayni."""

    def __init__(self, boyut: int, eps: float = 1e-6):
        super().__init__()
        self.agirlik = nn.Parameter(torch.ones(boyut))
        self.eps = eps

    def forward(self, x):
        kare_ort = x.float().pow(2).mean(-1, keepdim=True)
        return (x.float() * torch.rsqrt(kare_ort + self.eps)).type_as(x) * self.agirlik


def rope_tablosu(baglam: int, kafa_boyutu: int):
    """Her konum ve frekans icin cos/sin tablosu; dikkat q ve k'yi bu acilarla dondurur."""
    frekans = 1.0 / (ROPE_TABANI ** (torch.arange(0, kafa_boyutu, 2).float() / kafa_boyutu))
    aci = torch.outer(torch.arange(baglam).float(), frekans)
    return torch.cos(aci), torch.sin(aci)


def rope_uygula(x, cos, sin):
    """x: (b, kafa, uzunluk, kafa_boyutu). Cift/tek eksen ciftlerini konuma gore dondurur."""
    uzunluk = x.shape[-2]
    cos, sin = cos[:uzunluk].to(x.dtype), sin[:uzunluk].to(x.dtype)
    x1, x2 = x[..., 0::2], x[..., 1::2]
    donmus = torch.stack((x1 * cos - x2 * sin, x1 * sin + x2 * cos), dim=-1)
    return donmus.flatten(-2)


class Dikkat(nn.Module):
    def __init__(self, ayar):
        super().__init__()
        self.kafa = ayar["kafa"]
        self.qkv = nn.Linear(ayar["boyut"], 3 * ayar["boyut"], bias=False)
        self.cikis = nn.Linear(ayar["boyut"], ayar["boyut"], bias=False)

    def forward(self, x, cos, sin):
        b, uzunluk, boyut = x.shape
        q, k, v = self.qkv(x).view(b, uzunluk, 3, self.kafa, boyut // self.kafa).unbind(2)
        q, k, v = (t.transpose(1, 2) for t in (q, k, v))
        q, k = rope_uygula(q, cos, sin), rope_uygula(k, cos, sin)
        y = F.scaled_dot_product_attention(q, k, v, is_causal=True)
        return self.cikis(y.transpose(1, 2).reshape(b, uzunluk, boyut))


class SwiGLU(nn.Module):
    def __init__(self, ayar):
        super().__init__()
        self.kapi = nn.Linear(ayar["boyut"], ayar["ara_boyut"], bias=False)
        self.yukari = nn.Linear(ayar["boyut"], ayar["ara_boyut"], bias=False)
        self.asagi = nn.Linear(ayar["ara_boyut"], ayar["boyut"], bias=False)

    def forward(self, x):
        return self.asagi(F.silu(self.kapi(x)) * self.yukari(x))


class Blok(nn.Module):
    """Pre-norm: normu dala girmeden once uygula, artik yol temiz kalir; derin agda kararli."""

    def __init__(self, ayar):
        super().__init__()
        self.norm1, self.norm2 = RMSNorm(ayar["boyut"]), RMSNorm(ayar["boyut"])
        self.dikkat, self.mlp = Dikkat(ayar), SwiGLU(ayar)

    def forward(self, x, cos, sin):
        x = x + self.dikkat(self.norm1(x), cos, sin)
        return x + self.mlp(self.norm2(x))


class TransformerCocuk(nn.Module):
    def __init__(self, ayar=None):
        super().__init__()
        self.ayar = {**VARSAYILAN_AYAR, **(ayar or {})}
        a = self.ayar
        self.gomme = nn.Embedding(a["sozluk"], a["boyut"])
        self.bloklar = nn.ModuleList(Blok(a) for _ in range(a["katman"]))
        self.son_norm = RMSNorm(a["boyut"])
        cos, sin = rope_tablosu(a["baglam"], a["boyut"] // a["kafa"])
        self.register_buffer("cos", cos, persistent=False)
        self.register_buffer("sin", sin, persistent=False)
        self.apply(self._baslat)
        # Derin agda artik yola eklenen cikislari kucult (GPT-2 yontemi).
        for ad, p in self.named_parameters():
            if ad.endswith("cikis.weight") or ad.endswith("asagi.weight"):
                nn.init.normal_(p, std=INIT_STD / math.sqrt(2 * a["katman"]))

    @staticmethod
    def _baslat(modul):
        if isinstance(modul, (nn.Linear, nn.Embedding)):
            nn.init.normal_(modul.weight, std=INIT_STD)

    def forward(self, ids):
        """ids: (b, uzunluk) -> logit (b, uzunluk, sozluk). Cikis katmani gomme matrisiyle bagli."""
        x = self.gomme(ids)
        for blok in self.bloklar:
            x = blok(x, self.cos, self.sin)
        return F.linear(self.son_norm(x), self.gomme.weight)
