"""Pure H5 aggregation for heating devices and reading segments."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from lokara_domain import MeasurementUnit

from .inputs import HeatingInputError

AllocationKind = Literal["PARTY", "OWNER", "ANNUAL_UNSEGMENTED"]
_ONE_DECIMAL = Decimal("0.1")


@dataclass(frozen=True)
class HeatingDevice:
    device_id: str
    unit_id: str
    room: str
    measurement_unit: MeasurementUnit
    valuation_factor: Decimal


@dataclass(frozen=True)
class DeviceReadingSpan:
    device_id: str
    allocation_kind: AllocationKind
    target_id: str | None
    opening: Decimal | None
    closing: Decimal | None
    previous_period_units: Decimal | None = None


@dataclass(frozen=True)
class DeviceReadingLine:
    device_id: str
    unit_id: str
    room: str
    measurement_unit: MeasurementUnit
    valuation_factor: Decimal
    allocation_kind: AllocationKind
    target_id: str | None
    opening: Decimal | None
    closing: Decimal | None
    previous_period_units: Decimal | None
    units: Decimal
    estimated: bool
    estimation_basis: str | None


@dataclass(frozen=True)
class DeviceReadingAggregation:
    device_lines: tuple[DeviceReadingLine, ...]
    party_units: tuple[tuple[str, Decimal], ...]
    owner_units: Decimal
    unit_units: tuple[tuple[str, Decimal], ...]
    unsegmented_unit_units: tuple[tuple[str, Decimal], ...]
    estimated_device_ids: tuple[str, ...]


def _require_finite_non_negative(value: Decimal, *, field: str, device_id: str) -> None:
    if not value.is_finite() or value < 0:
        raise HeatingInputError(
            f"Gerät {device_id}: {field} muss eine endliche, nicht negative Zahl sein"
        )


def _validate_device(device: HeatingDevice) -> None:
    if not device.device_id or not device.unit_id or not device.room:
        raise HeatingInputError("Gerätenummer, Wohnung und Raum müssen angegeben sein")
    if not isinstance(device.measurement_unit, MeasurementUnit):
        raise HeatingInputError(f"Gerät {device.device_id}: ungültige Maßeinheit")
    if not device.valuation_factor.is_finite() or device.valuation_factor <= 0:
        raise HeatingInputError(
            f"Gerät {device.device_id}: Bewertungsfaktor muss endlich und größer als null sein"
        )


def _span_units(span: DeviceReadingSpan, device: HeatingDevice) -> tuple[Decimal, bool]:
    has_opening = span.opening is not None
    has_closing = span.closing is not None
    if has_opening != has_closing:
        raise HeatingInputError(
            f"Gerät {span.device_id}: Anfangs- und Endwert müssen gemeinsam angegeben sein"
        )
    if has_opening:
        if span.previous_period_units is not None:
            raise HeatingInputError(
                f"Gerät {span.device_id}: Messwerte und Vorjahresschätzung dürfen nicht "
                "gleichzeitig angegeben sein"
            )
        assert span.opening is not None and span.closing is not None
        _require_finite_non_negative(span.opening, field="Anfangswert", device_id=span.device_id)
        _require_finite_non_negative(span.closing, field="Endwert", device_id=span.device_id)
        delta = span.closing - span.opening
        if delta < 0:
            raise HeatingInputError(
                f"Gerät {span.device_id}: negativer Verbrauch aus Endwert minus Anfangswert"
            )
        return (
            (delta * device.valuation_factor).quantize(_ONE_DECIMAL, rounding=ROUND_HALF_UP),
            False,
        )
    if span.previous_period_units is None:
        raise HeatingInputError(
            f"Gerät {span.device_id}: Messwerte oder Vorjahreseinheiten müssen angegeben sein"
        )
    _require_finite_non_negative(
        span.previous_period_units,
        field="Vorjahreseinheiten",
        device_id=span.device_id,
    )
    return span.previous_period_units.quantize(_ONE_DECIMAL, rounding=ROUND_HALF_UP), True


def _add_total(totals: dict[str, Decimal], key: str, units: Decimal) -> None:
    totals[key] = totals.get(key, Decimal("0.0")) + units


def aggregate_device_reading_spans(
    *, devices: tuple[HeatingDevice, ...], spans: tuple[DeviceReadingSpan, ...]
) -> DeviceReadingAggregation:
    """Apply H5/R7 and aggregate the rounded span values in input order."""
    devices_by_id: dict[str, HeatingDevice] = {}
    for device in devices:
        _validate_device(device)
        if device.device_id in devices_by_id:
            raise HeatingInputError(f"Gerätenummer {device.device_id} ist doppelt vorhanden")
        devices_by_id[device.device_id] = device

    party_units: dict[str, Decimal] = {}
    unit_units: dict[str, Decimal] = {}
    unsegmented_units: dict[str, Decimal] = {}
    owner_units = Decimal("0.0")
    lines: list[DeviceReadingLine] = []
    estimated_ids: list[str] = []

    for span in spans:
        resolved_device = devices_by_id.get(span.device_id)
        if resolved_device is None:
            raise HeatingInputError(f"Unbekanntes Gerät {span.device_id}")
        if span.allocation_kind not in ("PARTY", "OWNER", "ANNUAL_UNSEGMENTED"):
            raise HeatingInputError(
                f"Gerät {span.device_id}: ungültige Zuordnungsart {span.allocation_kind}"
            )
        if span.allocation_kind == "PARTY" and not span.target_id:
            raise HeatingInputError(f"Gerät {span.device_id}: Mietverhältnis fehlt")
        if span.allocation_kind != "PARTY" and span.target_id is not None:
            raise HeatingInputError(
                f"Gerät {span.device_id}: Ziel ist nur für ein Mietverhältnis zulässig"
            )

        units, estimated = _span_units(span, resolved_device)
        lines.append(
            DeviceReadingLine(
                device_id=resolved_device.device_id,
                unit_id=resolved_device.unit_id,
                room=resolved_device.room,
                measurement_unit=resolved_device.measurement_unit,
                valuation_factor=resolved_device.valuation_factor,
                allocation_kind=span.allocation_kind,
                target_id=span.target_id,
                opening=span.opening,
                closing=span.closing,
                previous_period_units=span.previous_period_units,
                units=units,
                estimated=estimated,
                estimation_basis="previous_period_units" if estimated else None,
            )
        )
        if estimated and resolved_device.device_id not in estimated_ids:
            estimated_ids.append(resolved_device.device_id)

        if span.allocation_kind == "PARTY":
            assert span.target_id is not None
            _add_total(party_units, span.target_id, units)
            _add_total(unit_units, resolved_device.unit_id, units)
        elif span.allocation_kind == "OWNER":
            owner_units += units
            _add_total(unit_units, resolved_device.unit_id, units)
        else:
            _add_total(unsegmented_units, resolved_device.unit_id, units)

    return DeviceReadingAggregation(
        device_lines=tuple(lines),
        party_units=tuple(party_units.items()),
        owner_units=owner_units,
        unit_units=tuple(unit_units.items()),
        unsegmented_unit_units=tuple(unsegmented_units.items()),
        estimated_device_ids=tuple(estimated_ids),
    )
