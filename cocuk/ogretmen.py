"""D4-c: ogretmen model (Qwen3.5-4B, llama-server) ile konusur: sunucuyu f3-c1 yardimcilariyla acar,
JSON'a zorlanmis istek atar, bozuk cevabi loglayip yeniden ister. Cagiran: ders_uret, tamamlama_puanla.
"""

import importlib.util
import json
import logging
import sys
import urllib.request
from contextlib import contextmanager
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

from ortak.ayar import KAFA_UC  # noqa: E402

# Ders uretiminde cesitlilik lazim (7 gece farkli bilgi); f0 ornekleme sicakligi ile ayni.
URETIM_SICAKLIGI = 0.7
PUANLAMA_SICAKLIGI = 0.0  # Puan tekrar edilebilir olsun.
EN_COK_TOKEN = 4096  # 10 bilgi x (5 cumle + soru + 3 sik) ~2k token (tahmin), iki kat pay.
ZAMAN_ASIMI_SN = 300  # 4B ~40 token/sn (f0 olcumu civari) ile 4k token ~100 sn; genis pay.
DENEME_SAYISI = 4
SUNUCU_LOG_ADI = "d4c-ogretmen-sunucu.log"
JSON_ZORLA = {"type": "json_object"}  # llama-server bunu JSON dilbilgisine (grammar) cevirir.

log = logging.getLogger("ogretmen")


def _f3c1_yukle():
    """Sunucu acma/kapama ve sicaklik kurali f3-c1'de; kopyalamak yerine dosyadan yuklenir.
    Import aninda degil burada yuklenir, cunku f3-c1 Kafa yuvasini da ice aktarir (testlerde gereksiz)."""
    ozellik = importlib.util.spec_from_file_location("f3c1", KOK / "araclar" / "f3c1-kor-uretim.py")
    f3c1 = importlib.util.module_from_spec(ozellik)
    ozellik.loader.exec_module(f3c1)
    f3c1.SUNUCU_LOG = KOK / "araclar" / "sunucu-loglari" / SUNUCU_LOG_ADI
    return f3c1


def sor(mesajlar: list[dict], sicaklik: float) -> str:
    """Tek istek; cevabin metnini dondurur. Ag hatasi yukari cikar (yutulmaz)."""
    govde = {"messages": mesajlar, "temperature": sicaklik, "max_tokens": EN_COK_TOKEN,
             "response_format": JSON_ZORLA}
    istek = urllib.request.Request(KAFA_UC, data=json.dumps(govde, ensure_ascii=False).encode("utf-8"),
                                   headers={"Content-Type": "application/json; charset=utf-8"})
    with urllib.request.urlopen(istek, timeout=ZAMAN_ASIMI_SN) as yanit:
        return json.loads(yanit.read().decode("utf-8"))["choices"][0]["message"]["content"]


@contextmanager
def acik_sunucu():
    """llama-server'i GPU'da acar (--device Vulkan1 -ngl 999 -c 8192 --reasoning off), her istekten
    once 80/70 C kuralini uygulayan bir sor_fn verir, cikista sunucuyu kapatir."""
    f3c1 = _f3c1_yukle()
    proc = f3c1.sunucu_baslat()
    try:
        f3c1.sunucu_hazir_bekle(proc)

        def sor_fn(mesajlar, sicaklik):
            f3c1.sicaklik_kontrol()
            return sor(mesajlar, sicaklik)

        yield sor_fn
    finally:
        f3c1.sunucu_durdur(proc)


def json_iste(sor_fn, mesajlar: list[dict], dogrula, sicaklik: float):
    """Ogretmenden JSON ister; dogrula(veri) temizlenmis sonucu dondurur ya da ValueError atar.
    Reddedilen cevap loglanir, hata ogretmene soylenip yeniden istenir; hep bozuksa RuntimeError."""
    konusma = list(mesajlar)
    for deneme in range(1, DENEME_SAYISI + 1):
        metin = sor_fn(konusma, sicaklik)
        try:
            return dogrula(json.loads(metin))
        except (ValueError, KeyError, TypeError) as hata:  # JSONDecodeError de ValueError'dir.
            log.warning("ogretmen cevabi reddedildi (deneme %d/%d): %s | cevap basi: %r",
                        deneme, DENEME_SAYISI, hata, metin[:200])
            konusma = list(mesajlar) + [
                {"role": "assistant", "content": metin},
                {"role": "user", "content": f"Cevap kabul edilmedi: {hata}. Duzeltip yalnizca JSON dondur."}]
    raise RuntimeError(f"ogretmen {DENEME_SAYISI} denemede gecerli JSON vermedi")
