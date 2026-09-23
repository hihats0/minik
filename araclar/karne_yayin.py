"""Karneyi yayin klasorune (karne-site/index.html) uretir; once kisisel veri taramasi yapar, bulursa durur.
Cagiran: `python araclar/karne_yayin.py` (sonra `cd karne-site; vercel deploy --prod`), tests/test_karne_yayin.py."""

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
# Yayinlanacak sayfada gecmemesi gereken desenler: (ad, duzenli ifade). Buyuk/kucuk harf fark etmez.
YASAK_DESENLER = (
    ("e-posta", r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    ("soyad", r"<yerel liste>"),
    ("isim", r"<yerel liste>"),
    ("telefon", r"(\+90|0)?\s?5\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}"),
    ("yerel yol", r"[a-z]:(\\|/)(users|projelerim)"),
    ("gizli klasor", r"\.secrets"),
    ("jwt/supabase anahtari", r"eyJ[\w-]{10,}|sb_(secret|publishable)_\w+"),
    ("kisisel kart", r"sa[gğ]l[iı]k|\baile"),
)


class KisiselVeriHatasi(Exception):
    """Taramada yasak desen bulundu; yayin durur."""


def tara(metin):
    """Metinde bulunan yasak desenlerin adlarini dondurur (bos liste = temiz)."""
    return [ad for ad, desen in YASAK_DESENLER if re.search(desen, metin, re.IGNORECASE)]


def yayinla(metin, klasor=YAYIN_KLASORU):
    """Temizse metni klasor/index.html'e yazar; degilse loglar ve KisiselVeriHatasi atar."""
    bulunan = tara(metin)
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
