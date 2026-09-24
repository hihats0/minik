"""f3d olcumunun saf hesaplari: p95 sure ve 80/70 C duraklama karari.
Cagiran: araclar/f3d-ton-gpu.py, tests/test_f3d_ortak.py.
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ortak.gpu_sicaklik import DEVAM_ESIGI_C, DURAK_ESIGI_C  # noqa: E402

# Esikler ortak/gpu_sicaklik.py'de tek yerde (sicak-a).
DURAKLA_C = DURAK_ESIGI_C
DEVAM_C = DEVAM_ESIGI_C
YUZDELIK = 0.95


def p95(sureler):
    """En yakin sira yontemi: siralanmis listenin %95'lik elemani."""
    s = sorted(sureler)
    return s[math.ceil(YUZDELIK * len(s)) - 1]


def sicaklik_durumu(sicaklik, duraklatildi):
    """Duraklatilmali mi? 80'de durur, 70'e inene kadar durur (arada eski durum korunur)."""
    if sicaklik >= DURAKLA_C:
        return True
    if sicaklik <= DEVAM_C:
        return False
    return duraklatildi
