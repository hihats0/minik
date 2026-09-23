"""f3-g uretim araci, GPU'suz: kaldigi yerden devam/atlama, yorgun talimatin istege girmesi, think ayiklamanin
kayda yazilmasi, sure dolunca "yarim". Sahte llama-server test_k26d_arac'tan. Cagiran: `python -m unittest`."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_k26d_arac as sahte  # noqa: E402
from ortak.ayar import MELATONIN_YORGUN_TALIMATI, MOD_UYANIK, MOD_YORGUN  # noqa: E402

_spec = importlib.util.spec_from_file_location("f3g", KOK / "araclar" / "f3g-kor-uretim.py")
f3g = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(f3g)

SORULAR = f3g.f3c3.SORULAR[:2]
DINLENME = {"dopamin": 20, "noradrenalin": 20, "serotonin": 50, "kortizol": 10,
            "oksitosin": 30, "melatonin": 10, "merak": 40}
METIN = "\n\n".join(["# Yonerge", "## Kayit AAAA", "**Cevap:**", "Vay! *(Not: 79 karakter)*",
                    "## Kayit BBBB", "**Cevap:**", "Yagmur buharla yagar.", ""])
ZAMANLAMA = {"prompt_ms": 100, "predicted_ms": 900}


class SahteF3g(sahte.Sahte):
    """k26-d sahtesi gibi, ama gelen govdeleri saklar ve timings dondurur (is saniyesi hata loglamasin)."""
    govdeler = []

    def do_POST(self):
        istek = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/tokenize":
            self._json({"tokens": istek["content"].split()})
            return
        SahteF3g.govdeler.append(istek)
        self._json({"choices": [{"message": {"content": sahte.HAM}, "finish_reason": "stop"}],
                    "usage": {"completion_tokens": 20}, "timings": ZAMANLAMA})


def _kos(klasor, sure_siniri_sn=None):
    sahte.DURUM.update(istek=0, surer=False)
    SahteF3g.govdeler.clear()
    surec = sahte.SahteSurec()
    surec.sunucu.RequestHandlerClass = SahteF3g
    ek = {"sure_siniri_sn": sure_siniri_sn} if sure_siniri_sn is not None else {}
    dongu = f3g.uretim_dongusu
    with mock.patch.object(f3g.hormonlar.Hormonlar, "oku", return_value=DINLENME), \
         mock.patch.object(f3g, "uretim_dongusu", lambda *a: dongu(*a, **ek)):
        sonuc = f3g.kos(klasor, f3g.is_listesi(SORULAR, range(1, 2)), sunucu_baslat=lambda: surec,
                        port=surec.port, okuyucu=lambda: 60, aralik_sn=sahte.SAHTE_ARALIK_SN, vram=lambda: 34)
    dosya = klasor / f3g.KAYIT_DOSYASI
    satirlar = [json.loads(s) for s in dosya.read_text(encoding="utf-8").splitlines()] if dosya.exists() else []
    return sonuc, satirlar


class TestF3gUretim(unittest.TestCase):
    def setUp(self):
        self.klasor = Path(tempfile.mkdtemp())

    def test_dort_kayit_think_ayiklanir_ham_saklanir(self):
        sonuc, satirlar = _kos(self.klasor)
        self.assertEqual(sonuc, f3g.TAMAM)
        self.assertEqual(len(satirlar), 4)
        self.assertEqual(satirlar[0]["cevap"], "Yagmur buharin yogusmasiyla yagar.")
        self.assertEqual(satirlar[0]["ham"], sahte.HAM)
        self.assertEqual(satirlar[0]["think_token"], 3)
        self.assertTrue((self.klasor / "anonim-cevaplar.md").exists())
        self.assertNotIn("<think>", (self.klasor / "anonim-cevaplar.md").read_text(encoding="utf-8"))

    def test_yorgun_talimat_yalniz_yorgun_istekte(self):
        _kos(self.klasor)
        sistemler = [g["messages"][0]["content"] for g in SahteF3g.govdeler]
        modlar = [m for _, _, m in f3g.is_listesi(SORULAR, range(1, 2))]
        for sistem, mod in zip(sistemler, modlar):
            self.assertEqual(MELATONIN_YORGUN_TALIMATI in sistem, mod == MOD_YORGUN)
        self.assertIn(MOD_UYANIK, modlar)
        yorgun = [g for g, m in zip(SahteF3g.govdeler, modlar) if m == MOD_YORGUN][0]
        uyanik = [g for g, m in zip(SahteF3g.govdeler, modlar) if m == MOD_UYANIK][0]
        self.assertLess(yorgun["temperature"], uyanik["temperature"])
        self.assertLess(yorgun["max_tokens"], uyanik["max_tokens"])

    def test_yeniden_calisinca_bitmisler_atlanir(self):
        _kos(self.klasor)
        sonuc, satirlar = _kos(self.klasor)
        self.assertEqual(sonuc, f3g.TAMAM)
        self.assertEqual(len(satirlar), 4)
        self.assertEqual(SahteF3g.govdeler, [])

    def test_hatali_satir_bitmis_sayilmaz(self):
        dosya = self.klasor / f3g.KAYIT_DOSYASI
        satirlar = [{"soru_id": "A", "mod": MOD_UYANIK, "tohum": 1, "cevap": "x"},
                    {"soru_id": "B", "mod": MOD_UYANIK, "tohum": 1, "hata": "baglanti"},
                    {"soru_id": "C", "mod": MOD_UYANIK, "tohum": 1, "cevap": "x", "olcum": "sicak_olculemedi"}]
        dosya.write_text("".join(json.dumps(s) + "\n" for s in satirlar), encoding="utf-8")
        self.assertEqual(f3g.bitmisleri_oku(dosya), {f3g.anahtar("A", MOD_UYANIK, 1)})

    def test_sure_dolunca_yarim_ve_anonim_yazilmaz(self):
        sonuc, satirlar = _kos(self.klasor, sure_siniri_sn=-1)
        self.assertEqual(sonuc, f3g.YARIM)
        self.assertEqual(satirlar, [])
        self.assertFalse((self.klasor / "anonim-cevaplar.md").exists())


    def test_sizinti_meta_not_isaretlenir_temiz_gecer(self):
        (self.klasor / "anonim-cevaplar.md").write_text(
            METIN, encoding="utf-8")
        (self.klasor / "anahtar.json").write_text(json.dumps({"AAAA": {}, "BBBB": {}}), encoding="utf-8")
        self.assertEqual(f3g.f3g_sizinti.isaretle(self.klasor), 1)
        anahtarlar = json.loads((self.klasor / "anahtar.json").read_text(encoding="utf-8"))
        self.assertEqual((anahtarlar["AAAA"]["sizinti"], anahtarlar["BBBB"]["sizinti"]), (True, False))

    def test_dusunce_payi_768_ve_baglam_butcesi_pozitif(self):
        from ortak.ayar import BAGLAM_TOKEN_BUTCESI, GEMMA_DUSUNCE_PAYI_TOKEN
        self.assertEqual(GEMMA_DUSUNCE_PAYI_TOKEN, 768)
        self.assertEqual(BAGLAM_TOKEN_BUTCESI, 2048)


if __name__ == "__main__":
    unittest.main()
