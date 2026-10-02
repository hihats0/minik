"""X'te tek sayfayi Yigit'in giris yaptigi Chrome profiliyle okur, sonucu okundu ya da engel diye siniflar; engel asilmaz.
Cagiran: python -m agiz.x_oku [adres] ve tests/test_x_oku.py."""

import os
import sys
import time

PROFIL = os.path.join(os.environ.get("LOCALAPPDATA", "."), "minik", "x-profil-chrome")
# Chrome for Testing bu profilin cerezlerini cozemez (devam.md f8-d); gercek Chrome kanali sart.
KANAL = "chrome"
GORUNMEZ = False
SAYFA_ZAMAN_ASIMI_MS = 20000
# Tweetler sayfa yuklendikten sonra gelir; tek sayfa icinde en cok bu kadar beklenir, kaydirma yok.
TWEET_BEKLEME_MS = 5000
TWEET_SECICI = '[data-testid="tweetText"]'
VARSAYILAN_ADRES = "https://x.com/home"
ISTEK_ARALIGI_SN = 1.0

# Asagidaki isaretler tahmin; gercek engel ekrani gorulunce guncellenir.
GIRIS_URL_PARCALARI = ["/i/flow/login", "/login"]
CAPTCHA_URL_PARCALARI = ["/account/access"]
CAPTCHA_METINLERI = ["arkose", "authenticate"]
KISITLAMA_METINLERI = ["temporarily restricted", "geçici olarak kısıtlandı", "geçici kısıtlandı"]
OTURUM_DUSMUS_METINLERI = ["sign in", "giriş yap"]
OTURUM_GEREKEN_URL_PARCALARI = ["/home"]
PROFIL_KILIT_METINLERI = ["user data directory is already in use", "processsingleton", "profile appears to be in use"]

DURUM_OKUNDU = "okundu"
DURUM_ENGEL = "engel"

_son_istek = [float("-inf")]  # modul duzeyi: saniyede en cok bir istek


def _chrome_ac(adres):
    """Gercek Chrome'u X profiliyle acar, tek goto yapar, gozlem sozlugu (url, metin, tweetler) dondurur, kapatir."""
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightZamanAsimi  # agir paket; yalniz gercek okumada
    with sync_playwright() as p:
        baglam = p.chromium.launch_persistent_context(PROFIL, channel=KANAL, headless=GORUNMEZ)
        try:
            sayfa = baglam.new_page()
            sayfa.goto(adres, timeout=SAYFA_ZAMAN_ASIMI_MS)
            try:
                sayfa.wait_for_selector(TWEET_SECICI, timeout=TWEET_BEKLEME_MS)
            except PlaywrightZamanAsimi:
                pass  # tweet gelmemesi hata degil; engel sayfasi olabilir, siniflandirma karar verir
            return {
                "url": sayfa.url,
                "metin": sayfa.inner_text("body"),
                "tweetler": sayfa.locator(TWEET_SECICI).all_inner_texts(),
            }
        finally:
            baglam.close()


def _hiz_sinirla():
    """Son istekten bu yana ISTEK_ARALIGI_SN gecmediyse kalan sure kadar uyur, sonra zamani kaydeder."""
    kalan = ISTEK_ARALIGI_SN - (time.monotonic() - _son_istek[0])
    if kalan > 0:
        time.sleep(kalan)
    _son_istek[0] = time.monotonic()


def _ilk_eslesen(metin, parcalar):
    """metin icinde (kucuk harfle) gecen ilk parcayi, yoksa None dondurur."""
    kucuk = (metin or "").lower()
    return next((p for p in parcalar if p in kucuk), None)


def _engel(tur, url, isaret):
    return {"durum": DURUM_ENGEL, "tur": tur, "url": url, "isaret": isaret}


def siniflandir(istenen, gozlem):
    """Saf fonksiyon: istenen adres ve gozlemden okundu ya da engel sozlugu uretir, dayandigi isareti yazar."""
    url, metin, tweetler = gozlem.get("url", ""), gozlem.get("metin", ""), gozlem.get("tweetler", [])
    if tweetler:
        return {"durum": DURUM_OKUNDU, "sayi": len(tweetler), "metinler": list(tweetler), "url": url}
    isaret = _ilk_eslesen(url, CAPTCHA_URL_PARCALARI) or _ilk_eslesen(metin, CAPTCHA_METINLERI)
    if isaret:
        return _engel("captcha", url, isaret)
    isaret = _ilk_eslesen(metin, KISITLAMA_METINLERI)
    if isaret:
        return _engel("kisitlandi", url, isaret)
    isaret = _ilk_eslesen(url, GIRIS_URL_PARCALARI)
    oturum_gerekiyordu = _ilk_eslesen(istenen, OTURUM_GEREKEN_URL_PARCALARI) is not None
    if isaret:
        return _engel("oturum_dusmus" if oturum_gerekiyordu else "giris_istedi", url, isaret)
    isaret = _ilk_eslesen(metin, OTURUM_DUSMUS_METINLERI)
    if isaret:
        return _engel("oturum_dusmus", url, isaret)
    return _engel("bilinmeyen", url, (metin or "")[:200])


def oku(adres=VARSAYILAN_ADRES, acici=_chrome_ac):
    """Hiz sinirina uyup acici ile tek sayfa okur; profil kilitliyse zorla kapatmadan profil_kilitli doner."""
    _hiz_sinirla()
    try:
        gozlem = acici(adres)
    except Exception as hata:  # Playwright kendi hata turlerini atar; kilit disindakiler de sonucta gorunur kalir
        mesaj = str(hata)
        kilit = _ilk_eslesen(mesaj, PROFIL_KILIT_METINLERI)
        return _engel("profil_kilitli" if kilit else "bilinmeyen", "", kilit or f"hata: {mesaj[:300]}")
    return siniflandir(adres, gozlem)


def yazdir(sonuc):
    """Sonucu okunur satirlar halinde stdout'a basar."""
    if sonuc["durum"] == DURUM_OKUNDU:
        print(f"okundu: {sonuc['sayi']} tweet ({sonuc['url']})")
        for i, metin in enumerate(sonuc["metinler"], 1):
            print(f"  {i}. {metin.replace(chr(10), ' ')}")
    else:
        print(f"engel: {sonuc['tur']}")
        print(f"  url: {sonuc['url']}")
        print(f"  isaret: {sonuc['isaret']}")


if __name__ == "__main__":
    yazdir(oku(sys.argv[1] if len(sys.argv) > 1 else VARSAYILAN_ADRES))
