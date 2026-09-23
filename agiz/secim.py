"""Komut satirindan agiz secer: `--agiz konsol` (varsayilan), `dosya`, `site` ya da `x` (yerel kuyruk).
Yuva dosyalarina dokunmadan agiz degistirmenin tek yeri. Cagiran: minik.py (__main__)."""

import argparse

from agiz import dosya, konsol, site, x

KONSOL = "konsol"
# Her agiz: (sinif, varsayilan girdi, varsayilan cikti). x'in ciktisi gonderim kuyrugudur.
DOSYALI_AGIZLAR = {
    dosya.PLATFORM: (dosya.DosyaAgzi, dosya.VARSAYILAN_GIRDI, dosya.VARSAYILAN_CIKTI),
    site.PLATFORM: (site.SiteAgzi, site.VARSAYILAN_GIRDI, site.VARSAYILAN_CIKTI),
    x.PLATFORM: (x.XAgzi, x.VARSAYILAN_GIRDI, x.VARSAYILAN_KUYRUK),
}


def agiz_sec(argumanlar=None):
    """(dinle, soyle, platform) dondurur; platform Defter kaydinin `platform` alanina yazilir."""
    ayristirici = argparse.ArgumentParser(description="Minik ile konus")
    ayristirici.add_argument("--agiz", choices=[KONSOL, *DOSYALI_AGIZLAR], default=KONSOL)
    ayristirici.add_argument("--girdi", default=None)
    ayristirici.add_argument("--cikti", default=None)
    secim = ayristirici.parse_args(argumanlar)
    if secim.agiz == KONSOL:
        return konsol.dinle, konsol.soyle, KONSOL
    sinif, girdi, cikti = DOSYALI_AGIZLAR[secim.agiz]
    agiz = sinif(secim.girdi or girdi, secim.cikti or cikti)
    return agiz.dinle, agiz.soyle, secim.agiz
