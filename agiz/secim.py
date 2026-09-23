"""Komut satirindan agiz secer: `--agiz konsol` (varsayilan) ya da `--agiz dosya --girdi X --cikti Y`.
Yuva dosyalarina dokunmadan agiz degistirmenin tek yeri. Cagiran: minik.py (__main__)."""

import argparse

from agiz import dosya, konsol

KONSOL = "konsol"


def agiz_sec(argumanlar=None):
    """(dinle, soyle, platform) dondurur; platform Defter kaydinin `platform` alanina yazilir."""
    ayristirici = argparse.ArgumentParser(description="Minik ile konus")
    ayristirici.add_argument("--agiz", choices=[KONSOL, dosya.PLATFORM], default=KONSOL)
    ayristirici.add_argument("--girdi", default=str(dosya.VARSAYILAN_GIRDI))
    ayristirici.add_argument("--cikti", default=str(dosya.VARSAYILAN_CIKTI))
    secim = ayristirici.parse_args(argumanlar)
    if secim.agiz == KONSOL:
        return konsol.dinle, konsol.soyle, KONSOL
    agiz = dosya.DosyaAgzi(secim.girdi, secim.cikti)
    return agiz.dinle, agiz.soyle, dosya.PLATFORM
