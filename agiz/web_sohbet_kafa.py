"""Web sohbetinin Kafa (llama-server, GPU) yonetimi: ilk mesajda acar, sicaklik bekcisiyle korur, 84 C'de
kesilirse sonraki turda yeniden acar, uzun sessizlikte kapatip VRAM'i bosaltir. Cagiran: agiz/web_sohbet.py."""

import subprocess
import threading
import time
from pathlib import Path

from ortak import log
from ortak import sunucu as sunucu_yonet
from ortak.ayar import GEMMA_SUNUCU_ARGUMANLARI, KAFA_PORT
from ortak.gpu_sicaklik import SicaklikBekcisi
from yuvalar import kafa

YUVA_ADI = "web_sohbet_kafa"
BOSTA_KAPAT_SN = 60 * 60  # 60 dk mesaj gelmezse llama-server kapanir, VRAM bosalir
SUNUCU_LOG = Path(__file__).resolve().parent.parent / "loglar" / "web-sohbet-sunucu.log"
EK_ARGUMAN = ["-ngl", "99", "-np", "1", "--port", str(KAFA_PORT), "--no-webui"]
HAZIR, YUKLENIYOR, KAPALI = "hazir", "yukleniyor", "kapali"


def gercek_sunucu_baslat():
    """Gemma'yi GPU'da acar (GEMMA_SUNUCU_ARGUMANLARI icinde --device Vulkan1 var)."""
    SUNUCU_LOG.parent.mkdir(exist_ok=True)
    cikti = SUNUCU_LOG.open("a", encoding="utf-8")
    return subprocess.Popen([sunucu_yonet.LLAMA_SERVER, *GEMMA_SUNUCU_ARGUMANLARI, *EK_ARGUMAN],
                            stdout=cikti, stderr=subprocess.STDOUT)


class KafaYonetici:
    """dusun() calistir'a verilir: once sunucuyu hazirlar, sonra Kafa'ya sorar. Parametreler testte sahtedir."""

    def __init__(self, baslat=gercek_sunucu_baslat, hazir_bekle=None, durdur=sunucu_yonet.durdur,
                 bekci_yap=None, dusun_fn=kafa.dusun):
        self.baslat, self.durdur, self.dusun_fn = baslat, durdur, dusun_fn
        self.hazir_bekle = hazir_bekle or (lambda proc: sunucu_yonet.hazir_bekle(proc, KAFA_PORT))
        self.bekci_yap = bekci_yap or (lambda kes: SicaklikBekcisi(kes=kes).baslat())
        self.proc = self.bekci = None
        self.durum = KAPALI
        self.son_istek = time.monotonic()
        self._kilit = threading.Lock()

    def dusun(self, soru, baglam=None, hormon_degerleri=None):
        self.son_istek = time.monotonic()
        with self._kilit:
            self._hazirla()
        return self.dusun_fn(soru, baglam, hormon_degerleri)

    def _hazirla(self):
        """Bekci yoksa kurar; kesilmisse soguyana kadar bekler; soguma bekler; sunucu kapaliysa acar."""
        if self.bekci is None:
            self.bekci = self.bekci_yap(self._sunucuyu_durdur)
        if self.bekci.kesildi:
            log.yaz(YUVA_ADI, "kesme_sonrasi", 0, "ok", {"bekledi_sn": self.bekci.kesme_sonrasi_bekle()})
        self.bekci.serinle()
        if self.proc is None or self.proc.poll() is not None:
            self.durum = YUKLENIYOR
            basladi = time.perf_counter()
            self.proc = self.baslat()
            try:
                self.hazir_bekle(self.proc)
            except Exception as hata:
                log.yaz(YUVA_ADI, "ac", 0, "hata", {"hata": str(hata)})
                self._sunucuyu_durdur()
                raise
            log.yaz(YUVA_ADI, "ac", int((time.perf_counter() - basladi) * 1000), "ok", {"port": KAFA_PORT})
        self.durum = HAZIR

    def _sunucuyu_durdur(self):
        if self.proc is not None:
            self.durdur(self.proc)
            log.yaz(YUVA_ADI, "kapat", 0, "ok", {"port": KAFA_PORT})
        self.proc = None
        self.durum = KAPALI

    def bosta_kapat(self, simdi=None):
        """Son istekten BOSTA_KAPAT_SN gectiyse sunucuyu ve bekciyi kapatir. True: kapatti."""
        simdi = time.monotonic() if simdi is None else simdi
        if self.proc is None or simdi - self.son_istek < BOSTA_KAPAT_SN:
            return False
        with self._kilit:
            self.kapat()
        log.yaz(YUVA_ADI, "bosta_kapat", 0, "ok", {"bosta_sn": int(simdi - self.son_istek)})
        return True

    def kapat(self):
        self._sunucuyu_durdur()
        if self.bekci is not None:
            self.bekci.bitir()
            self.bekci = None
