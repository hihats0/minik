"""Fikir 61 (hece ortak birimi) CPU olcumu: kelime basina hece tokeni (tr16k ile ayni 1000 cumlede),
hece tipi sayisi ve en sik 16k hecenin kapsamasi. Cagiran: elle `PYTHONPATH=. python araclar/hece_olc.py`.
"""

import collections
import itertools
import json

from cocuk import egit_araclari as ea
from cocuk.hece import metni_hecele

ORNEK_SATIR = 200_000  # egitim metninin ilk 200 bin paragrafi (~8M kelime)
SOZLUK = 16_000


def main():
    sayac, kelime = collections.Counter(), 0
    with open(ea.VERI_DIZINI / "egitim.txt", encoding="utf-8") as f:
        for satir in itertools.islice(f, ORNEK_SATIR):
            sayac.update(metni_hecele(satir))
            kelime += len(satir.split())
    toplam = sum(sayac.values())
    kapsanan = sum(n for _, n in sayac.most_common(SOZLUK))
    sonuc = {"kelime": kelime, "hece_token": toplam, "token_kelime": round(toplam / kelime, 3),
             "hece_tipi": len(sayac), "ilk16k_kapsama": round(kapsanan / toplam, 5),
             "tr16k_token_kelime": json.loads((ea.VERI_DIZINI / "fertility.json").read_text("utf-8"))}
    print(json.dumps(sonuc, ensure_ascii=False))


if __name__ == "__main__":
    main()
