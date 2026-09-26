"""Kafa cevabindan <think>...</think> dusunce bloklarini ayiklar, dusunceyi kisa loglar (K26, Gemma-T1).
Cagiran: yuvalar/kafa.py (dusun)."""

import re

from ortak import log

YUVA_ADI = "kafa"
DUSUNCE_ACILIS = "<think>"
# Kapali bloklar once silinir; geriye kalan kapanmamis <think> cevabin kesildigi anlamina gelir.
KAPALI_BLOK = re.compile(r"<think>(.*?)</think>", re.DOTALL)
# Log sismesin diye dusuncenin yalniz basi yazilir.
LOG_DUSUNCE_UZUNLUGU = 200


def dusunce_ayikla(cevap, dogal_bitti=False):
    """Cevaptaki butun <think> bloklarini atar, kalan metni doner. Kapanmamis <think> varsa
    (uretim max_tokens'ta kesildi) ondan sonrasi dusunce sayilir. Ama model kendisi durduysa
    (dogal_bitti) ve disarida cevap yoksa, kapanmamis kisim cevabin kendisidir (26 Eyl, bos cevap).
    Ayiklanan dusunce loglanir; bos cevap 'hata' satiriyla loglanir (cevap yine de doner)."""
    dusunceler = KAPALI_BLOK.findall(cevap)
    kalan = KAPALI_BLOK.sub("", cevap)
    kesik = DUSUNCE_ACILIS in kalan
    if kesik:
        kalan, _, yarim = kalan.partition(DUSUNCE_ACILIS)
        if dogal_bitti and not kalan.strip():
            kalan = yarim
            log.yaz(YUVA_ADI, "dusunce_ayikla", 0, "ok", {"kapanmamis_cevap": True})
        else:
            dusunceler.append(yarim)
    kalan = kalan.strip()
    if dusunceler:
        ozet = " | ".join(d.strip() for d in dusunceler)[:LOG_DUSUNCE_UZUNLUGU]
        log.yaz(YUVA_ADI, "dusunce_ayikla", 0, "ok",
                {"blok": len(dusunceler), "kesik": kesik, "dusunce": ozet})
    if not kalan:
        log.yaz(YUVA_ADI, "dusunce_ayikla", 0, "hata",
                {"hata": "dusunce ayiklaninca cevap bos kaldi", "blok": len(dusunceler), "kesik": kesik})
    return kalan
