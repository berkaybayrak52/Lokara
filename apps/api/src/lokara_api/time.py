"""Application calendar helpers."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

_BERLIN = ZoneInfo("Europe/Berlin")


def berlin_today(now: datetime | None = None) -> date:
    """Return the calendar date in the legal/application timezone."""
    instant = datetime.now(UTC) if now is None else now
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=UTC)
    return instant.astimezone(_BERLIN).date()
