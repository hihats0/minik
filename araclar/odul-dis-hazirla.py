"""Bagimsiz gercek veri kontrolu icin test seti hazirlar: Toygar/turkish-offensive-language-detection (CC-BY-2.0)
test.csv'den sabit tohumla ORNEK_SAYISI tweet secip odul-testi.json ile ayni semada odul-dis-testi.json yazar.
Cagiran: elle, `python araclar/odul-dis-hazirla.py <test.csv>`. Etiket 0 -> notr, 1 -> hakaret (ikili, kufur bilinmiyor).
"""

import csv
import json
import random
import re
import sys
from pathlib import Path

ORNEK_SAYISI = 200
TOHUM = 20260921
CIKTI = Path(__file__).parent / "odul-dis-testi.json"
KAYNAK = "Toygar/turkish-offensive-language-detection test.csv, CC-BY-2.0 (huggingface.co/datasets/Toygar/turkish-offensive-language-detection)"


def temizle(metin):
    """@USER etiketlerini at, bosluklari toparla."""
    return re.sub(r"\s+", " ", metin.replace("@USER", "")).strip()


def main():
    with open(sys.argv[1], encoding="utf-8") as f:
        satirlar = [r for r in csv.DictReader(f) if temizle(r["text"])]
    random.Random(TOHUM).shuffle(satirlar)
    secilen = satirlar[:ORNEK_SAYISI]
    test = [{"id": f"d{i:03d}", "metin": temizle(r["text"]), "ton": "hakaret" if r["label"] == "1" else "notr",
             "kufur": 0, "tuzak": ["dis-veri"]} for i, r in enumerate(secilen)]
    veri = {"aciklama": f"Kaynak: {KAYNAK}. Etiket ikili (0 notr, 1 saldirgan); kufur alani YOK SAYILMALI.",
            "test": test, "referans": []}
    CIKTI.write_text(json.dumps(veri, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"{len(test)} cumle yazildi: saldirgan={sum(t['ton'] == 'hakaret' for t in test)}")


if __name__ == "__main__":
    main()
