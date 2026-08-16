"""A2 RED contract — Page 01b device and segmented-reading model.

Source: Page 01b §§ 3.3, 4 H5/H6, E11–E14, E18 and E25; fixtures
F01/F15/F16/F17/F22/F27. Transcription: `docs/03-nk-heating-engines.md`
"A2 executable input/output contract". Rechtsstand 08/2026. K10/K11 remain
`verify-before-production`; no new legal value is introduced here.

Every test resolves the future public symbols at runtime. Collection succeeds
today and the failure is the missing A2 capability, not an import error.
"""

from collections.abc import Callable
from decimal import Decimal
from typing import Any

import lokara_heating_engine
import pytest
from lokara_domain import MeasurementUnit
from lokara_heating_engine import HeatingInputError


def _a2_symbols() -> tuple[type[Any], type[Any], Callable[..., Any]]:
    device = getattr(lokara_heating_engine, "HeatingDevice", None)
    span = getattr(lokara_heating_engine, "DeviceReadingSpan", None)
    aggregate = getattr(lokara_heating_engine, "aggregate_device_reading_spans", None)
    assert isinstance(device, type), "A2 HeatingDevice input model is not implemented"
    assert isinstance(span, type), "A2 DeviceReadingSpan input model is not implemented"
    assert callable(aggregate), "A2 device/segmented-reading aggregation is not implemented"
    return device, span, aggregate


def _device(
    device_type: type[Any],
    device_id: str,
    unit_id: str,
    room: str,
    factor: str,
    measurement_unit: MeasurementUnit = MeasurementUnit.HKV_UNITS,
) -> Any:
    return device_type(
        device_id=device_id,
        unit_id=unit_id,
        room=room,
        measurement_unit=measurement_unit,
        valuation_factor=Decimal(factor),
    )


def _span(
    span_type: type[Any],
    device_id: str,
    allocation_kind: str,
    target_id: str | None,
    opening: str | None,
    closing: str | None,
    previous_period_units: str | None = None,
) -> Any:
    return span_type(
        device_id=device_id,
        allocation_kind=allocation_kind,
        target_id=target_id,
        opening=None if opening is None else Decimal(opening),
        closing=None if closing is None else Decimal(closing),
        previous_period_units=(
            None if previous_period_units is None else Decimal(previous_period_units)
        ),
    )


def test_berkay_01b_f27_aggregates_the_exact_f01_measured_segments() -> None:
    device_type, span_type, aggregate = _a2_symbols()
    devices = (
        _device(device_type, "88-1041", "WE-01", "Wohnzimmer", "1.80"),
        _device(device_type, "88-1042", "WE-01", "Schlafzimmer", "1.25"),
        _device(device_type, "88-1043", "WE-01", "Kinderzimmer", "1.60"),
        _device(device_type, "88-1044", "WE-01", "Bad", "2.00"),
        _device(device_type, "88-2041", "WE-02", "Wohnzimmer", "1.80"),
        _device(device_type, "88-2042", "WE-02", "Schlafzimmer", "1.20"),
        _device(device_type, "88-2043", "WE-02", "Bad", "2.00"),
        _device(device_type, "88-3041", "WE-03", "Wohnzimmer", "1.80"),
        _device(device_type, "88-3042", "WE-03", "Schlafzimmer", "1.25"),
        _device(device_type, "88-3043", "WE-03", "Bad", "2.00"),
    )
    spans = (
        _span(span_type, "88-1041", "PARTY", "Muster", "1240.0", "2110.0"),
        _span(span_type, "88-1042", "PARTY", "Muster", "880.0", "1512.0"),
        _span(span_type, "88-1043", "PARTY", "Muster", "640.0", "1245.0"),
        _span(span_type, "88-1044", "PARTY", "Muster", "302.0", "690.0"),
        _span(span_type, "88-2041", "PARTY", "Schneider", "500.0", "1320.0"),
        _span(span_type, "88-2041", "OWNER", None, "1320.0", "1320.0"),
        _span(span_type, "88-2041", "PARTY", "Weber", "1320.0", "1600.0"),
        _span(span_type, "88-2042", "PARTY", "Schneider", "300.0", "820.0"),
        _span(span_type, "88-2042", "OWNER", None, "820.0", "820.0"),
        _span(span_type, "88-2042", "PARTY", "Weber", "820.0", "1000.0"),
        _span(span_type, "88-2043", "PARTY", "Schneider", "150.0", "360.0"),
        _span(span_type, "88-2043", "OWNER", None, "360.0", "360.0"),
        _span(span_type, "88-2043", "PARTY", "Weber", "360.0", "540.0"),
        _span(span_type, "88-3041", "PARTY", "Beispiel", "0.0", "700.0"),
        _span(span_type, "88-3042", "PARTY", "Beispiel", "0.0", "560.0"),
        _span(span_type, "88-3043", "PARTY", "Beispiel", "0.0", "545.0"),
    )

    result = aggregate(devices=devices, spans=spans)
    assert result.party_units == (
        ("Muster", Decimal("4100.0")),
        ("Schneider", Decimal("2520.0")),
        ("Weber", Decimal("1080.0")),
        ("Beispiel", Decimal("3050.0")),
    )
    assert result.owner_units == Decimal("0.0")
    assert result.unit_units == (
        ("WE-01", Decimal("4100.0")),
        ("WE-02", Decimal("3600.0")),
        ("WE-03", Decimal("3050.0")),
    )
    assert sum((value for _, value in result.party_units), result.owner_units) == Decimal("10750.0")


def test_berkay_01b_f15_keeps_heat_meter_kwh_and_factor_one() -> None:
    device_type, span_type, aggregate = _a2_symbols()
    values = (
        ("Muster", "WE-01", "9000"),
        ("Schneider", "WE-02a", "5250"),
        ("Weber", "WE-02b", "2250"),
        ("Beispiel", "WE-03", "5000"),
    )
    devices = tuple(
        _device(
            device_type,
            f"WMZ-{unit_id}",
            unit_id,
            "Wohnung",
            "1.00",
            MeasurementUnit.KWH,
        )
        for _, unit_id, _ in values
    )
    spans = tuple(
        _span(span_type, f"WMZ-{unit_id}", "PARTY", party, "0", value)
        for party, unit_id, value in values
    )
    result = aggregate(devices=devices, spans=spans)
    assert result.party_units == tuple(
        (party, Decimal(value).quantize(Decimal("0.1"))) for party, _, value in values
    )
    assert {line.measurement_unit for line in result.device_lines} == {MeasurementUnit.KWH}
    assert sum((value for _, value in result.party_units), Decimal(0)) == Decimal("21500.0")


def test_berkay_01b_f16_keeps_an_annual_reading_unsegmented_for_k3() -> None:
    device_type, span_type, aggregate = _a2_symbols()
    result = aggregate(
        devices=(_device(device_type, "HKV-WE02", "WE-02", "Wohnung", "1.00"),),
        spans=(_span(span_type, "HKV-WE02", "ANNUAL_UNSEGMENTED", None, "0.0", "3600.0"),),
    )
    assert result.party_units == ()
    assert result.owner_units == Decimal("0.0")
    assert result.unsegmented_unit_units == (("WE-02", Decimal("3600.0")),)


def test_berkay_01b_f17_uses_and_labels_the_stated_prior_period_estimate() -> None:
    device_type, span_type, aggregate = _a2_symbols()
    devices = (
        _device(device_type, "WE03-measured", "WE-03", "Wohnräume", "1.00"),
        _device(device_type, "WE03-failed", "WE-03", "Ausfallraum", "1.00"),
    )
    spans = (
        _span(span_type, "WE03-measured", "PARTY", "Beispiel", "0.0", "2430.0"),
        _span(
            span_type,
            "WE03-failed",
            "PARTY",
            "Beispiel",
            None,
            None,
            previous_period_units="620.0",
        ),
    )
    result = aggregate(devices=devices, spans=spans)
    assert result.party_units == (("Beispiel", Decimal("3050.0")),)
    assert result.estimated_device_ids == ("WE03-failed",)
    estimated = next(line for line in result.device_lines if line.device_id == "WE03-failed")
    assert estimated.estimated is True
    assert estimated.estimation_basis == "previous_period_units"
    assert estimated.units == Decimal("620.0")
    assert sum((value for _, value in result.party_units), result.owner_units) == Decimal("3050.0")


def test_berkay_01b_f22_rejects_negative_delta_then_sums_replacement_devices() -> None:
    device_type, span_type, aggregate = _a2_symbols()
    bad_device = _device(device_type, "WE01-typed", "WE-01", "Wohnung", "1.00")
    with pytest.raises(HeatingInputError, match=r"negativ|WE01-typed"):
        aggregate(
            devices=(bad_device,),
            spans=(_span(span_type, "WE01-typed", "PARTY", "Muster", "12480.0", "11020.0"),),
        )

    devices = (
        _device(device_type, "WE01-old", "WE-01", "Wohnung", "1.00"),
        _device(device_type, "WE01-new", "WE-01", "Wohnung", "1.00"),
    )
    spans = (
        _span(span_type, "WE01-old", "PARTY", "Muster", "12480.0", "12900.0"),
        _span(span_type, "WE01-new", "PARTY", "Muster", "0.0", "1040.0"),
    )
    result = aggregate(devices=devices, spans=spans)
    assert result.party_units == (("Muster", Decimal("1460.0")),)
    assert tuple(line.units for line in result.device_lines) == (
        Decimal("420.0"),
        Decimal("1040.0"),
    )
    assert sum((value for _, value in result.party_units), result.owner_units) == Decimal("1460.0")
