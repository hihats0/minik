"""Defter'in turetilmis yarisi: defter/minik.sqlite (anilar, SM-2 alanlari, gomme BLOB'u, islenen geceler).
Cagiran: yuvalar/defter.py (`isle`), yuvalar/uyku.py ve yuvalar/gorunur.py (okuma yardimcilari). Gunduz hattinda cagrilmaz."""

import array
import sqlite3

from ortak.ayar import DEFTER_SQLITE_ADI, UYKU_BUDAMA_SINIRI

SEMA = """
CREATE TABLE IF NOT EXISTS anilar (
    id INTEGER PRIMARY KEY, tarih TEXT, sira INTEGER, zaman TEXT, soru TEXT, cevap TEXT,
    oncelik REAL, etiket TEXT, tekrar INTEGER, ef REAL, sonraki_gun TEXT,
    ust_uste_basarisiz INTEGER, gomme BLOB, UNIQUE (tarih, sira));
CREATE TABLE IF NOT EXISTS geceler (tarih TEXT PRIMARY KEY, bitti TEXT);
"""
VEKTOR_TIPI = "f"  # 4 baytlik float: 384 boyutlu e5-small vektoru 1,5 KB


def baglan(klasor):
    """sqlite'i acar (yoksa olusturur) ve semayi kurar."""
    klasor.mkdir(parents=True, exist_ok=True)
    baglanti = sqlite3.connect(klasor / DEFTER_SQLITE_ADI)
    baglanti.row_factory = sqlite3.Row
    baglanti.executescript(SEMA)
    return baglanti


def islendi_mi(baglanti, tarih):
    """Bu tarihin gecesi daha once tamamlandiysa True (ayni gun iki kez calismasin diye)."""
    satir = baglanti.execute("SELECT 1 FROM geceler WHERE tarih = ?", (tarih,)).fetchone()
    return satir is not None


def islenmis_geceler(baglanti):
    """Tamamlanmis gecelerin tarih kumesi."""
    return {s["tarih"] for s in baglanti.execute("SELECT tarih FROM geceler")}


def etiket_sayilari(baglanti):
    """Tutulan anilarin etikete gore sayisi, gorunur sayfa icin."""
    sorgu = "SELECT etiket, COUNT(*) AS sayi FROM anilar GROUP BY etiket"
    return {s["etiket"]: s["sayi"] for s in baglanti.execute(sorgu)}


def vadesi_gelenler(baglanti, tarih):
    """SM-2 takvimine gore bu gece gozden gecirilecek anilar, yuksek oncelikli once."""
    sorgu = "SELECT * FROM anilar WHERE sonraki_gun <= ? ORDER BY oncelik DESC"
    return [dict(s) for s in baglanti.execute(sorgu, (tarih,))]


def gommeli_anilar(baglanti):
    """Gommesi olan butun anilari (id, soru, vektor) olarak verir; kaba kuvvet kosinus icin."""
    satirlar = baglanti.execute("SELECT id, soru, gomme FROM anilar WHERE gomme IS NOT NULL")
    return [(s["id"], s["soru"], blobdan_vektor(s["gomme"])) for s in satirlar]


def vektorden_blob(vektor):
    """Liste halindeki vektoru sqlite BLOB'una cevirir; vektor yoksa None."""
    return None if vektor is None else array.array(VEKTOR_TIPI, vektor).tobytes()


def blobdan_vektor(blob):
    """BLOB'u yeniden float listesine cevirir."""
    return array.array(VEKTOR_TIPI, blob).tolist()


def islem(baglanti, tarih, yeni_anilar, guncellemeler, zaman):
    """Tek transaction: yeni anilari ekler, SM-2 alanlarini yazar, budar, geceyi isaretler.
    Herhangi bir adim hata verirse `with` bloku hepsini geri alir (spec 3.5 Hata)."""
    with baglanti:
        for ani in yeni_anilar:
            baglanti.execute(
                "INSERT OR IGNORE INTO anilar (tarih, sira, zaman, soru, cevap, oncelik, etiket,"
                " tekrar, ef, sonraki_gun, ust_uste_basarisiz, gomme)"
                " VALUES (:tarih, :sira, :zaman, :soru, :cevap, :oncelik, :etiket, :tekrar, :ef,"
                " :sonraki_gun, :ust_uste_basarisiz, :gomme)", ani)
        for g in guncellemeler:
            baglanti.execute(
                "UPDATE anilar SET tekrar = :tekrar, ef = :ef, sonraki_gun = :sonraki_gun,"
                " ust_uste_basarisiz = :ust_uste_basarisiz WHERE id = :id", g)
        budanan = budama_yap(baglanti)
        baglanti.execute("INSERT INTO geceler (tarih, bitti) VALUES (?, ?)", (tarih, zaman))
    return budanan


def budama_yap(baglanti):
    """Ust uste UYKU_BUDAMA_SINIRI kez hatirlanamayan anilari siler, silinen sayisini verir."""
    imlec = baglanti.execute(
        "DELETE FROM anilar WHERE ust_uste_basarisiz >= ?", (UYKU_BUDAMA_SINIRI,))
    return imlec.rowcount
