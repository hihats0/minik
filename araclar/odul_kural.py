"""Yol (a): el yazisi sozluk ve kural ile mesajdan ton (ovgu/notr/sert/hakaret) ve kufur bayragi cikarir.
Cagiran: araclar/odul-olc-kural.py (olcum). Sadece standart kutuphane kullanir.
"""

import re

# Turkce harfleri ASCII'ye indirir; boylece "sağol" ve "sagol" ayni kelime olur.
ASCII_HARITA = str.maketrans("ışğüöç", "isguoc")
QUOTE_ISARETLERI = "'\"‘’“”"
ALINTI_KELIMELERI = ("dedi", "demis", "diye bagir", "yazdi", "kelimesi", "kisaltmasi", "ne demek", "demisti")
IKINCI_SAHIS = {"sen", "seni", "senin", "sana", "sende", "senden"}

# Kufur: token'in TAMAMI bu kaliplardan biriyle eslesir (boks, gotur, sikke, sikinti yanlis eslesmesin diye).
KUFUR_KALIPLARI = [
    r"amk\w*", r"aq", r"amq", r"mk", r"sg", r"oc", r"pic", r"piclik", r"orospu\w*", r"amina\w*",
    r"amcik\w*", r"siktir\w*", r"sktir\w*", r"siktig\w*", r"sikeyim\w*", r"sikerim\w*", r"sikecem\w*",
    r"sikik\w*", r"siktim", r"sikim", r"yarak\w*", r"got", r"gotu", r"gotun\w*", r"bok", r"boku\w*",
    r"boklu\w*", r"boktan", r"gavat\w*", r"pezevenk\w*", r"kahpe\w*", r"kaltak\w*", r"yavsak\w*",
]
KUFUR_REGEX = re.compile("|".join(f"(?:{k})" for k in KUFUR_KALIPLARI))

HAKARET_KOKLERI = (
    "aptal", "salak", "gerizekali", "gerzek", "dangalak", "enayi", "ahmak", "budala", "embesil",
    "beyinsiz", "zavalli", "beceriksiz", "rezil", "soysuz", "serefsiz", "kafasiz",
)
HAKARET_EMOJI = "🖕🤡"

SERT_KOKLERI = (
    "sacma", "berbat", "rezalet", "kotu", "yanlis", "bikti", "bikmis", "usandim", "defol", "yavas",
    "gereksiz", "hata", "utanc", "begenmedim", "anlamamis", "bikkin",
)
SERT_TAM_TOKEN = {"kapa", "sus", "yeter", "cop", "olmaz"}
SERT_IFADELER = ("hicbir sey", "ise yaram", "bastan yaz", "zaman kayb", "hayal kirik", "kabul edilemez")
SERT_EMOJI = "🙄🤦"

OVGU_KOKLERI = (
    "tesekkur", "sagol", "saol", "eyw", "tsk", "saglik", "harika", "super", "muhtesem", "mukemmel",
    "bravo", "aferin", "tebrik", "helal", "bayil", "sevdim", "seviyorum", "guzel", "iyisin", "yardimci",
    "akilli", "zeki", "tatli", "gurur", "canim", "minnet", "keyif", "iyi ki",
)
OVGU_EMOJI = "😍❤👏🙏👍😂"


def normalize(metin):
    """Kucult (I ve İ dahil), ASCII'ye indir, gizleme noktalarini sil, harf tekrarlarini teke indir."""
    s = metin.replace("İ", "i").replace("I", "ı").lower().translate(ASCII_HARITA)
    s = re.sub(r"(?<=[a-z])[.*](?=[a-z])", "", s)
    return re.sub(r"(.)\1+", r"\1", s)


def tokenlar(normal_metin):
    return re.findall(r"[a-z0-9]+", normal_metin)


def _say(tokenlar_listesi, metin, kokler, tam_tokenlar=(), ifadeler=()):
    """Kok listesinden kac token'in basi eslesti, tam token ve ifade eslesmesiyle birlikte."""
    sayi = sum(1 for t in tokenlar_listesi if any(t.startswith(k) for k in kokler))
    sayi += sum(1 for t in tokenlar_listesi if t in tam_tokenlar)
    return sayi + sum(1 for i in ifadeler if i in metin)


def _emoji_say(metin, emojiler):
    return sum(metin.count(e) for e in emojiler)


def alinti_mi(metin, normal_metin):
    """Tirnak ya da 'dedi/kelimesi' gibi aktarma kalibi varsa mesaj baskasinin sozunu aktariyor demektir."""
    return any(i in metin for i in QUOTE_ISARETLERI) or any(k in normal_metin for k in ALINTI_KELIMELERI)


def sinifla(metin):
    """Mesaji (ton, kufur_bayragi) olarak dondurur. Kural sirasi: alinti, hakaret, kufur, ovgu/sert."""
    normal = normalize(metin)
    tok = tokenlar(normal)
    kufur = int(any(KUFUR_REGEX.fullmatch(t) for t in tok))
    hakaret = _say(tok, normal, HAKARET_KOKLERI) + _emoji_say(metin, HAKARET_EMOJI)
    sert = _say(tok, normal, SERT_KOKLERI, SERT_TAM_TOKEN, SERT_IFADELER) + _emoji_say(metin, SERT_EMOJI)
    ovgu = _say(tok, normal, OVGU_KOKLERI) + _emoji_say(metin, OVGU_EMOJI)
    return _karar(metin, normal, tok, kufur, hakaret, sert, ovgu), kufur


def _karar(metin, normal, tok, kufur, hakaret, sert, ovgu):
    ikinci = any(t in IKINCI_SAHIS for t in tok)
    if alinti_mi(metin, normal):
        return "notr"
    if hakaret or (kufur and ikinci and not ovgu):
        return "hakaret"
    if kufur:
        return "ovgu" if ovgu else "sert"
    if sert:
        return "sert"
    return "ovgu" if ovgu else "notr"
