"""llama-server'in OpenAI uyumlu ucuna sorar, cevap metnini dondurur, sureyi loglar.
Hormon degerlerini ornekleme ayarlarina cevirir (kademe 1, K6: donusum burada, akista degil).
Cagiran: minik.py akisi."""

import json
import os
import time
import urllib.error
import urllib.request

from ortak import log
from ortak.ayar import (
    ALT_ESIK,
    KAFA_BAGLAM,
    KAFA_MAX_TOKEN,
    KAFA_MODEL_YOLU,
    KAFA_SICAKLIK,
    KAFA_TOP_P,
    KAFA_UC,
    KAFA_ZAMAN_ASIMI_SN,
    KORTIZOL_REPEAT_PENALTY_ARALIK,
    KORTIZOL_REPEAT_PENALTY_MIN,
    MELATONIN_YORGUN_MAX_TOKEN_CARPANI,
    MELATONIN_YORGUN_SICAKLIK_CARPANI,
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
# Onceki turun modu: cift esik (Schmitt tetikleyici) hafiza ister, tek surecli akis tek Kafa
# kullandigi icin modul seviyesinde tutuluyor (testler dogrudan sifirlayabilir, DEFTER_KLASORU
# gibi).
ONCEKI_MOD = MOD_UYANIK


def dusun(soru, baglam=None, hormon_degerleri=None):
    """Soruyu (varsa onceki mesajlarla birlikte) llama-server'a sorar, cevap metnini dondurur.
    hormon_degerleri verilirse ornekleme ayarlari ondan hesaplanir (kademe 1); verilmezse f0'in
    olctugu sabit ayarlar kullanilir. Sunucu cevap vermezse hatayi yutmaz, yukseltir."""
    basladi = time.perf_counter()
    mesajlar = list(baglam) if baglam else []
    mesajlar.append({"role": "user", "content": soru})
    ayarlar, mod = _ornekleme_ayarlari(hormon_degerleri)
    govde = _govde_olustur(mesajlar, ayarlar)
    try:
        cevap, token_sayisi = _sunucuya_sor(govde)
    except (urllib.error.URLError, OSError) as hata:
        log.yaz(YUVA_ADI, "dusun", _gecen_ms(basladi), "hata",
                {"hata": str(hata), "model": KAFA_MODEL_YOLU, "mod": mod, "ayarlar": ayarlar})
        raise
    log.yaz(YUVA_ADI, "dusun", _gecen_ms(basladi), "ok",
            {"token": token_sayisi, "baglam": KAFA_BAGLAM, "model": KAFA_MODEL_YOLU,
             "mod": mod, "ayarlar": ayarlar})
    return cevap


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


def _govde_olustur(mesajlar, ayarlar):
    """Istek govdesini hazirlar: ornekleme ayarlari hesaplanan sozlukten gelir, ciplak sayi yok."""
    return {"messages": mesajlar, **ayarlar}


def _sunucuya_sor(govde):
    """HTTP istegini yollar, (cevap_metni, token_sayisi) dondurur."""
    istek = urllib.request.Request(
        KAFA_UC,
        data=json.dumps(govde, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(istek, timeout=KAFA_ZAMAN_ASIMI_SN) as yanit:
        yanit_json = json.loads(yanit.read().decode("utf-8"))
    cevap = yanit_json["choices"][0]["message"]["content"]
    token_sayisi = yanit_json.get("usage", {}).get("completion_tokens", 0)
    return cevap, token_sayisi


def _gecen_ms(basladi):
    """Olcum baslangicindan bu yana gecen sureyi tam sayi milisaniye verir."""
    return int((time.perf_counter() - basladi) * 1000)
