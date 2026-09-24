"""Az-veri deneyi: Vikipedi egitim metninden kisa, sade cumleleri secer (TinyStories fikrinin
uretimsiz hali) ve her cumleyi EOS ile ayirip cocuk/veri/sade.bin'e yazar.
Cagiran: elle `python -m cocuk.sade_veri`; egitimde cocuk/az_egit.py okur.
"""

import json
import re

import numpy as np
import sentencepiece as spm

from cocuk import egit_araclari as ea

EN_AZ_KELIME = 3
EN_COK_KELIME = 10
EN_COK_BUYUK_HARF = 1  # ilk kelime disinda; ozel ad yigini ansiklopedi dilidir, sade degil
CUMLE_BOL = re.compile(r"(?<=[.!?])\s+")
IZINLI = re.compile(r"^[A-Za-zÇĞİÖŞÜçğıöşüâîû ,'’.!?-]+$")
BITIS = (".", "!", "?")
TOKENIZER_YOLU = ea.COCUK_DIZINI / "tokenizer" / "tr16k.model"


def sade_mi(cumle: str) -> bool:
    """Buyuk harfle baslayan, rakamsiz, parantezsiz, 3-10 kelime, en fazla bir ozel adli cumle."""
    kelimeler = cumle.split()
    if not EN_AZ_KELIME <= len(kelimeler) <= EN_COK_KELIME:
        return False
    if not cumle[0].isupper() or not cumle.endswith(BITIS) or not IZINLI.match(cumle):
        return False
    buyuk = sum(1 for k in kelimeler[1:] if k[0].isupper())
    return buyuk <= EN_COK_BUYUK_HARF


def sade_cumleler(satirlar):
    for satir in satirlar:
        for cumle in CUMLE_BOL.split(satir.strip()):
            if sade_mi(cumle):
                yield cumle


def yaz(kaynak="egitim.txt", hedef="sade.bin") -> dict:
    sp = spm.SentencePieceProcessor(model_file=str(TOKENIZER_YOLU))
    ids, cumle_sayisi = [], 0
    with open(ea.VERI_DIZINI / kaynak, encoding="utf-8") as f:
        for cumle in sade_cumleler(f):
            ids.extend(sp.encode(cumle) + [sp.eos_id()])
            cumle_sayisi += 1
    np.array(ids, dtype=np.uint16).tofile(ea.VERI_DIZINI / hedef)
    sayim = {"cumle": cumle_sayisi, "token": len(ids)}
    (ea.VERI_DIZINI / "sade_sayim.json").write_text(json.dumps(sayim), encoding="utf-8")
    return sayim


if __name__ == "__main__":
    print(yaz())
