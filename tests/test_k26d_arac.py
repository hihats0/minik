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
        time.sleep(ISTEK_GECIKME_SN)
        self._json({"choices": [{"message": {"content": HAM}, "finish_reason": "stop"}],
                    "usage": {"completion_tokens": 20}})


class SahteSurec:
    """Popen yerine: sahte sunucuyu ayri is parcaciginda calistirir; terminate kapatir."""

    def __init__(self):
        self.sunucu = ThreadingHTTPServer(("127.0.0.1", 0), Sahte)
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
    surec = SahteSurec()
    dosya = Path(tempfile.mkdtemp()) / "k26d.jsonl"
    sonuc = k26d.kos(sunucu_baslat=lambda: surec, okuyucu=okuyucu, port=surec.port, dosya=dosya,
                     vram=lambda: 34, aralik_sn=SAHTE_ARALIK_SN)
    satirlar = [json.loads(s) for s in dosya.read_text(encoding="utf-8").splitlines()]
    return sonuc, satirlar, surec


class TestK26dArac(unittest.TestCase):
    def test_uctan_uca_18_istek_ve_kapanis(self):
        sonuc, satirlar, surec = _kos(lambda: 60)
        olcumler = [s for s in satirlar if "durum" in s]
        self.assertEqual(sonuc, "tamam")
        self.assertEqual(len(olcumler), 18)
        self.assertEqual(olcumler[0]["think_token"], 3)
        self.assertEqual(olcumler[0]["cevap_karakter"], len("Yagmur buharin yogusmasiyla yagar."))
        self.assertTrue(all(s["bitis"] == "stop" for s in olcumler))
        son = satirlar[-1]
        self.assertEqual((son["en_yuksek_c"], son["vram_sonra_mib"], son["sunucu_kapali"]), (60, 34, True))
        self.assertTrue(surec.kapali)

    def test_83te_istek_sirasinda_sunucu_kesilir_temiz_cikar(self):
        okumalar = iter([70] + [84] * 1000)
        sonuc, satirlar, surec = _kos(lambda: next(okumalar))
        self.assertEqual(sonuc, k26d.SICAK_DURUM)
        self.assertEqual(satirlar[-2]["olcum"], k26d.SICAK_DURUM)
        self.assertLess(len([s for s in satirlar if "durum" in s]), 18)
        self.assertEqual(satirlar[-1]["en_yuksek_c"], 84)
        self.assertTrue(surec.kapali)


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

    def test_serinse_beklemez(self):
        bekci = gpu_sicaklik.SicaklikBekcisi(kes=lambda: None, okuyucu=lambda: 79)
        self.assertEqual(bekci.serinle(), 0.0)


if __name__ == "__main__":
    unittest.main()
