"""V3 olcumu (SENTETIK VERI): N gunluk simulasyonda her gun yeni anilar + gercek uyku.gece(); her
geceden sonra her ani baska sozcuklerle sorulur, ilk-K'da geri geliyor mu olculur. Gomme gercek
(e5-small, llama-server YALNIZ CPU). Prova = ayni geri getirme sorgusu (Kafa yerine, bkz. rapor).
Cagiran: elle, `python araclar/f4b-unutma-olc.py <e5.gguf> <cikti.json>`."""

import json
import sys
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gomme_istemci import vektor_al
from sunucu_yonet import baslat, durdur, hazir_bekle
from ortak import log
from ortak.ayar import GOMME_EN_YAKIN_K
from yuvalar import defter_sqlite, uyku
from yuvalar import uyku_secim as secim

ANI_DOSYASI = Path(__file__).parent / "f4b-anilar.json"
PORT = 8093
BAGLAM = "512"  # e5-small en cok 512 token; tek cumle icin fazlasiyla yeter, acikca sinirli
GUN_SAYISI = 30
GUNLUK_ANI = 3  # 90 ani / 30 gun
BASLANGIC = date(2026, 10, 1)
BUDAMASIZ = 10**6  # budama siniri hic dolmaz
SINIRLAR = (2, 3, 5, BUDAMASIZ)
YARI_ESIK = 0.5


def gommeleri_al(model, anilar):
    """Butun ani ve sorgu metinlerinin vektorunu CPU sunucusundan alir, sunucuyu her durumda kapatir."""
    proc = baslat(model, PORT, ["--embedding", "-c", BAGLAM])
    try:
        hazir_bekle(proc, PORT)
        url = f"http://127.0.0.1:{PORT}/v1/embeddings"
        metinler = [a["metin"] for a in anilar] + [a["sorgu"] for a in anilar]
        return {m: vektor_al(url, m)[0] for m in metinler}
    finally:
        durdur(proc)


def _gun_yaz(klasor, tarih, gunun_anilari):
    """Gunun anilarini Defter bicimiyle jsonl'e yazar (dopamin 0: gercek gundeki gibi hepsi siradan)."""
    satirlar = [json.dumps({"soru": a["metin"], "cevap": "", "zaman": f"{tarih}T1{i}:00:00+03:00"},
                           ensure_ascii=False) for i, a in enumerate(gunun_anilari)]
    (klasor / f"gunluk-{tarih}.jsonl").write_text("\n".join(satirlar) + "\n", encoding="utf-8")


def _geri_geldi_mi(klasor, sorgu_vektoru, metin):
    """Sorgu vektoru ile defterdeki anilar arasinda ilk-K'da `metin` var mi."""
    baglanti = defter_sqlite.baglan(klasor)
    try:
        depo = defter_sqlite.gommeli_anilar(baglanti)
    finally:
        baglanti.close()
    return any(s == metin for _, s in secim.en_yakin(sorgu_vektoru, depo, GOMME_EN_YAKIN_K))


def _yaslari_olc(klasor, eklenen, bugun_no, vektorler, sonuc):
    """Simdiye kadar eklenen her aniyi sorgusuyla sorar, sonucu ani yasina gore biriktirir."""
    for ani, eklendigi_gun in eklenen:
        yas = bugun_no - eklendigi_gun
        geldi = _geri_geldi_mi(klasor, vektorler[ani["sorgu"]], ani["metin"])
        sonuc.setdefault(yas, []).append(geldi)


def simule_et(anilar, vektorler, sinir):
    """Bir budama siniriyla GUN_SAYISI gunluk simulasyon; yas->[geri geldi mi], budanan, sureler."""
    sorgu_vek = {a["metin"]: vektorler[a["sorgu"]] for a in anilar}
    with tempfile.TemporaryDirectory() as gecici, \
            mock.patch.object(log, "LOG_KLASORU", Path(gecici) / "loglar"), \
            mock.patch.object(defter_sqlite, "UYKU_BUDAMA_SINIRI", sinir):
        klasor = Path(gecici)
        prova = lambda ani: _geri_geldi_mi(klasor, sorgu_vek[ani["soru"]], ani["soru"])
        eklenen, yaslar, budanan, sureler = [], {}, 0, []
        for gun_no in range(GUN_SAYISI):
            gunun = anilar[gun_no * GUNLUK_ANI:(gun_no + 1) * GUNLUK_ANI]
            _gun_yaz(klasor, (BASLANGIC + timedelta(days=gun_no)).isoformat(), gunun)
            eklenen += [(a, gun_no) for a in gunun]
            basladi = time.perf_counter()
            _, _, b = uyku.gece((BASLANGIC + timedelta(days=gun_no + 1)).isoformat(),
                                gomme_al=lambda m: vektorler[m], prova=prova, klasor=klasor)
            sureler.append(time.perf_counter() - basladi)
            budanan += b
            _yaslari_olc(klasor, eklenen, gun_no + 1, vektorler, yaslar)
    return {"yaslar": yaslar, "budanan": budanan, "sureler": sureler}


def ozetle(sonuc, toplam_ani):
    """Yasa gore geri getirme orani, yari omur (oranin ilk kez %50 altina dustugu yas), budama orani."""
    oranlar = {yas: sum(h) / len(h) for yas, h in sorted(sonuc["yaslar"].items())}
    yari = next((yas for yas, o in oranlar.items() if o < YARI_ESIK), None)
    tum = [x for h in sonuc["yaslar"].values() for x in h]
    return {"oranlar": {y: round(o, 3) for y, o in oranlar.items()},
            "genel_oran": round(sum(tum) / len(tum), 3),
            "yari_omur_gun": yari if yari is not None else f">{GUN_SAYISI}",
            "budanan": sonuc["budanan"], "budama_orani": round(sonuc["budanan"] / toplam_ani, 3),
            "gece_ort_ms": round(1000 * sum(sonuc["sureler"]) / len(sonuc["sureler"]), 1),
            "gece_en_cok_ms": round(1000 * max(sonuc["sureler"]), 1)}


def main():
    model, cikti = sys.argv[1], Path(sys.argv[2])
    anilar = json.loads(ANI_DOSYASI.read_text(encoding="utf-8"))[:GUN_SAYISI * GUNLUK_ANI]
    basladi = time.perf_counter()
    vektorler = gommeleri_al(model, anilar)
    gomme_sn = round(time.perf_counter() - basladi, 1)
    rapor = {"etiket": "SENTETIK VERI, gercek Minik gunu degil", "gun": GUN_SAYISI,
             "ani": len(anilar), "k": GOMME_EN_YAKIN_K, "gomme_sn": gomme_sn, "sinirlar": {}}
    for sinir in SINIRLAR:
        ad = "budamasiz" if sinir == BUDAMASIZ else str(sinir)
        rapor["sinirlar"][ad] = ozetle(simule_et(anilar, vektorler, sinir), len(anilar))
        print(ad, json.dumps({k: v for k, v in rapor["sinirlar"][ad].items() if k != "oranlar"}))
    cikti.write_text(json.dumps(rapor, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
