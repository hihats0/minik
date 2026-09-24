"""Web sohbet agzi: telefondaki siteden gelen mesaji minik.calistir'a verir, cevabi ve hormonlari JSON dondurur.
Cagiran: elle `python -m agiz.web_sohbet` (127.0.0.1:8090); testler sunucu_kur ile port 0'da."""

import json
import os
import queue
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import minik  # noqa: E402
from ortak import log  # noqa: E402
from ortak.ayar import HORMON_DOSYA_ADI  # noqa: E402
from yuvalar import defter, hormonlar, ton  # noqa: E402

YUVA_ADI = "web_sohbet"
PLATFORM = "site_yigit"
HOST = "127.0.0.1"
PORT = 8090
IZINLI_KAYNAK = "https://minik-sohbet.vercel.app"
ANAHTAR_YOLU = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "minik" / "sohbet-anahtar.txt"
ANAHTAR_UZUNLUK = 24
EN_UZUN_MESAJ = 500
CEVAP_BEKLEME_SN = 180  # Gemma 10-40 sn, ilk mesajda model yuklemesi dahil genis pay
BOSTA_YOKLAMA_SN = 60


def anahtar_oku(yol=ANAHTAR_YOLU):
    """Anahtar dosyasini okur; yoksa rastgele anahtar uretip yazar. Anahtar repoya girmez."""
    if not yol.exists():
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_text(secrets.token_urlsafe(ANAHTAR_UZUNLUK), encoding="utf-8")
        log.yaz(YUVA_ADI, "anahtar_uret", 0, "ok", {"yol": str(yol)})
    return yol.read_text(encoding="utf-8").strip()


class Sohbet:
    """minik.calistir'i ayri is parcaciginda kosturur: dinle gelen kuyruktan alir, soyle gideni doldurur.
    Kilit sayesinde ayni anda tek tur islenir, GPU'ya iki istek gitmez."""

    def __init__(self, dusun, hormon_durumu, ton_oku):
        self.gelen, self.giden = queue.Queue(), queue.Queue()
        self.hormon_durumu = hormon_durumu
        self._kilit = threading.Lock()
        threading.Thread(target=minik.calistir, daemon=True, kwargs=dict(
            dinle=self.gelen.get, soyle=lambda metin, dis_id: self.giden.put(metin), dusun=dusun,
            hormon_durumu=hormon_durumu, platform=PLATFORM, ton_oku=ton_oku)).start()

    def konus(self, mesaj):
        """Mesaji akisa verir, cevabi bekler. Sure dolarsa queue.Empty yukselir (cagiran 504 doner)."""
        with self._kilit:
            while not self.giden.empty():  # onceki zaman asimindan kalan gec cevap atilir
                log.yaz(YUVA_ADI, "gec_cevap_atildi", 0, "ok", {"metin": self.giden.get()[:80]})
            self.gelen.put(mesaj)
            return self.giden.get(timeout=CEVAP_BEKLEME_SN)

    def durum(self):
        return {"hormonlar": {k: round(v, 1) for k, v in self.hormon_durumu.oku().items()},
                "yas": self.hormon_durumu.yas}


class Isleyici(BaseHTTPRequestHandler):
    """Uclar: POST /konus, GET /durum, OPTIONS. Her istek X-Anahtar ister."""

    def _yanit(self, kod, govde=None):
        veri = json.dumps(govde or {}, ensure_ascii=False).encode("utf-8")
        self.send_response(kod)
        self.send_header("Access-Control-Allow-Origin", IZINLI_KAYNAK)
        self.send_header("Access-Control-Allow-Headers", "X-Anahtar, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(veri)))
        self.end_headers()
        self.wfile.write(veri)

    def _yetkili(self):
        gelen = self.headers.get("X-Anahtar", "")
        if secrets.compare_digest(gelen.encode(), self.server.anahtar.encode()):
            return True
        log.yaz(YUVA_ADI, "yetkisiz", 0, "hata", {"hata": "anahtar yanlis", "yol": self.path})
        self._yanit(401, {"hata": "Anahtar yanlis."})
        return False

    def do_OPTIONS(self):
        self._yanit(204)

    def do_GET(self):
        if not self._yetkili():
            return
        if self.path != "/durum":
            return self._yanit(404, {"hata": "Boyle bir yer yok."})
        self._yanit(200, {**self.server.sohbet.durum(), "kafa": self.server.kafa_durumu()})

    def do_POST(self):
        if not self._yetkili():
            return
        if self.path != "/konus":
            return self._yanit(404, {"hata": "Boyle bir yer yok."})
        mesaj = self._mesaj_oku()
        if mesaj is None:
            return self._yanit(400, {"hata": f"Mesaj bos olamaz, en cok {EN_UZUN_MESAJ} karakter."})
        self._konus(mesaj)

    def _mesaj_oku(self):
        """Govdeden mesaji alir; bozuk, bos ya da uzunsa None."""
        try:
            uzunluk = int(self.headers.get("Content-Length", 0))
            mesaj = str(json.loads(self.rfile.read(uzunluk).decode("utf-8")).get("mesaj", "")).strip()
        except (ValueError, AttributeError) as hata:
            log.yaz(YUVA_ADI, "konus", 0, "hata", {"hata": f"govde bozuk: {hata}"})
            return None
        return mesaj if 0 < len(mesaj) <= EN_UZUN_MESAJ and mesaj != minik.CIKIS_KELIMESI else None

    def _konus(self, mesaj):
        basladi = time.perf_counter()
        try:
            cevap = self.server.sohbet.konus(mesaj)
        except queue.Empty:
            log.yaz(YUVA_ADI, "konus", _ms(basladi), "hata", {"hata": f"{CEVAP_BEKLEME_SN} sn cevap yok"})
            return self._yanit(504, {"hata": "Minik zamaninda cevap veremedi."})
        log.yaz(YUVA_ADI, "konus", _ms(basladi), "ok", {"mesaj_uzunlugu": len(mesaj)})
        self._yanit(200, {"cevap": cevap, **self.server.sohbet.durum()})

    def log_message(self, bicim, *args):
        pass  # http.server'in stderr satirlari kapali; her olay log.yaz ile yaziliyor


def _ms(basladi):
    return int((time.perf_counter() - basladi) * 1000)


def sunucu_kur(anahtar, dusun, kafa_durumu, hormon_durumu, ton_oku=ton.ton_oku, host=HOST, port=PORT):
    """HTTP sunucusunu ve akis is parcacigini kurar; serve_forever cagirana kalir."""
    sunucu = ThreadingHTTPServer((host, port), Isleyici)
    sunucu.anahtar, sunucu.kafa_durumu = anahtar, kafa_durumu
    sunucu.sohbet = Sohbet(dusun, hormon_durumu, ton_oku)
    return sunucu


def _bosta_izle(yonetici):
    while True:
        time.sleep(BOSTA_YOKLAMA_SN)
        yonetici.bosta_kapat()


def main():
    from agiz.web_sohbet_kafa import KafaYonetici
    yonetici = KafaYonetici()
    hormon = hormonlar.Hormonlar(defter.DEFTER_KLASORU / HORMON_DOSYA_ADI)
    sunucu = sunucu_kur(anahtar_oku(), yonetici.dusun, lambda: yonetici.durum, hormon)
    threading.Thread(target=_bosta_izle, args=(yonetici,), daemon=True).start()
    log.yaz(YUVA_ADI, "basla", 0, "ok", {"adres": f"{HOST}:{PORT}"})
    print(f"Web sohbet {HOST}:{PORT} dinliyor. Anahtar dosyasi: {ANAHTAR_YOLU}")
    try:
        sunucu.serve_forever()
    finally:
        yonetici.kapat()


if __name__ == "__main__":
    main()
