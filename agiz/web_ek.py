"""Web agzinin engelsiz ek kaynaklari (f10-b, K31=A): Ingilizce Vikipedi, Wikidata ve Marginalia arama API'leri
icin adres kaliplari ve JSON ayristiricilari. Anahtarsiz/oturumsuz, 2026-09-24 olculdu. Cagiran: agiz/web.py."""

import json

from agiz import web_iddia

EN_VIKI_ALANI = "en.wikipedia.org"
WIKIDATA_ADRESI = ("https://www.wikidata.org/w/api.php?action=wbsearchentities&format=json"
                   "&language=en&uselang=en&limit={n}&search=")
# "public" Marginalia'nin herkese acik paylasilan anahtari (belgelerinde yazili); oturum ya da hesap degil.
MARGINALIA_ADRESI = "https://api.marginalia.nu/public/search/{sorgu}?count={n}"


def en_viki_ayristir(metin):
    """en.wikipedia giris cumleli arama JSON'unu sonuc listesine cevirir (ozet = kisa iddia, f10-c)."""
    return web_iddia.viki_giris_ayristir(metin, EN_VIKI_ALANI)


def wikidata_ayristir(metin):
    """Wikidata varlik aramasini sonuc listesine cevirir: baslik = etiket, ozet = kisa tanim."""
    arama = json.loads(metin)["search"]
    return [{"baslik": s.get("label", ""), "ozet": _tanim_cumlesi(s),
             "adres": "https:" + s["url"] if s["url"].startswith("//") else s["url"]} for s in arama]


def _tanim_cumlesi(varlik):
    """Wikidata tanimi tek basina iddia degil ("biological process"); etiketle birlikte cumle olur."""
    tanim = varlik.get("description", "")
    return f"{varlik.get('label', '')}: {tanim}" if tanim else ""


def marginalia_ayristir(metin):
    """Marginalia arama JSON'unu sonuc listesine cevirir; her sonuc kendi sitesinin alan adiyla gelir."""
    return [{"baslik": s.get("title", ""), "ozet": web_iddia.kisa_iddia(s.get("description", "")), "adres": s["url"]}
            for s in json.loads(metin)["results"]]


def adresler(kodlu, en_cok):
    """Ek kaynaklarin (ad, adres, ayristirici) listesi; web.ara sirayla dolasir."""
    return [("en_viki", web_iddia.viki_giris_adresi(EN_VIKI_ALANI, kodlu, en_cok), en_viki_ayristir),
            ("wikidata", WIKIDATA_ADRESI.format(n=en_cok) + kodlu, wikidata_ayristir),
            ("marginalia", MARGINALIA_ADRESI.format(sorgu=kodlu, n=en_cok), marginalia_ayristir)]
