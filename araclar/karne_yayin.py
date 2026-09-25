"""Karneyi yayin klasorune (karne-site/index.html) uretir; once kisisel veri taramasi yapar, bulursa durur.
Cagiran: `python araclar/karne_yayin.py` (sonra `cd karne-site; vercel deploy --prod`), tests/test_karne_yayin.py."""

import os
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "araclar"))

import karne  # noqa: E402
from ortak import log  # noqa: E402

YUVA_ADI = "karne_yayin"
YAYIN_KLASORU = KOK / "karne-site"
YAYIN_SAYFASI = "index.html"
# Ad, soyad gibi kisiye ozel kelimeler repoya yazilmaz: bu yerel dosyada durur, satir basina bir kelime.
YEREL_LISTE = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "minik" / "yasak-kelimeler.txt"
YEREL_LISTE_ADI = "yerel liste"
# Yayinlanacak sayfada gecmemesi gereken desenler: (ad, duzenli ifade). Buyuk/kucuk harf fark etmez.
YASAK_DESENLER = (
    ("e-posta", r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    ("telefon", r"(\+90|0)?\s?5\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}"),
    ("yerel yol", r"[a-z]:(\\|/)(users|projelerim)"),
    ("gizli klasor", r"\.secrets"),
    ("jwt/supabase anahtari", r"eyJ[\w-]{10,}|sb_(secret|publishable)_\w+"),
    ("kisisel kart", r"sa[gğ]l[iı]k|\baile"),
)


class KisiselVeriHatasi(Exception):
    """Taramada yasak desen bulundu; yayin durur."""


def yerel_desenler(yol=YEREL_LISTE):
    """Yerel listedeki kelimeleri (ad, desen) olarak dondurur. Liste yoksa yayin durur: ad kontrol
    edilmeden sayfa cikmasin (kapali kapi acik kapidan guvenli)."""
    if not yol.exists():
        raise KisiselVeriHatasi(f"yerel yasak kelime listesi yok: {yol}")
    satirlar = yol.read_text(encoding="utf-8").splitlines()
    return [(YEREL_LISTE_ADI, re.escape(s.strip())) for s in satirlar if s.strip()]


def tara(metin, ek_desenler=()):
    """Metinde bulunan yasak desenlerin adlarini dondurur (bos liste = temiz)."""
    desenler = (*YASAK_DESENLER, *ek_desenler)
    return [ad for ad, desen in desenler if re.search(desen, metin, re.IGNORECASE)]


def yayinla(metin, klasor=YAYIN_KLASORU, ek_desenler=None):
    """Temizse metni klasor/index.html'e yazar; degilse loglar ve KisiselVeriHatasi atar.
    ek_desenler verilmezse yerel liste okunur (testler sahte liste verir)."""
    if ek_desenler is None:
        ek_desenler = yerel_desenler()
    bulunan = tara(metin, ek_desenler)
    if bulunan:
        log.yaz(YUVA_ADI, "tara", 0, "hata", {"hata": "kisisel veri deseni", "bulunan": bulunan})
        raise KisiselVeriHatasi(f"yayin durdu, kisisel veri deseni: {bulunan}")
    cikti = Path(klasor) / YAYIN_SAYFASI
    cikti.parent.mkdir(parents=True, exist_ok=True)
    cikti.write_text(metin, encoding="utf-8")
    log.yaz(YUVA_ADI, "yayinla", 0, "ok", {"yol": cikti.name})
    return cikti


def main():
    """Karneyi loglar/ altina uretir, taranmis kopyasini yayin klasorune koyar."""
    kaynak = karne.yaz()
    return yayinla(kaynak.read_text(encoding="utf-8"))


if __name__ == "__main__":
    print(main())
