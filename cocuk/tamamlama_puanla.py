"""D4-c sart 1: sabah tamamlamalarini ogretmen modele kor puanlatir (model adi ve gece gizli, karisik
sira, anonim id); 3-5 kelime sinirini kodla da uygular. Cagiran: elle
`python -m cocuk.tamamlama_puanla --adlar d4-transformer d4-ssm`.
"""

import argparse
import json
import logging
import random
import re
from collections import defaultdict

from cocuk import ders_dogrula as dd
from cocuk import ogretmen
from cocuk.degerlendir import SINAV_DIZINI
from cocuk import egit_araclari as ea
from cocuk.sabah_sinavi import TAMAMLAMA_DIZINI

# Kendi olctugunu puanlayan comert olur (vault dersler.md): kelime siniri ogretmene birakilmaz.
EN_AZ_KELIME, EN_COK_KELIME = 3, 5
KOR_DIZIN_ADI = "kor_puanlama"
SONUC_ADI = "sart1.json"
GECERLI_PUANLAR = (0, 1)
GEREKCE_EN_COK_KELIME = 12
SISTEM = ("Sen Türkçe dilbilgisi puanlayan titiz bir öğretmensin. Yalnızca "
          '{"puan": 0 ya da 1, "gerekce": "kısa açıklama"} biçiminde JSON döndür. '
          f"Gerekçe en fazla {GEREKCE_EN_COK_KELIME} kelime olsun, kelime tekrarlama.")
# Kesilmis cevabin basinda puan okunabiliyorsa kurtarilir (23 Eyl: gerekce dongusu JSON'u yarim birakti).
PUAN_DESENI = re.compile(r'^\s*\{\s*"puan"\s*:\s*(\d+)\s*[,}]')
KESILDI = "kesildi"
PUANLANAMADI = "puanlanamadi"

log = logging.getLogger("tamamlama_puanla")


def kayitlari_topla(adlar: list[str]) -> list[dict]:
    kayitlar = []
    for ad in adlar:
        for yol in sorted((ea.AGIRLIK_DIZINI / ad / TAMAMLAMA_DIZINI).glob("gece_*.json")):
            gece = int(yol.stem.split("_")[1])
            for t in json.loads(yol.read_text("utf-8")):
                kayitlar.append({"ad": ad, "gece": gece, "baslangic": t["baslangic"], "cumle": t["cumle"]})
    if not kayitlar:
        raise FileNotFoundError(f"tamamlama dosyasi yok: {adlar}; once yedi_gece kosmali")
    log.info("%d tamamlama puanlanacak", len(kayitlar))
    return kayitlar


def anonimlestir(kayitlar: list[dict], uretec: random.Random) -> dict:
    """Sira karistirilir, sonra sirayla id verilir: id ne modeli ne geceyi ele verir."""
    karisik = list(kayitlar)
    uretec.shuffle(karisik)
    return {f"C{i:04d}": k for i, k in enumerate(karisik)}


def kesik_kurtar(metin: str) -> str:
    """Bozuk JSON'un basinda gecerli puan varsa onu tasiyan saglam JSON dondurur, yoksa metni aynen."""
    try:
        json.loads(metin)
        return metin
    except ValueError:
        eslesme = PUAN_DESENI.match(metin)
    if eslesme is None or int(eslesme.group(1)) not in GECERLI_PUANLAR:
        return metin
    log.warning("kesilmis ogretmen cevabi kurtarildi, puan=%s | cevap basi: %r", eslesme.group(1), metin[:80])
    return json.dumps({"puan": int(eslesme.group(1)), "gerekce": KESILDI})


def ogretmen_puani(sor_fn, yonerge: str, cumle: str) -> dict:
    """Puan dict'i ya da hep bozuk cevapta {"puan": None, "gerekce": PUANLANAMADI} (loglanir)."""
    mesajlar = [{"role": "system", "content": SISTEM},
                {"role": "user", "content": f"Yönerge: {yonerge}\n\nCümle: {cumle}"}]

    def dogrula(veri):
        if veri.get("puan") not in GECERLI_PUANLAR:
            raise ValueError("puan 0 ya da 1 degil")
        return {"puan": veri["puan"], "gerekce": str(veri.get("gerekce", ""))}

    try:
        return ogretmen.json_iste(lambda m, s: kesik_kurtar(sor_fn(m, s)), mesajlar, dogrula,
                                  ogretmen.PUANLAMA_SICAKLIGI)
    except RuntimeError as hata:
        log.error("cumle puanlanamadi, ortalamaya girmeyecek: %r | %s", cumle, hata)
        return {"puan": None, "gerekce": PUANLANAMADI}


def ozetle(perde: dict, puanlar: dict) -> dict:
    """ad -> gece -> {toplam, ogretmen_1, kelime_uygun, puan, puanlanamadi}; puan = ogretmen 1 VE
    3-5 kelime. Puanlanamayan kayit toplama girmez, ayri sayilir."""
    bos = {"toplam": 0, "ogretmen_1": 0, "kelime_uygun": 0, "puan": 0, PUANLANAMADI: 0}
    ozet = defaultdict(lambda: defaultdict(lambda: dict(bos)))
    for kimlik, k in perde.items():
        hucre = ozet[k["ad"]][str(k["gece"])]
        if puanlar[kimlik]["puan"] is None:
            hucre[PUANLANAMADI] += 1
            continue
        kelime_uygun = EN_AZ_KELIME <= dd.kelime_say(k["cumle"]) <= EN_COK_KELIME
        hucre["toplam"] += 1
        hucre["ogretmen_1"] += puanlar[kimlik]["puan"]
        hucre["kelime_uygun"] += kelime_uygun
        hucre["puan"] += puanlar[kimlik]["puan"] == 1 and kelime_uygun
    return ozet


def puanla(adlar: list[str], sor_fn, tohum: int) -> dict:
    """Anonim listeyi ve perdeyi once yazar (Yigit de kor puanlayabilsin), sonra ogretmene sorar."""
    yonerge = json.loads((SINAV_DIZINI / "dilbilgisi.json").read_text("utf-8"))["yonerge"]["puan"]
    perde = anonimlestir(kayitlari_topla(adlar), random.Random(tohum))
    dizin = ea.AGIRLIK_DIZINI / KOR_DIZIN_ADI
    dizin.mkdir(parents=True, exist_ok=True)
    yaz(dizin / "anonim.json", {i: k["cumle"] for i, k in perde.items()})
    yaz(dizin / "perde.json", perde)
    puanlar = {i: ogretmen_puani(sor_fn, yonerge, k["cumle"]) for i, k in perde.items()}
    yaz(dizin / "ogretmen_puanlari.json", puanlar)
    ozet = ozetle(perde, puanlar)
    for ad in adlar:
        yaz(ea.AGIRLIK_DIZINI / ad / SONUC_ADI, ozet[ad])
    return ozet


def yaz(yol, veri) -> None:
    yol.write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--adlar", nargs="+", required=True)
    p.add_argument("--tohum", type=int, default=1337, help="karistirma tohumu")
    arg = p.parse_args()
    with ogretmen.acik_sunucu(ogretmen.PUANLAMA_AYARI) as sor_fn:
        print(json.dumps(puanla(arg.adlar, sor_fn, arg.tohum), ensure_ascii=False, indent=1))
