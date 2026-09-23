"""Iddia esleme (f10-b): ayni seyi soyleyen web kayitlarini gruplar, her grup Bekci'ye tek iddia metni ve
alan adi listesiyle gider. Esleyici degistirilebilir: basit (GPU'suz kelime ortusmesi) ya da Kafa'ya soran.
Cagiran: yuvalar/merak.py."""

import re

ASCII_HARITA = str.maketrans("ışğüöçâî", "isguocai")
EN_KISA_KELIME = 4  # "ve", "the", "bir" gibi baglaclar anlam tasimaz, kisa kelimeler atilir
ORTUSME_ESIGI = 0.5  # TAHMIN: kisa metnin kelimelerinin yarisi uzunda varsa ayni iddia sayilir
EN_AZ_ORTAK = 3  # TAHMIN: iki uc kelimelik tanim tesadufen %50 ortusmesin diye
KAFA_SORUSU = ("Iki metin ayni bilgiyi mi soyluyor? Yalniz 'evet' ya da 'hayir' yaz.\n"
               "1: {a}\n2: {b}")
KAFA_EVET = "evet"


def kelimeler(metin):
    """Metnin anlam tasiyan kelime kumesi: kucuk harf, ASCII, kisa kelimeler atilmis."""
    normal = metin.lower().translate(ASCII_HARITA)
    return {k for k in re.findall(r"[a-z0-9]+", normal) if len(k) >= EN_KISA_KELIME}


def basit_ayni_mi(a, b):
    """Kisa metnin kelimelerinin en az yarisi (ve en az 3 kelime) uzun metinde de varsa ayni iddia."""
    ka, kb = kelimeler(a), kelimeler(b)
    ortak = len(ka & kb)
    kucuk = min(len(ka), len(kb))
    return kucuk > 0 and ortak >= EN_AZ_ORTAK and ortak / kucuk >= ORTUSME_ESIGI


def kafa_ayni_mi(sor):
    """Kafa'ya soran karsilastirici uretir; sor(metin) -> cevap metni (gercekte kafa.dusun'un ilk ogesi)."""
    def ayni_mi(a, b):
        return sor(KAFA_SORUSU.format(a=a, b=b)).strip().lower().startswith(KAFA_EVET)
    return ayni_mi


def grupla(kayitlar, ayni_mi=basit_ayni_mi):
    """Kayitlari gruplar: her kayit, temsilcisi ayni iddiayi soyleyen ilk gruba girer, yoksa yeni grup acar.
    Donen grup: {"iddia": temsilci metin, "kayitlar": [...], "alanlar": sirali farkli alan adlari}."""
    gruplar = []
    for kayit in kayitlar:
        grup = next((g for g in gruplar if ayni_mi(g["iddia"], kayit["soru"])), None)
        if grup is None:
            grup = {"iddia": kayit["soru"], "kayitlar": []}
            gruplar.append(grup)
        grup["kayitlar"].append(kayit)
    for g in gruplar:
        g["alanlar"] = sorted({k["kaynak"] for k in g["kayitlar"]})
    return gruplar
