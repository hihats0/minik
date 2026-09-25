"""f10-e olcumu: DuckDuckGo HTML ve Google aramasini gercek Chrome (Playwright channel=chrome, ayri kalici profil) ile dener.
Engel/CAPTCHA asilmaz, o motor durur. Cagiran: elle, `python deneyler/f10e-chrome-arama-olc.py [--gorunur]`."""

import json
import os
import sys
import time
import urllib.parse

from playwright.sync_api import sync_playwright

PROFIL = os.path.join(os.environ["LOCALAPPDATA"], "minik", "arama-profil-chrome")
SORGULAR = ["photosynthesis", "speed of light", "mount everest height", "fotosentez nedir", "python programming language"]
MOTORLAR = {"ddg": "https://html.duckduckgo.com/html/?q={}", "google": "https://www.google.com/search?hl=tr&q={}"}
ENGEL_METINLERI = ("unusual traffic", "olağan dışı trafik", "captcha", "anomaly-modal", "challenge-form", "/sorry/")
RED_DUGMELERI = ("Tümünü reddet", "Reject all")
ISTEK_ARASI_SN = 1.5
SAYFA_ZAMAN_ASIMI_MS = 20000
SONUC_JS = {
    "ddg": "[...document.querySelectorAll('a.result__a')].map(a => a.href)",
    "google": "[...document.querySelectorAll('#search a:has(h3)')].map(a => a.href)",
}


def alan(adres):
    """Adresin alan adi, www. atilmis; DDG yonlendirmesinde asil adres kullanilir."""
    parca = urllib.parse.urlsplit(adres)
    asil = urllib.parse.parse_qs(parca.query).get("uddg")
    if asil:
        parca = urllib.parse.urlsplit(asil[0])
    return parca.netloc.lower().removeprefix("www.")


def onayi_reddet(sayfa):
    """Cerez onay sayfasi varsa en gizlilikci secenegi (reddet) tiklar; tikladiysa True."""
    for metin in RED_DUGMELERI:
        dugme = sayfa.get_by_role("button", name=metin)
        if dugme.count():
            dugme.first.click()
            sayfa.wait_for_load_state()
            return True
    return False


def olc(sayfa, motor, sorgu):
    """Tek sorgu, tek istek; durum sonuc/engel/hata ve alan adlarini dondurur."""
    try:
        sayfa.goto(MOTORLAR[motor].format(urllib.parse.quote(sorgu)), timeout=SAYFA_ZAMAN_ASIMI_MS)
        reddedildi = onayi_reddet(sayfa)
        # Kaynak degil gorunen metin: Google sonuc sayfasinin kaynaginda "captcha" dizgesi var (yanlis pozitif, olculdu).
        ozet = " ".join(sayfa.inner_text("body").split())[:200]
        if any(i in (ozet + sayfa.url).lower() for i in ENGEL_METINLERI) or sayfa.locator("form#challenge-form").count():
            return {"durum": "engel", "url": sayfa.url, "ekran": ozet, "onay_red": reddedildi}
        alanlar = [alan(a) for a in sayfa.evaluate(SONUC_JS[motor]) if a.startswith("http")]
        alanlar = [a for a in alanlar if a and "google." not in a and "duckduckgo.com" not in a]
        return {"durum": "sonuc", "sayi": len(alanlar), "alanlar": sorted(set(alanlar)), "onay_red": reddedildi}
    except Exception as hata:  # olcum araci: her hata sonuc satirina yazilir, yutulmaz
        return {"durum": "hata", "hata": str(hata)[:200]}


def calistir(gorunur):
    """Her motor icin sorgulari sirayla dener; engelde o motor durur (tekrar yok)."""
    satirlar = []
    with sync_playwright() as p:
        baglam = p.chromium.launch_persistent_context(PROFIL, channel="chrome", headless=not gorunur)
        sayfa = baglam.new_page()
        for motor in [m for m in MOTORLAR if m in sys.argv] or MOTORLAR:
            for sorgu in SORGULAR:
                sonuc = {"motor": motor, "sorgu": sorgu, "gorunur": gorunur, **olc(sayfa, motor, sorgu)}
                satirlar.append(sonuc)
                print(json.dumps(sonuc, ensure_ascii=False), flush=True)
                time.sleep(ISTEK_ARASI_SN)
                if sonuc["durum"] == "engel":
                    break
        baglam.close()
    return satirlar


if __name__ == "__main__":
    calistir("--gorunur" in sys.argv)
