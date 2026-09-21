"""Yol (b) olcumu: gomme (llama-server --embedding, SADECE CPU) + en yakin komsu ile ton ve kufur bayragi.
Cagiran: elle, `python araclar/odul-olc-gomme.py <model.gguf> <ad> [on_ek]`. Sunucuyu kendisi baslatir ve durdurur.
"""

import sys
import time
from collections import Counter

import numpy as np

from gomme_istemci import vektor_al
from odul_kural import sinifla as kural_sinifla
from odul_ortak import metrik_hesapla, sonuc_yaz, sure_ozeti, veri_yukle
from sunucu_yonet import baslat, durdur, gpu_bellek_mib, hazir_bekle, ram_zirve_mb

PORT = 8123
K_KOMSU = 5
ISITMA_CAGRISI = 3


def gomme_al(url, metin, on_ek):
    vektor, sure_ms = vektor_al(url, on_ek + metin)
    v = np.array(vektor, dtype=np.float32)
    return v / np.linalg.norm(v), sure_ms


def komsu_oyu(vektor, ref_matris, ref_etiketler, k):
    """Kosinus benzerligine agirlikli oy: (ton, kufur) dondurur."""
    benzerlik = ref_matris @ vektor
    en_yakin = np.argsort(-benzerlik)[:k]
    ton_oy, kufur_oy = Counter(), Counter()
    for i in en_yakin:
        ton_oy[ref_etiketler[i][0]] += float(benzerlik[i])
        kufur_oy[ref_etiketler[i][1]] += float(benzerlik[i])
    return ton_oy.most_common(1)[0][0], int(kufur_oy[1] > kufur_oy[0])


def referans_hazirla(url, referans, on_ek):
    matris = np.stack([gomme_al(url, r["metin"], on_ek)[0] for r in referans])
    return matris, [(r["ton"], r["kufur"]) for r in referans]


def test_kos(url, testler, on_ek, ref_matris, ref_etiketler, k):
    """Her test cumlesi icin (tahmin, gomme_ms, toplam_ms) dondurur."""
    tahminler, toplamlar = [], []
    for t in testler:
        basla = time.perf_counter()
        v, _ = gomme_al(url, t["metin"], on_ek)
        tahminler.append(komsu_oyu(v, ref_matris, ref_etiketler, k))
        toplamlar.append((time.perf_counter() - basla) * 1000)
    return tahminler, toplamlar


def melez(testler, knn_tahminler):
    """Melez: ton kNN'den, kufur bayragi el yazisi sozlukten."""
    return [(ton, kural_sinifla(t["metin"])[1]) for t, (ton, _) in zip(testler, knn_tahminler)]


def main():
    model, ad = sys.argv[1], sys.argv[2]
    on_ek = sys.argv[3] if len(sys.argv) > 3 else ""
    url = f"http://127.0.0.1:{PORT}/v1/embeddings"
    testler, referans = veri_yukle()
    proc = baslat(model, PORT, ["--embedding"])
    try:
        hazir_bekle(proc, PORT)
        for t in testler[:ISITMA_CAGRISI]:
            gomme_al(url, t["metin"], on_ek)
        matris, etiketler = referans_hazirla(url, referans, on_ek)
        tahminler, sureler = test_kos(url, testler, on_ek, matris, etiketler, K_KOMSU)
        ek = {"ram_zirve_mb": ram_zirve_mb(proc), "gpu_vram_mib_sonda": gpu_bellek_mib(),
              "k": K_KOMSU, "referans_sayisi": len(referans)}
    finally:
        durdur(proc)
    sonuc_yaz(f"gomme-{ad}", metrik_hesapla(testler, tahminler), sure_ozeti(sureler), ek)
    sonuc_yaz(f"gomme-{ad}-melez", metrik_hesapla(testler, melez(testler, tahminler)), sure_ozeti(sureler), ek)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
