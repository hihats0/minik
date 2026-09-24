"""Cevap metnini karakterin istedigi duz yaziya indirir: emoji, **kalin**/*egik* isareti, uzun tire cikar.
Cagiran: minik.py (Defter gecmisi Kafa'ya giderken ve her yeni cevapta, emoji-a)."""

import re

# Emoji bloklari + degisken secici (FE0F) + sifir genislik birlestirici (200D).
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")
KALIN_EGIK = re.compile(r"\*{1,2}([^*\n]+)\*{1,2}")
UZUN_TIRE = re.compile(r"\s*—\s*")
UZUN_TIRE_YERINE = ", "
FAZLA_BOSLUK = re.compile(r"[ \t]+")


def temizle(metin):
    """Emoji ve markdown isaretini siler, uzun tireyi virgule cevirir; kelimeler yerinde kalir."""
    metin = EMOJI.sub("", metin)
    metin = KALIN_EGIK.sub(r"\1", metin)
    metin = UZUN_TIRE.sub(UZUN_TIRE_YERINE, metin)
    satirlar = [FAZLA_BOSLUK.sub(" ", satir).strip() for satir in metin.split("\n")]
    return "\n".join(satirlar).strip()
