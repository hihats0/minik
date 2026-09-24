"""Butun testlerde log klasorunu gecici klasore yonlendirir; gercek loglar/ kirlenmesin (log-a).
Cagiran: pytest, her testten once otomatik."""

import pytest

from ortak import log


@pytest.fixture(autouse=True)
def gecici_log_klasoru(tmp_path, monkeypatch):
    """ortak.log.LOG_KLASORU'nu testin gecici klasorune cevirir."""
    monkeypatch.setattr(log, "LOG_KLASORU", tmp_path / "loglar")
