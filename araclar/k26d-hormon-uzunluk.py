"""k26-d olcumu: Gemma'da hormonlu max_tokens (dusunce payi + cevap butcesi) ile 6 soru x 3 hormon durumu;
her cevapta finish_reason, think token, think sonrasi karakter, sure, sicaklik. Sunucuyu kendisi acar/kapatir.
Cagiran: elle (python araclar/k26d-hormon-uzunluk.py); tests/test_k26d_arac.py sahte sunucuyla."""

import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sunucu_yonet  # noqa: E402
from ortak.ayar import (GEMMA_SUNUCU_ARGUMANLARI, KAFA_DUSUNCE_PAYI_TOKEN, KAFA_HOST, KAFA_PORT,  # noqa: E402
                        MOD_UYANIK, MOD_YORGUN)
from ortak.gpu_sicaklik import SicaklikBekcisi  # noqa: E402
from yuvalar import kafa  # noqa: E402
from yuvalar.kafa_dusunce import KAPALI_BLOK, dusunce_ayikla  # noqa: E402

KOK = Path(__file__).resolve().parent.parent
JSONL = KOK / "loglar" / "k26d-hormon-uzunluk.jsonl"
SUNUCU_LOG = KOK / "loglar" / "k26d-sunucu.log"
# k26-b/k26-c ile ayni: tum katmanlar GPU'da, tek slot.
EK_ARGUMAN = ["-ngl", "99", "-np", "1", "--port", str(KAFA_PORT)]
# Tek istek 1024 tokende ~28 sn surdu (k26-c); 1280 token + sogutma payi.
ZAMAN_ASIMI_SN = 180
DUSUNCE_KAPANIS = "</think>"
SICAK_DURUM = "olculemedi: sicak"
SICAK_ATLANDI = "sicak_olculemedi"
SICAK_TEKRAR = "kesildi_tekrar_denenecek"
SURE_DOLDU = "olculemedi: 90 dk GPU siniri"
# Gorev (k26-d kalani): ayni istek 2 kez kesilirse atla, toplam 4 kesmede bitir, kesintisiz GPU en cok 90 dk.
AYNI_ISTEK_KESME_SINIRI = 2
TOPLAM_KESME_SINIRI = 4
GPU_SURE_SINIRI_SN = 90 * 60
DINLENME = {"dopamin": 20, "noradrenalin": 20, "serotonin": 50, "kortizol": 10,
            "oksitosin": 30, "melatonin": 10, "merak": 40}
# Uc durum: serotonin iki ucta (uyanik), yorgunda serotonin dinlenmede, melatonin ust esik ustunde.
DURUMLAR = {
    "serotonin_dusuk": ({**DINLENME, "serotonin": 0}, MOD_UYANIK),
    "serotonin_yuksek": ({**DINLENME, "serotonin": 100}, MOD_UYANIK),
    "yorgun": ({**DINLENME, "melatonin": 90}, MOD_YORGUN),
}
SORULAR = [
    "Yağmur neden yağar?", "Bir kediye nasıl bakılır, kısaca anlat.",
    "Uyku düzenimi nasıl düzeltebilirim?", "Kitap okumak neden faydalıdır?",
    "Fotosentez nedir, basitçe açıkla.", "Merhaba, bugün biraz yorgunum.",
]


def yaz(dosya, satir):
    """jsonl'e bir satir ekler ve ekrana basar; ikisi de hemen flush (PYTHONUNBUFFERED gerekmesin)."""
    metin = json.dumps(satir, ensure_ascii=False)
    with dosya.open("a", encoding="utf-8") as f:
        f.write(metin + "\n")
        f.flush()
    print(metin, flush=True)


def post(uc, govde):
    """JSON POST; HTTP ya da baglanti hatasi yukselir (cagiran kaydeder)."""
    istek = urllib.request.Request(uc, data=json.dumps(govde, ensure_ascii=False).encode("utf-8"),
                                   headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI_SN) as yanit:
        return json.loads(yanit.read().decode("utf-8"))


def govde_hazirla(soru, hormon, mod):
    """Kafa'nin gercek yolu: hormon -> ayarlar, karakter + (yorgunsa) talimat tek sistem mesaji."""
    kafa.ONCEKI_MOD = mod  # cift esik hafizasi durumlar arasinda tasinmasin
    ayarlar, mod_cikan = kafa._ornekleme_ayarlari(hormon)
    karakter, _ = kafa._karakter_oku()
    mesajlar = kafa._sistem_mesaji_ekle([{"role": "user", "content": soru}], karakter, mod_cikan)
    return kafa._govde_olustur(mesajlar, ayarlar), mod_cikan


def think_token(kok_url, ham):
    """Kapanmis think bloklarinin token sayisi, sunucunun kendi /tokenize ucuyla. Think yoksa 0."""
    metin = "".join(KAPALI_BLOK.findall(ham))
    if not metin:
        return 0
    return len(post(f"{kok_url}/tokenize", {"content": metin})["tokens"])


def tek_istek(kok_url, soru, durum):
    """Bir soru, bir hormon durumu: sonuc satiri (sicaklik alanlarini cagiran ekler)."""
    govde, mod = govde_hazirla(soru, *DURUMLAR[durum])
    basladi = time.perf_counter()
    j = post(f"{kok_url}/v1/chat/completions", govde)
    sure = round(time.perf_counter() - basladi, 1)
    secim = j["choices"][0]
    ham = secim["message"]["content"]
    return {"durum": durum, "mod": mod, "soru": soru, "max_tokens": govde["max_tokens"],
            "bitis": secim.get("finish_reason"), "uretim_token": j.get("usage", {}).get("completion_tokens"),
            "think_kapandi": DUSUNCE_KAPANIS in ham, "think_token": think_token(kok_url, ham),
            "cevap_karakter": len(dusunce_ayikla(ham)), "sure_sn": sure}


def olc(kok_url, soru, durum, bekci):
    """Serinle, tek istek at; baglanti hatasi (kesme dahil) satira yazilir."""
    bekledi = bekci.serinle()
    satir = {"sicaklik_once": bekci.son_c, "soguma_sn": bekledi}
    try:
        satir.update(tek_istek(kok_url, soru, durum))
    except OSError as hata:
        satir.update({"durum": durum, "soru": soru, "hata": str(hata)})
    satir["sicaklik_sonra"] = bekci.son_c
    return satir


def istegi_dene(kok_url, soru, durum, bekci, dosya, yeniden_baslat, sayac):
    """Bir istek; kesilirse 70 C'ye kadar bekler, sunucuyu yeniden acar, tekrar dener.
    Ust uste AYNI_ISTEK_KESME_SINIRI kesmede istegi atlar. False: toplam kesme siniri doldu."""
    for deneme in range(1, AYNI_ISTEK_KESME_SINIRI + 1):
        satir = olc(kok_url, soru, durum, bekci)
        if not bekci.kesildi:
            yaz(dosya, satir)
            return True
        sayac["kesme"] += 1
        satir["olcum"] = SICAK_ATLANDI if deneme == AYNI_ISTEK_KESME_SINIRI else SICAK_TEKRAR
        satir["kesme_sonrasi_bekleme_sn"] = bekci.kesme_sonrasi_bekle()
        yaz(dosya, satir)
        if sayac["kesme"] >= TOPLAM_KESME_SINIRI:
            return False
        yeniden_baslat()
    return True


def olcum_dongusu(kok_url, bekci, dosya, yeniden_baslat):
    """18 istek; toplam kesme sinirinda ya da GPU sure sinirinda kosuyu bitirir."""
    sayac = {"kesme": 0}
    basladi = time.monotonic()
    for durum in DURUMLAR:
        for soru in SORULAR:
            if time.monotonic() - basladi > GPU_SURE_SINIRI_SN:
                return SURE_DOLDU
            if not istegi_dene(kok_url, soru, durum, bekci, dosya, yeniden_baslat, sayac):
                return SICAK_DURUM
    return "tamam"


def gercek_sunucu_baslat():
    """Gemma'yi GPU'da (Vulkan1) acar; ortak/ayar.py'deki k26-b profili."""
    SUNUCU_LOG.parent.mkdir(exist_ok=True)
    log = SUNUCU_LOG.open("a", encoding="utf-8")
    return subprocess.Popen([sunucu_yonet.LLAMA_SERVER, *GEMMA_SUNUCU_ARGUMANLARI, *EK_ARGUMAN, "--no-webui"],
                            stdout=log, stderr=subprocess.STDOUT)


def kos(sunucu_baslat=gercek_sunucu_baslat, okuyucu=None, port=KAFA_PORT, dosya=JSONL, vram=None,
        aralik_sn=None):
    """Uctan uca: sunucu ac, hazir bekle, olc, kapat, VRAM logla. Parametreler testte sahteyle degisir."""
    vram = vram or sunucu_yonet.gpu_bellek_mib
    kok_url = f"http://{KAFA_HOST}:{port}"
    yaz(dosya, {"basla": datetime.now().isoformat(timespec="seconds"), "dusunce_payi": KAFA_DUSUNCE_PAYI_TOKEN})
    sunucu = {"proc": sunucu_baslat()}

    def yeniden_baslat():
        sunucu_yonet.durdur(sunucu["proc"])
        sunucu["proc"] = sunucu_baslat()
        sunucu_yonet.hazir_bekle(sunucu["proc"], port)

    ek = {k: v for k, v in (("okuyucu", okuyucu), ("aralik_sn", aralik_sn)) if v is not None}
    bekci = SicaklikBekcisi(kes=lambda: sunucu_yonet.durdur(sunucu["proc"]), **ek).baslat()
    try:
        sunucu_yonet.hazir_bekle(sunucu["proc"], port)
        sonuc = olcum_dongusu(kok_url, bekci, dosya, yeniden_baslat)
    finally:
        bekci.bitir()
        sunucu_yonet.durdur(sunucu["proc"])
    proc = sunucu["proc"]
    yaz(dosya, {"bitti": sonuc, "en_yuksek_c": bekci.en_yuksek_c, "vram_sonra_mib": vram(),
                "sunucu_kapali": proc.poll() is not None})
    return sonuc


if __name__ == "__main__":
    kos()
