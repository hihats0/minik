"""Sabah demosu testi: --sahte --az tam kosu alt surecte (GPU'suz, gercek defter/'e yazmadan) ve ayar env ezmesi.
Cagiran: pytest."""

import json
import os
import subprocess
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
DEMO = KOK / "araclar" / "sabah_demo.py"
GERCEK_DEFTER = KOK / "defter"
DEMO_IZI = "En sevdiğim çiçek neydi?"  # yalniz demonun gonderdigi soru
KOSU_ZAMAN_ASIMI_SN = 50


def _iz_sayisi():
    """Gercek defter/ jsonl'lerinde demo sorusunun kac kez gectigi (canli web sohbet yazsa da bozulmaz)."""
    return sum(yol.read_text(encoding="utf-8").count(DEMO_IZI) for yol in GERCEK_DEFTER.glob("gunluk-*.jsonl"))


def test_sahte_tam_kosu_cikti_ve_sonuc(tmp_path):
    once = _iz_sayisi()
    subprocess.run([sys.executable, str(DEMO), "--sahte", "--az", "--cikti", str(tmp_path)],
                   check=True, capture_output=True, timeout=KOSU_ZAMAN_ASIMI_SN)
    jsonlar, mdler = list(tmp_path.glob("sabah-demo-*.json")), list(tmp_path.glob("sabah-demo-*.md"))
    assert len(jsonlar) == 1 and len(mdler) == 1
    sonuc = json.loads(jsonlar[0].read_text(encoding="utf-8"))
    assert sonuc["hatirlama"]["sonra"] > sonuc["hatirlama"]["once"]
    assert sonuc["uctan"]["ilk"]["hatirladi"] and sonuc["uctan"]["yeniden_baslatma"]["hatirladi"]
    assert all(tur["uydurma"] is None and tur["giden"] for tur in sonuc["oturum"]["turlar"])
    assert sonuc["kapanis"]["kafa_8081_kapali"]
    assert _iz_sayisi() == once


def test_env_defter_ve_kafa_portunu_ezer(tmp_path):
    env = {**os.environ, "MINIK_DEFTER_KLASORU": str(tmp_path), "MINIK_KAFA_PORT": "8081"}
    cikti = subprocess.run([sys.executable, "-c", "from ortak import ayar; print(ayar.DEFTER_KLASORU); "
                            "print(ayar.KAFA_PORT); print(ayar.KAFA_UC)"],
                           cwd=KOK, env=env, capture_output=True, text=True, check=True).stdout.splitlines()
    assert cikti == [str(tmp_path), "8081", "http://127.0.0.1:8081/v1/chat/completions"]


def test_env_yoksa_varsayilanlar():
    from ortak import ayar
    if "MINIK_DEFTER_KLASORU" not in os.environ:
        assert ayar.DEFTER_KLASORU == GERCEK_DEFTER
    if "MINIK_KAFA_PORT" not in os.environ:
        assert ayar.KAFA_PORT == 8080
