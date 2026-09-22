"""D4-c: gecenin sonunda (=ertesi sabah) cocugu sinar: dunku bilgi sorulari (sart 2), onceki gecelerin
sorulari (birikimli), eski sinav + dilbilgisi ciftleri (sart 3), tamamlamalar (sart 1, dosyaya).
karne.jsonl'e bir satir ekler. Cagiran: cocuk/yedi_gece.py.
"""

import json
import time

from cocuk import degerlendir as dg
from cocuk import ders_dogrula as dd

KARNE_ADI = "karne.jsonl"
TAMAMLAMA_DIZINI = "tamamlama"
ONDALIK = 3


def secmeli_dogru_mu(model, sp, soru: dict, cihaz) -> bool:
    """Bosluga dogru cevap ve yanlis siklar konur; en yuksek toplam log-olasilik dogrudaysa True
    (eski sinavla ayni olcu, sans %25)."""
    secenekler = [soru["cevap"]] + soru["yanlislar"]
    puanlar = [dg.log_olasilik(model, sp, dd.doldur(soru["soru"], s), cihaz)[0] for s in secenekler]
    return puanlar.index(max(puanlar)) == 0


def bilgi_sinavi(model, sp, dersler: list[dict], cihaz) -> dict | None:
    """Verilen gecelerin bilgi sorulari; gece bazinda dogruluk da tutulur (unutma egrisi icin)."""
    if not dersler:
        return None
    gece_bazinda, dogru, toplam = {}, 0, 0
    for ders in dersler:
        sonuclar = [secmeli_dogru_mu(model, sp, s, cihaz) for s in dd.sabah_sorulari(ders)]
        gece_bazinda[str(ders["gece"])] = round(sum(sonuclar) / len(sonuclar), ONDALIK)
        dogru, toplam = dogru + sum(sonuclar), toplam + len(sonuclar)
    return {"soru": toplam, "dogru": dogru, "dogruluk": round(dogru / toplam, ONDALIK),
            "gece_bazinda": gece_bazinda}


def tamamlamalari_yaz(model, sp, gece: int, cikti, cihaz) -> str:
    """Sart 1'in ham malzemesi; puanlama ayri (cocuk/tamamlama_puanla.py, kor)."""
    dizin = cikti / TAMAMLAMA_DIZINI
    dizin.mkdir(parents=True, exist_ok=True)
    yol = dizin / f"gece_{gece}.json"
    yol.write_text(json.dumps(dg.tamamlamalari_uret(model, sp, cihaz), ensure_ascii=False, indent=1),
                   encoding="utf-8")
    return f"{TAMAMLAMA_DIZINI}/{yol.name}"


def sabah_sinavi(model, sp, dersler: list[dict], gece: int, cikti, cihaz) -> dict:
    """gece 0 = on egitim sonu temel puan (bilgi sorusu yok). dersler: 1..gece arasi dersler."""
    model.eval()
    satir = {"gece": gece, "zaman": time.strftime("%Y-%m-%d %H:%M:%S"),
             "dun": bilgi_sinavi(model, sp, dersler[gece - 1:gece] if gece else [], cihaz),
             "onceki_geceler": bilgi_sinavi(model, sp, dersler[:max(gece - 1, 0)], cihaz),
             "eski_sinav": dg.eski_sinavi_puanla(model, sp, cihaz),
             "dilbilgisi_ciftleri": dg.ciftleri_puanla(model, sp, cihaz),
             "tamamlama_dosyasi": tamamlamalari_yaz(model, sp, gece, cikti, cihaz)}
    with open(cikti / KARNE_ADI, "a", encoding="utf-8") as dosya:
        dosya.write(json.dumps(satir, ensure_ascii=False) + "\n")
    return satir
