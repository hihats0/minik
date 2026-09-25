"""Gomme modeline kiyas icin saf stdlib kelime kesisimi (Jaccard) ile arama yapar,
ayni 15 sorguda ilk1/ilk3 dogrulugunu ve alakasiz sorgu tuzagini hesaplar.
Cagiran: elle, `python deneyler/kelime-arama-olc.py`.
"""

import json
import re
import sys
from pathlib import Path

VERI_KLASORU = Path(__file__).resolve().parent
ANI_DOSYASI = VERI_KLASORU / "cagrisim-anilar.json"
SORGU_DOSYASI = VERI_KLASORU / "cagrisim-sorgular.json"
ILK_K = 3
# Turkce'de her cumlede gecen, ayirt edici olmayan kisa kelimeler.
DURAK_KELIMELER = {"bir", "bu", "ve", "ile", "de", "da", "cok", "gibi", "icin", "ben", "sen"}


def kelimelere_ayir(metin):
    """Metni kucuk harfe cevirir, noktalamayi atar, durak kelimeleri cikarir."""
    kelimeler = re.findall(r"[a-z]+", metin.lower())
    return {k for k in kelimeler if k not in DURAK_KELIMELER}


def jaccard(a, b):
    """Iki kelime kumesinin Jaccard benzerligi: kesisim / birlesim."""
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def en_yakin_k(sorgu_kelimeleri, ani_kelimeleri, k):
    """Ani kelime kumeleri icinde sorguya en yakin k taneyi (id, benzerlik) dondurur."""
    benzerlikler = [(aid, jaccard(sorgu_kelimeleri, kw)) for aid, kw in ani_kelimeleri.items()]
    benzerlikler.sort(key=lambda x: x[1], reverse=True)
    return benzerlikler[:k]


def olc():
    """15 sorguyu kosar, her biri icin en yakin 3 aniyi ve dogruluk bayragini toplar."""
    anilar = json.loads(ANI_DOSYASI.read_text(encoding="utf-8"))
    sorgular = json.loads(SORGU_DOSYASI.read_text(encoding="utf-8"))
    ani_kelimeleri = {a["id"]: kelimelere_ayir(a["metin"]) for a in anilar}
    sonuclar = []
    for s in sorgular:
        sorgu_kw = kelimelere_ayir(s["sorgu"])
        en_yakin = en_yakin_k(sorgu_kw, ani_kelimeleri, ILK_K)
        sonuclar.append({
            "sorgu_id": s["id"],
            "tur": s["tur"],
            "dogru_id": s["dogru_id"],
            "en_yakin": en_yakin,
            "ilk1_dogru": en_yakin[0][0] == s["dogru_id"],
            "ilk3_dogru": s["dogru_id"] in [x[0] for x in en_yakin],
        })
    return sonuclar


def ozetle(sonuclar):
    """Tur bazinda ilk1/ilk3 oranini ve alakasiz sorgularin en yuksek benzerligini hesaplar."""
    ozet = {}
    for tur in ("dogrudan", "es_anlamli"):
        grup = [s for s in sonuclar if s["tur"] == tur]
        ozet[tur] = {
            "adet": len(grup),
            "ilk1_oran": round(sum(s["ilk1_dogru"] for s in grup) / len(grup), 2),
            "ilk3_oran": round(sum(s["ilk3_dogru"] for s in grup) / len(grup), 2),
        }
    alakasiz = [s for s in sonuclar if s["tur"] == "alakasiz"]
    ozet["alakasiz_en_yuksek_benzerlik"] = round(
        max(s["en_yakin"][0][1] for s in alakasiz), 3
    )
    return ozet


def main():
    sonuclar = olc()
    cikti = {"sonuclar": sonuclar, "ozet": ozetle(sonuclar)}
    print(json.dumps(cikti, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
