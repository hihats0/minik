"""k23-1: bir aday modeli GPU'da (Vulkan1) acar; Turkce sinavi, karakter testi, 10 turluk konusma
gecikmesi (onbellekli/onbelleksiz), zirve VRAM, sicaklik ve yukleme suresini olcup JSON yazar.
Cagiran: yonetici/olcum ekibi elle, `python deneyler/k23-olcum.py <etiket> <gguf> <baglam> [ek bayrak...]`."""

import json
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import k23_ortak as ortak  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # kok: ortak/, yuvalar/
from ortak.sunucu import LLAMA_SERVER, LOG_KLASORU, hazir_bekle  # noqa: E402

KOK = Path(__file__).resolve().parent.parent
SINAV_DOSYASI = KOK / "notes/turkce-testi.md"
HAM_KLASOR = KOK / "reports/k23-ham-cevaplar"
PORT = 8090
UC = f"http://127.0.0.1:{PORT}/v1/chat/completions"
ORNEKLEME = {"temperature": 0.7, "top_p": 0.9, "seed": 42, "max_tokens": 512}  # f0 ve kafa.py ile ayni
ZAMAN_ASIMI_SN = 300
GPU_SORGUSU = ["nvidia-smi", "--query-gpu=memory.used,temperature.gpu", "--format=csv,noheader,nounits"]
ORNEK_ARALIGI_SN = 1.0
DURAK_SICAKLIK = 80
DEVAM_SICAKLIK = 70
SOGUMA_BEKLEME_SN = 10


class GpuIzleyici(threading.Thread):
    """Arka planda saniyede bir VRAM ve sicaklik okur; zirveleri ve son sicakligi tutar."""

    def __init__(self):
        super().__init__(daemon=True)
        self.zirve_mib, self.zirve_c, self.son_c, self.dur = 0, 0, 0, False

    def run(self):
        while not self.dur:
            mib, derece = (int(x) for x in subprocess.check_output(GPU_SORGUSU, text=True).split(","))
            self.zirve_mib, self.zirve_c = max(self.zirve_mib, mib), max(self.zirve_c, derece)
            self.son_c = derece
            time.sleep(ORNEK_ARALIGI_SN)


def sogumayi_bekle(izleyici, kayit):
    """80 C ve ustundeyse 70 C'ye inene kadar bekler, bekleme saniyesini kayda ekler."""
    if izleyici.son_c < DURAK_SICAKLIK:
        return
    basla = time.time()
    while izleyici.son_c > DEVAM_SICAKLIK:
        time.sleep(SOGUMA_BEKLEME_SN)
    kayit["soguma_bekleme_sn"] = kayit.get("soguma_bekleme_sn", 0) + round(time.time() - basla)


def sor(mesajlar, onbellek=True):
    """Sohbet ucuna tek istek (akis yok). (cevap, timings, duvar_sn) dondurur; hata yukselir."""
    govde = {"messages": mesajlar, "cache_prompt": onbellek, **ORNEKLEME}
    istek = urllib.request.Request(UC, data=json.dumps(govde, ensure_ascii=False).encode("utf-8"),
                                   headers={"Content-Type": "application/json; charset=utf-8"})
    basla = time.perf_counter()
    with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI_SN) as yanit:
        veri = json.loads(yanit.read().decode("utf-8"))
    return veri["choices"][0]["message"]["content"], veri.get("timings", {}), time.perf_counter() - basla


def sunucu_ac(gguf, baglam, ek):
    """Sunucuyu GPU'da baslatir, hazir olana kadar gecen saniyeyi (yukleme suresi) dondurur."""
    LOG_KLASORU.mkdir(exist_ok=True)
    komut = [LLAMA_SERVER, "-m", gguf, "--device", "Vulkan1", "-ngl", "999", "-c", str(baglam),
             "--port", str(PORT), "--reasoning", "off", "--no-webui", *ek]
    log = open(LOG_KLASORU / f"k23-{PORT}.log", "w", encoding="utf-8")
    basla = time.perf_counter()
    proc = subprocess.Popen(komut, stdout=log, stderr=subprocess.STDOUT)
    hazir_bekle(proc, PORT)
    return proc, round(time.perf_counter() - basla, 1), komut


def tek_soru_listesi(sorular, izleyici, kayit, sistem=None):
    """Her soruyu bagimsiz (gecmissiz) sorar; [{no, soru, cevap, uretim_tps}] dondurur."""
    sonuc = []
    for no, soru in sorular:
        sogumayi_bekle(izleyici, kayit)
        mesajlar = ([{"role": "system", "content": sistem}] if sistem else []) + [{"role": "user", "content": soru}]
        cevap, t, duvar = sor(mesajlar)
        sonuc.append({"no": no, "soru": soru, "cevap": cevap, "uretim_tps": t.get("predicted_per_second"),
                      "uretilen_token": t.get("predicted_n"), "duvar_sn": round(duvar, 2)})
    return sonuc


def konusma(izleyici, kayit):
    """kafa.py bicimi: gecmis user/assistant olarak buyur. Once onbellekli tur tur konusur, sonra
    ayni mesaj gecmisini onbelleksiz tekrar gonderir (istem ayni, fark yalniz cache_prompt)."""
    gecmis, turlar = [], []
    for i, soru in enumerate(ortak.KONUSMA_TURLARI, 1):
        sogumayi_bekle(izleyici, kayit)
        mesajlar = gecmis + [{"role": "user", "content": soru}]
        cevap, t, duvar = sor(mesajlar, onbellek=True)
        turlar.append({"tur": i, "soru": soru, "cevap": cevap, "onbellekli": _sure(t, duvar),
                       "_mesajlar": mesajlar})
        gecmis = mesajlar + [{"role": "assistant", "content": cevap}]
    for tur in turlar:
        sogumayi_bekle(izleyici, kayit)
        _, t, duvar = sor(tur.pop("_mesajlar"), onbellek=False)
        tur["onbelleksiz"] = _sure(t, duvar)
    return turlar


def _sure(t, duvar):
    """timings alanindan konusma icin gereken sayilari secer."""
    return {"duvar_sn": round(duvar, 2), "istem_token": t.get("prompt_n"), "istem_ms": t.get("prompt_ms"),
            "istem_tps": t.get("prompt_per_second"), "uretilen_token": t.get("predicted_n"),
            "uretim_tps": t.get("predicted_per_second")}


def main(etiket, gguf, baglam, ek):
    izleyici = GpuIzleyici()
    izleyici.start()
    proc, yukleme_sn, komut = sunucu_ac(gguf, int(baglam), ek)
    kayit = {"etiket": etiket, "komut": " ".join(komut), "yukleme_sn": yukleme_sn}
    try:
        sinav = ortak.sorulari_oku(SINAV_DOSYASI.read_text(encoding="utf-8"))
        kayit["sinav"] = tek_soru_listesi(sinav, izleyici, kayit)
        karakter = list(enumerate(ortak.KARAKTER_SORULARI, 1))
        kayit["karakter"] = tek_soru_listesi(karakter, izleyici, kayit, sistem=ortak.KARAKTER_PROMPTU)
        kayit["konusma"] = konusma(izleyici, kayit)
    finally:
        proc.terminate()
        proc.wait(timeout=30)
        izleyici.dur = True
        kayit.update(zirve_vram_mib=izleyici.zirve_mib, zirve_sicaklik_c=izleyici.zirve_c)
        HAM_KLASOR.mkdir(parents=True, exist_ok=True)
        (HAM_KLASOR / f"{etiket}.json").write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{etiket}: yukleme {yukleme_sn} sn, zirve {izleyici.zirve_mib} MiB, {izleyici.zirve_c} C")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
