"""Meter port — MDL (Messdienstleister) and other reading sources.

One normalized ``MeterReading`` for all three ingestion paths: manual entry,
MDL exchange (ARGE/bved **HeiWaKo** standard — Techem, ista, …), and radio
self-read (Funk-Selbstabrechner). **The engines never know the source** — the
heating engine receives period consumption computed from these readings by the
caller; a reading itself is always a point-in-time register value.

Device management (Eichfrist tracking) is a guard over the same data, later.

TODO(provider): the real MDL implementation speaks HeiWaKo; only this module
ever parses that format.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Protocol


class MeterKind(StrEnum):
    HEAT = "HEAT"  # heat-cost allocator / heat meter units
    WARM_WATER = "WARM_WATER"  # m³
    COLD_WATER = "COLD_WATER"  # m³


class ReadingSource(StrEnum):
    MANUAL = "MANUAL"
    MDL = "MDL"
    RADIO = "RADIO"


@dataclass(frozen=True)
class MeterReading:
    """A point-in-time register value of one meter, normalized from any source."""

    meter_id: str
    unit_id: str
    kind: MeterKind
    read_at: date
    value: Decimal
    source: ReadingSource


class MeterGateway(Protocol):
    """Port: list normalized readings for one building."""

    def list_readings(
        self, building_id: str, window_from: date, window_to: date
    ) -> tuple[MeterReading, ...]:
        """Readings taken in the closed window ``[window_from, window_to]`` —
        a billing period needs both its opening and its closing register value,
        so unlike money windows this one includes the end date."""
        ...


def _readings() -> tuple[MeterReading, ...]:
    # Start/end register pairs whose differences are exactly the heating golden
    # fixture: heat 600/250/150 units, warm water 20/12/8 m³ (docs/03).
    spec: tuple[tuple[str, str, MeterKind, Decimal, Decimal], ...] = (
        ("met_heat_a", "unit_demo_a", MeterKind.HEAT, Decimal(1200), Decimal(1800)),
        ("met_heat_b", "unit_demo_b", MeterKind.HEAT, Decimal(3400), Decimal(3650)),
        ("met_heat_c", "unit_demo_c", MeterKind.HEAT, Decimal(880), Decimal(1030)),
        ("met_ww_a", "unit_demo_a", MeterKind.WARM_WATER, Decimal("241.5"), Decimal("261.5")),
        ("met_ww_b", "unit_demo_b", MeterKind.WARM_WATER, Decimal("96.2"), Decimal("108.2")),
        ("met_ww_c", "unit_demo_c", MeterKind.WARM_WATER, Decimal("55.0"), Decimal("63.0")),
    )
    readings: list[MeterReading] = []
    for meter_id, unit_id, kind, opening, closing in spec:
        readings.append(
            MeterReading(
                meter_id=meter_id,
                unit_id=unit_id,
                kind=kind,
                read_at=date(2025, 1, 1),
                value=opening,
                source=ReadingSource.MDL,
            )
        )
        readings.append(
            MeterReading(
                meter_id=meter_id,
                unit_id=unit_id,
                kind=kind,
                read_at=date(2025, 12, 31),
                value=closing,
                source=ReadingSource.MDL,
            )
        )
    return tuple(readings)


_FIXTURE_READINGS = _readings()


class StubMeterGateway:
    """Fixture stub: serves the demo building's 2025 register values.

    TODO(provider): HeiWaKo-speaking MDL adapter.
    """

    def list_readings(
        self, building_id: str, window_from: date, window_to: date
    ) -> tuple[MeterReading, ...]:
        del building_id  # the stub serves one fixture building
        return tuple(r for r in _FIXTURE_READINGS if window_from <= r.read_at <= window_to)
