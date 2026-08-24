"""Owner-only UVI generation and immutable archived document retrieval."""
# ruff: noqa: B009, E501

from __future__ import annotations

import json
from dataclasses import dataclass, fields, is_dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Literal, cast

from fastapi import APIRouter, HTTPException, Response
from lokara_db import (
    BuildingUviConfiguration,
    Meter,
    MonthlyMeterReading,
    MonthlyMeterReadingSource,
    Role,
    Tenancy,
    Unit,
    UviBuildingMonthlyEvidence,
    UviBuildingMonthlyEvidenceSource,
    UviDeliveryEvent,
    UviMonthlyDegreeDay,
    UviRun,
    UviStationAssignment,
    new_id,
)
from lokara_domain import EnergyReference, MeasurementUnit, MeterKind, RuleConflict, RuleEvidence
from lokara_pdf import (
    DISCLAIMER,
    UviDocumentBlock,
    UviDocumentData,
    render_html_to_pdf,
    uvi_document_html,
)
from lokara_rules_store.rules.heizspiegel import HEIZSPIEGEL_RULES, resolve_heizspiegel_row
from lokara_uvi_engine import (
    BlockBInput,
    BlockCInput,
    BlockD2Input,
    BlockDInput,
    ComparableUnit,
    NormalizedBlockAInput,
    UviRuleBundle,
    evaluate_block_b,
    evaluate_block_c,
    evaluate_block_d,
    evaluate_block_d2,
    evaluate_normalized_block_a,
)
from pydantic import BaseModel, ConfigDict, field_validator
from pydantic.alias_generators import to_camel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..authorization import require_building, require_owner
from ..deps import PathAccountSession

router = APIRouter(prefix="/a/{account_id}/buildings/{building_id}/uvi-runs")


class _ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class UviRunCreate(_ApiModel):
    tenancy_id: str
    target_month: date

    @field_validator("target_month")
    @classmethod
    def month_starts_on_first(cls, value: date) -> date:
        if value.day != 1:
            raise ValueError("targetMonth muss der erste Tag eines Kalendermonats sein")
        return value


class UviRunCreated(_ApiModel):
    run_id: str
    document_url: str
    production_blocked: bool
    unresolved_conflicts: list[str]


@dataclass(frozen=True, slots=True)
class ConfigurationResolution:
    selected_configuration_id: str | None
    status: Literal["ready", "blocked"]
    configuration: object | None


def resolve_building_uvi_configuration(
    configurations: tuple[object, ...], target_month: date
) -> ConfigurationResolution:
    """Pick the deepest eligible successor, then apply only its valid-to bound."""

    eligible = tuple(
        row for row in configurations if cast(date, getattr(row, "valid_from")) <= target_month
    )
    if not eligible:
        return ConfigurationResolution(None, "blocked", None)
    by_id = {cast(str, getattr(row, "id")): row for row in eligible}

    def depth(row: object) -> int:
        result = 0
        seen: set[str] = set()
        parent_id = cast(str | None, getattr(row, "supersedes_configuration_id"))
        while parent_id is not None and parent_id in by_id and parent_id not in seen:
            seen.add(parent_id)
            result += 1
            parent_id = cast(str | None, getattr(by_id[parent_id], "supersedes_configuration_id"))
        return result

    selected = max(eligible, key=lambda row: (depth(row), cast(date, getattr(row, "valid_from"))))
    valid_to = cast(date | None, getattr(selected, "valid_to"))
    status: Literal["ready", "blocked"] = (
        "blocked" if valid_to is not None and target_month >= valid_to else "ready"
    )
    return ConfigurationResolution(cast(str, getattr(selected, "id")), status, selected)


def _previous_month(month: date) -> date:
    return date(month.year - 1, 12, 1) if month.month == 1 else date(month.year, month.month - 1, 1)


def _snapshot(value: object) -> object:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {field.name: _snapshot(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, dict):
        return {str(key): _snapshot(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_snapshot(item) for item in value]
    raise TypeError(f"Unsupported UVI archive value: {type(value).__name__}")


def _leaf(rows: list[object], predecessor_field: str, *, label: str) -> object | None:
    if not rows:
        return None
    superseded = {
        cast(str, predecessor)
        for row in rows
        if (predecessor := getattr(row, predecessor_field)) is not None
    }
    heads = [row for row in rows if cast(str, getattr(row, "id")) not in superseded]
    if len(heads) != 1:
        raise HTTPException(status_code=422, detail=f"{label}: keine eindeutige aktuelle Fassung.")
    return heads[0]


def _monthly_leaf(
    session: Session,
    account_id: str,
    tenancy_id: str,
    month: date,
    *,
    device_category: MeasurementUnit | None = None,
) -> tuple[MonthlyMeterReading, Meter, list[str]] | None:
    statement = (
        select(MonthlyMeterReading)
        .join(Meter, Meter.id == MonthlyMeterReading.meter_id)
        .where(
            MonthlyMeterReading.account_id == account_id,
            MonthlyMeterReading.tenancy_id == tenancy_id,
            MonthlyMeterReading.month == month,
            Meter.account_id == account_id,
            Meter.kind == MeterKind.HEAT,
        )
    )
    if device_category is not None:
        statement = statement.where(Meter.measurement_unit == device_category)
    rows = list(session.scalars(statement))
    leaf = cast(
        MonthlyMeterReading | None,
        _leaf(cast(list[object], rows), "supersedes_reading_id", label="Monatsablesung"),
    )
    if leaf is None:
        return None
    meter = session.get(Meter, leaf.meter_id)
    if meter is None:
        raise HTTPException(status_code=422, detail="Zähler zur Monatsablesung fehlt.")
    raw_ids = list(
        session.scalars(
            select(MonthlyMeterReadingSource.meter_reading_id)
            .where(MonthlyMeterReadingSource.monthly_meter_reading_id == leaf.id)
            .order_by(MonthlyMeterReadingSource.meter_reading_id)
        )
    )
    if not raw_ids:
        raise HTTPException(status_code=422, detail="Quellablesungen zur Monatsablesung fehlen.")
    return leaf, meter, raw_ids


def _degree_leaf(
    session: Session, account_id: str, postal_code: str, month: date
) -> tuple[UviStationAssignment, UviMonthlyDegreeDay] | None:
    assignment = session.scalar(
        select(UviStationAssignment).where(
            UviStationAssignment.account_id == account_id,
            UviStationAssignment.postal_code == postal_code,
            UviStationAssignment.month == month,
        )
    )
    if assignment is None:
        return None
    rows = list(
        session.scalars(
            select(UviMonthlyDegreeDay).where(
                UviMonthlyDegreeDay.account_id == account_id,
                UviMonthlyDegreeDay.station_assignment_id == assignment.id,
            )
        )
    )
    leaf = cast(
        UviMonthlyDegreeDay | None,
        _leaf(cast(list[object], rows), "supersedes_degree_day_id", label="Gradtagszahl"),
    )
    return None if leaf is None else (assignment, leaf)


def _building_evidence_leaf(
    session: Session, account_id: str, building_id: str, month: date
) -> UviBuildingMonthlyEvidence | None:
    rows = list(
        session.scalars(
            select(UviBuildingMonthlyEvidence).where(
                UviBuildingMonthlyEvidence.account_id == account_id,
                UviBuildingMonthlyEvidence.building_id == building_id,
                UviBuildingMonthlyEvidence.month == month,
            )
        )
    )
    return cast(
        UviBuildingMonthlyEvidence | None,
        _leaf(cast(list[object], rows), "supersedes_evidence_id", label="Gebäudenachweis"),
    )


def _rule_bundle(configuration: BuildingUviConfiguration) -> UviRuleBundle:
    evidence = RuleEvidence(
        source=configuration.source_id,
        register_row=configuration.source_type,
        legal_basis="§ 6a HeizkostenV",
        rechtsstand=configuration.rechtsstand,
        verification_status=configuration.verification_status,
    )
    conflicts = (
        RuleConflict(
            code="uvi_plz_geodataset_unresolved",
            description="Der PLZ-Geodatensatz ist nicht gewählt.",
            production_blocking=True,
            applies_to_media=("uvi",),
        ),
        RuleConflict(
            code="uvi_register_rows_missing",
            description="Drei UVI-Registerzeilen fehlen.",
            production_blocking=True,
            applies_to_media=("uvi",),
        ),
    )
    return UviRuleBundle(evidence=(evidence,), unresolved_conflicts=conflicts)


def _configuration_snapshot(configuration: BuildingUviConfiguration) -> dict[str, object]:
    return {
        "id": configuration.id,
        "energy_source": configuration.energy_source,
        "energy_reference": configuration.energy_reference,
        "explicit_hkv_allocator": configuration.explicit_hkv_allocator,
        "calorific_factor": (
            None if configuration.calorific_factor is None else str(configuration.calorific_factor)
        ),
        "valid_from": configuration.valid_from.isoformat(),
        "valid_to": None if configuration.valid_to is None else configuration.valid_to.isoformat(),
        "source_type": configuration.source_type,
        "source_id": configuration.source_id,
        "rechtsstand": configuration.rechtsstand,
        "verification_status": configuration.verification_status,
        "supersedes_configuration_id": configuration.supersedes_configuration_id,
    }


def _building_evidence_snapshot(
    session: Session,
    account_id: str,
    building_evidence: UviBuildingMonthlyEvidence | None,
) -> dict[str, object]:
    if building_evidence is None:
        return {
            "id": None,
            "measured_building_heat_kwh_x1000": None,
            "building_hkv_movement_x1000": None,
        }
    source_links = list(
        session.scalars(
            select(UviBuildingMonthlyEvidenceSource)
            .where(
                UviBuildingMonthlyEvidenceSource.account_id == account_id,
                UviBuildingMonthlyEvidenceSource.building_monthly_evidence_id
                == building_evidence.id,
            )
            .order_by(UviBuildingMonthlyEvidenceSource.id)
        )
    )
    return {
        "id": building_evidence.id,
        "main_meter_id": building_evidence.main_meter_id,
        "month": building_evidence.month.isoformat(),
        "measured_building_heat_kwh_x1000": building_evidence.measured_building_heat_kwh_x1000,
        "building_hkv_movement_x1000": building_evidence.building_hkv_movement_x1000,
        "source_type": building_evidence.source_type,
        "source_id": building_evidence.source_id,
        "raw_evidence": building_evidence.raw_evidence,
        "source_links": [
            {"id": link.id, "meter_reading_id": link.meter_reading_id} for link in source_links
        ],
        "supersedes_evidence_id": building_evidence.supersedes_evidence_id,
    }


def _size_class(area_sqm: Decimal) -> str:
    if area_sqm <= Decimal(150):
        return "80-150"
    if area_sqm <= Decimal(250):
        return "150-250"
    if area_sqm <= Decimal(500):
        return "250-500"
    return "ueber-500"


def _decimal_text(value: Decimal) -> str:
    rendered = format(value, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def _decimal_text_de(value: Decimal) -> str:
    return _decimal_text(value).replace(".", ",")


def _canonical_run_hash(session: Session, payload: dict[str, object]) -> str:
    result = session.scalar(
        text(
            """SELECT encode(digest(convert_to(jsonb_build_object(
              'tenancy_id', CAST(:tenancy_id AS text), 'unit_id', CAST(:unit_id AS text),
              'month', to_jsonb(CAST(:month AS date)),
              'inputs', CAST(:inputs AS jsonb), 'results', CAST(:results AS jsonb),
              'heizspiegel_vintage', CAST(:heizspiegel_vintage AS text),
              'source_type', CAST(:source_type AS text), 'source_id', CAST(:source_id AS text),
              'station_assignment_id', CAST(:station_assignment_id AS text),
              'station_id', CAST(:station_id AS text),
              'station_distance_km', to_jsonb(CAST(:station_distance_km AS numeric))
            )::text, 'UTF8'), 'sha256'), 'hex')"""
        ),
        {
            **payload,
            "inputs": json.dumps(payload["inputs"], ensure_ascii=False, separators=(",", ":")),
            "results": json.dumps(payload["results"], ensure_ascii=False, separators=(",", ":")),
            "station_distance_km": (
                None
                if payload["station_distance_km"] is None
                else str(payload["station_distance_km"])
            ),
        },
    )
    if not isinstance(result, str):
        raise RuntimeError("Die Datenbank konnte den UVI-Prüfwert nicht bilden.")
    return result


def _document_block(
    *,
    heading: str,
    status: str,
    value: int | None,
    reference: int | None,
    delta: int | None,
    percent: Decimal | None,
    label: str | None = None,
    basis: str | None = None,
    attribution: str | None = None,
    provenance: tuple[str, ...] = (),
    flag: str | None = None,
) -> UviDocumentBlock:
    return UviDocumentBlock(
        heading_de=heading,
        status=status,
        value_kwh=value,
        reference_kwh=reference,
        delta_kwh=delta,
        percent=percent,
        label_de=label,
        basis_de=basis,
        attribution_de=attribution,
        provenance_de=provenance,
        data_quality_flag=flag,
    )


@router.post(
    "",
    status_code=201,
    response_model=UviRunCreated,
    responses={
        403: {"description": "Nicht berechtigt"},
        404: {"description": "Nicht gefunden"},
        422: {"description": "UVI-Eingaben unvollständig"},
    },
)
def create_uvi_run(
    account_id: str,
    building_id: str,
    body: UviRunCreate,
    session: PathAccountSession,
) -> UviRunCreated:
    # Keep the owner rejection first even for a directly invoked endpoint in a
    # focused boundary test; normal requests are then checked by the shared helper.
    scope = session.info.get("portal_scope")
    if getattr(scope, "role", None) is not None and getattr(scope, "role") is not Role.OWNER:
        raise HTTPException(status_code=403, detail="Nur Eigentümer dürfen eine UVI erzeugen.")
    require_owner(session)
    building = require_building(session, building_id)
    tenancy = session.scalar(
        select(Tenancy)
        .join(Unit)
        .where(
            Tenancy.account_id == account_id,
            Unit.account_id == account_id,
            Tenancy.id == body.tenancy_id,
            Unit.building_id == building_id,
        )
    )
    if tenancy is None:
        raise HTTPException(status_code=404, detail="Mietverhältnis nicht gefunden.")
    unit = session.get(Unit, tenancy.unit_id)
    if unit is None or unit.building_id != building_id:
        raise HTTPException(status_code=404, detail="Mietverhältnis nicht gefunden.")

    configurations = tuple(
        session.scalars(
            select(BuildingUviConfiguration).where(
                BuildingUviConfiguration.account_id == account_id,
                BuildingUviConfiguration.building_id == building_id,
            )
        )
    )
    months = {
        "target": body.target_month,
        "previous": _previous_month(body.target_month),
        "prior_year": date(body.target_month.year - 1, body.target_month.month, 1),
    }
    configuration_resolutions = {
        name: resolve_building_uvi_configuration(cast(tuple[object, ...], configurations), month)
        for name, month in months.items()
    }
    target_resolution = configuration_resolutions["target"]
    if target_resolution.status != "ready" or not isinstance(
        target_resolution.configuration, BuildingUviConfiguration
    ):
        raise HTTPException(
            status_code=422, detail="Für diesen Monat fehlt eine gültige UVI-Gebäudekonfiguration."
        )
    configuration = target_resolution.configuration

    target_reading_bundle = _monthly_leaf(session, account_id, tenancy.id, body.target_month)
    if target_reading_bundle is None:
        raise HTTPException(status_code=422, detail="Die Monatsablesung für den Zielmonat fehlt.")
    target_reading, target_meter, target_raw = target_reading_bundle
    device_category = target_meter.measurement_unit
    readings = {
        "target": target_reading_bundle,
        "previous": _monthly_leaf(
            session,
            account_id,
            tenancy.id,
            months["previous"],
            device_category=device_category,
        ),
        "prior_year": _monthly_leaf(
            session,
            account_id,
            tenancy.id,
            months["prior_year"],
            device_category=device_category,
        ),
    }
    month_configurations: dict[str, BuildingUviConfiguration | None] = {}
    for name, reading in readings.items():
        resolution = configuration_resolutions[name]
        resolved = resolution.configuration
        if reading is not None and (
            resolution.status != "ready" or not isinstance(resolved, BuildingUviConfiguration)
        ):
            raise HTTPException(
                status_code=422,
                detail="Für eine Vergleichsablesung fehlt die gültige UVI-Gebäudekonfiguration.",
            )
        month_configurations[name] = (
            resolved if isinstance(resolved, BuildingUviConfiguration) else None
        )

    degrees = {
        "target": _degree_leaf(session, account_id, building.postal_code, months["target"]),
        "prior_year": _degree_leaf(session, account_id, building.postal_code, months["prior_year"]),
    }
    target_assignment = None if degrees["target"] is None else degrees["target"][0]
    target_degree = None if degrees["target"] is None else degrees["target"][1]
    prior_assignment = None if degrees["prior_year"] is None else degrees["prior_year"][0]
    prior_degree = None if degrees["prior_year"] is None else degrees["prior_year"][1]

    building_evidences = {
        name: _building_evidence_leaf(session, account_id, building_id, month)
        for name, month in months.items()
    }
    building_evidence = building_evidences["target"]
    rules = _rule_bundle(configuration)
    block_a = evaluate_normalized_block_a(
        NormalizedBlockAInput(
            monthly_movement_x1000=target_reading.consumption_x1000,
            measurement_unit=target_meter.measurement_unit,
            energy_reference=EnergyReference(configuration.energy_reference),
            calorific_factor_kwh_per_unit=configuration.calorific_factor,
            explicit_hkv_allocator=configuration.explicit_hkv_allocator,
            measured_building_heat_kwh_x1000=(
                None
                if building_evidence is None
                else building_evidence.measured_building_heat_kwh_x1000
            ),
            building_hkv_movement_x1000=(
                None if building_evidence is None else building_evidence.building_hkv_movement_x1000
            ),
        ),
        rules,
    )
    if block_a.status != "ready" or block_a.heat_kwh is None:
        raise HTTPException(
            status_code=422,
            detail="Block A kann mit den hinterlegten Nachweisen nicht berechnet werden.",
        )

    computed_heat: dict[str, int | None] = {"target": block_a.heat_kwh}
    for name in ("previous", "prior_year"):
        archived_reading = readings[name]
        if archived_reading is None:
            computed_heat[name] = None
            continue
        row, meter, _raw = archived_reading
        month_configuration = month_configurations[name]
        if month_configuration is None:
            raise HTTPException(
                status_code=422,
                detail="Für eine Vergleichsablesung fehlt die gültige UVI-Gebäudekonfiguration.",
            )
        month_evidence = building_evidences[name]
        result = evaluate_normalized_block_a(
            NormalizedBlockAInput(
                monthly_movement_x1000=row.consumption_x1000,
                measurement_unit=meter.measurement_unit,
                energy_reference=EnergyReference(month_configuration.energy_reference),
                calorific_factor_kwh_per_unit=month_configuration.calorific_factor,
                explicit_hkv_allocator=month_configuration.explicit_hkv_allocator,
                measured_building_heat_kwh_x1000=(
                    None
                    if month_evidence is None
                    else month_evidence.measured_building_heat_kwh_x1000
                ),
                building_hkv_movement_x1000=(
                    None if month_evidence is None else month_evidence.building_hkv_movement_x1000
                ),
            ),
            _rule_bundle(month_configuration),
        )
        if result.status != "ready" or result.heat_kwh is None:
            raise HTTPException(
                status_code=422,
                detail="Eine Vergleichsablesung kann nicht in kWh umgerechnet werden.",
            )
        computed_heat[name] = result.heat_kwh

    block_b = evaluate_block_b(BlockBInput(block_a.heat_kwh, computed_heat["previous"]), rules)
    target_comparable = ComparableUnit(
        unit.id,
        Decimal(unit.area_sqm_x100) / Decimal(100),
        block_a.heat_kwh,
        target_meter.measurement_unit.value,
    )
    building_month_rows = list(
        session.scalars(
            select(MonthlyMeterReading)
            .join(Unit, Unit.id == MonthlyMeterReading.unit_id)
            .join(Meter, Meter.id == MonthlyMeterReading.meter_id)
            .where(
                Unit.building_id == building_id,
                Unit.account_id == account_id,
                MonthlyMeterReading.account_id == account_id,
                MonthlyMeterReading.month == body.target_month,
                MonthlyMeterReading.unit_id != unit.id,
                Meter.account_id == account_id,
                Meter.kind == MeterKind.HEAT,
                Meter.measurement_unit == device_category,
            )
        )
    )
    grouped_rows: dict[str, list[MonthlyMeterReading]] = {}
    for row in building_month_rows:
        grouped_rows.setdefault(row.unit_id, []).append(row)
    other_units: list[ComparableUnit] = []
    comparable_snapshots: list[dict[str, object]] = []
    for other_unit_id, rows in grouped_rows.items():
        current_rows = [
            row
            for row in rows
            if row.id
            not in {
                candidate.supersedes_reading_id
                for candidate in rows
                if candidate.supersedes_reading_id
            }
        ]
        if len(current_rows) != 1:
            continue
        other_row = current_rows[0]
        other_meter = session.get(Meter, other_row.meter_id)
        other_unit = session.get(Unit, other_unit_id)
        if other_meter is None or other_unit is None:
            continue
        other_result = evaluate_normalized_block_a(
            NormalizedBlockAInput(
                monthly_movement_x1000=other_row.consumption_x1000,
                measurement_unit=other_meter.measurement_unit,
                energy_reference=EnergyReference(configuration.energy_reference),
                calorific_factor_kwh_per_unit=configuration.calorific_factor,
                explicit_hkv_allocator=configuration.explicit_hkv_allocator,
                measured_building_heat_kwh_x1000=(
                    None
                    if building_evidence is None
                    else building_evidence.measured_building_heat_kwh_x1000
                ),
                building_hkv_movement_x1000=(
                    None
                    if building_evidence is None
                    else building_evidence.building_hkv_movement_x1000
                ),
            ),
            rules,
        )
        raw_ids = list(
            session.scalars(
                select(MonthlyMeterReadingSource.meter_reading_id)
                .where(MonthlyMeterReadingSource.monthly_meter_reading_id == other_row.id)
                .order_by(MonthlyMeterReadingSource.meter_reading_id)
            )
        )
        if not raw_ids:
            continue
        other_units.append(
            ComparableUnit(
                other_unit.id,
                Decimal(other_unit.area_sqm_x100) / Decimal(100),
                other_result.heat_kwh if other_result.status == "ready" else None,
                other_meter.measurement_unit.value,
            )
        )
        comparable_snapshots.append(
            {
                "unit_id": other_unit.id,
                "area_sqm_x100": other_unit.area_sqm_x100,
                "monthly_reading_id": other_row.id,
                "meter_id": other_meter.id,
                "meter_kind": other_meter.kind.value,
                "measurement_unit": other_meter.measurement_unit.value,
                "raw_reading_ids": raw_ids,
                "computed_heat_kwh": other_result.heat_kwh,
            }
        )
    block_d = evaluate_block_d(BlockDInput(target_comparable, tuple(other_units), 3), rules)
    block_c = evaluate_block_c(
        BlockCInput(
            current_heat_kwh=block_a.heat_kwh,
            previous_year_heat_kwh=computed_heat["prior_year"],
            monthly_degree_days_current=(
                None if target_degree is None else target_degree.monthly_degree_days
            ),
            monthly_degree_days_previous_year=(
                None if prior_degree is None else prior_degree.monthly_degree_days
            ),
            previous_year_interpolation_notice_de=None,
            station_id=None if target_assignment is None else target_assignment.station_id,
            distance_km=None if target_assignment is None else target_assignment.distance_km,
            dataset_attribution_de=(
                None if target_degree is None else "Quelle: Deutscher Wetterdienst"
            ),
            dataset_as_of=None if target_degree is None else target_degree.rechtsstand,
        ),
        rules,
    )

    resolved_heizspiegel = None
    block_d2 = None
    if block_d.status == "use_d2":
        if target_degree is None:
            raise HTTPException(
                status_code=422, detail="Die monatliche Gradtagszahl für den Zielmonat fehlt."
            )
        if target_degree.monthly_annual_share is None:
            raise HTTPException(
                status_code=422,
                detail="Der belegte Monatsanteil der Jahres-Gradtagszahl fehlt.",
            )
        area_rows = list(
            session.scalars(
                select(Unit.area_sqm_x100).where(
                    Unit.account_id == account_id, Unit.building_id == building_id
                )
            )
        )
        resolved_heizspiegel = resolve_heizspiegel_row(
            HEIZSPIEGEL_RULES,
            as_of=body.target_month,
            energy_source=configuration.energy_source,
            requested_size_class=_size_class(Decimal(sum(area_rows)) / Decimal(100)),
        )
        block_d2 = evaluate_block_d2(
            BlockD2Input(
                current_heat_kwh=block_a.heat_kwh,
                target_area_sqm=Decimal(unit.area_sqm_x100) / Decimal(100),
                monthly_degree_day_share=target_degree.monthly_annual_share,
                resolved_row=resolved_heizspiegel,
            ),
            rules,
        )

    conflict_descriptions = tuple(conflict.description for conflict in rules.unresolved_conflicts)
    weather_provenance: list[str] = []
    for label, assignment, degree in (
        ("Zielmonat", target_assignment, target_degree),
        ("Vorjahresmonat", prior_assignment, prior_degree),
    ):
        if assignment is not None and degree is not None:
            weather_provenance.append(
                f"{label} {degree.month:%m/%Y}: "
                f"{_decimal_text_de(degree.monthly_degree_days)} Kd · "
                f"Station {assignment.station_id} · "
                f"{_decimal_text_de(assignment.distance_km)} km · "
                f"Quelldatei {degree.source_file} · Quellen-ID {degree.source_id} · "
                f"Stationszuordnung {assignment.id} · "
                f"Stationsquelle {assignment.source_type}: {assignment.source_id}"
            )
    d_document = _document_block(
        heading="Block D — Durchschnittsnutzer",
        status=block_d.status,
        value=block_a.heat_kwh,
        reference=block_d.expected_target_kwh,
        delta=block_d.delta_kwh,
        percent=block_d.percent,
        basis=block_d.basis_de,
        flag=block_d.data_quality_flag,
    )
    if block_d.status == "use_d2" and block_d2 is not None and target_degree is not None:
        d_document = _document_block(
            heading="Block D2 — Durchschnittsnutzer",
            status=block_d2.status,
            value=block_a.heat_kwh,
            reference=block_d2.norm_month_kwh,
            delta=block_d2.delta_kwh,
            percent=block_d2.percent,
            label=block_d2.label_de or block_d2.fallback_label_de,
            basis=block_d2.basis_de,
            attribution=block_d2.attribution_de,
            provenance=tuple(
                value
                for value in (
                    f"Heizspiegel {block_d2.heizspiegel_vintage.replace('/billing-year-', ' · Abrechnungsjahr ')}",
                    block_d2.fallback_label_de,
                    (
                        "Monatsanteil der Jahres-Gradtagszahl: "
                        f"{_decimal_text_de(cast(Decimal, target_degree.monthly_annual_share))} · "
                        "Quelle: Deutscher Wetterdienst · "
                        f"Quelldatei {target_degree.source_file} · "
                        f"Quellen-ID {target_degree.source_id}"
                    ),
                )
                if value is not None
            ),
            flag=block_d2.data_quality_flag,
        )
    document = UviDocumentData(
        title_de="Monatliche Verbrauchsinformation",
        target_month=body.target_month,
        unit_label=unit.label,
        block_a=_document_block(
            heading="Block A — Monatsverbrauch",
            status=block_a.status,
            value=block_a.heat_kwh,
            reference=None,
            delta=None,
            percent=None,
            label=block_a.label_de,
            provenance=(
                *tuple(f"Quellablesung {reading_id}" for reading_id in target_raw),
                *(
                    ("linear nach verstrichenen Tagen interpoliert",)
                    if target_reading.interpolation_method == "linear_by_elapsed_days"
                    else ()
                ),
            ),
            flag=block_a.data_quality_flag,
        ),
        block_b=_document_block(
            heading="Block B — Vergleich zum Vormonat",
            status=block_b.status,
            value=block_a.heat_kwh,
            reference=computed_heat["previous"],
            delta=block_b.delta_kwh,
            percent=block_b.percent,
            label=block_b.label_de,
        ),
        block_c=_document_block(
            heading="Block C — Vorjahresmonat",
            status=block_c.status,
            value=block_a.heat_kwh,
            reference=block_c.reference_kwh,
            delta=block_c.delta_kwh,
            percent=block_c.percent,
            label=block_c.label_de,
            attribution=block_c.attribution_de,
            provenance=tuple(weather_provenance),
        ),
        block_d_or_d2=d_document,
        legal_risks_de=(),
        unresolved_conflicts_de=conflict_descriptions,
        rechtsstand=configuration.rechtsstand,
        disclaimer=DISCLAIMER,
    )

    degree_day_rows = {
        name: (
            None
            if degree is None
            else {
                "id": degree.id,
                "station_assignment_id": degree.station_assignment_id,
                "station_id": degree.station_id,
                "month": degree.month.isoformat(),
                "monthly_degree_days": _decimal_text(degree.monthly_degree_days),
                "valid_day_count": degree.valid_day_count,
                "monthly_annual_share": (
                    None
                    if degree.monthly_annual_share is None
                    else _decimal_text(degree.monthly_annual_share)
                ),
                "source_file": degree.source_file,
                "source_id": degree.source_id,
                "provenance": degree.provenance,
                "rechtsstand": degree.rechtsstand,
                "verification_status": degree.verification_status,
            }
        )
        for name, degree in (("target", target_degree), ("prior_year", prior_degree))
    }
    normalized_block_inputs: dict[str, object] = {
        "block_a": {
            "monthly_movement_x1000": target_reading.consumption_x1000,
            "measurement_unit": target_meter.measurement_unit.value,
            "energy_reference": configuration.energy_reference,
            "calorific_factor": (
                None
                if configuration.calorific_factor is None
                else str(configuration.calorific_factor)
            ),
            "explicit_hkv_allocator": configuration.explicit_hkv_allocator,
            "measured_building_heat_kwh_x1000": (
                None
                if building_evidence is None
                else building_evidence.measured_building_heat_kwh_x1000
            ),
            "building_hkv_movement_x1000": (
                None if building_evidence is None else building_evidence.building_hkv_movement_x1000
            ),
        },
        "block_b": {
            "current_heat_kwh": block_a.heat_kwh,
            "previous_heat_kwh": computed_heat["previous"],
        },
        "block_c": {
            "current_heat_kwh": block_a.heat_kwh,
            "prior_year_heat_kwh": computed_heat["prior_year"],
            "target_degree_day_id": None if target_degree is None else target_degree.id,
            "prior_year_degree_day_id": None if prior_degree is None else prior_degree.id,
            "target_degree_days": (
                None if target_degree is None else _decimal_text(target_degree.monthly_degree_days)
            ),
            "prior_year_degree_days": (
                None if prior_degree is None else _decimal_text(prior_degree.monthly_degree_days)
            ),
        },
        "block_d": {
            "target_area_sqm_x100": unit.area_sqm_x100,
            "target_heat_kwh": block_a.heat_kwh,
            "comparable_reading_ids": [
                snapshot["monthly_reading_id"] for snapshot in comparable_snapshots
            ],
            "minimum_valid_units_including_target": 3,
        },
    }
    if (
        block_d.status == "use_d2"
        and target_degree is not None
        and resolved_heizspiegel is not None
    ):
        normalized_block_inputs["block_d2"] = {
            "configuration_id": configuration.id,
            "degree_day_id": target_degree.id,
            "target_area_sqm_x100": unit.area_sqm_x100,
            "current_heat_kwh": block_a.heat_kwh,
            "monthly_annual_share": _decimal_text(
                cast(Decimal, target_degree.monthly_annual_share)
            ),
            "heizspiegel_mittel_kwh_m2a": int(resolved_heizspiegel.heizspiegel_mittel_kwh_m2a),
            "warm_water_deduction_kwh_m2a": int(resolved_heizspiegel.warm_water_deduction_kwh_m2a),
        }

    normalized_months: dict[str, object] = {}
    for name, reading in readings.items():
        month_configuration = month_configurations[name]
        month_evidence = building_evidences[name]
        if reading is None:
            normalized_months[name] = {
                "monthly_reading_id": None,
                "monthly_movement_x1000": None,
                "raw_reading_ids": [],
                "meter": None,
                "building_configuration_id": (
                    None if month_configuration is None else month_configuration.id
                ),
                "building_configuration": (
                    None
                    if month_configuration is None
                    else _configuration_snapshot(month_configuration)
                ),
                "building_monthly_evidence": _building_evidence_snapshot(
                    session, account_id, month_evidence
                ),
                "computed_heat_kwh": None,
            }
            continue
        month_reading, month_meter, month_raw = reading
        normalized_months[name] = {
            "monthly_reading_id": month_reading.id,
            "monthly_movement_x1000": month_reading.consumption_x1000,
            "raw_reading_ids": month_raw,
            "meter": {
                "id": month_meter.id,
                "kind": month_meter.kind.value,
                "measurement_unit": month_meter.measurement_unit.value,
            },
            "building_configuration_id": (
                None if month_configuration is None else month_configuration.id
            ),
            "building_configuration": (
                None
                if month_configuration is None
                else _configuration_snapshot(month_configuration)
            ),
            "building_monthly_evidence": _building_evidence_snapshot(
                session, account_id, month_evidence
            ),
            "computed_heat_kwh": computed_heat[name],
        }

    inputs = {
        "monthly_movements_x1000": {
            name: None if value is None else value[0].consumption_x1000
            for name, value in readings.items()
        },
        "monthly_reading_ids": {
            name: None if value is None else value[0].id for name, value in readings.items()
        },
        "raw_reading_ids": {
            name: [] if value is None else value[2] for name, value in readings.items()
        },
        "degree_days": {
            "target": (
                None if target_degree is None else _decimal_text(target_degree.monthly_degree_days)
            ),
            "prior_year": (
                None if prior_degree is None else _decimal_text(prior_degree.monthly_degree_days)
            ),
            "target_annual_share": (
                None
                if target_degree is None or target_degree.monthly_annual_share is None
                else _decimal_text(target_degree.monthly_annual_share)
            ),
        },
        "building_configuration_id": configuration.id,
        "building_configuration": {
            "energy_source": configuration.energy_source,
            "energy_reference": configuration.energy_reference,
            "explicit_hkv_allocator": configuration.explicit_hkv_allocator,
            "calorific_factor": None
            if configuration.calorific_factor is None
            else str(configuration.calorific_factor),
            "source_type": configuration.source_type,
            "source_id": configuration.source_id,
            "rechtsstand": configuration.rechtsstand,
            "verification_status": configuration.verification_status,
        },
        "station_assignment_ids": {
            "target": None if target_assignment is None else target_assignment.id,
            "prior_year": None if prior_assignment is None else prior_assignment.id,
        },
        "station_assignments": {
            name: (
                None
                if assignment is None
                else {
                    "id": assignment.id,
                    "station_id": assignment.station_id,
                    "distance_km": _decimal_text(assignment.distance_km),
                    "source_type": assignment.source_type,
                    "source_id": assignment.source_id,
                }
            )
            for name, assignment in (
                ("target", target_assignment),
                ("prior_year", prior_assignment),
            )
        },
        "target_unit": {"unit_id": unit.id, "area_sqm_x100": unit.area_sqm_x100},
        "target_meter": {
            "meter_id": target_meter.id,
            "kind": target_meter.kind.value,
            "measurement_unit": target_meter.measurement_unit.value,
        },
        "comparables": comparable_snapshots,
        "degree_day_rows": degree_day_rows,
        "normalized_block_inputs": normalized_block_inputs,
        "normalized_months": normalized_months,
        "building_monthly_evidence_ids": {
            name: None if evidence is None else evidence.id
            for name, evidence in building_evidences.items()
        },
    }
    if resolved_heizspiegel is not None:
        inputs["resolved_u2"] = {
            "configuration_id": configuration.id,
            "energy_source": configuration.energy_source,
            "energy_reference": configuration.energy_reference,
            "source_type": configuration.source_type,
            "source_id": configuration.source_id,
            "heizspiegel_vintage": resolved_heizspiegel.heizspiegel_vintage,
            "size_class": resolved_heizspiegel.actual_size_class,
            "heizspiegel_row": {
                "middle_kwh_m2a": int(resolved_heizspiegel.heizspiegel_mittel_kwh_m2a),
                "warm_water_deduction_kwh_m2a": int(
                    resolved_heizspiegel.warm_water_deduction_kwh_m2a
                ),
                "source": "heizspiegel.de/heizkosten-pruefen/methodik-heizspiegel",
                "rechtsstand": "09/2025",
                "verification_status": "verify-before-production",
            },
        }

    evidence: list[RuleEvidence] = list(rules.evidence)
    for degree in (target_degree, prior_degree):
        if degree is not None:
            evidence.append(
                RuleEvidence(
                    source=degree.source_id,
                    register_row=degree.source_file,
                    legal_basis="§ 6a HeizkostenV · DWD hdd_3807",
                    rechtsstand=degree.rechtsstand,
                    verification_status=degree.verification_status,
                )
            )
    if target_assignment is not None:
        evidence.append(
            RuleEvidence(
                source=target_assignment.source_id,
                register_row=target_assignment.source_type,
                legal_basis="Persistierte Stationszuordnung",
                rechtsstand=configuration.rechtsstand,
                verification_status="verify-before-production",
            )
        )
    if resolved_heizspiegel is not None:
        evidence.extend(resolved_heizspiegel.evidence)
        evidence.append(
            RuleEvidence(
                source="heizspiegel.de/heizkosten-pruefen/methodik-heizspiegel",
                register_row="K13",
                legal_basis="§ 6a Abs. 2 Nr. 3 HeizkostenV",
                rechtsstand="07/2026",
                verification_status="verify-before-production",
            )
        )

    block_d2_snapshot: object = None
    if block_d2 is not None and resolved_heizspiegel is not None:
        block_d2_snapshot = {
            **cast(dict[str, object], _snapshot(block_d2)),
            "heizspiegel_mittel_kwh_m2a": int(resolved_heizspiegel.heizspiegel_mittel_kwh_m2a),
            "warm_water_deduction_kwh_m2a": int(resolved_heizspiegel.warm_water_deduction_kwh_m2a),
        }
    results = {
        "block_a": _snapshot(block_a),
        "block_b": _snapshot(block_b),
        "block_c": _snapshot(block_c),
        "block_d": _snapshot(block_d),
        "block_d2": block_d2_snapshot,
        "production_blocked": any(
            conflict.production_blocking for conflict in rules.unresolved_conflicts
        ),
        "unresolved_conflicts": _snapshot(rules.unresolved_conflicts),
        "rule_evidence": _snapshot(tuple(evidence)),
        "reduction_risks": [
            {
                "code": "hkv_12_1_s2_remote_readability_3pct",
                "status": "verify-before-production",
                "automatic_deduction": False,
            },
            {
                "code": "hkv_12_1_s3_uvi_information_3pct",
                "status": "verify-before-production",
                "automatic_deduction": False,
            },
        ],
        "document": _snapshot(document),
    }
    station_assignment_id = None if target_assignment is None else target_assignment.id
    station_id = None if target_assignment is None else target_assignment.station_id
    station_distance_km = None if target_assignment is None else target_assignment.distance_km
    payload: dict[str, object] = {
        "tenancy_id": tenancy.id,
        "unit_id": unit.id,
        "month": body.target_month,
        "inputs": inputs,
        "results": results,
        "heizspiegel_vintage": (
            None if resolved_heizspiegel is None else resolved_heizspiegel.heizspiegel_vintage
        ),
        "source_type": (
            configuration.source_type
            if target_assignment is None
            else target_assignment.source_type
        ),
        "source_id": (
            configuration.source_id if target_assignment is None else target_assignment.source_id
        ),
        "station_assignment_id": station_assignment_id,
        "station_id": station_id,
        "station_distance_km": station_distance_km,
    }
    run_id = new_id()
    run = UviRun(
        id=run_id, account_id=account_id, sha256=_canonical_run_hash(session, payload), **payload
    )
    session.add(run)
    session.flush()
    event = UviDeliveryEvent(
        id=new_id(),
        account_id=account_id,
        uvi_run_id=run_id,
        status="GENERATED",
        occurred_at=datetime.now(UTC),
    )
    session.add(event)
    session.flush()
    return UviRunCreated(
        run_id=run_id,
        document_url=f"/a/{account_id}/buildings/{building_id}/uvi-runs/{run_id}/document",
        production_blocked=cast(bool, results["production_blocked"]),
        unresolved_conflicts=list(conflict_descriptions),
    )


def _archived_document(value: object) -> UviDocumentData:
    if not isinstance(value, dict):
        raise HTTPException(
            status_code=422, detail="Das archivierte UVI-Dokument ist unvollständig."
        )
    blocks = {}
    for name in ("block_a", "block_b", "block_c", "block_d_or_d2"):
        block = value.get(name)
        if not isinstance(block, dict):
            raise HTTPException(
                status_code=422, detail="Das archivierte UVI-Dokument ist unvollständig."
            )
        values = dict(block)
        percent = values.get("percent")
        values["percent"] = None if percent is None else Decimal(cast(str, percent))
        values["provenance_de"] = tuple(cast(list[str], values["provenance_de"]))
        blocks[name] = UviDocumentBlock(**values)
    return UviDocumentData(
        title_de=cast(str, value["title_de"]),
        target_month=date.fromisoformat(cast(str, value["target_month"])),
        unit_label=cast(str, value["unit_label"]),
        **blocks,
        legal_risks_de=tuple(cast(list[str], value["legal_risks_de"])),
        unresolved_conflicts_de=tuple(cast(list[str], value["unresolved_conflicts_de"])),
        rechtsstand=cast(str, value["rechtsstand"]),
        disclaimer=cast(str, value["disclaimer"]),
    )


@router.get(
    "/{run_id}/document",
    responses={403: {"description": "Nicht berechtigt"}, 404: {"description": "Nicht gefunden"}},
)
def download_uvi_document(
    account_id: str,
    building_id: str,
    run_id: str,
    session: PathAccountSession,
) -> Response:
    del account_id
    require_owner(session)
    require_building(session, building_id)
    run = session.scalar(
        select(UviRun)
        .join(Tenancy, Tenancy.id == UviRun.tenancy_id)
        .join(Unit, Unit.id == Tenancy.unit_id)
        .where(UviRun.id == run_id, Unit.building_id == building_id, UviRun.unit_id == Unit.id)
    )
    if run is None:
        raise HTTPException(status_code=404, detail="UVI-Dokument nicht gefunden.")
    document = _archived_document(run.results.get("document"))
    pdf = render_html_to_pdf(uvi_document_html(document))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="uvi-{run.month.isoformat()}-{run.id}.pdf"',
            "X-Content-SHA256": run.sha256,
        },
    )
