"""Sabah demosunun 3. asamasi: web sohbeti alt surec olarak gecici defterle acar, bilgi verip 13. mesajda sorar,
yeniden baslatip bir kez daha sorar. Cagiran: araclar/sabah_demo.py."""

import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from agiz.web_sohbet import anahtar_oku
from sabah_demo_veri import DOLGULAR, UCTAN_ANAHTAR, UCTAN_BILGI, UCTAN_DOLGU_SAYISI, UCTAN_SORU, geciyor_mu

WEB_PORT = 8095
WEB_KOK = f"http://127.0.0.1:{WEB_PORT}"
HAZIR_BEKLEME_SN = 60
YOKLAMA_SN = 0.3
ISTEK_ZAMAN_ASIMI_SN = 200  # web_sohbet CEVAP_BEKLEME_SN 180 + pay
WEB_BETIGI = Path(__file__).resolve().parent / "sabah_demo_web.py"


def _istek(yol, anahtar, govde=None):
    veri = None if govde is None else json.dumps(govde, ensure_ascii=False).encode("utf-8")
    istek = urllib.request.Request(WEB_KOK + yol, data=veri, headers={
        "X-Anahtar": anahtar, "Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(istek, timeout=ISTEK_ZAMAN_ASIMI_SN) as yanit:
        return json.loads(yanit.read().decode("utf-8"))


def _ac(defter_klasoru, sahte, cihaz, log_yolu):
    """Alt sureci acar, /durum cevap verene kadar bekler; acilmazsa hata yukseltir."""
    env = {**os.environ, "MINIK_DEFTER_KLASORU": str(defter_klasoru)}
    komut = [sys.executable, str(WEB_BETIGI), "--port", str(WEB_PORT), "--device", cihaz] + (["--sahte"] if sahte else [])
    surec = subprocess.Popen(komut, env=env, stdout=log_yolu.open("a", encoding="utf-8"), stderr=subprocess.STDOUT)
    bitis = time.monotonic() + HAZIR_BEKLEME_SN
    while time.monotonic() < bitis:
        if surec.poll() is not None:
            raise RuntimeError(f"web sohbet alt sureci kapandi (kod {surec.returncode}), log: {log_yolu}")
        try:
            _istek("/durum", anahtar_oku())
            return surec
        except OSError:
            time.sleep(YOKLAMA_SN)  # henuz dinlemiyor, sure dolana kadar tekrar
    kapat(surec)
    raise TimeoutError(f"web sohbet {HAZIR_BEKLEME_SN} sn icinde acilmadi, log: {log_yolu}")


def kapat(surec):
    """Surec agacini (varsa Gemma llama-server cocugu dahil) kapatir: terminate Windows'ta finally'yi calistirmaz."""
    subprocess.run(["taskkill", "/PID", str(surec.pid), "/T", "/F"], capture_output=True)
    surec.wait(timeout=HAZIR_BEKLEME_SN)


def _sor(mesaj, ilerleme):
    basladi = time.perf_counter()
    cevap = _istek("/konus", anahtar_oku(), {"mesaj": mesaj}).get("cevap", "")
    ilerleme(f"3: {mesaj} ({time.perf_counter() - basladi:.1f} sn)")
    return cevap


def uctan_asamasi(kok, sahte, cihaz, ilerleme):
    """Iki oturum: bilgi + dolgu + soru; yeniden acilista ayni soru. Iki sonuc ve cevaplar doner."""
    defter_klasoru, log_yolu = kok / "s3-defter", kok / "s3-web.log"
    surec = _ac(defter_klasoru, sahte, cihaz, log_yolu)
    try:
        for mesaj in [UCTAN_BILGI] + DOLGULAR[:UCTAN_DOLGU_SAYISI]:
            _sor(mesaj, ilerleme)
        ilk = _sor(UCTAN_SORU, ilerleme)
    finally:
        kapat(surec)
    surec = _ac(defter_klasoru, sahte, cihaz, log_yolu)
    try:
        yeniden = _sor(UCTAN_SORU, ilerleme)
    finally:
        kapat(surec)
    return {"ilk": {"cevap": ilk, "hatirladi": geciyor_mu(UCTAN_ANAHTAR, ilk)},
            "yeniden_baslatma": {"cevap": yeniden, "hatirladi": geciyor_mu(UCTAN_ANAHTAR, yeniden)}}
