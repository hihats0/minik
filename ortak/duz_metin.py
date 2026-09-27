"""Cevap metnini duz yaziya indirir: emoji, **kalin**/*egik*, uzun tire, sahne yonergesi, "Peki ya sen?" cikar.
Cagiran: minik.py (Defter gecmisi Kafa'ya giderken ve her yeni cevapta, emoji-a, cevap-b)."""

import re

# Emoji bloklari + degisken secici (FE0F) + sifir genislik birlestirici (200D).
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")
KALIN_EGIK = re.compile(r"\*{1,2}([^*\n]+)\*{1,2}")
UZUN_TIRE = re.compile(r"\s*—\s*")
UZUN_TIRE_YERINE = ", "
FAZLA_BOSLUK = re.compile(r"[ \t]+")
FAZLA_BOS_SATIR = re.compile(r"\n{3,}")
PARANTEZ = re.compile(r"[ \t]*\(([^()\n]*)\)")
# 27 Eyl: satir basindaki her parantez, kucuk harfli olsa da ("(tatli bir gulumsemeyle)"), yonergedir.
SATIR_BASI_PARANTEZ = re.compile(r"^[ \t]*\([^()\n]*\)[ \t]*", re.MULTILINE)
# cevap-b: "(omuz silker)", "(gulumseyerek)", "(bakiyormus gibi)": hareket anlatimi fiille biter.
HAREKET_EKI = re.compile(r"(arak|erek|[ıiuüae]r|yor|[mıiuü]ş gibi)$")
PEKI_YA_SEN = re.compile(r"peki ya sen\s*\?\s*", re.IGNORECASE)


def temizle(metin):
    """Emoji, markdown isareti, sahne yonergesi ve "Peki ya sen?" siler, uzun tireyi virgule cevirir."""
    metin = EMOJI.sub("", metin)
    metin = KALIN_EGIK.sub(r"\1", metin)
    metin = UZUN_TIRE.sub(UZUN_TIRE_YERINE, metin)
    metin = SATIR_BASI_PARANTEZ.sub("", metin)
    metin = PARANTEZ.sub(lambda es: "" if _yonerge_mi(es.group(1)) else es.group(0), metin)
    metin = PEKI_YA_SEN.sub("", metin)
    satirlar = [FAZLA_BOSLUK.sub(" ", satir).strip() for satir in metin.split("\n")]
    return FAZLA_BOS_SATIR.sub("\n\n", "\n".join(satirlar)).strip()


def _yonerge_mi(icerik):
    """Parantez ici sahne yonergesi mi: buyuk harfle basliyorsa ("(Kisa bir sessizlik)") ya da fiille
    bitiyorsa. Kucuk harfli aciklama ("(yani seni kaydedemiyorum)", "(lezzetli!)") yonerge sayilmaz."""
    icerik = icerik.strip()
    return bool(icerik) and (icerik[0].isupper() or bool(HAREKET_EKI.search(icerik)))


def rol_var_mi(metin):
    """Ham cevapta sahne yonergesi ya da "peki ya sen" varsa True: boyle kayit Kafa'ya ornek olmaz."""
    if PEKI_YA_SEN.search(metin) or SATIR_BASI_PARANTEZ.search(metin):
        return True
    return any(_yonerge_mi(icerik) for icerik in PARANTEZ.findall(metin))
