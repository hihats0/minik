"""Gomme tabanli cagrisimin kalitesini olcer: cagrisim-anilar.json'daki anilari ve
cagrisim-sorgular.json'daki 15 sorguyu gomer, kosinus benzerligiyle ilk1/ilk3
dogrulugunu ve alakasiz sorgu tuzagini hesaplar.
Cagiran: elle, `python deneyler/cagrisim-olc.py <url>`.
"""

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # kok: ortak/, yuvalar/
from ortak.gomme import vektor_al

VERI_KLASORU = Path(__file__).resolve().parent
ANI_DOSYASI = VERI_KLASORU / "cagrisim-anilar.json"
SORGU_DOSYASI = VERI_KLASORU / "cagrisim-sorgular.json"
ILK_K = 3


def kosinus(a, b):
    """Iki vektorun kosinus benzerligini stdlib math ile hesaplar."""
    ic_carpim = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return ic_carpim / (norm_a * norm_b)


def anilari_gom(url, anilar):
    """Her aniyi gomer, {id: vektor} sozlugu dondurur."""
    return {a["id"]: vektor_al(url, a["metin"])[0] for a in anilar}


def en_yakin_k(sorgu_vektoru, ani_vektorleri, k):
    """Ani vektorleri icinde sorguya en yakin k taneyi (id, benzerlik) olarak dondurur."""
    benzerlikler = [(aid, kosinus(sorgu_vektoru, v)) for aid, v in ani_vektorleri.items()]
    benzerlikler.sort(key=lambda x: x[1], reverse=True)
    return benzerlikler[:k]


def olc(url):
    """15 sorguyu kosar, her biri icin en yakin 3 aniyi ve dogruluk bayragini toplar."""
    anilar = json.loads(ANI_DOSYASI.read_text(encoding="utf-8"))
    sorgular = json.loads(SORGU_DOSYASI.read_text(encoding="utf-8"))
    ani_vektorleri = anilari_gom(url, anilar)
    sonuclar = []
    for s in sorgular:
        sorgu_v, _ = vektor_al(url, s["sorgu"])
        en_yakin = en_yakin_k(sorgu_v, ani_vektorleri, ILK_K)
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
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8811/v1/embeddings"
    sonuclar = olc(url)
    cikti = {"sonuclar": sonuclar, "ozet": ozetle(sonuclar)}
    print(json.dumps(cikti, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
