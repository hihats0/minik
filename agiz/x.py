"""X agzi (f8-b, spec 2.6): yalniz paylasim. Cevap Bekci cikis kapisindan gecerse "Automated" etiketiyle
yerel kuyruk dosyasina yazilir; gercek gonderim yok (K29 bekliyor). Cagiran: agiz/secim.py, testler."""

import json
from datetime import datetime
from pathlib import Path

from agiz.dosya import DosyaAgzi
from ortak import log
from yuvalar import bekci

PLATFORM = "x"
YUVA_ADI = "agiz_x"
VARSAYILAN_GIRDI = Path("x-agzi") / "konular.txt"
VARSAYILAN_KUYRUK = Path("x-agzi") / "kuyruk.jsonl"
# X politikasi bot hesabinin acikca etiketlenmesini ister (spec 2.6); etiket gonderinin icinde durur.
OTOMATIK_ETIKETI = "[Automated]"
UZUNLUK_SINIRI = 280  # X'in duz hesap karakter siniri; etiket dahil
GERCEK_GONDERIM_ACIK = False  # Yigit karari (K29) olmadan acilmaz
GERCEK_GONDERIM_HATASI = "X'e gercek gonderim kapali: Yigit karari bekleniyor (K29)"


class GercekGonderimKapali(RuntimeError):
    """Gercek gonderim yolu cagrildiginda yukselir; bu yolun govdesi bilerek yazilmadi."""


def gercek_gonder(gonderi):
    """Gercek X gonderimi. Govde yok: ag kodu Yigit'in karari gelmeden yazilmaz."""
    raise GercekGonderimKapali(GERCEK_GONDERIM_HATASI)


def gonderi_hazirla(metin):
    """Metne etiketi ekler, siniri asarsa keser; (gonderi, kesildi_mi) dondurur."""
    gonderi = f"{metin.strip()} {OTOMATIK_ETIKETI}"
    if len(gonderi) <= UZUNLUK_SINIRI:
        return gonderi, False
    pay = UZUNLUK_SINIRI - len(OTOMATIK_ETIKETI) - 1
    return f"{metin.strip()[:pay]} {OTOMATIK_ETIKETI}", True


class XAgzi:
    """dinle() yerel konu dosyasindan okur (X'ten okumaz); soyle() kuyruga yazar (X'e gondermez)."""

    def __init__(self, girdi=VARSAYILAN_GIRDI, kuyruk=VARSAYILAN_KUYRUK, gercek=GERCEK_GONDERIM_ACIK):
        self._konular = DosyaAgzi(girdi, Path(kuyruk).parent / "kullanilmaz.txt")
        self._kuyruk = Path(kuyruk)
        self._gercek = gercek

    def dinle(self):
        """Siradaki konuyu verir; dosya bitince cikis kelimesi (dosya agziyla ayni)."""
        return self._konular.dinle()

    def soyle(self, metin, dis_id):
        """Bekci'den gecen cevabi etiketleyip kuyruga ekler; gecmeyeni loglar, kuyruga koymaz."""
        gecti, gerekce = bekci.cikabilir_mi(metin)
        if not gecti:
            log.yaz(YUVA_ADI, "soyle", 0, "ok", {"kuyruk": False, "gerekce": gerekce})
            return {"gonderildi": False, "hata": gerekce}
        gonderi, kesildi = gonderi_hazirla(metin)
        if self._gercek:
            gercek_gonder(gonderi)
        satir = {"t": datetime.now().isoformat(timespec="seconds"), "metin": gonderi, "kesildi": kesildi}
        with self._kuyruk.open("a", encoding="utf-8") as f:
            f.write(json.dumps(satir, ensure_ascii=False) + "\n")
        log.yaz(YUVA_ADI, "soyle", 0, "ok", {"kuyruk": True, "kesildi": kesildi})
        return {"gonderildi": False, "dis_id": None}
