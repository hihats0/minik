"""D4 cocuk deneyi Turkce tokenizer'i: egitim metninden SentencePiece modeli egitir ve kelime basina
token sayisini (fertility) Qwen3.5 tokenizer'iyla karsilastirir. Cagiran: elle `python cocuk/tokenizer_egit.py`.
"""

import json
import logging
import random
import re
from pathlib import Path

import sentencepiece as spm

COCUK_DIZINI = Path(__file__).resolve().parent
VERI_DIZINI = COCUK_DIZINI / "veri"
EGITIM_METNI = VERI_DIZINI / "egitim.txt"
DOGRULAMA_METNI = VERI_DIZINI / "dogrulama.txt"
MODEL_ONEKI = COCUK_DIZINI / "tokenizer" / "tr16k"
FERTILITY_DOSYASI = VERI_DIZINI / "fertility.json"

# 30M'lik modelde 16k x 512 bagli gomme ~8M parametre; 32k olsa butcenin yarisi gomme olurdu.
SOZLUK_BOYU = 16_000
KARAKTER_KAPSAMI = 0.9995  # Turkce harfler + nadir yabanci harfler; kalan bayt yedegine duser.
EGITIM_CUMLE_SAYISI = 3_000_000  # RAM'i asmamak icin paragraf orneklemi.
EN_UZUN_PARAGRAF = 16_384  # Bayt; varsayilan 4192 uzun Vikipedi paragraflarini atiyor.
OLCUM_CUMLE_SAYISI = 1_000
OLCUM_TOHUMU = 7
EN_AZ_OLCUM_KELIMESI = 3
QWEN_DEPOSU = "Qwen/Qwen3.5-4B"

log = logging.getLogger("tokenizer_egit")


def tokenizer_egit(metin_yolu: Path, model_oneki: Path, sozluk_boyu: int) -> None:
    """SentencePiece unigram modelini egitir; <model_oneki>.model dosyasini yazar."""
    model_oneki.parent.mkdir(parents=True, exist_ok=True)
    spm.SentencePieceTrainer.train(
        input=str(metin_yolu), model_prefix=str(model_oneki), vocab_size=sozluk_boyu,
        model_type="unigram", character_coverage=KARAKTER_KAPSAMI, byte_fallback=True,
        input_sentence_size=EGITIM_CUMLE_SAYISI, shuffle_input_sentence=True,
        max_sentence_length=EN_UZUN_PARAGRAF, split_digits=True, num_threads=8)


def cumleleri_sec(paragraflar: list[str], adet: int, tohum: int) -> list[str]:
    """Paragraflari cumlelere boler, en az 3 kelimelik cumlelerden sabit tohumla ornek alir."""
    cumleler = [c for p in paragraflar for c in re.split(r"(?<=[.!?])\s+", p)
                if len(c.split()) >= EN_AZ_OLCUM_KELIMESI]
    return random.Random(tohum).sample(cumleler, min(adet, len(cumleler)))


def fertility(cumleler: list[str], token_say) -> float:
    """Kelime basina ortalama token: toplam token / toplam kelime."""
    toplam_token = sum(token_say(c) for c in cumleler)
    toplam_kelime = sum(len(c.split()) for c in cumleler)
    return toplam_token / toplam_kelime


def qwen_token_sayici():
    """Qwen3.5 tokenizer.json'u HF'den indirir; token sayan fonksiyon dondurur."""
    from huggingface_hub import hf_hub_download
    from tokenizers import Tokenizer

    yol = hf_hub_download(QWEN_DEPOSU, "tokenizer.json")
    tok = Tokenizer.from_file(yol)
    return lambda cumle: len(tok.encode(cumle, add_special_tokens=False).ids)


def fertility_olc(model_yolu: Path) -> dict:
    """Ayni 1.000 dogrulama cumlesinde bizim ve Qwen tokenizer'inin fertility'sini olcer."""
    paragraflar = DOGRULAMA_METNI.read_text(encoding="utf-8").splitlines()
    cumleler = cumleleri_sec(paragraflar, OLCUM_CUMLE_SAYISI, OLCUM_TOHUMU)
    sp = spm.SentencePieceProcessor(model_file=str(model_yolu))
    sonuc = {"cumle": len(cumleler), "kelime": sum(len(c.split()) for c in cumleler),
             "bizim": round(fertility(cumleler, lambda c: len(sp.encode(c))), 3)}
    sonuc["qwen"] = round(fertility(cumleler, qwen_token_sayici()), 3)
    return sonuc


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    tokenizer_egit(EGITIM_METNI, MODEL_ONEKI, SOZLUK_BOYU)
    sonuc = fertility_olc(MODEL_ONEKI.with_suffix(".model"))
    FERTILITY_DOSYASI.write_text(json.dumps(sonuc, indent=2), encoding="utf-8")
    log.info("fertility: %s", sonuc)


if __name__ == "__main__":
    main()
