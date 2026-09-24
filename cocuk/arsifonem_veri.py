"""T1 deneyi: egitim.bin ve dogrulama.bin'i arsifonem idlerine cevirip egitim_ars.bin,
dogrulama_ars.bin yazar (token sayisi ve konumlar ayni, kayip dogrudan kiyaslanir).
Cagiran: elle `python -m cocuk.arsifonem_veri`.
"""

import json

import numpy as np
import sentencepiece as spm

from cocuk import egit_araclari as ea
from cocuk.arsifonem import Donusturucu

PARCA = 5_000_000  # token; parca sinirinda yarim kalan kelimenin ilk eki yuzeyde kalir (ihmal edilir)
TOKENIZER_YOLU = ea.COCUK_DIZINI / "tokenizer" / "tr16k.model"


def cevir_dosya(d: Donusturucu, ad: str) -> dict:
    kaynak = ea.veri_ac(ad)
    hedef = np.empty(len(kaynak), dtype=np.uint16)
    for bas in range(0, len(kaynak), PARCA):
        hedef[bas:bas + PARCA] = d.cevir(kaynak[bas:bas + PARCA].tolist())
    hedef.tofile(ea.VERI_DIZINI / f"{ad}_ars.bin")
    return {"token": len(hedef), "soyut": int((hedef >= d.sp.get_piece_size()).sum())}


if __name__ == "__main__":
    donusturucu = Donusturucu(spm.SentencePieceProcessor(model_file=str(TOKENIZER_YOLU)))
    sayim = {ad: cevir_dosya(donusturucu, ad) for ad in ("dogrulama", "egitim")}
    sayim["sozluk"] = donusturucu.sozluk
    (ea.VERI_DIZINI / "arsifonem_sayim.json").write_text(json.dumps(sayim), encoding="utf-8")
    print(sayim)
