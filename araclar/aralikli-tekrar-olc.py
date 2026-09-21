"""Uyku'nun gece yukunu olcer: her aniyi her gece gozden gecirmek yerine SM-2 araliklariyla
gecikmeli gozden gecirmek kac islem ve kac dakika eder. Cagiran: elle, `python araclar/aralikli-tekrar-olc.py`."""

import random

GUN_SAYISI = 180  # yol haritasindaki 180 gecelik ufuk
GUNLUK_YENI = (8, 20, 75)  # devir notundaki gunluk kullanilabilir cift tahmini (alt, orta, ust)
TOHUM = 20260921
BASLANGIC_EF = 2.5  # SM-2'nin kolaylik carpani baslangici (super-memory.com/english/ol/sm2.htm)
EN_KUCUK_EF = 1.3
ILK_ARALIK = 1  # SM-2: I(1) = 1 gun
IKINCI_ARALIK = 6  # SM-2: I(2) = 6 gun
UNUTMA_OLASILIGI = 0.20  # bir gozden gecirmede hatirlayamama sansi (varsayim, olculmedi)
UNUTMA_SUPURMESI = (0.0, 0.10, 0.20, 0.35)  # tek varsayima yaslanmamak icin supurme
BUDAMA_SINIRI = 3  # toplam bu kadar kez unutulan ani atilir (Anki'deki "leech" kuralinin esi)
BUDAMASIZ = 10**9  # budama kapaliyken kullanilacak pratikte erisilmez sinir
BASARILI_KALITE = 4  # SM-2 q notu: hatirladi ama zorlandi
BASARISIZ_KALITE = 2
SANIYE_BASINA_ANI = 1.32  # olculdu: Qwen3.5-4B CPU cumle basi (reports/2026-09-21-odul-ve-gece-egitimi.md)
SANIYE_DAKIKA = 60.0
SON_PENCERE = 30  # kararli hale bakmak icin son kac gunun ortalamasi alinir


class Ani:
    """Tek bir aninin SM-2 durumu: kacinci tekrar, kolaylik carpani, bir sonraki gun."""

    def __init__(self, gun):
        self.tekrar = 0
        self.ef = BASLANGIC_EF
        self.sonraki_gun = gun + ILK_ARALIK
        self.basarisizlik = 0

    def gozden_gecir(self, gun, kalite):
        """SM-2 kuralini uygular ve bir sonraki gozden gecirme gununu belirler."""
        self.ef = _yeni_ef(self.ef, kalite)
        if kalite < BASARILI_KALITE:
            self.tekrar = 0
            self.basarisizlik += 1
            aralik = ILK_ARALIK
        else:
            self.tekrar += 1
            aralik = _aralik(self.tekrar, self.ef)
        self.sonraki_gun = gun + aralik


def _yeni_ef(ef, kalite):
    """SM-2 kolaylik carpani guncellemesi; EN_KUCUK_EF altina inemez."""
    fark = 5 - kalite
    return max(EN_KUCUK_EF, ef + (0.1 - fark * (0.08 + fark * 0.02)))


def _aralik(tekrar, ef):
    """SM-2 aralik merdiveni: 1 gun, 6 gun, sonra her seferinde EF ile carpilir."""
    if tekrar <= 1:
        return ILK_ARALIK
    if tekrar == 2:
        return IKINCI_ARALIK
    aralik = IKINCI_ARALIK
    for _ in range(tekrar - 2):
        aralik = int(round(aralik * ef))
    return aralik


def kos(gunluk_yeni, unutma=UNUTMA_OLASILIGI, budama=BUDAMASIZ, tohum=TOHUM):
    """GUN_SAYISI gece boyunca SM-2 takvimini isletir, gece basina gozden gecirme sayisini dondurur."""
    rastgele = random.Random(tohum)
    aniler = []
    gecelik = []
    budanan = 0
    for gun in range(1, GUN_SAYISI + 1):
        aniler.extend(Ani(gun) for _ in range(gunluk_yeni))
        gunun_isi = [a for a in aniler if a.sonraki_gun == gun]
        for ani in gunun_isi:
            hatirladi = rastgele.random() >= unutma
            ani.gozden_gecir(gun, BASARILI_KALITE if hatirladi else BASARISIZ_KALITE)
        atilacak = [a for a in aniler if a.basarisizlik >= budama]
        budanan += len(atilacak)
        aniler = [a for a in aniler if a.basarisizlik < budama]
        gecelik.append(len(gunun_isi))
    return gecelik, len(aniler) + budanan, budanan


def _naif_yuk(gunluk_yeni):
    """Karsilastirma tabani: her gece o ana kadar biriken butun anilari gozden gecirmek."""
    return sum(gun * gunluk_yeni for gun in range(1, GUN_SAYISI + 1))


def _satiri_bas(etiket, gecelik, toplam_ani, budanan, gunluk_yeni):
    """Tek bir kosunun sonuc satirini basar."""
    toplam = sum(gecelik)
    son = gecelik[-SON_PENCERE:]
    ortalama = sum(son) / len(son)
    dakika = ortalama * SANIYE_BASINA_ANI / SANIYE_DAKIKA
    naif = _naif_yuk(gunluk_yeni)
    print(f"{etiket:<14}{toplam_ani:>8}{budanan:>9}{toplam:>10}{max(gecelik):>8}"
          f"{ortalama:>11.1f}{dakika:>9.1f}{naif / toplam:>9.1f}x")


def _hacim_tablosu():
    """Gunluk yeni ani sayisini degistirerek gece yukunu olcer (budama kapali)."""
    print(f"\nA) Hacim: unutma {UNUTMA_OLASILIGI:.0%}, budama kapali")
    _basligi_bas("yeni/gun")
    for gunluk_yeni in GUNLUK_YENI:
        gecelik, toplam_ani, budanan = kos(gunluk_yeni)
        _satiri_bas(str(gunluk_yeni), gecelik, toplam_ani, budanan, gunluk_yeni)


def _unutma_tablosu(gunluk_yeni):
    """Unutma olasiligini supurur: gece yukunun hangi varsayima yaslandigini gosterir."""
    print(f"\nB) Unutma supurmesi: {gunluk_yeni} yeni/gun, budama kapali")
    _basligi_bas("unutma")
    for unutma in UNUTMA_SUPURMESI:
        gecelik, toplam_ani, budanan = kos(gunluk_yeni, unutma=unutma)
        _satiri_bas(f"{unutma:.0%}", gecelik, toplam_ani, budanan, gunluk_yeni)


def _budama_tablosu(gunluk_yeni):
    """Toplamda BUDAMA_SINIRI kez unutulan aniyi atmanin gece yukune etkisi."""
    print(f"\nC) Budama: {gunluk_yeni} yeni/gun, unutma {UNUTMA_OLASILIGI:.0%}")
    _basligi_bas("budama siniri")
    for sinir in (BUDAMASIZ, BUDAMA_SINIRI + 1, BUDAMA_SINIRI):
        gecelik, toplam_ani, budanan = kos(gunluk_yeni, budama=sinir)
        etiket = "yok" if sinir == BUDAMASIZ else str(sinir)
        _satiri_bas(etiket, gecelik, toplam_ani, budanan, gunluk_yeni)


def _basligi_bas(ilk_sutun):
    """Tablo basligi."""
    print(f"{ilk_sutun:<14}{'ani':>8}{'budanan':>9}{'toplam':>10}{'zirve':>8}"
          f"{'son30':>11}{'dakika':>9}{'naife':>10}")
    print("-" * 79)


def olc():
    """Uc tabloyu da kosturur. Hata yutulmaz, yukselir."""
    print(f"SM-2 takvimi, {GUN_SAYISI} gece, tohum {TOHUM}, "
          f"dakika = son 30 gece ort. x {SANIYE_BASINA_ANI} sn (olculmus 4B CPU)")
    _hacim_tablosu()
    orta = GUNLUK_YENI[1]
    _unutma_tablosu(orta)
    _budama_tablosu(orta)


if __name__ == "__main__":
    olc()
