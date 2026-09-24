"""Az-veri deneyinin yurutucusu: 4 kol x 3 tohumu sirayla egitir ve olcer, her koşudan once web
sohbeti, sicaklik kesme izini ve upscaler'i yoklar; 90 dk'da bir 15 dk sogur. Kesilirse yeniden
baslatmaz. Cagiran: elle `python araclar/az_deney_kosu.py` (arka planda). Sonuc: cocuk/agirlik/az_sonuclar.jsonl
"""

import json
import logging
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
AGIRLIK = KOK / "cocuk" / "agirlik"
SONUCLAR = AGIRLIK / "az_sonuclar.jsonl"
SICAK_IZI = KOK / "loglar" / "GPU-SICAK-DURDU"
SOHBET_UCU = "http://127.0.0.1:8090/durum"
UPSCALER_SURECI = "upscal"
SEANS_SN = 90 * 60
SOGUMA_SN = 15 * 60
TOPLAM_SN = 6 * 3600  # goal: toplam deney 6 saati gecmez
KOSU_PAYI_SN = 35 * 60  # bir kosunun soguma duraklariyla en uzun tahmini
TOHUMLAR = (1, 2, 3)
KOLLAR = {  # ad: (az_egit ek bayraklari, az_olc ek bayraklari); kosulacaklar komut satirindan
    "adamw": ([], []),
    "muon": (["--optimizer", "muon"], []),
    "sade": (["--sade-oran", "0.25"], []),
    "arsifonem": (["--veri-eki", "_ars", "--ayar", '{"sozluk": 17408}'], ["--arsifonem"]),
    "minik": (["--tur", "minik"], []),
}
TOKEN_MILYON = "50"

METIN = {"capture_output": True, "text": True, "encoding": "utf-8", "errors": "replace",
         "env": {**os.environ, "PYTHONIOENCODING": "utf-8"}}

log = logging.getLogger("az_kosu")


def sohbet_acik() -> bool:
    try:
        urllib.request.urlopen(SOHBET_UCU, timeout=3)
        return True
    except urllib.error.HTTPError:  # anahtarsiz 401 de "acik" demek
        return True
    except (urllib.error.URLError, OSError):
        return False


def upscaler_canli() -> bool:
    cikti = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Get-CimInstance Win32_Process | % CommandLine"],
                           **METIN).stdout
    return UPSCALER_SURECI in cikti.lower()


def engel() -> str | None:
    if SICAK_IZI.exists():
        return "gpu-bekci 85 C izi var"
    if sohbet_acik():
        return "web sohbet acik (8090)"
    if upscaler_canli():
        return "upscaler canli"
    return None


def kos(kol: str, tohum: int) -> dict | None:
    """Bir kolun bir tohumunu egitir ve olcer; basarisizsa None."""
    ad = f"az-{kol}-t{tohum}"
    egit_ek, olc_ek = KOLLAR[kol]
    egit = [sys.executable, "-m", "cocuk.az_egit", "--ad", ad, "--tohum", str(tohum),
            "--token-milyon", TOKEN_MILYON, *egit_ek]
    sonuc = subprocess.run(egit, cwd=KOK, **METIN)
    if sonuc.returncode != 0:
        log.error("%s egitim hatasi: %s", ad, sonuc.stderr[-800:])
        return None
    egitim = json.loads(sonuc.stdout.strip().splitlines()[-1])
    olc = subprocess.run([sys.executable, "-m", "cocuk.az_olc", "--ad", ad, *olc_ek], cwd=KOK, **METIN)
    if olc.returncode != 0:
        log.error("%s olcum hatasi: %s", ad, olc.stderr[-800:])
        return None
    return {"ad": ad, "kol": kol, "tohum": tohum, "egitim": egitim,
            "olcum": json.loads(olc.stdout.strip().splitlines()[-1])}


def yapilmis() -> set:
    if not SONUCLAR.exists():
        return set()
    return {json.loads(s)["ad"] for s in SONUCLAR.read_text("utf-8").splitlines() if s.strip()}


def sira(secilen: list) -> list:
    """Secilen kollar tohum tohum dengeli sirayla (once hepsinin tohum 1'i)."""
    return [(k, t) for t in TOHUMLAR for k in secilen]


def main(secilen: list):
    seans_basi = deney_basi = time.time()
    for kol, tohum in sira(secilen):
        if f"az-{kol}-t{tohum}" in yapilmis():
            continue
        if time.time() - deney_basi + KOSU_PAYI_SN > TOPLAM_SN:
            log.info("6 saat tavani: yeni kosu baslatilmiyor")
            return
        if (sebep := engel()):
            log.error("durdu: %s", sebep)
            return
        if time.time() - seans_basi > SEANS_SN:
            log.info("90 dk doldu, 15 dk soguma")
            time.sleep(SOGUMA_SN)
            seans_basi = time.time()
        log.info("basliyor az-%s-t%d", kol, tohum)
        satir = kos(kol, tohum)
        if satir is None:
            log.error("kosu basarisiz, yeniden baslatilmiyor")
            return
        with open(SONUCLAR, "a", encoding="utf-8") as f:
            f.write(json.dumps(satir, ensure_ascii=False) + "\n")
        log.info("bitti %s", json.dumps(satir["egitim"]))
    log.info("hepsi bitti")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        handlers=[logging.FileHandler(KOK / "loglar" / "az-deney-kosu.log",
                                                      encoding="utf-8"), logging.StreamHandler()])
    main(sys.argv[1:] or ["adamw"])  # ornek: python araclar/az_deney_kosu.py adamw arsifonem
