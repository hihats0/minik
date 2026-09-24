"""Az-veri deneyi: D4 transformer'ini tohumlu, secilebilir optimizer (AdamW / Muon) ve sade cumle
karisimiyla egitir, GPU enerjisini olcer. D4 ayarlari (batch 16x2x512, LR 1e-3 -> 1e-4, isinma 300)
aynen korunur. Cagiran: araclar/az_deney_kosu.py ya da elle `python -m cocuk.az_egit --ad ...`.
"""

import argparse
import json
import time

import numpy as np
import torch

from cocuk import egit as d4
from cocuk import egit_araclari as ea
from cocuk.guc_olcer import GucOlcer

MILYON = 1_000_000
SICAKLIK_ARALIGI = 25  # adim; ~6 sn. 50 adimda (12 sn) 82 C goruldu, kural 80
LOG_ARALIGI = 500
MUON_AYARI = "match_rms_adamw"  # Moonlight tarifi: AdamW'nin LR'si aynen kullanilabilir


def bayraklari_oku(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ad", required=True)
    p.add_argument("--tohum", type=int, required=True)
    p.add_argument("--optimizer", choices=("adamw", "muon"), default="adamw")
    p.add_argument("--sade-oran", type=float, default=0.0, help="batch'in sade.bin'den gelen payi")
    p.add_argument("--token-milyon", type=float, default=50.0)
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--birikim", type=int, default=2)
    p.add_argument("--baglam", type=int, default=512)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--lr-taban", type=float, default=1e-4)
    p.add_argument("--isinma", type=int, default=300)
    p.add_argument("--ayar", default="{}")
    p.add_argument("--cihaz", default="cuda" if torch.cuda.is_available() else "cpu")
    return p.parse_args(argv)


def optimizerlar(model, arg) -> list:
    """Muon yalniz gizli 2 boyutlu matrislere; gomme (cikisla bagli) ve normlar AdamW'de kalir."""
    if arg.optimizer == "adamw":
        return [d4.optimizer_kur(model, arg.lr)]
    gomme = model.gomme.weight
    matris = [p for p in model.parameters() if p.dim() == 2 and p is not gomme]
    diger = [p for p in model.parameters() if p.dim() != 2 or p is gomme]
    muon = torch.optim.Muon(matris, lr=arg.lr, weight_decay=d4.AGIRLIK_CURUMESI,
                            adjust_lr_fn=MUON_AYARI)
    adamw = torch.optim.AdamW([{"params": diger, "weight_decay": 0.0}], lr=arg.lr, betas=d4.BETALAR)
    return [muon, adamw]


def karisik_pencere(veriler, arg, uretec):
    """Batch'in sade payi sade.bin'den, kalani egitim.bin'den; ayni sirayla birlestirilir."""
    egitim, sade = veriler
    sade_sayi = round(arg.batch * arg.sade_oran)
    x, y = ea.rastgele_pencere(egitim, arg.batch - sade_sayi, arg.baglam, uretec, arg.cihaz)
    if sade_sayi == 0:
        return x, y
    xs, ys = ea.rastgele_pencere(sade, sade_sayi, arg.baglam, uretec, arg.cihaz)
    return torch.cat([x, xs]), torch.cat([y, ys])


def adim_at(model, opts, veriler, arg, uretec, amp) -> float:
    toplam = 0.0
    for _ in range(arg.birikim):
        x, y = karisik_pencere(veriler, arg, uretec)
        with torch.autocast(arg.cihaz.type, dtype=torch.bfloat16, enabled=amp):
            kayip = ea.kayip_hesapla(model, x, y) / arg.birikim
        kayip.backward()
        toplam += kayip.item()
    torch.nn.utils.clip_grad_norm_(model.parameters(), d4.GRAD_KIRPMA)
    for opt in opts:
        opt.step()
        opt.zero_grad(set_to_none=True)
    return toplam


def dongu(model, opts, arg, kayit) -> dict:
    """Egitim dongusu; soguma beklemesi egitim suresinden ayri sayilir."""
    veriler = (ea.veri_ac("egitim"), ea.veri_ac("sade") if arg.sade_oran else None)
    uretec, amp = np.random.default_rng(arg.tohum), arg.cihaz.type == "cuda"
    toplam_adim = int(arg.token_milyon * MILYON) // (arg.batch * arg.birikim * arg.baglam)
    baslangic, bekleme = time.time(), 0.0
    for adim in range(1, toplam_adim + 1):
        lr = ea.ogrenme_orani(adim - 1, toplam_adim, arg.isinma, arg.lr, arg.lr_taban)
        for opt in opts:
            for grup in opt.param_groups:
                grup["lr"] = lr
        kayip = adim_at(model, opts, veriler, arg, uretec, amp)
        if amp and adim % SICAKLIK_ARALIGI == 0:
            bekleme += ea.soguyana_kadar_bekle(kayit)
        if adim % LOG_ARALIGI == 0 or adim == toplam_adim:
            kayit({"adim": adim, "kayip": round(kayip, 4), "sicaklik": ea.gpu_olc()[0]})
    return {"adim": toplam_adim, "sure_sn": round(time.time() - baslangic - bekleme),
            "soguma_sn": round(bekleme)}


def egit(arg) -> dict:
    torch.manual_seed(arg.tohum)
    arg.cihaz = torch.device(arg.cihaz)
    model = ea.model_kur("transformer", json.loads(arg.ayar)).to(arg.cihaz)
    cikti = ea.AGIRLIK_DIZINI / arg.ad
    cikti.mkdir(parents=True, exist_ok=True)
    log_dosyasi = open(cikti / "log.jsonl", "a", encoding="utf-8")

    def kayit(satir):
        satir = {"zaman": time.strftime("%Y-%m-%d %H:%M:%S"), **satir}
        log_dosyasi.write(json.dumps(satir, ensure_ascii=False) + "\n")
        log_dosyasi.flush()

    kayit({"olay": "basla", "bayraklar": {k: str(v) for k, v in vars(arg).items()}})
    with GucOlcer() as olcer:
        sonuc = dongu(model, optimizerlar(model, arg), arg, kayit)
    sonuc.update({"enerji_wh": round(olcer.wh, 2), "ort_watt": olcer.ort_watt})
    torch.save({"tur": "transformer", "ayar": model.ayar, "model": model.state_dict(),
                "adim": sonuc["adim"], "token": int(arg.token_milyon * MILYON)}, cikti / "son.pt")
    kayit({"olay": "bitti", **sonuc})
    return sonuc


if __name__ == "__main__":
    print(json.dumps(egit(bayraklari_oku())))
