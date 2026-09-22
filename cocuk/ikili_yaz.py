"""D4 cocuk deneyi: egitim ve dogrulama metnini token id'lerine cevirip uint16 ikili dosyaya yazar,
egitim dongusu np.memmap ile hizli okusun diye. Cagiran: elle `python cocuk/ikili_yaz.py`.
"""

import json
import logging
from pathlib import Path

import numpy as np
import sentencepiece as spm

COCUK_DIZINI = Path(__file__).resolve().parent
VERI_DIZINI = COCUK_DIZINI / "veri"
MODEL_YOLU = COCUK_DIZINI / "tokenizer" / "tr16k.model"
PARCALAR = {"egitim": VERI_DIZINI / "egitim.txt", "dogrulama": VERI_DIZINI / "dogrulama.txt"}
SAYIM_DOSYASI = VERI_DIZINI / "token_sayim.json"
ID_TIPI = np.uint16  # 16k sozluk 65.535 sinirinin altinda; int32'nin yarisi yer.
PARTI_BOYU = 20_000  # Paragraf; bellegi sinirli tutar.
IS_PARCACIGI = 8

log = logging.getLogger("ikili_yaz")


def paragraf_partileri(metin_yolu: Path, parti_boyu: int):
    """Metin dosyasini parti_boyu paragraflik listeler halinde verir."""
    parti = []
    with open(metin_yolu, encoding="utf-8") as dosya:
        for satir in dosya:
            parti.append(satir.rstrip("\n"))
            if len(parti) == parti_boyu:
                yield parti
                parti = []
    if parti:
        yield parti


def partiyi_kodla(sp, parti: list[str]) -> np.ndarray:
    """Her paragrafi kodlar, sonuna EOS koyar; paragraflar tek diziye eklenir."""
    kodlar = sp.encode(parti, num_threads=IS_PARCACIGI)
    eos = sp.eos_id()
    duz = [tid for ids in kodlar for tid in ids + [eos]]
    return np.array(duz, dtype=ID_TIPI)


def ikili_yaz(sp, metin_yolu: Path, cikti_yolu: Path) -> int:
    """Metni uint16 id dosyasina yazar, toplam token sayisini dondurur."""
    if sp.get_piece_size() > np.iinfo(ID_TIPI).max:
        raise ValueError("sozluk uint16'ya sigmiyor")
    toplam = 0
    with open(cikti_yolu, "wb") as cikti:
        for parti in paragraf_partileri(metin_yolu, PARTI_BOYU):
            dizi = partiyi_kodla(sp, parti)
            dizi.tofile(cikti)
            toplam += len(dizi)
    return toplam


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    sp = spm.SentencePieceProcessor(model_file=str(MODEL_YOLU))
    sayim = {}
    for ad, metin_yolu in PARCALAR.items():
        sayim[ad] = ikili_yaz(sp, metin_yolu, VERI_DIZINI / f"{ad}.bin")
        log.info("%s: %d token", ad, sayim[ad])
    SAYIM_DOSYASI.write_text(json.dumps(sayim, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
