"""f3-c2: kor puanlari (kor-puanlar.json) ile perdeyi (perde.json) id ile birlestirir, mod farkini
Markdown olarak stdout'a basar ve analiz-cikti.md'ye yazar. Yorum YAPMAZ, sadece sayar.
Cagiran: elle, `.venv\\Scripts\\python.exe araclar\\f3c2-perde-kaldir.py`; tests/test_f3c2_analiz.py.
"""

import json
import statistics
import sys
from collections import defaultdict
from fractions import Fraction
from itertools import product
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from ortak.ayar import MOD_UYANIK, MOD_YORGUN  # noqa: E402

KLASOR = KOK / "reports" / "f3c-kor-olcum"
PUAN_DOSYASI = KLASOR / "kor-puanlar.json"
PERDE_DOSYASI = KLASOR / "perde.json"
CIKTI_DOSYASI = KLASOR / "analiz-cikti.md"
BOYUTLAR = ["dogallik", "soruya_uygunluk", "uzunluk", "tekrar", "genel"]
ESLESMIS_BOYUTLAR = ["genel", "uzunluk"]
MODLAR = [MOD_UYANIK, MOD_YORGUN]
ONDALIK = 3


def _f(sayi):
    """Kesirli sayiyi okunur ondalik dizgeye cevirir."""
    return f"{float(sayi):.{ONDALIK}f}"


def ortalama(degerler):
    """Tam (kesirli) ortalama: 3 tam sayinin ortalamasinda kayan nokta hatasi olmasin diye."""
    return Fraction(sum(degerler), len(degerler))


def birlestir(puanlar, perde):
    """Her puan kaydini perdedeki ayni id'li kayitla birlestirir; eslesmeyen varsa hata verir."""
    if len(puanlar) != len(perde):
        raise ValueError(f"kayit sayisi tutmuyor: puan {len(puanlar)}, perde {len(perde)}")
    satirlar = []
    for puan in puanlar:
        if puan["id"] not in perde:
            raise ValueError(f"perdede olmayan id: {puan['id']}")
        satirlar.append({**perde[puan["id"]], **puan})
    return satirlar


def mod_ortalamalari(satirlar, boyut):
    """{mod: ortalama} verilen boyut icin."""
    return {mod: ortalama([s[boyut] for s in satirlar if s["mod"] == mod]) for mod in MODLAR}


def soru_farklari(satirlar, boyut):
    """Soru basina (uyanik ort. - yorgun ort.); her ort. o sorunun 3 tekrarindan gelir.
    Donus: {soru_id: (uyanik_ort, yorgun_ort, fark)}, soru_id sirali."""
    gruplar = defaultdict(lambda: defaultdict(list))
    for s in satirlar:
        gruplar[s["soru_id"]][s["mod"]].append(s[boyut])
    sonuc = {}
    for soru_id in sorted(gruplar):
        uyanik = ortalama(gruplar[soru_id][MOD_UYANIK])
        yorgun = ortalama(gruplar[soru_id][MOD_YORGUN])
        sonuc[soru_id] = (uyanik, yorgun, uyanik - yorgun)
    return sonuc


def isaret_cevirme_p(farklar):
    """Tam isaret cevirme testi, cift yonlu: 2^n isaret kombinasyonunun kacinda |toplam| gozlenen
    |toplam|'dan kucuk degil. Sifir farklar da sayilir (isareti cevrilse sifir kalir)."""
    gozlenen = abs(sum(farklar))
    say = sum(1 for isaretler in product((1, -1), repeat=len(farklar))
              if abs(sum(i * f for i, f in zip(isaretler, farklar))) >= gozlenen)
    return Fraction(say, 2 ** len(farklar))


def bolum_mod_farki(satirlar):
    satir_metni = []
    for boyut in BOYUTLAR:
        ort = mod_ortalamalari(satirlar, boyut)
        fark = ort[MOD_UYANIK] - ort[MOD_YORGUN]
        satir_metni.append(f"| {boyut} | {_f(ort[MOD_UYANIK])} | {_f(ort[MOD_YORGUN])} | {_f(fark)} |")
    baslik = ["## a) Boyut basina mod ortalamasi (60 cevap)", "",
              "| boyut | uyanik | yorgun | fark (uyanik - yorgun) |", "|---|---|---|---|"]
    return "\n".join(baslik + satir_metni)


def bolum_eslesmis(satirlar):
    parcalar = ["## b) Eslesmis analiz (soru basina 3 tekrar ortalamasi, 10 soru)"]
    for boyut in ESLESMIS_BOYUTLAR:
        farklar = [f for _, _, f in soru_farklari(satirlar, boyut).values()]
        p = isaret_cevirme_p(farklar)
        parcalar.append(f"\n**{boyut}**: ortalama fark {_f(ortalama(farklar))}, "
                        f"isaret cevirme p (cift yonlu, 2^{len(farklar)} kombinasyon) = {_f(p)}\n\n"
                        f"soru farklari: {', '.join(_f(f) for f in farklar)}")
    return "\n".join(parcalar)


def bolum_kategori(satirlar):
    kategoriler = sorted({s["kategori"] for s in satirlar})
    metin = ["## c) Kategori basina `genel` ortalamasi", "",
             "| kategori | uyanik | yorgun | fark |", "|---|---|---|---|"]
    for kategori in kategoriler:
        ort = mod_ortalamalari([s for s in satirlar if s["kategori"] == kategori], "genel")
        metin.append(f"| {kategori} | {_f(ort[MOD_UYANIK])} | {_f(ort[MOD_YORGUN])} | "
                     f"{_f(ort[MOD_UYANIK] - ort[MOD_YORGUN])} |")
    return "\n".join(metin)


def bolum_karakter(satirlar):
    metin = ["## d) Cevap uzunlugu (karakter)", "", "| mod | ortalama | medyan |", "|---|---|---|"]
    for mod in MODLAR:
        karakterler = [s["cevap_karakter"] for s in satirlar if s["mod"] == mod]
        metin.append(f"| {mod} | {_f(ortalama(karakterler))} | {statistics.median(karakterler)} |")
    return "\n".join(metin)


def bolum_soru_tablosu(satirlar):
    kategori_of = {s["soru_id"]: s["kategori"] for s in satirlar}
    metin = ["## e) Soru basina `genel`", "",
             "| soru_id | kategori | uyanik genel ort | yorgun genel ort | fark |", "|---|---|---|---|---|"]
    for soru_id, (uyanik, yorgun, fark) in soru_farklari(satirlar, "genel").items():
        metin.append(f"| {soru_id} | {kategori_of[soru_id]} | {_f(uyanik)} | {_f(yorgun)} | {_f(fark)} |")
    return "\n".join(metin)


def rapor_uret(satirlar):
    bolumler = [bolum_mod_farki, bolum_eslesmis, bolum_kategori, bolum_karakter, bolum_soru_tablosu]
    baslik = "# f3-c2 perde kalkti: mod farki analizi\n"
    return baslik + "\n\n".join(b(satirlar) for b in bolumler) + "\n"


def main():
    puanlar = json.loads(PUAN_DOSYASI.read_text(encoding="utf-8"))
    perde = json.loads(PERDE_DOSYASI.read_text(encoding="utf-8"))
    rapor = rapor_uret(birlestir(puanlar, perde))
    CIKTI_DOSYASI.write_text(rapor, encoding="utf-8")
    print(rapor)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
