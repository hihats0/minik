"""Web agzi (f10): merak edilen sorguyu DuckDuckGo HTML, Turkce Vikipedi ve web_ek kaynaklarindan okur, sonuclari Bekci giris
kaydina cevirir (kaynak = alan adi, iddia = kisa cumle). Oturum acmaz, engel gorurse durur. Cagiran: yuvalar/merak.py, araclar/."""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from agiz import web_ek, web_iddia
from ortak import log

YUVA_ADI = "agiz_web"
PLATFORM = "web"
DDG_ADRESI = "https://html.duckduckgo.com/html/?q="
VIKI_ALANI = "tr.wikipedia.org"
EN_COK_SONUC = 10
ZAMAN_ASIMI_SN = 15
# f10-b: Marginalia 5 istekten 4unde zaman asimina dustu; zaman asiminda bir kez daha denenir, loglanir.
ZAMAN_ASIMI_TEKRAR = 1
SITE_ARASI_SN = 1.0  # ayni siteye saniyede en fazla bir istek
TARAYICI_KIMLIGI = "Mozilla/5.0 (Minik arastirma; tek kullanici, saniyede 1 istek)"
KOD_COZUMU = "utf-8"
# DuckDuckGo bot sandiginda "anomaly" sayfasi ya da 202 doner; ikisi de engel sayilir, asilmaz.
ENGEL_ISARETLERI = ("anomaly-modal", "challenge-form", "captcha")
ENGEL_KODU = 202
DDG_YONLENDIRME_ANAHTARI = "uddg"


class Engellendi(RuntimeError):
    """Site bot engeli ya da CAPTCHA gosterdi; arama durur, asilmaya calisilmaz."""


_son_istek = {}


def bekle(alan, saat=time.monotonic, uyu=time.sleep):
    """Ayni alana iki istek arasinda en az SITE_ARASI_SN gecmesini saglar."""
    simdi = saat()
    once = _son_istek.get(alan)
    if once is not None and simdi - once < SITE_ARASI_SN:
        uyu(SITE_ARASI_SN - (simdi - once))
        simdi = saat()
    _son_istek[alan] = simdi


def getir(adres):
    """Adresi hiz sinirina uyarak okur, metni dondurur; her istek loglanir, engel Engellendi yukseltir."""
    alan = alan_adi(adres)
    bekle(alan)
    basladi = time.perf_counter()
    istek = urllib.request.Request(adres, headers={"User-Agent": TARAYICI_KIMLIGI})
    try:
        with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI_SN) as yanit:
            kod, metin = yanit.status, yanit.read().decode(KOD_COZUMU, errors="replace")
    except (urllib.error.URLError, TimeoutError) as hata:
        log.yaz(YUVA_ADI, "istek", _ms(basladi), "hata", {"alan": alan, "hata": str(hata)})
        raise
    detay = {"alan": alan, "kod": kod, "bayt": len(metin)}
    if engel_mi(kod, metin):
        detay["hata"] = f"engellendi (kod {kod})"
        log.yaz(YUVA_ADI, "istek", _ms(basladi), "hata", detay)
        raise Engellendi(f"{alan} {detay['hata']}")
    log.yaz(YUVA_ADI, "istek", _ms(basladi), "ok", detay)
    return metin


def engel_mi(kod, metin):
    """Yanit bot engeli ya da CAPTCHA mi."""
    return kod == ENGEL_KODU or any(i in metin for i in ENGEL_ISARETLERI)


def alan_adi(adres):
    """Agiz kimligi: adresin alan adi, "www." atilmis, kucuk harf."""
    return urllib.parse.urlsplit(adres).netloc.lower().removeprefix("www.")


class _DdgAyristirici(HTMLParser):
    """DuckDuckGo HTML sayfasindan (baslik, adres, ozet) uclerini toplar."""

    def __init__(self):
        super().__init__()
        self.sonuclar, self._alan, self._adres = [], None, None

    def handle_starttag(self, etiket, nitelikler):
        n = dict(nitelikler)
        sinif = n.get("class") or ""
        if etiket == "a" and "result__a" in sinif:
            self._adres, self._alan = _gercek_adres(n.get("href", "")), "baslik"
            self.sonuclar.append({"baslik": "", "adres": self._adres, "ozet": ""})
        elif etiket == "a" and "result__snippet" in sinif and self.sonuclar:
            self._alan = "ozet"

    def handle_endtag(self, etiket):
        if etiket == "a":
            self._alan = None

    def handle_data(self, veri):
        if self._alan:
            self.sonuclar[-1][self._alan] += veri


def _gercek_adres(href):
    """DuckDuckGo yonlendirme adresinden (//duckduckgo.com/l/?uddg=...) asil adresi cikarir."""
    sorgu = urllib.parse.parse_qs(urllib.parse.urlsplit(href).query)
    return sorgu.get(DDG_YONLENDIRME_ANAHTARI, [href])[0]


def ddg_ayristir(sayfa):
    """DuckDuckGo HTML sayfasini sonuc listesine cevirir (reklam adresleri dahil degil)."""
    ayristirici = _DdgAyristirici()
    ayristirici.feed(sayfa)
    return [s for s in ayristirici.sonuclar if s["adres"].startswith("http") and "duckduckgo.com" not in s["adres"]]


def viki_ayristir(metin):
    """Turkce Vikipedi giris cumleli arama JSON'unu sonuc listesine cevirir (ozet = kisa iddia)."""
    return web_iddia.viki_giris_ayristir(metin, VIKI_ALANI)


def kayda_cevir(sorgu, sonuc):
    """Tek sonucu Bekci'nin bekledigi kayda cevirir: iddia `soru`, agiz `kaynak` (alan adi)."""
    return {"soru": " ".join(sonuc["ozet"].split()), "cevap": sonuc["baslik"].strip(),
            "kaynak": alan_adi(sonuc["adres"]), "platform": PLATFORM, "adres": sonuc["adres"], "sorgu": sorgu}


def ara(sorgu, en_cok=EN_COK_SONUC):
    """Sorguyu butun kaynaklarda arar, bos ozetleri atar, kayit listesi dondurur. Engelli ya da ulasilamayan
    kaynak loglanip atlanir (asilmaz); digerleriyle devam edilir."""
    kodlu = urllib.parse.quote(sorgu)
    kaynaklar = [("ddg", DDG_ADRESI + kodlu, ddg_ayristir),
                 ("tr_viki", web_iddia.viki_giris_adresi(VIKI_ALANI, kodlu, en_cok), viki_ayristir)] + web_ek.adresler(kodlu, en_cok)
    sonuclar = []
    for ad, adres, ayristirici in kaynaklar:
        sonuclar += _kaynaktan(sorgu, ad, adres, ayristirici)[:en_cok]
    kayitlar = [kayda_cevir(sorgu, s) for s in sonuclar if s["ozet"].strip()]
    log.yaz(YUVA_ADI, "ara", 0, "ok", {"sorgu": sorgu, "kayit": len(kayitlar),
                                        "alan": len({k["kaynak"] for k in kayitlar})})
    return kayitlar


def _kaynaktan(sorgu, ad, adres, ayristirici):
    """Tek kaynagi okur; engel ya da ag hatasi loglanir ve bos liste doner, bir kaynak digerlerini durdurmaz."""
    try:
        return ayristirici(_zaman_asiminda_tekrarla(sorgu, ad, adres))
    except (Engellendi, urllib.error.URLError, TimeoutError, ValueError, KeyError) as hata:
        log.yaz(YUVA_ADI, "ara", 0, "hata", {"sorgu": sorgu, "kaynak": ad, "hata": str(hata)})
        return []


def _zaman_asiminda_tekrarla(sorgu, ad, adres, getirici=None):
    """getir(adres); zaman asiminda ZAMAN_ASIMI_TEKRAR kez daha dener, her tekrar loglanir. Diger hatalar gecer."""
    getirici = getirici or getir
    for deneme in range(ZAMAN_ASIMI_TEKRAR + 1):
        try:
            return getirici(adres)
        except (urllib.error.URLError, TimeoutError) as hata:
            if not zaman_asimi_mi(hata) or deneme == ZAMAN_ASIMI_TEKRAR:
                raise
            log.yaz(YUVA_ADI, "yeniden_dene", 0, "ok", {"sorgu": sorgu, "kaynak": ad, "hata": str(hata)})


def zaman_asimi_mi(hata):
    """urllib zaman asimini iki bicimde verir: dogrudan TimeoutError ya da URLError(reason=TimeoutError)."""
    return isinstance(hata, TimeoutError) or isinstance(getattr(hata, "reason", None), TimeoutError)


def _ms(basladi):
    """Baslangictan bu yana gecen milisaniye."""
    return int((time.perf_counter() - basladi) * 1000)
