"""f3-g anonim cevaplarinda mod/ayar/meta izi arar, eslesen kaydi silmeden anahtar.json'da isaretler.
Cagiran: deneyler/f3g-kor-uretim.py (480 kayit bitince), tests/test_f3g_uretim.py."""

import json
import re

# Anonim cevapta mod/ayar/meta izi (Gemma sayilari: dinlenme hormonunda uyanik 448+768=1216, yorgun 224+768=992
# max_tokens; sicaklik 0,64/0,448). Eslesen kayit silinmez, anahtar.json'da "sizinti": true ile isaretlenir.
SIZINTI_DESENI = re.compile(
    r"uyan[ıi]k|yorgun|\bmod(u|da|unda|undayim|undayım)?\b|talimat|\(\s*not\s*:|\*\(|\d+\s*karakter"
    r"|karakter (say[ıi]s[ıi]|s[ıi]n[ıi]r[ıi])|se[çc]enek\s*\d|temperature|top_p|repeat_penalty|max_tokens|seed|tohum"
    r"|\b(1216|992|768|0[.,]64|0[.,]448|0[.,]836|1[.,]03)\b", re.IGNORECASE)


def isaretle(klasor):
    """Anonim dosyadaki her kaydin cevabini SIZINTI_DESENI ile tarar; eslesenleri anahtar.json'da isaretler,
    sayiyi ve ilk satirlari basar. Kayit silinmez: karar puanlamadan once verilir. Eslesen sayisini dondurur."""
    metin = (klasor / "anonim-cevaplar.md").read_text(encoding="utf-8")
    anahtar_yolu = klasor / "anahtar.json"
    anahtarlar = json.loads(anahtar_yolu.read_text(encoding="utf-8"))
    eslesen = 0
    for parca in metin.split("## Kayit ")[1:]:
        kimlik, _, govde = parca.partition("\n")
        bulunan = SIZINTI_DESENI.search(govde.split("**Cevap:**", 1)[-1])
        anahtarlar[kimlik]["sizinti"] = bool(bulunan)
        if bulunan:
            eslesen += 1
            print(f"  {kimlik}: '{bulunan.group(0)}'", flush=True)
    anahtar_yolu.write_text(json.dumps(anahtarlar, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[sizinti] {eslesen}/{len(anahtarlar)} kayit isaretlendi", flush=True)
    return eslesen
