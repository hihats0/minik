"""g007 kor puanlama dosyasi: LFM2.5 sinav cevaplari ve k23 Turkish-Gemma cevaplarini model adi gizli,
soru basina karisik sirada harfle etiketli tek md dosyasina ve ayri anahtar json'a yazar. Cagiran: elle."""

import json
import random
import string
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
G007_KLASOR = KOK / "reports/g007-ham-cevaplar"
GEMMA_DOSYA = KOK / "reports/k23-ham-cevaplar/gemma-9b.json"
KOR_KLASOR = G007_KLASOR / "kor"
KOR_MD = KOR_KLASOR / "kor.md"
ANAHTAR_JSON = KOR_KLASOR / "anahtar.json"
TOHUM = 2008  # tur1: 2007 (dosyalari kor/tur1/ altinda)
HARIC_SONEKLER = ("-dusunce-acik",)
KOSULDU = "kosuldu"
BEKLENEN_SORU = 20
BASLIK = ("# g007 kor cevaplar\n\nModel adi yok. Puan olcutu: deneyler/turkce-testi.md (0/1/2). "
          "Her soruda cevaplar harfle etiketli, sira soru basina karisik.")


def json_oku(yol):
    """Dosyayi utf-8 json olarak okur."""
    return json.loads(yol.read_text(encoding="utf-8"))


def kaynaklari_topla():
    """{etiket: sinav_listesi}: kosulmus g007 dosyalari (HARIC_SONEKLER disi) + k23 Gemma sinavi."""
    kaynaklar = {}
    for yol in sorted(G007_KLASOR.glob("*.json")):
        if yol.stem.endswith(HARIC_SONEKLER):
            continue
        kayit = json_oku(yol)
        if kayit.get("durum") == KOSULDU and kayit.get("sinav"):
            kaynaklar[yol.stem] = kayit["sinav"]
    kaynaklar[GEMMA_DOSYA.stem] = json_oku(GEMMA_DOSYA)["sinav"]
    return kaynaklar


def sorulari_birlestir(kaynaklar):
    """{no: {"soru": str, "cevaplar": {etiket: cevap}}}; soru metni kaynaklar arasi farkliysa hata verir."""
    sorular = {}
    for etiket, sinav in kaynaklar.items():
        for s in sinav:
            hedef = sorular.setdefault(s["no"], {"soru": s["soru"], "cevaplar": {}})
            if hedef["soru"] != s["soru"]:
                raise ValueError(f"Soru {s['no']} metni kaynaklar arasinda farkli ({etiket}).")
            hedef["cevaplar"][etiket] = s["cevap"]
    if len(sorular) != BEKLENEN_SORU:
        raise ValueError(f"{BEKLENEN_SORU} soru beklendi, {len(sorular)} bulundu.")
    for no, kayit in sorular.items():
        if len(kayit["cevaplar"]) != len(kaynaklar):
            raise ValueError(f"Soru {no} icin cevap eksik.")
    return dict(sorted(sorular.items()))


def korle(sorular, tohum):
    """(md_metni, anahtar): soru basina sirayi karistirir, A, B, C diye etiketler."""
    rastgele = random.Random(tohum)
    satirlar, anahtar = [BASLIK], {}
    for no, kayit in sorular.items():
        satirlar.append(f"\n## Soru {no}: {kayit['soru']}")
        etiketler = sorted(kayit["cevaplar"])
        rastgele.shuffle(etiketler)
        for harf, etiket in zip(string.ascii_uppercase, etiketler):
            anahtar[f"{no}{harf}"] = etiket
            satirlar.append(f"### {no}{harf}\n{kayit['cevaplar'][etiket]}")
    return "\n".join(satirlar) + "\n", anahtar


def main():
    kaynaklar = kaynaklari_topla()
    metin, anahtar = korle(sorulari_birlestir(kaynaklar), TOHUM)
    KOR_KLASOR.mkdir(parents=True, exist_ok=True)
    KOR_MD.write_text(metin, encoding="utf-8")
    ANAHTAR_JSON.write_text(json.dumps(anahtar, ensure_ascii=False), encoding="utf-8")
    print(f"Kaynak: {len(kaynaklar)} ({', '.join(kaynaklar)}); cevap: {len(anahtar)}")
    print(f"Yazildi: {KOR_MD.relative_to(KOK)}, {ANAHTAR_JSON.relative_to(KOK)}")


if __name__ == "__main__":
    main()
