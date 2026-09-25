"""Finalist B oyuncagi (hipokampus agirlikli): kucuk yogun govde + iki asamali ani deposu (1 bit imza taramasi,
64 adayda tam yeniden siralama) + tahmin hatasi kapili yazma + gece sayaci. Cagiran: tests/test_karalama.py.
"""

import numpy as np

from mimari_karalama import TOHUM, olc

SOZLUK = 512
TOKEN = 2000
GENISLIK = 64
ANI = 4096  # depodaki ani sayisi
ADAY = 64  # kaba taramadan ince siralamaya gecen aday (F3-180)
KOMSU = 8
IZ_UNUT = 0.7  # tek sabit katsayili iz: govdeye onceki tokenlerin ozeti; ogrenilmis matris yok
SURPRIZ_ESIGI = 1.0 / SOZLUK  # govde dogru tokene tekduze tahminden az olasilik verdiyse "sasirdi"
KARISIM = 0.3  # depo tahmininin payi (kNN-LM karisimi)
BAYT = 4  # float32
IMZA_BAYT = GENISLIK // 8  # 1 bit imza


def agirliklar():
    rng = np.random.default_rng(TOHUM)
    anahtar = rng.standard_normal((ANI, GENISLIK)).astype(np.float32)
    return {
        "gomme": rng.standard_normal((SOZLUK, GENISLIK)).astype(np.float32),
        "govde1": (rng.standard_normal((2 * GENISLIK, GENISLIK)) * 0.1).astype(np.float32),
        "govde2": (rng.standard_normal((GENISLIK, GENISLIK)) * 0.1).astype(np.float32),
        "cikis": rng.standard_normal((SOZLUK, GENISLIK)).astype(np.float32),
        "anahtar": anahtar,
        "imza": np.where(anahtar > 0, 1.0, -1.0).astype(np.float32),  # bellekte 1 bit, hesapta +-1
        "deger": rng.integers(0, SOZLUK, ANI),
    }


def govde(w, ids):
    """Gomme + tek iz -> iki yogun katman. Token arasi durum yalniz iz; tasiyici govde yogun MLP."""
    x = w["gomme"][ids]
    iz = np.empty_like(x)
    durum = np.zeros(GENISLIK, np.float32)
    for t in range(len(x)):
        iz[t] = durum
        durum = IZ_UNUT * durum + (1 - IZ_UNUT) * x[t]
    h = np.tanh(np.concatenate([x, iz], axis=1) @ w["govde1"])
    return np.tanh(h @ w["govde2"])


def depo_oku(w, sorgu):
    """Kaba: butun 1 bit imzalar Hamming ile taranir. Ince: en iyi 64 aday tam vektorle siralanir."""
    kaba = np.where(sorgu > 0, 1.0, -1.0).astype(np.float32) @ w["imza"].T
    aday = np.argpartition(-kaba, ADAY, axis=1)[:, :ADAY]
    ince = np.einsum("td,tkd->tk", sorgu, w["anahtar"][aday])
    en_iyi = np.take_along_axis(aday, np.argsort(-ince, axis=1)[:, :KOMSU], axis=1)
    dagilim = np.zeros((len(sorgu), SOZLUK), np.float32)
    np.add.at(dagilim, (np.arange(len(sorgu))[:, None], w["deger"][en_iyi]), 1.0 / KOMSU)
    return dagilim, en_iyi


def surpriz_kapisi(olasilik, hedef):
    """Tahmin hatasi kapisi (F3-073 + F3-201): yalniz sasirtan token gunduz depoya yazilir."""
    return olasilik[np.arange(len(hedef)), hedef] < SURPRIZ_ESIGI


def gece_sayaci(en_iyi):
    """K38=A: gunduz her aninin kac kez cagrildigi sayilir; gece en sik cagrilanlar agirliga tasinir."""
    return np.bincount(en_iyi.ravel(), minlength=ANI)


def dokunulan_bayt():
    """Token basina: govde tamami + cikis basi + butun imzalar (kaba tarama) + 64 tam anahtar + 8 deger."""
    govde_bayt = 3 * GENISLIK * GENISLIK * BAYT + GENISLIK * BAYT
    cikis = SOZLUK * GENISLIK * BAYT
    return govde_bayt + cikis + ANI * IMZA_BAYT + ADAY * GENISLIK * BAYT + KOMSU * BAYT


def toplam_bayt(w):
    yogun = sum(w[a].size for a in ("gomme", "govde1", "govde2", "cikis", "anahtar")) * BAYT
    return yogun + ANI * IMZA_BAYT + w["deger"].size * BAYT


def forward(ids):
    w = agirliklar()
    h = govde(w, ids)
    logit = h @ w["cikis"].T
    olasilik = np.exp(logit - logit.max(axis=1, keepdims=True))
    olasilik /= olasilik.sum(axis=1, keepdims=True)
    depo, en_iyi = depo_oku(w, h)
    karisik = (1 - KARISIM) * olasilik + KARISIM * depo
    yazilacak = surpriz_kapisi(karisik[:-1], ids[1:])
    sayac = gece_sayaci(en_iyi)
    print(f"  B: sasirtan (depoya yazilacak) pay {yazilacak.mean():.3f}, en sik ani {sayac.max()} cagri")
    return karisik, dokunulan_bayt(), toplam_bayt(w)


if __name__ == "__main__":
    girdi = np.random.default_rng(TOHUM).integers(0, SOZLUK, TOKEN)
    olc("B hipokampus agirlikli", forward, girdi)
