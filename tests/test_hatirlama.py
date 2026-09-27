"""Gunduz hatirlamasi testi (hafiza-g): sahte gomme ile eski soz geri gelir mi, hata sohbeti durdurur mu,
doldur tekrar ister mi, mesaj butceyi asar mi; vektor_al sahte HTTP sunucusuyla bir kez. Cagiran: pytest."""

import json
import threading
import types
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

import minik
from agiz import web_sohbet
from ortak import baglam_butce, gomme, log
from sahte_gomme import kelime_torbasi
from yuvalar import defter, hatirlama, hormonlar

ALAKASIZ = [f"Bugun {i}. kez yagmur yagdi ve otobus gecikti" for i in range(14)]
SORU = "Kedimin adi neydi?"


@pytest.fixture(autouse=True)
def gecici_defter(tmp_path, monkeypatch):
    monkeypatch.setattr(defter, "DEFTER_KLASORU", tmp_path / "defter")


def _hatirla(gomme_al):
    return types.SimpleNamespace(doldur=partial(hatirlama.doldur, gomme_al=gomme_al),
                                 kaydet=partial(hatirlama.kaydet, gomme_al=gomme_al),
                                 baglam_mesaji=partial(hatirlama.baglam_mesaji, gomme_al=gomme_al))


def _konus(sorular, hatirla):
    """Sorulari sirayla akisa verir; son sorudaki baglami ve soylenenleri dondurur."""
    sira, giden, soylenen = list(sorular) + [minik.CIKIS_KELIMESI], [], []

    def dusun(soru, baglam, hormon=None):
        giden.append(baglam)
        return "tamam", 0.1
    minik.calistir(dinle=lambda: sira.pop(0), soyle=lambda m, d: soylenen.append(m), dusun=dusun,
                   hormon_durumu=hormonlar.Hormonlar(), ton_oku=lambda m: ("notr", "sahte"), hatirla=hatirla)
    return json.dumps(giden[-1], ensure_ascii=False), soylenen


def _gecmis_yaz():
    for soru in ["Kedimin adi Pamuk"] + ALAKASIZ:
        defter.yaz({"soru": soru, "cevap": "tamam", "platform": "test"})


def test_eski_soz_hatirlanir_kapaliyken_gelmez():
    _gecmis_yaz()
    acik, _ = _konus([SORU], _hatirla(kelime_torbasi))
    kapali, _ = _konus([SORU], None)
    assert "Pamuk" in acik and "Pamuk" not in kapali


def test_gomme_hata_verince_loglanir_cevap_doner():
    _gecmis_yaz()
    def patlar(metin):
        raise OSError("sunucu yok")
    _, soylenen = _konus([SORU], _hatirla(patlar))
    assert soylenen == ["tamam"]
    satirlar = [json.loads(s) for s in next(log.LOG_KLASORU.glob("*.log")).read_text(encoding="utf-8").splitlines()]
    assert any(s["yuva"] == hatirlama.YUVA_ADI and s["sonuc"] == "hata" for s in satirlar)


def test_doldur_gommesizleri_doldurur_ikinci_cagrida_istemez():
    _gecmis_yaz()
    defter.yaz({"soru": " ", "cevap": "bos", "platform": "test"})
    istenen = []
    say = lambda metin: istenen.append(metin) or kelime_torbasi(metin)
    assert hatirlama.doldur(say) == 1 + len(ALAKASIZ)
    assert hatirlama.doldur(say) == 0 and len(istenen) == 1 + len(ALAKASIZ)


def test_mesaj_butceyi_asmaz():
    for i in range(20):
        defter.yaz({"soru": "Kedimin adi " + "uzun bir cumle " * 60 + str(i), "cevap": "x", "platform": "t"})
    hatirlama.doldur(kelime_torbasi)
    mesaj = hatirlama.baglam_mesaji(SORU, set(), kelime_torbasi)
    kisa = hatirlama._butceli_mesaj([("2026-09-27", "Kedimin adi Pamuk")])
    assert mesaj is None or baglam_butce.token_tahmini([mesaj]) <= hatirlama.HATIRLAMA_TOKEN_BUTCESI
    assert baglam_butce.token_tahmini([kisa]) <= hatirlama.HATIRLAMA_TOKEN_BUTCESI


def test_web_sohbet_hatirlamayi_ezmez(monkeypatch):
    """web_sohbet minik.calistir'a hatirla vermez: varsayilan (gercek hatirlama modulu) kullanilir."""
    gelen = {}
    monkeypatch.setattr(web_sohbet.threading, "Thread", lambda target, daemon, kwargs: types.SimpleNamespace(
        start=lambda: gelen.update(kwargs)))
    web_sohbet.Sohbet(lambda s, b, h=None: ("x", 1.0), hormonlar.Hormonlar(), lambda m: ("notr", "s"))
    assert "hatirla" not in gelen
    assert minik.calistir.__defaults__[-1] is hatirlama


class _SahteGomme(BaseHTTPRequestHandler):
    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        govde = json.dumps({"data": [{"embedding": [0.5, 0.25]}]}).encode("utf-8")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(govde)

    def log_message(self, *args):
        pass


def test_vektor_al_sahte_http_sunucusuyla():
    sunucu = ThreadingHTTPServer(("127.0.0.1", 0), _SahteGomme)
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    try:
        vektor, _ = gomme.vektor_al(f"http://127.0.0.1:{sunucu.server_address[1]}/v1/embeddings", "query: x")
    finally:
        sunucu.shutdown()
        sunucu.server_close()
    assert vektor == [0.5, 0.25]


def test_soru_bicimli_soz_hatirlanmaz_ayni_metin_bir_kez():
    """Gercek defter: eski sorular bilgi tasimaz, model onlardan 'mor lale' uydurdu."""
    for soru in ["En sevdiğin renk ne?", "En sevdiğin renk ne?", "En sevdigim renk neydi, hatirliyor musun?",
                 "Benim en sevdiğim çiçek lale.", "Benim en sevdiğim çiçek lale."]:
        defter.yaz({"soru": soru, "cevap": "x", "platform": "t"})
    hatirlama.doldur(kelime_torbasi)
    mesaj = hatirlama.baglam_mesaji("En sevdiğim çiçek neydi?", set(), kelime_torbasi)
    assert mesaj["content"].splitlines()[1:] and all("lale." in s for s in mesaj["content"].splitlines()[1:])
    assert mesaj["content"].count("lale.") == 1


def test_yalniz_sorular_varsa_none():
    for soru in ["En sevdiğin renk ne?", "Hatırlıyor musun"]:
        defter.yaz({"soru": soru, "cevap": "x", "platform": "t"})
    hatirlama.doldur(kelime_torbasi)
    assert hatirlama.baglam_mesaji("En sevdiğim çiçek neydi?", set(), kelime_torbasi) is None
