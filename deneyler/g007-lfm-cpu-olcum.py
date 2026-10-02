"""g007: GGUF adaylarini sirayla yalniz CPU'da acar, 20 soruluk Turkce sinavi sorar, model basina JSON yazar.
Cagiran: elle, `python deneyler/g007-lfm-cpu-olcum.py etiket=dosya.gguf [etiket=dosya.gguf ...] [--soru-sayisi N] [--max-tokens N]`."""

import argparse
import json
import re
import sys
import threading
import time
import urllib.request
from pathlib import Path

import psutil

sys.path.insert(0, str(Path(__file__).parent))
import k23_ortak  # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # kok: ortak/
from ortak.ayar import MODEL_KLASORU  # noqa: E402
from ortak.sunucu import LOG_KLASORU, baslat, durdur, hazir_bekle  # noqa: E402

KOK = Path(__file__).resolve().parent.parent
SINAV_DOSYASI = KOK / "deneyler/turkce-testi.md"
HAM_KLASOR = KOK / "reports/g007-ham-cevaplar"
PORT = 8095  # 8080/8081 Kafa, 8090 k23, 8093 web sohbet; cakismasin
UC = f"http://127.0.0.1:{PORT}/v1/chat/completions"
BAGLAM = 4096
# Varsayilan gunluk ayrintisi "offloaded 0/N" satirini basmiyor; GPU kaniti icin 4 gerekli
GUNLUK_AYRINTISI = 4
TEMPERATURE = 0.7
TOP_P = 0.9
SEED = 42
MAX_TOKENS = 512  # varsayilan; --max-tokens ile degisir
# k23 ile ayni: dusunce kapali, cevap butcesi dusunceye gitmesin
DUSUNCE_KAPALI = ["--reasoning", "off"]
ZAMAN_ASIMI_SN = 600  # CPU'da 512 token yavas uretilir
GB = 1024 ** 3
MB = 1024 ** 2
RAM_PAYI_GB = 1.5
RAM_ORNEK_ARALIGI_SN = 0.5
ONDALIK = 2
HATA_DESENI = re.compile(r"error|failed|unknown|unsupported|exception", re.IGNORECASE)
GPU_DESENI = re.compile(r"offload|GPU|CPU|Vulkan|CUDA|device", re.IGNORECASE)
HATA_YOKSA_SON_SATIR = 5  # gunlukte hata kelimesi yoksa en azindan sonu gorunsun
TIMINGS_ALANLARI = ("prompt_per_second", "predicted_per_second", "prompt_n", "predicted_n")


class RamIzleyici(threading.Thread):
    """llama-server surecinin working set'ini arka planda orneklenir, zirveyi (MB) tutar."""

    def __init__(self, pid):
        super().__init__(daemon=True)
        self.surec, self.zirve_mb, self.dur = psutil.Process(pid), 0.0, False

    def run(self):
        while not self.dur:
            try:
                # Windows'ta rss, working set'tir
                self.zirve_mb = max(self.zirve_mb, self.surec.memory_info().rss / MB)
            except psutil.NoSuchProcess:
                return  # surec kapandi; zirve o ana kadar olculeni gosterir
            time.sleep(RAM_ORNEK_ARALIGI_SN)


def gunluk_satirlari(desen):
    """Sunucu gunlugunden desene uyan satirlari dondurur."""
    yol = LOG_KLASORU / f"sunucu-{PORT}.log"
    satirlar = yol.read_text(encoding="utf-8", errors="replace").splitlines()
    return [s.strip() for s in satirlar if desen.search(s)]


def hata_satirlari():
    """Acilmayan adayin gunlukteki hata satirlari; hic yoksa gunlugun son satirlari."""
    satirlar = gunluk_satirlari(HATA_DESENI)
    if satirlar:
        return satirlar
    tum = (LOG_KLASORU / f"sunucu-{PORT}.log").read_text(encoding="utf-8", errors="replace").splitlines()
    return tum[-HATA_YOKSA_SON_SATIR:]


def sor(soru, max_tokens):
    """Sistem promptsuz tek soru sorar, (cevap, timings) dondurur; hata yukselir."""
    govde = {"messages": [{"role": "user", "content": soru}], "temperature": TEMPERATURE,
             "top_p": TOP_P, "seed": SEED, "max_tokens": max_tokens}
    istek = urllib.request.Request(UC, data=json.dumps(govde, ensure_ascii=False).encode("utf-8"),
                                   headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI_SN) as yanit:
        veri = json.loads(yanit.read().decode("utf-8"))
    mesaj = veri["choices"][0]["message"]
    # Dusunen modelde k23 JSON'lari gibi dusunce <think> icinde cevaba eklenir
    dusunce = mesaj.get("reasoning_content")
    cevap = f"<think>\n{dusunce}\n</think>\n{mesaj['content']}" if dusunce else mesaj["content"]
    return cevap, veri.get("timings", {})


def sinavi_sor(sorular, max_tokens):
    """Her soruyu bagimsiz sorar; [{no, soru, cevap, timings}] dondurur."""
    sonuc = []
    for no, soru in sorular:
        cevap, t = sor(soru, max_tokens)
        sonuc.append({"no": no, "soru": soru, "cevap": cevap,
                      "timings": {alan: t.get(alan) for alan in TIMINGS_ALANLARI}})
        print(f"  soru {no}: {t.get('predicted_per_second')} token/sn")
    return sonuc


def ram_kontrolu(dosya):
    """Bos RAM ile gereken RAM'i (GB) dondurur; gereken = dosya boyu + pay."""
    bos = psutil.virtual_memory().available / GB
    gereken = dosya.stat().st_size / GB + RAM_PAYI_GB
    return round(bos, ONDALIK), round(gereken, ONDALIK)


def adayi_kos(dosya, sorular, max_tokens):
    """Sunucuyu CPU'da acar, sinavi sorar, sunucuyu her durumda kapatir; kayit dondurur."""
    basla = time.perf_counter()
    proc = baslat(dosya, PORT, ek_arguman=["-c", str(BAGLAM), "-lv", str(GUNLUK_AYRINTISI),
                                          *DUSUNCE_KAPALI])
    kayit = {"komut": " ".join(proc.args)}
    try:
        try:
            hazir_bekle(proc, PORT)
        except (RuntimeError, TimeoutError) as hata:
            print(f"  acilmadi: {hata}")
            return {**kayit, "durum": "acilmadi", "istisna": str(hata), "hata": hata_satirlari()}
        kayit["yukleme_sn"] = round(time.perf_counter() - basla, 1)
        izleyici = RamIzleyici(proc.pid)
        izleyici.start()
        try:
            kayit["sinav"] = sinavi_sor(sorular, max_tokens)
        finally:
            izleyici.dur = True
            kayit["zirve_ram_mb"] = round(izleyici.zirve_mb, 1)
        kayit["durum"] = "kosuldu"
    finally:
        durdur(proc)
        kayit["gpu_kaniti"] = gunluk_satirlari(GPU_DESENI)
    return kayit


def adayi_isle(etiket, dosya_adi, sorular, max_tokens):
    """Tek adayi RAM kontrolunden gecirip kosar ve JSON'unu yazar."""
    dosya = MODEL_KLASORU / dosya_adi
    bos, gereken = ram_kontrolu(dosya)
    print(f"{etiket}: bos RAM {bos} GB, gereken {gereken} GB")
    if bos < gereken:
        kayit = {"durum": "RAM yüzünden koşulmadı", "bos_gb": bos, "gereken_gb": gereken}
        print(f"  {kayit['durum']}")
    else:
        kayit = adayi_kos(dosya, sorular, max_tokens)
    kayit = {"etiket": etiket, "dosya": str(dosya), "max_tokens": max_tokens, **kayit}
    HAM_KLASOR.mkdir(parents=True, exist_ok=True)
    (HAM_KLASOR / f"{etiket}.json").write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  yazildi: {HAM_KLASOR / (etiket + '.json')}")


def argumanlar():
    """Komut satirini okur: etiket=dosya_adi listesi ve istege bagli soru sayisi."""
    ayr = argparse.ArgumentParser(description="GGUF adaylarini CPU'da Turkce sinavdan gecirir.")
    ayr.add_argument("adaylar", nargs="+", help="etiket=dosya_adi (dosya MODEL_KLASORU icinde)")
    ayr.add_argument("--soru-sayisi", type=int, default=None, help="ilk N soru (duman testi icin)")
    ayr.add_argument("--max-tokens", type=int, default=MAX_TOKENS, help="soru basina azami uretim")
    return ayr.parse_args()


def main():
    arg = argumanlar()
    sorular = k23_ortak.sorulari_oku(SINAV_DOSYASI.read_text(encoding="utf-8"))[:arg.soru_sayisi]
    for aday in arg.adaylar:
        etiket, dosya_adi = aday.split("=", 1)
        adayi_isle(etiket, dosya_adi, sorular, arg.max_tokens)


if __name__ == "__main__":
    main()
