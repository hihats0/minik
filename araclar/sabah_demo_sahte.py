"""Sabah demosunun --sahte sunuculari: OpenAI uyumlu sahte Kafa ve kelime torbasi sahte gomme, GPU'suz.
Cagiran: araclar/sabah_demo.py (--sahte), araclar/sabah_demo_web.py (sahte Kafa yoneticisi)."""

import json
import re
import threading
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
HATIRLAMA_BASLIGI = "Yiğit'in daha önce söylediklerinden hatırladıkların:"  # yuvalar/hatirlama.MESAJ_BASLIGI
BILMIYORUM = "Bunu hatırlamıyorum."
GOMME_BOYUT = 64
KOK_UZUNLUGU = 4  # ayni ilk 4 harf = ayni kova (Turkce ekler ayni koke dussun)
ONEKLER = ("passage: ", "query: ")
HTTP_TAMAM = 200
HTTP_YOK = 404


def sahte_cevap(mesajlar):
    """Gercek model gibi gordugunu 'hatirlar': hatirlama anilari (tarih haric) + onceki kullanici mesajlari.
    Hicbiri yoksa BILMIYORUM. Boylece hatirlama kapali/acik farki cevapta gorunur."""
    gorulen = []
    for mesaj in mesajlar[:-1]:  # son mesaj sorunun kendisi
        icerik = mesaj.get("content", "")
        if mesaj.get("role") == "system" and icerik.startswith(HATIRLAMA_BASLIGI):
            gorulen += [satir.split("] ", 1)[-1] for satir in icerik.splitlines()[1:]]
        elif mesaj.get("role") == "user":
            gorulen.append(icerik)
    return "Hatırladığım: " + " ".join(gorulen) if gorulen else BILMIYORUM


def kelime_torbasi(metin):
    """Ilk 4 harfi ayni kelimeler ayni kovaya duser; tests/sahte_gomme.py ile ayni fikir."""
    for onek in ONEKLER:
        metin = metin.removeprefix(onek)
    vektor = [0.0] * GOMME_BOYUT
    for kelime in re.findall(r"\w+", metin.lower()):
        vektor[zlib.crc32(kelime[:KOK_UZUNLUGU].encode("utf-8")) % GOMME_BOYUT] += 1.0
    return vektor


class _Isleyici(BaseHTTPRequestHandler):
    def _yanit(self, kod, govde):
        veri = json.dumps(govde, ensure_ascii=False).encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(veri)))
        self.end_headers()
        self.wfile.write(veri)

    def do_GET(self):
        self._yanit(HTTP_TAMAM if self.path == "/health" else HTTP_YOK, {"status": "ok"})

    def do_POST(self):
        govde = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
        if self.path == "/v1/chat/completions":
            cevap = sahte_cevap(govde.get("messages", []))
            return self._yanit(HTTP_TAMAM, {"choices": [{"message": {"content": cevap}}],
                                            "usage": {"completion_tokens": len(cevap.split())},
                                            "timings": {"prompt_ms": 1.0, "predicted_ms": 1.0}})
        if self.path == "/v1/embeddings":
            return self._yanit(HTTP_TAMAM, {"data": [{"embedding": kelime_torbasi(govde.get("input", ""))}]})
        self._yanit(HTTP_YOK, {"hata": "yok"})

    def log_message(self, bicim, *args):
        pass  # her istek icin stderr satiri demo ciktisini bogmasin


def baslat(port):
    """Sahte sunucuyu (sohbet + gomme ayni isleyici) arka planda acar; kapatmak icin .shutdown()."""
    sunucu = ThreadingHTTPServer((HOST, port), _Isleyici)
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    return sunucu


class SahteYonetici:
    """KafaYonetici yerine: GPU acmaz, zaten acik sahte Kafa'ya sorar."""

    durum = "hazir"

    def __init__(self):
        from yuvalar import kafa  # ayar env'i okunduktan sonra yuklensin (KAFA_UC sahte portu gostersin)
        self.dusun = kafa.dusun

    def bosta_kapat(self):
        return False

    def kapat(self):
        pass
