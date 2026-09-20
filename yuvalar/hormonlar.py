"""Yedi hormonu tutar ve olaylara gore gunceller. Bu sayilar Minik'in her karar noktasini surer.
Cagiran: minik.py akisi (henuz yok) ve araclar/hormon-gunu.py. Hicbir yuva bunu dogrudan cagirmaz (K1)."""

import time
from dataclasses import dataclass

from ortak import log

EN_AZ = 0.0
EN_COK = 100.0
EN_AZ_SIDDET = 0.0
EN_COK_SIDDET = 1.0
YUVA_ADI = "hormonlar"


@dataclass(frozen=True)
class Tanim:
    """Bir hormonun yasasi. Yedi hormonun tamami bu ayni bes sayiyla anlatilir."""

    dinlenme: float  # olay yokken donecegi deger
    yukselten: str  # bu olay olunca cikar
    yukselme: float  # siddet 1,0 iken kac puan cikar
    dusuren: str | None  # bu DAVRANIS olunca iner; None ise sadece zamanla soner
    dusme: float  # davranis olunca kac puan iner
    sonum: float  # her adimda dinlenmeye dogru kapanan oran


# Kaynak: reports/2026-09-20-hormon-mimarisi.md bolum 7 (tablo vault'ta yoktu, turetildi).
# Davranisa bagli ucunde (kortizol, melatonin, merak) sonum bilerek cok kucuk, dusme cok buyuk:
# beklemek hormonu indirmesin, indiren sey davranis olsun (Yigit'in karari).
HORMONLAR = {
    "dopamin": Tanim(20.0, "odul", 30.0, None, 0.0, 0.25),
    "noradrenalin": Tanim(20.0, "belirsizlik", 25.0, "tanidik", 20.0, 0.10),
    "serotonin": Tanim(50.0, "yolunda", 15.0, None, 0.0, 0.05),
    "kortizol": Tanim(10.0, "ceza", 35.0, "iyi_sey", 25.0, 0.01),
    "oksitosin": Tanim(30.0, "iyi_davranis", 12.0, None, 0.0, 0.02),
    # yukselme 1,5: 100 adimlik bir gunun sonunda ~90'a cikiyor ama tavana yapismiyor.
    # 3,0 denendi, 45. adimda 100'e vurup orada kaldi ve "ne kadar yorgun" bilgisi kayboldu.
    "melatonin": Tanim(10.0, "calisma", 1.5, "uyku", 80.0, 0.01),
    "merak": Tanim(40.0, "ogrenilebilir_sasirma", 20.0, "ogrendi", 30.0, 0.01),
}

OLAYLAR = frozenset(
    [t.yukselten for t in HORMONLAR.values()]
    + [t.dusuren for t in HORMONLAR.values() if t.dusuren]
)


class Hormonlar:
    """Yedi sayiyi tutar. Ilk surumde hormonlar birbirine BAGLI DEGIL: her biri yalniz kendi
    girdisinden beslenir. Gerekce raporda: yedi hormon birbirini etkilerse 42 bag olur ve
    "bu sayi neden boyle cikti" sorusunun cevabi kalmaz."""

    def __init__(self):
        self._deger = {ad: t.dinlenme for ad, t in HORMONLAR.items()}

    def oku(self):
        """O anki yedi sayiyi verir. Disariya kopya gider, icerideki sozluk korunur."""
        return dict(self._deger)

    def guncelle(self, olay=None, siddet=1.0):
        """Bir adim gecirir: once hepsi dinlenmeye dogru soner, sonra olay islenir.
        olay None ise sadece sonumleme olur. Bilinmeyen olay hata yukseltir, yutulmaz."""
        basladi = time.perf_counter()
        try:
            _dogrula(olay, siddet)
        except ValueError as hata:
            log.yaz(YUVA_ADI, "guncelle", _gecen_ms(basladi), "hata",
                    {"hata": str(hata), "olay": olay, "siddet": siddet})
            raise
        self._sondur()
        if olay is not None:
            self._olayi_isle(olay, siddet)
        log.yaz(YUVA_ADI, "guncelle", _gecen_ms(basladi), "ok",
                {"olay": olay, "siddet": siddet, "deger": self.oku()})
        return self.oku()

    def _sondur(self):
        """Her hormon dinlenme degerine dogru biraz kapanir. Taskin olamaz: aradaki farkin
        bir orani alindigi icin sonuc hep iki degerin arasinda kalir."""
        for ad, t in HORMONLAR.items():
            self._deger[ad] += (t.dinlenme - self._deger[ad]) * t.sonum

    def _olayi_isle(self, olay, siddet):
        """Olay hangi hormonun girdisiyse onu oynatir. Bir olay en fazla bir hormona dokunur."""
        for ad, t in HORMONLAR.items():
            if olay == t.yukselten:
                self._deger[ad] = _sinirla(self._deger[ad] + t.yukselme * siddet)
            elif olay == t.dusuren:
                self._deger[ad] = _sinirla(self._deger[ad] - t.dusme * siddet)


def _dogrula(olay, siddet):
    """Girdiyi kontrol eder. Yanlis girdi sessizce yok sayilmaz, hata olur."""
    if olay is not None and olay not in OLAYLAR:
        raise ValueError(f"bilinmeyen olay: {olay!r}. Taninan olaylar: {sorted(OLAYLAR)}")
    if not EN_AZ_SIDDET <= siddet <= EN_COK_SIDDET:
        raise ValueError(f"siddet {EN_AZ_SIDDET}-{EN_COK_SIDDET} arasinda olmali, gelen: {siddet}")


def _sinirla(deger):
    """Hormonu tanimli araliga hapseder."""
    return max(EN_AZ, min(EN_COK, deger))


def _gecen_ms(basladi):
    """Olcum baslangicindan bu yana gecen sureyi tam sayi milisaniye verir."""
    return int((time.perf_counter() - basladi) * 1000)
