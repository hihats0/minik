"""f3-g: f3-c3'un ayni 30 soru x 2 mod x 8 tohum uretimini yorgun talimatli yeni Kafa ile tekrarlar;
cikti reports/f3g-kor-olcum/ altina gider (f3-c3 sonuclari ezilmez). Cagiran: elle ya da Start-Process."""

import importlib.util
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent

# f3-c3 betigi kopyalanmaz, yuklenir; yalniz cikti ve sunucu log yollari degisir.
_OZELLIK = importlib.util.spec_from_file_location("f3c3", KOK / "araclar" / "f3c3-kor-uretim.py")
f3c3 = importlib.util.module_from_spec(_OZELLIK)
_OZELLIK.loader.exec_module(f3c3)
f3c3.CIKTI_KLASORU = KOK / "reports" / "f3g-kor-olcum"
f3c3.f3c1.SUNUCU_LOG = KOK / "araclar" / "sunucu-loglari" / "f3g-sunucu.log"

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    f3c3.main()
