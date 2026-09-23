"""llama-server'in OpenAI uyumlu ucuna sorar, cevap metnini ve gercek is saniyesini dondurur.
Hormon degerlerini ornekleme ayarlarina cevirir (kademe 1, K6: donusum burada, akista degil).
Cagiran: minik.py akisi."""

import hashlib
import json
import os
import time
import urllib.error
import urllib.request

from ortak import log
from yuvalar.kafa_dusunce import dusunce_ayikla
from ortak.ayar import (
    ALT_ESIK,
    KAFA_BAGLAM,
    KAFA_MAX_TOKEN,
    KAFA_MODEL_YOLU,
    KAFA_SICAKLIK,
    KAFA_TOP_P,
    KAFA_UC,
    KAFA_ZAMAN_ASIMI_SN,
    KARAKTER_DOSYASI,
    KARAKTER_OZET_UZUNLUGU,
    KORTIZOL_REPEAT_PENALTY_ARALIK,
    KORTIZOL_REPEAT_PENALTY_MIN,
    MELATONIN_YORGUN_MAX_TOKEN_CARPANI,
    MELATONIN_YORGUN_SICAKLIK_CARPANI,
    MELATONIN_YORGUN_TALIMATI,
    MOD_UYANIK,
    MOD_YORGUN,
    MOD_ZORLA_DEGISKENI,
    NORADRENALIN_SICAKLIK_ARALIK,
    NORADRENALIN_SICAKLIK_MIN,
    NORADRENALIN_TOP_P_ARALIK,
    NORADRENALIN_TOP_P_MIN,
    SEROTONIN_MAX_TOKEN_ARALIK,
    SEROTONIN_MAX_TOKEN_MIN,
    UST_ESIK,
)

YUVA_ADI = "kafa"
# llama-server cevabindaki timings alanlari (f3-e'de gercek sunucuda olculdu, rapor).
TIMINGS_PROMPT_MS = "prompt_ms"
TIMINGS_URETIM_MS = "predicted_ms"
MS_SANIYE = 1000.0
# Loga yazilan HTTP hata govdesinin en cok uzunlugu (tasma mesaji ~200 karakter).
HATA_GOVDE_UZUNLUGU = 300
# Karakter metni ile yorgun talimati arasina bos satir (tek sistem mesajinda iki paragraf).
PARCA_AYIRICI = "\n\n"
# Onceki turun modu: cift esik (Schmitt tetikleyici) hafiza ister, tek surecli akis tek Kafa
# kullandigi icin modul seviyesinde tutuluyor (testler dogrudan sifirlayabilir, DEFTER_KLASORU
# gibi).
ONCEKI_MOD = MOD_UYANIK


def dusun(soru, baglam=None, hormon_degerleri=None):
    """Soruyu (varsa onceki mesajlarla birlikte) llama-server'a sorar, (cevap, is_sn) dondurur.
    is_sn: sunucunun bu cevap icin harcadigi gercek is saniyesi (melatonini besler, K10).
    hormon_degerleri verilirse ornekleme ayarlari ondan hesaplanir (kademe 1); verilmezse f0'in
    olctugu sabit ayarlar kullanilir. Sunucu cevap vermezse hatayi yutmaz, yukseltir."""
    basladi = time.perf_counter()
    mesajlar = list(baglam) if baglam else []
    mesajlar.append({"role": "user", "content": soru})
    ayarlar, mod = _ornekleme_ayarlari(hormon_degerleri)
    karakter, karakter_ozeti = _karakter_oku()
    mesajlar = _sistem_mesaji_ekle(mesajlar, karakter, mod)
    govde = _govde_olustur(mesajlar, ayarlar)
    ayarlar = {**ayarlar, "talimat": MELATONIN_YORGUN_TALIMATI if mod == MOD_YORGUN else None,
               "karakter": karakter_ozeti}
    try:
        cevap, token_sayisi, timings = _sunucuya_sor(govde)
    except (urllib.error.URLError, OSError) as hata:
        log.yaz(YUVA_ADI, "dusun", _gecen_ms(basladi), "hata",
                {"hata": _hata_metni(hata), "model": KAFA_MODEL_YOLU, "mod": mod, "ayarlar": ayarlar})
        raise
    is_sn = _is_saniyesi(timings, time.perf_counter() - basladi)
    log.yaz(YUVA_ADI, "dusun", _gecen_ms(basladi), "ok",
            {"token": token_sayisi, "is_sn": round(is_sn, 3), "baglam": KAFA_BAGLAM,
             "model": KAFA_MODEL_YOLU, "mod": mod, "ayarlar": ayarlar})
    return cevap, is_sn


def _hata_metni(hata):
    """Hata metni; sunucu HTTP hatasi dondurduyse govdesini de ekler. k26-c: baglam tasmasinda
    llama-server 400 + 'exceed_context_size_error' doner, sebep yalniz govdede yazar."""
    if isinstance(hata, urllib.error.HTTPError):
        return f"{hata} {hata.read().decode('utf-8', 'replace')[:HATA_GOVDE_UZUNLUGU]}"
    return str(hata)


def _is_saniyesi(timings, duvar_sn):
    """Sunucunun kendi olctugu is suresi: prompt okuma + uretim (prompt_ms + predicted_ms).
    Neden bu: ikisi de GPU'nun bu tur icin gercekten calistigi sure; baglam buyudukce prompt_ms
    de buyur, uzun cevapta predicted_ms buyur. timings yoksa melatonin sessizce 0 kalmasin diye
    istegin duvar saati kullanilir ve bu durum 'hata' satiriyla loglanir."""
    try:
        return (timings[TIMINGS_PROMPT_MS] + timings[TIMINGS_URETIM_MS]) / MS_SANIYE
    except (KeyError, TypeError) as hata:
        log.yaz(YUVA_ADI, "is_saniyesi", 0, "hata",
                {"hata": f"timings eksik ({hata!r}), duvar saati kullanildi", "duvar_sn": round(duvar_sn, 3)})
        return duvar_sn


def _ornekleme_ayarlari(hormon_degerleri):
    """Yedi hormondan dordunu Kafa'nin istek alanlarina cevirir: noradrenalin->sicaklik/top_p,
    serotonin->max_token (SUREKLI, esik yok), kortizol->repeat_penalty (SUREKLI). Melatonin
    AC/KAPA bir karar surer ("yorgun mu"), o yuzden cift esikle (ALT_ESIK/UST_ESIK) hesaplanan
    bir MOD doner; yorgun modda sicaklik ve max_token asagi cekilir. (ayarlar, mod) dondurur."""
    global ONCEKI_MOD
    if not hormon_degerleri:
        return ({"temperature": KAFA_SICAKLIK, "top_p": KAFA_TOP_P, "max_tokens": KAFA_MAX_TOKEN,
                  "repeat_penalty": KORTIZOL_REPEAT_PENALTY_MIN}, MOD_UYANIK)

    zorlanan = _mod_zorlanan()
    mod = zorlanan if zorlanan else _mod_hesapla(hormon_degerleri["melatonin"], ONCEKI_MOD)
    ONCEKI_MOD = mod

    sicaklik = NORADRENALIN_SICAKLIK_MIN + (hormon_degerleri["noradrenalin"] / 100) * NORADRENALIN_SICAKLIK_ARALIK
    top_p = NORADRENALIN_TOP_P_MIN + (hormon_degerleri["noradrenalin"] / 100) * NORADRENALIN_TOP_P_ARALIK
    max_token = SEROTONIN_MAX_TOKEN_MIN + (hormon_degerleri["serotonin"] / 100) * SEROTONIN_MAX_TOKEN_ARALIK
    repeat_penalty = KORTIZOL_REPEAT_PENALTY_MIN + (hormon_degerleri["kortizol"] / 100) * KORTIZOL_REPEAT_PENALTY_ARALIK

    if mod == MOD_YORGUN:
        sicaklik *= MELATONIN_YORGUN_SICAKLIK_CARPANI
        max_token *= MELATONIN_YORGUN_MAX_TOKEN_CARPANI

    ayarlar = {
        "temperature": round(sicaklik, 3),
        "top_p": round(top_p, 3),
        "max_tokens": int(max_token),
        "repeat_penalty": round(repeat_penalty, 3),
    }
    return ayarlar, mod


def _mod_hesapla(melatonin, onceki_mod):
    """Cift esikli (Schmitt tetikleyici) mod karari (spec 3.6.2, M1): yorgun moda girmek icin
    UST_ESIK asilmali, cikmak icin ALT_ESIK'in ALTINA inilmeli. Aradaki bolgede mod degismez,
    boylece esigin hemen ustunde/altinda titreme (histerezis) engellenir."""
    if onceki_mod == MOD_YORGUN:
        return MOD_UYANIK if melatonin <= ALT_ESIK else MOD_YORGUN
    return MOD_YORGUN if melatonin >= UST_ESIK else MOD_UYANIK


def _mod_zorlanan():
    """f3-c'nin 'ayni soru, iki mod' kosusu icin: MOD_ZORLA_DEGISKENI ortam degiskeni gecerli
    bir mod adiyla (uyanik/yorgun) doluysa hesaplanan modu ezer. Bos ya da taninmayan degerde
    None doner, normal hesaplama calisir."""
    deger = os.environ.get(MOD_ZORLA_DEGISKENI)
    return deger if deger in (MOD_UYANIK, MOD_YORGUN) else None


def _karakter_oku():
    """Karakter dosyasini okur, (metin, sha256 kisa ozeti) dondurur. Dosya yoksa ya da
    okunamazsa hatayi loglar ve (None, None) doner: Minik karaktersiz konusur ama susmaz."""
    try:
        ham = KARAKTER_DOSYASI.read_bytes()
    except OSError as hata:
        log.yaz(YUVA_ADI, "karakter_oku", 0, "hata",
                {"hata": str(hata), "dosya": str(KARAKTER_DOSYASI)})
        return None, None
    ozet = hashlib.sha256(ham).hexdigest()[:KARAKTER_OZET_UZUNLUGU]
    return ham.decode("utf-8").strip(), ozet


def _sistem_mesaji_ekle(mesajlar, karakter, mod):
    """Listenin basina TEK sistem mesaji koyar: karakter metni, yorgun modda altina tek cumlelik
    talimat (f3-g, K25=B). Iki ayri sistem mesaji yok: sohbet sablonlari sistem mesajini listenin
    basinda tek parca bekler. Ikisi de yoksa liste degismeden doner."""
    parcalar = [karakter] if karakter else []
    if mod == MOD_YORGUN:
        parcalar.append(MELATONIN_YORGUN_TALIMATI)
    if not parcalar:
        return mesajlar
    return [{"role": "system", "content": PARCA_AYIRICI.join(parcalar)}] + mesajlar


def _govde_olustur(mesajlar, ayarlar):
    """Istek govdesini hazirlar: ornekleme ayarlari hesaplanan sozlukten gelir, ciplak sayi yok."""
    return {"messages": mesajlar, **ayarlar}


def _sunucuya_sor(govde):
    """HTTP istegini yollar, (cevap_metni, token_sayisi, timings) dondurur. timings sunucu
    vermezse None olur; karari _is_saniyesi verir."""
    istek = urllib.request.Request(
        KAFA_UC,
        data=json.dumps(govde, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(istek, timeout=KAFA_ZAMAN_ASIMI_SN) as yanit:
        yanit_json = json.loads(yanit.read().decode("utf-8"))
    cevap = dusunce_ayikla(yanit_json["choices"][0]["message"]["content"])
    token_sayisi = yanit_json.get("usage", {}).get("completion_tokens", 0)
    return cevap, token_sayisi, yanit_json.get("timings")


def _gecen_ms(basladi):
    """Olcum baslangicindan bu yana gecen sureyi tam sayi milisaniye verir."""
    return int((time.perf_counter() - basladi) * 1000)
