"""Web agzinin engelsiz ek kaynaklari (f10-b, K31=A): Ingilizce Vikipedi, Wikidata ve Marginalia arama API'leri
icin adres kaliplari ve JSON ayristiricilari. Anahtarsiz/oturumsuz, 2026-09-24 olculdu. Cagiran: agiz/web.py."""

import html
import json
import re
import urllib.parse

EN_VIKI_ALANI = "en.wikipedia.org"
EN_VIKI_ADRESI = "https://en.wikipedia.org/w/api.php?action=query&list=search&format=json&srlimit={n}&srsearch="
WIKIDATA_ADRESI = ("https://www.wikidata.org/w/api.php?action=wbsearchentities&format=json"
                   "&language=en&uselang=en&limit={n}&search=")
# "public" Marginalia'nin herkese acik paylasilan anahtari (belgelerinde yazili); oturum ya da hesap degil.
MARGINALIA_ADRESI = "https://api.marginalia.nu/public/search/{sorgu}?count={n}"
ETIKET_DESENI = re.compile(r"<[^>]+>")


def en_viki_ayristir(metin):
    """en.wikipedia arama JSON'unu sonuc listesine cevirir; ozetteki vurgu etiketleri silinir."""
    arama = json.loads(metin)["query"]["search"]
    return [{"baslik": s["title"], "ozet": html.unescape(ETIKET_DESENI.sub("", s["snippet"])),
             "adres": f"https://{EN_VIKI_ALANI}/wiki/" + urllib.parse.quote(s["title"].replace(" ", "_"))}
            for s in arama]


def wikidata_ayristir(metin):
    """Wikidata varlik aramasini sonuc listesine cevirir: baslik = etiket, ozet = kisa tanim."""
    arama = json.loads(metin)["search"]
    return [{"baslik": s.get("label", ""), "ozet": s.get("description", ""),
             "adres": "https:" + s["url"] if s["url"].startswith("//") else s["url"]} for s in arama]


def marginalia_ayristir(metin):
    """Marginalia arama JSON'unu sonuc listesine cevirir; her sonuc kendi sitesinin alan adiyla gelir."""
    return [{"baslik": s.get("title", ""), "ozet": s.get("description", ""), "adres": s["url"]}
            for s in json.loads(metin)["results"]]


def adresler(kodlu, en_cok):
    """Ek kaynaklarin (ad, adres, ayristirici) listesi; web.ara sirayla dolasir."""
    return [("en_viki", EN_VIKI_ADRESI.format(n=en_cok) + kodlu, en_viki_ayristir),
            ("wikidata", WIKIDATA_ADRESI.format(n=en_cok) + kodlu, wikidata_ayristir),
            ("marginalia", MARGINALIA_ADRESI.format(sorgu=kodlu, n=en_cok), marginalia_ayristir)]
