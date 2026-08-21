"""Zähler (docs/04 M3 page 5) — meters, readings, and the heating invoice.

Two rules shape this router:

1. **Readings are create-only.** There is no PUT and no PATCH here by design: a
   wrong value is fixed by POSTing a new reading for the same date with
   ``reason = CORRECTION``, and the later one supersedes the earlier for
   billing while both stay visible. That is what lets a statement be
   re-derived years later exactly as it was billed (GoBD / § 147 AO).
2. **The Eichfrist is computed, never stored.** A meter carries its
   ``calibration_valid_until`` date; whether that has run out is derived on
   read — one guard pattern, no denormalized flag to drift (CLAUDE.md).
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException
from lokara_adapters import consumption_by_meter
from lokara_db import Building, HeatingCostEntry, Meter, MeterReading, Tenancy, Unit, new_id
from lokara_domain import MeasurementUnit, MeterKind, cents, format_eur
from lokara_pdf import format_number_de
from sqlalchemy import select

from ..deps import PathAccountSession
from ..meter_gateway import VALUE_SCALE, DbMeterGateway
from ..schemas import (
    HeatingCostCreate,
    HeatingCostListResponse,
    HeatingCostOut,
    MeterCreate,
    MeterListResponse,
    MeterOut,
    MeterReadingCreate,
    MeterReadingOut,
)
from ..statement_service import BILLING_END, BILLING_START, PERIOD_LABEL

router = APIRouter(prefix="/a/{account_id}")

KIND_LABELS: dict[MeterKind, str] = {
    MeterKind.HEAT: "Wärme",
    MeterKind.WARM_WATER: "Warmwasser",
    MeterKind.COLD_WATER: "Kaltwasser",
}

UNIT_SYMBOLS: dict[MeasurementUnit, str] = {
    MeasurementUnit.KWH: "kWh",
    MeasurementUnit.CUBIC_METRE: "m³",
    MeasurementUnit.HKV_UNITS: "Einheiten",
}

# An Eichfrist inside this window is a "renew it now" warning, not yet a defect.
EXPIRY_WARNING_DAYS = 90


CalibrationStatus = Literal["EXPIRED", "EXPIRING_SOON", "VALID", "NOT_APPLICABLE"]


def _calibration_status(valid_until: date | None, today: date) -> CalibrationStatus:
    # NULL means "not eichpflichtig" (Heizkostenverteiler), not "unknown" — so
    # it is a neutral state, never a warning.
    if valid_until is None:
        return "NOT_APPLICABLE"
    if valid_until < today:
        return "EXPIRED"
    if valid_until <= today + timedelta(days=EXPIRY_WARNING_DAYS):
        return "EXPIRING_SOON"
    return "VALID"


def _scaled(value_x1000: int) -> Decimal:
    return Decimal(value_x1000) / VALUE_SCALE


def _building_or_404(session: PathAccountSession, building_id: str) -> Building:
    building = session.get(Building, building_id)
    if building is None:  # unknown OR invisible under RLS — same answer
        raise HTTPException(status_code=404, detail="Building not found")
    return building


def _meter_out(meter: Meter, consumption_display: str | None, today: date) -> MeterOut:
    # Newest first; within a date the later-recorded row is the effective one,
    # so everything before it in that date is marked superseded.
    readings = sorted(meter.readings, key=lambda r: (r.read_at, r.recorded_at, r.id))
    effective_per_date: dict[date, str] = {}
    for reading in readings:
        effective_per_date[reading.read_at] = reading.id
    return MeterOut(
        id=meter.id,
        unit_id=meter.unit_id,
        unit_label=meter.unit.label if meter.unit is not None else None,
        kind=meter.kind,
        kind_label=KIND_LABELS[meter.kind],
        measurement_unit=meter.measurement_unit,
        unit_symbol=UNIT_SYMBOLS[meter.measurement_unit],
        serial=meter.serial,
        label=meter.label,
        calibration_valid_until=meter.calibration_valid_until,
        valuation_factor_x1000=meter.valuation_factor_x1000,
        valuation_factor_display=(
            format_number_de(_scaled(meter.valuation_factor_x1000))
            if meter.valuation_factor_x1000 is not None
            else None
        ),
        calibration_status=_calibration_status(meter.calibration_valid_until, today),
        readings=[
            MeterReadingOut(
                id=r.id,
                read_at=r.read_at,
                value_x1000=r.value_x1000,
                value_display=format_number_de(_scaled(r.value_x1000)),
                reason=r.reason,
                source=r.source,
                note=r.note,
                tenancy_id=r.tenancy_id,
                estimated_consumption_x1000=r.estimated_consumption_x1000,
                estimation_basis=r.estimation_basis,
                provenance_ref=r.provenance_ref,
                recorded_at=r.recorded_at,
                superseded=effective_per_date[r.read_at] != r.id,
            )
            for r in reversed(readings)
        ],
        period_consumption_display=consumption_display,
    )


@router.get("/buildings/{building_id}/meters")
def list_meters(
    account_id: str, building_id: str, session: PathAccountSession
) -> MeterListResponse:
    del account_id  # scoping happened in the dependency
    _building_or_404(session, building_id)
    meters = session.scalars(
        select(Meter)
        .where(Meter.building_id == building_id)
        # Building-level meters first (they drive the whole statement), then by
        # unit and medium so the table reads like the installation.
        .order_by(Meter.unit_id.is_not(None), Meter.unit_id, Meter.kind, Meter.serial)
    ).all()

    # Exactly the fold the statement uses — the page can never disagree with
    # the Abrechnung about what a meter consumed.
    consumption = consumption_by_meter(
        DbMeterGateway(session).list_readings(
            building_id, BILLING_START, BILLING_END - timedelta(days=1)
        )
    )
    today = date.today()
    return MeterListResponse(
        meters=[
            _meter_out(
                meter,
                (
                    f"{format_number_de(consumption[meter.id].value)} "
                    f"{UNIT_SYMBOLS[meter.measurement_unit]}"
                    if meter.id in consumption
                    else None
                ),
                today,
            )
            for meter in meters
        ],
        period_label=PERIOD_LABEL,
    )


@router.post("/buildings/{building_id}/meters", status_code=201)
def create_meter(
    account_id: str, building_id: str, body: MeterCreate, session: PathAccountSession
) -> MeterOut:
    _building_or_404(session, building_id)
    if body.unit_id is not None:
        unit = session.get(Unit, body.unit_id)
        if unit is None or unit.building_id != building_id:
            raise HTTPException(status_code=422, detail="Unit is not in this building")
    duplicate = session.scalar(
        select(Meter).where(Meter.building_id == building_id, Meter.serial == body.serial)
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=422, detail="Diese Zählernummer existiert bereits im Objekt"
        )
    meter = Meter(
        id=new_id(),
        account_id=account_id,
        building_id=building_id,
        unit_id=body.unit_id,
        kind=body.kind,
        measurement_unit=body.measurement_unit,
        serial=body.serial,
        label=body.label,
        calibration_valid_until=body.calibration_valid_until,
        valuation_factor_x1000=(
            body.valuation_factor_x1000
            if body.valuation_factor_x1000 is not None
            else (1000 if body.kind is MeterKind.HEAT else None)
        ),
    )
    session.add(meter)
    session.flush()
    session.refresh(meter)
    return _meter_out(meter, None, date.today())


@router.delete("/meters/{meter_id}", status_code=204)
def delete_meter(account_id: str, meter_id: str, session: PathAccountSession) -> None:
    """Removes a mis-created device together with its readings.

    Same reasoning as a cost entry: a meter is *input*, not an issued record.
    TODO(M4): refuse once a FINALIZED statement was computed from its readings
    — a correction then becomes a new statement version instead.
    """
    del account_id
    meter = session.get(Meter, meter_id)
    if meter is None:
        raise HTTPException(status_code=404, detail="Meter not found")
    for reading in list(meter.readings):
        session.delete(reading)
    session.delete(meter)


@router.post("/meters/{meter_id}/readings", status_code=201)
def create_reading(
    account_id: str, meter_id: str, body: MeterReadingCreate, session: PathAccountSession
) -> MeterOut:
    """Append a reading. There is no update path — that is the feature.

    A second reading for a date it already has is accepted on purpose: that is
    how a correction works, and the newer row wins for billing.
    """
    meter = session.get(Meter, meter_id)
    if meter is None:
        raise HTTPException(status_code=404, detail="Meter not found")
    if body.tenancy_id is not None:
        tenancy = session.get(Tenancy, body.tenancy_id)
        if tenancy is None or meter.unit_id is None or tenancy.unit_id != meter.unit_id:
            raise HTTPException(status_code=422, detail="Tenancy is not assigned to this meter")
    session.add(
        MeterReading(
            id=new_id(),
            account_id=account_id,
            meter_id=meter.id,
            read_at=body.read_at,
            value_x1000=body.value_x1000,
            reason=body.reason,
            source=body.source,
            note=body.note,
            tenancy_id=body.tenancy_id,
            estimated_consumption_x1000=body.estimated_consumption_x1000,
            estimation_basis=body.estimation_basis,
            provenance_ref=body.provenance_ref,
        )
    )
    session.flush()
    session.refresh(meter)
    consumption = consumption_by_meter(
        DbMeterGateway(session).list_readings(
            meter.building_id, BILLING_START, BILLING_END - timedelta(days=1)
        )
    )
    display = (
        f"{format_number_de(consumption[meter.id].value)} {UNIT_SYMBOLS[meter.measurement_unit]}"
        if meter.id in consumption
        else None
    )
    return _meter_out(meter, display, date.today())


# ── Heizkosten: the fuel invoice behind §§ 7-9 HeizkostenV + CO2KostAufG ──


def _heating_cost_out(row: HeatingCostEntry) -> HeatingCostOut:
    return HeatingCostOut(
        id=row.id,
        label=row.label,
        amount_cents=row.amount_cents,
        amount_eur=format_eur(cents(row.amount_cents)),
        period_from=row.period_from,
        period_to=row.period_to,
        co2_kg_x1000=row.co2_kg_x1000,
        co2_kg_display=(
            format_number_de(_scaled(row.co2_kg_x1000)) if row.co2_kg_x1000 is not None else None
        ),
        co2_cost_cents=row.co2_cost_cents,
        co2_cost_eur=(
            format_eur(cents(row.co2_cost_cents)) if row.co2_cost_cents is not None else None
        ),
    )


@router.get("/buildings/{building_id}/heating-costs")
def list_heating_costs(
    account_id: str, building_id: str, session: PathAccountSession
) -> HeatingCostListResponse:
    del account_id
    _building_or_404(session, building_id)
    rows = session.scalars(
        select(HeatingCostEntry)
        .where(HeatingCostEntry.building_id == building_id)
        .order_by(HeatingCostEntry.created_at, HeatingCostEntry.id)
    ).all()
    return HeatingCostListResponse(heating_costs=[_heating_cost_out(r) for r in rows])


@router.post("/buildings/{building_id}/heating-costs", status_code=201)
def create_heating_cost(
    account_id: str,
    building_id: str,
    body: HeatingCostCreate,
    session: PathAccountSession,
) -> HeatingCostOut:
    _building_or_404(session, building_id)
    row = HeatingCostEntry(
        id=new_id(),
        account_id=account_id,
        building_id=building_id,
        label=body.label,
        amount_cents=body.amount_cents,
        period_from=body.period_from,
        period_to=body.period_to,
        co2_kg_x1000=body.co2_kg_x1000,
        co2_cost_cents=body.co2_cost_cents,
    )
    session.add(row)
    session.flush()
    session.refresh(row)
    return _heating_cost_out(row)


@router.delete("/heating-costs/{heating_cost_id}", status_code=204)
def delete_heating_cost(account_id: str, heating_cost_id: str, session: PathAccountSession) -> None:
    del account_id
    row = session.get(HeatingCostEntry, heating_cost_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Heating cost not found")
    session.delete(row)
