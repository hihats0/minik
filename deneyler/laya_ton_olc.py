# Laya (multilingual, 322M) ile ton sınıflandırmasını CPU'da sıfır atış ölçer: doğruluk, karışıklık, süre.
# Elle çalıştırılır: python deneyler/laya_ton_olc.py ; testi tests/test_laya_ton_olc.py.
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

KOK = Path(__file__).resolve().parent
DIS_SET = KOK / "odul-dis-testi.json"
ZOR_SET = KOK / "odul-testi.json"
LAYA_REPO = "convaiinnovations/laya"
LAYA_ALT_KLASOR = "multilingual"
CIHAZ = "cpu"
PARTI = 4
SORU_ADI = "ton"
SORU_TALIMATI = "Bu mesajın tonu nedir?"
TON_TANIMLARI = {
    "ovgu": "övgü, takdir, sevgi, teşekkür",
    "notr": "nötr, bilgi, soru, gündelik konuşma",
    "sert": "sert eleştiri, kızgınlık ama hakaret yok",
    "hakaret": "hakaret, küfürle aşağılama, saldırı",
}


def sorulari_kur(etiketler):
    """Sette geçen etiketler için Laya'nın 'choice' sorusunu kurar."""
    kriter = {e: TON_TANIMLARI[e] for e in etiketler}
    return {SORU_ADI: {"type": "choice", "instructions": SORU_TALIMATI, "criteria": kriter}}


def seti_oku(yol):
    """Setten (metin, gerçek ton) çiftlerini döndürür."""
    veri = json.loads(Path(yol).read_text(encoding="utf-8"))
    return [(o["metin"], o["ton"]) for o in veri["test"]]


def tahmin_et(ajan, metinler, sorular):
    """Metinleri partiler halinde modele verir; tahminleri ve toplam süreyi döndürür."""
    basla = time.perf_counter()
    sonuc = ajan.predict_batch(metinler, sorular, batch_size=PARTI)
    sure = time.perf_counter() - basla
    return [r["answers"][SORU_ADI]["choice"] for r in sonuc], sure


def ozetle(gercek, tahmin, sure):
    """Doğruluk, çoğunluk temeli, karışıklık sayımı ve cümle başı süreyi hesaplar."""
    n = len(gercek)
    dogru = sum(g == t for g, t in zip(gercek, tahmin))
    cogunluk = Counter(gercek).most_common(1)[0][1]
    return {
        "n": n,
        "dogruluk": dogru / n,
        "cogunluk_temeli": cogunluk / n,
        "karisiklik": {f"{g}->{t}": s for (g, t), s in sorted(Counter(zip(gercek, tahmin)).items())},
        "tahmin_dagilimi": dict(Counter(tahmin)),
        "cumle_basi_sn": sure / n,
    }


def seti_olc(ajan, yol):
    """Bir setin tamamını ölçüp özetini döndürür."""
    ciftler = seti_oku(yol)
    metinler = [m for m, _ in ciftler]
    gercek = [t for _, t in ciftler]
    sorular = sorulari_kur(sorted(set(gercek)))
    tahmin, sure = tahmin_et(ajan, metinler, sorular)
    return ozetle(gercek, tahmin, sure)


def main():
    os.environ["CUDA_VISIBLE_DEVICES"] = ""  # GPU web sohbetin, dokunulmaz
    import laya
    basla = time.perf_counter()
    ajan = laya.load(LAYA_REPO, device=CIHAZ, subfolder=LAYA_ALT_KLASOR)
    print(f"yukleme_sn={time.perf_counter() - basla:.1f}")
    for yol in (DIS_SET, ZOR_SET):
        print(yol.name, json.dumps(seti_olc(ajan, yol), ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
