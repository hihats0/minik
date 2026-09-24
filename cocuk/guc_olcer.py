"""Az-veri deneyi: egitim boyunca GPU gucunu nvidia-smi'den saniyede bir okur, enerjiyi (Wh)
toplar. Cagiran: cocuk/az_egit.py (with GucOlcer() as olcer: ...).
"""

import logging
import subprocess
import threading
import time

ARALIK_SN = 1.0
SANIYE_SAAT = 3600.0
GUC_SORGU = ["nvidia-smi", "--query-gpu=power.draw", "--format=csv,noheader,nounits", "-i", "0"]

log = logging.getLogger("guc")


def guc_oku() -> float | None:
    try:
        cikti = subprocess.run(GUC_SORGU, capture_output=True, text=True, check=True).stdout
        return float(cikti.strip())
    except (OSError, subprocess.CalledProcessError, ValueError) as hata:
        log.warning("guc okunamadi: %s", hata)
        return None


def enerji_wh(ornekler: list[tuple[float, float]]) -> float:
    """(zaman_sn, watt) orneklerinden yamuk kuraliyla Wh."""
    toplam = 0.0
    for (t0, w0), (t1, w1) in zip(ornekler, ornekler[1:]):
        toplam += (w0 + w1) / 2 * (t1 - t0)
    return toplam / SANIYE_SAAT


class GucOlcer:
    """Arka plan is parcacigi; `wh` ve `ort_watt` cikista doldurulur."""

    def __init__(self, okuyucu=guc_oku, aralik=ARALIK_SN):
        self.okuyucu, self.aralik = okuyucu, aralik
        self.ornekler, self.okunamayan = [], 0
        self._dur = threading.Event()

    def _dongu(self):
        while not self._dur.is_set():
            watt = self.okuyucu()
            if watt is None:
                self.okunamayan += 1
            else:
                self.ornekler.append((time.time(), watt))
            self._dur.wait(self.aralik)

    def __enter__(self):
        self._is = threading.Thread(target=self._dongu, daemon=True)
        self._is.start()
        return self

    def __exit__(self, *_):
        self._dur.set()
        self._is.join()
        self.wh = enerji_wh(self.ornekler)
        watt = [w for _, w in self.ornekler]
        self.ort_watt = sum(watt) / len(watt) if watt else None
