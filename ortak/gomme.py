"""Gomme sunucusuna (llama-server --embedding) tek cumle gonderip vektor alan ortak istemci.
Cagiran: yuvalar/uyku.py (gece), deneyler/ (olcumler)."""

import json
import time
import urllib.request

ISTEK_ZAMAN_ASIMI_SN = 30


def vektor_al(url, metin):
    """Tek metni gomme ucuna gonderir, (vektor, sure_ms) dondurur."""
    govde = json.dumps({"input": metin}, ensure_ascii=False).encode("utf-8")
    istek = urllib.request.Request(
        url, data=govde, headers={"Content-Type": "application/json; charset=utf-8"}
    )
    basla = time.perf_counter()
    with urllib.request.urlopen(istek, timeout=ISTEK_ZAMAN_ASIMI_SN) as yanit:
        yanit_json = json.loads(yanit.read().decode("utf-8"))
    sure_ms = (time.perf_counter() - basla) * 1000
    return yanit_json["data"][0]["embedding"], sure_ms
