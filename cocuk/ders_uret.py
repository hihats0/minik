"""D4-c: ogretmen modelden 7 gecelik dersi tek kosuda uretir (gece basina 10 kurgusal bilgi + 50 okul
cumlesi), dogrular, cocuk/dersler/gece_N.json'a yazar. Cagiran: elle `python -m cocuk.ders_uret`.
"""

import json
import logging

from cocuk import ders_dogrula as dd
from cocuk import ogretmen
from cocuk.egit_araclari import COCUK_DIZINI

DERS_DIZINI = COCUK_DIZINI / "dersler"
GECE_SAYISI = 7
SISTEM = ("Sen küçük bir çocuğa Türkçe öğreten sabırlı bir öğretmensin. "
          "Yalnızca istenen biçimde geçerli JSON döndür, başka hiçbir şey yazma.")
# Her gece baska bir kurgusal dunya: bilgiler birbirine karismasin, gece bazinda hatirlama olculsun.
KONULAR = [
    "Minik'in evi ve evcil hayvanları (uydurma adlar)",
    "Uydurma bir kasaba: Pırtıköy ve orada yaşayanlar",
    "Uydurma hayvanlar: adları, renkleri, ne yedikleri",
    "Minik'in arkadaşları ve sevdikleri şeyler",
    "Uydurma bir ada: Fıstıkada'nın yerleri ve adetleri",
    "Uydurma yemekler, meyveler ve tatları",
    "Minik'in okulu: öğretmenler, dersler, oyunlar",
]
# Basit cumle mufredati: her gece bir dilbilgisi adimi eklenir, 3 kelimeden 6 kelimeye cikar.
MUFREDAT = [
    "3-4 kelime, şimdiki zaman (-yor), özne + yüklem ya da özne + nesne + yüklem",
    "3-4 kelime, geçmiş zaman (-dı/-di), hal ekleri -e ve -de",
    "4 kelime, -den hal eki ve iyelik ekleri (kitabım, evimiz)",
    "4-5 kelime, olumsuz cümleler (-me/-ma) ve soru eki (mı/mi)",
    "4-5 kelime, gelecek zaman (-acak/-ecek) ve sıfatlar (büyük, kırmızı)",
    "5-6 kelime, geniş zaman (-ır/-er), zaman zarfları (sabah, dün, yarın)",
    "5-6 kelime, 've' bağlacı, çoğul ekleri ve karışık zamanlar",
]
OKUL_BICIM = '{"cumleler": ["...", "..."]}'
BILGI_BICIM = ('{"bilgiler": [{"bilgi": "...", "cumlelemeler": ["...", "...", "...", "...", "..."], '
               '"soru": "... ___ ...", "cevap": "...", "yanlislar": ["...", "...", "..."]}]}')

log = logging.getLogger("ders_uret")


def okul_mesajlari(gece: int) -> list[dict]:
    istem = (f"Gece {gece} okul dersi. Seviye: {MUFREDAT[gece - 1]}.\n"
             f"{dd.OKUL_CUMLE_SAYISI} kısa Türkçe cümle yaz. Her cümle {dd.OKUL_EN_AZ_KELIME} ile "
             f"{dd.OKUL_EN_COK_KELIME} kelime arasında olsun, dilbilgisi kusursuz, çocuk kitabı "
             "sadeliğinde, nokta, soru ya da ünlem işaretiyle bitsin. Cümleler birbirinden farklı olsun.\n"
             f"Biçim: {OKUL_BICIM}")
    return [{"role": "system", "content": SISTEM}, {"role": "user", "content": istem}]


def bilgi_mesajlari(gece: int, onceki: list[dict]) -> list[dict]:
    eski = "; ".join(b["bilgi"] for d in onceki for b in d["bilgiler"]) or "yok"
    istem = (f"Gece {gece} bilgi dersi. Konu: {KONULAR[gece - 1]}.\n"
             f"Çocuğa öğretilecek {dd.BILGI_SAYISI} yeni bilgi uydur. Bilgiler kurgusal olsun: gerçek "
             "dünyada ve Vikipedi'de bulunmayan uydurma adlar kullan (ör. \"Minik'in kedisinin adı "
             "Pamuk.\"). Her bilgi basit ve tek cümlelik olsun.\n"
             f"Önceki gecelerin bilgilerini tekrar etme: {eski}\n"
             "Her bilgi için:\n- \"bilgi\": bilginin kendisi\n"
             f"- \"cumlelemeler\": aynı bilgiyi anlatan {dd.CUMLELEME_SAYISI} farklı kısa cümle, "
             "her birinde cevap kelimesi geçsin\n"
             f"- \"soru\": bilgiyi soran, tek {dd.BOSLUK} boşluklu bir cümle; cevap yerine konunca "
             "cümlelemelerin hiçbiriyle aynı olmasın, başka kelimelerle kurulsun\n"
             f"- \"cevap\": boşluğa gelen bir ya da iki kelime\n"
             f"- \"yanlislar\": boşluğa gelebilecek {dd.YANLIS_SAYISI} yanlış seçenek; cevapla "
             "aynı türden, onun gibi uydurma ve benzer uzunlukta olsun\n"
             f"Biçim: {BILGI_BICIM}")
    return [{"role": "system", "content": SISTEM}, {"role": "user", "content": istem}]


def geceyi_uret(gece: int, onceki: list[dict], sor_fn) -> dict:
    """Once okul cumleleri, sonra bilgiler (bilgi sizinti kontrolu okul cumlelerini de tarar)."""
    okul = ogretmen.json_iste(sor_fn, okul_mesajlari(gece),
                              lambda v: dd.okul_suz(v["cumleler"]), ogretmen.URETIM_SICAKLIGI)
    bilgiler = ogretmen.json_iste(sor_fn, bilgi_mesajlari(gece, onceki),
                                  lambda v: dd.bilgileri_suz(v["bilgiler"], onceki, okul),
                                  ogretmen.URETIM_SICAKLIGI)
    return {"gece": gece, "konu": KONULAR[gece - 1], "seviye": MUFREDAT[gece - 1],
            "bilgiler": bilgiler, "okul": okul}


def hepsini_uret(sor_fn, gece_sayisi: int = GECE_SAYISI) -> list[dict]:
    """Gece gece uretir ve yazar. Var olan ders ustune yazilmaz (egitilmis modelin sinavi degismesin);
    yarida kalan kosu kaldigi geceden devam eder."""
    DERS_DIZINI.mkdir(parents=True, exist_ok=True)
    dersler = []
    for gece in range(1, gece_sayisi + 1):
        yol = DERS_DIZINI / f"gece_{gece}.json"
        if yol.exists():
            dersler.append(json.loads(yol.read_text("utf-8")))
            log.info("gece %d dersi zaten var, atlandi", gece)
            continue
        ders = geceyi_uret(gece, dersler, sor_fn)
        yol.write_text(
            json.dumps(ders, ensure_ascii=False, indent=1), encoding="utf-8")
        log.info("gece %d dersi yazildi: %d bilgi, %d okul cumlesi", gece,
                 len(ders["bilgiler"]), len(ders["okul"]))
        dersler.append(ders)
    if dd.sizinti_var(dersler):
        raise RuntimeError("dersler arasi cevap sizintisi var; dogrulama hatasi, dersleri inceleyin")
    return dersler


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    with ogretmen.acik_sunucu() as sor_fn:
        hepsini_uret(sor_fn)
