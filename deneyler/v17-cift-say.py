"""V17 sayaci: defter/ altindaki gunluk jsonl kayitlarini platform alanina gore sayar, kacinin
egitim cifti olabilecegini (X disi) yazar. Cagiran: elle, `python deneyler/v17-cift-say.py`."""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # kok: ortak/, yuvalar/
from ortak.ayar import DEFTER_KLASORU
from yuvalar.buyume import x_kaynakli_mi

JSONL_DESENI = "gunluk-*.jsonl"
PLATFORMSIZ = "(platform yok)"


def say(klasor):
    """(platforma gore Counter, X disi kayit sayisi, dosya sayisi) dondurur."""
    sayim, x_disi, dosyalar = Counter(), 0, sorted(klasor.glob(JSONL_DESENI))
    for dosya in dosyalar:
        with dosya.open("r", encoding="utf-8") as f:
            for satir in f:
                if not satir.strip():
                    continue
                kayit = json.loads(satir)
                sayim[kayit.get("platform", PLATFORMSIZ)] += 1
                x_disi += not x_kaynakli_mi(kayit)
    return sayim, x_disi, len(dosyalar)


if __name__ == "__main__":
    sayim, x_disi, dosya_sayisi = say(Path(DEFTER_KLASORU))
    print(f"dosya: {dosya_sayisi}, kayit: {sum(sayim.values())}, platformlar: {dict(sayim)}")
    print(f"X disi (egitim cifti adayi, emniyetten once): {x_disi}")
