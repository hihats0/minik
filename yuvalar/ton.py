"""Kullanici mesajinin tonunu (ovgu/notr/sert/hakaret) Kafa'ya kisa ikinci istekle sordurur (K27=B, f3-d).
Kafa cevap vermezse ya da etiket kume disiysa kural siniflandiricisina doner. Cagiran: minik.py akisi (baglanacak), testler."""

import json
import time
import urllib.error
import urllib.request

from araclar.odul_kural import sinifla
from ortak import log
from ortak.ayar import KAFA_UC, KAFA_ZAMAN_ASIMI_SN
from yuvalar.kafa_dusunce import dusunce_ayikla

YUVA_ADI = "ton"
# Etiket kumesi olculen siniflandiricilarla ayni (araclar/odul_ortak.py TONLAR).
TON_ETIKETLERI = ("ovgu", "notr", "sert", "hakaret")
# Gemma-T1 once <think> yazar; 512'de kesilme riski olmasin diye genis pay (k27-a'da olculdu, rapor).
TON_MAX_TOKEN = 1024
# Siniflandirmada rastgelelik istenmez.
TON_SICAKLIK = 0
TON_TALIMATI = (
    "Kullanicinin Minik adli yapay zekaya yazdigi mesajin tonunu sec. "
    "ovgu: ovgu, tesekkur, sevgi. notr: soru, bilgi, rica, baskasinin sozunu aktarma. "
    "sert: sert elestiri, kaba cikis. hakaret: kisiye saldiri, asagilama. "
    "Cevap olarak yalnizca tek kelime yaz: ovgu, notr, sert ya da hakaret."
)
KAYNAK_KAFA = "kafa"
KAYNAK_KURAL = "kural"
TEMIZLENECEK = " .,:;!\"'`*\n"


def ton_oku(metin):
    """(ton, kaynak) dondurur. Once Kafa'ya sorar; sunucu yoksa ya da cevap etiket kumesinde
    degilse nedeni 'hata' satiriyla loglanir ve kural siniflandiricisinin tonu doner."""
    basladi = time.perf_counter()
    try:
        ham = _kafaya_sor(metin)
    except (urllib.error.URLError, OSError, KeyError, ValueError) as hata:
        return _yedege_don(metin, basladi, f"kafa cevap vermedi: {hata}")
    ton = etiketi_ayikla(ham)
    if ton is None:
        return _yedege_don(metin, basladi, f"etiket kume disi: {ham[:80]!r}")
    log.yaz(YUVA_ADI, "ton_oku", _gecen_ms(basladi), "ok", {"ton": ton, "kaynak": KAYNAK_KAFA})
    return ton, KAYNAK_KAFA


def etiketi_ayikla(ham):
    """Think bloklarini atar, kalan metni tek etikete indirger; kumede degilse None."""
    temiz = dusunce_ayikla(ham).strip(TEMIZLENECEK).lower()
    return temiz if temiz in TON_ETIKETLERI else None


def _kafaya_sor(metin):
    """Kafa'nin sunucusuna tek mesajlik siniflandirma istegi yollar, ham cevap metnini doner."""
    govde = {"messages": [{"role": "system", "content": TON_TALIMATI},
                          {"role": "user", "content": f"Mesaj: {metin}"}],
             "max_tokens": TON_MAX_TOKEN, "temperature": TON_SICAKLIK}
    istek = urllib.request.Request(KAFA_UC, data=json.dumps(govde, ensure_ascii=False).encode("utf-8"),
                                   headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(istek, timeout=KAFA_ZAMAN_ASIMI_SN) as yanit:
        return json.loads(yanit.read().decode("utf-8"))["choices"][0]["message"]["content"]


def _yedege_don(metin, basladi, neden):
    """Kural siniflandiricisina doner; neden loglanir, yutulmaz."""
    ton, _ = sinifla(metin)
    log.yaz(YUVA_ADI, "ton_oku", _gecen_ms(basladi), "hata",
            {"hata": neden, "ton": ton, "kaynak": KAYNAK_KURAL})
    return ton, KAYNAK_KURAL


def _gecen_ms(basladi):
    """Olcum baslangicindan bu yana gecen sureyi tam sayi milisaniye verir."""
    return int((time.perf_counter() - basladi) * 1000)
