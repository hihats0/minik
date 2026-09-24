"""Hormon degerlerini Kafa'nin sistem mesajina girecek Turkce duygu cumlelerine cevirir (duygu-a).
Cagiran: yuvalar/kafa.py _sistem_mesaji_ekle. Melatonin burada yok: yorgun cumlesi kafa.py'de."""

# Esikler TAHMIN: olculmedi, dinlenme degerlerine (yuvalar/hormonlar.py) gore secildi.
# Dinlenme: dopamin 20, oksitosin 30, kortizol 10, merak 40. Normal aralikta cumle yok.
DOPAMIN_YUKSEK_ESIK = 45.0  # TAHMIN
DOPAMIN_DUSUK_ESIK = 8.0  # TAHMIN
OKSITOSIN_YUKSEK_ESIK = 45.0  # TAHMIN
KORTIZOL_YUKSEK_ESIK = 40.0  # TAHMIN
MERAK_YUKSEK_ESIK = 65.0  # TAHMIN

# (hormon, yon, esik, cumle). yon "ust": deger >= esik; "alt": deger <= esik.
DUYGU_TABLOSU = [
    ("dopamin", "ust", DOPAMIN_YUKSEK_ESIK, "Keyfin yerinde, neselisin."),
    ("dopamin", "alt", DOPAMIN_DUSUK_ESIK, "Keyfin yok, biraz durgunsun."),
    ("oksitosin", "ust", OKSITOSIN_YUKSEK_ESIK, "Konustugun kisiye kendini yakin ve sicak hissediyorsun."),
    ("kortizol", "ust", KORTIZOL_YUKSEK_ESIK, "Gerginsin ve tedirginsin, sabrin az."),
    ("merak", "ust", MERAK_YUKSEK_ESIK, "Cok merakli hissediyorsun, soru sormak istiyorsun."),
]


def duygu_cumleleri(hormon_degerleri):
    """Esigi asan her satirin cumlesini tablo sirasiyla liste olarak dondurur. Deger yoksa bos liste."""
    if not hormon_degerleri:
        return []
    cumleler = []
    for ad, yon, esik, cumle in DUYGU_TABLOSU:
        deger = hormon_degerleri.get(ad)
        if deger is None:
            continue
        if (yon == "ust" and deger >= esik) or (yon == "alt" and deger <= esik):
            cumleler.append(cumle)
    return cumleler
