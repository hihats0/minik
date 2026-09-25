# -*- coding: utf-8 -*-
# Minik'in 14 saatlik gununun LLM maliyeti. Olculen hizlarla (2 is parcacigi, sadece CPU).
HIZ = {  # model: (prompt okuma tok/s, uretme tok/s)
    "0.8B": (156.4, 41.1),
    "2B":   (70.9, 19.7),
    "4B":   (27.7, 8.97),
}
UYANIK_SN = 14 * 3600

# (ad, cagri sayisi, onbellege girmeyen istem token, uretilen token, hangi katman)
ISLER = [
    ("Twitter: tweet elemesi",      400, 120,   5, "kucuk"),
    ("Twitter: dusunme + cevap",     30, 900, 180, "kafa"),
    ("Haber: hangisini okusam",     100, 100,   5, "kucuk"),
    ("Haber: okudu, anladi",         30, 900, 120, "kafa"),
    ("Arkadas sohbeti",              72, 700,  60, "kafa"),
    ("Bos durma, aklina gelen",      48, 400, 100, "kafa"),
    ("Siir / kitap / uzun yazi",      5, 500, 600, "kafa"),
]

def hesapla(kafa_modeli, kucuk_modeli="0.8B"):
    toplam, satir = 0.0, []
    for ad, n, istem, cikti, katman in ISLER:
        m = kafa_modeli if katman == "kafa" else kucuk_modeli
        pp, tg = HIZ[m]
        sn = n * (istem / pp + cikti / tg)
        toplam += sn
        satir.append((ad, n, m, sn))
    return toplam, satir

for kafa in ("4B", "2B"):
    toplam, satir = hesapla(kafa)
    print(f"\n=== Kafa = {kafa}, eleme = 0.8B, 2 vCPU, sadece CPU ===")
    for ad, n, m, sn in satir:
        print(f"  {ad:32s} {n:4d} cagri  {m:4s}  {sn/60:7.1f} dk")
    print(f"  {'TOPLAM':32s} {sum(i[1] for i in ISLER):4d} cagri        {toplam/60:7.1f} dk")
    print(f"  Uyanik surenin yuzdesi: %{100*toplam/UYANIK_SN:.1f}")
    kafa_cagri = sum(i[1] for i in ISLER if i[4] == "kafa")
    print(f"  Bunun {kafa_cagri}'i Kafa cagrisi, {sum(i[1] for i in ISLER)-kafa_cagri}'i kucuk model")
