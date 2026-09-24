"""DuckDuckGo HTML sayfasini gercek Chrome ile (Playwright channel=chrome, gorunur pencere, ayri kalici profil) okur.
f10-e: urllib ve headless Chrome 202/CAPTCHA aliyor, gorunur Chrome 5/5 sonuc verdi. Cagiran: agiz/web.py (ddg kaynagi)."""

import os
import urllib.error

PROFIL = os.path.join(os.environ.get("LOCALAPPDATA", "."), "minik", "arama-profil-chrome")
KANAL = "chrome"
# Olculdu: headless Chrome ilk istekte DDG CAPTCHA'si aldi; gorunur pencere almadi. Tespit atlatma yok.
GORUNMEZ = False
SAYFA_ZAMAN_ASIMI_MS = 20000


def _chrome_ac(adres):
    """Gercek Chrome'u ayri profille acar, adrese gider, (durum kodu, html) dondurur, pencereyi kapatir."""
    from playwright.sync_api import sync_playwright  # agir paket; yalniz gercek aramada yuklenir
    with sync_playwright() as p:
        baglam = p.chromium.launch_persistent_context(PROFIL, channel=KANAL, headless=GORUNMEZ)
        try:
            yanit = baglam.new_page().goto(adres, timeout=SAYFA_ZAMAN_ASIMI_MS)
            return yanit.status, baglam.pages[-1].content()
        finally:
            baglam.close()


def oku(adres, acici=_chrome_ac):
    """(kod, metin) dondurur; tarayici hatasi web agzinin tanidigi URLError'a cevrilir (kaynak atlanir, loglanir)."""
    try:
        return acici(adres)
    except Exception as hata:  # Playwright kendi hata turlerini atar; hepsi tek kaynak hatasi sayilir
        raise urllib.error.URLError(f"chrome: {hata}") from hata
