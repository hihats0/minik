"""f6 olcutu: kayitli Kafa cevaplari uzerinde cevrimdisi Kalp oynatir, refleks onerisi ile Kafa'nin
gercek cevabi arasindaki ayrisma oranini sayar. Model cagirmaz (GPU yasak). Cagiran: elle `python deneyler/f6-ayrisma-olc.py`."""

import json
import re
import sys
import tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))

from ortak import log  # noqa: E402
from yuvalar import defter, kalp  # noqa: E402

KAYNAK_MD = [KOK / "reports/f3c-kor-olcum/anonim-cevaplar.md", KOK / "reports/f3c3-kor-olcum/anonim-cevaplar.md"]
KAYNAK_JSON = sorted((KOK / "reports/k23-ham-cevaplar").glob("*.json"))
KAYNAK_JSONL = sorted((KOK / "defter").glob("gunluk-*.jsonl"))
JACCARD_ESIGI = 0.5  # tahmin: kelime kumesi ortakligi bunun altindaysa "kaba ayrisma"
KAYIT_DESENI = re.compile(r"\*\*Soru:\*\*(.*?)\*\*Cevap:\*\*(.*?)(?=\n---|\Z)", re.S)


def md_oku(yol):
    """Kor puanlama dosyasindaki (soru, cevap) ciftleri, dosyadaki (karistirilmis) sirayla."""
    return [(s.strip(), c.strip(), None) for s, c in KAYIT_DESENI.findall(yol.read_text(encoding="utf-8"))]


def json_oku(yol):
    return [(k["soru"], k["cevap"], None) for k in json.loads(yol.read_text(encoding="utf-8"))["sinav"]]


def jsonl_oku(yol):
    satirlar = [json.loads(s) for s in yol.read_text(encoding="utf-8").splitlines() if s.strip()]
    return [(k["soru"], k["cevap"], k.get("dopamin_degisimi")) for k in satirlar]


def jaccard(a, b):
    ka, kb = set(kalp.kalip_cikar(a).split()), set(kalp.kalip_cikar(b).split())
    return len(ka & kb) / len(ka | kb) if ka | kb else 1.0


def oynat(ciftler):
    """Temiz refleks dosyasiyla akisi taklit eder: once refleks_ara, sonra tur_sonu (minik.py sirasi)."""
    sayim = {"tur": 0, "oneri": 0, "tam_ayrisma": 0, "kaba_ayrisma": 0, "dogan": 0}
    for soru, cevap, dopamin in ciftler:
        sayim["tur"] += 1
        oneri, _ = kalp.refleks_ara({"soru": soru})
        if oneri is not None:
            sayim["oneri"] += 1
            sayim["tam_ayrisma"] += kalp.kalip_cikar(oneri["tepki"]) != kalp.kalip_cikar(cevap)
            sayim["kaba_ayrisma"] += jaccard(oneri["tepki"], cevap) < JACCARD_ESIGI
        once = len(json.loads(kalp._dosya().read_text(encoding="utf-8"))["refleksler"]) if kalp._dosya().exists() else 1
        kalp.tur_sonu(soru, cevap, oneri, dopamin)
        sayim["dogan"] += len(json.loads(kalp._dosya().read_text(encoding="utf-8"))["refleksler"]) > once
    return sayim


def kaynaklar():
    for yol in KAYNAK_MD:
        yield yol.relative_to(KOK).as_posix(), md_oku(yol)
    for yol in KAYNAK_JSON:
        yield yol.relative_to(KOK).as_posix(), json_oku(yol)
    for yol in KAYNAK_JSONL:
        yield yol.relative_to(KOK).as_posix(), jsonl_oku(yol)


def main():
    with tempfile.TemporaryDirectory() as gecici:
        defter.DEFTER_KLASORU = Path(gecici) / "defter"
        log.LOG_KLASORU = Path(gecici) / "loglar"  # olcum canli logu kirletmesin
        for ad, ciftler in kaynaklar():
            for dosya in defter.DEFTER_KLASORU.glob("*"):
                dosya.unlink()  # her kaynak kendi temiz refleks dosyasiyla baslar
            s = oynat(ciftler)
            oran = lambda k: f"{s[k]}/{s['oneri']} = {s[k] / s['oneri']:.3f}" if s["oneri"] else "oneri yok"
            print(f"{ad}: tur {s['tur']}, oneri {s['oneri']}, dogan {s['dogan']}, "
                  f"tam ayrisma {oran('tam_ayrisma')}, kaba ayrisma {oran('kaba_ayrisma')}")


if __name__ == "__main__":
    main()
