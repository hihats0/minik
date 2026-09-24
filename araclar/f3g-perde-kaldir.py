"""f3-g: tek kor puanlayicinin puanlarini anahtar.json ile birlestirir; tum kayitlar ve sizintisiz kayitlar icin
mod farki, kesik, "yorgunum" orani ve token tablolarini analiz-cikti.md'ye yazar. Yorum YAPMAZ.
Cagiran: elle, `python araclar\\f3g-perde-kaldir.py`; tests/test_f3g_perde.py. f3c3 aracinin bolumlerini kullanir.
f3c3.bolum_kesik kullanilmaz: bir mod/kesik grubu bos kaliyor, bos ortalama sifira bolme hatasi veriyor.
"""

import importlib.util
import json
import re
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
_OZ = importlib.util.spec_from_file_location("f3c3_perde", KOK / "araclar" / "f3c3-perde-kaldir.py")
f3c3 = importlib.util.module_from_spec(_OZ)
_OZ.loader.exec_module(f3c3)

KLASOR = KOK / "reports" / "f3g-kor-olcum"
ANAHTAR = KLASOR / "anahtar.json"
PUAN = KLASOR / "kor-puanlar-1.jsonl"
KAYITLAR = KLASOR / "kayitlar.jsonl"
CIKTI = KLASOR / "analiz-cikti.md"
UYANIK, YORGUN, _f, ortalama = f3c3.UYANIK, f3c3.YORGUN, f3c3._f, f3c3.f3c2.ortalama
# Puanlayici notu: 1'e dusen cevaplarin sik sebebi yersiz "yorgunum/uykum var" ekleri.
YORGUNLUK_DESENI = re.compile(r"yorgun|uykum|uykulu", re.IGNORECASE)


def cevaplari_ekle(anahtar, kayitlar):
    """Anahtara (soru_id, mod, tohum) eslesmesiyle cevap metni ve think_token ekler. Hata kayitlari atlanir."""
    tam = {(k["soru_id"], k["mod"], k["tohum"]): k for k in kayitlar if "cevap" in k}
    if len(tam) != len(anahtar):
        raise ValueError(f"kayit sayisi tutmuyor: kayitlar {len(tam)}, anahtar {len(anahtar)}")
    sonuc = {}
    for kimlik, a in anahtar.items():
        k = tam[(a["soru_id"], a["mod"], a["tohum"])]
        sonuc[kimlik] = {**a, "cevap": k["cevap"], "think_token": k["think_token"]}
    return sonuc


def bolum_nesnel(satirlar, baslik):
    """Mod basina kayit, ort. token, ort. dusunce tokeni, kesik orani ve yorgunluk kelimesi orani."""
    metin = [f"## {baslik}", "", "| mod | kayit | ort. token | ort. think_token | kesik | 'yorgun/uykum' geçen |",
             "|---|---|---|---|---|---|"]
    for mod in (UYANIK, YORGUN):
        alt = [s for s in satirlar if s["mod"] == mod]
        kesik = sum(s["kesik"] for s in alt)
        yorgunluk = sum(bool(YORGUNLUK_DESENI.search(s["cevap"])) for s in alt)
        metin.append(f"| {mod} | {len(alt)} | {float(ortalama([s['token'] for s in alt])):.1f} "
                     f"| {float(ortalama([s['think_token'] for s in alt])):.1f} "
                     f"| {kesik} ({kesik / len(alt):.1%}) | {yorgunluk} ({yorgunluk / len(alt):.1%}) |")
    return "\n".join(metin)


def bolum_yorgunluk_puani(satirlar):
    """Yorgun modda 'yorgun/uykum' gecen ve gecmeyen cevaplarin genel puan ortalamasi."""
    metin = ["## Yorgun modda yorgunluk kelimesi ve genel puan", "", "| kelime var mi | kayit | genel |",
             "|---|---|---|"]
    yorgun = [s for s in satirlar if s["mod"] == YORGUN]
    for var in (True, False):
        alt = [s for s in yorgun if bool(YORGUNLUK_DESENI.search(s["cevap"])) == var]
        metin.append(f"| {'evet' if var else 'hayir'} | {len(alt)} | "
                     f"{_f(ortalama([s['genel'] for s in alt])) if alt else '-'} |")
    return "\n".join(metin)


def rapor_uret(satirlar):
    temiz = [s for s in satirlar if not s["sizinti"]]
    bolumler = [f3c3.bolum_eslesmis(satirlar, f"Eslesmis mod farki, tum kayitlar ({len(satirlar)})"),
                f3c3.bolum_eslesmis(temiz, f"Eslesmis mod farki, sizintisiz kayitlar ({len(temiz)})"),
                f3c3.bolum_kategori(satirlar),
                bolum_nesnel(satirlar, "Nesnel sinyaller, tum kayitlar"),
                bolum_nesnel(temiz, "Nesnel sinyaller, sizintisiz kayitlar"), bolum_yorgunluk_puani(satirlar)]
    return "# f3-g perde kalkti: analiz ciktisi (tek puanlayici, kappa yok)\n\n" + "\n\n".join(bolumler) + "\n"


def main():
    anahtar = f3c3.kesik_isaretle(json.loads(ANAHTAR.read_text(encoding="utf-8")))
    anahtar = cevaplari_ekle(anahtar, f3c3.jsonl_oku(KAYITLAR))
    satirlar = f3c3.f3c2.birlestir(f3c3.jsonl_oku(PUAN), anahtar)
    rapor = rapor_uret(satirlar)
    CIKTI.write_text(rapor, encoding="utf-8")
    print(rapor)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
