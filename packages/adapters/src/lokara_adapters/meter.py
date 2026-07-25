"""Meter port — MDL (Messdienstleister) and other reading sources.

One normalized ``MeterReading`` for all three ingestion paths: manual entry,
MDL exchange (ARGE/bved **HeiWaKo** standard — Techem, ista, …), and radio
self-read (Funk-Selbstabrechner). **The engines never know the source** — the
heating engine receives period consumption computed from these readings by the
caller; a reading itself is always a point-in-time register value.

The vocabulary (kind / unit / reason / source) lives in ``lokara_domain`` so
the persistence layer can store exactly this shape without importing an
adapter: a hand-typed reading and an MDL delivery are the same row downstream.

Device management (Eichfrist tracking) is a guard over the same data: the
meter carries its calibration date, the warning is computed, never stored.

TODO(provider): the real MDL implementation speaks HeiWaKo; only this module
ever parses that format.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Protocol

from lokara_domain import MeasurementUnit, MeterKind, ReadingReason, ReadingSource

__all__ = [
    "MeasurementUnit",
    "MeterConsumption",
    "MeterGateway",
    "MeterKind",
    "MeterReading",
    "ReadingReason",
    "ReadingSource",
    "StubMeterGateway",
    "consumption_by_meter",
]


@dataclass(frozen=True)
class MeterReading:
    """A point-in-time register value of one meter, normalized from any source.

    ``unit_id`` is None for a building-level meter (Hauptzähler): the building's
    Wärmemengenzähler measures the whole system, not one flat.

    ``recorded_at`` is when the value entered the system, not when it was read.
    Readings are append-only, so two rows can share a ``read_at`` — the one
    recorded last wins. That is how a ``CORRECTION`` supersedes a typo without
    anything ever being updated or deleted.
    """

    meter_id: str
    unit_id: str | None
    kind: MeterKind
    measurement_unit: MeasurementUnit
    read_at: date
    value: Decimal
    reason: ReadingReason
    source: ReadingSource
    recorded_at: datetime


class MeterGateway(Protocol):
    """Port: list normalized readings for one building."""

    def list_readings(
        self, building_id: str, window_from: date, window_to: date
    ) -> tuple[MeterReading, ...]:
        """Readings taken in the closed window ``[window_from, window_to]`` —
        a billing period needs both its opening and its closing register value,
        so unlike money windows this one includes the end date."""
        ...


@dataclass(frozen=True)
class MeterConsumption:
    """What one meter consumed over the window: closing minus opening."""

    meter_id: str
    unit_id: str | None
    kind: MeterKind
    measurement_unit: MeasurementUnit
    opening: MeterReading
    closing: MeterReading
    value: Decimal


def consumption_by_meter(
    readings: Iterable[MeterReading],
) -> dict[str, MeterConsumption]:
    """Fold point-in-time register values into per-meter period consumption.

    The same fold for every source — that is the point of the normalized shape:
    hand-typed and MDL-delivered readings become one number the same way.

    Two rules carry the append-only contract:

    - **Supersession.** Several readings may share a ``read_at`` (a correction
      is a new row, never an UPDATE). The one recorded last wins; earlier ones
      stay for the audit trail and are ignored here.
    - **Unusable pairs are dropped, not guessed.** A meter with fewer than two
      dates, or one whose register ran backwards (rollover, device swap),
      yields no entry — the caller then has a *missing* reading, which the
      heating engine answers with the § 9a estimate. Inventing a number here
      would silently mis-bill; § 9a is the lawful answer.
    """
    latest_per_date: dict[str, dict[date, MeterReading]] = {}
    for reading in readings:
        by_date = latest_per_date.setdefault(reading.meter_id, {})
        previous = by_date.get(reading.read_at)
        # >= so the last one in input order wins a recorded_at tie; the DB
        # gateway orders by (recorded_at, id), making that total.
        if previous is None or reading.recorded_at >= previous.recorded_at:
            by_date[reading.read_at] = reading

    consumption: dict[str, MeterConsumption] = {}
    for meter_id, by_date in latest_per_date.items():
        if len(by_date) < 2:
            continue
        opening = by_date[min(by_date)]
        closing = by_date[max(by_date)]
        value = closing.value - opening.value
        if value < 0:
            continue
        consumption[meter_id] = MeterConsumption(
            meter_id=meter_id,
            unit_id=closing.unit_id,
            kind=closing.kind,
            measurement_unit=closing.measurement_unit,
            opening=opening,
            closing=closing,
            value=value,
        )
    return consumption


_STUB_RECORDED_AT = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)

# (meter_id, unit_id, kind, unit, opening, closing) — differences are exactly
# the heating golden fixture: the building meters give 20.000 kWh and 40 m³,
# the flats give heat 600/250/150 HKV units and warm water 20/12/8 m³
# (docs/03, docs/06 Scenario 2).
_SPEC: tuple[tuple[str, str | None, MeterKind, MeasurementUnit, str, str], ...] = (
    ("met_heat_main", None, MeterKind.HEAT, MeasurementUnit.KWH, "148500", "168500"),
    ("met_ww_main", None, MeterKind.WARM_WATER, MeasurementUnit.CUBIC_METRE, "812", "852"),
    ("met_heat_a", "unit_demo_a", MeterKind.HEAT, MeasurementUnit.HKV_UNITS, "1200", "1800"),
    ("met_heat_b", "unit_demo_b", MeterKind.HEAT, MeasurementUnit.HKV_UNITS, "3400", "3650"),
    ("met_heat_c", "unit_demo_c", MeterKind.HEAT, MeasurementUnit.HKV_UNITS, "880", "1030"),
    (
        "met_ww_a",
        "unit_demo_a",
        MeterKind.WARM_WATER,
        MeasurementUnit.CUBIC_METRE,
        "241.5",
        "261.5",
    ),
    (
        "met_ww_b",
        "unit_demo_b",
        MeterKind.WARM_WATER,
        MeasurementUnit.CUBIC_METRE,
        "96.2",
        "108.2",
    ),
    (
        "met_ww_c",
        "unit_demo_c",
        MeterKind.WARM_WATER,
        MeasurementUnit.CUBIC_METRE,
        "55.0",
        "63.0",
    ),
)


def _readings() -> tuple[MeterReading, ...]:
    readings: list[MeterReading] = []
    for meter_id, unit_id, kind, measurement_unit, opening, closing in _SPEC:
        for read_at, value in (
            (date(2025, 1, 1), opening),
            (date(2025, 12, 31), closing),
        ):
            readings.append(
                MeterReading(
                    meter_id=meter_id,
                    unit_id=unit_id,
                    kind=kind,
                    measurement_unit=measurement_unit,
                    read_at=read_at,
                    value=Decimal(value),
                    reason=ReadingReason.PERIODIC,
                    source=ReadingSource.MDL,
                    recorded_at=_STUB_RECORDED_AT,
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
