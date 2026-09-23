"""X girisi: Minik'in kalici tarayici profilini gorunur pencerede acar, Yigit kendisi giris yapar.
Cagiran: Yigit ya da ana oturum, elle (python araclar/x-giris.py). Sifre hicbir yere yazilmaz."""
import os
from playwright.sync_api import sync_playwright

PROFIL_KLASORU = os.path.join(os.environ["LOCALAPPDATA"], "minik", "x-profil")
GIRIS_ADRESI = "https://x.com/i/flow/login"
BEKLEME_SINIRI_MS = 30 * 60 * 1000  # pencere en fazla 30 dk acik kalir


def main():
    os.makedirs(PROFIL_KLASORU, exist_ok=True)
    with sync_playwright() as p:
        baglam = p.chromium.launch_persistent_context(PROFIL_KLASORU, headless=False)
        sayfa = baglam.pages[0] if baglam.pages else baglam.new_page()
        sayfa.goto(GIRIS_ADRESI)
        print("Pencere acik. Giris yapip pencereyi kapat.", flush=True)
        try:
            sayfa.wait_for_event("close", timeout=BEKLEME_SINIRI_MS)
        except Exception as hata:  # zaman asimi: oturum yine de profilde kalir
            print(f"bekleme bitti: {hata}", flush=True)
        baglam.close()
        print("Profil kaydedildi:", PROFIL_KLASORU, flush=True)


if __name__ == "__main__":
    main()
