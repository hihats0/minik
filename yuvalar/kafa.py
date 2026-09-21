"""llama-server'in OpenAI uyumlu ucuna sorar, cevap metnini dondurur, sureyi loglar.
Cagiran: minik.py akisi."""

import json
import time
import urllib.error
import urllib.request

from ortak import log
from ortak.ayar import (
    KAFA_BAGLAM,
    KAFA_MAX_TOKEN,
    KAFA_MODEL_YOLU,
    KAFA_SICAKLIK,
    KAFA_TOP_P,
    KAFA_UC,
    KAFA_ZAMAN_ASIMI_SN,
)

YUVA_ADI = "kafa"


def dusun(soru, baglam=None):
    """Soruyu (varsa onceki mesajlarla birlikte) llama-server'a sorar, cevap metnini dondurur.
    Sunucu cevap vermezse hatayi yutmaz, yukseltir; akis bunu yakalar."""
    basladi = time.perf_counter()
    mesajlar = list(baglam) if baglam else []
    mesajlar.append({"role": "user", "content": soru})
    govde = _govde_olustur(mesajlar)
    try:
        cevap, token_sayisi = _sunucuya_sor(govde)
    except (urllib.error.URLError, OSError) as hata:
        log.yaz(YUVA_ADI, "dusun", _gecen_ms(basladi), "hata",
                {"hata": str(hata), "model": KAFA_MODEL_YOLU})
        raise
    log.yaz(YUVA_ADI, "dusun", _gecen_ms(basladi), "ok",
            {"token": token_sayisi, "baglam": KAFA_BAGLAM, "model": KAFA_MODEL_YOLU})
    return cevap


def _govde_olustur(mesajlar):
    """Istek govdesini hazirlar: ornekleme ayarlari sabitten gelir, ciplak sayi yok."""
    return {
        "messages": mesajlar,
        "temperature": KAFA_SICAKLIK,
        "top_p": KAFA_TOP_P,
        "max_tokens": KAFA_MAX_TOKEN,
    }


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
