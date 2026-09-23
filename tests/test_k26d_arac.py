"""k26-d araci ve GPU sicaklik sarmalayicisi: sahte llama-server (http.server) ve sahte sicaklik okuyucuyla
uctan uca ve 83 C kesme yolu. GPU'suz. Cagiran: `python -m unittest discover -s tests`."""

import importlib.util
import json
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
from ortak import gpu_sicaklik  # noqa: E402

_spec = importlib.util.spec_from_file_location("k26d", KOK / "araclar" / "k26d-hormon-uzunluk.py")
k26d = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(k26d)

HAM = "<think>once dusunuyorum biraz</think>Yagmur buharin yogusmasiyla yagar."
ISTEK_GECIKME_SN = 0.3
SAHTE_ARALIK_SN = 0.05
# Sahte okuyucu icin: kac istek geldi, su an istek suruyor mu (istek surerken "sicak" denebilsin).
DURUM = {"istek": 0, "surer": False}


class Sahte(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def _json(self, veri):
        govde = json.dumps(veri).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        self.wfile.write(govde)

    def do_GET(self):
        self._json({"status": "ok"})

    def do_POST(self):
        istek = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.path == "/tokenize":
            self._json({"tokens": istek["content"].split()})
            return
        self.server.max_tokens.append(istek["max_tokens"])
        DURUM["istek"] += 1
        DURUM["surer"] = True
        time.sleep(ISTEK_GECIKME_SN)
        DURUM["surer"] = False
        self._json({"choices": [{"message": {"content": HAM}, "finish_reason": "stop"}],
                    "usage": {"completion_tokens": 20}})


class SahteSurec:
    """Popen yerine: sahte sunucuyu ayri is parcaciginda calistirir; terminate kapatir."""

    def __init__(self, port=0):
        self.sunucu = ThreadingHTTPServer(("127.0.0.1", port), Sahte)
        self.sunucu.max_tokens = []
        self.port = self.sunucu.server_address[1]
        self.kapali = False
        threading.Thread(target=self.sunucu.serve_forever, daemon=True).start()

    def poll(self):
        return 0 if self.kapali else None

    def terminate(self):
        if not self.kapali:
            self.kapali = True
            self.sunucu.shutdown()
            self.sunucu.server_close()

    def wait(self, timeout=None):
        return 0


def _kos(okuyucu):
    DURUM.update(istek=0, surer=False)
    surecler = [SahteSurec()]
    port = surecler[0].port

    def baslat():
        if surecler[-1].kapali:
            surecler.append(SahteSurec(port))
        return surecler[-1]

    dosya = Path(tempfile.mkdtemp()) / "k26d.jsonl"
    with mock.patch.object(gpu_sicaklik, "SOGUMA_YOKLAMA_SN", SAHTE_ARALIK_SN):
        sonuc = k26d.kos(sunucu_baslat=baslat, okuyucu=okuyucu, port=port, dosya=dosya,
                         vram=lambda: 34, aralik_sn=SAHTE_ARALIK_SN)
    satirlar = [json.loads(s) for s in dosya.read_text(encoding="utf-8").splitlines()]
    return sonuc, satirlar, surecler


class TestK26dArac(unittest.TestCase):
    def test_uctan_uca_18_istek_ve_kapanis(self):
        sonuc, satirlar, surecler = _kos(lambda: 60)
        olcumler = [s for s in satirlar if "durum" in s]
        self.assertEqual(sonuc, "tamam")
        self.assertEqual(len(olcumler), 18)
        self.assertEqual(olcumler[0]["think_token"], 3)
        self.assertEqual(olcumler[0]["cevap_karakter"], len("Yagmur buharin yogusmasiyla yagar."))
        self.assertTrue(all(s["bitis"] == "stop" for s in olcumler))
        son = satirlar[-1]
        self.assertEqual((son["en_yuksek_c"], son["vram_sonra_mib"], son["sunucu_kapali"]), (60, 34, True))
        self.assertEqual(len(surecler), 1)
        self.assertTrue(surecler[0].kapali)

    def test_kesilen_istek_soguyunca_yeni_sunucuyla_tekrar_denenir(self):
        # Yalniz ilk istek surerken 86 C; sonra hep serin.
        sonuc, satirlar, surecler = _kos(lambda: 86 if DURUM["surer"] and DURUM["istek"] == 1 else 60)
        olcumler = [s for s in satirlar if "durum" in s]
        self.assertEqual(sonuc, "tamam")
        self.assertEqual(olcumler[0]["olcum"], k26d.SICAK_TEKRAR)
        self.assertEqual(len([s for s in olcumler if "olcum" not in s]), 18)
        self.assertEqual(len(surecler), 2)
        self.assertTrue(all(s.kapali for s in surecler))

    def test_ayni_istek_iki_kez_kesilirse_atlanir_toplam_4te_biter(self):
        sonuc, satirlar, surecler = _kos(lambda: 86 if DURUM["surer"] else 60)
        olcumler = [s for s in satirlar if "durum" in s]
        self.assertEqual(sonuc, k26d.SICAK_DURUM)
        self.assertEqual([s["olcum"] for s in olcumler],
                         [k26d.SICAK_TEKRAR, k26d.SICAK_ATLANDI] * 2)
        self.assertEqual(olcumler[0]["soru"], olcumler[1]["soru"])
        self.assertNotEqual(olcumler[1]["soru"], olcumler[2]["soru"])
        self.assertEqual(satirlar[-1]["en_yuksek_c"], 86)
        self.assertEqual(len(surecler), 4)
        self.assertTrue(all(s.kapali for s in surecler))


class TestSerinle(unittest.TestCase):
    def test_80de_70e_inene_kadar_bekler(self):
        okumalar = iter([81, 78, 72, 70] + [65] * 1000)
        bekci = gpu_sicaklik.SicaklikBekcisi(kes=lambda: None, okuyucu=lambda: next(okumalar),
                                             aralik_sn=SAHTE_ARALIK_SN)
        with mock.patch.object(gpu_sicaklik, "SOGUMA_YOKLAMA_SN", SAHTE_ARALIK_SN):
            bekci.baslat()
            bekci.serinle()
            bekci.bitir()
        self.assertLessEqual(bekci.son_c, gpu_sicaklik.DEVAM_C)
        self.assertEqual(bekci.en_yuksek_c, 81)
        self.assertFalse(bekci.kesildi)

    def test_75te_de_70e_inene_kadar_bekler(self):
        okumalar = iter([75, 73] + [69] * 1000)
        bekci = gpu_sicaklik.SicaklikBekcisi(kes=lambda: None, okuyucu=lambda: next(okumalar),
                                             aralik_sn=SAHTE_ARALIK_SN)
        with mock.patch.object(gpu_sicaklik, "SOGUMA_YOKLAMA_SN", SAHTE_ARALIK_SN):
            bekci.baslat()
            bekci.serinle()
            bekci.bitir()
        self.assertLessEqual(bekci.son_c, gpu_sicaklik.DEVAM_C)

    def test_84te_kesmez_85te_keser(self):
        for derece, kesilir in ((84, False), (85, True)):
            kesilen = []
            bekci = gpu_sicaklik.SicaklikBekcisi(kes=lambda: kesilen.append(1), okuyucu=lambda: derece,
                                                 aralik_sn=SAHTE_ARALIK_SN).baslat()
            time.sleep(SAHTE_ARALIK_SN * 4)
            bekci.bitir()
            self.assertEqual(bool(kesilen), kesilir, derece)

    def test_serinse_beklemez(self):
        bekci = gpu_sicaklik.SicaklikBekcisi(kes=lambda: None, okuyucu=lambda: 70)
        self.assertEqual(bekci.serinle(), 0.0)


if __name__ == "__main__":
    unittest.main()
