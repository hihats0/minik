"""Site agzi (f8-b, spec 2.6), en aptal hali: dosya agziyla ayni is, yalniz platform "site". Yerel
dosyadan okur, yerel dosyaya yazar; sunucu yok, yayin yok (K29). Cagiran: agiz/secim.py, testler."""

from pathlib import Path

from agiz.dosya import DosyaAgzi

PLATFORM = "site"
VARSAYILAN_GIRDI = Path("site-agzi") / "girdi.txt"
VARSAYILAN_CIKTI = Path("site-agzi") / "cikti.txt"


class SiteAgzi(DosyaAgzi):
    """Sitedeki ziyaretci Yigit degildir: platform "site" Bekci giriste dis kaynak, buyumede elenir."""

    def __init__(self, girdi=VARSAYILAN_GIRDI, cikti=VARSAYILAN_CIKTI):
        super().__init__(girdi, cikti)
