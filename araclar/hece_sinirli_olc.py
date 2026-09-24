"""Fikir "hece sinirli token" CPU olcumu: hece n-gramlarindan (kelime ici, 1-4 hece) 16k sozluk, en uzun
eslesmeyle bolme; token hic hece sinirini kesmez. Kelime basina token tr16k ile ayni dogrulama metninde.
Cagiran: elle `PYTHONPATH=. python araclar/hece_sinirli_olc.py`.
"""

import collections
import itertools
import json

import sentencepiece as spm

from cocuk import egit_araclari as ea
from cocuk.hece import KELIME_BASI, metni_hecele

ORNEK_SATIR = 100_000
EN_UZUN = 4
SOZLUK = 16_000
DOGRULAMA_SATIR = 3_000


def kelimelere(heceler: list[str]) -> list[list[str]]:
    kelimeler = []
    for h in heceler:
        if h.startswith(KELIME_BASI) or not kelimeler:
            kelimeler.append([])
        kelimeler[-1].append(h)
    return kelimeler


def sozluk_kur(satirlar) -> set:
    """Tek heceler once (kapsama), kalan yere en cok token kazandiran n-gramlar (siklik x (n-1))."""
    tekil, coklu = collections.Counter(), collections.Counter()
    for satir in satirlar:
        for k in kelimelere(metni_hecele(satir)):
            tekil.update(k)
            for n in range(2, EN_UZUN + 1):
                coklu.update(tuple(k[i:i + n]) for i in range(len(k) - n + 1))
    tekler = [h for h, _ in tekil.most_common(SOZLUK // 2)]
    kazanc = sorted(coklu.items(), key=lambda kv: -kv[1] * (len(kv[0]) - 1))
    return set((h,) for h in tekler) | {g for g, _ in kazanc[:SOZLUK - len(tekler)]}


def bol(kelime: list[str], sozluk: set) -> int:
    """En uzun eslesme; sozlukte olmayan tek hece harflerine duser (harf sayisi kadar token)."""
    i = sayi = 0
    while i < len(kelime):
        for n in range(min(EN_UZUN, len(kelime) - i), 0, -1):
            if tuple(kelime[i:i + n]) in sozluk:
                i, sayi = i + n, sayi + 1
                break
        else:
            sayi, i = sayi + len(kelime[i]), i + 1
    return sayi


def main():
    with open(ea.VERI_DIZINI / "egitim.txt", encoding="utf-8") as f:
        sozluk = sozluk_kur(itertools.islice(f, ORNEK_SATIR))
    sp = spm.SentencePieceProcessor(model_file=str(ea.COCUK_DIZINI / "tokenizer" / "tr16k.model"))
    hece_tok = tr16k_tok = kelime = 0
    with open(ea.VERI_DIZINI / "dogrulama.txt", encoding="utf-8") as f:
        for satir in itertools.islice(f, DOGRULAMA_SATIR):
            kelime += len(satir.split())
            hece_tok += sum(bol(k, sozluk) for k in kelimelere(metni_hecele(satir)))
            tr16k_tok += len(sp.encode(satir))
    print(json.dumps({"kelime": kelime, "hece_sinirli_token_kelime": round(hece_tok / kelime, 3),
                      "tr16k_token_kelime": round(tr16k_tok / kelime, 3), "sozluk": len(sozluk)}))


if __name__ == "__main__":
    main()
