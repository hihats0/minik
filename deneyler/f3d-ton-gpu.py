"""f3d (K8/V7): ayni 78 ton cumlesini GPU'daki Qwen3.5-4B'ye (Vulkan1) sorar; sure, p95, zirve VRAM ve sicakligi olcer.
Cagiran: elle, `python deneyler/f3d-ton-gpu.py <model.gguf>`. Sunucuyu kendisi baslatir ve durdurur.
"""

import importlib.util
import subprocess
import sys
import threading
import time
from pathlib import Path

from f3d_ortak import p95, sicaklik_durumu
from odul_ortak import metrik_hesapla, sonuc_yaz, sure_ozeti, veri_yukle
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # kok: ortak/, yuvalar/
from ortak.sunucu import LLAMA_SERVER, LOG_KLASORU, durdur, hazir_bekle, ram_zirve_mb

PORT = 8125
OLCUM_ARALIGI_SN = 5
# Baglam acikca sinirli; tum katmanlar GPU'da, Vulkan1 = RTX 4070 (CLAUDE.md).
SUNUCU_ARGUMANLARI = ["--device", "Vulkan1", "-ngl", "999", "-c", "4096", "-np", "1", "--reasoning", "off", "--no-webui"]
GPU_SORGUSU = ["nvidia-smi", "--query-gpu=temperature.gpu,memory.used", "--format=csv,noheader,nounits"]


def llm_modulu():
    """odul-olc-llm.py (tireli ad, dogrudan import edilemez): ayni talimat ve ornekler oradan gelir."""
    yol = Path(__file__).parent / "odul-olc-llm.py"
    spec = importlib.util.spec_from_file_location("odul_olc_llm", yol)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def gpu_oku():
    sicaklik, bellek = subprocess.check_output(GPU_SORGUSU, text=True).strip().splitlines()[0].split(",")
    return int(sicaklik), int(bellek)


def izleyici(durum, devam, bitti):
    """Her 5 sn sicaklik ve VRAM okur, zirveyi tutar; 80 C'de `devam`i kapatir, 70 C'de acar."""
    while not bitti.is_set():
        sicaklik, bellek = gpu_oku()
        durum["zirve_c"] = max(durum["zirve_c"], sicaklik)
        durum["zirve_vram_mib"] = max(durum["zirve_vram_mib"], bellek)
        durakla = sicaklik_durumu(sicaklik, not devam.is_set())
        if durakla and devam.is_set():
            print(f"{sicaklik} C: duraklatildi", flush=True)
            durum["duraklama_sayisi"] += 1
        devam.clear() if durakla else devam.set()
        bitti.wait(OLCUM_ARALIGI_SN)


def baslat(model):
    LOG_KLASORU.mkdir(exist_ok=True)
    log = open(LOG_KLASORU / f"sunucu-{PORT}.log", "w", encoding="utf-8")
    komut = [LLAMA_SERVER, "-m", str(model), "--port", str(PORT), *SUNUCU_ARGUMANLARI]
    return subprocess.Popen(komut, stdout=log, stderr=subprocess.STDOUT)


def olc(llm, url, onek, testler, devam):
    tahminler, sureler = [], []
    for t in testler:
        devam.wait()
        tahmin, sure_ms, _ = llm.siniflandir(url, onek, t["metin"])
        tahminler.append(tahmin)
        sureler.append(sure_ms)
    return tahminler, sureler


def main():
    llm = llm_modulu()
    url = f"http://127.0.0.1:{PORT}/v1/chat/completions"
    testler, referans = veri_yukle()
    tablo = {r["id"]: r for r in referans}
    onek = llm.istem_olustur([tablo[i] for i in llm.ORNEK_KIMLIKLERI])
    durum = {"zirve_c": 0, "zirve_vram_mib": 0, "duraklama_sayisi": 0}
    devam, bitti = threading.Event(), threading.Event()
    devam.set()
    threading.Thread(target=izleyici, args=(durum, devam, bitti), daemon=True).start()
    proc = baslat(sys.argv[1])
    try:
        hazir_bekle(proc, PORT)
        _, soguk_ms, _ = llm.siniflandir(url, onek, "Bugun hava nasil?")
        for t in testler[:llm.ISITMA_CAGRISI]:
            llm.siniflandir(url, onek, t["metin"])
        tahminler, sureler = olc(llm, url, onek, testler, devam)
        ek = {"ram_zirve_mb": ram_zirve_mb(proc), "soguk_ilk_istek_ms": round(soguk_ms, 1),
              "p95_ms": round(p95(sureler), 1), **durum}
    finally:
        durdur(proc)
        bitti.set()
    sonuc_yaz("llm-qwen35-4b-gpu", metrik_hesapla(testler, tahminler), sure_ozeti(sureler), ek)
    print(ek)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
