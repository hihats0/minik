"""f10-b gercek deneme: birkac sorguyu merak akisindan (ara -> esle -> Bekci) gecirir, gecici sqlite ve listeye
yazar (gercek Defter'e dokunmaz), sorgu basina sayilari basar. Cagiran: elle, `python deneyler/f10b-merak-dene.py`."""

import sqlite3
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agiz import web  # noqa: E402
from yuvalar import bekci_giris, iddia_esle, merak  # noqa: E402

SORGULAR = ["photosynthesis", "speed of light", "mount everest height", "fotosentez nedir", "python programming language"]
TARIH = "2026-09-24"


def main():
    """Her sorguyu akistan gecirir; kaynak basina kayit, grup, en cok alan ve Bekci kabul sayisini yazar."""
    baglanti = sqlite3.connect(":memory:")
    bekci_giris.kur(baglanti)
    toplam = 0
    for sorgu in SORGULAR:
        kayitlar = web.ara(sorgu)
        gruplar = iddia_esle.grupla(kayitlar)
        kabul = merak.ogren(baglanti, sorgu, TARIH, ara=lambda _s, k=kayitlar: k, yaz=lambda _k: None)
        toplam += len(kabul)
        alanlar = Counter(k["kaynak"] for k in kayitlar)
        print(f"{sorgu!r}: kayit={len(kayitlar)} alan={len(alanlar)} grup={len(gruplar)} "
              f"en_cok_alan={max((len(g['alanlar']) for g in gruplar), default=0)} kabul={len(kabul)}")
        for g in kabul:
            print("   KABUL", g["alanlar"], "|", g["iddia"][:90])
    print("toplam kabul:", toplam)


if __name__ == "__main__":
    main()
