"""Uyku yuvasi, tur 1 (egitimsiz): gunun jsonl'ini okur, etiketler, SM-2 provasi yapar, budar,
sqlite'a tek islemle yazar, sabah ozeti birakir, melatonini indirir (spec 2.4, 3.5).
Cagiran: minik.py akisi (uyku_tetik "uyu" deyince), elle ya da testler (`gece(tarih)`)."""

import json
import time
import urllib.error

from araclar.gomme_istemci import vektor_al
from ortak import log
from ortak.ayar import (
    DEFTER_KLASORU, GOMME_EN_YAKIN_K, GOMME_UC, SM2_BASARILI_KALITE, SM2_BASARISIZ_KALITE,
    UYKU_PROVA_KALIBI, UYKU_SABAH_OZET_KALIBI,
)
from yuvalar import defter, defter_sqlite, kafa
from yuvalar import uyku_secim as secim

YUVA_ADI = "uyku"
ZATEN_ISLENDI = "zaten islendi"
UYKU_SIDDETI = 1.0


def gece(tarih, hormon_durumu=None, gomme_al=None, prova=None, klasor=None):
    """Bir gunun gecesini isler, (ozet, etiketlenen_sayisi, budanan_sayisi) dondurur.
    gomme_al/prova/klasor testler icin disaridan verilebilir; verilmezse gercekleri kullanilir."""
    basladi = time.perf_counter()
    klasor = klasor or DEFTER_KLASORU
    baglanti = defter_sqlite.baglan(klasor)
    try:
        if defter_sqlite.islendi_mi(baglanti, tarih):
            log.yaz(YUVA_ADI, "gece", _gecen_ms(basladi), "ok", {"tarih": tarih, "atlandi": True})
            return ZATEN_ISLENDI, 0, 0
        yeni = _yeni_anilar(klasor, tarih, gomme_al or _sunucudan_gomme)
        guncellemeler = _provalar(baglanti, tarih, prova or _kafaya_sor)
        budanan = defter.isle(baglanti, tarih, yeni, guncellemeler)
        komsular = _komsular(baglanti, yeni)
    finally:
        baglanti.close()
    if hormon_durumu is not None:
        hormon_durumu.guncelle("uyku", UYKU_SIDDETI)
    etiketlenen = sum(1 for a in yeni if a["etiket"] != secim.ETIKET_SIRADAN)
    ozet = _sabah_ozeti(tarih, yeni, guncellemeler, budanan, komsular)
    (klasor / UYKU_SABAH_OZET_KALIBI.format(tarih=tarih)).write_text(ozet, encoding="utf-8")
    log.yaz(YUVA_ADI, "gece", _gecen_ms(basladi), "ok",
            {"tarih": tarih, "okunan": len(yeni), "etiketlenen": etiketlenen,
             "budanan": budanan, "ogeler": len(guncellemeler)})
    return ozet, etiketlenen, budanan


def _yeni_anilar(klasor, tarih, gomme_al):
    """Gunun jsonl'ini SALT OKUNUR acar, kayitlari etiketli ve SM-2 baslangicli aniya cevirir."""
    dosya = klasor / f"gunluk-{tarih}.jsonl"
    if not dosya.exists():
        return []
    with dosya.open("r", encoding="utf-8") as f:
        kayitlar = [json.loads(s) for s in f if s.strip()]
    anilar = []
    for sira, kayit in enumerate(secim.etiketle(kayitlar), start=1):
        vektor = gomme_al(kayit.get("soru", ""))
        anilar.append({"tarih": tarih, "sira": sira, "zaman": kayit["zaman"],
                       "soru": kayit.get("soru", ""), "cevap": kayit.get("cevap", ""),
                       "oncelik": kayit["oncelik"], "etiket": kayit["etiket"],
                       "gomme": defter_sqlite.vektorden_blob(vektor),
                       **secim.yeni_sm2_alanlari(tarih)})
    return anilar


def _provalar(baglanti, tarih, prova):
    """Vadesi gelen her aniyi prova eder (ruya); cevap alinamayani bu gece guncellemez."""
    guncellemeler = []
    for ani in defter_sqlite.vadesi_gelenler(baglanti, tarih):
        hatirladi = prova(ani)
        if hatirladi is None:
            continue
        kalite = SM2_BASARILI_KALITE if hatirladi else SM2_BASARISIZ_KALITE
        guncellemeler.append(secim.sm2_adimi(ani, kalite, tarih))
    return guncellemeler


def _kafaya_sor(ani):
    """Kafa'ya eski soruyu yeniden sorar, cevabi eskisiyle kiyaslar. Kafa kapaliysa None."""
    basladi = time.perf_counter()
    try:
        cevap, _ = kafa.dusun(UYKU_PROVA_KALIBI.format(soru=ani["soru"]))
    except (urllib.error.URLError, OSError) as hata:
        log.yaz(YUVA_ADI, "prova", _gecen_ms(basladi), "hata", {"id": ani["id"], "hata": str(hata)})
        return None
    return secim.hatirladi_mi(ani["cevap"], cevap)


def _sunucudan_gomme(metin):
    """CPU'daki gomme sunucusundan vektor alir. Sunucu yoksa None: Uyku gommesiz devam eder."""
    basladi = time.perf_counter()
    try:
        vektor, _ = vektor_al(GOMME_UC, metin)
    except (urllib.error.URLError, OSError) as hata:
        log.yaz(YUVA_ADI, "gomme", _gecen_ms(basladi), "hata", {"hata": str(hata)})
        return None
    return vektor


def _komsular(baglanti, yeni):
    """Oncelikli yeni anilarin gommeye gore en yakin eski anilari (cagrisim, spec 3.4)."""
    tum = defter_sqlite.gommeli_anilar(baglanti)
    sonuc = {}
    for ani in yeni:
        if ani["etiket"] != secim.ETIKET_ONCELIKLI or ani["gomme"] is None:
            continue
        vektor = defter_sqlite.blobdan_vektor(ani["gomme"])
        adaylar = [a for a in tum if a[1] != ani["soru"]]
        sonuc[ani["soru"]] = secim.en_yakin(vektor, adaylar, GOMME_EN_YAKIN_K)
    return sonuc


def _sabah_ozeti(tarih, yeni, guncellemeler, budanan, komsular):
    """Yigit'in sabah okuyacagi kisa ozet metni."""
    sayim = {e: sum(1 for a in yeni if a["etiket"] == e)
             for e in (secim.ETIKET_ONCELIKLI, secim.ETIKET_YAKALANDI, secim.ETIKET_SIRADAN)}
    hatirlanan = sum(1 for g in guncellemeler if g["ust_uste_basarisiz"] == 0)
    gommesiz = sum(1 for a in yeni if a["gomme"] is None)
    satirlar = [f"# Sabah ozeti {tarih}", "",
                f"- Okunan kayit: {len(yeni)} (gommesiz: {gommesiz})",
                f"- Etiket: {sayim}",
                f"- Prova: {len(guncellemeler)} ani, hatirlanan {hatirlanan}",
                f"- Budanan: {budanan}"]
    for soru, yakinlar in komsular.items():
        satirlar.append(f"- '{soru}' su anilari cagristirdi: "
                        + ", ".join(f"'{s}' ({skor:.2f})" for skor, s in yakinlar))
    return "\n".join(satirlar) + "\n"


def _gecen_ms(basladi):
    """Olcum baslangicindan bu yana gecen sureyi tam sayi milisaniye verir."""
    return int((time.perf_counter() - basladi) * 1000)
