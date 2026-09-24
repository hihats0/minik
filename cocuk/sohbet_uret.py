"""Sohbet tohumu verisi (Turkce TinyChats): yerel Gemma ogretmen sade Turkce kisa sohbetler yazar; bicim
ve tekrar suzgecinden gecen sohbetler cocuk/veri/sohbet.jsonl'a eklenir (yarida kalirsa devam eder).
Cagiran: elle `python -m cocuk.sohbet_uret --sohbet 2000`; tohum model bu veriyle ince ayarlanir.
"""

import argparse
import itertools
import json
import logging
import random
import re
import subprocess
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from cocuk import egit_araclari as ea
from ortak.ayar import GEMMA_SUNUCU_ARGUMANLARI
from yuvalar.kafa_dusunce import dusunce_ayikla

LLAMA_SERVER = (Path.home() / "AppData/Local/Microsoft/WinGet/Packages/"
                "ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe/llama-server.exe")
PORT = 8095  # Kafa 8080, web sohbet 8090, gomme 8093 ile cakismaz
UC = f"http://127.0.0.1:{PORT}/v1/chat/completions"
YUVA = 1  # 25 Eyl 01:20: 2 yuva + 6144 baglam 8 GB'a sigmadi, sunucu istek ortasinda coktu
BAGLAM = 4096  # Kafa'da olculen calisan ayar (zirve 6382 MiB)
ISTEK_BASI_SOHBET = 3
EN_COK_TOKEN = 2048
SICAKLIK = 0.9  # cesitlilik; tekrar suzgeci ayiklar
ZAMAN_ASIMI_SN = 300
ARDISIK_HATA = 3
CIKTI = ea.VERI_DIZINI / "sohbet.jsonl"
KONUSMACI = re.compile(r"^\s*([AB])\s*:\s*(.+)$")
EN_AZ_REPLIK, EN_COK_REPLIK, EN_COK_KELIME = 4, 12, 20
KONULAR = ["okul", "kahvaltı", "yağmur", "kedi", "köpek", "futbol", "doğum günü", "market", "hastane",
           "otobüs", "tatil", "deniz", "kar", "oyun parkı", "ödev", "kitap", "resim", "müzik", "bahçe",
           "yemek pişirmek", "arkadaşlık", "kavga ve barışma", "korku", "sevinç", "uyku", "rüya",
           "bilgisayar", "telefon", "bayram", "misafir", "alışveriş", "kayıp eşya", "hayvanat bahçesi",
           "yıldızlar", "ağaçlar", "bisiklet", "özür dilemek", "teşekkür etmek", "yardım istemek", "merak"]
KISILER = ["iki çocuk", "anne ve çocuk", "baba ve çocuk", "öğretmen ve öğrenci", "iki arkadaş",
           "dede ve torun", "satıcı ve müşteri", "doktor ve çocuk", "iki komşu", "abla ve kardeş"]
ISTEM = ("Sade, günlük Türkçeyle {kisi} arasında geçen {n} ayrı kısa sohbet yaz. Konu: {konu}. "
         "Her sohbet {az}-{cok} replik, her replik en çok 15 kelime. Konuşanları yalnız 'A:' ve 'B:' ile "
         "göster. Sohbetleri '###' satırıyla ayır. Emoji, başlık, madde işareti, açıklama yazma.")

log = logging.getLogger("sohbet_uret")


def sohbetleri_ayikla(metin: str) -> list[list[str]]:
    """'###' ile bolunmus metinden gecerli sohbetleri cikarir: A/B sirali, replik sayisi ve uzunlugu uygun."""
    gecerli = []
    for parca in metin.split("###"):
        satirlar = [KONUSMACI.match(s) for s in parca.strip().splitlines() if s.strip()]
        if not satirlar or any(m is None for m in satirlar):
            continue
        replikler = [f"{m.group(1)}: {m.group(2).strip()}" for m in satirlar]
        sira_dogru = all(m.group(1) == "AB"[i % 2] for i, m in enumerate(satirlar))
        kisa = all(len(m.group(2).split()) <= EN_COK_KELIME for m in satirlar)
        if sira_dogru and kisa and EN_AZ_REPLIK <= len(replikler) <= EN_COK_REPLIK:
            gecerli.append(replikler)
    return gecerli


def istek(konu: str, kisi: str) -> str:
    govde = {"messages": [{"role": "user", "content": ISTEM.format(
        kisi=kisi, n=ISTEK_BASI_SOHBET, konu=konu, az=EN_AZ_REPLIK, cok=EN_COK_REPLIK - 2)}],
        "temperature": SICAKLIK, "max_tokens": EN_COK_TOKEN}
    rica = urllib.request.Request(UC, data=json.dumps(govde, ensure_ascii=False).encode("utf-8"),
                                  headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(rica, timeout=ZAMAN_ASIMI_SN) as yanit:
        return dusunce_ayikla(json.loads(yanit.read())["choices"][0]["message"]["content"])


def sunucu_ac():
    argumanlar = list(GEMMA_SUNUCU_ARGUMANLARI)
    argumanlar[argumanlar.index("-c") + 1] = str(BAGLAM)  # Kafa'nin 4096'si yerine iki yuvalik baglam
    komut = [str(LLAMA_SERVER), *argumanlar, "-np", str(YUVA), "-ngl", "999", "--port", str(PORT),
             "--no-webui"]
    proc = subprocess.Popen(komut, stdout=open(ea.AGIRLIK_DIZINI / "sohbet-sunucu.log", "w"),
                            stderr=subprocess.STDOUT)
    for _ in range(120):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=2)
            return proc
        except OSError:
            time.sleep(2)
    proc.kill()
    raise RuntimeError("sohbet sunucusu 240 sn'de acilmadi, log: sohbet-sunucu.log")


def gorulen_basliklar() -> set:
    if not CIKTI.exists():
        return set()
    return {json.loads(s)["replikler"][0] for s in CIKTI.read_text("utf-8").splitlines() if s.strip()}


def guvenli_istek(konu: str, kisi: str) -> str:
    """Tek istegin ag hatasi uretimi durdurmasin: loglanir, bos metin doner."""
    try:
        return istek(konu, kisi)
    except OSError as hata:
        log.error("istek basarisiz (%s / %s): %s", konu, kisi, hata)
        return ""


def uret(hedef: int, tohum: int):
    """Hedef sohbet sayisina kadar istek atar; her gecerli ve yeni sohbet hemen dosyaya yazilir.
    Sunucu olurse yeniden acilir; ust uste ARDISIK_HATA kez olurse durur."""
    gorulen, uretec = gorulen_basliklar(), random.Random(tohum)
    ciftler = list(itertools.product(KONULAR, KISILER))
    proc, baslangic, eklenen, hata_serisi = sunucu_ac(), time.time(), 0, 0
    try:
        with ThreadPoolExecutor(YUVA) as havuz, open(CIKTI, "a", encoding="utf-8") as f:
            while len(gorulen) < hedef and hata_serisi < ARDISIK_HATA:
                if proc.poll() is not None:
                    log.error("sunucu oldu (kod %s), yeniden aciliyor", proc.returncode)
                    hata_serisi += 1
                    proc = sunucu_ac()
                isler = [havuz.submit(guvenli_istek, *uretec.choice(ciftler)) for _ in range(YUVA)]
                for gorev in isler:
                    for replikler in sohbetleri_ayikla(gorev.result()):
                        if replikler[0] not in gorulen:
                            gorulen.add(replikler[0])
                            f.write(json.dumps({"replikler": replikler}, ensure_ascii=False) + "\n")
                            eklenen += 1
                f.flush()
                hata_serisi = 0 if proc.poll() is None else hata_serisi
                log.info("sohbet %d / %d, %.1f sohbet/dk", len(gorulen), hedef,
                         eklenen / max(1e-9, (time.time() - baslangic) / 60))
    finally:
        proc.kill()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sohbet", type=int, required=True)
    p.add_argument("--tohum", type=int, default=1)
    a = p.parse_args()
    uret(a.sohbet, a.tohum)
