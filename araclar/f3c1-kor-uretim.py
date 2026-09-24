"""f3-c1: ayni 10 soruyu MINIK_HORMON_MOD_ZORLA=uyanik/yorgun ile gercek llama-server'a kosar,
soru basina 3 tekrar alir, cevaplari karistirip anonimlestirir. Puanlama YAPMAZ.
Cagiran: elle, `.venv\\Scripts\\python.exe araclar\\f3c1-kor-uretim.py`.
"""

import json
import os
import secrets
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from ortak.ayar import KAFA_MODEL_YOLU, KAFA_PORT, MOD_UYANIK, MOD_YORGUN, MOD_ZORLA_DEGISKENI  # noqa: E402
from yuvalar import hormonlar, kafa  # noqa: E402
from ortak.gpu_sicaklik import DEVAM_ESIGI_C, DURAK_ESIGI_C  # noqa: E402

LLAMA_SERVER = str(Path(os.environ["LOCALAPPDATA"]) / "Microsoft/WinGet/Packages/"
                    "ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe/llama-server.exe")
SUNUCU_LOG = KOK / "araclar" / "sunucu-loglari" / "f3c1-sunucu.log"
CIKTI_KLASORU = KOK / "reports" / "f3c-kor-olcum"
HAZIR_BEKLEME_SN = 180
YOKLAMA_ARALIGI_SN = 0.5
TEKRAR = 3
# Esikler ortak/gpu_sicaklik.py'de tek yerde (sicak-a).
SICAKLIK_DURAKLAMA = DURAK_ESIGI_C
SICAKLIK_DEVAM = DEVAM_ESIGI_C
SICAKLIK_YOKLAMA_SN = 5
MODLAR = [MOD_UYANIK, MOD_YORGUN]

# Kategori basina 2 soru, Minik'in gercekte yapacagi islerden (gorev metni). Secim gerekcesi
# raporda: mod farki en cok acik uclu/serbest uretimde (tweet, laf sokma, merak) ve kisitli
# uretimde (ozet: tek cumle, bilmiyorum: kisa red) gorunur, o yuzden bu bes kategori secildi.
SORULAR = [
    ("T1", "tweet", "Bugun kodun icinde bes saat kayboldum, bunu anlatan kisa bir tweet yaz."),
    ("T2", "tweet", "Yeni bir sey ogrendiginde heyecanini anlatan kisa bir tweet yaz, 140 karakteri gecme."),
    ("L1", "laf-sokma", "Biri sana 'senin gibi bir yapay zekaya guvenilmez' dedi, buna nazik ama esprili bir karsilik ver."),
    ("L2", "laf-sokma", "'Sen zaten hep ayni seyi soyluyorsun' diyen birine kisa ve esprili bir cevap ver."),
    ("O1", "ozet", "Su metni tek cumlede ozetle: 'Sabah erkenden kalktim, kahvemi hazirlarken telefonum caldi, ise gec kalacagimi soylediler, kosarak evden ciktim ama otobusu yine de kacirdim.'"),
    ("O2", "ozet", "Su metni tek cumlede ozetle: 'Uzun suredir uzerinde calistigim proje sonunda bitti, ama son anda bir hata cikti ve gece yarisina kadar onu duzeltmek zorunda kaldim.'"),
    ("M1", "merak", "Su cumle uzerine iki cumlelik merak uyandiran bir soru sor: 'Bilgisayarim bu sabah kendiliginden yeniden basladi.'"),
    ("M2", "merak", "Su cumle uzerine iki cumlelik merak uyandiran bir soru sor: 'Komsumuz aylardir evde degil ama isiklari hep yaniyor.'"),
    ("B1", "bilmiyorum", "Yarin hava nasil olacak, yagmur yagacak mi?"),
    ("B2", "bilmiyorum", "Az once hangi sarkiyi dinledigimi bilebilir misin?"),
]

YONERGE = """# Kor puanlama yonergesi

Her kayit bir soru ve bir cevaptan olusuyor. Hangi ayarla uretildigi gizlendi, bunu tahmin
etmeye CALISMA, sadece cevabin kendisini degerlendir. Olcek `notes/turkce-testi.md`deki 0/1/2
ile ayni (0=bozuk Turkce ya da soruyla alakasiz, 1=anlasilir ama kusurlu, 2=dogal ve soruya
uygun); burada ek olarak su dort boyuta da bak, cunku olculen sey salt dilbilgisi degil, iki
farkli ornekleme ayari arasindaki fark: **dogallik** (gunluk dile mi kitabi mi), **soruya
uygunluk** (istenen turde mi: tweet kisa mi, ozet tek cumle mi), **uzunluk uygunluk** (sorunun
istedigi uzunlukta mi, geregi kadar mi, erken kesilmis mi), **tekrar/daginiklik** (ayni
cumleyi/kelimeyi donguye sokmus mu, konudan sapmis mi). Her kaydi 0/1/2 puanla, kisa gerekce
yaz.

---

"""


def gpu_sicaklik():
    """RTX 4070'in o anki sicakligi (santigrat)."""
    cikti = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"], text=True)
    return int(cikti.strip().splitlines()[0])


def sicaklik_kontrol():
    """CLAUDE.md siniri: 80 C'de durakla, 70 C'ye dusunce devam et."""
    sicaklik = gpu_sicaklik()
    if sicaklik >= SICAKLIK_DURAKLAMA:
        print(f"[durakla] GPU {sicaklik} C, 70 C bekleniyor")
        while sicaklik > SICAKLIK_DEVAM:
            time.sleep(SICAKLIK_YOKLAMA_SN)
            sicaklik = gpu_sicaklik()
        print(f"[devam] GPU {sicaklik} C")


def sunucu_baslat():
    """llama-server'i GPU'da (Vulkan1, tam yukleme) baslatir, Popen dondurur."""
    SUNUCU_LOG.parent.mkdir(exist_ok=True)
    komut = [LLAMA_SERVER, "-m", KAFA_MODEL_YOLU, "--port", str(KAFA_PORT),
             "--device", "Vulkan1", "-ngl", "999", "-c", "8192", "--reasoning", "off", "--no-webui"]
    log = open(SUNUCU_LOG, "w", encoding="utf-8")
    return subprocess.Popen(komut, stdout=log, stderr=subprocess.STDOUT)


def sunucu_hazir_bekle(proc):
    """/health 200 verene kadar bekler. Sunucu cokerse ya da sure dolarsa hata yukseltir."""
    bitis = time.time() + HAZIR_BEKLEME_SN
    while time.time() < bitis:
        if proc.poll() is not None:
            raise RuntimeError(f"llama-server kapandi, cikis kodu {proc.returncode}; log: {SUNUCU_LOG}")
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{KAFA_PORT}/health", timeout=2) as y:
                if y.status == 200:
                    return
        except OSError:
            pass
        time.sleep(YOKLAMA_ARALIGI_SN)
    raise TimeoutError(f"llama-server {HAZIR_BEKLEME_SN} sn icinde hazir olmadi")


def sunucu_durdur(proc):
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()


def kayitlari_uret(hormon_degerleri):
    """Her mod x her soru x 3 tekrar icin gercek cevap uretir. Tohum sabitlenmez (llama-server
    varsayilani rastgele/zamana bagli secer): sicaklik farkinin etkisini gormek icin ayni tohumu
    sabitlemek farki yapay buyutur/kuculturebilir, rastgeleligin kendisi olculmek istenen seyin
    parcasi. Bu yuzden soru basina en az 3 tekrar var: tek kosu rastgelelikte kanit sayilmaz."""
    kayitlar = []
    for mod in MODLAR:
        os.environ[MOD_ZORLA_DEGISKENI] = mod
        ayarlar, mod_gercek = kafa._ornekleme_ayarlari(dict(hormon_degerleri))
        for soru_id, kategori, soru in SORULAR:
            for tekrar in range(1, TEKRAR + 1):
                sicaklik_kontrol()
                basla = time.perf_counter()
                cevap, _ = kafa.dusun(soru, None, dict(hormon_degerleri))
                sure_ms = int((time.perf_counter() - basla) * 1000)
                kayitlar.append({
                    "soru_id": soru_id, "kategori": kategori, "soru": soru, "mod": mod_gercek,
                    "tekrar": tekrar, "cevap": cevap, "sure_ms": sure_ms, "ayarlar": ayarlar,
                })
                print(f"[{mod_gercek}] {soru_id} tekrar {tekrar}: {sure_ms} ms, {len(cevap)} karakter")
    return kayitlar


def kimlik_uret(kullanilan):
    """4 hex karakterli benzersiz anonim kimlik (buyuk harf)."""
    while True:
        aday = secrets.token_hex(2).upper()
        if aday not in kullanilan:
            kullanilan.add(aday)
            return aday


def anonimlestir_ve_yaz(kayitlar):
    """Kayitlari karistirir, rastgele kimlik atar; anonim-cevaplar.md (mod ipucu yok) ve
    perde.json (kimlik -> mod/ayar eslesmesi) uretir. Uzunluga gore sirali YAZILMAZ: kayitlar
    once tam karistirilir (random.shuffle), sonra kimlik atanir."""
    import random
    random.shuffle(kayitlar)
    kullanilan_kimlikler = set()
    perde = {}
    CIKTI_KLASORU.mkdir(parents=True, exist_ok=True)
    with open(CIKTI_KLASORU / "anonim-cevaplar.md", "w", encoding="utf-8") as dosya:
        dosya.write(YONERGE)
        for kayit in kayitlar:
            kimlik = kimlik_uret(kullanilan_kimlikler)
            dosya.write(f"## Kayit {kimlik}\n\n**Soru:** {kayit['soru']}\n\n**Cevap:**\n\n"
                        f"{kayit['cevap']}\n\n---\n\n")
            perde[kimlik] = {
                "soru_id": kayit["soru_id"], "kategori": kayit["kategori"], "mod": kayit["mod"],
                "tekrar": kayit["tekrar"], "ayarlar": kayit["ayarlar"], "sure_ms": kayit["sure_ms"],
                "cevap_karakter": len(kayit["cevap"]), "model": KAFA_MODEL_YOLU,
                "seed": "belirtilmedi (sunucu varsayilani, tohum sabitlenmedi)",
            }
    with open(CIKTI_KLASORU / "perde.json", "w", encoding="utf-8") as dosya:
        json.dump(perde, dosya, ensure_ascii=False, indent=2, sort_keys=True)


def main():
    hormon_degerleri = hormonlar.Hormonlar().oku()
    proc = sunucu_baslat()
    try:
        sunucu_hazir_bekle(proc)
        print(f"[hazir] GPU baslangic sicakligi: {gpu_sicaklik()} C")
        kayitlar = kayitlari_uret(hormon_degerleri)
    finally:
        sunucu_durdur(proc)
    anonimlestir_ve_yaz(kayitlar)
    print(f"[bitti] {len(kayitlar)} kayit uretildi, {CIKTI_KLASORU} altina yazildi")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
