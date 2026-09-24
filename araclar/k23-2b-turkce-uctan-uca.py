"""k23-2b GPU olcumu: (1) karakter dosyasi + Gemma Kafa ile 10 kisa soru, Turkce/asistan/emoji/markdown sayimi;
(2) spec 7.5 sart 2: `python minik.py` iki kez (soru, sonra yeniden acilista hatirlama), loga dusen satir sayisi.
Cagiran: elle, python araclar/k23-2b-turkce-uctan-uca.py. Gemma'yi 8080'de kendisi acar, bitince kapatir."""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "araclar"))
import k23_2b_sayim as sayim  # noqa: E402
import sunucu_yonet  # noqa: E402
from ortak.ayar import GEMMA_SUNUCU_ARGUMANLARI, KAFA_PORT  # noqa: E402
from ortak.gpu_sicaklik import SicaklikBekcisi  # noqa: E402
from ortak.log import LOG_KLASORU  # noqa: E402
from yuvalar import kafa  # noqa: E402

SORULAR = ["Nasılsın?", "Bugün ne yaptın?", "En sevdiğin renk ne?", "Kedi mi köpek mi?", "Canın sıkılıyor mu?",
           "Bana bir şaka yap.", "Yarın hava nasıl olur sence?", "Kitap okur musun?", "Kimsin sen?", "İyi geceler."]
UCTAN_UCA_GIRDILER = ["Merhaba Minik, ben Yiğit. Bugün çay içtim.\ncik\n", "Az önce sana ne içtiğimi söyledim?\ncik\n"]
EK_ARGUMAN = ["-ngl", "99", "-np", "1", "--port", str(KAFA_PORT), "--no-webui"]
MINIK_ZAMAN_ASIMI_SN = 300
CIKTI = KOK / "reports" / "k23-2b-ham.jsonl"
SUNUCU_LOG = KOK / "araclar" / "sunucu-loglari" / "k23-2b-gemma.log"


def yaz(satir):
    """Olcum satirini jsonl'a ekler ve ekrana basar."""
    with CIKTI.open("a", encoding="utf-8") as f:
        f.write(json.dumps(satir, ensure_ascii=False) + "\n")
    print(json.dumps(satir, ensure_ascii=False)[:300], flush=True)


def turkce_kontrol(bekci):
    """10 soruyu kafa.dusun ile (karakter dosyasi otomatik girer) sorar, her cevabi sayar."""
    for soru in SORULAR:
        bekci.serinle()
        cevap, is_sn = kafa.dusun(soru)
        yaz({"soru": soru, "cevap": cevap, "is_sn": round(is_sn, 1), **sayim.say(cevap)})


def minik_kos(bekci, girdi):
    """python minik.py'yi girdiyle calistirir; ciktiyi ve bugunku loga eklenen satir sayisini yazar."""
    bekci.serinle()
    log_dosya = LOG_KLASORU / f"{datetime.now():%Y-%m-%d}.log"
    once = log_dosya.stat().st_size if log_dosya.exists() else 0
    sonuc = subprocess.run([sys.executable, "minik.py"], input=girdi, capture_output=True, text=True,
                           encoding="utf-8", cwd=KOK, timeout=MINIK_ZAMAN_ASIMI_SN,
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    with log_dosya.open("rb") as f:
        f.seek(once)
        yeni = f.read().decode("utf-8").splitlines()
    yaz({"girdi": girdi, "cikis_kodu": sonuc.returncode, "stdout": sonuc.stdout, "stderr": sonuc.stderr[-500:],
         "log_satir": len(yeni), "log_yuvalar": sorted({json.loads(s).get("yuva", "?") for s in yeni if s.startswith("{")})})


def kos():
    """Sunucu ac, sicaklik izle, iki olcumu yap, kapat, VRAM yaz."""
    sys.stdout.reconfigure(encoding="utf-8")  # cevaplarda emoji olabilir, Windows konsolu cp1254
    yaz({"basla": datetime.now().isoformat(timespec="seconds"), "vram_once_mib": sunucu_yonet.gpu_bellek_mib()})
    SUNUCU_LOG.parent.mkdir(exist_ok=True)
    proc = subprocess.Popen([sunucu_yonet.LLAMA_SERVER, *GEMMA_SUNUCU_ARGUMANLARI, *EK_ARGUMAN],
                            stdout=SUNUCU_LOG.open("a", encoding="utf-8"), stderr=subprocess.STDOUT)
    bekci = SicaklikBekcisi(kes=lambda: sunucu_yonet.durdur(proc)).baslat()
    basladi = time.monotonic()
    try:
        sunucu_yonet.hazir_bekle(proc, KAFA_PORT)
        yaz({"vram_yuklu_mib": sunucu_yonet.gpu_bellek_mib()})
        turkce_kontrol(bekci)
        for girdi in UCTAN_UCA_GIRDILER:
            minik_kos(bekci, girdi)
    finally:
        bekci.bitir()
        sunucu_yonet.durdur(proc)
    time.sleep(3)  # suruc VRAM'i birkac saniyede birakir
    yaz({"bitti": datetime.now().isoformat(timespec="seconds"), "en_yuksek_c": bekci.en_yuksek_c,
         "vram_sonra_mib": sunucu_yonet.gpu_bellek_mib(), "sure_dk": round((time.monotonic() - basladi) / 60, 1)})


if __name__ == "__main__":
    kos()
