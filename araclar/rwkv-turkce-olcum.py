"""RWKV Turkce olcumu: 20 soruyu calisan llama-server'a gonderir, cevaplari ve
zamanlama bilgisini JSON olarak basar. Cagiran: elle, `python araclar/rwkv-turkce-olcum.py [port]`."""

import json
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

VARSAYILAN_PORT = 8090
N_PREDICT = 200
DURDURMA_DIZISI = "\n\nUser:"

# Model kartinin (shoumenchougou/RWKV7-G1j-1.5B-GGUF) test edilmis ornek ayarlari.
ORNEKLEME = {
    "temperature": 1,
    "top_k": 128,
    "top_p": 0.5,
    "frequency_penalty": 0.5,
    "presence_penalty": 0.5,
    "repeat_penalty": 1,
}

SORULAR = [
    "Bugun hava cok guzel diye bir tweet at, 140 karakteri gecmesin.",
    "Yeni bir kod hatasi cozdum, bunu ovunerek ama alcakgonullu bir tweet yap.",
    "Bir kedi videosunu paylasirken altina yazilacak kisa bir sey yaz.",
    "Biri sana 'sen zaten hicbir ise yaramazsin' dedi, ona nazik ama sivri bir cevap ver.",
    "'Yine mi gec kaldin' diyen birine espirili bir karsilik ver.",
    "'Senin gibi biri bunu asla basaramaz' diyen birine kisa ve kendinden emin bir cevap yaz.",
    "2027 yilinda hangi takim sampiyon olacak?",
    "Yigit'in en sevdigi rengi soyler misin?",
    "Su anki saat kac?",
    "'Eline saglik' ne demek, kisaca acikla.",
    "'Kafayi yemek' deyimini bir cumlede kullan.",
    "Biri sana 'oha falso' yazdi, bu ne demek ve nasil cevap verirsin?",
    "'Yagmur gibi yagdi' ile 'para gibi yagdi' arasindaki farki anlat.",
    "'Kitap' kelimesine hem cogul hem iyelik hem de hal eki ekleyerek bir cumle kur (ornek: kitaplarimda).",
    "'Gormek' fiilini olumsuz, soru ve gecmis zaman ekleriyle birlikte cek (ornek: gormedin mi?).",
    "'Gel-,git-,otur-' fiillerini '-ecek/-acak' gelecek zaman ekiyle cekimle.",
    "Yabanci bir kelime olan 'laptop'a Turkce hal eki ekleyerek bir cumle kur (ornek: laptopumu aldim).",
    (
        "Asagidaki metni tek cumlede ozetle: 'Dun aksam eve gec geldim cunku otobus saatlerce "
        "gelmedi, sonra yagmur basladi ve semsiyem yoktu, sirilsiklam oldum ama neyse ki evde "
        "sicak corba beni bekliyordu.'"
    ),
    "Su cumle uzerine iki cumlelik merak uyandiran bir soru sor: 'Dun gece garip bir ses duydum.'",
    (
        "Su metnin tonunu tek kelimeyle soyle: 'Yapma ya, cidden mi kazandik?? Inanamiyorum "
        "su an, resmen havalardayim!'"
    ),
]


def soru_gonder(port, soru, dusunmeyi_atla=False):
    """Tek soruyu /completion ucuna gonderir, cevap metnini ve timings sozlugunu dondurur.
    dusunmeyi_atla=True ise bos <think> blogu ekleyip modelin dogrudan cevaba gecmesini dener."""
    ek = "<think>\n\n</think>\n\n" if dusunmeyi_atla else ""
    prompt = f"User: {soru}\n\nAssistant: {ek}"
    govde = {
        "prompt": prompt,
        "n_predict": N_PREDICT,
        "stop": [DURDURMA_DIZISI],
        **ORNEKLEME,
    }
    istek = urllib.request.Request(
        f"http://127.0.0.1:{port}/completion",
        data=json.dumps(govde).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    baslangic = time.time()
    with urllib.request.urlopen(istek, timeout=120) as yanit:
        veri = json.loads(yanit.read().decode("utf-8"))
    toplam_sure = time.time() - baslangic
    return {
        "soru": soru,
        "cevap": veri.get("content", "").strip(),
        "timings": veri.get("timings", {}),
        "toplam_saniye": round(toplam_sure, 3),
    }


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else VARSAYILAN_PORT
    dusunmeyi_atla = "--skip-think" in sys.argv
    sonuclar = []
    for i, soru in enumerate(SORULAR, start=1):
        sonuc = soru_gonder(port, soru, dusunmeyi_atla)
        sonuclar.append(sonuc)
        t = sonuc["timings"]
        hiz = t.get("predicted_per_second", 0)
        print(f"[{i:2d}/20] {hiz:6.2f} tok/s  ({sonuc['toplam_saniye']}s)  {soru[:40]}")

    print("\n--- JSON cikti ---")
    print(json.dumps(sonuclar, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
