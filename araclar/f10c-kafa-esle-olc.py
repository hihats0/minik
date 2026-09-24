"""f10-c GPU olcumu: 5 gercek sorgu uctan uca (web.ara -> kisa iddia -> Kafa ile esle -> Bekci -> gecici Defter).
Ayni kayitlar basit eslemeyle de gruplanir (karsilastirma). Gercek Defter'e dokunmaz. Cagiran: elle, python araclar/f10c-kafa-esle-olc.py."""

import json
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sunucu_yonet  # noqa: E402
from agiz import web  # noqa: E402
from ortak.ayar import GEMMA_MAX_TOKEN, GEMMA_SUNUCU_ARGUMANLARI, KAFA_PORT, KAFA_UC, KAFA_ZAMAN_ASIMI_SN  # noqa: E402
from ortak.gpu_sicaklik import SicaklikBekcisi  # noqa: E402
from yuvalar import bekci_giris, defter, iddia_esle, merak  # noqa: E402
from yuvalar.kafa_dusunce import dusunce_ayikla  # noqa: E402

SORGULAR = ["photosynthesis", "speed of light", "mount everest height", "fotosentez nedir", "python programming language"]
TARIH = "2026-09-24"
KAYNAK_BASI_SONUC = 5  # 5 kaynak x 5 sonuc: esleme cift sayisi Kafa'ya 90 dk'da sigsin
SORGU_BASI_KAFA_SINIRI = 80  # asilirsa kalan ciftler "hayir" sayilir ve sayilip rapora yazilir
GPU_SURE_SINIRI_SN = 85 * 60  # proje kurali: kesintisiz en fazla 90 dk
EK_ARGUMAN = ["-ngl", "99", "-np", "1", "--port", str(KAFA_PORT), "--no-webui"]
SICAKLIK_0 = 0.0  # esleme karari tekrarlanabilir olsun
JSONL = Path(__file__).resolve().parent.parent / "reports" / "f10c-ham" / "olcum.jsonl"
SUNUCU_LOG = Path(__file__).resolve().parent / "sunucu-loglari" / "f10c-gemma.log"


def yaz(satir):
    """Olcum satirini jsonl'a ekler ve ekrana basar."""
    JSONL.parent.mkdir(parents=True, exist_ok=True)
    with JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(satir, ensure_ascii=False) + "\n")
    print(json.dumps(satir, ensure_ascii=False)[:300], flush=True)


def kafaya_sor(bekci, metin):
    """Kafa'ya karakter ve hormon olmadan duz soru sorar (serinledikten sonra), think ayiklanmis cevabi dondurur."""
    bekci.serinle()
    govde = {"messages": [{"role": "user", "content": metin}], "temperature": SICAKLIK_0,
             "max_tokens": GEMMA_MAX_TOKEN}
    istek = urllib.request.Request(KAFA_UC, json.dumps(govde).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(istek, timeout=KAFA_ZAMAN_ASIMI_SN * 3) as y:
        ham = json.loads(y.read())["choices"][0]["message"]["content"]
    return dusunce_ayikla(ham)


def esleyici(bekci, kurumlar, sayac):
    """kafa_ayni_mi sarmali: ayni kurumun ya da ortak anlamli kelimesi olmayan iki metin Kafa'ya gitmez (hayir);
    sorgu basina SORGU_BASI_KAFA_SINIRI asilirsa hayir. Her Kafa cagrisi sayilir."""
    kafa = iddia_esle.kafa_ayni_mi(lambda m: kafaya_sor(bekci, m))

    def ayni_mi(a, b):
        if kurumlar.get(a) == kurumlar.get(b) or not iddia_esle.kelimeler(a) & iddia_esle.kelimeler(b):
            sayac["suzgec"] += 1
            return False
        if sayac["kafa"] >= SORGU_BASI_KAFA_SINIRI:
            sayac["sinir"] += 1
            return False
        sayac["kafa"] += 1
        basladi = time.perf_counter()
        karar = kafa(a, b)
        sayac["kafa_sn"] += time.perf_counter() - basladi
        sayac["evet"] += karar
        return karar
    return ayni_mi


def sorgu_olc(sorgu, bekci, defter_yaz):
    """Tek sorgu: ara, basit ve Kafa eslemesiyle grupla, Kafa gruplarini Bekci'den gecirip gecici Defter'e yazar."""
    kayitlar = web.ara(sorgu, KAYNAK_BASI_SONUC)
    kurumlar = {k["soru"]: iddia_esle.kurum(k["kaynak"]) for k in kayitlar}
    basit = iddia_esle.grupla(kayitlar)
    sayac = {"kafa": 0, "evet": 0, "suzgec": 0, "sinir": 0, "kafa_sn": 0.0}
    baglanti = sqlite3.connect(":memory:")
    bekci_giris.kur(baglanti)
    kafa_gruplari = iddia_esle.grupla(kayitlar, esleyici(bekci, kurumlar, sayac))
    kabul = merak.ogren(baglanti, sorgu, TARIH, ara=lambda _s: kayitlar,
                        ayni_mi=_hazir_grup_esleyici(kafa_gruplari), yaz=defter_yaz)
    return {"sorgu": sorgu, "kayit": len(kayitlar), "alan": len({k["kaynak"] for k in kayitlar}),
            "kurum": len(set(kurumlar.values())), "basit_grup": len(basit),
            "basit_en_cok_agiz": max((len(g["agizlar"]) for g in basit), default=0),
            "kafa_grup": len(kafa_gruplari), "kafa_en_cok_agiz": max((len(g["agizlar"]) for g in kafa_gruplari), default=0),
            "kabul": len(kabul), "kabul_iddia": [(g["agizlar"], g["iddia"][:150]) for g in kabul],
            **{k: round(v, 1) for k, v in sayac.items()}, "en_yuksek_c": bekci.en_yuksek_c}


def _hazir_grup_esleyici(gruplar):
    """merak.ogren'e Kafa'yi ikinci kez cagirmadan ayni gruplamayi verir: iki metin ayni Kafa grubundaysa ayni."""
    grup_no = {k["soru"]: i for i, g in enumerate(gruplar) for k in g["kayitlar"]}
    return lambda a, b: grup_no.get(a) == grup_no.get(b)


def sunucu_baslat():
    """Gemma'yi tamamen GPU'da (Vulkan1, -ngl 99) acar; ortak/ayar.py profili, baglam 4096, q8 KV."""
    SUNUCU_LOG.parent.mkdir(exist_ok=True)
    return subprocess.Popen([sunucu_yonet.LLAMA_SERVER, *GEMMA_SUNUCU_ARGUMANLARI, *EK_ARGUMAN],
                            stdout=SUNUCU_LOG.open("a", encoding="utf-8"), stderr=subprocess.STDOUT)


def sorgulari_kos(sunucu, bekci, basladi, defter_yaz):
    """Sorgulari sirayla olcer. Sicak kesmede (gpu_sicaklik 84 C) 70 C'ye kadar bekler, sunucuyu yeniden acar,
    ayni sorguyu bir kez daha dener; ikinci kesmede ya da sure dolunca durur."""
    for sorgu in SORGULAR:
        for deneme in range(2):
            if time.monotonic() - basladi > GPU_SURE_SINIRI_SN:
                return yaz({"durdu": "90 dk siniri", "sorgu": sorgu})
            try:
                yaz(sorgu_olc(sorgu, bekci, defter_yaz))
                break
            except OSError as hata:
                if not bekci.kesildi or deneme == 1:
                    raise
                yaz({"sicak_kesme": sorgu, "hata": str(hata), "bekleme_sn": bekci.kesme_sonrasi_bekle()})
                sunucu["proc"] = sunucu_baslat()
                sunucu_yonet.hazir_bekle(sunucu["proc"], KAFA_PORT)


def kos():
    """Sunucu ac, sicaklik izle, 5 sorguyu olc, kapat, VRAM yaz. Gecici Defter klasoru is bitince silinir."""
    yaz({"basla": datetime.now().isoformat(timespec="seconds")})
    sunucu = {"proc": sunucu_baslat()}
    bekci = SicaklikBekcisi(kes=lambda: sunucu_yonet.durdur(sunucu["proc"])).baslat()
    basladi = time.monotonic()
    try:
        sunucu_yonet.hazir_bekle(sunucu["proc"], KAFA_PORT)
        yaz({"vram_yuklu_mib": sunucu_yonet.gpu_bellek_mib()})
        with tempfile.TemporaryDirectory() as gecici:
            defter.DEFTER_KLASORU = Path(gecici)  # gercek Defter'e yazilmaz
            sorgulari_kos(sunucu, bekci, basladi, defter.yaz)
            yaz({"gecici_defter_satir": sum(len(d.read_text(encoding="utf-8").splitlines())
                                            for d in Path(gecici).glob("*.jsonl"))})
    finally:
        bekci.bitir()
        sunucu_yonet.durdur(sunucu["proc"])
    yaz({"bitti": datetime.now().isoformat(timespec="seconds"), "en_yuksek_c": bekci.en_yuksek_c,
         "vram_sonra_mib": sunucu_yonet.gpu_bellek_mib(), "sure_dk": round((time.monotonic() - basladi) / 60, 1)})


if __name__ == "__main__":
    kos()
