"""D4 cocuk deneyi veri hazirligi: Turkce Vikipedi'yi indirir, temizler, ~50M kelimelik dilim
cikarir, %99 egitim / %1 dogrulama metnine ayirir. Cagiran: elle `python cocuk/veri_hazirla.py`.
"""

import json
import logging
import re
from pathlib import Path

VERI_DIZINI = Path(__file__).resolve().parent / "veri"
EGITIM_METNI = VERI_DIZINI / "egitim.txt"
DOGRULAMA_METNI = VERI_DIZINI / "dogrulama.txt"
SAYIM_DOSYASI = VERI_DIZINI / "sayim.json"

VERI_SETI = "wikimedia/wikipedia"
VERI_AYARI = "20231101.tr"
KARISTIRMA_TOHUMU = 42
HEDEF_KELIME = 50_000_000
EN_AZ_KELIME = 6  # Basliklar ve liste maddeleri bundan kisa kaliyor.
EN_FAZLA_RAKAM_ORANI = 0.3  # Uzerinde satir cogunlukla tablo artigi.
CUMLE_SONU = (".", "!", "?")
TABLO_ISARETLERI = ("|", "{{", "}}", "==", "\t")
DOGRULAMA_ARALIGI = 100  # Her 100 paragraftan biri dogrulamaya: %1.

log = logging.getLogger("veri_hazirla")


def temiz_mi(satir: str) -> bool:
    """Satir egitime girecek duzgun bir paragraf mi."""
    if len(satir.split()) < EN_AZ_KELIME:
        return False
    if not satir.endswith(CUMLE_SONU):
        return False
    if any(isaret in satir for isaret in TABLO_ISARETLERI):
        return False
    rakam = sum(harf.isdigit() for harf in satir)
    return rakam / len(satir) <= EN_FAZLA_RAKAM_ORANI


def makale_paragraflari(metin: str) -> list[str]:
    """Makale metnini temiz paragraflara boler; bosluklar teklenir."""
    satirlar = (re.sub(r"\s+", " ", s).strip() for s in metin.split("\n"))
    return [s for s in satirlar if temiz_mi(s)]


def dilimi_yaz(makaleler, egitim_yolu: Path, dogrulama_yolu: Path, hedef_kelime: int) -> dict:
    """Makalelerden hedef kelimeye ulasana kadar paragraf yazar; sayimlari dondurur."""
    sayim = {"makale": 0, "paragraf": 0, "kelime": 0, "karakter": 0,
             "egitim_paragraf": 0, "dogrulama_paragraf": 0}
    with open(egitim_yolu, "w", encoding="utf-8") as egitim, \
            open(dogrulama_yolu, "w", encoding="utf-8") as dogrulama:
        for metin in makaleler:
            if sayim["kelime"] >= hedef_kelime:
                break
            sayim["makale"] += 1
            for paragraf in makale_paragraflari(metin):
                dogrulamaya = sayim["paragraf"] % DOGRULAMA_ARALIGI == DOGRULAMA_ARALIGI - 1
                (dogrulama if dogrulamaya else egitim).write(paragraf + "\n")
                sayim["dogrulama_paragraf" if dogrulamaya else "egitim_paragraf"] += 1
                sayim["paragraf"] += 1
                sayim["kelime"] += len(paragraf.split())
                sayim["karakter"] += len(paragraf)
    return sayim


def vikipedi_makaleleri():
    """Turkce Vikipedi'yi indirir (HF onbellegi), karistirir, makale metinlerini verir."""
    from datasets import load_dataset  # Agir modul; testler bu dosyayi indirmeden kullanir.

    veri = load_dataset(VERI_SETI, VERI_AYARI, split="train")
    log.info("toplam makale: %d", len(veri))
    for satir in veri.shuffle(seed=KARISTIRMA_TOHUMU):
        yield satir["text"]


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    VERI_DIZINI.mkdir(parents=True, exist_ok=True)
    sayim = dilimi_yaz(vikipedi_makaleleri(), EGITIM_METNI, DOGRULAMA_METNI, HEDEF_KELIME)
    sayim.update(kaynak=f"{VERI_SETI} {VERI_AYARI}", lisans="CC BY-SA 4.0")
    SAYIM_DOSYASI.write_text(json.dumps(sayim, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("sayim: %s", sayim)


if __name__ == "__main__":
    main()
