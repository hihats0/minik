"""GPU sicaklik sarmalayicisi: ayri is parcaciginda nvidia-smi ile sicaklik okur ve loglar; 80 C gorulunce
sonraki istekten once 70'e kadar bekletir, istek SURERKEN 84 C'de durdurma fonksiyonunu cagirir (sicak-a).
Cagiran: araclar/k26d-hormon-uzunluk.py; GPU'ya uzun istek atan her olcum araci."""

import subprocess
import threading
import time

from ortak import log

YUVA_ADI = "gpu_sicaklik"
SICAKLIK_SORGUSU = ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader,nounits"]
# Proje kurali (CLAUDE.md): 80'de durakla, 70'e inince devam. Projedeki tek kaynak bu iki sabit (sicak-a).
DURAK_ESIGI_C = 80
DEVAM_ESIGI_C = 70
# Kural: sicaklik is suresince en az 30 sn'de bir okunur; kurucu daha seyrek araligi reddeder.
EN_UZUN_OKUMA_ARALIGI_SN = 30
# Bilerek daha siki: istekten once bu sicakligin ustundeyse DEVAM_ESIGI_C'ye inene kadar beklenir: laptop tek istekte ~12 C isiniyor
# (f3-g 23 Eyl olcumu), 76-82 C'de baslayan istekler 83'u gecti. Kart 80 -> 70'e 10-15 sn'de iniyor.
# 24 Eyl: istekler 68-78'de baslayip 81-83'e cikiyordu, bekci aracin 10 sn okuma arasinda 85'i gordu; 65'e indi.
ISTEK_ONCESI_ESIK_C = 65
# Koşan istek durdurulamaz; 80'i gecerse bekci durak bayragini kaldirir, 84'te sunucuyu keser.
# Kesme guvenlik agidir: araclar/gpu-bekci.ps1 85'te oldurur, arac bir derece once temiz kessin; 84'e kadar kisa asim Yigit onayli (22 Eyl).
# 85 denendi: 24 Eyl 00:15'te bekci aractan once davrandi (aracin son okumasi 83'tu).
KES_C = 84
# Gorev: en az 10 sn'de bir okuma. k26-c'de tek istek ~28 sn, 30 sn aralik istegi kacirabiliyordu.
# 24 Eyl: 10 -> 5 sn, nvidia-smi ucuz, bekciden once gorsun.
OKUMA_ARALIGI_SN = 5
SOGUMA_YOKLAMA_SN = 5


def nvidia_smi_oku():
    """Ilk NVIDIA GPU'nun sicakligi (C). nvidia-smi hata verirse hata yukselir, yutulmaz."""
    cikti = subprocess.check_output(SICAKLIK_SORGUSU, text=True)
    return int(cikti.strip().splitlines()[0])


class SicaklikBekcisi:
    """Arka planda sicaklik izler. kes: KES_C'de bir kez cagrilan fonksiyon (llama-server'i durdurur).
    okuyucu ve aralik testte sahtesiyle degistirilir."""

    def __init__(self, kes, okuyucu=nvidia_smi_oku, aralik_sn=OKUMA_ARALIGI_SN, uyku=time.sleep):
        if aralik_sn > EN_UZUN_OKUMA_ARALIGI_SN:
            raise ValueError(f"okuma araligi {aralik_sn} sn > {EN_UZUN_OKUMA_ARALIGI_SN} sn kurali")
        self.kes = kes
        self.uyku = uyku
        self.durak_gerek = False
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
            self._adim()

    def _adim(self):
        """Tek okuma: loglar, 80'de durak bayragini kaldirir, KES_C'de kes() bir kez cagrilir."""
        self._oku_kaydet()
        if self.son_c >= DURAK_ESIGI_C and not self.durak_gerek:
            self.durak_gerek = True
            log.yaz(YUVA_ADI, "durak_esigi", 0, "ok", {"c": self.son_c, "esik": DURAK_ESIGI_C})
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
        """Istekten once cagrilir: son istekte 80 goruldu ya da son okuma ISTEK_ONCESI_ESIK_C'nin ustundeyse
        DEVAM_ESIGI_C'ye inene kadar bekler. Okumalari arka plan yapar. Bekledigi saniyeyi dondurur."""
        basladi = time.perf_counter()
        if self.son_c <= ISTEK_ONCESI_ESIK_C and not self.durak_gerek:
            return 0.0
        log.yaz(YUVA_ADI, "durakla", 0, "ok", {"c": self.son_c, "durak_esigi_goruldu": self.durak_gerek})
        while self.son_c > DEVAM_ESIGI_C and not self.kesildi:
            log.yaz(YUVA_ADI, "bekliyor", 0, "ok", {"c": self.son_c, "hedef": DEVAM_ESIGI_C})
            self.uyku(SOGUMA_YOKLAMA_SN)
        self.durak_gerek = False
        log.yaz(YUVA_ADI, "devam", 0, "ok", {"c": self.son_c})
        return round(time.perf_counter() - basladi, 1)

    def kesme_sonrasi_bekle(self):
        """Kesmeden sonra cagrilir: DEVAM_ESIGI_C'ye inene kadar bekler, kesildi bayragini indirir (yeni sunucu
        yeniden kesilebilsin). Bekledigi saniyeyi dondurur."""
        basladi = time.perf_counter()
        log.yaz(YUVA_ADI, "kesme_sonrasi_bekle", 0, "ok", {"c": self.son_c})
        while self.son_c > DEVAM_ESIGI_C:
            self.uyku(SOGUMA_YOKLAMA_SN)
        self.kesildi = False
        self.durak_gerek = False
        return round(time.perf_counter() - basladi, 1)


# Sicak kesmede istek sonucu satirina yazilan isaretler (k26-d, f3-g ayni degerleri kullanir).
SICAK_ATLANDI = "sicak_olculemedi"
SICAK_TEKRAR = "kesildi_tekrar_denenecek"
# k26-d kurali: ayni istek 2 kez kesilirse atla, toplam 4 kesmede kosuyu bitir.
AYNI_ISTEK_KESME_SINIRI = 2
TOPLAM_KESME_SINIRI = 4


def sicakta_dene(olc, bekci, kaydet, yeniden_baslat, sayac):
    """olc() bir istegi olcup satir dondurur. Istek surerken sicak kesme olursa 70 C'ye kadar bekler,
    sunucuyu yeniden acar, tekrar dener; ust uste AYNI_ISTEK_KESME_SINIRI kesmede istegi atlar.
    Her satir kaydet()'e gider. sayac["kesme"] kosu boyunca birikir. False: toplam kesme siniri doldu."""
    for deneme in range(1, AYNI_ISTEK_KESME_SINIRI + 1):
        satir = olc()
        if not bekci.kesildi:
            kaydet(satir)
            return True
        sayac["kesme"] += 1
        satir["olcum"] = SICAK_ATLANDI if deneme == AYNI_ISTEK_KESME_SINIRI else SICAK_TEKRAR
        satir["kesme_sonrasi_bekleme_sn"] = bekci.kesme_sonrasi_bekle()
        kaydet(satir)
        if sayac["kesme"] >= TOPLAM_KESME_SINIRI:
            return False
        yeniden_baslat()
    return True
