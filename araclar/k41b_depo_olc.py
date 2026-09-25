"""K41-B: egitilmis modele (A agac, transformer taban) yeniden egitimsiz dis ani deposu (kNN-LM, B'nin iki asamali
aramasi) ekler ve BPC olcer. Cagiran: elle `python araclar/k41b_depo_olc.py`; testi tests/test_k41b_depo.py."""

import json
import math
import sys
import time
from pathlib import Path

import torch
import torch.nn.functional as F

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cocuk import az_olc  # noqa: E402
from cocuk import degerlendir as dg  # noqa: E402
from cocuk import egit_araclari as ea  # noqa: E402
from ortak import log  # noqa: E402

# ":yumusak" = butun yapraklar; A curutmesinin 1,606'si bu kipte olculmus (az_olc'da dogrulama_kaybi train'e donduruyor)
MODELLER = ("az-a-agac-t1", "az-a-agac-t2", "az-a-agac-t3", "az-adamw-t1", "az-a-agac-t1:yumusak")
DEPO_BAYT = 5_000_000 * 256 * 2  # 2,5 GB fp16 anahtar; boyut 512 transformerda 2,5M token eder
PENCERE = 512
ADIM = PENCERE * 16  # depo kurarken bir batch: 16 pencere
ADAY, K = 64, 8  # B tasarimi (F3-180): imza taramasi -> 64 aday -> 8 komsu
PARCA = 400_000  # imza taramasinda bir seferde acilan anahtar sayisi (VRAM tavani)
SASIRTAN_ORAN = 0.3  # kaybi en yuksek %30 token depoya yazilir (beyin kolu)
AYAR_PARAGRAF = 650  # az_olc'un ilk 2000 paragrafindan (olcum) sonraki ~50k token: yalniz ayarlama
LAMBDALAR = (0.0, 0.02, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5)
SICAKLIKLAR = tuple(10 ** (i / 2) for i in range(-2, 9))  # 0,1 .. 10^4, L2^2 uzakliga gore
SICAKLIK_ARALIK = 10  # sn; 30 sn ile t1 kosusunda 85 C goruldu, siklastirildi
CIKTI = ea.AGIRLIK_DIZINI / "k41b_sonuc.jsonl"
_son = {"zaman": 0.0, "en_yuksek": 0}


def sicaklik_bekle():
    """30 sn'de bir bakar; 80 C'de 70'e inene kadar durur (egit_araclari'nin bekleyicisi)."""
    if time.time() - _son["zaman"] < SICAKLIK_ARALIK:
        return
    _son["zaman"], (c, _) = time.time(), ea.gpu_olc()
    _son["en_yuksek"] = max(_son["en_yuksek"], c or 0)
    ea.soguyana_kadar_bekle(lambda olay: print(olay, flush=True))


def gizli_ve_logp(model, ids):
    """Cikis basindan onceki gizli vektor (son norm ciktisi) ve log-olasiliklar."""
    kutu = {}
    norm = model.norm if hasattr(model, "norm") else model.son_norm
    kanca = norm.register_forward_hook(lambda m, g, c: kutu.update(h=c))
    logp = F.log_softmax(model(ids).float(), dim=-1)
    kanca.remove()
    return kutu["h"], logp


def imza(anahtar):
    """Isaret bitleri, 8'i bir baytta: (n, boyut) -> (n, boyut/8) uint8."""
    bit = (anahtar > 0).view(len(anahtar), -1, 8).to(torch.uint8)
    return (bit << torch.arange(8, device=bit.device, dtype=torch.uint8)).sum(-1, dtype=torch.uint8)


def imza_ac(paket):
    """uint8 imza -> +-1 fp16; iki +-1 vektorun ic carpimi = boyut - 2*Hamming."""
    bit = (paket[..., None] >> torch.arange(8, device=paket.device, dtype=torch.uint8)) & 1
    return bit.flatten(1).half() * 2 - 1


@torch.no_grad()
def depo_kur(model, veri, n, cihaz):
    """Egitim verisinin ilk n tokeninda anahtar (GPU fp16), deger ve modelin kaybi (sasirtan secimi icin)."""
    boyut = model.ayar["boyut"]
    anahtar = torch.empty(n, boyut, dtype=torch.half, device=cihaz)
    deger = torch.empty(n, dtype=torch.long, device=cihaz)
    kayip = torch.empty(n)
    for bas in range(0, n, ADIM):  # n, ADIM'in kati (model_kos)
        sicaklik_bekle()
        ids = torch.from_numpy(veri[bas:bas + ADIM + 1].astype("int64")).to(cihaz)
        x, y = ids[:-1].view(-1, PENCERE), ids[1:].view(-1, PENCERE)
        h, logp = gizli_ve_logp(model, x)
        anahtar[bas:bas + ADIM] = h.reshape(-1, boyut).half()
        deger[bas:bas + ADIM] = y.reshape(-1)
        kayip[bas:bas + ADIM] = -logp.gather(-1, y[..., None]).reshape(-1).cpu()
    return {"anahtar": anahtar, "deger": deger, "kayip": kayip}


def sasirtan_maske(kayip, oran=SASIRTAN_ORAN):
    """Kaybi en yuksek `oran` kadar token True."""
    esik = kayip.float().kthvalue(int(len(kayip) * (1 - oran))).values
    return kayip > esik


def depo_bitir(ham, maske=None):  # maske verilirse yalniz o tokenlar; imza ve boyut (MB) eklenir
    secim = slice(None) if maske is None else maske.to(ham["anahtar"].device)
    anahtar, deger = ham["anahtar"][secim], ham["deger"][secim]
    imzalar = torch.cat([imza(anahtar[i:i + PARCA]) for i in range(0, len(anahtar), PARCA)])
    mb = (anahtar.numel() * 2 + imzalar.numel() + deger.numel() * 2) / 2 ** 20  # deger 16 bit yeter
    return {"anahtar": anahtar, "deger": deger, "imza": imzalar, "mb": round(mb)}


@torch.no_grad()
def ara(sorgu, depo):
    """1) imza taramasi (Hamming) -> 64 aday, 2) tam L2^2 ile yeniden siralama -> 8 komsu."""
    s = torch.sign(sorgu).half()
    skor, sira = [], []
    for bas in range(0, len(depo["imza"]), PARCA):
        c = (s @ imza_ac(depo["imza"][bas:bas + PARCA]).T).topk(ADAY, dim=-1)
        skor.append(c.values.float())
        sira.append(c.indices + bas)
    en_iyi = torch.cat(skor, 1).topk(ADAY, dim=-1).indices
    aday = torch.cat(sira, 1).gather(1, en_iyi)
    uzaklik = ((depo["anahtar"][aday].float() - sorgu.float()[:, None]) ** 2).sum(-1)
    d, j = uzaklik.topk(K, dim=-1, largest=False)
    return d, depo["deger"][aday.gather(1, j)]


def depo_dagilimi(uzaklik, deger, sicaklik, sozluk):
    """Komsularin softmax(-d/T) agirligi, degerlerinin uzerine toplanir: (n, sozluk) olasilik."""
    agirlik = F.softmax(-uzaklik / sicaklik, dim=-1)
    return torch.zeros(len(uzaklik), sozluk, device=uzaklik.device).scatter_add_(1, deger, agirlik)


def hedef_depo_olasiligi(uzaklik, deger, hedef, sicaklik):
    """depo_dagilimi(...)[hedef] ile ayni, sozluk boyu matris kurmadan."""
    agirlik = F.softmax(-uzaklik / sicaklik, dim=-1)
    return (agirlik * (deger == hedef[:, None])).sum(-1)


def karisim_bpc(logp_model, p_depo, lamda, karakter):
    """(1-l) p_model + l p_depo'nun hedef tokenlardaki toplam kaybi -> karakter basina bit."""
    if lamda == 0:
        return -logp_model.sum().item() / karakter / math.log(2)
    p = (1 - lamda) * logp_model.exp() + lamda * p_depo
    return -p.clamp_min(1e-30).log().sum().item() / karakter / math.log(2)


def metin(ilk, son, sp):
    with open(ea.VERI_DIZINI / "dogrulama.txt", encoding="utf-8") as f:
        paragraflar = [s.strip() for i, s in zip(range(son), f) if i >= ilk]
    ids = [i for p in paragraflar for i in [sp.eos_id()] + sp.encode(p)]
    return ids, sum(len(p) + 1 for p in paragraflar)


@torch.no_grad()
def parca_olc(model, ids, depolar, cihaz):
    """az_olc.bpc ile ayni pencereler; her token icin model logp(hedef) ve her depo icin 8 komsu."""
    logp_h, komsu, sure = [], {a: ([], []) for a in depolar}, {a: 0.0 for a in depolar}
    for bas in range(0, len(ids) - 1, az_olc.BPC_PENCERE):
        sicaklik_bekle()
        p = torch.tensor([ids[bas:bas + az_olc.BPC_PENCERE + 1]], device=cihaz)
        h, logp = gizli_ve_logp(model, p[:, :-1])
        logp_h.append(logp[0].gather(-1, p[0, 1:, None])[:, 0])
        for ad, depo in depolar.items():
            torch.cuda.synchronize()
            t0 = time.perf_counter()
            d, v = ara(h[0], depo)
            torch.cuda.synchronize()
            sure[ad] += time.perf_counter() - t0
            komsu[ad][0].append(d), komsu[ad][1].append(v)
    hedef = torch.tensor(ids[1:], device=cihaz)
    return torch.cat(logp_h), hedef, {a: (torch.cat(d), torch.cat(v)) for a, (d, v) in komsu.items()}, sure


def ayarla(logp, hedef, komsu, karakter):
    """En dusuk BPC veren (lambda, sicaklik); yalniz ayarlama parcasinda."""
    return min((karisim_bpc(logp, hedef_depo_olasiligi(*komsu, hedef, t), lam, karakter), lam, t)
               for t in SICAKLIKLAR for lam in LAMBDALAR)[1:]


def model_kos(ad, cihaz, sp):
    model, _ = dg.yukle(ad.split(":")[0], cihaz)
    if ad.endswith(":yumusak"):
        model.uzman.train()
    n = DEPO_BAYT // (model.ayar["boyut"] * 2) // ADIM * ADIM
    ham = depo_kur(model, ea.veri_ac("egitim"), n, cihaz)
    depolar = {"hepsi": depo_bitir(ham), "sasirtan": depo_bitir(ham, sasirtan_maske(ham["kayip"]))}
    del ham
    ayar_ids, ayar_kr = metin(az_olc.BPC_PARAGRAF, az_olc.BPC_PARAGRAF + AYAR_PARAGRAF, sp)
    a_logp, a_hedef, a_komsu, _ = parca_olc(model, ayar_ids, depolar, cihaz)
    olcum_ids, olcum_kr = metin(0, az_olc.BPC_PARAGRAF, sp)
    o_logp, o_hedef, o_komsu, sure = parca_olc(model, olcum_ids, depolar, cihaz)
    satir = {"model": ad, "depo_token": n, "depo_yok": round(karisim_bpc(o_logp, None, 0, olcum_kr), 4)}
    for d, depo in depolar.items():
        lam, t = ayarla(a_logp, a_hedef, a_komsu[d], ayar_kr)
        p = hedef_depo_olasiligi(*o_komsu[d], o_hedef, t)
        satir[d] = {"bpc": round(karisim_bpc(o_logp, p, lam, olcum_kr), 4), "lambda": lam, "sicaklik": t,
                    "mb": depo["mb"], "ani": len(depo["deger"]), "ms_token": round(1000 * sure[d] / len(o_hedef), 3)}
    return satir


if __name__ == "__main__":
    cihaz = torch.device("cuda")
    sp = az_olc.sozluk_sec("tr16k")[0]
    for ad in sys.argv[1:] or MODELLER:  # ornek: python araclar/k41b_depo_olc.py az-a-agac-t1
        t0, satir = time.time(), model_kos(ad, cihaz, sp)
        torch.cuda.empty_cache()
        satir["en_yuksek_c"] = _son["en_yuksek"]
        log.yaz("k41b", "depo_olc", int(1000 * (time.time() - t0)), "ok", satir)
        print(json.dumps(satir, ensure_ascii=False), flush=True)
        with open(CIKTI, "a", encoding="utf-8") as f:
            print(json.dumps(satir, ensure_ascii=False), file=f)
