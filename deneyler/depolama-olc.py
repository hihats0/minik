"""Sqlite'ta tutulan vektorler icin kaba kuvvet kosinus aramanin maliyetini olcer:
1.000 / 10.000 / 100.000 anida arama suresi (ms) ve surecin RAM'ini yazar.
Cagiran: elle, `python deneyler/depolama-olc.py`.

Not: vektorler sentetik (rastgele), cunku amac icerik degil arama algoritmasinin
boyut ve adede gore maliyetini olcmek; kosinus hesabinin suresi vektorun sayisal
degerine degil boyutuna ve adedine baglidir.
"""

import ctypes
import json
import math
import random
import sqlite3
import struct
import sys
import time

VEKTOR_BOYUTU = 384  # kucuk gomme modeli adayinin (e5-small) vektor boyutu
DENEME_ADETLERI = (1000, 10000, 100000)
RASTGELE_TOHUM = 42
EN_YAKIN_K = 3


def rastgele_vektor(rng):
    """Belirli boyutta rastgele float listesi uretir."""
    return [rng.uniform(-1, 1) for _ in range(VEKTOR_BOYUTU)]


def vektoru_paketle(vektor):
    """Float listesini sqlite BLOB'a yazilacak bayt dizisine cevirir (stdlib struct)."""
    return struct.pack(f"{len(vektor)}f", *vektor)


def vektoru_ac(blob):
    """BLOB'u float listesine geri cevirir."""
    return struct.unpack(f"{len(blob) // 4}f", blob)


def veritabani_doldur(baglanti, adet, rng):
    """Sqlite'a adet kadar rastgele vektor yazar (bellek ici veritabani)."""
    baglanti.execute("CREATE TABLE ani (id INTEGER PRIMARY KEY, vektor BLOB)")
    satirlar = ((i, vektoru_paketle(rastgele_vektor(rng))) for i in range(adet))
    baglanti.executemany("INSERT INTO ani VALUES (?, ?)", satirlar)
    baglanti.commit()


def kosinus(a, b):
    """Iki vektorun kosinus benzerligi, stdlib math ile."""
    ic_carpim = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return ic_carpim / (norm_a * norm_b) if norm_a and norm_b else 0.0


def kaba_kuvvet_ara(baglanti, sorgu_vektoru):
    """Tum tabloyu okuyup kosinus hesaplar, en yakin K taneyi ve sureyi (ms) dondurur."""
    basla = time.perf_counter()
    satirlar = baglanti.execute("SELECT id, vektor FROM ani").fetchall()
    benzerlikler = [(rid, kosinus(sorgu_vektoru, vektoru_ac(blob))) for rid, blob in satirlar]
    benzerlikler.sort(key=lambda x: x[1], reverse=True)
    sure_ms = (time.perf_counter() - basla) * 1000
    return benzerlikler[:EN_YAKIN_K], sure_ms


class _BellekSayaclari(ctypes.Structure):
    """Windows PROCESS_MEMORY_COUNTERS yapisi. GetProcessMemoryInfo boyut kontrolu
    yaptigi icin tum alanlar eksiksiz olmali, yoksa WinError 122 (alan cok kucuk) doner."""

    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]


def ram_zirve_kb():
    """Bu surecin (Python) o ana kadarki RAM zirvesini KB olarak dondurur (Windows API)."""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    psapi.GetProcessMemoryInfo.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(_BellekSayaclari), ctypes.c_ulong
    ]
    sayac = _BellekSayaclari()
    sayac.cb = ctypes.sizeof(_BellekSayaclari)
    tutamak = kernel32.GetCurrentProcess()
    basarili = psapi.GetProcessMemoryInfo(tutamak, ctypes.byref(sayac), sayac.cb)
    if not basarili:
        raise OSError(ctypes.get_last_error(), "GetProcessMemoryInfo basarisiz")
    return sayac.PeakWorkingSetSize // 1024


def olc(adet, rng):
    """Adet kadar vektorla veritabani kurar, arama suresini ve RAM zirvesini olcer."""
    baglanti = sqlite3.connect(":memory:")
    veritabani_doldur(baglanti, adet, rng)
    sorgu_vektoru = rastgele_vektor(rng)
    _, sure_ms = kaba_kuvvet_ara(baglanti, sorgu_vektoru)
    ram_mb = ram_zirve_kb() / 1024
    baglanti.close()
    return {"adet": adet, "arama_ms": round(sure_ms, 2), "ram_zirve_mb": round(ram_mb, 1)}


def main():
    rng = random.Random(RASTGELE_TOHUM)
    sonuclar = [olc(adet, rng) for adet in DENEME_ADETLERI]
    print(json.dumps(sonuclar, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
