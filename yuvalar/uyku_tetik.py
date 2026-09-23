"""Uyku tetiginin karari: melatonin + saat egilimi (Borbely surec C) cift esigi gecince "uyu" der.
Karar burada verilir, akis yalniz sorar (K6). Cagiran: minik.py akisi, testler."""

import math

from ortak.ayar import C_GENLIK, C_TEPE_SAAT, GUN_SAAT, UYKU_ALT_ESIK, UYKU_UST_ESIK


def saat_egilimi(saat):
    """Gunun saatine gore uyku egilimi: 04'te +C_GENLIK, 16'da -C_GENLIK (spec 3.6.1)."""
    return C_GENLIK * math.cos(2 * math.pi * (saat - C_TEPE_SAAT) / GUN_SAAT)


class UykuTetigi:
    """Cift esik (Schmitt tetikleyici, spec 3.6.2): basinc UST'u gecince uykulu olur, ALT'in
    altina inene kadar oyle kalir. Boylece esik cevresinde titreyen basinc tek tetik uretir."""

    def __init__(self):
        self.uykulu = False

    def uyumali_mi(self, melatonin, saat):
        """Yalniz uyaniktan uykuluya GECISTE True doner: bir yorgunluk dalgasi bir gece demek."""
        basinc = melatonin + saat_egilimi(saat)
        if not self.uykulu and basinc > UYKU_UST_ESIK:
            self.uykulu = True
            return True
        if self.uykulu and basinc < UYKU_ALT_ESIK:
            self.uykulu = False
        return False
