"""k23-2b: bir cevabin Turkce olup olmadigini ve asistan kalibi / emoji / markdown sayisini kaba kurallarla sayar.
Cagiran: araclar/k23-2b-turkce-uctan-uca.py, tests/test_k23_2b_sayim.py."""

import re

# Turkceye ozgu harfler ve en sik gecen kisa kelimeler; ikisinden biri yeterli sayida varsa "Turkce" denir.
TURKCE_HARFLER = set("çğıöşüÇĞİÖŞÜ")
TURKCE_KELIMELER = {"bir", "ve", "bu", "da", "de", "ne", "ben", "sen", "mi", "mı", "için", "ama", "çok", "var", "yok", "gibi"}
INGILIZCE_KELIMELER = {"the", "and", "is", "you", "are", "what", "this", "that", "of", "to"}
ASISTAN_KALIPLARI = [r"size nasıl yardımcı", r"yardımcı olabilir", r"bir yapay zeka", r"yapay zeka (asistanı|modeli)",
                     r"dil modeli", r"umarım (bu )?yardımcı", r"başka bir sorunuz", r"memnuniyetle", r"elbette[!,]"]
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
MARKDOWN = re.compile(r"(\*\*[^*]+\*\*|^#{1,6} |^\s*[-*] |^\s*\d+\. |`)", re.MULTILINE)


def turkce_mi(metin):
    """Turkce harf ya da Turkce sik kelime sayisi Ingilizce sik kelime sayisindan fazlaysa True."""
    kelimeler = re.findall(r"\w+", metin.lower())
    turkce = sum(k in TURKCE_KELIMELER for k in kelimeler) + sum(h in TURKCE_HARFLER for h in metin)
    ingilizce = sum(k in INGILIZCE_KELIMELER for k in kelimeler)
    return turkce > ingilizce


def say(metin):
    """Tek cevap icin sozluk: turkce, asistan kalibi, emoji ve markdown isareti sayisi."""
    kucuk = metin.lower()
    return {"turkce": turkce_mi(metin),
            "asistan": sum(bool(re.search(k, kucuk)) for k in ASISTAN_KALIPLARI),
            "emoji": len(EMOJI.findall(metin)),
            "markdown": len(MARKDOWN.findall(metin))}
