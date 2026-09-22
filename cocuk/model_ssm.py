"""D4 cocuk deneyi: ~30M parametreli secici durum uzayi modeli (Mamba-2 tarzi), saf PyTorch.
Cagiran: cocuk/egit.py ve cocuk/degerlendir.py (model_kur uzerinden), tests/test_cocuk_model.py.
"""

import math

import torch
import torch.nn as nn
import torch.nn.functional as F

from cocuk.model_transformer import INIT_STD, RMSNorm

# Neden Mamba-2 (SSD) bicimi: her kafada A tek sayi oldugu icin tarama parcali matris carpimina
# donusur; saf PyTorch'ta hizli ve kararli. Mamba-1'in (kanal x durum) A'si bunu yapamaz.
VARSAYILAN_AYAR = {
    "sozluk": 16_000,
    "boyut": 512,
    "katman": 13,
    "genisleme": 2,  # Ic boyut = 2 x 512 = 1024.
    "durum": 64,  # Her kafanin durum genisligi (N).
    "kafa_boyutu": 64,  # 1024 / 64 = 16 kafa.
    "cekirdek": 4,  # Nedensel konvolusyon penceresi.
    "parca": 64,  # Tarama parca uzunlugu.
    "baglam": 512,
}
DT_ALT, DT_UST = 1e-3, 1e-1  # Baslangic adim boyu araligi (Mamba makalesi).
A_ALT, A_UST = 1.0, 16.0  # Baslangic sonum hizi araligi.


def parcali_toplam(x):
    """x: (..., T) -> (..., T, T); [i, j] = x[j+1] + ... + x[i] (i >= j), ustu -inf.
    exp'i "j adimindan i adimina kadar durum ne kadar sondu" demek."""
    uzunluk = x.size(-1)
    x = x[..., None].expand(*x.shape, uzunluk)
    alt = torch.tril(torch.ones(uzunluk, uzunluk, dtype=torch.bool, device=x.device), -1)
    toplam = torch.cumsum(x.masked_fill(~alt, 0), dim=-2)
    kosegen = torch.tril(torch.ones(uzunluk, uzunluk, dtype=torch.bool, device=x.device))
    return toplam.masked_fill(~kosegen, -torch.inf)


def ssd_tarama(X, A, B, C, parca, ilk_durum):
    """h_t = exp(A_t) h_{t-1} + B_t X_t, y_t = C_t h_t; parca icinde matris, parcalar arasi durum.
    X: (b,L,h,p) A: (b,L,h) B,C: (b,L,n) ilk_durum: (b,h,p,n). L parcanin kati olmali."""
    b, uzunluk, h, p = X.shape
    c = uzunluk // parca
    X, B, C = X.view(b, c, parca, h, p), B.view(b, c, parca, -1), C.view(b, c, parca, -1)
    A = A.view(b, c, parca, h).permute(0, 3, 1, 2)  # (b,h,c,l)
    A_kum = torch.cumsum(A, dim=-1)
    # 1) Parca ici: her adim ayni parcadaki onceki adimlari gorur.
    y_ic = torch.einsum("bcln,bcsn,bhcls,bcshp->bclhp", C, B, torch.exp(parcali_toplam(A)), X)
    # 2) Her parcanin sonunda biriken durum.
    sonum = torch.exp(A_kum[..., -1:] - A_kum)
    durumlar = torch.einsum("bcln,bhcl,bclhp->bchpn", B, sonum, X)
    # 3) Durumlari parcadan parcaya aktar (ilk_durum en basa).
    durumlar = torch.cat([ilk_durum[:, None], durumlar], dim=1)
    gecis = torch.exp(parcali_toplam(F.pad(A_kum[..., -1], (1, 0))))
    durumlar = torch.einsum("bhzc,bchpn->bzhpn", gecis, durumlar)
    onceki, son_durum = durumlar[:, :-1], durumlar[:, -1]
    # 4) Onceki parcalardan gelen durumun bu parcadaki ciktiya katkisi.
    y_dis = torch.einsum("bcln,bchpn,bhcl->bclhp", C, onceki, torch.exp(A_kum))
    return (y_ic + y_dis).reshape(b, uzunluk, h, p), son_durum


class Karistirici(nn.Module):
    """Mamba-2 katmani: girdiye bagli adim (dt), sabit boyutlu durum (kafa x p x n)."""

    def __init__(self, a):
        super().__init__()
        self.ic = a["genisleme"] * a["boyut"]
        self.n, self.p, self.parca = a["durum"], a["kafa_boyutu"], a["parca"]
        self.h = self.ic // self.p
        self.konv_kanal = self.ic + 2 * self.n
        self.giris = nn.Linear(a["boyut"], 2 * self.ic + 2 * self.n + self.h, bias=False)
        self.konv = nn.Conv1d(self.konv_kanal, self.konv_kanal, a["cekirdek"], groups=self.konv_kanal)
        dt = torch.exp(torch.empty(self.h).uniform_(math.log(DT_ALT), math.log(DT_UST)))
        self.dt_sapma = nn.Parameter(dt + torch.log(-torch.expm1(-dt)))  # softplus'in tersi
        self.A_log = nn.Parameter(torch.log(torch.empty(self.h).uniform_(A_ALT, A_UST)))
        self.D = nn.Parameter(torch.ones(self.h))
        self.norm = RMSNorm(self.ic)
        self.cikis = nn.Linear(self.ic, a["boyut"], bias=False)

    def bos_durum(self, b, cihaz):
        konv = torch.zeros(b, self.konv_kanal, self.konv.kernel_size[0] - 1, device=cihaz)
        return konv, torch.zeros(b, self.h, self.p, self.n, device=cihaz)

    def konv_uygula(self, xBC, konv_durum):
        """Nedensel konvolusyon; onceki parcanin son (cekirdek-1) girdisi durumdan gelir."""
        tam = torch.cat([konv_durum.to(xBC.dtype), xBC.transpose(1, 2)], dim=2)
        yeni_durum = tam[:, :, -konv_durum.shape[2]:]
        return F.silu(self.konv(tam)).transpose(1, 2), yeni_durum

    def forward(self, u, durum):
        b, uzunluk, _ = u.shape
        z, xBC, dt = self.giris(u).split([self.ic, self.konv_kanal, self.h], dim=-1)
        xBC, konv_durum = self.konv_uygula(xBC, durum[0])
        x, B, C = xBC.split([self.ic, self.n, self.n], dim=-1)
        dt = F.softplus(dt.float() + self.dt_sapma)  # (b,L,h)
        A = -torch.exp(self.A_log.float())
        x = x.float().view(b, uzunluk, self.h, self.p)
        eksik = (-uzunluk) % self.parca  # Sona sifir: A=0 (sonum yok), X=0 (girdi yok), durum bozulmaz.
        pad = lambda t: F.pad(t, (0, 0) * (t.dim() - 2) + (0, eksik))
        with torch.autocast(u.device.type, enabled=False):  # Tarama float32: exp birikimi kararli.
            y, ssm_durum = ssd_tarama(pad(x * dt[..., None]), pad(A * dt), pad(B.float()),
                                      pad(C.float()), self.parca, durum[1].float())
        y = y[:, :uzunluk] + x * self.D[:, None]
        y = self.norm((y.reshape(b, uzunluk, self.ic) * F.silu(z.float())).type_as(u))
        return self.cikis(y), (konv_durum, ssm_durum)


class SSMCocuk(nn.Module):
    def __init__(self, ayar=None):
        super().__init__()
        self.ayar = {**VARSAYILAN_AYAR, **(ayar or {})}
        a = self.ayar
        self.gomme = nn.Embedding(a["sozluk"], a["boyut"])
        self.normlar = nn.ModuleList(RMSNorm(a["boyut"]) for _ in range(a["katman"]))
        self.katmanlar = nn.ModuleList(Karistirici(a) for _ in range(a["katman"]))
        self.son_norm = RMSNorm(a["boyut"])
        for modul in self.modules():
            if isinstance(modul, (nn.Linear, nn.Embedding)):
                nn.init.normal_(modul.weight, std=INIT_STD)
        for k in self.katmanlar:  # Artik yola eklenen cikisi kucult (GPT-2 yontemi).
            nn.init.normal_(k.cikis.weight, std=INIT_STD / math.sqrt(2 * a["katman"]))

    def bos_durum(self, b, cihaz):
        return [k.bos_durum(b, cihaz) for k in self.katmanlar]

    def durumla(self, ids, durum=None):
        """ids: (b, L) -> (logit, yeni durum). Durum verilirse metin kaldigi yerden devam eder."""
        if durum is None:
            durum = self.bos_durum(ids.shape[0], ids.device)
        x, yeni = self.gomme(ids), []
        for norm, katman, d in zip(self.normlar, self.katmanlar, durum):
            cikti, d_yeni = katman(norm(x), d)
            x = x + cikti
            yeni.append(d_yeni)
        return F.linear(self.son_norm(x), self.gomme.weight), yeni

    def forward(self, ids):
        return self.durumla(ids)[0]
