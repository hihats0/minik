"""Ham konusmayi gunluk jsonl'e yazar, geri okur, gece sqlite'a isler (spec 3.4, R2: uc ad
`yaz`/`oku`/`isle`). `isle` turetilmis tabloyu (defter/minik.sqlite) tazeler; ham jsonl'e dokunmaz.
Cagiran: minik.py akisi (yaz, oku), yuvalar/uyku.py (yalniz isle)."""

import json
import time
from datetime import datetime

from ortak import log
from yuvalar import defter_sqlite
from ortak.ayar import DEFTER_GERI_GUN_SINIRI, DEFTER_KLASORU, DEFTER_SON_N

YUVA_ADI = "defter"

# Satir sayaci: {dosya_yolu: (boyut, degisme_ns, satir_sayisi)}. Baska surec (orn. agiz.web_sohbet)
# ayni dosyaya yazarsa boyut/degisme zamani tutmaz, dosya yeniden sayilir. Iki surecin ayni anda
# yazdigi pencerede kayit_no yine kayabilir (eski kodda da ayni yaris vardi).
_sayac = {}


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
        onceki = _sayac_oku(dosya)
        with dosya.open("a", encoding="utf-8") as f:
            f.write(json.dumps(satir, ensure_ascii=False) + "\n")
        _sayac_yaz(dosya, onceki + 1)
    except OSError as hata:
        log.yaz(YUVA_ADI, "yaz", log.gecen_ms(basladi), "hata", {"hata": str(hata)})
        raise
    kayit_no = onceki + 1
    log.yaz(YUVA_ADI, "yaz", log.gecen_ms(basladi), "ok", {"kayit_no": kayit_no})
    return kayit_no


def oku(kac_tane=DEFTER_SON_N):
    """Son `kac_tane` kaydi (eskiden yeniye) dondurur. Bugunku dosya yetmezse gun dosyalarinda
    geriye gider (en yeniden en eskiye), en cok DEFTER_GERI_GUN_SINIRI dosya acar; boylece
    yeniden baslatmadan sonra dunku (ya da daha eski) konu da geri gelir (spec 8.1 f2 olcutu).
    Istenen sayi daha yeni dosyalarla karsilaniyorsa daha eski dosya hic acilmaz. Bozuk bir
    satir varsa onu atlar, dosyanin tamamini dusurmez. Hic dosya yoksa bos liste doner."""
    basladi = time.perf_counter()
    kayitlar = []
    dosya_sayisi = 0
    for dosya in _gun_dosyalari_yeniden_eskiye(DEFTER_GERI_GUN_SINIRI):
        gunun_kayitlari = _satirlari_ayristir(dosya, basladi)
        kayitlar = gunun_kayitlari + kayitlar
        dosya_sayisi += 1
        if len(kayitlar) >= kac_tane:
            break
    sonuc = kayitlar[-kac_tane:]
    log.yaz(YUVA_ADI, "oku", log.gecen_ms(basladi), "ok",
            {"istenen": kac_tane, "bulunan": len(sonuc), "dosya_sayisi": dosya_sayisi})
    return sonuc


def isle(baglanti, tarih, yeni_anilar, guncellemeler):
    """Uyku'nun gece sonucunu sqlite'a TEK transaction ile yazar; yarida hata olursa hepsi geri
    alinir ve hata yukselir. Budanan ani sayisini dondurur. Yalniz Uyku cagirir (R2)."""
    basladi = time.perf_counter()
    zaman = datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        budanan = defter_sqlite.islem(baglanti, tarih, yeni_anilar, guncellemeler, zaman)
    except Exception as hata:
        log.yaz(YUVA_ADI, "isle", log.gecen_ms(basladi), "hata", {"tarih": tarih, "hata": str(hata)})
        raise
    log.yaz(YUVA_ADI, "isle", log.gecen_ms(basladi), "ok",
            {"tarih": tarih, "yeni": len(yeni_anilar), "guncellenen": len(guncellemeler),
             "budanan": budanan})
    return budanan


def _bugunku_dosya():
    """Bugunun tarihiyle adlanan jsonl dosyasinin yolunu dondurur (spec 4.2)."""
    return DEFTER_KLASORU / f"gunluk-{datetime.now().astimezone():%Y-%m-%d}.jsonl"


def _gun_dosyalari_yeniden_eskiye(en_cok):
    """Gun dosyalarini (gunluk-YYYY-MM-DD.jsonl) dosya adindan en yeniden en eskiye siralar,
    en cok `en_cok` tanesini uretir. Klasor yoksa hic uretmez."""
    if not DEFTER_KLASORU.exists():
        return
    dosyalar = sorted(DEFTER_KLASORU.glob("gunluk-*.jsonl"), key=lambda d: d.name, reverse=True)
    for dosya in dosyalar[:en_cok]:
        yield dosya


def _satir_sayisi(dosya):
    """Dosyadaki bos olmayan satir sayisini dondurur (bir sonraki kayit_no icin)."""
    with dosya.open(encoding="utf-8") as f:
        return sum(1 for satir in f if satir.strip())


def _sayac_oku(dosya):
    """Onbellekteki satir sayisini verir; dosya boyutu ya da degisme zamani degistiyse yeniden sayar."""
    if not dosya.exists():
        return 0
    durum = dosya.stat()
    kayitli = _sayac.get(str(dosya))
    if kayitli and kayitli[:2] == (durum.st_size, durum.st_mtime_ns):
        return kayitli[2]
    return _satir_sayisi(dosya)


def _sayac_yaz(dosya, sayi):
    """Yazimdan sonraki boyut ve degisme zamaniyla sayaci kaydeder."""
    durum = dosya.stat()
    _sayac[str(dosya)] = (durum.st_size, durum.st_mtime_ns, sayi)


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
                log.yaz(YUVA_ADI, "satir_atla", log.gecen_ms(basladi), "hata",
                        {"hata": str(hata), "satir_no": i})
    return kayitlar
