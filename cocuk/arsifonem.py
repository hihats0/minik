"""T1 deneyi (arsifonem dili): tr16k tokenlarinda kelime ici (ek) parcalarin unlu uyumu ve d/t
sertlesmesi kurala birakilir: parca kuralla yeniden uretilebiliyorsa soyut bicimine (lar/ler -> lAr,
da/de/ta/te -> DA) cevrilir, uretilemiyorsa (istisna, alinti) oldugu gibi kalir. Cagiran:
cocuk/arsifonem_veri.py (donusum), cocuk/az_olc.py (ArsifonemSP ile olcum), tests/test_az_deney.py.
"""

import sentencepiece as spm

KALIN = set("aıou")
INCE = set("eiöü")
UNLU = KALIN | INCE
SERT = set("fstkçşhp")  # fıstıkçı şahap: bunlardan sonra d -> t
A_ARSI, I_ARSI, D_ARSI = "A", "I", "D"
KELIME_BASI = "▁"


def soyutla(parca: str) -> str:
    """Yuzey parcayi soyut bicime: a/e -> A, ı/i/u/ü -> I, bastaki d/t -> D."""
    soyut = "".join(A_ARSI if h in "ae" else I_ARSI if h in "ıiuü" else h for h in parca)
    if soyut[:1] in ("d", "t"):
        soyut = D_ARSI + soyut[1:]
    return soyut


def gerceklestir(soyut: str, onceki: str) -> str:
    """Soyut parcayi kelimenin o ana kadarki yuzey metnine (onceki) gore yuzeye cevirir."""
    cikti = []
    for i, h in enumerate(soyut):
        baglam = onceki + "".join(cikti)
        son_unlu = next((c for c in reversed(baglam.lower()) if c in UNLU), "e")
        if h == A_ARSI:
            h = "a" if son_unlu in KALIN else "e"
        elif h == I_ARSI:
            h = {"a": "ı", "ı": "ı", "e": "i", "i": "i", "o": "u", "u": "u", "ö": "ü", "ü": "ü"}[son_unlu]
        elif h == D_ARSI and i == 0:
            h = "t" if baglam[-1:].lower() in SERT else "d"
        cikti.append(h)
    return "".join(cikti)


class Donusturucu:
    """tr16k id dizisi <-> arsifonem id dizisi. Yeni idler 16000'den baslar (soyut parcalar)."""

    def __init__(self, sp: spm.SentencePieceProcessor):
        self.sp = sp
        self.parca = [sp.id_to_piece(i) for i in range(sp.get_piece_size())]
        adaylar = sorted({soyutla(p) for p in self.parca if self._ek_mi(p) and soyutla(p) != p})
        self.soyut_id = {s: sp.get_piece_size() + i for i, s in enumerate(adaylar)}
        self.soyut_parca = {i: s for s, i in self.soyut_id.items()}
        self.sozluk = sp.get_piece_size() + len(adaylar)

    def _ek_mi(self, parca: str) -> bool:
        return not parca.startswith(KELIME_BASI) and parca.isalpha() and parca.islower()

    def cevir(self, ids: list[int]) -> list[int]:
        """Her ek parcasi, kural onu ayni yuzeye geri getiriyorsa soyut idye cevrilir."""
        cikti, kelime = [], ""
        for i in ids:
            p = self.parca[i]
            if p.startswith(KELIME_BASI) or not self._ek_mi(p):
                kelime = p.lstrip(KELIME_BASI) if p.startswith(KELIME_BASI) else kelime + p
                cikti.append(i)
                continue
            s = soyutla(p)
            kural_tutar = s in self.soyut_id and gerceklestir(s, kelime) == p
            cikti.append(self.soyut_id[s] if kural_tutar else i)
            kelime += p
        return cikti

    def geri(self, ids: list[int]) -> list[int]:
        """Soyut idleri, kelimenin onceki yuzeyine gore tr16k idlerine geri cevirir."""
        cikti, kelime = [], ""
        for i in ids:
            p = self.parca[i] if i < len(self.parca) else gerceklestir(self.soyut_parca[i], kelime)
            yuzey_id = i if i < len(self.parca) else self.sp.piece_to_id(p)
            kelime = p.lstrip(KELIME_BASI) if p.startswith(KELIME_BASI) else kelime + p
            cikti.append(yuzey_id)
        return cikti


class ArsifonemSP:
    """degerlendir.py'nin bekledigi encode/decode/eos_id arayuzu, arsifonem idleriyle."""

    def __init__(self, sp, donusturucu: Donusturucu):
        self.sp, self.d = sp, donusturucu

    def eos_id(self):
        return self.sp.eos_id()

    def encode(self, metin: str) -> list[int]:
        return self.d.cevir(self.sp.encode(metin))

    def decode(self, ids: list[int]) -> str:
        return self.sp.decode(self.d.geri(list(ids)))
