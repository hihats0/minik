"""Herkese acik karne taslagi (f8-b): var olan olcumlerden loglar/karne.html uretir. Yalniz sayi girer;
defter icerigi, konusma metni, kisisel veri girmez. Yayin yok (K29). Cagiran: `python araclar/karne.py`, testler."""

import html
import sys
import unittest
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from ortak import log  # noqa: E402
from yuvalar import bekci_giris, defter, defter_sqlite  # noqa: E402

YUVA_ADI = "karne"
SAYFA_ADI = "karne.html"
TEST_KLASORU = KOK / "tests"
BILINMIYOR = "bilinmiyor"
# Raporlardan elle alinan olcumler: (ad, deger, kaynak rapor). Rapor degisirse burasi da degisir.
RAPOR_OLCUMLERI = (
    ("Turkce sinav, Kafa (Qwen3.5-4B)", "13/40", "reports/2026-09-23-k23-1-turkce-sinav.md"),
    ("Turkce sinav, en iyi aday (Turkish-Gemma-9b)", "20/40", "reports/2026-09-23-k23-1-turkce-sinav.md"),
    ("Refleks ayrisma (f3c3, tam)", "%94,9 (259/273)", "reports/2026-09-23-f6-kalp.md"),
    ("Uyku geri getirme (budama siniri 3)", "%94,3", "reports/2026-09-23-f4b-uyku-tur2.md"),
)
SAYFA_KALIBI = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><title>Minik karne</title></head>
<body>
<h1>Minik karne</h1>
<p>Uretildi: {zaman}. Yalniz olcum sayilari; konusma ve defter icerigi yok.</p>
<table border="1"><tr><th>Olcum</th><th>Deger</th><th>Kaynak</th></tr>
{satirlar}
</table>
</body></html>
"""


def test_sayisi():
    """tests/ altindaki test sayisini kosmadan sayar (yukler, calistirmaz)."""
    paket = unittest.defaultTestLoader.discover(str(TEST_KLASORU))
    return paket.countTestCases()


def bekci_satirlari(klasor):
    """Bekci giris kapisi red oranlari (defter sqlite'tan, yalniz oran)."""
    baglanti = defter_sqlite.baglan(klasor)
    try:
        genel, yigit = bekci_giris.red_oranlari(baglanti)
    finally:
        baglanti.close()
    return (("Bekci giris red orani", _oran(genel), "defter sqlite"),
            ("Bekci Yigit kaynakli red orani (~0 olmali)", _oran(yigit), "defter sqlite"))


def _oran(deger):
    return BILINMIYOR if deger is None else f"%{deger * 100:.1f}"


def sayfa_uret(klasor, test_adedi):
    """Olcum satirlarini HTML sayfaya doker, metni dondurur."""
    olcumler = [("Test sayisi", str(test_adedi), "python -m unittest"), *bekci_satirlari(klasor),
                *RAPOR_OLCUMLERI]
    satirlar = "\n".join(
        "<tr>" + "".join(f"<td>{html.escape(h)}</td>" for h in olcum) + "</tr>" for olcum in olcumler)
    return SAYFA_KALIBI.format(zaman=datetime.now().isoformat(timespec="seconds"), satirlar=satirlar)


def yaz(klasor=None, cikti_klasoru=None, test_adedi=None):
    """Karneyi cikti_klasoru/karne.html'e yazar (varsayilan loglar/), yolu dondurur."""
    klasor = Path(klasor or defter.DEFTER_KLASORU)
    cikti = Path(cikti_klasoru or log.LOG_KLASORU) / SAYFA_ADI
    adet = test_sayisi() if test_adedi is None else test_adedi
    cikti.parent.mkdir(parents=True, exist_ok=True)
    cikti.write_text(sayfa_uret(klasor, adet), encoding="utf-8")
    log.yaz(YUVA_ADI, "yaz", 0, "ok", {"test_sayisi": adet})
    return cikti


if __name__ == "__main__":
    print(yaz())
