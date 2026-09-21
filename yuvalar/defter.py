"""Ham konusmayi gunluk jsonl'e yazar, geri okur (spec 3.4, R2: uc ad `yaz`/`oku`/`isle`).
Cagiran: minik.py akisi (yaz, oku); yuvalar/uyku.py (isle, henuz yok, f4)."""

import json
import time
from datetime import datetime

from ortak import log
from ortak.ayar import DEFTER_KLASORU, DEFTER_SON_N

YUVA_ADI = "defter"


def yaz(kayit):
    """Kaydi bugunku jsonl dosyasinin SONUNA ekler, var olan satirlara asla dokunmaz.
    Yazim basarisiz olursa hatayi yutmaz, yukseltir: kaydedilmeyen konusma Minik icin
    en pahali kayiptir (spec 3.4), akis bunu yakalayip durur."""
    basladi = time.perf_counter()
    satir = dict(kayit)
    satir["zaman"] = datetime.now().astimezone().isoformat(timespec="seconds")
    dosya = _bugunku_dosya()
    try:
        dosya.parent.mkdir(parents=True, exist_ok=True)
        onceki = _satir_sayisi(dosya) if dosya.exists() else 0
        with dosya.open("a", encoding="utf-8") as f:
            f.write(json.dumps(satir, ensure_ascii=False) + "\n")
    except OSError as hata:
        log.yaz(YUVA_ADI, "yaz", _gecen_ms(basladi), "hata", {"hata": str(hata)})
        raise
    kayit_no = onceki + 1
    log.yaz(YUVA_ADI, "yaz", _gecen_ms(basladi), "ok", {"kayit_no": kayit_no})
    return kayit_no


def oku(kac_tane=DEFTER_SON_N):
    """Bugunku dosyadan son `kac_tane` kaydi (eskiden yeniye) dondurur. Dosya yoksa bos
    liste doner. Bozuk bir satir varsa onu atlar, dosyanin tamamini dusurmez."""
    basladi = time.perf_counter()
    dosya = _bugunku_dosya()
    kayitlar = _satirlari_ayristir(dosya, basladi) if dosya.exists() else []
    sonuc = kayitlar[-kac_tane:]
    log.yaz(YUVA_ADI, "oku", _gecen_ms(basladi), "ok", {"istenen": kac_tane, "bulunan": len(sonuc)})
    return sonuc


def isle(*_args, **_kwargs):
    """R2 (K16): Defter'in ucuncu adi. Spec 3.4 tanimi: sqlite'taki turetilmis tabloyu
    tazeler (etiket, SM-2 alani, gomme BLOB'u, budama); yalniz Uyku cagirir, gunduz hattinda
    cagrilmaz. sqlite Uyku ile birlikte f4'te doguyor (K4) ve ikisi de bu fazin (f2-a) disinda
    (CLAUDE.md: bir oturumda bir yuva). Bu yuzden bugun no-op: uc-ad sozlesmesini acik tutar,
    sqlite'a dokunmaz. Karsiligi olmayan bir is icat edilmedi."""
    log.yaz(YUVA_ADI, "isle", 0, "ok", {"not": "sqlite f4'te doguyor, bugun no-op"})


def _bugunku_dosya():
    """Bugunun tarihiyle adlanan jsonl dosyasinin yolunu dondurur (spec 4.2)."""
    return DEFTER_KLASORU / f"gunluk-{datetime.now().astimezone():%Y-%m-%d}.jsonl"


def _satir_sayisi(dosya):
    """Dosyadaki bos olmayan satir sayisini dondurur (bir sonraki kayit_no icin)."""
    with dosya.open(encoding="utf-8") as f:
        return sum(1 for satir in f if satir.strip())


def _satirlari_ayristir(dosya, basladi):
    """Dosyayi satir satir JSON'a cevirir. Bozuk satiri atlar ve loglar, akisi kesmez."""
    kayitlar = []
    with dosya.open(encoding="utf-8") as f:
        for i, satir in enumerate(f, start=1):
            if not satir.strip():
                continue
            try:
                kayitlar.append(json.loads(satir))
            except json.JSONDecodeError as hata:
                log.yaz(YUVA_ADI, "satir_atla", _gecen_ms(basladi), "hata",
                        {"hata": str(hata), "satir_no": i})
    return kayitlar


def _gecen_ms(basladi):
    """Olcum baslangicindan bu yana gecen sureyi tam sayi milisaniye verir."""
    return int((time.perf_counter() - basladi) * 1000)
