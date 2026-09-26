"""Gunduz hatirlamasi icin gomme sunucusunu (e5-small, yalniz CPU) acik tutar: aciksa dokunmaz, kapaliysa baslatir.
Cagiran: yuvalar/hatirlama.py (varsayilan gomme_al)."""

import urllib.request

from ortak import log, sunucu
from ortak.ayar import GOMME_MODEL_YOLU, GOMME_PORT

YUVA_ADI = "gomme_sunucu"
SAGLIK_URL = f"http://127.0.0.1:{GOMME_PORT}/health"
SAGLIK_ZAMAN_ASIMI_SN = 2
HTTP_TAMAM = 200
GOMME_ARGUMANLARI = ["--embedding", "-c", "512"]

_surec = None  # baslattigimiz sunucu; Minik kapanana kadar acik kalir


def hazirla():
    """Sunucu hazirsa True; degilse baslatip bekler. Baslatamazsa hatayi loglar, False doner."""
    global _surec
    if _saglikli_mi():
        return True
    try:
        _surec = sunucu.baslat(GOMME_MODEL_YOLU, GOMME_PORT, GOMME_ARGUMANLARI)
        sunucu.hazir_bekle(_surec, GOMME_PORT)
    except Exception as hata:
        log.yaz(YUVA_ADI, "hazirla", 0, "hata", {"hata": f"gomme sunucusu acilamadi: {hata}"})
        return False
    log.yaz(YUVA_ADI, "hazirla", 0, "ok", {"port": GOMME_PORT})
    return True


def _saglikli_mi():
    """/health 200 donuyorsa True. Baglanamamak hata degil, 'kapali' demektir."""
    try:
        with urllib.request.urlopen(SAGLIK_URL, timeout=SAGLIK_ZAMAN_ASIMI_SN) as yanit:
            return yanit.status == HTTP_TAMAM
    except OSError:
        return False
