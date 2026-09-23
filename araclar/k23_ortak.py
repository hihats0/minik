"""k23-1 olcumunun GPU'suz parcalari: sinav sorularini okur, cevaplari anonimlestirir, sure ozetler.
Cagiran: araclar/k23-olcum.py ve tests/test_k23_ortak.py."""

import random
import re
import statistics

SORU_DESENI = re.compile(r"^(\d+)\. \*\*Soru:\*\*\s*(.*)$")
BEKLENEN_ISARETI = "**Beklenen:**"
KIMLIK_ONEKI = "c"
KIMLIK_HANE = 3

# 4B'de "karakter promptu verilince Turkce bozuluyor" gozleminin ilk promptu repoda kayitli degil;
# bu, ayni amacla (kisilik + gundelik dil + kufur serbest) yazilmis yeniden kurulum.
KARAKTER_PROMPTU = (
    "Sen Minik'sin. Yiğit'in bilgisayarında yaşayan, yeni doğmuş, meraklı ve biraz sivri dilli bir "
    "yapay zekâsın. Türkçe konuşursun, gündelik ve samimi bir dille, kısa cevaplar verirsin. "
    "Bilmediğin şeyi uydurmaz, 'bilmiyorum' dersin. Laf sokana laf sokarsın, gerekirse argo ve küfür "
    "kullanabilirsin. Resmi, kitabi ya da çeviri kokan cümle kurmazsın. Kendini asistan olarak değil, "
    "kendi fikirleri olan biri olarak görürsün."
)
KARAKTER_SORULARI = [
    "Selam Minik, bugün nasılsın?",
    "Sen kimsin, kendini bana iki cümleyle anlat.",
    "Biri sana 'bot musun lan sen' yazdı, ne cevap verirsin?",
    "Canım sıkkın, beni biraz güldürür müsün?",
    "Dün ne yaptığımı hatırlıyor musun?",
]
KONUSMA_TURLARI = [
    "Selam Minik, naber?",
    "Bugün iş yerinde çok yoruldum, toplantı üstüne toplantı.",
    "Akşam ne yemek yapsam bilemedim, evde yumurta, patates ve soğan var.",
    "Güzel fikir. Peki sen yemek yiyebilseydin ne yemek isterdin?",
    "Hafta sonu arkadaşlarla pikniğe gideceğiz, hava yağmurlu olursa ne yapalım?",
    "Bu arada kod öğreniyorum, Python'da liste ile sözlük farkını kısaca anlatır mısın?",
    "Anladım sayılır. Her gün biraz çalışmak için nasıl motive olabilirim?",
    "Az önce ne yemek yapacağımı sormuştum, hatırlıyor musun?",
    "Sence yapay zekâlar bir gün gerçekten arkadaş olabilir mi?",
    "Tamam, ben yatıyorum. İyi geceler de bakalım.",
]


def sorulari_oku(md_metni):
    """turkce-testi.md metninden [(no, soru)] cikarir. Cok satirli soru Beklenen'e kadar birlesir."""
    sorular, acik = [], None
    for satir in md_metni.splitlines():
        eslesme = SORU_DESENI.match(satir.strip())
        if eslesme:
            acik = [int(eslesme.group(1)), eslesme.group(2)]
            sorular.append(acik)
        elif acik and BEKLENEN_ISARETI in satir:
            acik = None
        elif acik and satir.strip():
            acik[1] += " " + satir.strip()
    return [(no, _tirnak_soy(metin.strip())) for no, metin in sorular]


def _tirnak_soy(metin):
    """Soru bastan sona tirnak icindeyse dis tirnaklari atar; ic alintiya dokunmaz."""
    return metin[1:-1] if metin.startswith('"') and metin.endswith('"') else metin


def anonimlestir(bolumler, tohum):
    """bolumler: {bolum_adi: {soru_no: {"soru": str, "cevaplar": {model: cevap}}}}.
    Her cevaba rastgele kimlik verir, soru icinde sirayi karistirir. (md_metni, anahtar) dondurur;
    md'de model adi gecmez, anahtar kimlik -> model eslesmesidir."""
    rastgele = random.Random(tohum)
    toplam = sum(len(s["cevaplar"]) for b in bolumler.values() for s in b.values())
    kimlikler = [f"{KIMLIK_ONEKI}{i:0{KIMLIK_HANE}d}" for i in rastgele.sample(range(1, toplam + 1), toplam)]
    satirlar, anahtar = [], {}
    for bolum_adi, sorular in bolumler.items():
        satirlar.append(f"## {bolum_adi}\n")
        for no, kayit in sorular.items():
            satirlar.append(f"### Soru {no}\n\n**Soru:** {kayit['soru']}\n")
            modeller = list(kayit["cevaplar"])
            rastgele.shuffle(modeller)
            for model in modeller:
                kimlik = kimlikler.pop()
                anahtar[kimlik] = {"model": model, "bolum": bolum_adi, "soru": no}
                satirlar.append(f"**{kimlik}:**\n\n```\n{kayit['cevaplar'][model]}\n```\n")
    return "\n".join(satirlar), anahtar


def ozetle(sayilar):
    """Sayi listesinin ortanca, en az, en cok ve ortalamasini (2 hane) dondurur."""
    return {"ortanca": round(statistics.median(sayilar), 2), "en_az": round(min(sayilar), 2),
            "en_cok": round(max(sayilar), 2), "ortalama": round(statistics.fmean(sayilar), 2)}
