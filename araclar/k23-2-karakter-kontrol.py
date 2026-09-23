"""k23-2 olcum hazirligi: f0'in 20 sorusundan 5'ini Kafa'ya karakterli ve karaktersiz sorar,
cevaplari yan yana bir md dosyasina yazar (Turkce bozuluyor mu gozle bakmak icin).
Cagiran: elle, llama-server 4B ile 8080'de acikken. GPU'yu kendisi baslatmaz."""

import json
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from ortak.ayar import KAFA_MAX_TOKEN, KAFA_SICAKLIK, KAFA_TOP_P, KAFA_UC, KAFA_ZAMAN_ASIMI_SN, KARAKTER_DOSYASI

KOK = Path(__file__).resolve().parent.parent
F0_CEVAPLARI = KOK / "reports" / "f0-ham-cevaplar" / "qwen3.5-4b.md"
CIKTI = KOK / "reports" / "k23-2-karakter-kontrol-ham.md"
# 20 sorudan esit aralikli 5'i: farkli soru tiplerine (tweet, sohbet, bilgi, ceviri) denk gelsin.
SECILEN_SIRALAR = [1, 5, 9, 13, 17]
SORU_KALIBI = re.compile(r"\*\*Soru:\*\* (.+)")


def f0_sorulari():
    """f0 ham cevap dosyasindaki soru satirlarini sirayla dondurur."""
    return SORU_KALIBI.findall(F0_CEVAPLARI.read_text(encoding="utf-8"))


def sor(soru, sistem):
    """Tek istek yollar; sistem None ise sistem mesaji yok. Cevap metnini dondurur."""
    mesajlar = ([{"role": "system", "content": sistem}] if sistem else []) + [{"role": "user", "content": soru}]
    govde = {"messages": mesajlar, "temperature": KAFA_SICAKLIK, "top_p": KAFA_TOP_P, "max_tokens": KAFA_MAX_TOKEN}
    istek = urllib.request.Request(KAFA_UC, data=json.dumps(govde, ensure_ascii=False).encode("utf-8"),
                                   headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(istek, timeout=KAFA_ZAMAN_ASIMI_SN) as yanit:
        return json.loads(yanit.read().decode("utf-8"))["choices"][0]["message"]["content"]


def main():
    karakter = KARAKTER_DOSYASI.read_text(encoding="utf-8").strip()
    sorular = f0_sorulari()
    satirlar = ["# k23-2 karakter kontrolu (ham)\n"]
    for sira in SECILEN_SIRALAR:
        soru = sorular[sira - 1]
        satirlar.append(f"## Soru {sira}\n\n**Soru:** {soru}\n")
        satirlar.append(f"**Karaktersiz:**\n\n```\n{sor(soru, None)}\n```\n")
        satirlar.append(f"**Karakterli:**\n\n```\n{sor(soru, karakter)}\n```\n")
    CIKTI.write_text("\n".join(satirlar), encoding="utf-8")
    print(f"yazildi: {CIKTI}")


if __name__ == "__main__":
    main()
