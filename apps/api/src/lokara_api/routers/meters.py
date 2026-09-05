"""UI-08 meter inventory, append-only readings and heating source workflow."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException
from lokara_adapters import consumption_by_meter
from lokara_db import (
    Building,
    BuildingUviConfiguration,
    HeatingBillingModeVersion,
    HeatingCostEntry,
    MdlStatement,
    Meter,
    MeterLifecycleEvent,
    MeterReading,
    Statement,
    Tenancy,
    Unit,
    new_id,
)
from lokara_domain import (
    CalibrationDataState,
    ExternalHeatingStatus,
    MeasurementUnit,
    MeterDeviceType,
    MeterKind,
    MeterLifecycleEventType,
    Period,
    ReadingReason,
    ReadingSource,
    cents,
    format_eur,
)
from lokara_guard_engine import (
    GuardSourceIdentity,
    MeterCalibrationInput,
    MeterCalibrationRuleBundle,
    RuleConflict,
    RuleEvidence,
    evaluate_meter_calibration,
)
from lokara_pdf import format_number_de
from lokara_rules_store import resolve_page05_g1_rules
from sqlalchemy import select

from ..authorization import (
    portal_role,
    require_building,
    require_owner,
    require_resource_building,
    visible_building_ids,
)
from ..deps import PathAccountSession
from ..meter_gateway import VALUE_SCALE, DbMeterGateway
from ..schemas import (
    GasConversionOut,
    HeatingBillingModeCreate,
    HeatingBillingModeOut,
    HeatingCostCreate,
    HeatingCostListResponse,
    HeatingCostOut,
    HeatingCostVoid,
    MeterConsumptionPeriod,
    MeterConsumptionReading,
    MeterCreate,
    MeterLifecycleCreate,
    MeterLifecycleOut,
    MeterListResponse,
    MeterOut,
    MeterReadingCreate,
    MeterReadingOut,
    MeterWorkspaceBuilding,
    MeterWorkspacePermissions,
    MeterWorkspaceResponse,
    MeterWorkspaceTenancy,
    MeterWorkspaceUnit,
    ReadingPlausibilityFinding,
    ReadingPlausibilityResponse,
)
from ..statement_service import period_label
from ..time import berlin_today

router = APIRouter(prefix="/a/{account_id}")

DEVICE_LABELS: dict[MeterDeviceType, str] = {
    MeterDeviceType.HEAT_METER: "Wärmemengenzähler",
    MeterDeviceType.HEAT_COST_ALLOCATOR: "Heizkostenverteiler",
    MeterDeviceType.WARM_WATER_METER: "Warmwasserzähler",
    MeterDeviceType.COLD_WATER_METER: "Kaltwasserzähler",
    MeterDeviceType.GAS_METER: "Gaszähler",
}

UNIT_SYMBOLS: dict[MeasurementUnit, str] = {
    MeasurementUnit.KWH: "kWh",
    MeasurementUnit.CUBIC_METRE: "m³",
    MeasurementUnit.HKV_UNITS: "Einheiten",
}

CALIBRATION_MEDIUM: dict[MeterDeviceType, str] = {
    MeterDeviceType.HEAT_METER: "heat_meter",
    MeterDeviceType.HEAT_COST_ALLOCATOR: "heat_cost_allocator",
    MeterDeviceType.WARM_WATER_METER: "warm_water",
    MeterDeviceType.COLD_WATER_METER: "cold_water",
    MeterDeviceType.GAS_METER: "gas",
}

CalibrationStatus = Literal[
    "EXPIRED",
    "EXPIRING_SOON",
    "VALID",
    "MISSING_DATA",
    "NOT_APPLICABLE",
    "REVIEW_REQUIRED",
]


def _scaled(value_x1000: int) -> Decimal:
    return Decimal(value_x1000) / VALUE_SCALE


def _meter_or_404(session: PathAccountSession, meter_id: str) -> Meter:
    meter = session.get(Meter, meter_id)
    if meter is None:
        raise HTTPException(status_code=404, detail="Zähler nicht gefunden")
    require_resource_building(session, meter.building_id)
    return meter


def _events_by_meter(
    session: PathAccountSession, building_ids: list[str]
) -> dict[str, list[MeterLifecycleEvent]]:
    if not building_ids:
        return {}
    rows = session.scalars(
        select(MeterLifecycleEvent)
        .where(MeterLifecycleEvent.building_id.in_(building_ids))
        .order_by(
            MeterLifecycleEvent.effective_on,
            MeterLifecycleEvent.created_at,
            MeterLifecycleEvent.id,
        )
    ).all()
    grouped: dict[str, list[MeterLifecycleEvent]] = defaultdict(list)
    for row in rows:
        grouped[row.meter_id].append(row)
    return grouped


def _lifecycle(
    meter: Meter, events: list[MeterLifecycleEvent]
) -> tuple[Literal["ACTIVE", "REMOVED", "REPLACED", "VOID"], date | None, str | None]:
    status: Literal["ACTIVE", "REMOVED", "REPLACED", "VOID"] = "ACTIVE"
    ended_on: date | None = None
    related_id: str | None = None
    for event in events:
        if event.event_type is MeterLifecycleEventType.INSTALLED:
            continue
        if event.event_type is MeterLifecycleEventType.REMOVED:
            status = "REMOVED"
        elif event.event_type is MeterLifecycleEventType.REPLACED:
            status = "REPLACED"
        else:
            status = "VOID"
        ended_on = event.effective_on
        related_id = event.related_meter_id
    return status, ended_on, related_id


def _guard_bundle(today: date) -> tuple[MeterCalibrationRuleBundle, str]:
    resolved = resolve_page05_g1_rules(today)
    source = resolved.value.w2
    return (
        MeterCalibrationRuleBundle(
            evidence=tuple(
                RuleEvidence(
                    source=item.source,
                    register_row=item.register_row,
                    legal_basis=item.legal_basis,
                    rechtsstand=item.rechtsstand,
                    verification_status=item.verification_status,
                )
                for item in source.evidence
            ),
            unresolved_conflicts=tuple(
                RuleConflict(
                    code=item.code,
                    description=item.description,
                    production_blocking=item.production_blocking,
                    applies_to_media=item.applies_to_media or None,
                )
                for item in source.unresolved_conflicts
            ),
            years_by_medium=source.years_by_medium,
            legacy_years_by_medium=source.legacy_years_by_medium,
            medium_labels_de=source.medium_labels_de,
            excluded_media=source.excluded_media,
            expiry_month=source.expiry_month,
            expiry_day=source.expiry_day,
            warning_de=source.warning_de,
            channels_by_stage=source.channels_by_stage,
            resolution_event=source.resolution_event,
        ),
        resolved.rechtsstand,
    )


def _calibration(
    meter: Meter, today: date
) -> tuple[CalibrationStatus, date | None, str | None, str | None, list[str]]:
    if meter.calibration_data_state is CalibrationDataState.NOT_APPLICABLE:
        return "NOT_APPLICABLE", None, "Nicht eichpflichtig", None, []
    if meter.calibration_data_state is CalibrationDataState.MISSING_DATA:
        return "MISSING_DATA", None, "Eichdaten fehlen", None, []
    if meter.calibration_data_state is CalibrationDataState.REVIEW_REQUIRED:
        return "REVIEW_REQUIRED", None, "Eichpflicht prüfen", None, []
    rules, rechtsstand = _guard_bundle(today)
    result = evaluate_meter_calibration(
        MeterCalibrationInput(
            source_identity=GuardSourceIdentity(source_type="meter", source_id=meter.id),
            today=today,
            calibration_date=meter.calibration_date,
            medium=CALIBRATION_MEDIUM[meter.device_type],
            unit_label=meter.unit.label if meter.unit is not None else "Gebäude/Heizungsanlage",
        ),
        rules,
    )
    status: CalibrationStatus
    if result.stage == "exceeded":
        status = "EXPIRED"
    elif result.stage in {"expiry_month", "notice"}:
        status = "EXPIRING_SOON"
    elif result.stage == "missing_calibration_date":
        status = "MISSING_DATA"
    elif result.stage == "excluded":
        status = "NOT_APPLICABLE"
    else:
        status = "VALID"
    return (
        status,
        result.boundary_date,
        result.warning_de,
        rechtsstand,
        list(result.production_blockers),
    )


def _effective_readings(meter: Meter) -> tuple[list[MeterReading], set[str]]:
    rows = sorted(meter.readings, key=lambda row: (row.read_at, row.recorded_at, row.id))
    effective_per_date: dict[date, str] = {}
    explicitly_superseded = {
        row.supersedes_reading_id for row in rows if row.supersedes_reading_id is not None
    }
    for row in rows:
        effective_per_date[row.read_at] = row.id
    superseded = {
        row.id
        for row in rows
        if effective_per_date[row.read_at] != row.id or row.id in explicitly_superseded
    }
    return rows, superseded


def _workspace_periods(session: PathAccountSession, building_ids: list[str]) -> tuple[Period, ...]:
    periods: dict[tuple[date, date], Period] = {}
    if building_ids:
        costs = session.scalars(
            select(HeatingCostEntry)
            .where(
                HeatingCostEntry.building_id.in_(building_ids),
                HeatingCostEntry.voided_at.is_(None),
            )
            .order_by(HeatingCostEntry.period_to.desc(), HeatingCostEntry.id.desc())
        ).all()
        for cost in costs:
            periods[(cost.period_from, cost.period_to)] = Period(
                valid_from=cost.period_from, valid_to=cost.period_to
            )
        reading_dates = session.scalars(
            select(MeterReading.read_at)
            .join(Meter, Meter.id == MeterReading.meter_id)
            .where(Meter.building_id.in_(building_ids))
            .order_by(MeterReading.read_at.desc())
        ).all()
        for read_at in reading_dates:
            annual_to = date(read_at.year + 1, 1, 1)
            annual = Period(valid_from=date(read_at.year, 1, 1), valid_to=annual_to)
            periods.setdefault((annual.valid_from, annual_to), annual)
    if not periods:
        year = berlin_today().year
        current_to = date(year + 1, 1, 1)
        current = Period(valid_from=date(year, 1, 1), valid_to=current_to)
        periods[(current.valid_from, current_to)] = current
    return tuple(
        sorted(
            periods.values(),
            key=lambda item: (item.valid_to or item.valid_from, item.valid_from),
            reverse=True,
        )
    )


def _workspace_period(session: PathAccountSession, building_ids: list[str]) -> Period:
    return _workspace_periods(session, building_ids)[0]


def _consumption_display(
    session: PathAccountSession, building_id: str, period: Period
) -> dict[str, str]:
    assert period.valid_to is not None
    rows = DbMeterGateway(session).list_readings(
        building_id, period.valid_from, period.valid_to - timedelta(days=1)
    )
    return {
        meter_id: f"{format_number_de(result.value)} {UNIT_SYMBOLS[result.measurement_unit]}"
        for meter_id, result in consumption_by_meter(rows).items()
    }


def _meter_out(
    meter: Meter,
    events: list[MeterLifecycleEvent],
    consumption_display: str | None,
    today: date,
    periods: tuple[Period, ...] | None = None,
    gas_configuration: BuildingUviConfiguration | None = None,
) -> MeterOut:
    lifecycle_status, lifecycle_ended_on, related_meter_id = _lifecycle(meter, events)
    calibration_status, valid_until, message, rechtsstand, blockers = _calibration(meter, today)
    rows, superseded = _effective_readings(meter)
    gas_conversion = None
    if gas_configuration is not None:
        assert gas_configuration.calorific_factor is not None
        assert gas_configuration.condition_number is not None
        gas_conversion = GasConversionOut(
            calorific_factor_kwh_per_m3=gas_configuration.calorific_factor,
            condition_number=gas_configuration.condition_number,
            valid_from=gas_configuration.valid_from,
            valid_to=gas_configuration.valid_to,
            supplier_invoice_reference=gas_configuration.source_id,
            source_type="SUPPLIER_INVOICE",
            source_id=gas_configuration.source_id,
            rechtsstand="08/2026",
            verification_status="verify-before-production",
            configuration_id=gas_configuration.id,
            supersedes_configuration_id=gas_configuration.supersedes_configuration_id,
        )
    return MeterOut(
        id=meter.id,
        unit_id=meter.unit_id,
        unit_label=meter.unit.label if meter.unit is not None else None,
        device_type=meter.device_type,
        device_type_label=DEVICE_LABELS[meter.device_type],
        kind=meter.kind,
        kind_label=DEVICE_LABELS[meter.device_type],
        measurement_unit=meter.measurement_unit,
        unit_symbol=UNIT_SYMBOLS[meter.measurement_unit],
        serial=meter.serial,
        label=meter.label,
        location=meter.location,
        manufacturer=meter.manufacturer,
        model=meter.model,
        installed_on=meter.installed_on,
        lifecycle_status=lifecycle_status,
        lifecycle_ended_on=lifecycle_ended_on,
        related_meter_id=related_meter_id,
        lifecycle_events=[
            MeterLifecycleOut(
                id=event.id,
                event_type=event.event_type,
                effective_on=event.effective_on,
                reason=event.reason,
                related_meter_id=event.related_meter_id,
                created_at=event.created_at,
            )
            for event in reversed(events)
        ],
        remote_readability=meter.remote_readability,
        calibration_data_state=meter.calibration_data_state,
        calibration_date=meter.calibration_date,
        calibration_evidence_ref=meter.calibration_evidence_ref,
        calibration_valid_until=valid_until,
        valuation_factor_x1000=meter.valuation_factor_x1000,
        valuation_factor_display=(
            format_number_de(_scaled(meter.valuation_factor_x1000))
            if meter.valuation_factor_x1000 is not None
            else None
        ),
        gas_conversion=gas_conversion,
        calibration_status=calibration_status,
        calibration_message=message,
        calibration_rechtsstand=rechtsstand,
        calibration_production_blockers=blockers,
        readings=[
            MeterReadingOut(
                id=row.id,
                read_at=row.read_at,
                value_x1000=row.value_x1000,
                value_display=format_number_de(_scaled(row.value_x1000)),
                reason=row.reason,
                source=row.source,
                note=row.note,
                supersedes_reading_id=row.supersedes_reading_id,
                confirmation_note=row.confirmation_note,
                tenancy_id=row.tenancy_id,
                estimated_consumption_x1000=row.estimated_consumption_x1000,
                estimation_basis=row.estimation_basis,
                provenance_ref=row.provenance_ref,
                recorded_at=row.recorded_at,
                superseded=row.id in superseded,
            )
            for row in reversed(rows)
        ],
        consumption_periods=[
            _meter_consumption_period(meter, events, period) for period in (periods or ())
        ],
        period_consumption_display=consumption_display,
    )


def _consumption_reading(row: MeterReading) -> MeterConsumptionReading:
    return MeterConsumptionReading(
        id=row.id,
        read_at=row.read_at,
        value_x1000=row.value_x1000,
        value_display=format_number_de(_scaled(row.value_x1000)),
        source=row.source,
    )


def _meter_consumption_period(
    meter: Meter, events: list[MeterLifecycleEvent], period: Period
) -> MeterConsumptionPeriod:
    assert period.valid_to is not None
    period_to = period.valid_to
    period_end = period_to - timedelta(days=1)
    _, lifecycle_ended_on, _ = _lifecycle(meter, events)
    rows, superseded = _effective_readings(meter)
    effective = [
        row
        for row in rows
        if row.id not in superseded and period.valid_from <= row.read_at <= period_end
    ]
    opening = next((row for row in effective if row.read_at == period.valid_from), None)
    closing = next((row for row in reversed(effective) if row.read_at == period_end), None)

    def result(
        *,
        status: Literal["MEASURED", "INCOMPLETE", "ESTIMATED", "NOT_APPLICABLE"],
        consumption_x1000: int | None,
        consumption_display: str | None,
        finding: str | None,
        estimation_basis: str | None,
        provenance_ref: str | None,
    ) -> MeterConsumptionPeriod:
        return MeterConsumptionPeriod(
            period_from=period.valid_from,
            period_to=period_to,
            period_label=period_label(period),
            status=status,
            opening_reading=_consumption_reading(opening) if opening is not None else None,
            closing_reading=_consumption_reading(closing) if closing is not None else None,
            consumption_x1000=consumption_x1000,
            consumption_display=consumption_display,
            finding=finding,
            estimation_basis=estimation_basis,
            provenance_ref=provenance_ref,
        )

    if meter.installed_on > period.valid_from or (
        lifecycle_ended_on is not None and lifecycle_ended_on <= period_end
    ):
        return result(
            status="NOT_APPLICABLE",
            consumption_x1000=None,
            consumption_display=None,
            finding="Gerätewechsel im Zeitraum",
            estimation_basis=None,
            provenance_ref=None,
        )
    estimate = next(
        (row for row in reversed(effective) if row.estimated_consumption_x1000 is not None), None
    )
    if estimate is not None:
        assert estimate.estimated_consumption_x1000 is not None
        return result(
            status="ESTIMATED",
            consumption_x1000=estimate.estimated_consumption_x1000,
            consumption_display=(
                f"{format_number_de(_scaled(estimate.estimated_consumption_x1000))} "
                f"{UNIT_SYMBOLS[meter.measurement_unit]}"
            ),
            finding="Geschätzter Verbrauch",
            estimation_basis=estimate.estimation_basis,
            provenance_ref=estimate.provenance_ref,
        )
    if opening is None or closing is None:
        missing = (
            "Anfangs- und Endablesung fehlen"
            if opening is None and closing is None
            else ("Anfangsablesung fehlt" if opening is None else "Endablesung fehlt")
        )
        return result(
            status="INCOMPLETE",
            consumption_x1000=None,
            consumption_display=None,
            finding=missing,
            estimation_basis=None,
            provenance_ref=None,
        )
    difference = closing.value_x1000 - opening.value_x1000
    if difference < 0:
        return result(
            status="INCOMPLETE",
            consumption_x1000=None,
            consumption_display=None,
            finding="Zählerstand läuft rückwärts; Verbrauch wird nicht verwendet",
            estimation_basis=None,
            provenance_ref=None,
        )
    return result(
        status="MEASURED",
        consumption_x1000=difference,
        consumption_display=(
            f"{format_number_de(_scaled(difference))} {UNIT_SYMBOLS[meter.measurement_unit]}"
        ),
        finding=None,
        estimation_basis=None,
        provenance_ref=None,
    )


def _building_meters(
    session: PathAccountSession,
    building: Building,
    events: dict[str, list[MeterLifecycleEvent]],
    periods: tuple[Period, ...],
    today: date,
) -> list[MeterOut]:
    consumption = _consumption_display(session, building.id, periods[0])
    meters = sorted(
        building.meters,
        key=lambda meter: (
            meter.unit_id is not None,
            meter.unit.label if meter.unit is not None else "",
            DEVICE_LABELS[meter.device_type],
            meter.serial,
        ),
    )
    return [
        _meter_out(
            meter,
            events.get(meter.id, []),
            consumption.get(meter.id),
            today,
            periods,
        )
        for meter in meters
    ]


@router.get("/meter-workspace")
def meter_workspace(account_id: str, session: PathAccountSession) -> MeterWorkspaceResponse:
    del account_id
    visible = visible_building_ids(session)
    query = (
        select(Building).where(Building.archived_at.is_(None)).order_by(Building.name, Building.id)
    )
    if visible is not None:
        query = query.where(Building.id.in_(visible))
    buildings = list(session.scalars(query).all())
    building_ids = [building.id for building in buildings]
    events = _events_by_meter(session, building_ids)
    periods = _workspace_periods(session, building_ids)
    period = periods[0]
    today = berlin_today()
    projections: list[MeterWorkspaceBuilding] = []
    expired_ids: list[str] = []
    for building in buildings:
        meters = _building_meters(session, building, events, periods, today)
        by_unit: dict[str, list[MeterOut]] = defaultdict(list)
        building_meters: list[MeterOut] = []
        for meter in meters:
            if meter.unit_id is None:
                building_meters.append(meter)
            else:
                by_unit[meter.unit_id].append(meter)
            if meter.calibration_status == "EXPIRED" and meter.lifecycle_status == "ACTIVE":
                expired_ids.append(meter.id)
        units = [
            MeterWorkspaceUnit(
                id=unit.id,
                label=unit.label,
                active_meter_count=sum(
                    meter.lifecycle_status == "ACTIVE" for meter in by_unit.get(unit.id, [])
                ),
                warning_count=sum(
                    meter.calibration_status in {"EXPIRED", "MISSING_DATA", "REVIEW_REQUIRED"}
                    and meter.lifecycle_status == "ACTIVE"
                    for meter in by_unit.get(unit.id, [])
                ),
                tenancies=[
                    MeterWorkspaceTenancy(
                        id=tenancy.id,
                        label=(
                            ", ".join(
                                party.renter.legal_name
                                for party in tenancy.parties
                                if party.renter is not None
                            )
                            or "Mietverhältnis"
                        ),
                        valid_from=tenancy.valid_from,
                        valid_to=tenancy.valid_to,
                    )
                    for tenancy in sorted(
                        unit.tenancies,
                        key=lambda row: (row.valid_from, row.id),
                        reverse=True,
                    )
                ],
                meters=by_unit.get(unit.id, []),
            )
            for unit in sorted(building.units, key=lambda row: (row.label, row.id))
        ]
        projections.append(
            MeterWorkspaceBuilding(
                id=building.id,
                name=building.name,
                address=f"{building.street}, {building.postal_code} {building.city}",
                active_meter_count=sum(meter.lifecycle_status == "ACTIVE" for meter in meters),
                expired_count=sum(
                    meter.calibration_status == "EXPIRED" and meter.lifecycle_status == "ACTIVE"
                    for meter in meters
                ),
                missing_data_count=sum(
                    meter.calibration_status in {"MISSING_DATA", "REVIEW_REQUIRED"}
                    and meter.lifecycle_status == "ACTIVE"
                    for meter in meters
                ),
                building_meters=building_meters,
                units=units,
            )
        )
    return MeterWorkspaceResponse(
        as_of=datetime.now(UTC),
        period_label=period_label(period),
        buildings=projections,
        expired_meter_ids=expired_ids,
        permissions=MeterWorkspacePermissions(can_write=portal_role(session).value == "OWNER"),
    )


@router.get("/buildings/{building_id}/meters")
def list_meters(
    account_id: str, building_id: str, session: PathAccountSession
) -> MeterListResponse:
    del account_id
    building = require_building(session, building_id)
    periods = _workspace_periods(session, [building_id])
    period = periods[0]
    events = _events_by_meter(session, [building_id])
    return MeterListResponse(
        meters=_building_meters(session, building, events, periods, berlin_today()),
        period_label=period_label(period),
    )


def _new_meter(account_id: str, building_id: str, body: MeterCreate) -> Meter:
    assert body.device_type is not None
    assert body.kind is not None
    assert body.measurement_unit is not None
    return Meter(
        id=new_id(),
        account_id=account_id,
        building_id=building_id,
        unit_id=body.unit_id,
        device_type=body.device_type,
        kind=body.kind,
        measurement_unit=body.measurement_unit,
        serial=body.serial,
        label=body.label,
        location=body.location,
        manufacturer=body.manufacturer,
        model=body.model,
        installed_on=body.installed_on,
        remote_readability=body.remote_readability,
        calibration_data_state=body.calibration_data_state,
        calibration_date=body.calibration_date,
        calibration_evidence_ref=body.calibration_evidence_ref,
        calibration_valid_until=None,
        valuation_factor_x1000=(
            body.valuation_factor_x1000
            if body.valuation_factor_x1000 is not None
            else (1000 if body.kind is MeterKind.HEAT else None)
        ),
    )


def _append_gas_configuration(
    account_id: str,
    building_id: str,
    body: MeterCreate,
    session: PathAccountSession,
) -> BuildingUviConfiguration | None:
    conversion = body.gas_conversion
    if conversion is None:
        return None
    configurations = list(
        session.scalars(
            select(BuildingUviConfiguration).where(
                BuildingUviConfiguration.account_id == account_id,
                BuildingUviConfiguration.building_id == building_id,
            )
        )
    )
    superseded_ids = {
        row.supersedes_configuration_id
        for row in configurations
        if row.supersedes_configuration_id is not None
    }
    leaves = [row for row in configurations if row.id not in superseded_ids]
    if len(leaves) > 1:
        raise HTTPException(
            status_code=422,
            detail="Die UVI-Gebäudekonfiguration hat mehrere aktive Nachfolger.",
        )
    predecessor = leaves[0] if leaves else None
    if predecessor is not None and conversion.valid_from <= predecessor.valid_from:
        raise HTTPException(
            status_code=422,
            detail="Die Gaskonfiguration muss nach der bisherigen Version beginnen.",
        )
    configuration = BuildingUviConfiguration(
        id=new_id(),
        account_id=account_id,
        building_id=building_id,
        energy_source="Erdgas",
        energy_reference="HO",
        explicit_hkv_allocator=False,
        calorific_factor=conversion.calorific_factor_kwh_per_m3,
        condition_number=conversion.condition_number,
        valid_from=conversion.valid_from,
        valid_to=conversion.valid_to,
        source_type="SUPPLIER_INVOICE",
        source_id=conversion.supplier_invoice_reference,
        rechtsstand="08/2026",
        verification_status="verify-before-production",
        supersedes_configuration_id=None if predecessor is None else predecessor.id,
    )
    session.add(configuration)
    return configuration


@router.post("/buildings/{building_id}/meters", status_code=201)
def create_meter(
    account_id: str, building_id: str, body: MeterCreate, session: PathAccountSession
) -> MeterOut:
    require_owner(session)
    require_building(session, building_id)
    if body.unit_id is not None:
        unit = session.get(Unit, body.unit_id)
        if unit is None or unit.building_id != building_id:
            raise HTTPException(status_code=422, detail="Einheit gehört nicht zu diesem Objekt")
    duplicate = session.scalar(
        select(Meter).where(Meter.building_id == building_id, Meter.serial == body.serial)
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=422, detail="Diese Zählernummer existiert bereits im Objekt"
        )
    predecessor: Meter | None = None
    if body.creation_mode == "REPLACEMENT":
        assert body.replaces_meter_id is not None
        predecessor = _meter_or_404(session, body.replaces_meter_id)
        if predecessor.building_id != building_id or predecessor.unit_id != body.unit_id:
            raise HTTPException(
                status_code=422, detail="Ersatzgerät muss dieselbe Objektzuordnung haben"
            )
        status, _, _ = _lifecycle(
            predecessor, _events_by_meter(session, [building_id]).get(predecessor.id, [])
        )
        if status != "ACTIVE":
            raise HTTPException(status_code=422, detail="Der Vorgänger ist nicht aktiv")
    meter = _new_meter(account_id, building_id, body)
    session.add(meter)
    gas_configuration = _append_gas_configuration(account_id, building_id, body, session)
    session.flush()
    session.add(
        MeterLifecycleEvent(
            id=new_id(),
            account_id=account_id,
            building_id=building_id,
            meter_id=meter.id,
            event_type=MeterLifecycleEventType.INSTALLED,
            effective_on=body.installed_on,
            reason=None,
            related_meter_id=predecessor.id if predecessor is not None else None,
        )
    )
    if predecessor is not None:
        assert body.replacement_date is not None
        assert body.old_final_value_x1000 is not None
        assert body.new_initial_value_x1000 is not None
        assert body.replacement_reason is not None
        session.add_all(
            [
                MeterLifecycleEvent(
                    id=new_id(),
                    account_id=account_id,
                    building_id=building_id,
                    meter_id=predecessor.id,
                    event_type=MeterLifecycleEventType.REPLACED,
                    effective_on=body.replacement_date,
                    reason=body.replacement_reason,
                    related_meter_id=meter.id,
                ),
                MeterReading(
                    id=new_id(),
                    account_id=account_id,
                    meter_id=predecessor.id,
                    read_at=body.replacement_date,
                    value_x1000=body.old_final_value_x1000,
                    reason=ReadingReason.DEVICE_CHANGE,
                    source=ReadingSource.MANUAL,
                    note="Schlussstand beim Zählerwechsel",
                    supersedes_reading_id=None,
                    confirmation_note=body.replacement_reason,
                    tenancy_id=None,
                    estimated_consumption_x1000=None,
                    estimation_basis=None,
                    provenance_ref=None,
                ),
                MeterReading(
                    id=new_id(),
                    account_id=account_id,
                    meter_id=meter.id,
                    read_at=body.replacement_date,
                    value_x1000=body.new_initial_value_x1000,
                    reason=ReadingReason.DEVICE_CHANGE,
                    source=ReadingSource.MANUAL,
                    note="Anfangsstand beim Zählerwechsel",
                    supersedes_reading_id=None,
                    confirmation_note=body.replacement_reason,
                    tenancy_id=None,
                    estimated_consumption_x1000=None,
                    estimation_basis=None,
                    provenance_ref=None,
                ),
            ]
        )
    session.flush()
    session.refresh(meter)
    events = _events_by_meter(session, [building_id]).get(meter.id, [])
    return _meter_out(
        meter,
        events,
        None,
        berlin_today(),
        gas_configuration=gas_configuration,
    )


def _terminal_event(
    *,
    account_id: str,
    meter: Meter,
    body: MeterLifecycleCreate,
    event_type: MeterLifecycleEventType,
    session: PathAccountSession,
) -> MeterOut:
    require_owner(session)
    events = _events_by_meter(session, [meter.building_id]).get(meter.id, [])
    status, _, _ = _lifecycle(meter, events)
    if status != "ACTIVE":
        raise HTTPException(status_code=422, detail="Der Zähler ist nicht mehr aktiv")
    if body.effective_on < meter.installed_on:
        raise HTTPException(status_code=422, detail="Datum liegt vor dem Einbau")
    if event_type is MeterLifecycleEventType.VOID:
        if meter.readings:
            raise HTTPException(
                status_code=422,
                detail="Ein Zähler mit Ablesungen kann nicht storniert, nur ausgebaut werden",
            )
        used_statement = session.scalar(
            select(Statement.id).where(
                Statement.building_id == meter.building_id,
                Statement.period_end >= meter.installed_on,
            )
        )
        if used_statement is not None:
            raise HTTPException(
                status_code=422,
                detail="Der Zähler kann wegen vorhandener Abrechnungen nicht storniert werden",
            )
    session.add(
        MeterLifecycleEvent(
            id=new_id(),
            account_id=account_id,
            building_id=meter.building_id,
            meter_id=meter.id,
            event_type=event_type,
            effective_on=body.effective_on,
            reason=body.reason,
            related_meter_id=None,
        )
    )
    session.flush()
    return _meter_out(
        meter,
        _events_by_meter(session, [meter.building_id]).get(meter.id, []),
        None,
        berlin_today(),
    )


@router.post("/meters/{meter_id}/remove")
def remove_meter(
    account_id: str,
    meter_id: str,
    body: MeterLifecycleCreate,
    session: PathAccountSession,
) -> MeterOut:
    return _terminal_event(
        account_id=account_id,
        meter=_meter_or_404(session, meter_id),
        body=body,
        event_type=MeterLifecycleEventType.REMOVED,
        session=session,
    )


@router.post("/meters/{meter_id}/void")
def void_meter(
    account_id: str,
    meter_id: str,
    body: MeterLifecycleCreate,
    session: PathAccountSession,
) -> MeterOut:
    return _terminal_event(
        account_id=account_id,
        meter=_meter_or_404(session, meter_id),
        body=body,
        event_type=MeterLifecycleEventType.VOID,
        session=session,
    )


def _reading_findings(
    meter: Meter, body: MeterReadingCreate, session: PathAccountSession
) -> ReadingPlausibilityResponse:
    events = _events_by_meter(session, [meter.building_id]).get(meter.id, [])
    status, ended_on, _ = _lifecycle(meter, events)
    findings: list[ReadingPlausibilityFinding] = []
    if body.read_at < meter.installed_on or (ended_on is not None and body.read_at > ended_on):
        findings.append(
            ReadingPlausibilityFinding(
                code="OUTSIDE_DEVICE_LIFECYCLE",
                severity="BLOCKER",
                message="Das Ablesedatum liegt außerhalb des aktiven Gerätezeitraums.",
                requires_confirmation=False,
            )
        )
    if status == "VOID":
        findings.append(
            ReadingPlausibilityFinding(
                code="VOID_DEVICE",
                severity="BLOCKER",
                message="Für einen stornierten Zähler kann keine Ablesung erfasst werden.",
                requires_confirmation=False,
            )
        )
    rows, superseded = _effective_readings(meter)
    effective = [row for row in rows if row.id not in superseded]
    same_date = [row for row in effective if row.read_at == body.read_at]
    if body.reason is ReadingReason.CORRECTION:
        target = session.get(MeterReading, body.supersedes_reading_id)
        if (
            target is None
            or target.meter_id != meter.id
            or target.read_at != body.read_at
            or target.id in superseded
        ):
            findings.append(
                ReadingPlausibilityFinding(
                    code="INVALID_CORRECTION_TARGET",
                    severity="BLOCKER",
                    message="Die gewählte Ablesung kann nicht auf diesem Datum korrigiert werden.",
                    requires_confirmation=False,
                )
            )
    elif same_date:
        findings.append(
            ReadingPlausibilityFinding(
                code="DUPLICATE_DATE",
                severity="WARNING",
                message="Für dieses Datum besteht bereits eine wirksame Ablesung.",
                requires_confirmation=True,
            )
        )
    previous = [row for row in effective if row.read_at < body.read_at]
    if previous and body.value_x1000 < max(previous, key=lambda row: row.read_at).value_x1000:
        findings.append(
            ReadingPlausibilityFinding(
                code="REGISTER_ROLLBACK",
                severity="WARNING",
                message=(
                    "Der neue Stand liegt unter der vorherigen wirksamen Ablesung. "
                    "Ein negativer Verbrauch wird nicht verwendet."
                ),
                requires_confirmation=True,
            )
        )
    suggested_tenancy_id: str | None = None
    if body.reason is ReadingReason.TENANT_CHANGE and meter.unit_id is not None:
        suggested_tenancy_id = session.scalar(
            select(Tenancy.id).where(
                Tenancy.unit_id == meter.unit_id,
                Tenancy.valid_from <= body.read_at,
                (Tenancy.valid_to.is_(None) | (Tenancy.valid_to > body.read_at)),
            )
        )
        if suggested_tenancy_id is None:
            findings.append(
                ReadingPlausibilityFinding(
                    code="TENANCY_CONTEXT_MISSING",
                    severity="WARNING",
                    message="Für dieses Datum wurde kein passendes Mietverhältnis gefunden.",
                    requires_confirmation=True,
                )
            )
    return ReadingPlausibilityResponse(findings=findings, suggested_tenancy_id=suggested_tenancy_id)


@router.post("/meters/{meter_id}/readings/check")
def check_reading(
    account_id: str,
    meter_id: str,
    body: MeterReadingCreate,
    session: PathAccountSession,
) -> ReadingPlausibilityResponse:
    del account_id
    return _reading_findings(_meter_or_404(session, meter_id), body, session)


@router.post("/meters/{meter_id}/readings", status_code=201)
def create_reading(
    account_id: str,
    meter_id: str,
    body: MeterReadingCreate,
    session: PathAccountSession,
) -> MeterOut:
    require_owner(session)
    meter = _meter_or_404(session, meter_id)
    result = _reading_findings(meter, body, session)
    blockers = [finding for finding in result.findings if finding.severity == "BLOCKER"]
    if blockers:
        raise HTTPException(status_code=422, detail=blockers[0].message)
    missing_confirmation = [
        finding.code
        for finding in result.findings
        if finding.requires_confirmation and finding.code not in body.confirmed_finding_codes
    ]
    if missing_confirmation:
        raise HTTPException(
            status_code=409,
            detail="Bestätigung erforderlich: " + ", ".join(missing_confirmation),
        )
    confirmed_codes = sorted(
        finding.code
        for finding in result.findings
        if finding.requires_confirmation and finding.code in body.confirmed_finding_codes
    )
    tenancy_id = body.tenancy_id
    if body.reason is ReadingReason.TENANT_CHANGE and tenancy_id is None:
        tenancy_id = result.suggested_tenancy_id
    if tenancy_id is not None:
        tenancy = session.get(Tenancy, tenancy_id)
        if tenancy is None or meter.unit_id is None or tenancy.unit_id != meter.unit_id:
            raise HTTPException(status_code=422, detail="Mietverhältnis gehört nicht zum Zähler")
    session.add(
        MeterReading(
            id=new_id(),
            account_id=account_id,
            meter_id=meter.id,
            read_at=body.read_at,
            value_x1000=body.value_x1000,
            reason=body.reason,
            source=ReadingSource.MANUAL,
            note=body.note,
            supersedes_reading_id=body.supersedes_reading_id,
            confirmation_note=(
                body.confirmation_note
                or (
                    "Bestätigte Befunde: " + ", ".join(confirmed_codes) if confirmed_codes else None
                )
            ),
            tenancy_id=tenancy_id,
            estimated_consumption_x1000=body.estimated_consumption_x1000,
            estimation_basis=body.estimation_basis,
            provenance_ref=body.provenance_ref,
        )
    )
    session.flush()
    session.refresh(meter)
    period = _workspace_period(session, [meter.building_id])
    consumption = _consumption_display(session, meter.building_id, period)
    return _meter_out(
        meter,
        _events_by_meter(session, [meter.building_id]).get(meter.id, []),
        consumption.get(meter.id),
        berlin_today(),
    )


def _heating_cost_out(row: HeatingCostEntry) -> HeatingCostOut:
    return HeatingCostOut(
        id=row.id,
        category=row.category,
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
        source_ref=row.source_ref,
        voided_at=row.voided_at,
        void_reason=row.void_reason,
    )


@router.get("/buildings/{building_id}/heating-costs")
def list_heating_costs(
    account_id: str, building_id: str, session: PathAccountSession
) -> HeatingCostListResponse:
    del account_id
    require_building(session, building_id)
    rows = session.scalars(
        select(HeatingCostEntry)
        .where(HeatingCostEntry.building_id == building_id)
        .order_by(HeatingCostEntry.created_at, HeatingCostEntry.id)
    ).all()
    active = [row for row in rows if row.voided_at is None]
    findings: list[str] = []
    if not active:
        findings.append("Noch keine Heizkostenposition erfasst.")
    if any(row.source_ref is None for row in active):
        findings.append("Bei mindestens einer Position fehlt die Belegreferenz.")
    fuel = [row for row in active if row.category.value == "FUEL_OR_HEAT_SUPPLY"]
    if fuel and any(row.co2_kg_x1000 is None or row.co2_cost_cents is None for row in fuel):
        findings.append("Bei einer Brennstoff-/Wärmelieferung fehlen CO₂-Angaben.")
    readiness: Literal["COMPLETE", "MISSING_INFORMATION", "REVIEW_REQUIRED"]
    if not active:
        readiness = "MISSING_INFORMATION"
    elif findings:
        readiness = "REVIEW_REQUIRED"
    else:
        readiness = "COMPLETE"
    return HeatingCostListResponse(
        heating_costs=[_heating_cost_out(row) for row in rows],
        readiness=readiness,
        findings=findings,
    )


@router.post("/buildings/{building_id}/heating-costs", status_code=201)
def create_heating_cost(
    account_id: str,
    building_id: str,
    body: HeatingCostCreate,
    session: PathAccountSession,
) -> HeatingCostOut:
    require_owner(session)
    require_building(session, building_id)
    row = HeatingCostEntry(
        id=new_id(),
        account_id=account_id,
        building_id=building_id,
        category=body.category,
        label=body.label,
        amount_cents=body.amount_cents,
        period_from=body.period_from,
        period_to=body.period_to,
        co2_kg_x1000=body.co2_kg_x1000,
        co2_cost_cents=body.co2_cost_cents,
        source_ref=body.source_ref,
        voided_at=None,
        void_reason=None,
    )
    session.add(row)
    session.flush()
    session.refresh(row)
    return _heating_cost_out(row)


@router.post("/heating-costs/{heating_cost_id}/void")
def void_heating_cost(
    account_id: str,
    heating_cost_id: str,
    body: HeatingCostVoid,
    session: PathAccountSession,
) -> HeatingCostOut:
    del account_id
    require_owner(session)
    row = session.get(HeatingCostEntry, heating_cost_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Heizkostenposition nicht gefunden")
    require_resource_building(session, row.building_id)
    if row.voided_at is not None:
        raise HTTPException(status_code=422, detail="Position ist bereits storniert")
    row.voided_at = datetime.now(UTC)
    row.void_reason = body.reason
    session.flush()
    return _heating_cost_out(row)


def _mode_out(row: HeatingBillingModeVersion) -> HeatingBillingModeOut:
    return HeatingBillingModeOut(
        id=row.id,
        building_id=row.building_id,
        period_from=row.period_from,
        period_to=row.period_to,
        version=row.version,
        mode=row.mode,
        provider_name=row.provider_name,
        provider_reference=row.provider_reference,
        external_status=row.external_status,
        mdl_statement_id=row.mdl_statement_id,
        note=row.note,
        created_at=row.created_at,
    )


@router.get("/buildings/{building_id}/heating-billing-modes")
def list_heating_billing_modes(
    account_id: str, building_id: str, session: PathAccountSession
) -> list[HeatingBillingModeOut]:
    del account_id
    require_building(session, building_id)
    rows = session.scalars(
        select(HeatingBillingModeVersion)
        .where(HeatingBillingModeVersion.building_id == building_id)
        .order_by(
            HeatingBillingModeVersion.period_from.desc(),
            HeatingBillingModeVersion.version.desc(),
        )
    ).all()
    return [_mode_out(row) for row in rows]


@router.post("/buildings/{building_id}/heating-billing-modes", status_code=201)
def create_heating_billing_mode(
    account_id: str,
    building_id: str,
    body: HeatingBillingModeCreate,
    session: PathAccountSession,
) -> HeatingBillingModeOut:
    require_owner(session)
    require_building(session, building_id)
    if body.mdl_statement_id is not None:
        mdl = session.get(MdlStatement, body.mdl_statement_id)
        if (
            mdl is None
            or mdl.building_id != building_id
            or mdl.period_from != body.period_from
            or mdl.period_to != body.period_to
        ):
            raise HTTPException(
                status_code=422,
                detail="Messdienstleister-Abrechnung passt nicht zu Objekt und Zeitraum",
            )
    latest = session.scalars(
        select(HeatingBillingModeVersion)
        .where(
            HeatingBillingModeVersion.building_id == building_id,
            HeatingBillingModeVersion.period_from == body.period_from,
            HeatingBillingModeVersion.period_to == body.period_to,
        )
        .order_by(HeatingBillingModeVersion.version.desc())
    ).first()
    if latest is not None and latest.external_status is ExternalHeatingStatus.UEBERNOMMEN:
        raise HTTPException(
            status_code=422,
            detail="Ein übernommenes Heizkostenergebnis ist versioniert und nicht überschreibbar",
        )
    row = HeatingBillingModeVersion(
        id=new_id(),
        account_id=account_id,
        building_id=building_id,
        period_from=body.period_from,
        period_to=body.period_to,
        version=1 if latest is None else latest.version + 1,
        mode=body.mode,
        provider_name=body.provider_name,
        provider_reference=body.provider_reference,
        external_status=body.external_status,
        mdl_statement_id=body.mdl_statement_id,
        note=body.note,
    )
    session.add(row)
    session.flush()
    session.refresh(row)
    return _mode_out(row)
