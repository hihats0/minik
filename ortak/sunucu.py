"""llama-server'i baslatir (baslat: SADECE CPU), hazir olmasini bekler, RAM ve GPU kullanimini olcer, durdurur.
Cagiran: agiz/web_sohbet_kafa.py (Gemma, GPU), deneyler/ (olcumler)."""

import os
import subprocess
import time
import urllib.request
from pathlib import Path


LLAMA_SERVER = str(Path(os.environ["LOCALAPPDATA"]) / "Microsoft/WinGet/Packages/"
                   "ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe/llama-server.exe")
LOG_KLASORU = Path(__file__).resolve().parent.parent / "loglar" / "sunucu"
HAZIR_BEKLEME_SN = 180
YOKLAMA_ARALIGI_SN = 0.5
GPU_BELLEK_SORGUSU = ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"]


def gpu_bellek_mib():
    """RTX 4070'in kullandigi VRAM (MiB). CPU-only kosuda ~0 kalmali."""
    cikti = subprocess.check_output(GPU_BELLEK_SORGUSU, text=True)
    return int(cikti.strip().splitlines()[0])


def baslat(model_yolu, port, ek_arguman=(), thread=None):
    """Sunucuyu `-dev none -ngl 0` ile baslatir (GPU'ya hic dokunmaz), Popen dondurur."""
    LOG_KLASORU.mkdir(parents=True, exist_ok=True)
    komut = [LLAMA_SERVER, "-m", str(model_yolu), "--port", str(port), "-dev", "none", "-ngl", "0",
             "--no-webui", *ek_arguman]
    if thread:
        komut += ["-t", str(thread)]
    log = open(LOG_KLASORU / f"sunucu-{port}.log", "w", encoding="utf-8")
    return subprocess.Popen(komut, stdout=log, stderr=subprocess.STDOUT)


def hazir_bekle(proc, port):
    """/health 200 verene kadar bekler. Sunucu cokerse ya da sure dolarsa hata firlatir (yutmaz)."""
    bitis = time.time() + HAZIR_BEKLEME_SN
    while time.time() < bitis:
        if proc.poll() is not None:
            raise RuntimeError(f"llama-server kapandi, cikis kodu {proc.returncode}; log: loglar/sunucu/")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as y:
                if y.status == 200:
                    return
        except OSError:
            pass  # sunucu henuz dinlemiyor; dongu tekrar dener, sure dolunca asagida hata verilir
        time.sleep(YOKLAMA_ARALIGI_SN)
    raise TimeoutError(f"llama-server {HAZIR_BEKLEME_SN} sn icinde hazir olmadi")


def ram_zirve_mb(proc):
    """Sunucu surecinin zirve calisan bellek boyutu (MB), Windows peak working set."""
    import psutil  # yalniz olcumlerde lazim; web sohbet bu paket olmadan da calissin
    return round(psutil.Process(proc.pid).memory_info().peak_wset / 2**20, 1)


def durdur(proc):
    """Sureci kibarca kapatir, 15 sn icinde kapanmazsa oldurur."""
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
