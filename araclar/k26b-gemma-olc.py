"""k26-b olcumu: GPU'da koşan Gemma llama-server'ina Kafa'nin govde bicimiyle sorar; think ayiklamayi,
10 turluk konusmayi, sureyi ve tok/sn'yi olcer, her istekten once sicaklik CSV'sine bakar.
Cagiran: elle (python araclar/k26b-gemma-olc.py), sunucu ve nvidia-smi izleyicisi ayrica baslatilir."""

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ortak.ayar import KAFA_MAX_TOKEN, KAFA_SICAKLIK, KAFA_TOP_P, KAFA_UC  # noqa: E402
from yuvalar.kafa_dusunce import dusunce_ayikla  # noqa: E402

KOK = Path(__file__).resolve().parent.parent
GPU_CSV = KOK / "loglar" / "k26b-gpu.csv"
SICAK_DURDU = KOK / "loglar" / "GPU-SICAK-DURDU"
CIKTI = KOK / "loglar" / "k26b-sonuc.json"
DURAKLA_C = 80
DEVAM_C = 70
SOGUMA_BEKLE_SN = 15
ZAMAN_ASIMI_SN = 180
DUSUNCE_ACILIS = "<think>"

TEK_SORULAR = [
    "Türkiye'nin başkenti neresidir ve neden orası seçilmiştir?",
    "Bir kediye nasıl bakılır, kısaca anlat.",
    "Yağmur neden yağar?",
    "Sabah erken kalkmak için üç öneri ver.",
    "Bilgisayar ile hesap makinesi arasındaki fark nedir?",
]
KONUSMA = [
    "Merhaba, bugün biraz yorgunum.", "Neden yorgun olabilirim sence?", "Uyku düzenim bozuk aslında.",
    "Gece geç yatıyorum, telefona bakıyorum.", "Bunu nasıl bırakabilirim?", "Kitap okumak işe yarar mı?",
    "Hangi tür kitap önerirsin?", "Peki sabah kahvaltısı önemli mi?", "Konuştuklarımızı özetler misin?",
    "Teşekkürler, iyi geceler.",
]


def sicaklik_bekle():
    """CSV'nin son satirindaki sicakligi okur; 80'de 70'in altina inene kadar bekler.
    Bekci durdurma dosyasi varsa istisna atar. Donus: okunan sicaklik."""
    while True:
        if SICAK_DURDU.exists():
            raise RuntimeError("GPU-SICAK-DURDU belirdi")
        son = GPU_CSV.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-1]
        derece = int(son.split(",")[1])
        if derece < DURAKLA_C:
            return derece
        print(f"sicaklik {derece}, bekleniyor", flush=True)
        while derece >= DEVAM_C:
            time.sleep(SOGUMA_BEKLE_SN)
            son = GPU_CSV.read_text(encoding="utf-8").strip().splitlines()[-1]
            derece = int(son.split(",")[1])


def sor(mesajlar):
    """Kafa'nin govde bicimiyle istek atar; ham metin, temiz metin, sure ve timings doner.
    HTTP hatasi yutulmaz: sonuca 'hata' olarak yazilir."""
    govde = {"messages": mesajlar, "temperature": KAFA_SICAKLIK, "top_p": KAFA_TOP_P,
             "max_tokens": KAFA_MAX_TOKEN}
    istek = urllib.request.Request(KAFA_UC, data=json.dumps(govde, ensure_ascii=False).encode("utf-8"),
                                   headers={"Content-Type": "application/json; charset=utf-8"})
    derece = sicaklik_bekle()
    basladi = time.perf_counter()
    try:
        with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI_SN) as yanit:
            j = json.loads(yanit.read().decode("utf-8"))
    except urllib.error.HTTPError as hata:
        return {"hata": f"{hata.code} {hata.read().decode('utf-8', 'replace')[:300]}", "sicaklik": derece}
    ham = j["choices"][0]["message"]["content"]
    t = j.get("timings", {})
    return {"sure_sn": round(time.perf_counter() - basladi, 2), "sicaklik": derece,
            "think_var": DUSUNCE_ACILIS in ham, "ham_uzunluk": len(ham), "temiz": dusunce_ayikla(ham),
            "prompt_token": t.get("prompt_n"), "uretim_token": t.get("predicted_n"),
            "tok_sn": round(t.get("predicted_per_second", 0), 1)}


def konusma_olc():
    """Ayni konusmayi 10 tur surdurur; gecmise temiz cevaplar eklenir (Kafa'nin Defter'e yazdigi gibi)."""
    gecmis, turlar = [], []
    for soru in KONUSMA:
        gecmis.append({"role": "user", "content": soru})
        sonuc = sor(gecmis)
        turlar.append(sonuc)
        print("tur", len(turlar), {k: v for k, v in sonuc.items() if k != "temiz"}, flush=True)
        gecmis.append({"role": "assistant", "content": sonuc.get("temiz", "")})
    return turlar


def main():
    teklar = []
    for soru in TEK_SORULAR:
        teklar.append(sor([{"role": "user", "content": soru}]))
        print("tek", {k: v for k, v in teklar[-1].items() if k != "temiz"}, flush=True)
    turlar = konusma_olc()
    CIKTI.write_text(json.dumps({"tek": teklar, "konusma": turlar}, ensure_ascii=False, indent=1),
                     encoding="utf-8")


if __name__ == "__main__":
    main()
