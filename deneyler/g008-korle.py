"""Yeni olcum ve k23 Turkish-Gemma cevaplarini model adi ve kip gizli, adlari maskeli, soru basina
karisik sirada harfle etiketli tek md dosyasina ve ayri anahtar json'a yazar. Cagiran: elle."""

import json
import random
import re
import string
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
KAYNAK_KLASOR = KOK / "reports/g008-ham-cevaplar"
GEMMA_DOSYA = KOK / "reports/k23-ham-cevaplar/gemma-9b.json"
KOR_KLASOR = KAYNAK_KLASOR / "kor"
KOR_MD = KOR_KLASOR / "kor.md"
ANAHTAR_JSON = KOR_KLASOR / "anahtar.json"
TOHUM = 2009  # 2007 ve 2008 onceki kor turlarinda kullanildi; ayni sira tekrar etmesin
KOSULDU = "kosuldu"
BEKLENEN_SORU = 20
MASKE = "[model]"
# Kelime icinde de yakalansin diye sinir yok ("LFM2.5", "Kumru'nun").
MODEL_ADLARI = ("Gemma", "Google", "Kumru", "VNGRS", "Jamba", "AI21", "Mamba", "LFM", "Liquid", "Qwen")
MODEL_DESENI = re.compile("|".join(re.escape(ad) for ad in MODEL_ADLARI), re.IGNORECASE)
BASLIK = ("# kor cevaplar\n\nModel adi yok. Puan olcutu: deneyler/turkce-testi.md (0/1/2). "
          "Her soruda cevaplar harfle etiketli, sira soru basina karisik.")


def json_oku(yol):
    """Dosyayi utf-8 json olarak okur."""
    return json.loads(yol.read_text(encoding="utf-8"))


def kaynaklari_topla():
    """{etiket: sinav_listesi}: kosulmus ve sinavi dolu tum kaynak dosyalari + k23 Gemma sinavi."""
    kaynaklar = {}
    for yol in sorted(KAYNAK_KLASOR.glob("*.json")):
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


def maskele(metin):
    """(maskeli_metin, sayi): model adlarini buyuk/kucuk harf duyarsiz MASKE ile degistirir."""
    return MODEL_DESENI.subn(MASKE, metin)


def korle(sorular, tohum):
    """(md_metni, anahtar, maske_sayisi): soru basina sirayi karistirir, A, B, C diye etiketler."""
    rastgele = random.Random(tohum)
    satirlar, anahtar, maske_sayisi = [BASLIK], {}, 0
    for no, kayit in sorular.items():
        satirlar.append(f"\n## Soru {no}: {kayit['soru']}")
        etiketler = sorted(kayit["cevaplar"])
        rastgele.shuffle(etiketler)
        for harf, etiket in zip(string.ascii_uppercase, etiketler):
            cevap, sayi = maskele(kayit["cevaplar"][etiket])
            maske_sayisi += sayi
            anahtar[f"{no}{harf}"] = etiket
            satirlar.append(f"### {no}{harf}\n{cevap}")
    return "\n".join(satirlar) + "\n", anahtar, maske_sayisi


def main():
    kaynaklar = kaynaklari_topla()
    metin, anahtar, maske_sayisi = korle(sorulari_birlestir(kaynaklar), TOHUM)
    KOR_KLASOR.mkdir(parents=True, exist_ok=True)
    KOR_MD.write_text(metin, encoding="utf-8")
    ANAHTAR_JSON.write_text(json.dumps(anahtar, ensure_ascii=False), encoding="utf-8")
    print(f"Kaynak: {len(kaynaklar)} ({', '.join(kaynaklar)}); cevap: {len(anahtar)}; maskeleme: {maske_sayisi}")
    print(f"Yazildi: {KOR_MD.relative_to(KOK)}, {ANAHTAR_JSON.relative_to(KOK)}")


if __name__ == "__main__":
    main()
