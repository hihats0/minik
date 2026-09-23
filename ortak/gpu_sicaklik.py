"""GPU sicaklik sarmalayicisi: ayri is parcaciginda nvidia-smi ile sicaklik okur ve loglar, istekten once
80 C'de 70'e kadar bekletir, istek SURERKEN 83 C'de verilen durdurma fonksiyonunu cagirir (k26-d, f3-g).
Cagiran: araclar/k26d-hormon-uzunluk.py; GPU'ya uzun istek atan her olcum araci."""

import subprocess
import threading
import time

from ortak import log

YUVA_ADI = "gpu_sicaklik"
SICAKLIK_SORGUSU = ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"]
# Proje kurali (CLAUDE.md): 80'de durakla, 70'e inince devam.
DURAKLA_C = 80
DEVAM_C = 70
# gpu-bekci 85'te llama-server'i keser; bir gunde ikinci kesme o gunun GPU'sunu bitirir. Bizim sinir altinda.
KES_C = 83
# Gorev: en az 10 sn'de bir okuma. k26-c'de tek istek ~28 sn, 30 sn aralik istegi kacirabiliyordu.
OKUMA_ARALIGI_SN = 10
SOGUMA_YOKLAMA_SN = 5


def nvidia_smi_oku():
    """Ilk NVIDIA GPU'nun sicakligi (C). nvidia-smi hata verirse hata yukselir, yutulmaz."""
    cikti = subprocess.check_output(SICAKLIK_SORGUSU, text=True)
    return int(cikti.strip().splitlines()[0])


class SicaklikBekcisi:
    """Arka planda sicaklik izler. kes: 83 C'de bir kez cagrilan fonksiyon (llama-server'i durdurur).
    okuyucu ve aralik testte sahtesiyle degistirilir."""

    def __init__(self, kes, okuyucu=nvidia_smi_oku, aralik_sn=OKUMA_ARALIGI_SN):
        self.kes = kes
        self.okuyucu = okuyucu
        self.aralik_sn = aralik_sn
        self.son_c = self.okuyucu()
        self.en_yuksek_c = self.son_c
        self.kesildi = False
        self._dur = threading.Event()
        self._is = threading.Thread(target=self._dongu, daemon=True)

    def baslat(self):
        self._is.start()
        return self

    def bitir(self):
        self._dur.set()
        self._is.join()

    def _dongu(self):
        """aralik_sn'de bir okur, loglar; KES_C'ye varinca kes() bir kez cagrilir."""
        while not self._dur.wait(self.aralik_sn):
            self._oku_kaydet()
            if self.son_c >= KES_C and not self.kesildi:
                self.kesildi = True
                log.yaz(YUVA_ADI, "kes", 0, "hata",
                        {"hata": f"sicaklik {self.son_c} C >= {KES_C}, llama-server durduruluyor"})
                self.kes()

    def _oku_kaydet(self):
        self.son_c = self.okuyucu()
        self.en_yuksek_c = max(self.en_yuksek_c, self.son_c)
        log.yaz(YUVA_ADI, "oku", 0, "ok", {"c": self.son_c, "en_yuksek": self.en_yuksek_c})

    def serinle(self):
        """Istekten once cagrilir: son okuma DURAKLA_C ve ustundeyse DEVAM_C'ye inene kadar bekler.
        Bekleme sirasinda arka plandaki okumalar son_c'yi gunceller. Bekledigi saniyeyi dondurur."""
        basladi = time.perf_counter()
        if self.son_c < DURAKLA_C:
            return 0.0
        log.yaz(YUVA_ADI, "durakla", 0, "ok", {"c": self.son_c})
        while self.son_c > DEVAM_C and not self.kesildi:
            time.sleep(SOGUMA_YOKLAMA_SN)
        return round(time.perf_counter() - basladi, 1)

    def kesme_sonrasi_bekle(self):
        """Kesmeden sonra cagrilir: DEVAM_C'ye inene kadar bekler, kesildi bayragini indirir (yeni sunucu
        yeniden kesilebilsin). Bekledigi saniyeyi dondurur."""
        basladi = time.perf_counter()
        log.yaz(YUVA_ADI, "kesme_sonrasi_bekle", 0, "ok", {"c": self.son_c})
        while self.son_c > DEVAM_C:
            time.sleep(SOGUMA_YOKLAMA_SN)
        self.kesildi = False
        return round(time.perf_counter() - basladi, 1)
