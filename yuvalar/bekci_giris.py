"""Bekci giris kapisi (spec 3.7, f5): bir iddia ancak birbirinden bagimsiz UC kaynaktan gelince kalici
hafizaya (anilar tablosu) aday olur; sayac, merak tavani ve otoimmunite olceri sqlite'ta. Cagiran: yuvalar/uyku.py (gece), yuvalar/gorunur.py (oranlar)."""

import time

from ortak import log

YUVA_ADI = "bekci"
UC_AGIZ_ESIGI = 3
# TAHMIN: oksitosini yuksek kaynakta esik 2'ye iner; taban asla 1 degil (tek agiz = Tay).
OKSITOSIN_ESIGI = 2
OKSITOSIN_YUKSEK = 60.0  # TAHMIN: oksitosin dinlenme degeri 30, bunun iki kati "yuksek" sayildi
MERAK_TAVANI = 20  # TAHMIN: bir kaynaktan bir gunde en fazla bu kadar yeni iddia sayilir
# Yigit'in konsolu tek agizla gecer: Yigit Minik'in sahibi, spec olcutu "Yigit kaynakli red ~0".
# site_yigit: web sohbet sitesi (agiz/web_sohbet.py), X-Anahtar ile korunur, yalniz Yigit kullanir (24 Eyl).
YIGIT_KAYNAKLARI = {"konsol", "site_yigit"}
VARSAYILAN_KAYNAK = "konsol"  # platform alanindan onceki eski kayitlar yalniz konsoldan yazildi

GEREKCE_YIGIT = "Yigit kaynagi (konsol), tek agiz yeter"
# K28=B, K29=D (Yigit, 2026-09-23): X kaynagi sayilir, her X hesabi bir agiz. Kayit Defter'e platform
# "x" isaretiyle girer; S7 (buyume.x_kaynakli_mi) bu isaretle onu LoRA disinda tutar.
X_KAYNAK_TURU = "x"
X_PLATFORMLARI = {"x", "twitter"}
X_ONEKI = "x:"
GEREKCE_BOS = "iddia bos, hafizaya aday degil"
GEREKCE_TAVAN = "merak tavani doldu: bu kaynaktan bugun {tavan} yeni iddia sayildi"
GEREKCE_GECTI = "uc agiz kurali: {sayi}/{esik} bagimsiz kaynak"
GEREKCE_BEKLE = "uc agiz kurali: {sayi}/{esik} bagimsiz kaynak, yetmedi"
GEREKCE_COKTU = "bekci giris kapisi hata verdi, varsayilan hayir (spec 3.7)"

SEMA = """
CREATE TABLE IF NOT EXISTS kaynaklar (kaynak TEXT PRIMARY KEY, oksitosin REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS agizlar (iddia TEXT, kaynak TEXT, tarih TEXT, UNIQUE (iddia, kaynak));
CREATE INDEX IF NOT EXISTS agiz_iddia ON agizlar (iddia);
CREATE TABLE IF NOT EXISTS giris_kararlari (tarih TEXT, kaynak TEXT, yigit INTEGER, gecti INTEGER,
    gerekce TEXT);
"""


def kur(baglanti):
    """Giris kapisinin tablolarini kurar (defter sqlite'inin icinde)."""
    baglanti.executescript(SEMA)


def iddia_anahtari(metin):
    """Tur 1 iddia cikarimi LLM'siz: kayit metninin kucuk harfli, bosluklari tekillesmis hali."""
    return " ".join(str(metin).lower().split())


def gecsin_mi(baglanti, bilgi, kaynak, tarih, platform=None):
    """(evet_hayir, gerekce) dondurur, gerekce hic bos degil. Hata olursa loglar ve varsayilan
    "hayir" doner: kapali kapi acik kapidan guvenlidir (spec 3.7)."""
    basladi = time.perf_counter()
    kaynak = kaynak_kimligi(kaynak, platform)
    try:
        with baglanti:
            evet, gerekce, sayi = _karar(baglanti, iddia_anahtari(bilgi), kaynak, tarih)
            baglanti.execute("INSERT INTO giris_kararlari VALUES (?, ?, ?, ?, ?)",
                             (tarih, kaynak, kaynak in YIGIT_KAYNAKLARI, evet, gerekce))
    except Exception as hata:
        log.yaz(YUVA_ADI, "gecsin_mi", _gecen_ms(basladi), "hata", {"kaynak": kaynak, "hata": str(hata)})
        return False, GEREKCE_COKTU
    log.yaz(YUVA_ADI, "gecsin_mi", _gecen_ms(basladi), "ok",
            {"kaynak": kaynak, "karar": evet, "gerekce": gerekce, "agiz_sayisi": sayi})
    return evet, gerekce


def kaynak_kimligi(kaynak, platform=None):
    """Agiz kimligi. X'te hesap adi kimliktir: "@Ali", "ali", "x:ALI" hepsi "x:ali" olur."""
    kaynak = str(kaynak or VARSAYILAN_KAYNAK).strip()
    x_mi = str(platform).strip().lower() in X_PLATFORMLARI or kaynak.lower().startswith(X_ONEKI)
    if not x_mi:
        return kaynak
    hesap = kaynak.lower().removeprefix(X_ONEKI).strip().lstrip("@")
    return X_ONEKI + hesap


def _karar(baglanti, iddia, kaynak, tarih):
    """(evet, gerekce, agiz_sayisi): once Yigit ve bos iddia, sonra merak tavani, sonra uc agiz."""
    if kaynak in YIGIT_KAYNAKLARI:
        return True, GEREKCE_YIGIT, 1
    if not iddia:
        return False, GEREKCE_BOS, 0
    yeni_agiz = not _agiz_var_mi(baglanti, iddia, kaynak)
    if yeni_agiz and _bugun_sayilan(baglanti, kaynak, tarih) >= MERAK_TAVANI:
        return False, GEREKCE_TAVAN.format(tavan=MERAK_TAVANI), _agiz_sayisi(baglanti, iddia)
    if yeni_agiz:
        baglanti.execute("INSERT INTO agizlar VALUES (?, ?, ?)", (iddia, kaynak, tarih))
    sayi, esik = _agiz_sayisi(baglanti, iddia), esik_hesapla(baglanti, kaynak)
    if sayi >= esik:
        return True, GEREKCE_GECTI.format(sayi=sayi, esik=esik), sayi
    return False, GEREKCE_BEKLE.format(sayi=sayi, esik=esik), sayi


def esik_hesapla(baglanti, kaynak):
    """Kaynagin oksitosin agirligi yuksekse OKSITOSIN_ESIGI, degilse UC_AGIZ_ESIGI."""
    satir = baglanti.execute("SELECT oksitosin FROM kaynaklar WHERE kaynak = ?", (kaynak,)).fetchone()
    yuksek = satir is not None and satir[0] >= OKSITOSIN_YUKSEK
    return OKSITOSIN_ESIGI if yuksek else UC_AGIZ_ESIGI


def oksitosin_yaz(baglanti, kaynak, deger):
    """Kaynak tablosuna kaynagin oksitosin agirligini yazar (kademe 5, geri alinabilir tablo)."""
    with baglanti:
        baglanti.execute("INSERT OR REPLACE INTO kaynaklar VALUES (?, ?)", (kaynak, deger))


def _agiz_var_mi(baglanti, iddia, kaynak):
    """Bu kaynak bu iddiayi daha once soyledi mi (ayni kaynagin tekrari sayilmaz)."""
    sorgu = "SELECT 1 FROM agizlar WHERE iddia = ? AND kaynak = ?"
    return baglanti.execute(sorgu, (iddia, kaynak)).fetchone() is not None


def _agiz_sayisi(baglanti, iddia):
    """Iddiayi soyleyen farkli kaynak sayisi."""
    sorgu = "SELECT COUNT(*) FROM agizlar WHERE iddia = ?"
    return baglanti.execute(sorgu, (iddia,)).fetchone()[0]


def _bugun_sayilan(baglanti, kaynak, tarih):
    """Kaynagin bu tarihte sayilan yeni iddia sayisi (merak tavani icin)."""
    sorgu = "SELECT COUNT(*) FROM agizlar WHERE kaynak = ? AND tarih = ?"
    return baglanti.execute(sorgu, (kaynak, tarih)).fetchone()[0]


def red_oranlari(baglanti):
    """Otoimmunite olceri: (genel red orani, Yigit kaynakli red orani); karar yoksa None."""
    sorgu = "SELECT yigit, COUNT(*), SUM(1 - gecti) FROM giris_kararlari GROUP BY yigit"
    sayim = {bool(s[0]): (s[1], s[2]) for s in baglanti.execute(sorgu)}
    toplam = sum(s[0] for s in sayim.values())
    red = sum(s[1] for s in sayim.values())
    genel = red / toplam if toplam else None
    yigit = sayim[True][1] / sayim[True][0] if True in sayim else None
    return genel, yigit


def _gecen_ms(basladi):
    """Olcum baslangicindan bu yana gecen sureyi tam sayi milisaniye verir."""
    return int((time.perf_counter() - basladi) * 1000)
