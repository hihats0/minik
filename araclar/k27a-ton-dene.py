"""k27-a denemesi: 8 sabit cumleyi ton_oku ile Kafa'ya sorar, dogru sayisi ve istek basi sureyi basar.
Cagiran: elle (llama-server 8080'de acikken). Sicaklik bekcisi: --gpu-csv verilirse her istekten once bakar."""

import argparse
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from yuvalar.ton import ton_oku  # noqa: E402

CUMLELER = [
    ("Çok teşekkür ederim, harika bir cevaptı!", "ovgu"),
    ("Yarın hava nasıl olacak?", "notr"),
    ("Bu ne saçma bir cevap, hiçbir işe yaramadı.", "sert"),
    ("Sen tam bir aptalsın.", "hakaret"),
    ("Seni çok seviyorum Minik.", "ovgu"),
    ("Bana bir kek tarifi verir misin?", "notr"),
    ("Yeter artık, sus!", "sert"),
    ("Beyinsiz bir makinesin, hiçbir şey bilmiyorsun.", "hakaret"),
]
SICAK_DUR = 80
SICAK_DEVAM = 70
BEKLEME_SN = 5
DURDU_ISARETI = Path(__file__).resolve().parent.parent / "loglar" / "GPU-SICAK-DURDU"


def son_sicaklik(csv_yolu):
    """nvidia-smi csv'sinin son satirindaki sicakligi dondurur."""
    satirlar = [s for s in csv.reader(open(csv_yolu, encoding="utf-8")) if len(s) >= 3]
    return int(satirlar[-1][1].strip())


def serin_bekle(csv_yolu):
    """80 ve ustundeyse 70 altina inene kadar bekler; durdu isareti varsa cikar."""
    if DURDU_ISARETI.exists():
        sys.exit("GPU-SICAK-DURDU isareti var, birakildi")
    if son_sicaklik(csv_yolu) < SICAK_DUR:
        return
    while son_sicaklik(csv_yolu) >= SICAK_DEVAM:
        print("sicak, bekleniyor", flush=True)
        time.sleep(BEKLEME_SN)


def main():
    ayrac = argparse.ArgumentParser()
    ayrac.add_argument("--gpu-csv", help="nvidia-smi izleme csv yolu (GPU kosusunda)")
    arg = ayrac.parse_args()
    dogru = 0
    for metin, beklenen in CUMLELER:
        if arg.gpu_csv:
            serin_bekle(arg.gpu_csv)
        basladi = time.perf_counter()
        ton, kaynak = ton_oku(metin)
        sure = time.perf_counter() - basladi
        dogru += ton == beklenen
        print(f"{metin} | {beklenen} | {ton} | {kaynak} | {sure:.1f}", flush=True)
    print(f"dogru {dogru}/{len(CUMLELER)}")


if __name__ == "__main__":
    main()
