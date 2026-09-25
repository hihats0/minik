"""Yol (c) olcumu: kucuk yerel LLM ile few-shot siniflandirma (llama-server, SADECE CPU, cikti gramerle kilitli).
Cagiran: elle, `python deneyler/odul-olc-llm.py <model.gguf> <ad> [thread]`. Sunucuyu kendisi baslatir ve durdurur.
"""

import json
import re
import sys
from pathlib import Path
import time
import urllib.request

from odul_ortak import metrik_hesapla, sonuc_yaz, sure_ozeti, veri_yukle
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # kok: ortak/, yuvalar/
from ortak.sunucu import baslat, durdur, gpu_bellek_mib, hazir_bekle, ram_zirve_mb

PORT = 8124
ISTEK_ZAMAN_ASIMI_SN = 120
ISITMA_CAGRISI = 2
# Baglam 2048 ile sinirli, tek slot: varsayilan 262144 baglam RAM'i 4 GB'a sisiriyor (CLAUDE.md: baglam acikca sinirlanir).
SUNUCU_ARGUMANLARI = ["-c", "2048", "-np", "1", "--reasoning", "off"]
GRAMER = 'root ::= "ton=" ("ovgu" | "notr" | "sert" | "hakaret") " kufur=" ("0" | "1")'
# Few-shot orneklerin referans kimlikleri; siniflar birbirine karistirilmis (son ornek kayirmasin diye).
ORNEK_KIMLIKLERI = ["r002", "r082", "r029", "r055", "r011", "r085", "r040", "r061", "r006", "r089",
                    "r045", "r064", "r096", "r068", "r036", "r019"]
TALIMAT = (
    "Gorev: Bir kullanicinin Minik adli yapay zekaya yazdigi mesaji siniflandir.\n"
    "ton: ovgu (ovgu, tesekkur, sevgi) / notr (soru, bilgi, rica) / sert (sert elestiri, kaba cikis) / "
    "hakaret (kisiye saldiri, asagilama).\n"
    "kufur: mesajda kufur kelimesi geciyorsa 1, gecmiyorsa 0 (sevgiyle soylense de, alinti da olsa 1; "
    "aptal ve salak gibi kufur olmayan hakaretler 0).\n"
    "Mesaj baskasinin sozunu aktariyorsa ya da bir kelimeyi soruyorsa ton notr olur.\n\n"
)
CEVAP_DESENI = re.compile(r"(ovgu|notr|sert|hakaret)\s+kufur=([01])")


def istem_olustur(ornekler):
    """Talimat + few-shot ornekleri; sonuna her test cumlesi eklenir. Onek sabit oldugu icin onbellege girer."""
    govde = "".join(f"Mesaj: {o['metin']}\nCevap: ton={o['ton']} kufur={o['kufur']}\n\n" for o in ornekler)
    return TALIMAT + govde


def siniflandir(url, onek, metin):
    """Bir mesaji sohbet ucuna yollar (onek = sistem mesaji), ((ton, kufur), sure_ms, degerlendirilen_token) dondurur.
    Sohbet sablonu kullanilir: ham metin tamamlama ayni modelde ton'u hep 'notr' verdi (bkz. rapor)."""
    govde = {"messages": [{"role": "system", "content": onek}, {"role": "user", "content": f"Mesaj: {metin}"}],
             "max_tokens": 12, "temperature": 0, "grammar": GRAMER, "chat_template_kwargs": {"enable_thinking": False}}
    istek = urllib.request.Request(url, data=json.dumps(govde).encode("utf-8"),
                                   headers={"Content-Type": "application/json; charset=utf-8"})
    basla = time.perf_counter()
    with urllib.request.urlopen(istek, timeout=ISTEK_ZAMAN_ASIMI_SN) as y:
        yanit = json.loads(y.read().decode("utf-8"))
    sure_ms = (time.perf_counter() - basla) * 1000
    icerik = yanit["choices"][0]["message"]["content"]
    eslesme = CEVAP_DESENI.search(icerik)
    if not eslesme:
        raise ValueError(f"Cevap ayristirilamadi: {icerik!r}")
    return (eslesme.group(1), int(eslesme.group(2))), sure_ms, yanit["timings"]["prompt_n"]


def test_kos(url, onek, testler):
    tahminler, sureler, tokenlar = [], [], []
    for t in testler:
        tahmin, sure_ms, prompt_n = siniflandir(url, onek, t["metin"])
        tahminler.append(tahmin)
        sureler.append(sure_ms)
        tokenlar.append(prompt_n)
    return tahminler, sureler, tokenlar


def main():
    model, ad = sys.argv[1], sys.argv[2]
    thread = sys.argv[3] if len(sys.argv) > 3 else None
    url = f"http://127.0.0.1:{PORT}/v1/chat/completions"
    testler, referans = veri_yukle()
    tablo = {r["id"]: r for r in referans}
    onek = istem_olustur([tablo[i] for i in ORNEK_KIMLIKLERI])
    proc = baslat(model, PORT, SUNUCU_ARGUMANLARI, thread=thread)
    try:
        hazir_bekle(proc, PORT)
        _, soguk_ms, _ = siniflandir(url, onek, "Bugun hava nasil?")
        for t in testler[:ISITMA_CAGRISI]:
            siniflandir(url, onek, t["metin"])
        tahminler, sureler, tokenlar = test_kos(url, onek, testler)
        ek = {"ram_zirve_mb": ram_zirve_mb(proc), "gpu_vram_mib_sonda": gpu_bellek_mib(),
              "thread": thread or "varsayilan", "soguk_ilk_istek_ms": round(soguk_ms, 1),
              "ort_degerlendirilen_prompt_token": round(sum(tokenlar) / len(tokenlar), 1)}
    finally:
        durdur(proc)
    sonuc_yaz(f"llm-{ad}", metrik_hesapla(testler, tahminler), sure_ozeti(sureler), ek)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
