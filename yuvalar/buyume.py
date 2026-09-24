"""Buyume (f9-a, GPU'suz kisim): gece islenen gunun kayitlarindan LoRA egitim cifti adayi toplar
(S7 filtresi: X kaynakli girdi ve emniyet reddi girmez), esik bayragi kaldirir, yeni adaptor icin
kabul gecidi karari verir. Egitimin kendisi burada YOK (GPU yasak). Cagiran: yuvalar/uyku.py, testler."""

import json
import time

from ortak import log
from yuvalar import bekci, bekci_giris

YUVA_ADI = "buyume"
CIFT_DOSYASI = "egitim-ciftleri.jsonl"
HAZIR_BAYRAGI = "egitim-hazir.flag"
# K11: ~500-1.000 filtreli cift (tahmin, LIMA ~1.000). Alt ucu secildi: bayrak yalniz haber verir.
EGITIM_ESIGI = 500
# S7/KT8: X icerigi egitim girdisi olamaz. "x" disinda X'ten gelen kaydin baska adi yok (minik.py).
# "dosya" agzi (f8-a) da eleniyor: dosyayi kimin yazdigi bilinmiyor, X'ten kopya olabilir.
# "site" (f8-b): ziyaretci Yigit degil, yazdigi bilinmeyen dis kaynak; egitime girmez.
X_PLATFORMLARI = bekci_giris.X_PLATFORMLARI | {"dosya", "site"}
# K34 revize: "vikipedi_okudum" etiketli kayit tek agizdir, tam bilgi gibi LoRA'ya girmez (merak.py).
ETIKETLI_GUVENLER = {"vikipedi_okudum"}
KABUL_SINAVLARI = ("turkce", "odul")


def x_kaynakli_mi(kayit):
    """Kaydin platform ya da kaynak alani X'i gosteriyorsa True; alan yoksa da True (bilinmeyen
    kaynak guvenli tarafta kalir, S7). Kaynak "x:" onekliyse de X (Bekci X hesabini boyle yazar).
    Yalniz "@ali" (platform yok, onek yok) belirsiz sayilir, X sayilmaz."""
    platform = str(kayit.get("platform", kayit.get("kaynak", "x"))).strip().lower()
    kaynak = str(kayit.get("kaynak", "")).strip().lower()
    return platform in X_PLATFORMLARI or kaynak.startswith(bekci_giris.X_ONEKI)


def cift_adaylari(kayitlar, tarih, emniyet=bekci.cikabilir_mi):
    """Kayitlardan {tarih, girdi, cikti} ciftleri; X kaynakli, bos ya da emniyetten gecmeyen elenir."""
    ciftler = []
    for kayit in kayitlar:
        girdi, cikti = kayit.get("soru", ""), kayit.get("cevap", "")
        if x_kaynakli_mi(kayit) or kayit.get("guven") in ETIKETLI_GUVENLER or not girdi or not cikti:
            continue
        gecti, _ = emniyet(cikti)
        if gecti:
            ciftler.append({"tarih": tarih, "girdi": girdi, "cikti": cikti})
    return ciftler


def biriktir(klasor, tarih, kayitlar, emniyet=bekci.cikabilir_mi):
    """Gunun ciftlerini defter/egitim-ciftleri.jsonl'e ekler, (eklenen, toplam) dondurur. Esik
    gecilince yalniz bayrak dosyasi yazilir ve loglanir; egitim baslatilmaz (GPU yasak)."""
    basladi = time.perf_counter()
    ciftler = cift_adaylari(kayitlar, tarih, emniyet)
    dosya = klasor / CIFT_DOSYASI
    with dosya.open("a", encoding="utf-8") as f:
        for cift in ciftler:
            f.write(json.dumps(cift, ensure_ascii=False) + "\n")
    with dosya.open("r", encoding="utf-8") as f:
        toplam = sum(1 for s in f if s.strip())
    hazir = toplam >= EGITIM_ESIGI
    if hazir:
        (klasor / HAZIR_BAYRAGI).write_text(f"{toplam} cift, esik {EGITIM_ESIGI}\n", encoding="utf-8")
    log.yaz(YUVA_ADI, "biriktir", int((time.perf_counter() - basladi) * 1000), "ok",
            {"tarih": tarih, "okunan": len(kayitlar), "eklenen": len(ciftler),
             "toplam": toplam, "egitim_hazir": hazir})
    return len(ciftler), toplam


def ozet_satiri(eklenen, toplam):
    """Sabah ozetine (ve onunla gorunur sayfaya) giden sayac satiri."""
    durum = "egitim hazir (baslatilmadi)" if toplam >= EGITIM_ESIGI else "birikiyor"
    return f"- Egitim cifti: +{eklenen}, toplam {toplam}/{EGITIM_ESIGI} ({durum})"


def yeni_adaptor_kabul(eski_puanlar, yeni_puanlar):
    """K11 kabul gecidi. Kural: yeni adaptor HICBIR sinavda eskiden dusuk olamaz VE en az birinde
    kesin yuksek olmali. Her sinavda esitlik = gecmedi, eskide kalinir (egitim bedava degil,
    fark yoksa degisiklik de yok). (kabul, gerekce) dondurur ve loglar."""
    dusen = [s for s in KABUL_SINAVLARI if yeni_puanlar[s] < eski_puanlar[s]]
    artan = [s for s in KABUL_SINAVLARI if yeni_puanlar[s] > eski_puanlar[s]]
    if dusen:
        kabul, gerekce = False, "dustu: " + ", ".join(dusen)
    elif not artan:
        kabul, gerekce = False, "esit: hicbir sinavda gecmedi"
    else:
        kabul, gerekce = True, "gecti: " + ", ".join(artan)
    log.yaz(YUVA_ADI, "kabul_gecidi", 0, "ok",
            {"eski": eski_puanlar, "yeni": yeni_puanlar, "kabul": kabul, "gerekce": gerekce})
    return kabul, gerekce
