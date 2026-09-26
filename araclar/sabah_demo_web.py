"""Sabah demosunun alt sureci: agiz.web_sohbet'i --device ezilmis ve (--sahte ise) GPU'suz Kafa ile acar.
Cagiran: araclar/sabah_demo_uctan.py (`python araclar/sabah_demo_web.py --port 8095 [--sahte] [--device X]`)."""

import argparse
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))


def cihaz_ez(arguman_listesi, cihaz):
    """GEMMA_SUNUCU_ARGUMANLARI'ndaki --device degerini yerinde degistirir, eskisini doner."""
    yer = arguman_listesi.index("--device") + 1
    eski, arguman_listesi[yer] = arguman_listesi[yer], cihaz
    return eski


def main():
    ayristirici = argparse.ArgumentParser()
    ayristirici.add_argument("--port", required=True)
    ayristirici.add_argument("--device", required=True)
    ayristirici.add_argument("--sahte", action="store_true")
    secenek = ayristirici.parse_args()
    from ortak.ayar import GEMMA_SUNUCU_ARGUMANLARI  # env (MINIK_*) sabitlerden once okunmus olmali
    cihaz_ez(GEMMA_SUNUCU_ARGUMANLARI, secenek.device)
    from agiz import web_sohbet, web_sohbet_kafa
    if secenek.sahte:
        from sabah_demo_sahte import SahteYonetici
        web_sohbet_kafa.KafaYonetici = SahteYonetici  # main() yoneticiyi bu addan ice aktarir
    sys.argv = [sys.argv[0], "--port", secenek.port]
    web_sohbet.main()


if __name__ == "__main__":
    main()
