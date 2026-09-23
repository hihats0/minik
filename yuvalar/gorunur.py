"""Gorunur sayfa (spec 4.8): Uyku her uykudan sonra loglar/gorunur.html'i bastan yazar. Statik,
salt okunur, yalniz stdlib string; sunucu yok, disariya yayin yok. Cagiran: yuvalar/uyku.py (gece)."""

import html
import time
from datetime import datetime

from ortak import log
from yuvalar import defter_sqlite

YUVA_ADI = "gorunur"
SAYFA_ADI = "gorunur.html"
BILINMIYOR = "bilinmiyor"
SAYFA_KALIBI = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><title>Minik gorunur sayfa</title></head>
<body>
<h1>Minik: son uyku</h1>
<p>Uretildi: {zaman}. Salt okunur, her uykuda yeniden yazilir.</p>
<h2>Anilar</h2>
<ul><li>Tutulan ani: {tutulan}</li><li>Etiketlere gore: {etiketler}</li>
<li>Bu uykuda budanan: {budanan}</li><li>Islenmis gece: {gece_sayisi}</li></ul>
<h2>Yas ve hormonlar</h2>
<p>Yas (gece sayaci): {yas}</p>
<table border="1"><tr><th>Hormon</th><th>Deger</th></tr>{hormon_satirlari}</table>
<h2>Son gecenin ozeti</h2>
<pre>{ozet}</pre>
</body></html>
"""


def yaz(klasor, hormon_durumu, ozet, budanan):
    """Defter sqlite'indan sayilari okur, sayfayi LOG_KLASORU/gorunur.html'e yazar, yolu dondurur."""
    basladi = time.perf_counter()
    baglanti = defter_sqlite.baglan(klasor)
    try:
        etiketler = defter_sqlite.etiket_sayilari(baglanti)
        gece_sayisi = len(defter_sqlite.islenmis_geceler(baglanti))
    finally:
        baglanti.close()
    metin = SAYFA_KALIBI.format(
        zaman=datetime.now().astimezone().isoformat(timespec="seconds"),
        tutulan=sum(etiketler.values()), etiketler=html.escape(str(etiketler)),
        budanan=budanan, gece_sayisi=gece_sayisi,
        yas=BILINMIYOR if hormon_durumu is None else hormon_durumu.yas,
        hormon_satirlari=_hormon_satirlari(hormon_durumu), ozet=html.escape(ozet))
    log.LOG_KLASORU.mkdir(parents=True, exist_ok=True)
    yol = log.LOG_KLASORU / SAYFA_ADI
    yol.write_text(metin, encoding="utf-8")
    log.yaz(YUVA_ADI, "yaz", int((time.perf_counter() - basladi) * 1000), "ok",
            {"tutulan": sum(etiketler.values()), "budanan": budanan})
    return yol


def _hormon_satirlari(hormon_durumu):
    """Her hormon icin bir tablo satiri; hormon durumu verilmediyse tek 'bilinmiyor' satiri."""
    if hormon_durumu is None:
        return f"<tr><td>{BILINMIYOR}</td><td>-</td></tr>"
    return "".join(f"<tr><td>{html.escape(ad)}</td><td>{deger:.1f}</td></tr>"
                   for ad, deger in hormon_durumu.oku().items())
