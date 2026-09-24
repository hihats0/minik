"""emoji-a GPU olcumu: minik.calistir gercek Defter gecmisiyle 10 soru; Kafa'nin HAM cevabi (cikis temizliginden
once) emoji/markdown/uzun tire icin sayilir, boylece sebep duzeltmesi olculur, guvenlik agi degil.
Cagiran: elle, python araclar/emoji-a-olcum.py [2]. Gemma'yi 8080'de kendisi acar, bitince kapatir."""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "araclar"))
import k23_2b_sayim as sayim  # noqa: E402
import minik  # noqa: E402
import sunucu_yonet  # noqa: E402
from ortak.ayar import GEMMA_SUNUCU_ARGUMANLARI, KAFA_PORT  # noqa: E402
from ortak.gpu_sicaklik import SicaklikBekcisi  # noqa: E402
from yuvalar import kafa  # noqa: E402

SORULAR = ["Nasılsın?", "Bugün ne yaptın?", "En sevdiğin renk ne?", "Kedi mi köpek mi?", "Canın sıkılıyor mu?",
           "Bana bir şaka yap.", "Yarın hava nasıl olur sence?", "Kitap okur musun?", "Kimsin sen?",
           "Az önce sana ne içtiğimi söyledim?"]
# Kosu 2 (sonda kural hatirlatmasi): kosu 1'de emoji cikan uc soru + hatirlama, toplam 10 soru siniri.
KOSU2_SORULAR = ["Bugün ne yaptın?", "En sevdiğin renk ne?", "Kedi mi köpek mi?", "Az önce sana ne içtiğimi söyledim?"]
EK_ARGUMAN = ["-ngl", "99", "-np", "1", "--port", str(KAFA_PORT), "--no-webui"]
UZUN_TIRE = "—"
CIKTI = KOK / "reports" / "emoji-a-ham.jsonl"
SUNUCU_LOG = KOK / "araclar" / "sunucu-loglari" / "emoji-a-gemma.log"


def yaz(satir):
    """Olcum satirini jsonl'a ekler ve ekrana basar."""
    with CIKTI.open("a", encoding="utf-8") as f:
        f.write(json.dumps(satir, ensure_ascii=False) + "\n")
    print(json.dumps(satir, ensure_ascii=False)[:300], flush=True)


def minik_kos(bekci):
    """minik.calistir'i sahte agizla surer; her Kafa cagrisindan once serinler, ham cevabi sayar."""
    sorular = list(KOSU2_SORULAR if "2" in sys.argv else SORULAR) + [minik.CIKIS_KELIMESI]
    soylenen = []

    def dusun(soru, baglam, hormon):
        bekci.serinle()
        cevap, is_sn = kafa.dusun(soru, baglam, hormon)
        yaz({"soru": soru, "ham": cevap, "is_sn": round(is_sn, 1), "uzun_tire": cevap.count(UZUN_TIRE),
             "gecmis_mesaj": len(baglam), **sayim.say(cevap)})
        return cevap, is_sn

    minik.calistir(dinle=lambda: sorular.pop(0), soyle=lambda m, d: soylenen.append(m), dusun=dusun)
    yaz({"cikan": soylenen, "cikan_emoji": sum(sayim.say(m)["emoji"] for m in soylenen)})


def kos():
    """Sunucu ac, sicaklik izle, olc, kapat, VRAM yaz."""
    sys.stdout.reconfigure(encoding="utf-8")
    yaz({"basla": datetime.now().isoformat(timespec="seconds"), "vram_once_mib": sunucu_yonet.gpu_bellek_mib()})
    SUNUCU_LOG.parent.mkdir(exist_ok=True)
    proc = subprocess.Popen([sunucu_yonet.LLAMA_SERVER, *GEMMA_SUNUCU_ARGUMANLARI, *EK_ARGUMAN],
                            stdout=SUNUCU_LOG.open("a", encoding="utf-8"), stderr=subprocess.STDOUT)
    bekci = SicaklikBekcisi(kes=lambda: sunucu_yonet.durdur(proc)).baslat()
    basladi = time.monotonic()
    try:
        sunucu_yonet.hazir_bekle(proc, KAFA_PORT)
        yaz({"vram_yuklu_mib": sunucu_yonet.gpu_bellek_mib()})
        minik_kos(bekci)
    finally:
        bekci.bitir()
        sunucu_yonet.durdur(proc)
    time.sleep(3)  # suruc VRAM'i birkac saniyede birakir
    yaz({"bitti": datetime.now().isoformat(timespec="seconds"), "en_yuksek_c": bekci.en_yuksek_c,
         "vram_sonra_mib": sunucu_yonet.gpu_bellek_mib(), "sure_dk": round((time.monotonic() - basladi) / 60, 1)})


if __name__ == "__main__":
    kos()
