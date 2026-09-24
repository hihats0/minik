"""Fikir 61/64 (hece ortak birimi), metin tarafi: Turkce kelimeyi kuralla hecelere boler; kelimenin ilk
hecesi "▁" isareti alir (SentencePiece gibi). Ses ve ekran yazisi ileride ayni hece sozlugunu kullanacak.
Cagiran: araclar/hece_olc.py (sozluk ve kapsama olcumu), tests/test_az_deney.py.
"""

import re

UNLU = set("aeıioöuüAEIİOÖUÜâîûÂÎÛ")
KELIME_BASI = "▁"
PARCA = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşüâîûÂÎÛ]+|\S")


def hecele(kelime: str) -> list[str]:
    """Turkce hece kurali: iki unlu arasinda 0 unsuz -> V.V, 1 -> V.CV, 2 -> VC.CV, 3+ -> VCC.CV."""
    unluler = [i for i, h in enumerate(kelime) if h in UNLU]
    if len(unluler) < 2:
        return [kelime]
    kesimler = []
    for once, sonra in zip(unluler, unluler[1:]):
        unsuz = sonra - once - 1
        kesimler.append(sonra if unsuz == 0 else sonra - 1 if unsuz < 3 else once + 3)
    return [kelime[a:b] for a, b in zip([0] + kesimler, kesimler + [len(kelime)])]


def metni_hecele(metin: str) -> list[str]:
    """Metni hece tokenlarina: harf dizisi hecelenir, diger isaret tek token; kelime basi isaretlenir."""
    tokenlar = []
    for kelime in metin.split():
        for j, parca in enumerate(PARCA.findall(kelime)):
            heceler = hecele(parca) if parca[0].isalpha() else [parca]
            if j == 0:
                heceler[0] = KELIME_BASI + heceler[0]
            tokenlar.extend(heceler)
    return tokenlar


def birlestir(tokenlar: list[str]) -> str:
    return "".join(tokenlar).replace(KELIME_BASI, " ").strip()
