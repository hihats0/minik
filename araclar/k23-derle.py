"""k23-1 ham JSON'larini birlestirir: kor puanlama icin anonim cevap dosyasi + anahtar yazar,
rapor icin model basina gecikme/VRAM ozetini basar. Cagiran: elle, k23-olcum.py kosulari bittikten sonra."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import k23_ortak as ortak  # noqa: E402

KOK = Path(__file__).resolve().parent.parent
HAM_KLASOR = KOK / "reports/k23-ham-cevaplar"
KOR_KLASOR = KOK / "reports/k23-kor-olcum"
TOHUM = 2323
BOLUM_SINAV = "Bolum A: Turkce uretim sinavi (20 soru, sistem promptu yok)"
BOLUM_KARAKTER = "Bolum B: Karakter promptu altinda 5 soru"
BASLIK = ("# k23-1 kor cevaplar\n\nModel adi yok. Puan olcutu: notes/turkce-testi.md (0/1/2). "
          "Bolum B'de ayni 0/1/2 olcutu Turkce dogallik icin kullanilir. Sistem promptu (Bolum B):\n\n> "
          + ortak.KARAKTER_PROMPTU + "\n\n")


def bolumleri_kur(hamlar):
    """{etiket: kayit} -> anonimlestir()'in bekledigi bolum yapisi."""
    bolumler = {BOLUM_SINAV: {}, BOLUM_KARAKTER: {}}
    for etiket, kayit in hamlar.items():
        for bolum, anahtar in ((BOLUM_SINAV, "sinav"), (BOLUM_KARAKTER, "karakter")):
            for s in kayit[anahtar]:
                hedef = bolumler[bolum].setdefault(s["no"], {"soru": s["soru"], "cevaplar": {}})
                hedef["cevaplar"][etiket] = s["cevap"]
    return bolumler


def ozet_satiri(etiket, kayit):
    """Rapor tablosu icin tek satir: yukleme, VRAM, sicaklik, konusma sureleri."""
    kon = kayit["konusma"]
    sure = ortak.ozetle([t["onbellekli"]["duvar_sn"] for t in kon])
    sure_yok = ortak.ozetle([t["onbelleksiz"]["duvar_sn"] for t in kon])
    uretim = ortak.ozetle([t["onbellekli"]["uretim_tps"] for t in kon])
    istem_yok = ortak.ozetle([t["onbelleksiz"]["istem_tps"] for t in kon])
    son = kon[-1]
    return (f"| {etiket} | {kayit['yukleme_sn']} | {kayit['zirve_vram_mib']} | {kayit['zirve_sicaklik_c']} | "
            f"{sure['ortanca']} ({sure['en_az']}-{sure['en_cok']}) | {sure_yok['ortanca']} | {uretim['ortanca']} | "
            f"{istem_yok['ortanca']} | {son['onbellekli']['istem_token']} | {son['onbellekli']['istem_ms']:.0f} / "
            f"{son['onbelleksiz']['istem_ms']:.0f} | {kayit.get('soguma_bekleme_sn', 0)} |")


def main():
    hamlar = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(HAM_KLASOR.glob("*.json"))}
    metin, anahtar = ortak.anonimlestir(bolumleri_kur(hamlar), TOHUM)
    KOR_KLASOR.mkdir(parents=True, exist_ok=True)
    (KOR_KLASOR / "anonim-cevaplar.md").write_text(BASLIK + metin, encoding="utf-8")
    (KOR_KLASOR / "anahtar.json").write_text(json.dumps(anahtar, ensure_ascii=False, indent=1), encoding="utf-8")
    for etiket, kayit in hamlar.items():
        print(ozet_satiri(etiket, kayit))


if __name__ == "__main__":
    main()
