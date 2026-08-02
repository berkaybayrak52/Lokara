"""Destatis port — official price indices (VPI) for index-linked rents.

An Indexmiete adjustment (M8) is computed from the Verbraucherpreisindex as
published by Destatis; the index month and base year are part of the legal
justification letter, so values are normalized with both. Like every legal
input, an index value is data with a source — never hardcoded.

TODO(provider): the real implementation reads the **Destatis GENESIS API**
(series 61111-0002, VPI base 2020 = 100); only this module knows that API.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class PriceIndexValue:
    """One published monthly index value. ``month`` is normalized to the first
    of the month; ``base_year`` names the =100 reference the value is on."""

    series_code: str
    month: date
    value: Decimal
    base_year: int


class PriceIndexGateway(Protocol):
    """Port: published index values of one series, oldest first."""

    def list_index_values(
        self, series_code: str, month_from: date, month_to: date
    ) -> tuple[PriceIndexValue, ...]:
        """Values for months in the half-open window ``[month_from, month_to)``."""
        ...


VPI_SERIES_CODE = "61111-0002"

# Plausible fixture values (base 2020 = 100) — for dev/tests/demo only; the
# real numbers come from GENESIS at M8 and are never shipped as constants.
_FIXTURE_VALUES: tuple[PriceIndexValue, ...] = tuple(
    PriceIndexValue(series_code=VPI_SERIES_CODE, month=month, value=value, base_year=2020)
    for month, value in (
        (date(2024, 10, 1), Decimal("119.3")),
        (date(2024, 11, 1), Decimal("119.1")),
        (date(2024, 12, 1), Decimal("119.6")),
        (date(2025, 1, 1), Decimal("119.4")),
        (date(2025, 2, 1), Decimal("119.9")),
        (date(2025, 3, 1), Decimal("120.2")),
    )
)


class StubPriceIndexGateway:
    """Fixture stub. TODO(provider): GENESIS-backed adapter at M8."""

    def list_index_values(
        self, series_code: str, month_from: date, month_to: date
    ) -> tuple[PriceIndexValue, ...]:
        return tuple(
            v
            for v in _FIXTURE_VALUES
            if v.series_code == series_code and month_from <= v.month < month_to
        )
