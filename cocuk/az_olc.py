"""Az-veri deneyi: egitilmis cocugu olcer: dogrulama kaybi (D4'le ayni 200 pencere), dilbilgisi
ciftleri, eski sinav ve 40 tamamlama (bosluk hatasi duzeltilmis) + otomatik tamamlama olculeri.
Cagiran: araclar/az_deney_kosu.py ya da `python -m cocuk.az_olc --ad <ad>`; sonuc <ad>/az_olcum.json.
"""

import argparse
import collections
import json
import math
import re

import sentencepiece as spm
import torch

from cocuk import degerlendir as dg
from cocuk import egit_araclari as ea
from cocuk.arsifonem import ArsifonemSP, Donusturucu
from cocuk.hece_token import HeceTokenizer

DOGRULAMA_PENCERE = 200  # cocuk/egit.py ile ayni pencereler, D4 kaybiyla dogrudan kiyas
DOGRULAMA_BATCH = 16
SOZLUK_YOLU = ea.VERI_DIZINI / "kelime_sozlugu.json"
SOZLUK_ESIGI = 20  # egitim metninde en az 20 kez gecen kelime "gercek kelime" sayilir
KELIME = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşüâîû']+")
RAKAM = re.compile(r"\d")
BPC_PARAGRAF = 2000  # dogrulama.txt'nin ilk 2000 paragrafi; farkli tokenizerli modeller ayni metinde
BPC_PENCERE = 512


@torch.no_grad()
def tamamla(model, sp, baslangic: str, cihaz) -> str:
    """D4'teki tamamla ile ayni acgozlu uretim; fark: metin butun id'lerden cozulur. D4 devami ayri
    cozup baslangica yapistiriyordu, SentencePiece bastaki bosluk isaretini dusurdugu icin
    'Ben okula gitti.' puanlayiciya 'Ben okulagitti.' diye gidiyordu."""
    ids = [sp.eos_id()] + sp.encode(baslangic)
    for _ in range(dg.URETIM_TOKEN):
        sonraki = model(torch.tensor([ids], device=cihaz))[0, -1].argmax().item()
        if sonraki == sp.eos_id():
            break
        ids.append(sonraki)
        if dg.CUMLE_SONU.search(sp.decode(ids[1:])[len(baslangic):]):
            break
    metin = sp.decode(ids[1:])
    kesim = dg.CUMLE_SONU.search(metin, len(baslangic))
    return metin[:kesim.end()] if kesim else metin


def sozluk_kur() -> set:
    """Egitim metninin kelime sayimi (kucuk harf); bir kez kurulur, dosyada saklanir."""
    if SOZLUK_YOLU.exists():
        return set(json.loads(SOZLUK_YOLU.read_text("utf-8")))
    sayac = collections.Counter()
    with open(ea.VERI_DIZINI / "egitim.txt", encoding="utf-8") as f:
        for satir in f:
            sayac.update(k.lower() for k in KELIME.findall(satir))
    kelimeler = sorted(k for k, n in sayac.items() if n >= SOZLUK_ESIGI)
    SOZLUK_YOLU.write_text(json.dumps(kelimeler, ensure_ascii=False), encoding="utf-8")
    return set(kelimeler)


def tamamlama_olculeri(cumleler: list[str], baslangiclar: list[str], sozluk: set) -> dict:
    """Uretilen kisimda: gercek kelime orani, rakam iceren cumle, cumle sonuyla biten cumle."""
    kelime = gercek = rakamli = biten = 0
    for cumle, bas in zip(cumleler, baslangiclar):
        devam = cumle[len(bas):]
        kelimeler = [k.lower() for k in KELIME.findall(devam)]
        kelime += len(kelimeler)
        gercek += sum(k in sozluk for k in kelimeler)
        rakamli += bool(RAKAM.search(devam))
        biten += bool(dg.CUMLE_SONU.search(devam))
    n = len(cumleler)
    return {"gercek_kelime_orani": round(gercek / max(1, kelime), 3), "rakamli": rakamli,
            "cumle_bitti": biten, "toplam": n}


@torch.no_grad()
def bpc(model, sp, cihaz) -> float:
    """Karakter basina bit: tokenizer'dan bagimsiz, farkli sozluklu modeller ayni metinde kiyaslanir."""
    with open(ea.VERI_DIZINI / "dogrulama.txt", encoding="utf-8") as f:
        paragraflar = [s.strip() for _, s in zip(range(BPC_PARAGRAF), f)]
    ids = [i for p in paragraflar for i in [sp.eos_id()] + sp.encode(p)]
    karakter = sum(len(p) + 1 for p in paragraflar)  # +1: paragraf ayraci
    toplam = 0.0
    for bas in range(0, len(ids) - 1, BPC_PENCERE):
        parca = torch.tensor([ids[bas:bas + BPC_PENCERE + 1]], device=cihaz)
        toplam += ea.kayip_hesapla(model, parca[:, :-1], parca[:, 1:]).item() * (parca.shape[1] - 1)
    return toplam / karakter / math.log(2)


def sozluk_sec(tur: str):
    """tr16k (taban), arsifonem (T1) ya da hece (fikir 1); ayni encode/decode/eos_id arayuzu."""
    sp = spm.SentencePieceProcessor(model_file=str(dg.TOKENIZER_YOLU))
    if tur == "arsifonem":
        return ArsifonemSP(sp, Donusturucu(sp)), "_ars"
    if tur == "hece":
        return HeceTokenizer(), "_hece"
    return sp, ""


def olc(ad: str, cihaz, sozluk: str = "tr16k") -> dict:
    model, paket = dg.yukle(ad, cihaz)
    sp, veri_eki = sozluk_sec(sozluk)
    amp = cihaz.type == "cuda"
    kayip = ea.dogrulama_kaybi(model, ea.veri_ac("dogrulama" + veri_eki),
                               model.ayar["baglam"],
                               DOGRULAMA_BATCH, DOGRULAMA_PENCERE, cihaz, amp)
    baslangiclar = json.loads((dg.SINAV_DIZINI / "dilbilgisi.json").read_text("utf-8"))["baslangiclar"]
    cumleler = [tamamla(model, sp, b, cihaz).strip() for b in baslangiclar]
    sonuc = {"ad": ad, "token": paket["token"], "dogrulama_kaybi": round(kayip, 4),
             "bpc": round(bpc(model, sp, cihaz), 4),
             "dilbilgisi_ciftleri": dg.ciftleri_puanla(model, sp, cihaz),
             "eski_sinav": dg.eski_sinavi_puanla(model, sp, cihaz),
             "tamamlama": tamamlama_olculeri(cumleler, baslangiclar, sozluk_kur()),
             "cumleler": cumleler}
    (ea.AGIRLIK_DIZINI / ad / "az_olcum.json").write_text(
        json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    return sonuc


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ad", required=True)
    p.add_argument("--cihaz", default="cuda" if torch.cuda.is_available() else "cpu")
    p.add_argument("--sozluk", choices=("tr16k", "arsifonem", "hece"), default="tr16k")
    a = p.parse_args()
    s = olc(a.ad, torch.device(a.cihaz), a.sozluk)
    print(json.dumps({k: v for k, v in s.items() if k != "cumleler"}, ensure_ascii=False))
