"""conftest'teki log yonlendirmesinin calistigini kontrol eder.
Cagiran: pytest."""

from ortak import log

GERCEK_KLASOR_ADI = "loglar"


def test_log_gercek_klasore_yazmaz(tmp_path):
    log.yaz("test", "deneme", 0, "ok", {})
    assert log.LOG_KLASORU.is_relative_to(tmp_path)
    assert any(log.LOG_KLASORU.glob("*.log"))
