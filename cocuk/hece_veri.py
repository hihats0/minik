"""Hece sinirli sozlugu kurar (hece16k.json) ve egitim/dogrulama metnini hece idlerine cevirip
egitim_hece.bin, dogrulama_hece.bin yazar. Cagiran: elle `python -m cocuk.hece_veri`.
"""

import collections
import itertools
import json

import numpy as np

from cocuk import egit_araclari as ea
from cocuk.hece import KELIME_BASI, metni_hecele
from cocuk.hece_token import EN_UZUN, OZEL, SOZLUK_YOLU, HeceTokenizer, kelimelere

ORNEK_SATIR = 100_000  # sozluk sayimi icin (araclar/hece_sinirli_olc.py ile ayni)
SOZLUK = 16_000
HARF_ESIGI = 50  # harf yedegi: ornekte en az 50 kez gecen karakter


def say(satirlar):
    tekil, coklu, harf = collections.Counter(), collections.Counter(), collections.Counter()
    for satir in satirlar:
        harf.update(satir.strip())
        for k in kelimelere(metni_hecele(satir)):
            tekil.update(k)
            for n in range(2, EN_UZUN + 1):
                coklu.update(("".join(k[i:i + n]), n) for i in range(len(k) - n + 1))
    return tekil, coklu, harf


def sozluk_kur() -> list[str]:
    """Ozel + '▁' + harf yedegi + en sik tek heceler (yarisi) + en cok token kazandiran n-gramlar."""
    with open(ea.VERI_DIZINI / "egitim.txt", encoding="utf-8") as f:
        tekil, coklu, harf = say(itertools.islice(f, ORNEK_SATIR))
    temel = OZEL + [KELIME_BASI] + sorted(h for h, n in harf.items() if n >= HARF_ESIGI and h != " ")
    tekler = [h for h, _ in tekil.most_common(SOZLUK // 2) if h not in temel]
    kalan = SOZLUK - len(temel) - len(tekler)
    # n-gram kazanci: siklik x (hece sayisi - 1) = bu parca sozluge girince kazanilan token sayisi
    sirali = sorted(coklu.items(), key=lambda kv: -kv[1] * (kv[0][1] - 1))
    gorulen = set(temel) | set(tekler)
    ekler = [g for (g, _), _ in sirali if g not in gorulen][:kalan]
    return temel + tekler + ekler


def cevir(tok: HeceTokenizer, ad: str) -> dict:
    ids = []
    with open(ea.VERI_DIZINI / f"{ad}.txt", encoding="utf-8") as f:
        for satir in f:
            ids.extend(tok.encode(satir) + [tok.eos_id()])
    np.array(ids, dtype=np.uint16).tofile(ea.VERI_DIZINI / f"{ad}_hece.bin")
    return {"token": len(ids), "unk": ids.count(0)}


if __name__ == "__main__":
    parcalar = sozluk_kur()
    SOZLUK_YOLU.write_text(json.dumps(parcalar, ensure_ascii=False), encoding="utf-8")
    tok = HeceTokenizer(parcalar)
    print({"sozluk": tok.get_piece_size(), **{ad: cevir(tok, ad) for ad in ("dogrulama", "egitim")}})
