"""Dis (gercek tweet) kontrol sonucunu ikili saldirgan/degil metrigine cevirir.
Cagiran: elle, `python araclar/odul-dis-degerlendir.py <ad> [<ad> ...]`; odul-sonuc-<ad>.json dosyalarini okur
(ODUL_TEST_DOSYASI=odul-dis-testi.json ile kosulmus olcumlerin ciktisi).
"""

import json
import sys

from odul_ortak import ARAC_KLASORU, YUZDE_HANE

ANA_KURAL = ("hakaret",)
GENIS_KURAL = ("sert", "hakaret")


def saldirgan_mi(tahmin, tonlar):
    """Ana kural: kufur bayragi ya da ton hakaret. Genis kural: sert de sayilir."""
    ton, kufur = tahmin
    return kufur == 1 or ton in tonlar


def ikili_metrik(altin, tahmin, tonlar):
    tp = sum(a and saldirgan_mi(tahmin[i], tonlar) for i, a in altin.items())
    fp = sum((not a) and saldirgan_mi(tahmin[i], tonlar) for i, a in altin.items())
    fn = sum(a and not saldirgan_mi(tahmin[i], tonlar) for i, a in altin.items())
    n = len(altin)
    kesinlik, duyarlilik = tp / (tp + fp) if tp + fp else 0, tp / (tp + fn) if tp + fn else 0
    f1 = 2 * kesinlik * duyarlilik / (kesinlik + duyarlilik) if kesinlik + duyarlilik else 0
    return {"dogruluk": round(100 * (n - fp - fn) / n, YUZDE_HANE), "kesinlik": round(100 * kesinlik, YUZDE_HANE),
            "duyarlilik": round(100 * duyarlilik, YUZDE_HANE), "f1": round(100 * f1, YUZDE_HANE), "n": n, "fp": fp, "fn": fn}


def main():
    with open(ARAC_KLASORU / "odul-dis-testi.json", encoding="utf-8") as f:
        altin_hepsi = {t["id"]: t["ton"] == "hakaret" for t in json.load(f)["test"]}
    for ad in sys.argv[1:]:
        with open(ARAC_KLASORU / f"odul-sonuc-{ad}.json", encoding="utf-8") as f:
            sonuc = json.load(f)
        tahmin = sonuc["metrik"]["tahminler"]
        altin = {i: altin_hepsi[i] for i in tahmin}
        print(ad, "ana", ikili_metrik(altin, tahmin, ANA_KURAL), "genis", ikili_metrik(altin, tahmin, GENIS_KURAL),
              "sure_ms", sonuc["sure"]["medyan_ms"])


if __name__ == "__main__":
    main()
