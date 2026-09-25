"""f3-c3: f3-c1'in 10 sorusu + 20 yeni soru, 8 sabit tohum, uyanik/yorgun modda gercek llama-server'a
kosar (480 cevap), anonim dosya + anahtar dosyasi yazar, anonim dosyada mod izi tarar. Puanlama YAPMAZ.
Cagiran: elle, `.venv\\Scripts\\python.exe deneyler\\f3c3-kor-uretim.py`."""

import importlib.util
import json
import os
import random
import re
import subprocess
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from ortak.ayar import MOD_UYANIK, MOD_YORGUN, MOD_ZORLA_DEGISKENI  # noqa: E402
from yuvalar import hormonlar, kafa  # noqa: E402

# Sunucu acma/kapama, sicaklik kurali, kimlik ve yonerge f3-c1'de var; kopyalamak yerine yuklenir.
_OZELLIK = importlib.util.spec_from_file_location("f3c1", KOK / "deneyler" / "f3c1-kor-uretim.py")
f3c1 = importlib.util.module_from_spec(_OZELLIK)
_OZELLIK.loader.exec_module(f3c1)
f3c1.SUNUCU_LOG = KOK / "loglar" / "sunucu" / "f3c3-sunucu.log"

CIKTI_KLASORU = KOK / "reports" / "f3c3-kor-olcum"
TOHUMLAR = range(1, 9)
MODLAR = [MOD_UYANIK, MOD_YORGUN]
KARISTIRMA_DENEME = 1000
MS = 1000
# Anonim dosyada mod ya da ayar izi: mod adlari, istek alan adlari, tohum ve iki modun sayilari.
SIZINTI_DESENI = re.compile(
    r"uyan[ıi]k|yorgun|temperature|top_p|repeat_penalty|max_tokens|seed|tohum|s[ıi]cakl[ıi]k"
    r"|\b(448|224|0[.,]64|0[.,]448|0[.,]836|1[.,]03)\b", re.IGNORECASE)

# 20 yeni soru, dort tur x 5. Uzun anlatim sorulari yorgun modun max_tokens tavanina (224) carpsin
# diye uzun cevap ister; kisa cevaplar tavandan uzak kalsin diye tek kelime/cumle ister.
YENI_SORULAR = [
    ("K1", "kisa-cevap", "Türkiye'nin başkenti neresidir? Tek kelimeyle cevap ver."),
    ("K2", "kisa-cevap", "Bir haftada kaç gün vardır? Sadece sayıyı yaz."),
    ("K3", "kisa-cevap", "Suyun kaynama noktası kaç derecedir? Tek cümleyle söyle."),
    ("K4", "kisa-cevap", "'Merhaba' kelimesinin İngilizcesi nedir?"),
    ("K5", "kisa-cevap", "Gökkuşağında kaç renk vardır? Kısaca cevap ver."),
    ("U1", "uzun-anlatim", "İnternetin nasıl çalıştığını adım adım, ayrıntılı bir şekilde anlat."),
    ("U2", "uzun-anlatim", "Bir bilgisayar programının yazılıp çalıştırılmasına kadar geçen süreci baştan sona uzun uzun açıkla."),
    ("U3", "uzun-anlatim", "Mevsimlerin neden oluştuğunu bir çocuğa anlatır gibi, örneklerle ve ayrıntılı açıkla."),
    ("U4", "uzun-anlatim", "Yeni başlayan biri için yemek yapmayı öğrenmenin yollarını madde madde ve açıklamalı yaz."),
    ("U5", "uzun-anlatim", "Kısa bir hikaye yaz: kaybolan bir kedi evinin yolunu buluyor. En az üç paragraf olsun."),
    ("D1", "duygu-sohbet", "Bugün çok moralim bozuk, sınavdan düşük aldım. Benimle biraz konuşur musun?"),
    ("D2", "duygu-sohbet", "En yakın arkadaşım başka şehre taşındı, onu çok özleyeceğim."),
    ("D3", "duygu-sohbet", "Bugün ilk kez kendi başıma bir program yazdım ve çalıştı! Çok mutluyum."),
    ("D4", "duygu-sohbet", "Sence insan yalnız kaldığında ne yapmalı?"),
    ("D5", "duygu-sohbet", "Nasılsın, bugün günün nasıl geçti?"),
    ("L3", "laf-sokma", "'Senin cevapların hep çok uzun, kimse okumuyor' diyen birine cevap ver."),
    ("L4", "laf-sokma", "Biri sana 'hesap makinesi senden daha akıllı' dedi. Ne dersin?"),
    ("L5", "laf-sokma", "'Bir şeyi de düzgün yap' diye söylenen birine kısa ve esprili bir karşılık ver."),
    ("L6", "laf-sokma", "Arkadaşın 'sen yine mi buradasın, sıkılmadın mı' diye takıldı. Cevabın ne olur?"),
    ("L7", "laf-sokma", "'Yapay zekalar hiçbir zaman şaka yapmayı öğrenemez' diyen birine şakayla cevap ver."),
]
SORULAR = f3c1.SORULAR + YENI_SORULAR
TOPLAM = len(SORULAR) * len(TOHUMLAR) * len(MODLAR)


def gpu_durumu():
    """GPU sicakligi (C) ve kullanilan VRAM (MiB), tek nvidia-smi cagrisiyla."""
    cikti = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=temperature.gpu,memory.used", "--format=csv,noheader,nounits"],
        text=True)
    sicaklik, vram = cikti.strip().splitlines()[0].split(",")
    return int(sicaklik), int(vram)


def tek_cevap(soru, hormon_degerleri, tohum):
    """kafa.dusun ile ayni ayar ve govde, tek fark sabit `seed`: dusun() tohum almadigi icin kafa'nin
    kendi parcalari kullanilir, ayar hesaplamasina dokunulmaz. (cevap, mod, token, is_sn, duvar_ms)."""
    ayarlar, mod = kafa._ornekleme_ayarlari(dict(hormon_degerleri))
    govde = {**kafa._govde_olustur([{"role": "user", "content": soru}], ayarlar), "seed": tohum}
    basla = time.perf_counter()
    cevap, token, timings = kafa._sunucuya_sor(govde)
    duvar_sn = time.perf_counter() - basla
    return cevap, mod, ayarlar, token, kafa._is_saniyesi(timings, duvar_sn), int(duvar_sn * MS)


def kayitlari_uret(hormon_degerleri, zirve):
    """Tohum > soru > mod sirasiyla doner: iki mod ayni anda, ayni isilikta uretilsin diye
    modlar ic dongude. zirve sozlugune en yuksek sicaklik ve VRAM yazilir."""
    kayitlar = []
    for tohum in TOHUMLAR:
        for soru_id, kategori, soru in SORULAR:
            for mod in MODLAR:
                f3c1.sicaklik_kontrol()
                sicaklik, vram = gpu_durumu()
                zirve["sicaklik_c"] = max(zirve["sicaklik_c"], sicaklik)
                zirve["vram_mib"] = max(zirve["vram_mib"], vram)
                os.environ[MOD_ZORLA_DEGISKENI] = mod
                cevap, mod_gercek, ayarlar, token, is_sn, duvar_ms = tek_cevap(soru, hormon_degerleri, tohum)
                kayitlar.append({"soru_id": soru_id, "kategori": kategori, "soru": soru, "mod": mod_gercek,
                                 "tohum": tohum, "cevap": cevap, "ayarlar": ayarlar, "token": token,
                                 "is_sn": round(is_sn, 3), "duvar_ms": duvar_ms})
                print(f"[{len(kayitlar)}/{TOPLAM}] t{tohum} {soru_id} {mod_gercek}: {duvar_ms} ms, {token} tok, {sicaklik} C")
    return kayitlar


def karistir(kayitlar):
    """Rastgele sirala; ayni sorunun iki cevabi yan yana gelmesin (f3-c1 dersi). 480 kayitta duz
    shuffle neredeyse hic temiz cikmaz, o yuzden her adimda onceki sorudan farkli bir kayit
    kalanlarin sayisiyla agirlikli secilir; cikmaza girerse bastan denenir."""
    for _ in range(KARISTIRMA_DENEME):
        kalan = {}
        for kayit in kayitlar:
            kalan.setdefault(kayit["soru_id"], []).append(kayit)
        for liste in kalan.values():
            random.shuffle(liste)
        sirali, onceki = [], None
        while kalan:
            adaylar = [s for s in kalan if s != onceki]
            if not adaylar:
                break
            onceki = random.choices(adaylar, weights=[len(kalan[s]) for s in adaylar])[0]
            sirali.append(kalan[onceki].pop())
            if not kalan[onceki]:
                del kalan[onceki]
        if len(sirali) == len(kayitlar):
            return sirali
    raise RuntimeError(f"{KARISTIRMA_DENEME} denemede komsu soru cakismasiz sira bulunamadi")


def yaz(kayitlar):
    """anonim-cevaplar.md (yalniz kimlik+soru+cevap) ve anahtar.json (kimlik -> mod/tohum/sure/...)."""
    CIKTI_KLASORU.mkdir(parents=True, exist_ok=True)
    kullanilan, anahtar, parcalar = set(), {}, [f3c1.YONERGE]
    for kayit in karistir(kayitlar):
        kimlik = f3c1.kimlik_uret(kullanilan)
        parcalar.append(f"## Kayit {kimlik}\n\n**Soru:** {kayit['soru']}\n\n**Cevap:**\n\n{kayit['cevap']}\n\n---\n\n")
        anahtar[kimlik] = {k: kayit[k] for k in ("soru_id", "kategori", "mod", "tohum", "ayarlar",
                                                 "token", "is_sn", "duvar_ms")}
        anahtar[kimlik]["cevap_karakter"] = len(kayit["cevap"])
    (CIKTI_KLASORU / "anonim-cevaplar.md").write_text("".join(parcalar), encoding="utf-8")
    with open(CIKTI_KLASORU / "anahtar.json", "w", encoding="utf-8") as dosya:
        json.dump(anahtar, dosya, ensure_ascii=False, indent=2, sort_keys=True)


def sizinti_tara(metin):
    """Anonim metinde mod/ayar izi arar, (satir_no, satir) listesi dondurur. Yonerge basligi
    taranmaz, cunku puanlayiciya zaten gosterilen sabit metin."""
    govde_basi = metin.index("## Kayit")
    onceki_satir = metin[:govde_basi].count("\n")
    return [(onceki_satir + no, satir) for no, satir in enumerate(metin[govde_basi:].splitlines(), 1)
            if SIZINTI_DESENI.search(satir)]


def main():
    hormon_degerleri = hormonlar.Hormonlar().oku()
    zirve = {"sicaklik_c": 0, "vram_mib": 0}
    basla = time.time()
    proc = f3c1.sunucu_baslat()
    try:
        f3c1.sunucu_hazir_bekle(proc)
        kayitlar = kayitlari_uret(hormon_degerleri, zirve)
    finally:
        f3c1.sunucu_durdur(proc)
    yaz(kayitlar)
    eslesmeler = sizinti_tara((CIKTI_KLASORU / "anonim-cevaplar.md").read_text(encoding="utf-8"))
    print(f"[bitti] {len(kayitlar)} kayit, {int(time.time() - basla)} sn, zirve {zirve}")
    print(f"[sizinti] {len(eslesmeler)} eslesme")
    for no, satir in eslesmeler:
        print(f"  {no}: {satir[:200]}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
