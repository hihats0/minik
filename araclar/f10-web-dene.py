"""f10 gercek deneme: tek sorguyu webde arar, kayitlari gecici bir sqlite'taki Bekci kapisindan gecirir,
gecenleri gecici jsonl'e yazar (gercek Defter'e dokunmaz). Cagiran: elle, `python araclar/f10-web-dene.py`."""

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from agiz import web  # noqa: E402
from yuvalar import bekci_giris  # noqa: E402

SORGU = "fotosentez nedir"
TARIH = "2026-09-23"


def main():
    """Aramayi yapar, Bekci kararlarini sayar, ozeti yazdirir."""
    kayitlar = web.ara(SORGU)
    with tempfile.TemporaryDirectory() as dizin:
        baglanti = sqlite3.connect(Path(dizin) / "deneme.sqlite")
        bekci_giris.kur(baglanti)
        gecen = [k for k in kayitlar
                 if bekci_giris.gecsin_mi(baglanti, k["soru"], k["kaynak"], TARIH, k["platform"])[0]]
        jsonl = Path(dizin) / f"gunluk-{TARIH}.jsonl"
        jsonl.write_text("".join(json.dumps(k, ensure_ascii=False) + "\n" for k in gecen), encoding="utf-8")
        en_cok = baglanti.execute("SELECT MAX(c) FROM (SELECT COUNT(*) c FROM agizlar GROUP BY iddia)").fetchone()[0]
        baglanti.close()
    alanlar = sorted({k["kaynak"] for k in kayitlar})
    print(f"sorgu={SORGU!r} sonuc={len(kayitlar)} alan={len(alanlar)} gecen={len(gecen)} en_cok_agiz={en_cok}")
    print("alanlar:", ", ".join(alanlar))
    for k in kayitlar[:3]:
        print("-", k["kaynak"], "|", k["soru"][:100])


if __name__ == "__main__":
    main()
