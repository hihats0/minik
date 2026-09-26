"""Butun testlerde log klasorunu gecici klasore yonlendirir; gercek loglar/ kirlenmesin (log-a).
Cagiran: pytest, her testten once otomatik."""

import pytest

from ortak import log


@pytest.fixture(autouse=True)
def gecici_log_klasoru(tmp_path, monkeypatch):
    """ortak.log.LOG_KLASORU'nu testin gecici klasorune cevirir."""
    monkeypatch.setattr(log, "LOG_KLASORU", tmp_path / "loglar")


@pytest.fixture(autouse=True)
def sahte_gomme(monkeypatch):
    """Varsayilan hatirlama gommesi ag acmasin, gercek gomme sunucusu baslatilmasin (hafiza-g)."""
    from sahte_gomme import kelime_torbasi
    from yuvalar import hatirlama
    monkeypatch.setattr(hatirlama, "varsayilan_gomme_al", kelime_torbasi)
