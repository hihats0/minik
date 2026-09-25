"""Sohbet tohumu v0: D4'un Vikipedi'yle 200M token egitilmis modeli, Gemma'nin yazdigi sade sohbetlerle
ince ayarlanir (unutmasin diye %25 Vikipedi karisik), sonra CPU'da 10 sabit acilisla konusturulur ve
CPU hizi olculur. Cagiran: araclar/tohum_sonra.sh (sohbet uretimi bitince) ya da elle
`python -m cocuk.tohum_sohbet`. Cikti: cocuk/agirlik/tohum-v0/{son.pt, konusma.json}.
"""

import json
import re
import time

import numpy as np
import sentencepiece as spm
import torch

from cocuk import degerlendir as dg
from cocuk import egit_araclari as ea

TABAN = "d4-transformer"
AD = "tohum-v0"
ADIM = 1500
BATCH, BAGLAM = 16, 256
VIKIPEDI_PAYI = 0.25  # unutmaya karsi capa (D4 gece dersi karisimindaki Vikipedi payi ile ayni fikir)
LR = 3e-4
URETIM_TOKEN = 40
SICAKLIK, TOHUM = 0.8, 1
SICAKLIK_ARALIGI = 25  # adim; durak olmadan GPU 91 C'ye cikti (25 Eyl)
SAHNE_NOTU = re.compile(r"\s*\([^)]*\)")  # Gemma bazen "(Gulerek)" gibi sahne notu yaziyor
ACILISLAR = ["A: Merhaba, adın ne?", "A: Bugün ne yaptın?", "A: En sevdiğin hayvan hangisi?",
             "A: Karnım acıktı.", "A: Yağmur yağıyor, dışarı çıkalım mı?", "A: Okulda ne öğrendin?",
             "A: Neden gökyüzü mavi?", "A: Bana bir oyun öner.", "A: Çok yorgunum.", "A: Beni seviyor musun?"]


def sohbet_idleri(sp) -> np.ndarray:
    """Her sohbet tek satir: 'A: ... B: ...' + EOS; replikler bosluklu dizilir (tr16k'da satir sonu yok)."""
    ids = []
    for satir in (ea.VERI_DIZINI / "sohbet.jsonl").read_text("utf-8").splitlines():
        metin = SAHNE_NOTU.sub("", " ".join(json.loads(satir)["replikler"]))
        ids.extend(sp.encode(metin) + [sp.eos_id()])
    return np.array(ids, dtype=np.int64)


def pencere(veri, adet, uretec, cihaz):
    baslar = uretec.integers(0, len(veri) - BAGLAM - 1, size=adet)
    parca = torch.from_numpy(np.stack([np.asarray(veri[s:s + BAGLAM + 1], dtype=np.int64) for s in baslar]))
    return parca[:, :-1].to(cihaz), parca[:, 1:].to(cihaz)


def ince_ayar(model, sohbet, cihaz) -> dict:
    vikipedi, uretec = ea.veri_ac("egitim"), np.random.default_rng(TOHUM)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=0.1)
    capa = round(BATCH * VIKIPEDI_PAYI)
    baslangic = time.time()
    for adim in range(ADIM):
        xs, ys = pencere(sohbet, BATCH - capa, uretec, cihaz)
        xv, yv = pencere(vikipedi, capa, uretec, cihaz)
        with torch.autocast(cihaz.type, dtype=torch.bfloat16, enabled=cihaz.type == "cuda"):
            kayip = ea.kayip_hesapla(model, torch.cat([xs, xv]), torch.cat([ys, yv]))
        kayip.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()
        opt.zero_grad(set_to_none=True)
        if cihaz.type == "cuda" and adim % SICAKLIK_ARALIGI == 0:
            ea.soguyana_kadar_bekle(lambda satir: None)  # 80 C'de durakla, 70'te devam
    return {"adim": ADIM, "son_kayip": round(kayip.item(), 4), "sure_sn": round(time.time() - baslangic)}


@torch.no_grad()
def konus(model, sp, acilis: str, uretec: torch.Generator) -> str:
    """Acilistan sonra ' B:' ile model cevaplar; ornekleme, ' A:' ya da EOS gelince durur."""
    ids = [sp.eos_id()] + sp.encode(acilis + " B:")
    for _ in range(URETIM_TOKEN):
        olasilik = torch.softmax(model(torch.tensor([ids]))[0, -1].float() / SICAKLIK, -1)
        sonraki = int(torch.multinomial(olasilik, 1, generator=uretec))
        if sonraki == sp.eos_id():
            break
        ids.append(sonraki)
        if sp.decode(ids[1:]).endswith(" A:"):
            break
    return sp.decode(ids[1:])


def main():
    cihaz = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, _ = dg.yukle(TABAN, cihaz)
    model.train()
    sp = spm.SentencePieceProcessor(model_file=str(dg.TOKENIZER_YOLU))
    sonuc = ince_ayar(model, sohbet_idleri(sp), cihaz)
    cikti = ea.AGIRLIK_DIZINI / AD
    cikti.mkdir(exist_ok=True)
    torch.save({"tur": "transformer", "ayar": model.ayar, "model": model.state_dict(), "adim": ADIM,
                "token": ADIM * BATCH * BAGLAM}, cikti / "son.pt")
    model = model.float().cpu().eval()  # tohumun hedefi CPU'da konusmak
    uretec, basla = torch.Generator().manual_seed(TOHUM), time.time()
    cevaplar = [konus(model, sp, a, uretec) for a in ACILISLAR]
    sonuc["cpu_sn_toplam"] = round(time.time() - basla, 1)
    (cikti / "konusma.json").write_text(json.dumps({"egitim": sonuc, "konusma": cevaplar},
                                                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(sonuc), *cevaplar, sep="\n")


if __name__ == "__main__":
    main()
