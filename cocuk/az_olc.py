"""Az-veri deneyi: egitilmis cocugu olcer: dogrulama kaybi (D4'le ayni 200 pencere), dilbilgisi
ciftleri, eski sinav ve 40 tamamlama (bosluk hatasi duzeltilmis) + otomatik tamamlama olculeri.
Cagiran: araclar/az_deney_kosu.py ya da `python -m cocuk.az_olc --ad <ad>`; sonuc <ad>/az_olcum.json.
"""

import argparse
import collections
import json
import re

import sentencepiece as spm
import torch

from cocuk import degerlendir as dg
from cocuk import egit_araclari as ea
from cocuk.arsifonem import ArsifonemSP, Donusturucu

DOGRULAMA_PENCERE = 200  # cocuk/egit.py ile ayni pencereler, D4 kaybiyla dogrudan kiyas
DOGRULAMA_BATCH = 16
SOZLUK_YOLU = ea.VERI_DIZINI / "kelime_sozlugu.json"
SOZLUK_ESIGI = 20  # egitim metninde en az 20 kez gecen kelime "gercek kelime" sayilir
KELIME = re.compile(r"[A-Za-zÇĞİÖŞÜçğıöşüâîû']+")
RAKAM = re.compile(r"\d")


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


def olc(ad: str, cihaz, arsifonem: bool = False) -> dict:
    """arsifonem: T1 modeli; sinav metinleri arsifonem idlerine cevrilir, dogrulama ayni konumlarda."""
    model, paket = dg.yukle(ad, cihaz)
    sp = spm.SentencePieceProcessor(model_file=str(dg.TOKENIZER_YOLU))
    if arsifonem:  # ayni sinif arayuzu: encode/decode/eos_id
        sp = ArsifonemSP(sp, Donusturucu(sp))
    amp = cihaz.type == "cuda"
    kayip = ea.dogrulama_kaybi(model, ea.veri_ac("dogrulama" + ("_ars" if arsifonem else "")),
                               model.ayar["baglam"],
                               DOGRULAMA_BATCH, DOGRULAMA_PENCERE, cihaz, amp)
    baslangiclar = json.loads((dg.SINAV_DIZINI / "dilbilgisi.json").read_text("utf-8"))["baslangiclar"]
    cumleler = [tamamla(model, sp, b, cihaz).strip() for b in baslangiclar]
    sonuc = {"ad": ad, "token": paket["token"], "dogrulama_kaybi": round(kayip, 4),
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
    p.add_argument("--arsifonem", action="store_true")
    a = p.parse_args()
    s = olc(a.ad, torch.device(a.cihaz), a.arsifonem)
    print(json.dumps({k: v for k, v in s.items() if k != "cumleler"}, ensure_ascii=False))
