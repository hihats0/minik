"""Bekci'nin kufur sozlugu ile olcum aracinin sozlugunun ayni kalmasini bekler.
Cagiran: unittest discover (tests/)."""

import importlib.util
import sys
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from ortak.ayar import BEKCI_KARAKTER_KALIPLARI

OLCUM_ARACI = KOK / "araclar" / "odul_kural.py"


def _olcum_aracini_yukle():
    """Olcum aracini dosya yolundan yukler: `araclar/` paket degil, normal import calismaz."""
    tanim = importlib.util.spec_from_file_location("odul_kural", OLCUM_ARACI)
    modul = importlib.util.module_from_spec(tanim)
    tanim.loader.exec_module(modul)
    return modul


class SozlukTutarliligi(unittest.TestCase):
    """Sozluk iki yerde duruyor: `ortak/ayar.py` (Bekci kullanir) ve `araclar/odul_kural.py`
    (olcum araci kullanir, yalniz standart kutuphane olsun diye kopyalandi). Kopya kacinilmaz
    ama sessiz ayrisma kacinilir: bu test ayrisirsa kirmizi yanar.

    Ayrisma neden pahali: Bekci'nin kapisi ile olculmus %80,5 dogruluk sayisi ayni sozluge
    dayaniyor (reports/2026-09-21-odul-ve-gece-egitimi.md). Listeler ayrisirsa rapordaki sayi
    artik Bekci'yi tarif etmiyor, ama hicbir sey kirilmadigi icin kimse fark etmiyor.
    """

    def test_iki_sozluk_birebir_ayni(self):
        olcum = _olcum_aracini_yukle()
        self.assertEqual(
            list(BEKCI_KARAKTER_KALIPLARI),
            list(olcum.KUFUR_KALIPLARI),
            "Sozlukler ayrismis. Birini degistirdiysen digerini de guncelle ya da bilerek "
            "ayirdiysan bu testi gerekcesiyle degistir; sessizce ayrismasina izin verme.",
        )
