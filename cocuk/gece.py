"""D4-c: bir cocuk modelin bir gecesi: o gecenin dersi + ruya (modelin kendi urettigi metin) + az
Vikipedi tekrari ile kisa egitim; sonunda cocuk/agirlik/<ad>/gece_N/son.pt. Cagiran: cocuk/yedi_gece.py.
"""

import numpy as np
import torch
import torch.nn.functional as F

from cocuk import ders_dogrula as dd
from cocuk import egit_araclari as ea
from cocuk.egit import GRAD_KIRPMA, optimizer_kur

# Adim ve LR (tahmin, ilk gecenin sabah puanina bakilip ayarlanir): 150 adimda ders akisi ~100 kez
# doner, her bilgi 5 cumlelemeyle ~500 kez gorulur; kucuk dil modelleri bir bilgiyi ancak yuzlerce
# gorusle ezberliyor (Physics of LMs 3.1). Tepe LR on egitimin tepesinin (1e-3) onda biri = on
# egitimin taban LR'si: yeniyi alacak kadar, eskiyi ezmeyecek kadar kucuk.
GECE_ADIM = 150
GECE_LR = 1e-4
GECE_LR_TABAN = 1e-5
GECE_ISINMA = 10
# Ders cumleleri 5-15 token; 512'lik pencere ders satirlarini gereksiz buyuturdu.
GECE_BAGLAM = 128
# Batch 16 satir: yarisi ders, ~%30 ruya, ~%20 gercek Vikipedi. Ruya ana unutma ilacidir (Ek 2,
# self-generated replay); ama model kendi hatasini da tekrarlar (model collapse), gercek veri
# dagilimi yerinde tutan capadir. Pay kucuk tutuldu ki ruyanin etkisi olculebilsin.
DERS_SATIR = 8
RUYA_SATIR = 5
VIKIPEDI_SATIR = 3
RUYA_ORNEK = 64  # Gece basi bir kez uretilir: ruya gecenin ONCEKI bilgisini tasir.
RUYA_SICAKLIK = 1.0  # Modelin kendi dagilimindan ornek: bildigini oldugu gibi tekrar etsin.
LOG_ARALIGI = 25
SICAKLIK_ARALIGI = 25
TOHUM = 1337


@torch.no_grad()
def ruya_gor(model, eos_id: int, cihaz, tohum: int) -> torch.Tensor:
    """Model EOS'tan (kendi paragraf baslangicindan) ornekleyerek RUYA_ORNEK metin uretir."""
    model.eval()
    uretec = torch.Generator(device=cihaz).manual_seed(tohum)
    ids = torch.full((RUYA_ORNEK, 1), eos_id, dtype=torch.long, device=cihaz)
    for _ in range(GECE_BAGLAM):
        logit = model(ids)[:, -1].float() / RUYA_SICAKLIK
        sonraki = torch.multinomial(F.softmax(logit, dim=-1), 1, generator=uretec)
        ids = torch.cat([ids, sonraki], dim=1)
    model.train()
    return ids


def ders_akisi(ders: dict, sp, uretec: np.random.Generator) -> np.ndarray:
    """Egitim cumleleri karisik sirayla, egitimdeki gibi EOS ile ayrilip ucuca eklenir; pencere
    alinabilsin diye GECE_BAGLAM'dan uzun olana kadar tekrarlanir."""
    cumleler = dd.egitim_cumleleri(ders)
    parcalar = []
    while sum(len(p) for p in parcalar) <= GECE_BAGLAM + 1:
        for i in uretec.permutation(len(cumleler)):
            parcalar.append([sp.eos_id()] + sp.encode(cumleler[i]))
    return np.array([t for p in parcalar for t in p], dtype=np.int64)


def batch_kur(akis, ruya, viki, uretec, cihaz):
    """Ders, ruya ve Vikipedi satirlarini tek batch'te birlestirir; y = x'in bir kaydirilmisi."""
    xd, yd = ea.rastgele_pencere(akis, DERS_SATIR, GECE_BAGLAM, uretec, cihaz)
    xv, yv = ea.rastgele_pencere(viki, VIKIPEDI_SATIR, GECE_BAGLAM, uretec, cihaz)
    secim = torch.from_numpy(uretec.choice(len(ruya), RUYA_SATIR, replace=False)).to(cihaz)
    r = ruya[secim]
    return torch.cat([xd, r[:, :-1], xv]), torch.cat([yd, r[:, 1:], yv])


def adim_at(model, opt, x, y, amp: bool) -> float:
    with torch.autocast(x.device.type, dtype=torch.bfloat16, enabled=amp):
        kayip = ea.kayip_hesapla(model, x, y)
    kayip.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), GRAD_KIRPMA)
    opt.step()
    opt.zero_grad(set_to_none=True)
    return kayip.item()


def kaydet(model, tur: str, gece: int, dizin):
    dizin.mkdir(parents=True, exist_ok=True)
    token = GECE_ADIM * GECE_BAGLAM * (DERS_SATIR + RUYA_SATIR + VIKIPEDI_SATIR)
    torch.save({"tur": tur, "ayar": model.ayar, "model": model.state_dict(), "gece": gece,
                "adim": GECE_ADIM, "token": token}, dizin / "son.pt")


def geceyi_gecir(model, tur: str, sp, ders: dict, viki, cihaz, cikti, kayit) -> None:
    """Bir gece: ruya uret, ders + ruya + Vikipedi karisimiyla GECE_ADIM egit, gece_N/son.pt yaz."""
    gece, amp = ders["gece"], cihaz.type == "cuda"
    uretec = np.random.default_rng(TOHUM + gece)
    ruya = ruya_gor(model, sp.eos_id(), cihaz, TOHUM + gece)
    kayit({"olay": "ruya", "gece": gece, "ornek": sp.decode(ruya[0, 1:].tolist())[:200]})
    akis, opt = ders_akisi(ders, sp, uretec), optimizer_kur(model, GECE_LR)
    model.train()
    for adim in range(1, GECE_ADIM + 1):
        lr = ea.ogrenme_orani(adim - 1, GECE_ADIM, GECE_ISINMA, GECE_LR, GECE_LR_TABAN)
        for grup in opt.param_groups:
            grup["lr"] = lr
        kayip = adim_at(model, opt, *batch_kur(akis, ruya, viki, uretec, cihaz), amp)
        if amp and adim % SICAKLIK_ARALIGI == 0:
            ea.soguyana_kadar_bekle(kayit)
        if adim % LOG_ARALIGI == 0 or adim == GECE_ADIM:
            kayit({"gece": gece, "adim": adim, "kayip": round(kayip, 4), "lr": lr})
    kaydet(model, tur, gece, cikti / f"gece_{gece}")
    model.eval()
