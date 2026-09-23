"""Yedi hormonu tutar ve olaylara gore gunceller. Bu sayilar Minik'in her karar noktasini surer.
Dosya verilirse (defter/hormon.json) baslarken okunur, her olayda yazilir; "uyku" olayi yasi 1 artirir.
Cagiran: minik.py akisi, yuvalar/uyku.py, araclar/hormon-gunu.py, araclar/hormon-yoksunluk-gunu.py.
Hicbir yuva bunu dogrudan cagirmaz (K1)."""

import json
import time
from dataclasses import dataclass

from ortak import log

EN_AZ = 0.0
EN_COK = 100.0
EN_AZ_SIDDET = 0.0
EN_COK_SIDDET = 1.0
YUVA_ADI = "hormonlar"
GECE_OLAYI = "uyku"  # bir gece gecti: yas (gece sayaci) bir artar


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
#
# K19 (2026-09-21, notes/kararlar-anlatimli.md Soru 4): "hicbir sey yapmamanin bedeli" var olan
# hormonlara baglandi, sekizinci satir acilmadi. Uc yoksunluktan biri (hicbir sey ogrenilmeyen
# gun) zaten var olan davranisin sonucu: "ogrendi" gelmezse merak zaten inmez, birikir, yeni kod
# gerekmedi. Diger ikisi asagida dusuren olarak eklendi. serotonin dusme=15 (yukselmeyle simetrik,
# TAHMIN) 30 gunluk kosuda ic tarafta bir dengeye oturuyor (~27,8), tavana/tabana degmiyor.
# oksitosin ILK denemede dusme=12 (simetrik) ile 5. gunde 0,0'a (taban) yapisti, gun 10 ile gun 30
# ayirt edilemez oldu (olculdu: araclar/hormon-yoksunluk-gunu.py). Melatoninin 45. adimda 100'e
# yapismasiyla ayni sinif kusur: TAHMIN yanlisti, dusuruldu. dusme=4.0 ile ic dengeye oturuyor
# (~18,4), taban 0'a degmiyor (bkz. reports/2026-09-21-f3a-hormon-revizyonu.md).
#
# K10 (2026-09-21, Yigit'in karari; f3-e 2026-09-22): melatonin artik soyut "calisma" sayaci
# degil, Kafa'nin llama-server'da harcadigi olculen is saniyesi (timings, ortak/kaynak_olc.py).
# Ilk surumdeki CPU saniyesi (process_time) harici sunucu isini goremedigi icin f3-e'de kaldirildi.
# "calisma" olay adi ve yukselme (1,5) DEGISMEDI: tek bicimlilik
# korunuyor (hormonlar.py hala sadece olay+siddet aliyor), degisen siddetin NEREDEN geldigi -
# cagiran taraf artik siddeti gercek is suresinden hesaplayip veriyor, elle 1,0 vermiyor.
# araclar/hormon-gunu.py ile olculdu: gercekci karisik is yukunde (hafif/orta/agir) gun sonu
# tepe 48,5, ne tavana (100) ne tabana yapisiyor; 1,5 katsayisi bu rejimde de gecerli kaldi,
# degistirilmedi (bkz. reports/2026-09-21-f3a-hormon-revizyonu.md).
HORMONLAR = {
    "dopamin": Tanim(20.0, "odul", 30.0, None, 0.0, 0.25),
    "noradrenalin": Tanim(20.0, "belirsizlik", 25.0, "tanidik", 20.0, 0.10),
    "serotonin": Tanim(50.0, "yolunda", 15.0, "hicbir_sey_uretilmedi", 15.0, 0.05),
    "kortizol": Tanim(10.0, "ceza", 35.0, "iyi_sey", 25.0, 0.01),
    "oksitosin": Tanim(30.0, "iyi_davranis", 12.0, "kimseyle_konusulmadi", 4.0, 0.02),
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

    def __init__(self, dosya=None):
        """dosya None ise kalicilik yok (testler, araclar). Dosya yoksa ya da bozuksa dinlenme
        degerleriyle ve yas 0 ile baslanir; bozuk dosya loglanir, yutulmaz."""
        self._dosya = dosya
        self._deger = {ad: t.dinlenme for ad, t in HORMONLAR.items()}
        self.yas = 0
        if dosya is not None and dosya.exists():
            self._dosyadan_yukle()

    def _dosyadan_yukle(self):
        """hormon.json'u okur. Bozuksa dinlenme degerlerinde kalir ve nedenini loglar."""
        try:
            veri = json.loads(self._dosya.read_text(encoding="utf-8"))
            deger = {ad: float(veri["deger"][ad]) for ad in HORMONLAR}
            yas = int(veri["yas"])
        except (OSError, ValueError, KeyError, TypeError) as hata:
            log.yaz(YUVA_ADI, "yukle", 0, "hata", {"hata": f"hormon.json okunamadi: {hata}"})
            return
        self._deger, self.yas = deger, yas

    def _dosyaya_yaz(self):
        """Durumu once gecici dosyaya yazip sonra degistirir: yarim yazilmis dosya kalmasin."""
        if self._dosya is None:
            return
        self._dosya.parent.mkdir(parents=True, exist_ok=True)
        gecici = self._dosya.with_suffix(".tmp")
        gecici.write_text(json.dumps({"deger": self._deger, "yas": self.yas}), encoding="utf-8")
        gecici.replace(self._dosya)

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
        if olay == GECE_OLAYI:
            self.yas += 1
        self._dosyaya_yaz()
        log.yaz(YUVA_ADI, "guncelle", _gecen_ms(basladi), "ok",
                {"olay": olay, "siddet": siddet, "deger": self.oku(), "yas": self.yas})
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
