"""Sabah demosu: hatirlama once/sonra, 20 soruluk oturum ve web sohbet uctan uca; her sey gecici defterde, Kafa 8081'de.
Cagiran: elle `python araclar/sabah_demo.py [--sahte] [--device Vulkan1] [--cikti KLASOR]`, tests/test_sabah_demo.py."""

import argparse
import os
import sys
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))

DEMO_KAFA_PORT = 8081  # gercek web sohbetin Kafa'si 8080'de, cakismasin
SAHTE_GOMME_PORT = 8097  # gercek gomme 8093'e dokunulmaz
VARSAYILAN_CIKTI = KOK / "loglar" / "sabah-demo"
VARSAYILAN_CIHAZ = "Vulkan1"
DOLU_VRAM_MIB = 1000  # ustundeyse baska GPU isi var, demo baslamaz
SAGLIK_ZAMAN_ASIMI_SN = 2


def ilerleme(metin):
    print(f"[{datetime.now():%H:%M:%S}] {metin}", flush=True)


def _secenekler():
    ayristirici = argparse.ArgumentParser(description="Minik sabah demosu")
    ayristirici.add_argument("--sahte", action="store_true", help="GPU'suz sahte Kafa ve gomme")
    ayristirici.add_argument("--device", default=VARSAYILAN_CIHAZ)
    ayristirici.add_argument("--cikti", type=Path, default=VARSAYILAN_CIKTI)
    ayristirici.add_argument("--az", action="store_true", help="testler icin kucuk soru kumesi")
    return ayristirici.parse_args()


def _ortam_kur(gecici, sahte):
    """Proje modulleri ice aktarilmadan once: ayar.py sabitleri bu degiskenlerden okur."""
    os.environ["MINIK_KAFA_PORT"] = str(DEMO_KAFA_PORT)
    os.environ["MINIK_DEFTER_KLASORU"] = str(gecici / "bos-defter")  # gercek defter/ hic gorulmesin
    if sahte:
        os.environ["MINIK_GOMME_PORT"] = str(SAHTE_GOMME_PORT)


def _gpu_bos_mu():
    """Gercek modda: kullanilan VRAM DOLU_VRAM_MIB ustundeyse cikis mesajiyla durur."""
    from ortak.sunucu import gpu_bellek_mib
    kullanilan = gpu_bellek_mib()
    if kullanilan > DOLU_VRAM_MIB:
        sys.exit(f"GPU'da {kullanilan} MiB kullaniliyor (> {DOLU_VRAM_MIB}): baska GPU isi var, demo baslamadi.")
    ilerleme(f"GPU bos: {kullanilan} MiB")
    return kullanilan


def _port_acik_mi(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=SAGLIK_ZAMAN_ASIMI_SN):
            return True
    except OSError:
        return False  # baglanamamak = kapali, aranan sonuc bu


def _kafa_yoneticisi(sahte, cihaz):
    from ortak.ayar import GEMMA_SUNUCU_ARGUMANLARI
    from sabah_demo_web import cihaz_ez
    ilerleme(f"--device {cihaz_ez(GEMMA_SUNUCU_ARGUMANLARI, cihaz)} -> {cihaz}")
    if sahte:
        from sabah_demo_sahte import SahteYonetici
        return SahteYonetici()
    from agiz.web_sohbet_kafa import KafaYonetici
    return KafaYonetici()


def _asamalar(secenek, kok):
    """1 ve 2 demo'nun kendi Kafa'siyla; Kafa kapatilir, sonra 3 (alt surec kendi Kafa'sini acar)."""
    import sabah_demo_asama as asama
    import sabah_demo_veri as veri
    from sabah_demo_uctan import uctan_asamasi
    bilgiler = veri.BILGILER[:veri.AZ_BILGI_SAYISI] if secenek.az else veri.BILGILER
    sorular = veri.OTURUM_SORULARI[:veri.AZ_OTURUM_SORU_SAYISI] if secenek.az else veri.OTURUM_SORULARI
    yonetici = _kafa_yoneticisi(secenek.sahte, secenek.device)
    try:
        hatirlama = asama.hatirlama_asamasi(yonetici.dusun, kok, bilgiler, ilerleme)
        oturum = asama.oturum_asamasi(yonetici.dusun, kok, sorular, ilerleme)
    finally:
        yonetici.kapat()
    uctan = uctan_asamasi(kok, secenek.sahte, secenek.device, ilerleme)
    return {"hatirlama": hatirlama, "oturum": oturum, "uctan": uctan}


def _kapanis(sahte, sahte_sunucular):
    """Sahte sunuculari kapatir; demo Kafa portu kapali mi, gercek modda VRAM ne, bakar."""
    for sunucu in sahte_sunucular:
        sunucu.shutdown()
        sunucu.server_close()
    kapanis = {"kafa_8081_kapali": not _port_acik_mi(DEMO_KAFA_PORT)}
    if not sahte:
        from ortak.sunucu import gpu_bellek_mib
        kapanis["vram_mib"] = gpu_bellek_mib()
    ilerleme(f"kapanis: {kapanis}")
    return kapanis


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # Turkce harfler boru/konsolda bozulmasin
    secenek = _secenekler()
    baslangic = datetime.now()
    with tempfile.TemporaryDirectory(prefix="sabah-demo-", ignore_cleanup_errors=True) as gecici:
        kok = Path(gecici)
        _ortam_kur(kok, secenek.sahte)
        sahte_sunucular = []
        if secenek.sahte:
            import sabah_demo_sahte
            sahte_sunucular = [sabah_demo_sahte.baslat(DEMO_KAFA_PORT), sabah_demo_sahte.baslat(SAHTE_GOMME_PORT)]
        vram_once = None if secenek.sahte else _gpu_bos_mu()
        sonuc = {"zaman": baslangic.isoformat(timespec="seconds"), "sahte": secenek.sahte,
                 "device": secenek.device, "vram_once_mib": vram_once, **_asamalar(secenek, kok)}
        sonuc["kapanis"] = _kapanis(secenek.sahte, sahte_sunucular)
    import sabah_demo_rapor
    yollar = sabah_demo_rapor.yaz(sonuc, secenek.cikti / f"sabah-demo-{baslangic:%Y%m%d-%H%M}")
    ilerleme(f"yazildi: {yollar[0]} ve {yollar[1]}")


if __name__ == "__main__":
    main()
