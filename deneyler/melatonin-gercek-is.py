"""f3-e olcumu: acik bir llama-server'la minik.calistir() uzerinden 10 turluk gercek konusma
yapar, her turda is saniyesini, siddeti, melatonini ve modu basar; sonra olculen ortalama
siddetle kac turda 'yorgun'a gecilecegini gercek Hormonlar ile hesaplar.
Cagiran: elle, sunucu aciksa `.venv\\Scripts\\python.exe deneyler\\melatonin-gercek-is.py`."""

import statistics
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import minik  # noqa: E402
from ortak import kaynak_olc  # noqa: E402
from ortak.ayar import MELATONIN_IS_TAVAN_SN, UST_ESIK  # noqa: E402
from yuvalar import hormonlar, kafa  # noqa: E402

SORULAR = [
    "Merhaba, bugun nasilsin?",
    "Bana kendini kisaca tanitir misin?",
    "Yazilim ogrenmeye yeni basladim, nereden baslamaliyim?",
    "Python'da liste ile sozluk arasindaki farki anlatir misin?",
    "Bir fonksiyon neden 30 satiri gecmemeli sence?",
    "Bugun biraz yorgunum, moral verecek bir sey soyler misin?",
    "Istanbul'da gezilecek uc yer oner.",
    "Bir yapay zeka yorulabilir mi?",
    "Bana kisa bir hikaye anlatir misin?",
    "Tesekkurler, yarin devam edelim.",
]
SIMULASYON_TUR_SINIRI = 1000  # bu kadar turda yorgun olmuyorsa "hic olmaz" sayilir


def konusmayi_kos():
    """10 turu gercek akistan gecirir, tur basina (is_sn, siddet, melatonin, mod) listesi verir."""
    kayitlar = []
    hormon_durumu = hormonlar.Hormonlar()
    sorular = list(SORULAR) + [minik.CIKIS_KELIMESI]

    def olcen_dusun(soru, baglam, hormon_degerleri):
        cevap, is_sn = kafa.dusun(soru, baglam, hormon_degerleri)
        kayitlar.append({"is_sn": is_sn, "siddet": kaynak_olc.siddet(is_sn, MELATONIN_IS_TAVAN_SN),
                         "mod": kafa.ONCEKI_MOD, "cevap_karakter": len(cevap)})
        return cevap, is_sn

    def sessiz_soyle(metin, dis_id):
        kayitlar[-1]["melatonin"] = hormon_durumu.oku()["melatonin"] if kayitlar else None

    minik.calistir(dinle=lambda: sorular.pop(0), soyle=sessiz_soyle, dusun=olcen_dusun,
                   hormon_durumu=hormon_durumu)
    return kayitlar


def yorgunluga_kac_tur(siddetler):
    """Olculen siddet dizisi basa sararak tekrarlanirsa (ayni konusma surup giderse) melatoninin
    UST_ESIK'e kac turda ulastigini gercek Hormonlar ile sayar. Ulasmiyorsa None."""
    durum = hormonlar.Hormonlar()
    for tur in range(1, SIMULASYON_TUR_SINIRI + 1):
        siddet = siddetler[(tur - 1) % len(siddetler)]
        if durum.guncelle("calisma", siddet)["melatonin"] >= UST_ESIK:
            return tur
    return None


def main():
    with tempfile.TemporaryDirectory() as gecici:
        minik.defter.DEFTER_KLASORU = Path(gecici)  # olcum Minik'in gercek defterini kirletmesin
        kayitlar = konusmayi_kos()
    print(f"tavan {MELATONIN_IS_TAVAN_SN} sn, UST_ESIK {UST_ESIK}")
    print(f"{'tur':>3} {'is_sn':>7} {'siddet':>7} {'melatonin':>10} {'mod':>7} {'karakter':>9}")
    for i, k in enumerate(kayitlar, 1):
        print(f"{i:>3} {k['is_sn']:>7.2f} {k['siddet']:>7.3f} {k['melatonin']:>10.2f} "
              f"{k['mod']:>7} {k['cevap_karakter']:>9}")
    is_saniyeleri = [k["is_sn"] for k in kayitlar]
    siddetler = [k["siddet"] for k in kayitlar]
    print(f"is_sn ortalama {statistics.mean(is_saniyeleri):.2f}, medyan "
          f"{statistics.median(is_saniyeleri):.2f}, en az {min(is_saniyeleri):.2f}, "
          f"en cok {max(is_saniyeleri):.2f}")
    print(f"ortalama siddet {statistics.mean(siddetler):.3f}; bu konusma surerse yorgun'a "
          f"{yorgunluga_kac_tur(siddetler)}. turda gecer; her tur siddet 1,0 olsa (en hizli) "
          f"{yorgunluga_kac_tur([1.0])}. turda")


if __name__ == "__main__":
    main()
