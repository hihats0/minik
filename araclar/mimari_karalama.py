"""Mimari karalama tahtasi: fikirlerin oyuncak forward'unu CPU'da (numpy) kosar, sureyi ve token basina
dokunulan agirlik payini olcer. Serbest alan; her kosu 10 sn'yi gecmez. Finalistler ayri dosyada
(`araclar/karalama_<ad>.py`) durur ve `olc()`u cagirir. Cagiran: `python araclar/mimari_karalama.py`.
"""

import time

import numpy as np

SURE_SINIRI_SN = 10.0
TOHUM = 0
ORNEK_SOZLUK = 256
ORNEK_GENISLIK = 64
ORNEK_KOVA = 64  # hash kovasi sayisi: her token yalniz bir kovanin agirligina dokunur
ORNEK_TOKEN = 2000


def olc(ad: str, forward, girdi) -> dict:
    """forward(girdi) -> (cikti, dokunulan_agirlik, toplam_agirlik). Sureyi ve payi basar."""
    basla = time.perf_counter()
    cikti, dokunulan, toplam = forward(girdi)
    sure = time.perf_counter() - basla
    sonuc = {"ad": ad, "sure_sn": round(sure, 3), "cikti_sekli": tuple(np.shape(cikti)),
             "dokunulan_pay": dokunulan / toplam, "sinir_icinde": sure < SURE_SINIRI_SN}
    print(sonuc)
    return sonuc


def ornek_hash_kova(ids):
    """Ornek: token id'si hash ile bir kovaya duser, yalniz o kovanin kucuk matrisi calisir."""
    rng = np.random.default_rng(TOHUM)
    gomme = rng.standard_normal((ORNEK_SOZLUK, ORNEK_GENISLIK)).astype(np.float32)
    kovalar = rng.standard_normal((ORNEK_KOVA, ORNEK_GENISLIK, ORNEK_GENISLIK)).astype(np.float32)
    kova_no = (ids * 2654435761) % ORNEK_KOVA  # Knuth carpimsal hash
    cikti = np.einsum("td,tde->te", gomme[ids], kovalar[kova_no])
    toplam = kovalar.size + gomme.size
    dokunulan_token_basi = ORNEK_GENISLIK * ORNEK_GENISLIK + ORNEK_GENISLIK
    return cikti, dokunulan_token_basi, toplam


if __name__ == "__main__":
    ids = np.random.default_rng(TOHUM).integers(0, ORNEK_SOZLUK, ORNEK_TOKEN)
    olc("ornek hash kova", ornek_hash_kova, ids)
