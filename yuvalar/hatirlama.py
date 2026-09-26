"""Gunduz hatirlamasi (hipokampus): her yeni Defter sorusunun gommesini ayri sqlite'a yazar, yeni soruya
en yakin eski sozleri Kafa'ya tek sistem mesaji olarak verir. Cagiran: minik.py akisi (doldur, kaydet, baglam_mesaji)."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from ortak import baglam_butce, gomme, gomme_sunucu, log
from ortak.ayar import GOMME_EN_YAKIN_K, GOMME_UC
from yuvalar import defter, uyku_secim
from yuvalar.defter_sqlite import blobdan_vektor, vektorden_blob

YUVA_ADI = "hatirlama"
DB_ADI = "hatirlama.sqlite"  # minik.sqlite'tan ayri: gece Uyku'nun transaction'ina kilit karismasin
SEMA = """CREATE TABLE IF NOT EXISTS gunduz_gomme (dosya TEXT, sira INTEGER, zaman TEXT, soru TEXT,
          gomme BLOB, PRIMARY KEY (dosya, sira))"""
BELGE_ONEKI = "passage: "  # e5 belge ve sorguyu oneklerle ayirir
SORGU_ONEKI = "query: "
HATIRLAMA_TOKEN_BUTCESI = 300
MESAJ_BASLIGI = "Yigit'in sana daha once soyledikleri (hatirladiklarin):"
TARIH_UZUNLUGU = 10  # "YYYY-MM-DD"


def varsayilan_gomme_al(metin):
    """Gomme sunucusunu hazirlar, metnin vektorunu dondurur; hazirlanamazsa OSError."""
    if not gomme_sunucu.hazirla():
        raise OSError("gomme sunucusu hazir degil")
    vektor, _ = gomme.vektor_al(GOMME_UC, metin)
    return vektor


@contextmanager
def _baglan():
    """Baglantiyi acar, is bitince kaydedip KAPATIR (Windows'ta acik dosya gecici klasoru kilitler)."""
    defter.DEFTER_KLASORU.mkdir(parents=True, exist_ok=True)
    baglanti = sqlite3.connect(defter.DEFTER_KLASORU / DB_ADI)
    try:
        baglanti.execute(SEMA)
        yield baglanti
    finally:
        baglanti.commit()  # doldur yarida kalsa da o ana kadar alinan gommeler bosa gitmesin
        baglanti.close()


def _yaz(baglanti, dosya, sira, zaman, soru, gomme_al):
    vektor = gomme_al(BELGE_ONEKI + soru)
    baglanti.execute("INSERT OR REPLACE INTO gunduz_gomme VALUES (?, ?, ?, ?, ?)",
                     (dosya, sira, zaman, soru, vektorden_blob(vektor)))


def kaydet(kayit_no, soru, gomme_al=None):
    """Bugun Defter'e yazilan kaydin (kayit_no) sorusunu gommeyle saklar. Gomme alinamazsa loglar,
    False doner: sohbet durmaz, eksik kaydi bir sonraki acilistaki doldur tamamlar."""
    if not soru.strip():
        return False
    dosya = defter._bugunku_dosya().name
    zaman = datetime.now().astimezone().isoformat(timespec="seconds")
    try:
        with _baglan() as baglanti:
            _yaz(baglanti, dosya, kayit_no, zaman, soru, gomme_al or varsayilan_gomme_al)
    except (OSError, sqlite3.Error, KeyError, ValueError) as hata:
        log.yaz(YUVA_ADI, "kaydet", 0, "hata", {"hata": str(hata), "sira": kayit_no})
        return False
    return True


def _defter_kayitlari():
    """(dosya_adi, sira, kayit) uretir; sira Defter'in kayit_no'su gibi bos olmayan satir sayisidir."""
    if not defter.DEFTER_KLASORU.exists():
        return
    for yol in sorted(defter.DEFTER_KLASORU.glob("gunluk-*.jsonl")):
        satirlar = [s for s in yol.read_text(encoding="utf-8").splitlines() if s.strip()]
        for sira, satir in enumerate(satirlar, start=1):
            try:
                yield yol.name, sira, json.loads(satir)
            except json.JSONDecodeError as hata:
                log.yaz(YUVA_ADI, "satir_atla", 0, "hata", {"hata": str(hata), "dosya": yol.name})


def doldur(gomme_al=None):
    """Gommesi olmayan eski Defter kayitlarini doldurur, eklenen sayiyi dondurur. Ilk gomme
    hatasinda loglayip durur (sunucu yoksa her kayit icin ayri beklenmesin)."""
    eklenen = 0
    try:
        with _baglan() as baglanti:
            var = set(baglanti.execute("SELECT dosya, sira FROM gunduz_gomme"))
            for dosya, sira, kayit in _defter_kayitlari():
                soru = kayit.get("soru", "")
                if (dosya, sira) in var or not soru.strip():
                    continue
                _yaz(baglanti, dosya, sira, kayit.get("zaman", ""), soru, gomme_al or varsayilan_gomme_al)
                eklenen += 1
    except (OSError, sqlite3.Error, KeyError, ValueError) as hata:
        log.yaz(YUVA_ADI, "doldur", 0, "hata", {"hata": str(hata), "eklenen": eklenen})
        return eklenen
    log.yaz(YUVA_ADI, "doldur", 0, "ok", {"eklenen": eklenen})
    return eklenen


def baglam_mesaji(soru, haric_sorular, gomme_al=None):
    """Soruya en yakin GOMME_EN_YAKIN_K eski sozu (son baglamda olanlar haric) tek sistem mesaji
    yapar; yalniz Yigit'in sozu girer, eski cevap girmez. Hic yoksa ya da gomme alinamazsa None."""
    try:
        sorgu = (gomme_al or varsayilan_gomme_al)(SORGU_ONEKI + soru)
        with _baglan() as baglanti:
            satirlar = list(baglanti.execute("SELECT zaman, soru, gomme FROM gunduz_gomme"))
    except (OSError, sqlite3.Error, KeyError, ValueError) as hata:
        log.yaz(YUVA_ADI, "baglam_mesaji", 0, "hata", {"hata": str(hata)})
        return None
    adaylar = [(zaman, eski, blobdan_vektor(b)) for zaman, eski, b in satirlar
               if eski not in haric_sorular and eski != soru]
    secilen = uyku_secim.en_yakin(sorgu, adaylar, GOMME_EN_YAKIN_K)
    zamanlar = {eski: zaman for zaman, eski, _ in adaylar}
    return _butceli_mesaj([(zamanlar[eski], eski) for _, eski in secilen])


def _butceli_mesaj(anilar):
    """Anilari satir satir ekler; HATIRLAMA_TOKEN_BUTCESI'ni asacak satir girmez."""
    mesaj = {"role": "system", "content": MESAJ_BASLIGI}
    for zaman, eski in anilar:
        satir = f"\n[{zaman[:TARIH_UZUNLUGU]}] {eski}"
        aday = {"role": "system", "content": mesaj["content"] + satir}
        if baglam_butce.token_tahmini([aday]) <= HATIRLAMA_TOKEN_BUTCESI:
            mesaj = aday
    return None if mesaj["content"] == MESAJ_BASLIGI else mesaj
