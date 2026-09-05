from datetime import UTC, datetime

from lokara_api.time import berlin_today


def test_berlin_today_uses_berlin_calendar_at_utc_midnight_boundary() -> None:
    instant = datetime(2026, 8, 30, 22, 30, tzinfo=UTC)
    assert berlin_today(instant).isoformat() == "2026-08-31"
