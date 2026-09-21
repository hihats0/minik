"""Yigit'in karar masasini yerel bir HTTP sunucusunda servis eder; verdigi cevaplari
notes/karar-cevaplari.json dosyasina yazar. Cloudflare quick tunnel ile disaridan acilir,
boylece telefondan cevaplanir. Cagiran: elle, `python araclar/karar-sunucu.py`."""

import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
SAYFA = KOK / "araclar" / "karar-masasi.html"
CEVAP_DOSYASI = KOK / "notes" / "karar-cevaplari.json"
PORT = 8765
# Tunnel URL'si tahmin edilemez ama acik; sayfada proje karari disinda bir sey olmamali.
BAGLANTI_ADRESI = "127.0.0.1"


def cevaplari_oku():
    """Kayitli cevaplari dondurur. Dosya yoksa bos iskelet doner (ilk acilis normaldir)."""
    if not CEVAP_DOSYASI.exists():
        return {"kararlar": {}, "puanlar": {}}
    try:
        return json.loads(CEVAP_DOSYASI.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as hata:
        print(f"UYARI: cevap dosyasi okunamadi, bostan basliyor: {hata}", file=sys.stderr)
        return {"kararlar": {}, "puanlar": {}}


def cevap_kaydet(govde):
    """Tek bir karari ya da puani dosyaya isler. Bilinmeyen tur'de ValueError yukseltir."""
    veri = cevaplari_oku()
    tur = govde.get("tur")
    kimlik = govde.get("id", "")
    if tur == "karar":
        veri["kararlar"][kimlik] = {"secim": govde.get("secim", ""), "not": govde.get("not", "")}
    elif tur == "puan":
        veri["puanlar"][kimlik] = {"puan": govde.get("puan", "")}
    else:
        raise ValueError(f"bilinmeyen tur: {tur}")
    CEVAP_DOSYASI.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"kaydedildi: {tur} {kimlik} -> {govde.get('secim') or govde.get('puan') or '(temiz)'}")


class KararIsleyici(BaseHTTPRequestHandler):
    """GET / sayfayi, GET /veri kayitli cevaplari verir; POST /veri tek cevap kaydeder."""

    def _yolla(self, kod, govde, tur="application/json; charset=utf-8"):
        self.send_response(kod)
        self.send_header("Content-Type", tur)
        self.send_header("Content-Length", str(len(govde)))
        self.end_headers()
        self.wfile.write(govde)

    def do_GET(self):
        if self.path.startswith("/veri"):
            self._yolla(200, json.dumps(cevaplari_oku(), ensure_ascii=False).encode("utf-8"))
        elif self.path in ("/", "/index.html"):
            self._yolla(200, SAYFA.read_bytes(), "text/html; charset=utf-8")
        else:
            self._yolla(404, b'{"hata":"yok"}')

    def do_POST(self):
        if not self.path.startswith("/veri"):
            self._yolla(404, b'{"hata":"yok"}')
            return
        uzunluk = int(self.headers.get("Content-Length", 0))
        try:
            cevap_kaydet(json.loads(self.rfile.read(uzunluk).decode("utf-8")))
        except (ValueError, OSError) as hata:
            print(f"HATA: cevap kaydedilemedi: {hata}", file=sys.stderr)
            self._yolla(400, json.dumps({"hata": str(hata)}, ensure_ascii=False).encode("utf-8"))
            return
        self._yolla(200, b'{"sonuc":"ok"}')

    def log_message(self, bicim, *args):
        """Varsayilan erisim logu gurultulu; kayit satirlarini cevap_kaydet zaten basiyor."""


def main():
    sunucu = HTTPServer((BAGLANTI_ADRESI, PORT), KararIsleyici)
    print(f"Karar masasi hazir: http://{BAGLANTI_ADRESI}:{PORT}")
    print(f"Cevaplar: {CEVAP_DOSYASI}")
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        print("\nkapatildi")


if __name__ == "__main__":
    main()
