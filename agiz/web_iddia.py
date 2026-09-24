"""Web kaynagindan kisa iddia cikarma (f10-c): arama ozeti yerine sayfa girisinin ilk cumlesi ve sayi/tarih
iceren ilk cumle; Vikipedi giris (extracts) JSON ayristiricisi. Standart kutuphane. Cagiran: agiz/web.py, agiz/web_ek.py."""

import json
import re
import urllib.parse

# Vikipedi aramasi sayfa girisinin ilk cumleleriyle gelir (generator=search + prop=extracts), tek istek.
VIKI_GIRIS_ADRESI = ("https://{alan}/w/api.php?action=query&format=json&generator=search&gsrlimit={n}"
                     "&prop=extracts&exintro=1&explaintext=1&exsentences=3&exlimit=max&gsrsearch=")
CUMLE_SONU = re.compile(r"(?<=[.!?])\s+(?=[A-ZÇĞİÖŞÜ0-9\"'(])")
SAYI_DESENI = re.compile(r"\d")
EN_KISA_CUMLE = 20  # "Vd." gibi kesik parcalar iddia sayilmaz
EN_UZUN_IDDIA = 300  # Kafa'ya giden karsilastirma sorusu kisa kalsin


def cumleler(metin):
    """Metni cumlelere boler; bosluklar tekillesir, cok kisa parcalar atilir."""
    duz = " ".join(str(metin).split())
    return [c for c in CUMLE_SONU.split(duz) if len(c) >= EN_KISA_CUMLE]


def kisa_iddia(metin):
    """Ilk cumle; ilk cumlede sayi yoksa sayi/tarih iceren ilk cumle de eklenir. Cumle yoksa metnin kendisi."""
    parcalar = cumleler(metin)
    if not parcalar:
        return " ".join(str(metin).split())[:EN_UZUN_IDDIA]
    secilen = [parcalar[0]]
    if not SAYI_DESENI.search(parcalar[0]):
        secilen += [c for c in parcalar[1:] if SAYI_DESENI.search(c)][:1]
    return " ".join(secilen)[:EN_UZUN_IDDIA]


def viki_giris_adresi(alan, kodlu, en_cok):
    """Verilen Vikipedi alani icin giris cumleli arama adresi."""
    return VIKI_GIRIS_ADRESI.format(alan=alan, n=en_cok) + kodlu


def viki_giris_ayristir(metin, alan):
    """Giris cumleli arama JSON'unu arama sirasina gore sonuc listesine cevirir; ozet = kisa iddia."""
    sayfalar = sorted(json.loads(metin).get("query", {}).get("pages", {}).values(), key=lambda s: s["index"])
    return [{"baslik": s["title"], "ozet": kisa_iddia(s.get("extract", "")),
             "adres": f"https://{alan}/wiki/" + urllib.parse.quote(s["title"].replace(" ", "_"))}
            for s in sayfalar]
