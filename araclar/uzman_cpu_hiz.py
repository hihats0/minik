"""K42-B: egitilmis cocuklarin CPU'da greedy uretim hizi (token/sn), tek cekirdek ve tum cekirdek.
Cagiran: elle `python araclar/uzman_cpu_hiz.py --ad u4-t1 u16-t1`; sonuc stdout'a ve loglar/'a JSON satiri.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import sentencepiece as spm
import torch

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from cocuk import degerlendir as dg

URETIM_TOKEN = 200
PENCERE = 512  # KV cache yok: her adimda son 512 token bastan hesaplanir
ISTEM = "Bugün hava çok güzel, ben de"
LOG_YOLU = KOK / "loglar" / "uzman_cpu_hiz.jsonl"


@torch.no_grad()
def hiz_olc(model, ids: list[int], cekirdek: int) -> float:
    """Acgozlu URETIM_TOKEN token uretir; saniye basina token dondurur (EOS'ta durmaz, sure sabit)."""
    torch.set_num_threads(cekirdek)
    ids = list(ids)
    baslangic = time.perf_counter()
    for _ in range(URETIM_TOKEN):
        ids.append(model(torch.tensor([ids[-PENCERE:]]))[0, -1].argmax().item())
    return URETIM_TOKEN / (time.perf_counter() - baslangic)


def olc(ad: str, ids: list[int]) -> dict:
    model, paket = dg.yukle(ad, torch.device("cpu"))
    tum = os.cpu_count()
    return {"zaman": time.strftime("%Y-%m-%d %H:%M:%S"), "ad": ad, "ayar": paket["ayar"],
            "tek_cekirdek_token_sn": round(hiz_olc(model, ids, 1), 2),
            "tum_cekirdek": tum, "tum_cekirdek_token_sn": round(hiz_olc(model, ids, tum), 2)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ad", nargs="+", required=True)
    a = p.parse_args()
    sp = spm.SentencePieceProcessor(model_file=str(dg.TOKENIZER_YOLU))
    ids = [sp.eos_id()] + sp.encode(ISTEM)
    LOG_YOLU.parent.mkdir(exist_ok=True)
    for ad in a.ad:
        satir = json.dumps(olc(ad, ids), ensure_ascii=False)
        print(satir)
        with open(LOG_YOLU, "a", encoding="utf-8") as f:
            f.write(satir + "\n")


if __name__ == "__main__":
    main()
