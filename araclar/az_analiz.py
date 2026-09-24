"""Az-veri deneyinin analizi: az_sonuclar.jsonl'daki kollari tohum ortalamasi +- sapma ile tabloya
doker, her kolu AdamW tabanina Welch t-testiyle (iki yonlu) karsilastirir, ana olculerde Holm duzeltir.
Kesin permutasyon 3'e 3'te en kucuk p=0,1 verir, anlamliliga hic ulasamaz; o yuzden t-testi.
Cagiran: elle `python araclar/az_analiz.py`; cikti ekrana (rapora yapistirilir) ve az_analiz.json.
"""

import json
import math
import statistics
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
SONUCLAR = KOK / "cocuk" / "agirlik" / "az_sonuclar.jsonl"
CIKTI = KOK / "cocuk" / "agirlik" / "az_analiz.json"
TABAN = "adamw"
ANA_OLCULER = ("bpc", "ciftler", "eski_sinav", "enerji_wh")  # Holm ailesi
INTEGRAL_ADIMI = 2000
OLCULER = {  # ad: sonuc satirindan deger cikaran fonksiyon
    "bpc": lambda s: s["olcum"]["bpc"],  # farkli sozluklu kollari kiyaslayan tek ortak olcu
    "dogrulama_kaybi": lambda s: s["olcum"]["dogrulama_kaybi"],
    "ciftler": lambda s: s["olcum"]["dilbilgisi_ciftleri"]["toplam_logp"]["hepsi"],
    "eski_sinav": lambda s: s["olcum"]["eski_sinav"]["dogru"],
    "rakamli_tamamlama": lambda s: s["olcum"]["tamamlama"]["rakamli"],
    "cumle_bitti": lambda s: s["olcum"]["tamamlama"]["cumle_bitti"],
    "gercek_kelime": lambda s: s["olcum"]["tamamlama"]["gercek_kelime_orani"],
    "egitim_sn": lambda s: s["egitim"]["sure_sn"],
    "enerji_wh": lambda s: s["egitim"]["enerji_wh"],
}


def t_yogunluk(x: float, sd: float) -> float:
    sabit = math.gamma((sd + 1) / 2) / (math.sqrt(sd * math.pi) * math.gamma(sd / 2))
    return sabit * (1 + x * x / sd) ** (-(sd + 1) / 2)


def welch_p(a: list, b: list) -> float:
    """Iki yonlu Welch t-testi; t dagilimi Simpson integraliyle (scipy kurulu degil)."""
    va, vb = statistics.variance(a) / len(a), statistics.variance(b) / len(b)
    if va + vb == 0:
        return 0.0 if statistics.mean(a) != statistics.mean(b) else 1.0
    t = abs(statistics.mean(a) - statistics.mean(b)) / math.sqrt(va + vb)
    sd = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1))
    h = t / INTEGRAL_ADIMI
    alan = t_yogunluk(0, sd) + t_yogunluk(t, sd)
    alan += sum((4 if i % 2 else 2) * t_yogunluk(i * h, sd) for i in range(1, INTEGRAL_ADIMI))
    return max(0.0, 1 - 2 * alan * h / 3)


def holm(p_ler: dict) -> dict:
    """Holm-Bonferroni: kucukten buyuge p x (kalan sayi), tekduze artacak sekilde."""
    sirali = sorted(p_ler.items(), key=lambda kv: kv[1])
    duzeltilmis, en_buyuk = {}, 0.0
    for i, (ad, p) in enumerate(sirali):
        en_buyuk = max(en_buyuk, min(1.0, p * (len(sirali) - i)))
        duzeltilmis[ad] = en_buyuk
    return duzeltilmis


def kollara_ayir(satirlar: list) -> dict:
    kollar = {}
    for s in satirlar:
        kollar.setdefault(s["kol"], []).append(s)
    return kollar


def ozet(kollar: dict) -> dict:
    tablo = {}
    for kol, satirlar in kollar.items():
        tablo[kol] = {"n": len(satirlar)}
        for olcu, al in OLCULER.items():
            degerler = [al(s) for s in satirlar]
            sapma = statistics.stdev(degerler) if len(degerler) > 1 else 0.0
            tablo[kol][olcu] = {"ort": statistics.mean(degerler), "sapma": sapma, "degerler": degerler}
    return tablo


def karsilastir(tablo: dict) -> dict:
    """Taban disindaki her kol x olcu icin ham ve Holm duzeltilmis p."""
    ham = {}
    for kol in tablo:
        if kol == TABAN or tablo[kol]["n"] < 2 or tablo.get(TABAN, {}).get("n", 0) < 2:
            continue
        for olcu in OLCULER:
            ham[f"{kol}:{olcu}"] = welch_p(tablo[kol][olcu]["degerler"],
                                                  tablo[TABAN][olcu]["degerler"])
    ana = {k: p for k, p in ham.items() if k.split(":")[1] in ANA_OLCULER}
    return {"ham": ham, "holm": holm(ana)}


def guncel_olcum(satir: dict) -> dict:
    """Koşudan sonra yeniden olculmus olabilir (ör. BPC sonradan eklendi): dosyadaki olcum esas."""
    dosya = SONUCLAR.parent / satir["ad"] / "az_olcum.json"
    if dosya.exists():
        satir["olcum"] = json.loads(dosya.read_text("utf-8"))
    return satir


def main():
    satirlar = [guncel_olcum(json.loads(s)) for s in SONUCLAR.read_text("utf-8").splitlines() if s.strip()]
    tablo = ozet(kollara_ayir(satirlar))
    sonuc = {"tablo": tablo, "testler": karsilastir(tablo)}
    CIKTI.write_text(json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    for kol, satir in tablo.items():
        hucreler = [f"{o} {v['ort']:.3f}±{v['sapma']:.3f}" for o, v in satir.items() if o != "n"]
        print(kol, f"n={satir['n']}", " | ".join(hucreler))
    for ad, p in sonuc["testler"]["ham"].items():
        holm_p = sonuc["testler"]["holm"].get(ad)
        print(f"{ad}: p={p:.4f}" + (f" holm={holm_p:.4f}" if holm_p is not None else " (ikincil)"))


if __name__ == "__main__":
    main()
