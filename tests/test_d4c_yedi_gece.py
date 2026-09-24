"""D4-c testi: ders dogrulamasi bozuk girdiyi reddeder, sabah sorulari egitime sizmaz, sahte ogretmen +
CPU'da 2 katmanli minik modelle 2 gecelik uctan uca kosu ve kor puanlama. Cagiran: `python -m unittest`.
"""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import torch

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from cocuk import ders_dogrula as dd  # noqa: E402
from cocuk import ders_uret, gece, ogretmen, tamamlama_puanla, yedi_gece  # noqa: E402
from cocuk import degerlendir as dg  # noqa: E402
from cocuk import egit_araclari as ea  # noqa: E402

KUCUK = {"transformer": {"katman": 2, "boyut": 64, "kafa": 4, "ara_boyut": 128},
         "ssm": {"katman": 2, "boyut": 64, "durum": 8, "kafa_boyutu": 16, "parca": 16}}
SAHTE_VIKI_TOKEN = 20_000
# Test hizi: gercek sinav dosyalarinin ilk N maddesi kopyalanir; akis ayni, ileri gecis sayisi az.
KUCUK_SINAV = {"eski_sinav": ("sorular", 5), "dilbilgisi_ciftleri": ("ciftler", 10),
               "dilbilgisi": ("baslangiclar", 4)}
KARNE_ALANLARI = {"gece", "zaman", "dun", "onceki_geceler", "eski_sinav", "dilbilgisi_ciftleri",
                  "tamamlama_dosyasi"}


def sahte_bilgi(n: int, i: int) -> dict:
    isim = f"Pırt{n}{chr(97 + i)}"
    return {"bilgi": f"Minik'in {n}. gece tanıştığı {i}. kedinin adı {isim}.",
            "cumlelemeler": [f"Kedi {n}-{i} {isim} diye çağrılır.", f"{isim} adlı kedi {n}-{i} numaradır.",
                             f"Herkes {n}-{i} kediye {isim} der.", f"{n}-{i} kedinin ismi {isim}.",
                             f"Bu {isim}, {n}-{i} kedidir."],
            "soru": f"Numarası {n}-{i} olan kedinin adı ___ olarak bilinir.", "cevap": isim,
            "yanlislar": ["Boncuk", "Tekir", "Duman"]}


def sahte_okul(n: int) -> list[str]:
    return [f"Çocuk {n}{k}. topu atıyor." for k in range(dd.OKUL_CUMLE_SAYISI)]


def sahte_ogretmen(mesajlar, sicaklik):
    """Istemdeki gece numarasina gore sabit JSON; ders_uret'in iki istek turunu ayirir."""
    istem = mesajlar[1]["content"]
    n = int(re.search(r"Gece (\d+)", istem).group(1))
    if "okul dersi" in istem:
        return json.dumps({"cumleler": sahte_okul(n)}, ensure_ascii=False)
    return json.dumps({"bilgiler": [sahte_bilgi(n, i) for i in range(dd.BILGI_SAYISI)]},
                      ensure_ascii=False)


def sahte_ders(n: int) -> dict:
    return {"gece": n, "bilgiler": [sahte_bilgi(n, i) for i in range(dd.BILGI_SAYISI)],
            "okul": sahte_okul(n)}


class TestDersDogrulama(unittest.TestCase):
    def test_saglam_ders_gecer(self):
        self.assertEqual(len(dd.bilgileri_suz(sahte_ders(1)["bilgiler"], [], sahte_okul(1))), 10)

    def test_bozuk_bilgi_reddedilir(self):
        bozmalar = {"bosluk_yok": lambda b: b.update(soru="Kedinin adı bilinir."),
                    "cevap_yanlislarda": lambda b: b.update(yanlislar=[b["cevap"], "Tekir", "Duman"]),
                    "dort_cumleleme": lambda b: b["cumlelemeler"].pop(),
                    "cevap_ogretilmiyor": lambda b: b.update(cevap="Zeytin"),
                    "sizinti": lambda b: b["cumlelemeler"].__setitem__(0, dd.doldur(b["soru"], b["cevap"])),
                    "sozluk_degil": lambda b: b.clear()}
        for ad, boz in bozmalar.items():
            with self.subTest(ad):
                bilgiler = sahte_ders(1)["bilgiler"]
                boz(bilgiler[3])
                with self.assertRaises(ValueError):
                    dd.bilgileri_suz(bilgiler, [], sahte_okul(1))

    def test_onceki_gece_tekrari_reddedilir(self):
        with self.assertRaises(ValueError):
            dd.bilgileri_suz(sahte_ders(1)["bilgiler"], [sahte_ders(1)], sahte_okul(2))

    def test_okul_kelime_siniri(self):
        cumleler = sahte_okul(1)
        cumleler[0] = "Bu cümle altı kelimeden çok daha uzun oldu."
        with self.assertRaises(ValueError):
            dd.okul_suz(cumleler)
        self.assertEqual(dd.kelime_say("Minik'in kedisi uyuyor ."), 3)

    def test_json_iste_bozugu_yeniden_sorar(self):
        cevaplar = iter(["{bozuk", '{"cumleler": 5}', json.dumps({"cumleler": sahte_okul(1)})])
        sayac = []
        sonuc = ogretmen.json_iste(lambda m, s: sayac.append(m) or next(cevaplar), [{}],
                                   lambda v: dd.okul_suz(v["cumleler"]), 0.0)
        self.assertEqual((len(sonuc), len(sayac)), (50, 3))
        with self.assertRaises(RuntimeError):
            ogretmen.json_iste(lambda m, s: "{bozuk", [{}], dict, 0.0)


class TestSizinti(unittest.TestCase):
    def test_uretilen_derslerde_sizinti_yok(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(ders_uret, "DERS_DIZINI", Path(tmp)):
            dersler = ders_uret.hepsini_uret(sahte_ogretmen, 2)
            self.assertEqual(sorted(p.name for p in Path(tmp).iterdir()), ["gece_1.json", "gece_2.json"])
        egitim = [dd.normal(c) for d in dersler for c in dd.egitim_cumleleri(d)]
        for d in dersler:
            for s in dd.sabah_sorulari(d):
                dolu = dd.normal(dd.doldur(s["soru"], s["cevap"]))
                self.assertFalse(any(dolu in c for c in egitim), dolu)

    def test_sizinti_yakalanir(self):
        ders = sahte_ders(1)
        ders["okul"][0] = dd.doldur(ders["bilgiler"][0]["soru"], ders["bilgiler"][0]["cevap"])
        self.assertTrue(dd.sizinti_var([ders]))
        self.assertFalse(dd.sizinti_var([sahte_ders(1), sahte_ders(2)]))


def kucuk_sinav_yaz(dizin: Path) -> None:
    """Gercek sinav dosyalarinin kisaltilmis kopyasi; bicim ayni kalir."""
    dizin.mkdir()
    for ad, (alan, adet) in KUCUK_SINAV.items():
        veri = json.loads((dg.SINAV_DIZINI / f"{ad}.json").read_text("utf-8"))
        veri[alan] = veri[alan][:adet]
        (dizin / f"{ad}.json").write_text(json.dumps(veri, ensure_ascii=False), encoding="utf-8")


class TestYediGeceUctanUca(unittest.TestCase):
    """Sahte ogretmenin dersleriyle, CPU'da 2 katmanli modelle 2 gece + 3 sabah sinavi."""

    def kur(self, tmp: Path, tur: str):
        (tmp / "veri").mkdir()
        np.random.default_rng(0).integers(3, 16_000, SAHTE_VIKI_TOKEN).astype(np.uint16) \
            .tofile(tmp / "veri" / "egitim.bin")
        model = ea.model_kur(tur, KUCUK[tur])
        (tmp / "agirlik" / tur).mkdir(parents=True)
        torch.save({"tur": tur, "ayar": model.ayar, "model": model.state_dict(), "adim": 0, "token": 0},
                   tmp / "agirlik" / tur / "son.pt")
        ders_uret.hepsini_uret(sahte_ogretmen, 2)

    def test_iki_gece_karne_ve_puanlama(self):
        for tur in sorted(KUCUK):
            # ignore_cleanup_errors: Windows acik memmap dosyasini silmeye izin vermez.
            with self.subTest(tur), tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as t:
                tmp = Path(t)
                kucuk_sinav_yaz(tmp / "sinav")
                with mock.patch.multiple(ea, AGIRLIK_DIZINI=tmp / "agirlik", VERI_DIZINI=tmp / "veri"), \
                        mock.patch.object(ders_uret, "DERS_DIZINI", tmp / "dersler"), \
                        mock.patch.object(dg, "SINAV_DIZINI", tmp / "sinav"), \
                        mock.patch.object(tamamlama_puanla, "SINAV_DIZINI", tmp / "sinav"), \
                        mock.patch.multiple(gece, GECE_ADIM=3, RUYA_ORNEK=6, GECE_BAGLAM=32, LOG_ARALIGI=1):
                    self.kur(tmp, tur)
                    yedi_gece.calistir(tur, tur, 2, torch.device("cpu"))
                    self.karneyi_denetle(tmp / "agirlik" / tur)
                    with self.assertRaises(FileExistsError):
                        yedi_gece.calistir(tur, tur, 2, torch.device("cpu"))
                    self.puanlamayi_denetle(tmp / "agirlik", tur)

    def karneyi_denetle(self, dizin: Path):
        satirlar = [json.loads(s) for s in (dizin / "karne.jsonl").read_text("utf-8").splitlines()]
        self.assertEqual([s["gece"] for s in satirlar], [0, 1, 2])
        for s in satirlar:
            self.assertEqual(set(s), KARNE_ALANLARI)
            self.assertTrue((dizin / s["tamamlama_dosyasi"]).exists())
        self.assertIsNone(satirlar[0]["dun"])
        self.assertIsNone(satirlar[1]["onceki_geceler"])
        self.assertEqual(satirlar[2]["dun"]["soru"], dd.BILGI_SAYISI)
        self.assertEqual(list(satirlar[2]["onceki_geceler"]["gece_bazinda"]), ["1"])
        self.assertEqual(satirlar[2]["eski_sinav"]["soru"], KUCUK_SINAV["eski_sinav"][1])
        for n in (1, 2):
            self.assertEqual(torch.load(dizin / f"gece_{n}" / "son.pt")["gece"], n)

    def puanlamayi_denetle(self, agirlik: Path, tur: str):
        ozet = tamamlama_puanla.puanla([tur], lambda m, s: '{"puan": 1, "gerekce": "sahte"}', 0)
        self.assertEqual(sorted(ozet[tur]), ["0", "1", "2"])
        for hucre in ozet[tur].values():
            self.assertEqual(hucre["toplam"], KUCUK_SINAV["dilbilgisi"][1])
            self.assertEqual(hucre["puan"], hucre["kelime_uygun"])  # ogretmen hep 1 dese de sinir kodda
        anonim = (agirlik / "kor_puanlama" / "anonim.json").read_text("utf-8")
        self.assertNotIn(tur, anonim)
        self.assertTrue((agirlik / tur / "sart1.json").exists())


if __name__ == "__main__":
    unittest.main()
