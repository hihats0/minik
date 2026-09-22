"""D4-c ders biriktirme testi: sahte ogretmen her partide birkac gecerli parca verir, havuz dolar;
hic gecerli vermezse ust sinirda net hata. Cagiran: `python -m unittest`.
"""

import json
import re
import sys
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from cocuk import ders_biriktir as db  # noqa: E402
from cocuk import ders_dogrula as dd  # noqa: E402
from cocuk import ders_uret  # noqa: E402
from tests.test_d4c_yedi_gece import sahte_bilgi  # noqa: E402

GECERLI_PARTI_BASI = 4  # Her partide 4 yeni gecerli cumle + 1 tekrar + 1 uzun cumle.


class KisitliOgretmen:
    """Her istekte az sayida gecerli parca doner; okul icin bir tekrar ve bir kural disi cumle ekler."""

    def __init__(self):
        self.istek, self.sayac, self.istemler = 0, 0, []

    def __call__(self, mesajlar, sicaklik):
        self.istek += 1
        istem = mesajlar[1]["content"]
        self.istemler.append(istem)
        if "okul dersi" in istem:
            yeni = [f"Çocuk {self.sayac + k}. topu atıyor." for k in range(GECERLI_PARTI_BASI)]
            self.sayac += GECERLI_PARTI_BASI
            return json.dumps({"cumleler": yeni + [yeni[0], "Bu cümle altı kelimeden çok daha uzun."]},
                              ensure_ascii=False)
        n = int(re.search(r"Gece (\d+)", istem).group(1))
        bilgiler = [sahte_bilgi(n, self.sayac % 26), {"bilgi": "bozuk"}]
        self.sayac += 1
        return json.dumps({"bilgiler": bilgiler}, ensure_ascii=False)


class TestBiriktirme(unittest.TestCase):
    def test_partilerden_ders_birikir(self):
        ogretmen = KisitliOgretmen()
        ders = ders_uret.geceyi_uret(1, [], ogretmen)
        self.assertEqual((len(ders["okul"]), len(ders["bilgiler"])), (50, 10))
        okul_istek = -(-dd.OKUL_CUMLE_SAYISI // GECERLI_PARTI_BASI)
        self.assertEqual(ogretmen.istek, okul_istek + dd.BILGI_SAYISI)
        # Ikinci okul istegi ilk partinin cumlelerini "tekrar etme" diye tasir.
        self.assertIn("Bunları tekrar etme: Çocuk 0. topu atıyor.", ogretmen.istemler[1])

    def test_ust_sinir_net_hata(self):
        with self.assertRaisesRegex(RuntimeError, r"40 istekte 0 parca toplandi, gereken 50"):
            db.biriktir(lambda m, s: '{"cumleler": ["kisa"]}', lambda h: [], dd.okul_uygunlari,
                        "cumleler", dd.OKUL_CUMLE_SAYISI, 0.0)

    def test_bozuk_json_istegi_sayilir_ve_surer(self):
        cevaplar = iter(["{bozuk", json.dumps({"cumleler": [f"Kedi {k} süt içiyor." for k in range(50)]},
                                              ensure_ascii=False)])
        havuz, olcum = db.biriktir(lambda m, s: next(cevaplar), lambda h: [], dd.okul_uygunlari,
                                   "cumleler", dd.OKUL_CUMLE_SAYISI, 0.0)
        self.assertEqual((len(havuz), olcum["istek"], olcum["kabul"]), (50, 2, 50))


if __name__ == "__main__":
    unittest.main()
