"""Finalist A (gradyanli seyrek): dikkatsiz gomme + parametresiz iz + agac/hash/yogun yonlendirilmis uzman.
Cagiran: cocuk/egit_araclari.py (MODELLER["seyrek"]), az_egit/az_olc uzerinden; tests/test_model_seyrek.py.
"""
# Basitlestirmeler: kok/ek yerine "kelime basi mi" bayragi (SentencePiece'in bosluk isareti), SSE yok
# (soru govde), yavas iz her tokende guncellenir (rapordaki "her 8 tokende" yok).

from pathlib import Path

import sentencepiece as spm
import torch
import torch.nn as nn
import torch.nn.functional as F

TOKENIZER_YOLU = Path(__file__).resolve().parent / "tokenizer" / "tr16k.model"  # degerlendir.py ile ayni

VARSAYILAN_AYAR = {
    "sozluk": 16_000, "boyut": 256, "bloom": 16_384, "derinlik": 8, "yaprak_ara": 64,
    "baglam": 512, "yonlendirici": "agac",
}
HIZLI, YAVAS = 0.5, 0.95  # iki izin azalma katsayisi (rapor Finalist A)
IZ_SAYISI = 3  # x = [gomme ; hizli iz ; yavas iz]
BLOOM_CARPANLARI = ((1_000_003, 7_919), (998_244_353, 104_729), (19_260_817, 1_299_709))
HASH_CARPAN = 2_654_435_761  # Knuth carpimsal hash; yaprak = id * c % yaprak sayisi
KELIME_BASI = "▁"  # SentencePiece'in bosluk isareti
SERTLESTIRME = 0.01  # dugum kararlarinin entropisi bu katsayiyla kayba eklenir (FFF hardening)
INIT_STD = 0.02
EPS = 1e-6


def kelime_basi_tablosu(sozluk: int) -> torch.Tensor:
    """Her token id icin 1 (bosluk isaretiyle baslar = kelime basi) ya da 0 (kelime devami)."""
    sp = spm.SentencePieceProcessor(model_file=str(TOKENIZER_YOLU))
    adet = min(sozluk, sp.get_piece_size())
    bayrak = [int(sp.id_to_piece(i).startswith(KELIME_BASI)) for i in range(adet)]
    return torch.tensor(bayrak + [0] * (sozluk - adet), dtype=torch.long)


def iz_matrisi(baglam: int, katsayi: float) -> torch.Tensor:
    """Alt ucgen M[t, s] = (1-a) a^(t-s), s <= t: M @ e nedensel ustel ortalamadir."""
    konum = torch.arange(baglam, dtype=torch.float32)
    fark = konum[:, None] - konum[None, :]
    return torch.where(fark >= 0, (1 - katsayi) * katsayi ** fark.clamp(min=0), torch.zeros(()))


class Gomme(nn.Module):
    """Token + kelime ici konum + (onceki, simdiki) ikilisinin 3 Bloom satirinin toplami."""

    def __init__(self, a):
        super().__init__()
        self.token = nn.Embedding(a["sozluk"], a["boyut"])
        self.konum = nn.Embedding(2, a["boyut"])
        self.bloom = nn.Embedding(a["bloom"], a["boyut"])
        self.register_buffer("kelime_basi", kelime_basi_tablosu(a["sozluk"]), persistent=False)

    def forward(self, ids):
        onceki = F.pad(ids[:, :-1], (1, 0))  # ilk tokenin oncesi 0
        e = self.token(ids) + self.konum(self.kelime_basi[ids])
        for c1, c2 in BLOOM_CARPANLARI:
            e = e + self.bloom((onceki * c1 + ids * c2) % self.bloom.num_embeddings)
        return e


class Uzman(nn.Module):
    """2^derinlik yaprak, her biri boyut*3 -> yaprak_ara -> boyut (GELU). Agac ya da hash secer."""

    def __init__(self, a):
        super().__init__()
        self.tur, self.derinlik = a["yonlendirici"], a["derinlik"]
        yaprak, giris, ara = 2 ** a["derinlik"], IZ_SAYISI * a["boyut"], a["yaprak_ara"]
        self.w1 = nn.Parameter(torch.randn(giris, yaprak * ara) * INIT_STD)
        self.b1 = nn.Parameter(torch.zeros(yaprak * ara))
        self.w2 = nn.Parameter(torch.randn(yaprak * ara, a["boyut"]) * INIT_STD)
        self.b2 = nn.Parameter(torch.zeros(yaprak, a["boyut"]))
        if self.tur == "agac":
            self.dugum = nn.Linear(giris, yaprak - 1)  # her dugum bir dogrusal test
        self.yaprak, self.ara, self.yan_kayip, self.son_yapraklar = yaprak, ara, 0.0, None

    def yol_olasiligi(self, x):
        """Yumusak agac: her yaprak icin kokten yapraga sigmoid kararlarinin carpimi -> (N, yaprak)."""
        sag = torch.sigmoid(self.dugum(x).float())
        entropi = -(sag * sag.clamp_min(EPS).log() + (1 - sag) * (1 - sag).clamp_min(EPS).log())
        self.yan_kayip = SERTLESTIRME * entropi.mean()
        olasilik = x.new_ones(x.shape[0], 1)
        for d in range(self.derinlik):
            bas = 2 ** d - 1
            karar = sag[:, bas:bas + 2 ** d]
            olasilik = torch.stack((olasilik * (1 - karar), olasilik * karar), -1).flatten(1)
        return olasilik

    def sert_yaprak(self, x):
        """Agaci inerek token basina tek yaprak: sag cocuk 2i+2, sol 2i+1."""
        dugum = torch.zeros(x.shape[0], dtype=torch.long, device=x.device)
        for _ in range(self.derinlik):
            skor = (x * self.dugum.weight[dugum]).sum(-1) + self.dugum.bias[dugum]
            dugum = 2 * dugum + 1 + (skor > 0).long()
        return dugum - (self.yaprak - 1)

    def yumusak(self, x, olasilik):
        """Butun yapraklar tek matris carpimiyla; gizli birimler yol olasiligiyla agirliklanir."""
        gizli = F.gelu(x @ self.w1 + self.b1).view(-1, self.yaprak, self.ara)
        gizli = (gizli * olasilik.unsqueeze(-1).to(gizli.dtype)).flatten(1)
        return gizli @ self.w2 + olasilik.to(gizli.dtype) @ self.b2

    def sert(self, x, yaprak):
        """Her token yalniz kendi yapragini hesaplar; dongu kullanilan yapraklar uzerinde."""
        w1 = self.w1.view(x.shape[1], self.yaprak, self.ara)
        w2, b1 = self.w2.view(self.yaprak, self.ara, -1), self.b1.view(self.yaprak, self.ara)
        sira = yaprak.argsort()  # ayni yapraga gidenler yan yana: GPU'ya tek senkron (sayilar)
        sayilar = torch.bincount(yaprak, minlength=self.yaprak).tolist()
        parcalar = []
        for j, grup in enumerate(x[sira].split(sayilar)):
            if len(grup):
                gizli = F.gelu(grup @ w1[:, j].to(x.dtype) + b1[j].to(x.dtype))
                parcalar.append(gizli @ w2[j].to(x.dtype) + self.b2[j].to(x.dtype))
        birlesik = torch.cat(parcalar)
        return birlesik.new_empty(birlesik.shape).index_copy(0, sira, birlesik)

    def forward(self, x, ids):
        if self.tur == "hash":
            yaprak = ids * HASH_CARPAN % self.yaprak
        elif self.training:
            return self.yumusak(x, self.yol_olasiligi(x))
        else:
            yaprak = self.sert_yaprak(x)
        self.son_yapraklar = yaprak
        return self.sert(x, yaprak)


class Yogun(nn.Module):
    """Karsilastirma kolu: uzmanla ayni parametreli tek yogun FFN."""

    def __init__(self, a):
        super().__init__()
        giris, yaprak = IZ_SAYISI * a["boyut"], 2 ** a["derinlik"]
        uzman = (yaprak * a["yaprak_ara"] * (giris + 1 + a["boyut"]) + yaprak * a["boyut"]
                 + (yaprak - 1) * (giris + 1))
        ara = (uzman - a["boyut"]) // (giris + 1 + a["boyut"])
        self.ag = nn.Sequential(nn.Linear(giris, ara), nn.GELU(), nn.Linear(ara, a["boyut"]))
        self.yan_kayip = 0.0

    def forward(self, x, ids):
        return self.ag(x)


class SeyrekCocuk(nn.Module):
    def __init__(self, ayar=None):
        super().__init__()
        self.ayar = {**VARSAYILAN_AYAR, **(ayar or {})}
        a = self.ayar
        self.gomme = Gomme(a)
        izler = torch.stack([iz_matrisi(a["baglam"], k) for k in (HIZLI, YAVAS)])
        self.register_buffer("izler", izler, persistent=False)
        self.uzman = Yogun(a) if a["yonlendirici"] == "yogun" else Uzman(a)
        self.norm = nn.LayerNorm(a["boyut"])
        self.cikis = nn.Linear(a["boyut"], a["sozluk"])  # gommeyle bagli degil (rapor)
        for m in (self.gomme.token, self.gomme.konum, self.gomme.bloom, self.cikis):
            nn.init.normal_(m.weight, std=INIT_STD)

    @property
    def yan_kayip(self):
        return self.uzman.yan_kayip if self.training else 0.0

    def forward(self, ids):
        """ids: (b, uzunluk) -> logit (b, uzunluk, sozluk). Dikkat yok; gecmis yalniz iki izden gelir."""
        b, uzunluk = ids.shape
        e = self.gomme(ids)
        izler = self.izler[:, :uzunluk, :uzunluk].to(e.dtype)
        x = torch.cat([e, izler[0] @ e, izler[1] @ e], -1)
        u = self.uzman(x.view(b * uzunluk, -1), ids.reshape(-1)).view(b, uzunluk, -1)
        return self.cikis(self.norm(e + u.to(e.dtype)))
