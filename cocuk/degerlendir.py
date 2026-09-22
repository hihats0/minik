"""D4 cocuk deneyi: egitilmis cocugu olcer: dogrulama perplexity, dilbilgisi minimal ciftleri,
eski sinav (secmeli) ve dilbilgisi baslangiclarindan acgozlu tamamlama. Cagiran: elle
`python -m cocuk.degerlendir --ad <ad>`; sonuc cocuk/agirlik/<ad>/degerlendirme.json.
"""

import argparse
import json
import math
import re
from collections import defaultdict

import sentencepiece as spm
import torch
import torch.nn.functional as F

from cocuk import egit_araclari as ea

SINAV_DIZINI = ea.COCUK_DIZINI / "sinav"
TOKENIZER_YOLU = ea.COCUK_DIZINI / "tokenizer" / "tr16k.model"
URETIM_TOKEN = 12  # dilbilgisi.json yonergesi: en fazla 12 token.
CUMLE_SONU = re.compile(r"[.!?\n]")
BOSLUK = "___"


def yukle(ad: str, cihaz):
    paket = torch.load(ea.AGIRLIK_DIZINI / ad / "son.pt", map_location=cihaz)
    model = ea.model_kur(paket["tur"], paket["ayar"]).to(cihaz)
    model.load_state_dict(paket["model"])
    return model.eval(), paket


@torch.no_grad()
def log_olasilik(model, sp, metin: str, cihaz) -> tuple[float, int]:
    """Metnin toplam log-olasiligi ve token sayisi. Egitimde paragraflar EOS ile ayrildigi icin
    metin EOS'tan sonra baslamis gibi verilir."""
    ids = torch.tensor([[sp.eos_id()] + sp.encode(metin)], device=cihaz)
    logp = F.log_softmax(model(ids[:, :-1]).float(), dim=-1)
    hedef = ids[:, 1:]
    return logp.gather(-1, hedef[..., None]).sum().item(), hedef.shape[1]


@torch.no_grad()
def perplexity(model, veri, baglam: int, pencere_sayisi: int | None, cihaz) -> dict:
    """Dogrulama verisini ortusmeyen baglam boyu pencerelere boler; ortalama kayip -> exp."""
    toplam_pencere = (len(veri) - 1) // baglam
    n = min(toplam_pencere, pencere_sayisi or toplam_pencere)
    toplam = 0.0
    for i in range(n):
        parca = torch.from_numpy(veri[i * baglam:(i + 1) * baglam + 1].astype("int64")).to(cihaz)
        toplam += ea.kayip_hesapla(model, parca[None, :-1], parca[None, 1:]).item()
    return {"pencere": n, "kayip": toplam / n, "perplexity": math.exp(toplam / n)}


def oran(sayac: dict) -> dict:
    return {k: round(v[0] / v[1], 3) for k, v in sayac.items()}


def ciftleri_puanla(model, sp, cihaz) -> dict:
    """Minimal ciftler: toplam log-olasilik (BLiMP) ve token basina ortalama, kategori bazinda."""
    ciftler = json.loads((SINAV_DIZINI / "dilbilgisi_ciftleri.json").read_text("utf-8"))["ciftler"]
    toplam_say, ortalama_say = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    for cift in ciftler:
        (d_lp, d_n), (b_lp, b_n) = (log_olasilik(model, sp, cift[k], cihaz) for k in ("dogru", "bozuk"))
        for kategori in (cift["kategori"], "hepsi"):
            toplam_say[kategori][0] += d_lp > b_lp
            ortalama_say[kategori][0] += d_lp / d_n > b_lp / b_n
            toplam_say[kategori][1] += 1
            ortalama_say[kategori][1] += 1
    return {"toplam_logp": oran(toplam_say), "token_basina_logp": oran(ortalama_say)}


def eski_sinavi_puanla(model, sp, cihaz) -> dict:
    """Her soruda dogru cevap + 3 celdirici; en yuksek toplam log-olasilik dogrudaysa 1 puan."""
    sorular = json.loads((SINAV_DIZINI / "eski_sinav.json").read_text("utf-8"))["sorular"]
    dogru = 0
    for soru in sorular:
        secenekler = [soru["kabul"][0]] + soru["celdiriciler"]
        puanlar = [log_olasilik(model, sp, soru["soru"].replace(BOSLUK, s), cihaz)[0]
                   for s in secenekler]
        dogru += puanlar.index(max(puanlar)) == 0
    return {"soru": len(sorular), "dogru": dogru, "dogruluk": round(dogru / len(sorular), 3)}


@torch.no_grad()
def tamamla(model, sp, baslangic: str, cihaz) -> str:
    """Acgozlu uretim; ilk cumle sonu isaretinde ya da EOS'ta kesilir."""
    ids = [sp.eos_id()] + sp.encode(baslangic)
    istem_boyu = len(ids)
    for _ in range(URETIM_TOKEN):
        sonraki = model(torch.tensor([ids], device=cihaz))[0, -1].argmax().item()
        if sonraki == sp.eos_id():
            break
        ids.append(sonraki)
        if CUMLE_SONU.search(sp.decode(ids[istem_boyu:])):
            break
    devam = sp.decode(ids[istem_boyu:])
    kesim = CUMLE_SONU.search(devam)
    return baslangic + (devam[:kesim.end()] if kesim else devam)


def tamamlamalari_uret(model, sp, cihaz) -> list[dict]:
    baslangiclar = json.loads((SINAV_DIZINI / "dilbilgisi.json").read_text("utf-8"))["baslangiclar"]
    return [{"baslangic": b, "cumle": tamamla(model, sp, b, cihaz).strip(), "puan": None}
            for b in baslangiclar]


def degerlendir(ad: str, pencere_sayisi: int | None, cihaz) -> dict:
    model, paket = yukle(ad, cihaz)
    sp = spm.SentencePieceProcessor(model_file=str(TOKENIZER_YOLU))
    sonuc = {"ad": ad, "tur": paket["tur"], "adim": paket["adim"], "token": paket["token"],
             "parametre": ea.parametre_sayisi(model),
             "dogrulama": perplexity(model, ea.veri_ac("dogrulama"), model.ayar["baglam"],
                                     pencere_sayisi, cihaz),
             "dilbilgisi_ciftleri": ciftleri_puanla(model, sp, cihaz),
             "eski_sinav_secmeli": eski_sinavi_puanla(model, sp, cihaz)}
    cikti = ea.AGIRLIK_DIZINI / ad
    tamamlamalar = tamamlamalari_uret(model, sp, cihaz)
    (cikti / "tamamlamalar.json").write_text(
        json.dumps(tamamlamalar, ensure_ascii=False, indent=1), encoding="utf-8")
    (cikti / "degerlendirme.json").write_text(
        json.dumps(sonuc, ensure_ascii=False, indent=1), encoding="utf-8")
    return sonuc


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ad", required=True)
    p.add_argument("--pencere", type=int, default=None, help="perplexity pencere siniri; yoksa hepsi")
    p.add_argument("--cihaz", default="cuda" if torch.cuda.is_available() else "cpu")
    arg = p.parse_args()
    print(json.dumps(degerlendir(arg.ad, arg.pencere, torch.device(arg.cihaz)),
                     ensure_ascii=False, indent=1))
