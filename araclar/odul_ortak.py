"""Odul testi olcumlerinin ortak kismi: veri yukleme, dogruluk/kufur metrikleri, sure ozeti, sonuc dosyasi.
Cagiran: araclar/odul-olc-kural.py, odul-olc-gomme.py, odul-olc-llm.py.
"""

import json
import os
import statistics
from collections import Counter, defaultdict
from pathlib import Path

ARAC_KLASORU = Path(__file__).parent
VERI_YOLU = ARAC_KLASORU / "odul-testi.json"
TONLAR = ("ovgu", "notr", "sert", "hakaret")
OLUMSUZ_TONLAR = ("sert", "hakaret")
YUZDE_HANE = 1


def veri_yukle():
    """(test_listesi, referans_listesi) dondurur. Ortam degiskenleri bagimsiz dis veri kontrolu icindir:
    ODUL_TEST_DOSYASI test cumlelerini baska bir json'dan, ODUL_TEST_SAYISI ilk N tanesini alir."""
    with open(VERI_YOLU, encoding="utf-8") as f:
        veri = json.load(f)
    test = veri["test"]
    if os.environ.get("ODUL_TEST_DOSYASI"):
        with open(ARAC_KLASORU / os.environ["ODUL_TEST_DOSYASI"], encoding="utf-8") as f:
            test = json.load(f)["test"]
    return test[:int(os.environ.get("ODUL_TEST_SAYISI", len(test)))], veri["referans"]


def isaret(ton):
    """Odul isareti: ovgu / notr / olumsuz (sert ve hakaret birlestirilir). Hormon icin asil onemli olan bu."""
    return "olumsuz" if ton in OLUMSUZ_TONLAR else ton


def _yuzde(pay, payda):
    return round(100 * pay / payda, YUZDE_HANE) if payda else None


def kufur_karisikligi(testler, tahminler):
    """Kufur bayragi icin dogru-pozitif, yanlis-pozitif, yanlis-negatif, dogru-negatif sayilari."""
    say = Counter()
    for t, (_, kufur) in zip(testler, tahminler):
        durum = ("d" if kufur == t["kufur"] else "y") + ("p" if kufur else "n")
        say[durum] += 1
    return {"dogru_pozitif": say["dp"], "yanlis_pozitif": say["yp"],
            "yanlis_negatif": say["yn"], "dogru_negatif": say["dn"]}


def etiket_dokumu(testler, tahminler):
    """Her tuzak etiketi icin (kac cumle, ton dogru, kufur bayragi dogru) dondurur."""
    tablo = defaultdict(lambda: [0, 0, 0])
    for t, (ton, kufur) in zip(testler, tahminler):
        for etiket in t["tuzak"] or ["tuzaksiz"]:
            tablo[etiket][0] += 1
            tablo[etiket][1] += int(ton == t["ton"])
            tablo[etiket][2] += int(kufur == t["kufur"])
    return {e: {"n": v[0], "ton_dogru": v[1], "kufur_dogru": v[2]} for e, v in sorted(tablo.items())}


def metrik_hesapla(testler, tahminler):
    """Tum metrikleri tek sozlukte toplar. tahminler: testler ile ayni sirada (ton, kufur) listesi."""
    n = len(testler)
    ton_dogru = sum(t["ton"] == p[0] for t, p in zip(testler, tahminler))
    isaret_dogru = sum(isaret(t["ton"]) == isaret(p[0]) for t, p in zip(testler, tahminler))
    karisiklik = kufur_karisikligi(testler, tahminler)
    return {
        "n": n,
        "ton_dogruluk_yuzde": _yuzde(ton_dogru, n),
        "isaret_dogruluk_yuzde": _yuzde(isaret_dogru, n),
        "kufur": karisiklik,
        "kufur_dogruluk_yuzde": _yuzde(karisiklik["dogru_pozitif"] + karisiklik["dogru_negatif"], n),
        "etiket_dokumu": etiket_dokumu(testler, tahminler),
        "ton_karisikligi": ton_karisikligi(testler, tahminler),
        "hatalar": hata_listesi(testler, tahminler),
        "tahminler": {t["id"]: list(p) for t, p in zip(testler, tahminler)},
    }


def ton_karisikligi(testler, tahminler):
    """'gercek->tahmin' anahtariyla sayim, yalnizca hatalar."""
    say = Counter(f"{t['ton']}->{p[0]}" for t, p in zip(testler, tahminler) if t["ton"] != p[0])
    return dict(say.most_common())


def hata_listesi(testler, tahminler):
    return [{"id": t["id"], "metin": t["metin"], "gercek": [t["ton"], t["kufur"]], "tahmin": list(p)}
            for t, p in zip(testler, tahminler) if (t["ton"], t["kufur"]) != tuple(p)]


def sure_ozeti(sureler_ms):
    """Cumle basina sure: medyan, ortalama, en yavas (ms, 3 hane)."""
    s = sorted(sureler_ms)
    return {"medyan_ms": round(statistics.median(s), 3), "ortalama_ms": round(statistics.fmean(s), 3),
            "en_yavas_ms": round(s[-1], 3), "n": len(s)}


def sonuc_yaz(ad, metrik, sure, ek=None):
    """araclar/odul-sonuc-<ad>.json dosyasina yazar, ozet satirini ekrana basar."""
    cikti = {"yol": ad, "metrik": metrik, "sure": sure, **(ek or {})}
    yol = ARAC_KLASORU / f"odul-sonuc-{ad}.json"
    yol.write_text(json.dumps(cikti, ensure_ascii=False, indent=1), encoding="utf-8")
    k = metrik["kufur"]
    print(f"[{ad}] ton %{metrik['ton_dogruluk_yuzde']}  isaret %{metrik['isaret_dogruluk_yuzde']}  "
          f"kufur YP={k['yanlis_pozitif']} YN={k['yanlis_negatif']}  sure medyan {sure['medyan_ms']} ms  -> {yol.name}")
