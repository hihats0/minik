"""Testler icin ag acmayan sahte gomme: kelime torbasini sabit boyutlu hash vektorune cevirir.
Cagiran: tests/conftest.py (varsayilan), tests/test_hatirlama.py."""

import re
import zlib

BOYUT = 64
ONEKLER = ("passage: ", "query: ")


def kelime_torbasi(metin):
    """Ayni kok kelimeyi (ilk 4 harf) paylasan metinler benzer vektor alir."""
    for onek in ONEKLER:
        metin = metin.removeprefix(onek)
    vektor = [0.0] * BOYUT
    for kelime in re.findall(r"\w+", metin.lower()):
        vektor[zlib.crc32(kelime[:4].encode("utf-8")) % BOYUT] += 1.0
    return vektor
