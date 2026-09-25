"""Tek log bicimi: her yuva buradan yazar, satir basina bir JSON nesnesi (K5). Sure olcumu de burada.
Cagiran: butun yuvalar, agizlar ve minik.py."""

import json
import time
from datetime import datetime
from pathlib import Path

LOG_KLASORU = Path(__file__).resolve().parent.parent / "loglar"
GECERLI_SONUC = ("ok", "hata")


def yaz(yuva, olay, sure_ms, sonuc, detay):
    """Tek satirlik JSON log dusurur. Basarisizsa sessiz kalmaz, hata yukseltir."""
    _dogrula(sonuc, detay)
    simdi = datetime.now().astimezone()
    satir = {
        "t": simdi.isoformat(timespec="seconds"),
        "yuva": yuva,
        "olay": olay,
        "sure_ms": sure_ms,
        "sonuc": sonuc,
        "detay": detay,
    }
    LOG_KLASORU.mkdir(exist_ok=True)
    dosya = LOG_KLASORU / f"{simdi:%Y-%m-%d}.log"
    # encoding acikca verilir: Windows varsayilani cp1254, Turkce disi isaret patlatiyor.
    with dosya.open("a", encoding="utf-8") as f:
        f.write(json.dumps(satir, ensure_ascii=False) + "\n")


def gecen_ms(basladi):
    """time.perf_counter() ile alinan baslangictan bu yana gecen sureyi tam sayi milisaniye verir."""
    return int((time.perf_counter() - basladi) * 1000)


def _dogrula(sonuc, detay):
    """Log satirinin bicim sozlesmesini kontrol eder."""
    if sonuc not in GECERLI_SONUC:
        raise ValueError(f"sonuc sadece {GECERLI_SONUC} olabilir, gelen: {sonuc!r}")
    if sonuc == "hata" and not detay.get("hata"):
        # Hata yutulmaz kuralinin log tarafi: hata satirinda gerekce bos gecilemez.
        raise ValueError("sonuc 'hata' ise detay['hata'] dolu olmali")
