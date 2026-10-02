"""Turkce kucuk GGUF adaylarini yalniz CPU'da sohbet ya da duz kipte sinavdan gecirir, aday basina JSON yazar;
ayrica llama-bench hiz olcumu ve en uzun sorunun token sayimi. Cagiran: elle, `--help` ile kullanim."""

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

import psutil

BURASI = Path(__file__).resolve().parent
# Olcum dongusu (sunucu, RAM izleme, gunluk okuma, ayarlar) onceki CPU olcum betiginden gelir
_SPEC = importlib.util.spec_from_file_location("cpu_olcum", BURASI / "g007-lfm-cpu-olcum.py")
cpu = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cpu)
from ortak.sunucu import LLAMA_SERVER  # noqa: E402  (kok yolu cpu_olcum yuklenirken eklendi)

HAM_KLASOR = cpu.KOK / "reports/g008-ham-cevaplar"
SOHBET_UCU = cpu.UC
DUZ_UCU = f"http://127.0.0.1:{cpu.PORT}/completion"  # llama-server'in yerel ucu, sablon uygulamaz
DUZ_BICIM = "{soru}\n"
SOHBET, DUZ = "sohbet", "duz"
# etiket: (dosya, kip); kosu sirasi bu sira, en buyuk model en sonda
ADAYLAR = {
    "jamba2-3b-tr": ("Jamba2-3B-Turkish-SFT-v1.Q4_K_M.gguf", SOHBET),
    "kumru-2b": ("kumru-2b-Q4_K_M.gguf", SOHBET),
    "mamba-370m-tr": ("mamba-370m-hf-turkish-f16.gguf", DUZ),
    "ba2han-lfm-1.2b-tr": ("Ba2han-LFM2.5-1.2B-Turkish-Q4_K_M.gguf", DUZ),
    "ba2han-lfm-1.2b-tr-sohbet": ("Ba2han-LFM2.5-1.2B-Turkish-Q4_K_M.gguf", SOHBET),
    "lfm25-8b-a1b": ("LFM2.5-8B-A1B-Q4_K_M.gguf", SOHBET),
}
# MoE modelinde dosya + pay kurali yetmez; kapi sabit
SABIT_RAM_KAPISI_GB = {"lfm25-8b-a1b": 6.7}
EK_BENCH = {"ba2han-lfm-1.2b-tr": ("ba2han-lfm-1.2b-tr-f16", "Ba2han-LFM2.5-1.2B-Turkish-f16.gguf")}
TAVAN_BITISLERI = ("length", "limit")  # sohbet ucu finish_reason, duz uc stop_type
DUSUNCE_ACILIS = "<think>"
DUSUNCE_BLOGU = re.compile(r"<think>.*?(</think>|$)", re.DOTALL)
# Mamba ve Jamba durum bellegini KV yerine llama_memory_recurrent satirinda yazar
KV_DESENI = re.compile(r"llama_kv_cache|KV self size|kv_cache|llama_memory_recurrent")
LLAMA_BENCH = str(Path(LLAMA_SERVER).with_name("llama-bench.exe"))
LLAMA_TOKENIZE = str(Path(LLAMA_SERVER).with_name("llama-tokenize.exe"))
BENCH_THREAD, BENCH_PROMPT, BENCH_URETIM = 8, 512, 128
BENCH_ZAMAN_ASIMI_SN = 1800
DOSYA_YOK = "dosya yok"
RAM_YOK = "RAM yüzünden koşulmadı"


def istek_gonder(uc, govde):
    """JSON govdeyi POST eder, cozulmus yaniti dondurur; hata yukselir."""
    istek = urllib.request.Request(uc, data=json.dumps(govde, ensure_ascii=False).encode("utf-8"),
                                   headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(istek, timeout=cpu.ZAMAN_ASIMI_SN) as yanit:
        return json.loads(yanit.read().decode("utf-8"))


def sor_sohbet(soru, max_tokens):
    """Sistem promptsuz sohbet sorusu; (cevap, timings, bitis nedeni) dondurur."""
    veri = istek_gonder(SOHBET_UCU, {"messages": [{"role": "user", "content": soru}],
                                     "temperature": cpu.TEMPERATURE, "top_p": cpu.TOP_P,
                                     "seed": cpu.SEED, "max_tokens": max_tokens})
    secim = veri["choices"][0]
    mesaj = secim["message"]
    dusunce = mesaj.get("reasoning_content")
    cevap = f"<think>\n{dusunce}\n</think>\n{mesaj['content']}" if dusunce else mesaj["content"]
    return cevap, veri.get("timings", {}), secim.get("finish_reason")


def sor_duz(soru, max_tokens):
    """Sablonsuz duz metin tamamlama; (cevap, timings, bitis nedeni) dondurur."""
    veri = istek_gonder(DUZ_UCU, {"prompt": DUZ_BICIM.format(soru=soru), "temperature": cpu.TEMPERATURE,
                                  "top_p": cpu.TOP_P, "seed": cpu.SEED, "n_predict": max_tokens})
    return veri["content"], veri.get("timings", {}), veri.get("stop_type")


def dusunce_var_son_bos(cevap):
    """Cevapta dusunce blogu var ve blok disinda kalan metin bossa True."""
    if DUSUNCE_ACILIS not in cevap:
        return False
    return not DUSUNCE_BLOGU.sub("", cevap).strip()


def sinav_fonksiyonu(kip):
    """Kipe gore soran fonksiyonu kullanan, olcum dongusune verilecek sinav fonksiyonunu dondurur."""
    sor = sor_duz if kip == DUZ else sor_sohbet

    def sinav(sorular, max_tokens):
        sonuc = []
        for no, soru in sorular:
            cevap, t, bitis = sor(soru, max_tokens)
            timings = {alan: t.get(alan) for alan in cpu.TIMINGS_ALANLARI}
            tavan = (timings["predicted_n"] or 0) >= max_tokens or bitis in TAVAN_BITISLERI
            sonuc.append({"no": no, "soru": soru, "cevap": cevap, "timings": timings,
                          "tavana_carpti": tavan, "dusunce_var_son_bos": dusunce_var_son_bos(cevap)})
            print(f"  soru {no}: {t.get('predicted_per_second')} token/sn, bitis {bitis}")
        return sonuc
    return sinav


def ram_kapisi(etiket, dosya):
    """(bos RAM GB, gereken GB): gereken sabit kapi ya da dosya boyu + pay."""
    bos, gereken = cpu.ram_kontrolu(dosya)
    return bos, SABIT_RAM_KAPISI_GB.get(etiket, gereken)


def kaydi_yaz(kayit):
    """Kaydi etiketine gore JSON dosyasina yazar."""
    HAM_KLASOR.mkdir(parents=True, exist_ok=True)
    yol = HAM_KLASOR / f"{kayit['etiket']}.json"
    yol.write_text(json.dumps(kayit, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  yazildi: {yol}")


def adayi_isle(etiket, sorular, max_tokens):
    """Tek adayi dosya ve RAM kapisindan gecirip kipine gore kosar, JSON'unu yazar."""
    dosya_adi, kip = ADAYLAR[etiket]
    dosya = cpu.MODEL_KLASORU / dosya_adi
    bas = {"etiket": etiket, "dosya": str(dosya), "kip": kip, "max_tokens": max_tokens}
    if not dosya.exists():
        print(f"{etiket}: {DOSYA_YOK}")
        return kaydi_yaz({**bas, "durum": DOSYA_YOK})
    bos, gereken = ram_kapisi(etiket, dosya)
    print(f"{etiket} ({kip}): bos RAM {bos} GB, gereken {gereken} GB")
    bas["bos_ram_gb"] = bos
    if bos < gereken:
        print(f"  {RAM_YOK}")
        return kaydi_yaz({**bas, "durum": RAM_YOK, "gereken_gb": gereken})
    kayit = cpu.adayi_kos(dosya, sorular, max_tokens, sinav=sinav_fonksiyonu(kip))
    kaydi_yaz({**bas, **kayit, "kv_cache": cpu.gunluk_satirlari(KV_DESENI)})


def bench_kos(cikti_etiketi, dosya):
    """llama-bench'i yalniz CPU'da kosar, stdout+stderr'i (hatada hata metnini) dosyaya yazar."""
    komut = [LLAMA_BENCH, "-m", str(dosya), "-ngl", "0", "-dev", "none", "-t", str(BENCH_THREAD),
             "-p", str(BENCH_PROMPT), "-n", str(BENCH_URETIM)]
    try:
        sonuc = subprocess.run(komut, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               timeout=BENCH_ZAMAN_ASIMI_SN)
        metin = f"{' '.join(komut)}\ncikis kodu {sonuc.returncode}\n{sonuc.stdout}\n{sonuc.stderr}"
    except (OSError, subprocess.TimeoutExpired) as hata:
        metin = f"{' '.join(komut)}\nHATA: {hata}"  # hata gizlenmez, bench dosyasinda okunur
    HAM_KLASOR.mkdir(parents=True, exist_ok=True)
    yol = HAM_KLASOR / f"{cikti_etiketi}-bench.txt"
    yol.write_text(metin, encoding="utf-8")
    print(f"  bench yazildi: {yol}")


def bench_isle(etiket):
    """Adayin dosyasini (ve varsa ek dosyasini, ornegin f16) bench'ten gecirir."""
    isler = [(etiket, ADAYLAR[etiket][0])]
    if etiket in EK_BENCH:
        isler.append(EK_BENCH[etiket])
    for cikti_etiketi, dosya_adi in isler:
        print(f"{cikti_etiketi}: bench")
        bench_kos(cikti_etiketi, cpu.MODEL_KLASORU / dosya_adi)


def token_say(etiket, sorular, max_tokens):
    """Sinavdaki en uzun sorunun (karakter) token sayisini llama-tokenize ile stdout'a yazar."""
    no, soru = max(sorular, key=lambda s: len(s[1]))
    dosya = cpu.MODEL_KLASORU / ADAYLAR[etiket][0]
    # --stdin: Turkce karakterler komut satiri kodlamasina takilmasin
    sonuc = subprocess.run([LLAMA_TOKENIZE, "-m", str(dosya), "--stdin", "--ids", "--log-disable"],
                           input=soru.encode("utf-8"), capture_output=True, check=True)
    son_satir = sonuc.stdout.decode("utf-8", errors="replace").strip().splitlines()[-1]
    sayi = len(json.loads(son_satir))
    print(f"{etiket}: en uzun soru {no}, {sayi} token; + max_tokens {max_tokens} = {sayi + max_tokens}")


def argumanlar():
    """Komut satirini okur: aday etiketleri, soru sayisi, max_tokens ve is secimi."""
    ayr = argparse.ArgumentParser(description="Turkce kucuk adaylari CPU'da sinavdan gecirir.")
    ayr.add_argument("--aday", action="append", choices=list(ADAYLAR),
                     help="etiket (tekrarlanabilir); verilmezse tablodaki tum adaylar sirayla")
    ayr.add_argument("--soru-sayisi", type=int, default=None, help="ilk N soru (duman testi icin)")
    ayr.add_argument("--max-tokens", type=int, default=cpu.MAX_TOKENS, help="soru basina azami uretim")
    ayr.add_argument("--bench", action="store_true", help="sinav yerine llama-bench kos")
    ayr.add_argument("--token-say", action="store_true", help="sinav yerine en uzun sorunun token sayisi")
    return ayr.parse_args()


def main():
    arg = argumanlar()
    sorular = cpu.k23_ortak.sorulari_oku(cpu.SINAV_DOSYASI.read_text(encoding="utf-8"))[:arg.soru_sayisi]
    for etiket in arg.aday or list(ADAYLAR):
        if arg.bench:
            bench_isle(etiket)
        elif arg.token_say:
            token_say(etiket, sorular, arg.max_tokens)
        else:
            adayi_isle(etiket, sorular, arg.max_tokens)


if __name__ == "__main__":
    main()
