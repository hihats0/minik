"""Calgicilar yuvasi (spec 3.3, f7): beyaz listeli hesabi Python yapar, iki yoldan dogrular, iz verir.
Cagiran: yuvalar/calgici_tani.py (minik.py akisi icin), tests/test_calgicilar.py."""

import ast
import operator
import time
from datetime import date
from fractions import Fraction

from ortak import log

YUVA_ADI = "calgicilar"
SASIRMA_OLAYI = "odul"  # hormonlar.py'de dopamini yukselten olay; sasirma dopamin olarak gelir
SASIRMA_SIDDETI = 1.0  # tahmin: tam bir odul kadar sasirma
TOLERANS = Fraction(1, 10**9)  # tahmin: float yolu ile kesir yolu bu farka kadar "ayni" sayilir
# Birimler temel birime carpan olarak: uzunluk m, kutle g, zaman sn.
BIRIMLER = {
    "mm": ("uzunluk", Fraction(1, 1000)), "cm": ("uzunluk", Fraction(1, 100)),
    "m": ("uzunluk", Fraction(1)), "km": ("uzunluk", Fraction(1000)),
    "g": ("kutle", Fraction(1)), "kg": ("kutle", Fraction(1000)),
    "sn": ("zaman", Fraction(1)), "dk": ("zaman", Fraction(60)), "saat": ("zaman", Fraction(3600)),
}
ISLEMLER = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}


def _yurut(dugum, sayi_yap):
    """ast agacini yalniz sayi, + - * / ve tekli eksiyle yurutur; baska her dugum ValueError."""
    if isinstance(dugum, ast.Constant) and type(dugum.value) in (int, float):
        return sayi_yap(dugum.value)
    if isinstance(dugum, ast.UnaryOp) and isinstance(dugum.op, ast.USub):
        return -_yurut(dugum.operand, sayi_yap)
    if isinstance(dugum, ast.BinOp) and type(dugum.op) in ISLEMLER:
        sol, sag = _yurut(dugum.left, sayi_yap), _yurut(dugum.right, sayi_yap)
        if isinstance(dugum.op, ast.Div) and sag == 0:
            raise ValueError("sifira bolme")
        return ISLEMLER[type(dugum.op)](sol, sag)
    raise ValueError(f"beyaz liste disi ifade parcasi: {type(dugum).__name__}")


def _agac(girdi):
    """Metni yalniz ayristirir (calistirmaz); agaci _yurut dolasir."""
    try:
        return ast.parse(str(girdi), mode="eval").body
    except SyntaxError as hata:
        raise ValueError(f"dort islem ayristirilamadi: {girdi!r}") from hata


def dort_islem_float(girdi):
    return float(_yurut(_agac(girdi), float))


def dort_islem_kesir(girdi):
    """Ikinci yol: ayni agac tam kesirle (Fraction) yurutulur, yuvarlama hatasi yok."""
    return _yurut(_agac(girdi), lambda sayi: Fraction(str(sayi)))


def _tarihler(girdi):
    parcalar = str(girdi).split()
    if len(parcalar) != 2:
        raise ValueError(f"tarih farki iki ISO tarih ister (YYYY-AA-GG YYYY-AA-GG): {girdi!r}")
    return date.fromisoformat(parcalar[0]), date.fromisoformat(parcalar[1])


def tarih_cikar(girdi):
    ilk, son = _tarihler(girdi)
    return (son - ilk).days


def tarih_ordinal(girdi):
    """Ikinci yol: takvim cikarmasi yerine gun sirasi (ordinal) farki."""
    ilk, son = _tarihler(girdi)
    return son.toordinal() - ilk.toordinal()


def _birim_girdisi(girdi):
    parcalar = str(girdi).split()
    if len(parcalar) != 3 or parcalar[1] not in BIRIMLER or parcalar[2] not in BIRIMLER:
        raise ValueError(f"birim cevirme 'deger kaynak hedef' ister, birimler {sorted(BIRIMLER)}: {girdi!r}")
    (tur1, carpan1), (tur2, carpan2) = BIRIMLER[parcalar[1]], BIRIMLER[parcalar[2]]
    if tur1 != tur2:
        raise ValueError(f"farkli turler cevrilemez: {tur1} -> {tur2}")
    return float(parcalar[0].replace(",", ".")), carpan1, carpan2


def birim_dogrudan(girdi):
    """Birinci yol: kaynak/hedef oranini tek carpan yapip float ile carpar."""
    deger, carpan1, carpan2 = _birim_girdisi(girdi)
    return deger * float(carpan1 / carpan2)


def birim_temelden(girdi):
    """Ikinci yol: once temel birime (m, g, sn) kesirle cikar, sonra hedefe iner."""
    deger, carpan1, carpan2 = _birim_girdisi(girdi)
    temel = Fraction(str(deger)) * carpan1
    return temel / carpan2


YOLLAR = {
    "dort_islem": (dort_islem_float, dort_islem_kesir),
    "tarih_farki": (tarih_cikar, tarih_ordinal),
    "birim_cevirme": (birim_dogrudan, birim_temelden),
}


def cal(gorev_tipi, girdi, hormon_durumu=None):
    """Sozlesme: (sonuc, iz). Iki yol ayrisirsa sasirma: dopamin olayi + log, sonuc None.
    Beyaz liste disi gorev ya da hatali girdide ValueError yukselir."""
    basladi = time.perf_counter()
    if gorev_tipi not in YOLLAR:
        raise ValueError(f"beyaz liste disi gorev: {gorev_tipi!r}, izinli: {sorted(YOLLAR)}")
    birinci, ikinci = YOLLAR[gorev_tipi]
    sonuc1, sonuc2 = birinci(girdi), ikinci(girdi)
    iz = [f"{birinci.__name__}({girdi!r}) = {sonuc1}", f"{ikinci.__name__}({girdi!r}) = {sonuc2}"]
    sonuc = sonuc1
    if abs(Fraction(sonuc1) - Fraction(sonuc2)) > TOLERANS:
        iz.append("sasirma: iki yol ayristi")
        sonuc = None
        _sasir(gorev_tipi, sonuc1, sonuc2, hormon_durumu)
    detay = {"gorev_tipi": gorev_tipi, "iz_uzunlugu": len(iz), "sonuc_tipi": type(sonuc).__name__}
    log.yaz(YUVA_ADI, "cal", int((time.perf_counter() - basladi) * 1000), "ok", detay)
    return sonuc, iz


def _sasir(gorev_tipi, sonuc1, sonuc2, hormon_durumu):
    """Ayrisma gorunur olsun: log satiri ve (verildiyse) Hormonlar'a dopamin olayi."""
    log.yaz(YUVA_ADI, "sasirma", 0, "ok", {"gorev_tipi": gorev_tipi, "yol1": str(sonuc1), "yol2": str(sonuc2)})
    if hormon_durumu is not None:
        hormon_durumu.guncelle(SASIRMA_OLAYI, SASIRMA_SIDDETI)
