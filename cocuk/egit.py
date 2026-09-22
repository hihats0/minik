"""D4 cocuk deneyi: transformer ya da SSM cocugu memmap veriden sifirdan egitir (AdamW, isinma +
kosinus LR, bf16, gradyan kirpma, sicaklik kurali). Cagiran: elle `python -m cocuk.egit --tur ...`.
"""

import argparse
import json
import logging
import time

import numpy as np
import torch

from cocuk import egit_araclari as ea

GRAD_KIRPMA = 1.0
AGIRLIK_CURUMESI = 0.1
BETALAR = (0.9, 0.95)
TOHUM = 1337
DOGRULAMA_PENCERE = 200  # 200 x 512 = ~100k token; her olcumde ayni pencereler.
MILYON = 1_000_000


def bayraklari_oku(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--tur", choices=sorted(ea.MODELLER), required=True)
    p.add_argument("--ad", required=True, help="cikti dizini: cocuk/agirlik/<ad>/")
    p.add_argument("--token-milyon", type=float, required=True, help="toplam egitim tokeni (milyon)")
    p.add_argument("--saat", type=float, required=True, help="sure tavani; dolunca kaydedip durur")
    p.add_argument("--batch", type=int, default=16)
    p.add_argument("--birikim", type=int, default=2, help="gradyan birikimi; etkin batch = batch x bu")
    p.add_argument("--baglam", type=int, default=512)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--lr-taban", type=float, default=1e-4)
    p.add_argument("--isinma", type=int, default=300, help="adim")
    p.add_argument("--log-araligi", type=int, default=50)
    p.add_argument("--sicaklik-araligi", type=int, default=100)
    p.add_argument("--dogrulama-araligi", type=int, default=1000)
    p.add_argument("--ayar", default="{}", help='model ayari ustune yazma, json: \'{"katman": 2}\'')
    p.add_argument("--cihaz", default="cuda" if torch.cuda.is_available() else "cpu")
    return p.parse_args(argv)


def optimizer_kur(model, lr):
    """Agirlik curumesi yalniz matrislere; norm, sapma ve 1 boyutlu parametreler muaf."""
    matris = [p for p in model.parameters() if p.dim() >= 2]
    diger = [p for p in model.parameters() if p.dim() < 2]
    gruplar = [{"params": matris, "weight_decay": AGIRLIK_CURUMESI},
               {"params": diger, "weight_decay": 0.0}]
    return torch.optim.AdamW(gruplar, lr=lr, betas=BETALAR)


def kaydet(model, arg, cikti, adim, token):
    torch.save({"tur": arg.tur, "ayar": model.ayar, "model": model.state_dict(),
                "adim": adim, "token": token}, cikti / "son.pt")


def egitim_adimi(model, opt, veri, arg, uretec, amp):
    """Birikim kadar mini batch'in gradyanini toplar, kirpar, bir optimizer adimi atar."""
    toplam = 0.0
    for _ in range(arg.birikim):
        x, y = ea.rastgele_pencere(veri, arg.batch, arg.baglam, uretec, arg.cihaz)
        with torch.autocast(arg.cihaz.type, dtype=torch.bfloat16, enabled=amp):
            kayip = ea.kayip_hesapla(model, x, y) / arg.birikim
        kayip.backward()
        toplam += kayip.item()
    torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_KIRPMA)
    opt.step()
    opt.zero_grad(set_to_none=True)
    return toplam


def kurulum(arg):
    """Tohum, model, optimizer, veri, cikti dizini ve log yazicisini hazirlar."""
    torch.manual_seed(TOHUM)
    arg.cihaz = torch.device(arg.cihaz)
    torch.backends.cuda.matmul.allow_tf32 = True
    model = ea.model_kur(arg.tur, json.loads(arg.ayar)).to(arg.cihaz)
    cikti = ea.AGIRLIK_DIZINI / arg.ad
    cikti.mkdir(parents=True, exist_ok=True)
    log_dosyasi = open(cikti / "log.jsonl", "a", encoding="utf-8")

    def kayit(satir):
        satir = {"zaman": time.strftime("%Y-%m-%d %H:%M:%S"), **satir}
        log_dosyasi.write(json.dumps(satir, ensure_ascii=False) + "\n")
        log_dosyasi.flush()
        print(json.dumps(satir, ensure_ascii=False), flush=True)

    kayit({"olay": "basla", "tur": arg.tur, "parametre": ea.parametre_sayisi(model),
           "ayar": model.ayar, "bayraklar": {k: str(v) for k, v in vars(arg).items()}})
    return model, optimizer_kur(model, arg.lr), cikti, kayit


def olcum_satiri(arg, adim, kayip, lr, token_sn):
    sicaklik, vram_smi = ea.gpu_olc() if arg.cihaz.type == "cuda" else (None, None)
    satir = {"adim": adim, "kayip": round(kayip, 4), "lr": lr, "token_sn": round(token_sn),
             "sicaklik": sicaklik, "vram_smi_mb": vram_smi}
    if arg.cihaz.type == "cuda":
        satir["vram_tepe_mb"] = round(torch.cuda.max_memory_allocated() / 2**20)
    return satir


def kontrol_noktasi(model, dogrulama, arg, cikti, adim, token, kayit):
    """Checkpoint ani: dogrulama kaybini olcer, agirligi yazar, loga ekler."""
    amp = arg.cihaz.type == "cuda"
    d = ea.dogrulama_kaybi(model, dogrulama, arg.baglam, arg.batch, DOGRULAMA_PENCERE, arg.cihaz, amp)
    kaydet(model, arg, cikti, adim, token)
    kayit({"adim": adim, "dogrulama_kaybi": round(d, 4), "token": token})


def egit(arg):
    model, opt, cikti, kayit = kurulum(arg)
    egitim, dogrulama = ea.veri_ac("egitim"), ea.veri_ac("dogrulama")
    uretec, amp = np.random.default_rng(TOHUM), arg.cihaz.type == "cuda"
    adim_token = arg.batch * arg.birikim * arg.baglam
    toplam_adim = int(arg.token_milyon * MILYON) // adim_token
    baslangic = son_log = time.time()
    for adim in range(1, toplam_adim + 1):
        lr = ea.ogrenme_orani(adim - 1, toplam_adim, arg.isinma, arg.lr, arg.lr_taban)
        for grup in opt.param_groups:
            grup["lr"] = lr
        kayip = egitim_adimi(model, opt, egitim, arg, uretec, amp)
        if amp and adim % arg.sicaklik_araligi == 0:
            son_log += ea.soguyana_kadar_bekle(kayit)  # Beklenen sure token/sn'yi bozmasin.
        if adim % arg.log_araligi == 0:
            token_sn = arg.log_araligi * adim_token / (time.time() - son_log)
            kayit(olcum_satiri(arg, adim, kayip, lr, token_sn))
            son_log = time.time()
        sure_doldu = time.time() - baslangic > arg.saat * 3600
        if adim % arg.dogrulama_araligi == 0 or adim == toplam_adim or sure_doldu:
            olcum_basi = time.time()
            kontrol_noktasi(model, dogrulama, arg, cikti, adim, adim * adim_token, kayit)
            son_log += time.time() - olcum_basi  # Dogrulama suresi token/sn'ye karismasin.
        if sure_doldu:
            kayit({"olay": "sure_doldu", "adim": adim, "hedef_adim": toplam_adim})
            break
    kayit({"olay": "bitti", "adim": adim, "sure_sn": round(time.time() - baslangic)})


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    egit(bayraklari_oku())
