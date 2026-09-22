"""f3-c3: iki kor puanlayicinin jsonl puanlarini anahtar.json ile birlestirir; mod farki, uyum ve kesiklik
tablolarini analiz-cikti.md'ye yazar. Yorum YAPMAZ. f3-c2 betiginin ortalama/soru farki fonksiyonlarini kullanir.
Cagiran: elle, `python araclar\\f3c3-perde-kaldir.py`; tests/test_f3c3_perde.py.
"""

import importlib.util
import json
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK / "araclar"))
import f3c3_istatistik as ist  # noqa: E402

_OZ = importlib.util.spec_from_file_location("f3c2", KOK / "araclar" / "f3c2-perde-kaldir.py")
f3c2 = importlib.util.module_from_spec(_OZ)
_OZ.loader.exec_module(f3c2)

KLASOR = KOK / "reports" / "f3c3-kor-olcum"
ANAHTAR = KLASOR / "anahtar.json"
PUAN_1 = KLASOR / "kor-puanlar-1.jsonl"
PUAN_2 = KLASOR / "kor-puanlar-2.jsonl"
CIKTI = KLASOR / "analiz-cikti.md"
BOYUTLAR, UYANIK, YORGUN, _f = f3c2.BOYUTLAR, f3c2.MOD_UYANIK, f3c2.MOD_YORGUN, f3c2._f


def jsonl_oku(yol):
    return [json.loads(satir) for satir in yol.read_text(encoding="utf-8").splitlines() if satir.strip()]


def kesik_isaretle(anahtar):
    """Uretim raporundaki tanim: token >= max_tokens ise cevap tavana vurmus, kesik sayilir."""
    return {i: {**k, "kesik": k["token"] >= k["ayarlar"]["max_tokens"]} for i, k in anahtar.items()}


def eslesmis_satir(satirlar, boyut):
    """Soru basina tohum ortalamasi farki (uyanik - yorgun); iki modu da olan sorular. Donus: tablo hucreleri."""
    tum = f3c2.soru_farklari([s for s in satirlar if _iki_mod_var(satirlar, s["soru_id"])], boyut)
    farklar = [f for _, _, f in tum.values()]
    arti, eksi, p_isaret = ist.isaret_testi_p(farklar)
    return {"n": len(farklar), "fark": f3c2.ortalama(farklar), "arti": arti, "eksi": eksi,
            "p_isaret": p_isaret, "p_perm": ist.permutasyon_p(farklar)}


def _iki_mod_var(satirlar, soru_id):
    return {s["mod"] for s in satirlar if s["soru_id"] == soru_id} == {UYANIK, YORGUN}


def bolum_eslesmis(satirlar, baslik):
    sonuclar = {b: eslesmis_satir(satirlar, b) for b in BOYUTLAR}
    duz = ist.holm({b: r["p_perm"] for b, r in sonuclar.items()})
    metin = [f"## {baslik}", "", "| boyut | soru | ort. fark (U-Y) | U>Y / U<Y | isaret p | perm p | Holm p |",
             "|---|---|---|---|---|---|---|"]
    for b, r in sonuclar.items():
        metin.append(f"| {b} | {r['n']} | {_f(r['fark'])} | {r['arti']}/{r['eksi']} | {r['p_isaret']:.4f} "
                     f"| {r['p_perm']:.4f} | {duz[b]:.4f} |")
    return "\n".join(metin)


def bolum_kategori(satirlar):
    metin = ["## Kategori basina mod farki (uyanik - yorgun, tum kayitlar)", "",
             "| kategori | soru | " + " | ".join(BOYUTLAR) + " |", "|---" * (len(BOYUTLAR) + 2) + "|"]
    for kat in sorted({s["kategori"] for s in satirlar}):
        alt = [s for s in satirlar if s["kategori"] == kat]
        hucre = []
        for b in BOYUTLAR:
            ort = f3c2.mod_ortalamalari(alt, b)
            hucre.append(_f(ort[UYANIK] - ort[YORGUN]))
        metin.append(f"| {kat} | {len({s['soru_id'] for s in alt})} | " + " | ".join(hucre) + " |")
    return "\n".join(metin)


def bolum_uyum(satirlar1, satirlar2):
    """120 ortak kayitta boyut basina uyum ve iki puanlayicinin ayni alt kumedeki mod farki."""
    bir = {s["id"]: s for s in satirlar1}
    ortak1 = [bir[s["id"]] for s in satirlar2]
    metin = [f"## Puanlayicilar arasi uyum ({len(satirlar2)} ortak kayit)", "",
             "| boyut | tam uyum | agirlikli kappa | P1 fark (U-Y) | P2 fark (U-Y) | ayni yon |",
             "|---|---|---|---|---|---|"]
    for b in BOYUTLAR:
        a, c = [s[b] for s in ortak1], [s[b] for s in satirlar2]
        o1, o2 = f3c2.mod_ortalamalari(ortak1, b), f3c2.mod_ortalamalari(satirlar2, b)
        f1, f2 = o1[UYANIK] - o1[YORGUN], o2[UYANIK] - o2[YORGUN]
        metin.append(f"| {b} | {float(ist.tam_uyum(a, c)):.3f} | {ist.agirlikli_kappa(a, c):.3f} "
                     f"| {_f(f1)} | {_f(f2)} | {'evet' if f1 * f2 > 0 else 'hayir'} |")
    return "\n".join(metin)


def bolum_kesik(satirlar):
    metin = ["## Kesik cevap etkisi (genel ve uzunluk ortalamasi)", "",
             "| mod | kesik mi | kayit | genel | uzunluk |", "|---|---|---|---|---|"]
    for mod in (UYANIK, YORGUN):
        for kesik in (True, False):
            alt = [s for s in satirlar if s["mod"] == mod and s["kesik"] == kesik]
            metin.append(f"| {mod} | {'evet' if kesik else 'hayir'} | {len(alt)} | "
                         f"{_f(f3c2.ortalama([s['genel'] for s in alt]))} | "
                         f"{_f(f3c2.ortalama([s['uzunluk'] for s in alt]))} |")
    return "\n".join(metin)


def rapor_uret(satirlar1, satirlar2):
    kesiksiz = [s for s in satirlar1 if not s["kesik"]]
    bolumler = [bolum_eslesmis(satirlar1, "P1 eslesmis mod farki (30 soru, soru basina 8 tohum ort.)"),
                bolum_kategori(satirlar1), bolum_uyum(satirlar1, satirlar2), bolum_kesik(satirlar1),
                bolum_eslesmis(kesiksiz, "P1 eslesmis mod farki, yalniz kesik olmayan cevaplar")]
    return "# f3-c3 perde kalkti: analiz ciktisi\n\n" + "\n\n".join(bolumler) + "\n"


def main():
    anahtar = kesik_isaretle(json.loads(ANAHTAR.read_text(encoding="utf-8")))
    puan1, puan2 = jsonl_oku(PUAN_1), jsonl_oku(PUAN_2)
    satirlar1 = f3c2.birlestir(puan1, anahtar)
    satirlar2 = f3c2.birlestir(puan2, {p["id"]: anahtar[p["id"]] for p in puan2})
    rapor = rapor_uret(satirlar1, satirlar2)
    CIKTI.write_text(rapor, encoding="utf-8")
    print(rapor)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
