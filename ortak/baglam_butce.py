"""Kafa'ya giden baglami token butcesinde tutar: asarsa en eski turlari (soru+cevap cifti)
dusurur, kac tur dustugunu loglar (f3-f). Cagiran: minik.py akisi (_tur_isle)."""

from ortak import log
from ortak.ayar import BAGLAM_KARAKTER_PER_TOKEN, BAGLAM_TOKEN_BUTCESI

YUVA_ADI = "akis"
TUR_MESAJ_SAYISI = 2  # bir tur = bir kullanici + bir asistan mesaji


def token_tahmini(mesajlar):
    """Mesaj listesinin token sayisini karakterden TAHMIN eder (sunucuya sorulmaz, ayar.py'deki
    olculmus orana emniyet payi konmus hali)."""
    karakter = sum(len(m["content"]) for m in mesajlar)
    return int(karakter / BAGLAM_KARAKTER_PER_TOKEN) + 1


def sinirla(baglam, soru, butce=BAGLAM_TOKEN_BUTCESI):
    """baglam + soru butceyi asiyorsa baglam'in basindan (en eski) turlari YERINDE siler.
    Soru (en yeni kullanici mesaji) hic dusmez; tek basina butceyi assa bile gonderilir ve
    bu durum hata satiriyla loglanir. Dusurulen tur sayisini dondurur."""
    yeni = {"role": "user", "content": soru}
    dusen = 0
    while baglam and token_tahmini(baglam + [yeni]) > butce:
        del baglam[:TUR_MESAJ_SAYISI]
        dusen += 1
    tahmin = token_tahmini(baglam + [yeni])
    if tahmin > butce:
        log.yaz(YUVA_ADI, "baglam_sinirla", 0, "hata",
                {"hata": "soru tek basina butceyi asiyor", "tahmin_token": tahmin, "butce": butce})
    elif dusen:
        log.yaz(YUVA_ADI, "baglam_sinirla", 0, "ok",
                {"dusen_tur": dusen, "kalan_tur": len(baglam) // TUR_MESAJ_SAYISI,
                 "tahmin_token": tahmin, "butce": butce})
    return dusen
