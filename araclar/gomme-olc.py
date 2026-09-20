"""Calisan bir llama-server gomme ucuna ayni cumleyi N kez gonderip gecikmeyi ve
surecin RAM zirvesini olcer. Cagiran: elle, `python araclar/gomme-olc.py <url> <exe-adi> [tekrar]`.

Not: Bu betik sunucuyu baslatmaz, zaten calisan bir llama-server --embedding
sunucusuna baglanir. Bunun nedeni, model yuklemenin bir kereye mahsus maliyetini
(disk okuma, ilk init) tekrarlanan gomme cagrisinin hizindan ayri tutmak.
"""

import json
import subprocess
import sys

from gomme_istemci import vektor_al

VARSAYILAN_TEKRAR = 20
TEST_CUMLESI = "Bugun hava cok guzeldi, parkta uzun bir yuruyus yaptim."


def tasklist_ram_kb(exe_adi):
    """Verilen exe adinin RAM (Mem Usage) degerini KB olarak dondurur, tasklist ile."""
    cikti = subprocess.check_output(
        ["tasklist", "/FI", f"IMAGENAME eq {exe_adi}", "/FO", "CSV", "/NH"],
        text=True,
    )
    ilk_satir = cikti.strip().splitlines()[0]
    alanlar = [a.strip('"') for a in ilk_satir.split('","')]
    mem_metni = alanlar[-1].replace(" K", "").replace(".", "")
    return int(mem_metni)


def gomme_iste(url, cumle):
    """Tek cumleyi gomme ucuna gonderir, (vektor_boyutu, sure_ms) dondurur."""
    vektor, sure_ms = vektor_al(url, cumle)
    return len(vektor), sure_ms


def olc(url, exe_adi, tekrar):
    """N tekrar gomme cagrisi yapar, gecikme listesini ve RAM zirvesini toplar."""
    sureler = []
    boyut = None
    ram_zirve_kb = 0
    for _ in range(tekrar):
        boyut, sure_ms = gomme_iste(url, TEST_CUMLESI)
        sureler.append(sure_ms)
        ram_zirve_kb = max(ram_zirve_kb, tasklist_ram_kb(exe_adi))
    sureler.sort()
    orta = sureler[len(sureler) // 2]
    return {
        "vektor_boyutu": boyut,
        "tekrar": tekrar,
        "medyan_ms": round(orta, 2),
        "en_hizli_ms": round(sureler[0], 2),
        "en_yavas_ms": round(sureler[-1], 2),
        "ram_zirve_mb": round(ram_zirve_kb / 1024, 1),
    }


def main():
    if len(sys.argv) < 3:
        print("kullanim: python gomme-olc.py <url> <exe-adi> [tekrar]", file=sys.stderr)
        sys.exit(1)
    url = sys.argv[1]
    exe_adi = sys.argv[2]
    tekrar = int(sys.argv[3]) if len(sys.argv) > 3 else VARSAYILAN_TEKRAR
    sonuc = olc(url, exe_adi, tekrar)
    print(json.dumps(sonuc, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
