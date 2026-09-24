"""Hece sinirli tokenizer (fikir 1): token hic hece sinirini kesmez, 1-4 heceyi birlestirebilir. tr16k ile
ayni arayuz (encode/decode/eos_id/get_piece_size), boylece degerlendir.py olculeri aynen calisir.
Cagiran: cocuk/hece_veri.py (sozluk kurar, veriyi cevirir), cocuk/az_olc.py (--hece), tests.
"""

import json

from cocuk import egit_araclari as ea
from cocuk.hece import KELIME_BASI, metni_hecele

SOZLUK_YOLU = ea.COCUK_DIZINI / "tokenizer" / "hece16k.json"
OZEL = ["<unk>", "<s>", "</s>"]  # tr16k ile ayni: EOS id 2
EN_UZUN = 4


def kelimelere(heceler: list[str]) -> list[list[str]]:
    kelimeler = []
    for h in heceler:
        if h.startswith(KELIME_BASI) or not kelimeler:
            kelimeler.append([])
        kelimeler[-1].append(h)
    return kelimeler


class HeceTokenizer:
    def __init__(self, parcalar: list[str] | None = None):
        parcalar = parcalar or json.loads(SOZLUK_YOLU.read_text("utf-8"))
        self.parca = OZEL + [p for p in parcalar if p not in OZEL]
        self.kimlik = {p: i for i, p in enumerate(self.parca)}

    def eos_id(self):
        return OZEL.index("</s>")

    def get_piece_size(self):
        return len(self.parca)

    def _harfle(self, hece: str) -> list[int]:
        """Sozlukte olmayan hece: '▁' ve harfleri ayri token; bilinmeyen harf <unk>."""
        cikti = [self.kimlik[KELIME_BASI]] if hece.startswith(KELIME_BASI) else []
        return cikti + [self.kimlik.get(h, 0) for h in hece.lstrip(KELIME_BASI)]

    def _kelime(self, k: list[str]) -> list[int]:
        """En uzun eslesme: once 4 heceyi, sonra 3, 2, 1'i dener."""
        ids, i = [], 0
        while i < len(k):
            for n in range(min(EN_UZUN, len(k) - i), 0, -1):
                aday = "".join(k[i:i + n])
                if aday in self.kimlik:
                    ids.append(self.kimlik[aday])
                    i += n
                    break
            else:
                ids.extend(self._harfle(k[i]))
                i += 1
        return ids

    def encode(self, metin: str) -> list[int]:
        return [i for k in kelimelere(metni_hecele(metin)) for i in self._kelime(k)]

    def decode(self, ids) -> str:
        metin = "".join(self.parca[i] for i in ids if i >= len(OZEL))
        return metin.replace(KELIME_BASI, " ").strip()
