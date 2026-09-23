"""f3-g: f3-c3'un 30 soru x 2 mod x 8 tohum uretimini Gemma'li Kafa ile (karakter + yorgun talimati, think
ayiklama) tekrarlar; kaldigi yerden devam eder, 90 dk'da "yarim" cikar. Cagiran: araclar/f3g-uretim-baslat.ps1."""

import argparse
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))
sys.path.insert(0, str(KOK / "araclar"))
import f3g_sizinti  # noqa: E402
import sunucu_yonet  # noqa: E402
from ortak.ayar import KAFA_HOST, KAFA_PORT, MOD_YORGUN, MOD_ZORLA_DEGISKENI  # noqa: E402
from ortak.gpu_sicaklik import SicaklikBekcisi, sicakta_dene  # noqa: E402
from yuvalar import hormonlar, kafa  # noqa: E402
from yuvalar.kafa_dusunce import dusunce_ayikla  # noqa: E402


def _yukle(ad, dosya):
    """Tire iceren betik adlari import edilemez; kopyalamak yerine yuklenir."""
    ozellik = importlib.util.spec_from_file_location(ad, KOK / "araclar" / dosya)
    modul = importlib.util.module_from_spec(ozellik)
    ozellik.loader.exec_module(modul)
    return modul


# Sorular, karistirma, anonim yazim ve sizinti taramasi f3-c3'ten; post, think sayimi, Gemma sunucusu k26-d'den.
f3c3 = _yukle("f3c3", "f3c3-kor-uretim.py")
k26d = _yukle("k26d", "k26d-hormon-uzunluk.py")
k26d.SUNUCU_LOG = KOK / "loglar" / "f3g-sunucu.log"

CIKTI_KLASORU = KOK / "reports" / "f3g-kor-olcum"
DUMAN_KLASORU = KOK / "reports" / "f3g-duman"
KAYIT_DOSYASI = "kayitlar.jsonl"
DUMAN_SORU_SAYISI = 2
DUMAN_TOHUMLAR = range(1, 2)
# Ana oturum 90 dk kosu + 15 dk soguma parcalariyla calistirir (k26-d kurali).
GPU_SURE_SINIRI_SN = 90 * 60
MS = 1000
TAMAM, YARIM, SICAK = "tamam", "yarim", "sicak"
# Baslatici durum dosyasina cikis koduna gore yazar.
CIKIS_KODU = {TAMAM: 0, YARIM: 3, SICAK: 4}


def is_listesi(sorular, tohumlar):
    """Tohum > soru > mod sirasi (f3-c3 ile ayni): iki mod ayni isilikta uretilsin."""
    return [(tohum, soru, mod) for tohum in tohumlar for soru in sorular for mod in f3c3.MODLAR]


def anahtar(soru_id, mod, tohum):
    return f"{soru_id}|{mod}|{tohum}"


def bitmisleri_oku(dosya):
    """Daha once tamamlanmis (soru, mod, tohum) anahtarlari. Hata ya da sicak isaretli satir bitmis sayilmaz."""
    if not dosya.exists():
        return set()
    satirlar = [json.loads(s) for s in dosya.read_text(encoding="utf-8").splitlines() if s.strip()]
    return {anahtar(s["soru_id"], s["mod"], s["tohum"]) for s in satirlar
            if "cevap" in s and "hata" not in s and "olcum" not in s}


def govde_hazirla(soru, mod, tohum, hormon):
    """Kafa'nin gercek yolu: hormon -> ayarlar (yorgunda sicaklik x0,7, cevap butcesi x0,5, + think payi),
    karakter + yorgunsa talimat tek sistem mesaji; tek fark sabit seed."""
    os.environ[MOD_ZORLA_DEGISKENI] = mod
    try:
        ayarlar, mod_cikan = kafa._ornekleme_ayarlari(dict(hormon))
    finally:
        os.environ.pop(MOD_ZORLA_DEGISKENI)  # surecte kalirsa Kafa'nin sonraki cagrilarini da zorlar
    karakter, _ = kafa._karakter_oku()
    mesajlar = kafa._sistem_mesaji_ekle([{"role": "user", "content": soru}], karakter, mod_cikan)
    return {**kafa._govde_olustur(mesajlar, ayarlar), "seed": tohum}, ayarlar, mod_cikan


def tek_istek(kok_url, is_, hormon):
    """Bir (tohum, soru, mod): kayit satiri; cevap think ayiklanmis, ham da saklanir."""
    tohum, (soru_id, kategori, soru), mod = is_
    govde, ayarlar, mod_cikan = govde_hazirla(soru, mod, tohum, hormon)
    basladi = time.perf_counter()
    j = k26d.post(f"{kok_url}/v1/chat/completions", govde)
    duvar_sn = time.perf_counter() - basladi
    secim = j["choices"][0]
    ham = secim["message"]["content"]
    return {"soru_id": soru_id, "kategori": kategori, "soru": soru, "mod": mod_cikan, "tohum": tohum,
            "ayarlar": ayarlar, "talimat": mod_cikan == MOD_YORGUN, "bitis": secim.get("finish_reason"),
            "token": j.get("usage", {}).get("completion_tokens"), "think_token": k26d.think_token(kok_url, ham),
            "cevap": dusunce_ayikla(ham), "ham": ham, "is_sn": round(kafa._is_saniyesi(j.get("timings"), duvar_sn), 3),
            "duvar_ms": int(duvar_sn * MS)}


def olc(kok_url, is_, hormon, bekci):
    """Serinle, tek istek; baglanti hatasi (sicak kesme dahil) satira yazilir, bitmis sayilmaz."""
    tohum, (soru_id, _, soru), mod = is_
    satir = {"sicaklik_once": bekci.son_c, "soguma_sn": bekci.serinle()}
    try:
        satir.update(tek_istek(kok_url, is_, hormon))
    except OSError as hata:
        satir.update({"soru_id": soru_id, "soru": soru, "mod": mod, "tohum": tohum, "hata": str(hata)})
    satir["sicaklik_sonra"] = bekci.son_c
    return satir


def uretim_dongusu(kok_url, isler, hormon, bekci, dosya, yeniden_baslat, sure_siniri_sn=GPU_SURE_SINIRI_SN):
    """Bitmemis isleri sirayla kosar; sure dolarsa YARIM, toplam kesme siniri dolarsa SICAK doner."""
    bitmis = bitmisleri_oku(dosya)
    kalan = [i for i in isler if anahtar(i[1][0], i[2], i[0]) not in bitmis]
    print(f"[devam] {len(isler) - len(kalan)}/{len(isler)} bitmis, {len(kalan)} kalan", flush=True)
    sayac, basladi = {"kesme": 0}, time.monotonic()
    for no, is_ in enumerate(kalan, 1):
        if time.monotonic() - basladi > sure_siniri_sn:
            return YARIM
        if not sicakta_dene(lambda: olc(kok_url, is_, hormon, bekci), bekci,
                            lambda satir: _satir_yaz(dosya, satir, no, len(kalan)), yeniden_baslat, sayac):
            return SICAK
    return TAMAM if len(bitmisleri_oku(dosya)) == len(isler) else YARIM


def _satir_yaz(dosya, satir, no, toplam):
    """Kayit tamamlaninca hemen diske (kaldigi yerden devam buna dayanir) ve ekrana kisa ozet."""
    with dosya.open("a", encoding="utf-8") as f:
        f.write(json.dumps(satir, ensure_ascii=False) + "\n")
    print(f"[{no}/{toplam}] t{satir.get('tohum')} {satir.get('soru_id')} {satir.get('mod')}: "
          f"{satir.get('duvar_ms')} ms, think {satir.get('think_token')}, {satir.get('sicaklik_sonra')} C"
          f"{' HATA ' + satir['hata'] if 'hata' in satir else ''}{' ' + satir['olcum'] if 'olcum' in satir else ''}",
          flush=True)


def anonim_yaz(klasor, dosya):
    """Butun isler bitince: son gecerli kayitlardan anonim-cevaplar.md + anahtar.json (f3-c3 bicimi)."""
    satirlar = [json.loads(s) for s in dosya.read_text(encoding="utf-8").splitlines() if s.strip()]
    gecerli = {anahtar(s["soru_id"], s["mod"], s["tohum"]): s for s in satirlar
               if "cevap" in s and "hata" not in s and "olcum" not in s}
    f3c3.CIKTI_KLASORU = klasor
    f3c3.yaz(list(gecerli.values()))
    f3g_sizinti.isaretle(klasor)


def kos(klasor, isler, sunucu_baslat=k26d.gercek_sunucu_baslat, port=KAFA_PORT, okuyucu=None, aralik_sn=None,
        vram=None):
    """Uctan uca: sunucu ac, bitmemisleri uret, kapat, VRAM logla; hepsi bittiyse anonim dosyalari yaz."""
    klasor.mkdir(parents=True, exist_ok=True)
    dosya = klasor / KAYIT_DOSYASI
    vram = vram or sunucu_yonet.gpu_bellek_mib
    sunucu = {"proc": sunucu_baslat()}

    def yeniden_baslat():
        sunucu_yonet.durdur(sunucu["proc"])
        sunucu["proc"] = sunucu_baslat()
        sunucu_yonet.hazir_bekle(sunucu["proc"], port)

    ek = {k: v for k, v in (("okuyucu", okuyucu), ("aralik_sn", aralik_sn)) if v is not None}
    bekci = SicaklikBekcisi(kes=lambda: sunucu_yonet.durdur(sunucu["proc"]), **ek).baslat()
    try:
        sunucu_yonet.hazir_bekle(sunucu["proc"], port)
        sonuc = uretim_dongusu(f"http://{KAFA_HOST}:{port}", isler, hormonlar.Hormonlar().oku(), bekci, dosya,
                               yeniden_baslat)
    finally:
        bekci.bitir()
        sunucu_yonet.durdur(sunucu["proc"])
    print(f"[durum] {sonuc} en_yuksek_c={bekci.en_yuksek_c} vram_sonra_mib={vram()} "
          f"sunucu_kapali={sunucu['proc'].poll() is not None}", flush=True)
    if sonuc == TAMAM:
        anonim_yaz(klasor, dosya)
    return sonuc


def main():
    ayrac = argparse.ArgumentParser(description=__doc__)
    ayrac.add_argument("--duman", action="store_true", help="2 soru x 2 mod x 1 tohum, ayri klasore")
    arg = ayrac.parse_args()
    if arg.duman:
        sonuc = kos(DUMAN_KLASORU, is_listesi(f3c3.SORULAR[:DUMAN_SORU_SAYISI], DUMAN_TOHUMLAR))
    else:
        sonuc = kos(CIKTI_KLASORU, is_listesi(f3c3.SORULAR, f3c3.TOHUMLAR))
    sys.exit(CIKIS_KODU[sonuc])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
