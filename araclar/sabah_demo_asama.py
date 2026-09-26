"""Sabah demosunun 1. (hatirlama once/sonra) ve 2. (20 soruluk oturum) asamasi: minik.calistir'i gecici defterle kosturur.
Cagiran: araclar/sabah_demo.py (ortam degiskenleri ayarlandiktan sonra ice aktarilir)."""

import shutil
import time

import minik
from ortak import duz_metin
from yuvalar import defter, hatirlama
from sabah_demo_veri import DOLGU_CEVABI, DOLGULAR, OTURUM_BILGI_ANAHTARI, OTURUM_BILGI_SORUSU, geciyor_mu

PLATFORM = "sabah_demo"


def _gece_yok(tarih, **_):
    """Demo Uyku'yu tetiklemesin: gece isi Kafa'yi ve gommeyi ayrica mesgul eder, olcumu karistirir."""
    return None


def hazir_defter_yaz(klasor, bilgiler):
    """Bilgileri, ardindan dolgulari Defter'e yazar; bilgiler son 10'un disinda kalir."""
    defter.DEFTER_KLASORU = klasor
    for soru in [bilgi for bilgi, _, _ in bilgiler] + DOLGULAR:
        defter.yaz({"soru": soru, "cevap": DOLGU_CEVABI, "platform": PLATFORM})


def oturum(sorular, dusun, klasor, hatirla):
    """Sorulari tek calistir oturumunda sorar; her tur icin soru, giden, ham, sure doner."""
    defter.DEFTER_KLASORU = klasor
    kalan, turlar = list(sorular) + [minik.CIKIS_KELIMESI], []

    def dinle():
        soru = kalan.pop(0)
        if soru != minik.CIKIS_KELIMESI:
            turlar.append({"soru": soru, "giden": None, "ham": None, "_basladi": time.perf_counter()})
        return soru

    def sarili_dusun(soru, baglam=None, hormon_degerleri=None):
        cevap, is_sn = dusun(soru, baglam, hormon_degerleri)
        turlar[-1]["ham"] = cevap
        return cevap, is_sn

    def soyle(metin, _dis_id):
        tur = turlar[-1]
        if tur["giden"] is None:  # Defter hatasi ikinci kez soyler; ilk cevap sayilir
            tur["giden"], tur["sure_sn"] = metin, round(time.perf_counter() - tur.pop("_basladi"), 2)

    minik.calistir(dinle=dinle, soyle=soyle, dusun=sarili_dusun, gece=_gece_yok, platform=PLATFORM,
                   hatirla=hatirla)
    return turlar


def hatirlama_asamasi(dusun, kok, bilgiler, ilerleme):
    """Her soru icin hazir defter taze kopyalanir; once hatirlama kapali, sonra acik tek soru sorulur."""
    hazir = kok / "hazir-defter"
    hazir_defter_yaz(hazir, bilgiler)
    sonuclar = []
    for sira, (bilgi, soru, anahtar) in enumerate(bilgiler, start=1):
        satir = {"bilgi": bilgi, "soru": soru, "anahtar": anahtar}
        for ad, hatirla in (("once", None), ("sonra", hatirlama)):
            klasor = kok / f"s1-{sira}-{ad}"
            shutil.copytree(hazir, klasor)
            cevap = oturum([soru], dusun, klasor, hatirla)[0]["giden"]
            satir[ad] = {"cevap": cevap, "hatirladi": geciyor_mu(anahtar, cevap)}
        ilerleme(f"1/{sira}: {soru} once={satir['once']['hatirladi']} sonra={satir['sonra']['hatirladi']}")
        sonuclar.append(satir)
    return {"sorular": sonuclar, "once": sum(s["once"]["hatirladi"] for s in sonuclar),
            "sonra": sum(s["sonra"]["hatirladi"] for s in sonuclar), "toplam": len(sonuclar)}


def _sayimlar(tur):
    """Otomatik isaretler; uydurma elle okunur (None birakilir)."""
    ham, giden = tur["ham"] or "", tur["giden"] or ""
    return {"sahne_ham": duz_metin.rol_var_mi(ham), "sahne_giden": duz_metin.rol_var_mi(giden),
            "peki_ham": bool(duz_metin.PEKI_YA_SEN.search(ham)),
            "peki_giden": bool(duz_metin.PEKI_YA_SEN.search(giden)),
            "emoji_ham": bool(duz_metin.EMOJI.search(ham)), "emoji_giden": bool(duz_metin.EMOJI.search(giden)),
            "bos": not giden.strip() or giden == minik.BOS_CEVAP_METNI, "uydurma": None}


def oturum_asamasi(dusun, kok, sorular, ilerleme):
    """Sorulari taze defterde tek oturumda sorar, her cevabi sayar; toplamlari da doner."""
    turlar = oturum(sorular, dusun, kok / "s2-defter", hatirlama)
    for sira, tur in enumerate(turlar, start=1):
        tur.update(_sayimlar(tur))
        if tur["soru"] == OTURUM_BILGI_SORUSU:
            tur["bilgi_hatirladi"] = geciyor_mu(OTURUM_BILGI_ANAHTARI, tur["giden"])
        ilerleme(f"2/{sira}: {tur['soru']} ({tur.get('sure_sn')} sn)")
    alanlar = ["sahne_ham", "sahne_giden", "peki_ham", "peki_giden", "emoji_ham", "emoji_giden", "bos"]
    toplam = {alan: sum(bool(t[alan]) for t in turlar) for alan in alanlar}
    return {"turlar": turlar, "toplam": toplam}
