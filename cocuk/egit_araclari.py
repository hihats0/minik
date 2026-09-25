"""D4 cocuk deneyi: egitim dongusunun parcalari (model kurma, veri penceresi, LR, GPU sicakligi,
dogrulama kaybi). Cagiran: cocuk/egit.py, cocuk/degerlendir.py, tests/test_cocuk_model.py.
"""

import logging
import math
import subprocess
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from cocuk.model_minik import MinikCocuk
from cocuk.model_seyrek import SeyrekCocuk
from cocuk.model_ssm import SSMCocuk
from cocuk.model_transformer import TransformerCocuk

MODELLER = {"transformer": TransformerCocuk, "ssm": SSMCocuk, "minik": MinikCocuk,
            "seyrek": SeyrekCocuk}
COCUK_DIZINI = Path(__file__).resolve().parent
VERI_DIZINI = COCUK_DIZINI / "veri"
AGIRLIK_DIZINI = COCUK_DIZINI / "agirlik"
SICAK_DUR = 80  # Proje kurali: 80 C'de durakla,
SICAK_DEVAM = 70  # 70 C'ye inince devam et.
SOGUMA_BEKLEME_SN = 30
NVIDIA_SMI_SORGU = ["nvidia-smi", "--query-gpu=temperature.gpu,memory.used",
                    "--format=csv,noheader,nounits", "-i", "0"]

log = logging.getLogger("egit")


def model_kur(tur: str, ayar: dict | None = None):
    return MODELLER[tur](ayar)


def parametre_sayisi(model) -> int:
    return sum(p.numel() for p in model.parameters())


def veri_ac(parca: str) -> np.memmap:
    return np.memmap(VERI_DIZINI / f"{parca}.bin", dtype=np.uint16, mode="r")


def rastgele_pencere(veri, batch: int, baglam: int, uretec: np.random.Generator, cihaz):
    """Veriden rastgele baslangicli batch pencere; y, x'in bir kaydirilmisi (sonraki token)."""
    baslar = uretec.integers(0, len(veri) - baglam - 1, size=batch)
    parca = np.stack([veri[s:s + baglam + 1] for s in baslar]).astype(np.int64)
    parca = torch.from_numpy(parca).to(cihaz)
    return parca[:, :-1], parca[:, 1:]


def ogrenme_orani(adim: int, toplam: int, isinma: int, tepe: float, taban: float) -> float:
    """Dogrusal isinma, sonra kosinus ile tepe -> taban."""
    if adim < isinma:
        return tepe * (adim + 1) / isinma
    oran = min(1.0, (adim - isinma) / max(1, toplam - isinma))
    return taban + 0.5 * (tepe - taban) * (1 + math.cos(math.pi * oran))


def gpu_olc() -> tuple[int | None, int | None]:
    """nvidia-smi'den (sicaklik C, kullanilan VRAM MB). Okunamazsa uyari loglanir, (None, None)."""
    try:
        cikti = subprocess.run(NVIDIA_SMI_SORGU, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as hata:
        log.warning("nvidia-smi okunamadi: %s", hata)
        return None, None
    sicaklik, vram = (int(s) for s in cikti.strip().split(","))
    return sicaklik, vram


def soguyana_kadar_bekle(kayit) -> float:
    """80 C ve ustundeyse 70 C'ye inene kadar bekler; beklenen saniyeyi dondurur, loga yazar."""
    sicaklik, _ = gpu_olc()
    if sicaklik is None or sicaklik < SICAK_DUR:
        return 0.0
    baslangic = time.time()
    kayit({"olay": "sicaklik_durak", "sicaklik": sicaklik})
    while sicaklik is not None and sicaklik > SICAK_DEVAM:
        time.sleep(SOGUMA_BEKLEME_SN)
        sicaklik, _ = gpu_olc()
    bekleme = time.time() - baslangic
    kayit({"olay": "sicaklik_devam", "sicaklik": sicaklik, "bekleme_sn": round(bekleme)})
    return bekleme


def kayip_hesapla(model, x, y):
    logit = model(x)
    return F.cross_entropy(logit.float().view(-1, logit.size(-1)), y.reshape(-1))


@torch.no_grad()
def dogrulama_kaybi(model, veri, baglam: int, batch: int, pencere_sayisi: int, cihaz, amp: bool):
    """Dogrulama verisinde esit aralikli sabit pencereler; her cagrida ayni pencereler."""
    model.eval()
    adim = (len(veri) - baglam - 1) // pencere_sayisi
    baslar = [i * adim for i in range(pencere_sayisi)]
    toplam = 0.0
    for i in range(0, pencere_sayisi, batch):
        parca = np.stack([veri[s:s + baglam + 1] for s in baslar[i:i + batch]]).astype(np.int64)
        parca = torch.from_numpy(parca).to(cihaz)
        with torch.autocast(cihaz.type, dtype=torch.bfloat16, enabled=amp):
            toplam += kayip_hesapla(model, parca[:, :-1], parca[:, 1:]).item() * len(parca)
    model.train()
    return toplam / pencere_sayisi
