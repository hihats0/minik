"""k26-c olcumu: Gemma'da max_tokens 512/1024/1536 icin kesilme (finish_reason=length), think sonrasi cevap
uzunlugu ve sureyi olcer; 4096 baglam tasmasini ve 'Yeter artik, sus!' ton cevabini dener.
Cagiran: elle (python deneyler/k26c-gemma-uzunluk.py), sunucu ve nvidia-smi izleyicisi ayrica baslatilir."""

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ortak.ayar import KAFA_SICAKLIK, KAFA_TOP_P, KAFA_UC  # noqa: E402
from yuvalar import kafa, ton  # noqa: E402
from yuvalar.kafa_dusunce import dusunce_ayikla  # noqa: E402
from ortak.gpu_sicaklik import DEVAM_ESIGI_C, DURAK_ESIGI_C  # noqa: E402

KOK = Path(__file__).resolve().parent.parent
GPU_CSV = KOK / "loglar" / "k26c-gpu.csv"
CIKTI = KOK / "loglar" / "k26c-sonuc.json"
# Esikler ortak/gpu_sicaklik.py'de tek yerde (sicak-a).
DURAKLA_C = DURAK_ESIGI_C
DEVAM_C = DEVAM_ESIGI_C
SOGUMA_BEKLE_SN = 15
ZAMAN_ASIMI_SN = 180
DENENEN_MAX_TOKEN = (512, 1024, 1536)
# Tasma denemesi: tahmini ~3 karakter/token (f3-e olcumu); 12.000 karakter ~4000 token, 4096'yi zorlar.
TASMA_KARAKTER = (9000, 16000)
TASMA_PARCA = "Dun parkta yuruduk, hava guzeldi, kuslar otuyordu ve cok konustuk. "
SORULAR = [
    "Türkiye'nin başkenti neresidir ve neden orası seçilmiştir?", "Bir kediye nasıl bakılır, kısaca anlat.",
    "Yağmur neden yağar?", "Sabah erken kalkmak için üç öneri ver.",
    "Bilgisayar ile hesap makinesi arasındaki fark nedir?", "Merhaba, bugün biraz yorgunum.",
    "Uyku düzenimi nasıl düzeltebilirim?", "Kitap okumak neden faydalıdır?",
    "Bana kısa bir masal anlatır mısın?", "Fotosentez nedir, basitçe açıkla.",
]


def sicaklik_bekle():
    """CSV son satirindaki sicakliga bakar; 80 ve ustunde 70'in altina inene kadar bekler."""
    while True:
        derece = int(GPU_CSV.read_text(encoding="utf-8").strip().splitlines()[-1].split(",")[1])
        if derece < DURAKLA_C:
            return derece
        print(f"sicaklik {derece}, bekleniyor", flush=True)
        while derece >= DEVAM_C:
            time.sleep(SOGUMA_BEKLE_SN)
            derece = int(GPU_CSV.read_text(encoding="utf-8").strip().splitlines()[-1].split(",")[1])


def sor(mesajlar, max_token):
    """Kafa govde biciminde istek; finish_reason, cevap uzunlugu, sure. HTTP hatasi sonuca yazilir."""
    govde = {"messages": mesajlar, "temperature": KAFA_SICAKLIK, "top_p": KAFA_TOP_P, "max_tokens": max_token}
    istek = urllib.request.Request(KAFA_UC, data=json.dumps(govde, ensure_ascii=False).encode("utf-8"),
                                   headers={"Content-Type": "application/json; charset=utf-8"})
    derece = sicaklik_bekle()
    basladi = time.perf_counter()
    try:
        with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI_SN) as yanit:
            j = json.loads(yanit.read().decode("utf-8"))
    except urllib.error.HTTPError as hata:
        return {"hata": f"{hata.code} {hata.read().decode('utf-8', 'replace')[:300]}", "sicaklik": derece}
    secim = j["choices"][0]
    t = j.get("timings", {})
    return {"max": max_token, "bitis": secim.get("finish_reason"), "sure_sn": round(time.perf_counter() - basladi, 1),
            "sicaklik": derece, "cevap_uzunluk": len(dusunce_ayikla(secim["message"]["content"])),
            "prompt_token": t.get("prompt_n"), "uretim_token": t.get("predicted_n")}


def uzunluk_olc():
    """Her soru, her max_tokens degeri icin bir istek."""
    sonuc = []
    for max_token in DENENEN_MAX_TOKEN:
        for soru in SORULAR:
            sonuc.append(sor([{"role": "user", "content": soru}], max_token))
            print(sonuc[-1], flush=True)
    return sonuc


def tasma_dene():
    """Uzun gecmisle Kafa'nin kendi dusun() fonksiyonunu cagirir; hata yukselirse metni kaydedilir."""
    sonuc = []
    for karakter in TASMA_KARAKTER:
        metin = (TASMA_PARCA * (karakter // len(TASMA_PARCA) + 1))[:karakter]
        baglam = [{"role": "user", "content": metin}, {"role": "assistant", "content": "Anladim."}]
        sicaklik_bekle()
        try:
            cevap, is_sn = kafa.dusun("Bunu bir cumleyle ozetle.", baglam)
            sonuc.append({"karakter": karakter, "cevap_uzunluk": len(cevap), "is_sn": round(is_sn, 1)})
        except urllib.error.URLError as hata:
            govde = hata.read().decode("utf-8", "replace")[:300] if hasattr(hata, "read") else ""
            sonuc.append({"karakter": karakter, "hata": f"{hata} {govde}"})
        print(sonuc[-1], flush=True)
    return sonuc


def sus_dene():
    """'Yeter artik, sus!' icin Kafa'nin ham cevabini (sicaklik 0, deterministik) kaydeder."""
    sicaklik_bekle()
    ham = ton._kafaya_sor("Yeter artık, sus!")
    return {"ham_sonu": ham[-300:], "ayiklanmis": dusunce_ayikla(ham), "etiket": ton.etiketi_ayikla(ham)}


def main():
    sonuc = {"sus": sus_dene()}
    print(sonuc["sus"], flush=True)
    sonuc["tasma"] = tasma_dene()
    sonuc["uzunluk"] = uzunluk_olc()
    CIKTI.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
