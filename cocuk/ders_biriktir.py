"""D4-c: ogretmenden dersi parti parti toplar; her istekte gecen parcalar havuza eklenir, havuz hedefe
ulasinca durur. 4B tek istekte 50 cumle ya da 10 bilgi veremiyordu. Cagiran: ders_uret.geceyi_uret.
"""

import json
import logging

# 4B'nin tek istekte guvenle verdigi miktar (d4-ders-uret.out: 50 istenince 11-35 gecerli geldi).
OKUL_PARTI = 15
BILGI_PARTI = 3
# Gece basina ust sinir. Olcum (gece 1): okul 18 istek (tekrarlar sona dogru artar), bilgi 10 istek; iki kat pay.
EN_COK_ISTEK = 40

log = logging.getLogger("ders_biriktir")


def cevabi_coz(metin: str, anahtar: str) -> list:
    """Cevaptaki listeyi dondurur; JSON bozuksa ya da liste yoksa loglar ve bos liste dondurur
    (o istek bosa gitmis sayilir, biriktirme surer)."""
    try:
        liste = json.loads(metin)[anahtar]
    except (ValueError, KeyError, TypeError) as hata:
        log.warning("cevap cozulemedi (%s): %r", hata, metin[:200])
        return []
    if not isinstance(liste, list):
        log.warning("%r liste degil: %r", anahtar, metin[:200])
        return []
    return liste


def biriktir(sor_fn, istem_fn, suz_fn, anahtar: str, hedef: int, sicaklik: float) -> tuple[list, dict]:
    """istem_fn(havuz) mesajlari kurar, suz_fn(havuz + gelen) gecenleri dondurur. Havuz hedefe
    ulasinca ilk `hedef` parca ve olcum (istek, gelen, kabul) doner; EN_COK_ISTEK asilirsa RuntimeError."""
    havuz, olcum = [], {"istek": 0, "gelen": 0, "kabul": 0}
    while len(havuz) < hedef:
        if olcum["istek"] >= EN_COK_ISTEK:
            raise RuntimeError(f"{anahtar}: {EN_COK_ISTEK} istekte {len(havuz)} parca toplandi, "
                               f"gereken {hedef} (dogrulama reddi, sebepler logda)")
        gelen = cevabi_coz(sor_fn(istem_fn(havuz), sicaklik), anahtar)
        yeni = suz_fn(havuz + gelen)
        olcum["istek"] += 1
        olcum["gelen"] += len(gelen)
        olcum["kabul"] += max(0, len(yeni) - len(havuz))
        log.info("%s istek %d: %d geldi, havuz %d -> %d / %d", anahtar, olcum["istek"], len(gelen),
                 len(havuz), len(yeni), hedef)
        havuz = yeni
    return havuz[:hedef], olcum
