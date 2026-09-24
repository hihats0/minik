"""Minik blogu v0 (beyin ilkesi: beklenen seye az enerji): D4 transformer'i ile ayni govde, ama ilk
2 katmandan sonraki her katmanin girisinde tek sayilik bir surpriz kapisi var; esigi gecmeyen token
blogu gercekten atlar (secilenler toplanir, islenir, yerine konur). Karar yalniz o tokena bakar
(gelecege bakmaz); homeostaz cezasi ortalama gecisi %50'de tutar. Cagiran: egit_araclari.model_kur("minik").
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

from cocuk.model_transformer import INIT_STD, Blok, TransformerCocuk

YOGUN_KATMAN = 2  # ilk katmanlar her tokeni isler: kapinin karar verecegi temsil once kurulmali
ESIK = 0.5
HEDEF_ORAN = 0.5  # enerji butcesi: kapili katmanlarda tokenlarin yarisi
BUTCE_KATSAYI = 1.0


def dondur(x, cos, sin):
    """RoPE, konumlari toplanmis tokenlar icin: cos/sin (b, 1, M, kafa_boyutu/2)."""
    x1, x2 = x[..., 0::2], x[..., 1::2]
    return torch.stack((x1 * cos - x2 * sin, x1 * sin + x2 * cos), dim=-1).flatten(-2)


class KapiliBlok(Blok):
    """Blok + surpriz kapisi. Bloga giren tokenlarin degisimi kapi olasiligiyla olceklenir, boylece
    kapi "bu token islenmeye degdi mi" sorusunu kayiptan ogrenir (Mixture-of-Depths yontemi)."""

    def __init__(self, ayar):
        super().__init__(ayar)
        self.kapi = nn.Linear(ayar["boyut"], 1)

    def dal(self, xs, cos, sin, gecerli):
        """Secilmis tokenlarda dikkat (yalniz secilmislere, nedensel) + MLP; toplam degisimi dondurur."""
        b, m, boyut = xs.shape
        kafa = self.dikkat.kafa
        q, k, v = self.dikkat.qkv(self.norm1(xs)).view(b, m, 3, kafa, boyut // kafa).unbind(2)
        q, k, v = (t.transpose(1, 2) for t in (q, k, v))
        q, k = dondur(q, cos, sin), dondur(k, cos, sin)
        ucgen = torch.ones(m, m, dtype=torch.bool, device=xs.device).tril()
        maske = (ucgen[None, None] & gecerli[:, None, None, :]) | torch.eye(m, dtype=torch.bool,
                                                                             device=xs.device)
        y = F.scaled_dot_product_attention(q, k, v, attn_mask=maske)
        a = self.dikkat.cikis(y.transpose(1, 2).reshape(b, m, boyut))
        return a + self.mlp(self.norm2(xs + a))

    def forward(self, x, cos, sin):
        p = torch.sigmoid(self.kapi(x).float()).squeeze(-1)  # (b, uzunluk)
        secim = p > ESIK
        self.yumusak_oran, self.oran = p.mean(), secim.float().mean().detach()
        sayi = secim.sum(1)
        m = int(sayi.max())
        if m == 0:
            return x
        # Secilenler basa, sirasi korunarak (kararli siralama); fazlasi dolgu, agirligi 0.
        sira = torch.argsort((~secim).to(torch.int8), dim=1, stable=True)[:, :m]
        gecerli = torch.arange(m, device=x.device)[None] < sayi[:, None]
        indeks = sira[..., None].expand(-1, -1, x.shape[-1])
        degisim = self.dal(torch.gather(x, 1, indeks), cos[sira][:, None], sin[sira][:, None], gecerli)
        agirlik = (torch.gather(p, 1, sira) * gecerli)[..., None].to(degisim.dtype)
        return x.scatter_add(1, indeks, degisim * agirlik)


class MinikCocuk(TransformerCocuk):
    def __init__(self, ayar=None):
        super().__init__(ayar)
        a = self.ayar
        self.bloklar = nn.ModuleList(Blok(a) if i < YOGUN_KATMAN else KapiliBlok(a)
                                     for i in range(a["katman"]))
        self.apply(self._baslat)
        for ad, p in self.named_parameters():
            if ad.endswith("cikis.weight") or ad.endswith("asagi.weight"):
                nn.init.normal_(p, std=INIT_STD / (2 * a["katman"]) ** 0.5)
            if ad.endswith("kapi.bias"):
                nn.init.zeros_(p)  # basta p ~ 0,5: tokenlarin yarisi gecer

    def forward(self, ids):
        x = self.gomme(ids)
        for blok in self.bloklar:
            x = blok(x, self.cos, self.sin)
        kapililar = [b for b in self.bloklar if isinstance(b, KapiliBlok)]
        self.yan_kayip = BUTCE_KATSAYI * sum((b.yumusak_oran - HEDEF_ORAN) ** 2 for b in kapililar)
        self.gecis_orani = sum(b.oran for b in kapililar).item() / len(kapililar)
        return F.linear(self.son_norm(x), self.gomme.weight)
