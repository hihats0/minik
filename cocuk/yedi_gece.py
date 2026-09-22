"""D4-c: tek komutla yedi gece: on egitim checkpoint'inden (cocuk/agirlik/<ad>/son.pt) baslar, gece 0
sinavi, sonra her gece egitim + sabah sinavi. Cagiran: elle `python -m cocuk.yedi_gece --ad .. --tur ..`.
"""

import argparse
import json
import logging
import time

import sentencepiece as spm
import torch

from cocuk import degerlendir as dg
from cocuk import ders_dogrula as dd
from cocuk import ders_uret
from cocuk import egit_araclari as ea
from cocuk import gece as gece_modulu
from cocuk.sabah_sinavi import KARNE_ADI, sabah_sinavi

GECE_LOG_ADI = "gece_log.jsonl"


def dersleri_oku(gece_sayisi: int) -> list[dict]:
    """gece_1..N dersleri; eksik ya da sizintili ders kosuyu baslamadan durdurur."""
    yollar = [ders_uret.DERS_DIZINI / f"gece_{n}.json" for n in range(1, gece_sayisi + 1)]
    eksik = [str(y) for y in yollar if not y.exists()]
    if eksik:
        raise FileNotFoundError(f"ders yok, once `python -m cocuk.ders_uret`: {eksik}")
    dersler = [json.loads(y.read_text("utf-8")) for y in yollar]
    if dd.sizinti_var(dersler):
        raise ValueError("sabah sorularindan biri egitim cumlelerinde geciyor (sizinti)")
    return dersler


def kayitci(yol):
    """Satiri hem jsonl dosyasina hem ekrana yazan fonksiyon dondurur."""
    def kayit(satir):
        satir = {"zaman": time.strftime("%Y-%m-%d %H:%M:%S"), **satir}
        with open(yol, "a", encoding="utf-8") as dosya:
            dosya.write(json.dumps(satir, ensure_ascii=False) + "\n")
        print(json.dumps(satir), flush=True)  # Konsol cp1254 olabilir: ekranda kacisli, dosyada UTF-8.
    return kayit


def calistir(ad: str, tur: str, gece_sayisi: int, cihaz) -> list[dict]:
    cikti = ea.AGIRLIK_DIZINI / ad
    if (cikti / KARNE_ADI).exists():
        raise FileExistsError(f"{cikti / KARNE_ADI} var: eski kosuyla karismasin, silin ya da baska ad")
    model, paket = dg.yukle(ad, cihaz)
    if paket["tur"] != tur:
        raise ValueError(f"checkpoint turu {paket['tur']}, istenen {tur}")
    sp = spm.SentencePieceProcessor(model_file=str(dg.TOKENIZER_YOLU))
    dersler, viki = dersleri_oku(gece_sayisi), ea.veri_ac("egitim")
    kayit = kayitci(cikti / GECE_LOG_ADI)
    karne = [sabah_sinavi(model, sp, dersler, 0, cikti, cihaz)]
    kayit({"olay": "sabah", **karne[-1]})
    for ders in dersler:
        torch.manual_seed(gece_modulu.TOHUM + ders["gece"])
        gece_modulu.geceyi_gecir(model, tur, sp, ders, viki, cihaz, cikti, kayit)
        karne.append(sabah_sinavi(model, sp, dersler, ders["gece"], cikti, cihaz))
        kayit({"olay": "sabah", **karne[-1]})
    return karne


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ad", required=True, help="on egitim dizini: cocuk/agirlik/<ad>/son.pt")
    p.add_argument("--tur", choices=sorted(ea.MODELLER), required=True)
    p.add_argument("--gece", type=int, default=ders_uret.GECE_SAYISI)
    p.add_argument("--cihaz", default="cuda" if torch.cuda.is_available() else "cpu")
    arg = p.parse_args()
    calistir(arg.ad, arg.tur, arg.gece, torch.device(arg.cihaz))
