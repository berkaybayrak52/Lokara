"""Unified Page 01b H0-H8 statement orchestration.

This module composes the existing pure capabilities.  It deliberately keeps
the legacy ``calculate_heating_statement`` calculation untouched as the H3-H6
compatibility core while adding the typed readiness, evidence and MDL result
that Page 01b needs end to end.
"""

from dataclasses import dataclass, replace
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from lokara_domain import Cents, Co2Table, Period, cents

from .co2 import split_co2_cost
from .device_readings import (
    DeviceReadingAggregation,
    DeviceReadingLine,
    DeviceReadingSpan,
    HeatingDevice,
    aggregate_device_reading_spans,
)
from .engine import calculate_heating_statement
from .inputs import (
    Co2Result,
    HeatingConsumptionSegment,
    HeatingInput,
    HeatingInputError,
    HeatingResult,
)
from .mdl import rescale_mdl_gross_positions
from .plant_co2 import PlantCo2Input, PlantCo2Result, assess_co2_plausibility, evaluate_plant_co2
from .self_billing import (
    DistrictHeatDisclosure,
    HeatingCostPosition,
    InvoiceAllocation,
    OilConsumptionResult,
    OilStockInput,
    OwnerBurdenPreview,
    PlantCostAggregation,
    aggregate_plant_cost_positions,
    allocate_invoice_to_billing_period,
    calculate_oil_consumption,
    calculate_owner_burden_preview,
)

Readiness = Literal["READY", "BLOCKED"]
FindingSeverity = Literal["NOTICE", "WARNING", "BLOCKER"]
MdlBranch = Literal["NET", "GROSS"]
AnnualComparisonState = Literal["READY", "RAW_FALLBACK", "NO_PRIOR"]


@dataclass(frozen=True)
class Page01bFinding:
    code: str
    message_de: str
    severity: FindingSeverity
    dismissible: bool
    field_ref: str | None = None


@dataclass(frozen=True)
class Page01bProvenance:
    code: str
    source_ref: str
    detail_de: str


@dataclass(frozen=True)
class RiskTriggers:
    remote_readability_missing: bool = False
    section_6a_information_missing: bool = False
    co2_disclosure_missing: bool = False
    consumption_billing_missing: bool = False


@dataclass(frozen=True)
class ReductionRisk:
    code: str
    percent: Decimal
    amounts: tuple[Cents, ...]
    message_de: str


@dataclass(frozen=True)
class Section12RenterReduction:
    """One renter's auditable § 12 HeizkostenV reduction calculation.

    The three components deliberately remain separate.  They are calculated
    from their own unreduced bases, so a consumer cannot accidentally cascade
    one reduction into the next.
    """

    renter_id: str
    gross_claim: Cents
    non_consumption_15_percent: Cents
    remote_readability_3_percent: Cents
    section_6a_information_3_percent: Cents
    total_deduction: Cents
    net_claim: Cents | None


@dataclass(frozen=True)
class Section12ReductionResult:
    """Separate § 12 result; it does not alter the warning-only projections."""

    renters: tuple[Section12RenterReduction, ...]
    component_definitions: tuple[str, ...]
    active_grounds: tuple[str, ...]
    warnings: tuple[str, ...]
    is_complete: bool
    incomplete_reason_de: str | None = None


@dataclass(frozen=True)
class AnnualClimateFactor:
    value: Decimal
    period_label: str
    source_label: str


@dataclass(frozen=True)
class AnnualComparisonInput:
    current_heat: Decimal
    previous_heat: Decimal | None
    current_warm_water: Decimal | None
    previous_warm_water: Decimal | None
    current_factor: AnnualClimateFactor | None = None
    previous_factor: AnnualClimateFactor | None = None


@dataclass(frozen=True)
class AnnualComparisonResult:
    state: AnnualComparisonState
    current_heat_raw: Decimal
    previous_heat_raw: Decimal | None
    current_heat_adjusted: Decimal | None
    previous_heat_adjusted: Decimal | None
    current_warm_water: Decimal | None
    previous_warm_water: Decimal | None
    raw_change_percent: Decimal | None
    adjusted_change_percent: Decimal | None
    graph_required: bool
    note_de: str | None
    current_factor: AnnualClimateFactor | None
    previous_factor: AnnualClimateFactor | None


@dataclass(frozen=True)
class InvoiceCostInput:
    """One normalized invoice position with a half-open source period."""

    kind: Literal[
        "fuel",
        "district_heat",
        "operating_electricity",
        "maintenance",
        "measurement",
        "equipment",
        "other",
    ]
    amount: Cents
    period_from: date
    period_to: date

    def __post_init__(self) -> None:
        # Avoid importing framework validation into this pure package while
        # still failing structurally on a wrong boundary type.
        if not isinstance(self.period_from, date) or not isinstance(self.period_to, date):
            raise HeatingInputError("Rechnungszeiträume müssen als Datum angegeben sein")
        if self.period_to <= self.period_from:
            raise HeatingInputError("Rechnungsende muss nach dem Rechnungsbeginn liegen")


@dataclass(frozen=True)
class MdlCo2Calculation:
    total_co2_kg: Decimal
    co2_cost: Cents
    heated_area_sqm: Decimal
    table: Co2Table
    rechtsstand: str
    billing_period: Period


@dataclass(frozen=True)
class SelfBillingStatementInput:
    heating: HeatingInput
    plant: PlantCo2Input | None = None
    invoice_costs: tuple[InvoiceCostInput, ...] = ()
    district_heat_disclosure: DistrictHeatDisclosure | None = None
    devices: tuple[HeatingDevice, ...] = ()
    device_spans: tuple[DeviceReadingSpan, ...] = ()
    segments: tuple[HeatingConsumptionSegment, ...] = ()
    risks: RiskTriggers = RiskTriggers()
    annual_comparison: AnnualComparisonInput | None = None
    owner_preview_baseline: Cents | None = None
    area_fallback_authorized: bool = False
    oil_stock: OilStockInput | None = None
    oil_heating_value_kwh_per_litre: Decimal | None = None
    oil_emission_factor_kg_per_kwh: Decimal | None = None


@dataclass(frozen=True)
class MdlStatementInput:
    branch: MdlBranch
    renter_ids: tuple[str, ...]
    renter_positions: tuple[int, ...]
    owner_position: int
    confirmed_total: int
    co2: MdlCo2Calculation | None = None
    co2_evidence_present: bool = True
    risks: RiskTriggers = RiskTriggers()
    annual_comparison: AnnualComparisonInput | None = None
    # Confirmed MDL positions do not contain the §§ 7/8 split by themselves.
    # The adapter must carry this per-renter source position rather than letting
    # the engine reconstruct it from raw supplier material.
    renter_non_consumption_positions: tuple[int, ...] | None = None


@dataclass(frozen=True)
class Page01bStatementValues:
    path: Literal["SELF_BILLING", "MDL_NET", "MDL_GROSS"]
    renter_ids: tuple[str, ...]
    renter_totals: tuple[Cents, ...]
    owner_total: Cents
    source_total: Cents
    billable_total: Cents
    co2_landlord_amount: Cents
    co2_landlord_percent: int | None
    co2_intensity: Decimal | None
    co2_mass_grams: int | None
    co2_module_enabled: bool
    ww_unmetered_owner: Cents
    heating_result: HeatingResult | None
    co2_result: Co2Result | PlantCo2Result | None


@dataclass(frozen=True)
class Page01bStatementResult:
    readiness: Readiness
    values: Page01bStatementValues | None
    findings: tuple[Page01bFinding, ...]
    provenance: tuple[Page01bProvenance, ...]
    device_evidence: tuple[DeviceReadingLine, ...]
    risks: tuple[ReductionRisk, ...]
    annual_comparison: AnnualComparisonResult | None
    cost_aggregation: PlantCostAggregation | None = None
    invoice_allocations: tuple[InvoiceAllocation, ...] = ()
    device_aggregation: DeviceReadingAggregation | None = None
    owner_burden_preview: OwnerBurdenPreview | None = None
    oil_consumption: OilConsumptionResult | None = None
    section12_reduction: Section12ReductionResult | None = None
    # Deliberately absent as an amount: the unresolved cumulation question may
    # not acquire a plausible number through a convenience property.
    risk_total: None = None


def _finding(
    code: str,
    message: str,
    severity: FindingSeverity = "WARNING",
    *,
    dismissible: bool = False,
    field_ref: str | None = None,
) -> Page01bFinding:
    return Page01bFinding(code, message, severity, dismissible, field_ref)


def _percent_change(current: Decimal, previous: Decimal) -> Decimal:
    if previous == 0:
        raise HeatingInputError(
            "Vorjahresverbrauch muss für einen Prozentvergleich größer null sein"
        )
    return ((current / previous - Decimal(1)) * Decimal(100)).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP
    )


def calculate_annual_comparison(value: AnnualComparisonInput) -> AnnualComparisonResult:
    for label, amount in (
        ("Heizverbrauch laufendes Jahr", value.current_heat),
        ("Heizverbrauch Vorjahr", value.previous_heat),
        ("Warmwasser laufendes Jahr", value.current_warm_water),
        ("Warmwasser Vorjahr", value.previous_warm_water),
    ):
        if amount is not None and (not amount.is_finite() or amount < 0):
            raise HeatingInputError(f"{label} muss endlich und nicht negativ sein")
    if value.previous_heat is None:
        return AnnualComparisonResult(
            state="NO_PRIOR",
            current_heat_raw=value.current_heat,
            previous_heat_raw=None,
            current_heat_adjusted=None,
            previous_heat_adjusted=None,
            current_warm_water=value.current_warm_water,
            previous_warm_water=value.previous_warm_water,
            raw_change_percent=None,
            adjusted_change_percent=None,
            graph_required=False,
            note_de=(
                "Kein Vorjahreswert vorhanden — statt einer Grafik wird dieser Hinweis ausgegeben."
            ),
            current_factor=value.current_factor,
            previous_factor=value.previous_factor,
        )
    raw_change = _percent_change(value.current_heat, value.previous_heat)
    if value.current_factor is None or value.previous_factor is None:
        return AnnualComparisonResult(
            state="RAW_FALLBACK",
            current_heat_raw=value.current_heat,
            previous_heat_raw=value.previous_heat,
            current_heat_adjusted=None,
            previous_heat_adjusted=None,
            current_warm_water=value.current_warm_water,
            previous_warm_water=value.previous_warm_water,
            raw_change_percent=raw_change,
            adjusted_change_percent=None,
            graph_required=True,
            note_de=(
                "DWD-Klimafaktor fehlt — Heizverbrauch wird ausdrücklich unbereinigt verglichen."
            ),
            current_factor=value.current_factor,
            previous_factor=value.previous_factor,
        )
    for factor in (value.current_factor, value.previous_factor):
        if (
            not factor.value.is_finite()
            or factor.value < Decimal("0.40")
            or factor.value > Decimal("1.80")
        ):
            raise HeatingInputError(
                "DWD-Klimafaktor muss im freigegebenen Bereich 0,40 bis 1,80 liegen"
            )
        if not factor.period_label or not factor.source_label:
            raise HeatingInputError("DWD-Klimafaktor benötigt Zeitraum und Quellenbezeichnung")
    current_adjusted = (value.current_heat * value.current_factor.value).quantize(Decimal("0.01"))
    previous_adjusted = (value.previous_heat * value.previous_factor.value).quantize(
        Decimal("0.01")
    )
    return AnnualComparisonResult(
        state="READY",
        current_heat_raw=value.current_heat,
        previous_heat_raw=value.previous_heat,
        current_heat_adjusted=current_adjusted,
        previous_heat_adjusted=previous_adjusted,
        current_warm_water=value.current_warm_water,
        previous_warm_water=value.previous_warm_water,
        raw_change_percent=raw_change,
        adjusted_change_percent=_percent_change(current_adjusted, previous_adjusted),
        graph_required=True,
        note_de=None,
        current_factor=value.current_factor,
        previous_factor=value.previous_factor,
    )


def _risk_amount(amount: Cents, percent: Decimal) -> Cents:
    return cents(
        int((Decimal(amount) * percent / Decimal(100)).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    )


_RISK_ORDER: tuple[tuple[str, Decimal, str], ...] = (
    (
        "remote_readability_missing",
        Decimal(3),
        "3-%-Risiko wegen fehlender fernablesbarer Ausstattung; kein automatischer Abzug.",
    ),
    (
        "section_6a_information_missing",
        Decimal(3),
        "3-%-Risiko wegen fehlender oder unvollständiger §-6a-Informationen; "
        "kein automatischer Abzug.",
    ),
    (
        "co2_disclosure_missing",
        Decimal(3),
        "3-%-Risiko wegen fehlender CO₂-Pflichtangaben; kein automatischer Abzug.",
    ),
    (
        "consumption_billing_missing",
        Decimal(15),
        "15-%-Risiko bei nicht verbrauchsabhängiger Abrechnung; kein automatischer Abzug.",
    ),
)


def _risks(triggers: RiskTriggers, renter_totals: tuple[Cents, ...]) -> tuple[ReductionRisk, ...]:
    active = {
        "remote_readability_missing": triggers.remote_readability_missing,
        "section_6a_information_missing": triggers.section_6a_information_missing,
        "co2_disclosure_missing": triggers.co2_disclosure_missing,
        "consumption_billing_missing": triggers.consumption_billing_missing,
    }
    return tuple(
        ReductionRisk(
            code=code,
            percent=percent,
            amounts=tuple(_risk_amount(amount, percent) for amount in renter_totals),
            message_de=message,
        )
        for code, percent, message in _RISK_ORDER
        if active[code]
    )


_SECTION12_COMPONENT_DEFINITIONS = (
    "non_consumption_15_percent",
    "remote_readability_3_percent",
    "section_6a_information_3_percent",
)
_SECTION12_WARNING = (
    "Zwei Kürzungsgründe gleichzeitig — bitte prüfen Sie, ob beide zutreffen. "
    "Die Kürzungen wirken nebeneinander."
)


def _section12_active_grounds(triggers: RiskTriggers) -> tuple[str, ...]:
    return tuple(
        code
        for code, enabled in (
            ("consumption_billing_missing", triggers.consumption_billing_missing),
            ("remote_readability_missing", triggers.remote_readability_missing),
            ("section_6a_information_missing", triggers.section_6a_information_missing),
        )
        if enabled
    )


def _section12_result(
    *,
    renter_ids: tuple[str, ...],
    gross_claims: tuple[Cents, ...],
    non_consumption_claims: tuple[Cents, ...] | None,
    triggers: RiskTriggers,
) -> Section12ReductionResult:
    """Calculate the three independent § 12 components without changing claims.

    MDL callers without an explicit split receive an incomplete audit result;
    their confirmed gross positions remain visible but no plausible net figure is
    produced.
    """

    active_grounds = _section12_active_grounds(triggers)
    warning = (_SECTION12_WARNING,) if len(active_grounds) >= 2 else ()
    if (
        non_consumption_claims is None
        or len(non_consumption_claims) != len(gross_claims)
        or any(int(amount) < 0 for amount in non_consumption_claims)
        or any(
            int(base) > int(gross)
            for base, gross in zip(non_consumption_claims, gross_claims, strict=True)
        )
    ):
        incomplete_renters = tuple(
            Section12RenterReduction(
                renter_id=renter_id,
                gross_claim=gross,
                non_consumption_15_percent=cents(0),
                remote_readability_3_percent=cents(0),
                section_6a_information_3_percent=cents(0),
                total_deduction=cents(0),
                net_claim=None,
            )
            for renter_id, gross in zip(renter_ids, gross_claims, strict=True)
        )
        return Section12ReductionResult(
            renters=incomplete_renters,
            component_definitions=_SECTION12_COMPONENT_DEFINITIONS,
            active_grounds=active_grounds,
            warnings=warning,
            is_complete=False,
            incomplete_reason_de=(
                "§-12-Kürzung unvollständig: bestätigte nichtverbrauchsabhängige "
                "Positionen je Mieter fehlen, sind ungültig oder übersteigen den Bruttoanspruch."
            ),
        )

    renters: list[Section12RenterReduction] = []
    for renter_id, gross, non_consumption in zip(
        renter_ids, gross_claims, non_consumption_claims, strict=True
    ):
        non_consumption_component = (
            _risk_amount(non_consumption, Decimal(15))
            if triggers.consumption_billing_missing
            else cents(0)
        )
        remote_component = (
            _risk_amount(gross, Decimal(3)) if triggers.remote_readability_missing else cents(0)
        )
        section_6a_component = (
            _risk_amount(gross, Decimal(3)) if triggers.section_6a_information_missing else cents(0)
        )
        independently_rounded_total = (
            int(non_consumption_component) + int(remote_component) + int(section_6a_component)
        )
        capped_total = min(independently_rounded_total, int(_risk_amount(gross, Decimal(21))))
        deduction = cents(capped_total)
        renters.append(
            Section12RenterReduction(
                renter_id=renter_id,
                gross_claim=gross,
                non_consumption_15_percent=non_consumption_component,
                remote_readability_3_percent=remote_component,
                section_6a_information_3_percent=section_6a_component,
                total_deduction=deduction,
                net_claim=cents(int(gross) - int(deduction)),
            )
        )
    return Section12ReductionResult(
        renters=tuple(renters),
        component_definitions=_SECTION12_COMPONENT_DEFINITIONS,
        active_grounds=active_grounds,
        warnings=warning,
        is_complete=True,
    )


def _block(
    finding: Page01bFinding,
    *,
    provenance: tuple[Page01bProvenance, ...] = (),
    device: DeviceReadingAggregation | None = None,
    annual: AnnualComparisonResult | None = None,
) -> Page01bStatementResult:
    return Page01bStatementResult(
        readiness="BLOCKED",
        values=None,
        findings=(finding,),
        provenance=provenance,
        device_evidence=() if device is None else device.device_lines,
        risks=(),
        annual_comparison=annual,
        device_aggregation=device,
    )


def _apply_device_input(
    value: SelfBillingStatementInput,
    heating: HeatingInput,
) -> tuple[
    HeatingInput, DeviceReadingAggregation | None, list[Page01bFinding], list[Page01bProvenance]
]:
    if bool(value.devices) != bool(value.device_spans):
        raise HeatingInputError("Geräte und Ablesesegmente müssen gemeinsam angegeben sein")
    segments = list(value.segments or heating.consumption_segments)
    if not value.devices:
        return replace(heating, consumption_segments=tuple(segments)), None, [], []
    aggregation = aggregate_device_reading_spans(devices=value.devices, spans=value.device_spans)
    device_by_id = {device.device_id: device for device in value.devices}
    grouped: dict[tuple[str, str | None], Decimal] = {}
    annual_by_unit = dict(aggregation.unsegmented_unit_units)
    for line in aggregation.device_lines:
        if line.allocation_kind == "ANNUAL_UNSEGMENTED":
            continue
        key = (line.unit_id, line.target_id if line.allocation_kind == "PARTY" else None)
        grouped[key] = grouped.get(key, Decimal(0)) + line.units
    for (unit_id, tenancy_id), amount in grouped.items():
        segments.append(
            HeatingConsumptionSegment(
                unit_id=unit_id,
                tenancy_id=tenancy_id,
                heat_consumption=amount,
            )
        )
    touched = {device.unit_id for device in value.devices}
    units = tuple(
        replace(
            unit,
            heat_consumption=(
                annual_by_unit.get(unit.unit_id)
                if unit.unit_id in touched
                else unit.heat_consumption
            ),
            heat_consumption_unit=(
                next(
                    (
                        device.measurement_unit
                        for device in value.devices
                        if device.unit_id == unit.unit_id
                    ),
                    unit.heat_consumption_unit,
                )
                if unit.unit_id in touched
                else unit.heat_consumption_unit
            ),
        )
        for unit in heating.units
    )
    findings: list[Page01bFinding] = []
    provenance: list[Page01bProvenance] = []
    for device_id in aggregation.estimated_device_ids:
        device = device_by_id[device_id]
        findings.append(
            _finding(
                "device_estimate",
                f"Gerät {device_id} wurde nach § 9a Abs. 1 HeizkostenV geschätzt.",
                "NOTICE",
            )
        )
        provenance.append(
            Page01bProvenance(
                "device_previous_period",
                device_id,
                f"Vorjahreseinheiten für {device.room} wurden als Schätzgrundlage übernommen.",
            )
        )
    for line in aggregation.device_lines:
        for source_ref in line.provenance_refs:
            provenance.append(
                Page01bProvenance(
                    "device_reading_source",
                    source_ref,
                    f"Ablese- oder Schätznachweis für Gerät {line.device_id}.",
                )
            )
    return (
        replace(heating, units=units, consumption_segments=tuple(segments)),
        aggregation,
        findings,
        provenance,
    )


def _invoice_costs(
    value: SelfBillingStatementInput,
    heating: HeatingInput,
) -> tuple[
    HeatingInput, PlantCostAggregation | None, tuple[InvoiceAllocation, ...], list[Page01bFinding]
]:
    if not value.invoice_costs:
        if value.district_heat_disclosure is not None:
            raise HeatingInputError("Fernwärmeangaben benötigen eine Fernwärme-Kostenposition")
        return heating, None, (), []
    valid_to = heating.billing_period.valid_to
    if valid_to is None:
        raise HeatingInputError("Abrechnungszeitraum muss begrenzt sein")
    allocations: list[InvoiceAllocation] = []
    positions: list[HeatingCostPosition] = []
    findings: list[Page01bFinding] = []
    for source in value.invoice_costs:
        allocation = allocate_invoice_to_billing_period(
            amount=source.amount,
            invoice_from=source.period_from,
            invoice_to=source.period_to - timedelta(days=1),
            billing_from=heating.billing_period.valid_from,
            billing_to=valid_to - timedelta(days=1),
        )
        allocations.append(allocation)
        positions.append(HeatingCostPosition(source.kind, allocation.allocated_amount))
        if allocation.warning is not None:
            findings.append(
                _finding(
                    "invoice_period_incomplete",
                    "Rechnungszeitraum deckt die Abrechnung nicht vollständig; "
                    f"{allocation.missing_days} Tage fehlen.",
                    "WARNING",
                    dismissible=False,
                )
            )
    aggregation = aggregate_plant_cost_positions(
        positions=tuple(positions),
        district_heat_disclosure=value.district_heat_disclosure,
    )
    return (
        replace(heating, total_cost=aggregation.total_cost),
        aggregation,
        tuple(allocations),
        findings,
    )


def _reading_total(heating: HeatingInput, *, heat: bool) -> tuple[Decimal, int]:
    segmented_units = {
        segment.unit_id
        for segment in heating.consumption_segments
        if (segment.heat_consumption if heat else segment.ww_consumption_m3) is not None
    }
    total = Decimal(0)
    for segment in heating.consumption_segments:
        segment_amount = segment.heat_consumption if heat else segment.ww_consumption_m3
        if segment_amount is not None:
            total += segment_amount
    missing_area = 0
    for unit in heating.units:
        if unit.unit_id in segmented_units:
            continue
        amount = unit.heat_consumption if heat else unit.ww_consumption_m3
        if amount is None:
            missing_area += unit.area_sqm_x100
        else:
            total += amount
    return total, missing_area


def _self_billing(value: SelfBillingStatementInput) -> Page01bStatementResult:
    unified_heating = replace(
        value.heating,
        round_degree_day_units=True,
        use_central_ww_denominator=True,
    )
    heating, cost_aggregation, invoice_allocations, findings = _invoice_costs(
        value, unified_heating
    )
    heating, device, device_findings, provenance = _apply_device_input(value, heating)
    findings.extend(device_findings)

    total_area = sum(unit.area_sqm_x100 for unit in heating.units)
    heat_total, heat_missing_area = _reading_total(heating, heat=True)
    if (heat_total == 0 and heat_missing_area == 0) or (
        heat_missing_area * 4 > total_area and not value.area_fallback_authorized
    ):
        return _block(
            _finding(
                "zero_heat_consumption_denominator",
                "Heizverbrauch kann nicht verteilt werden: Verbrauchsnenner ist null "
                "oder der §-9a-Ersatzweg wurde nicht bestätigt.",
                "BLOCKER",
                field_ref="heat_consumption",
            ),
            provenance=tuple(provenance),
            device=device,
            annual=(
                calculate_annual_comparison(value.annual_comparison)
                if value.annual_comparison is not None
                else None
            ),
        )

    oil: OilConsumptionResult | None = None
    if value.oil_stock is not None:
        if (
            value.oil_heating_value_kwh_per_litre is None
            or value.oil_emission_factor_kg_per_kwh is None
        ):
            raise HeatingInputError("Heizölbestand benötigt Heizwert und Emissionsfaktor")
        oil = calculate_oil_consumption(
            stock=value.oil_stock,
            heating_value_kwh_per_litre=value.oil_heating_value_kwh_per_litre,
            emission_factor_kg_per_kwh=value.oil_emission_factor_kg_per_kwh,
        )
        provenance.append(
            Page01bProvenance(
                "oil_stock_consumption",
                "Heizölbestand",
                "Verbrauch und gewichteter Brennstoffwert stammen aus Anfangsbestand, "
                "Zukäufen und Endbestand.",
            )
        )

    core: HeatingResult
    plant_result: PlantCo2Result | None = None
    source_total = heating.total_cost
    if value.plant is not None:
        co2 = heating.co2
        total_co2 = None if co2 is None else co2.total_co2_kg
        co2_cost = None if co2 is None else co2.co2_cost
        table = heating.rules.co2_table
        rechtsstand = heating.rules.co2_rechtsstand
        if table is None or rechtsstand is None:
            raise HeatingInputError("CO₂-Regeltabelle und Rechtsstand fehlen")
        plant_result = evaluate_plant_co2(
            plant=value.plant,
            total_cost=source_total,
            total_co2_kg=total_co2,
            co2_cost=co2_cost,
            heated_area_sqm=Decimal(total_area) / Decimal(100),
            table=table,
            rechtsstand=rechtsstand,
            billing_period=heating.billing_period,
        )
        core = calculate_heating_statement(
            replace(heating, total_cost=plant_result.billable_total, co2=None)
        )
        for warning in plant_result.warnings:
            findings.append(
                _finding(
                    warning.code,
                    "CO₂-Intensität liegt außerhalb des Plausibilitätsbands; "
                    "Rechnung bitte prüfen.",
                    "WARNING",
                    dismissible=True,
                )
            )
    else:
        core = calculate_heating_statement(heating)
        if core.co2 is not None:
            for warning in assess_co2_plausibility(core.co2.intensity_kg_per_sqm):
                findings.append(
                    _finding(
                        warning.code,
                        "CO₂-Intensität liegt außerhalb des Plausibilitätsbands; "
                        "Rechnung bitte prüfen.",
                        "WARNING",
                        dismissible=True,
                    )
                )

    triggers = value.risks
    if heating.co2 is not None and heating.co2.total_co2_kg is None:
        findings.append(
            _finding(
                "supplier_co2_mass_derived",
                "Lieferant hat keine CO₂-Masse ausgewiesen; die Masse wurde mit einem "
                "bestätigten Emissionsfaktor abgeleitet.",
            )
        )
        provenance.append(
            Page01bProvenance(
                "co2_mass_emission_factor",
                "K4 Emissionsfaktor",
                "CO₂-Masse aus Energiemenge und Faktor mit identischer Ho/Hu-Bezugsgröße.",
            )
        )
        triggers = replace(triggers, co2_disclosure_missing=True)

    if (
        core.warm_water_separation is not None
        and core.warm_water_separation.method == "AREA_FALLBACK"
    ):
        findings.append(
            _finding(
                "ww_area_fallback",
                "Warmwasserenergie wurde mangels Messung mit 32 kWh je m² und Jahr angesetzt.",
                "WARNING",
            )
        )
    for unit_id in core.estimated_unit_ids:
        findings.append(
            _finding(
                "unit_consumption_estimate",
                f"Verbrauch der Wohnung {unit_id} wurde nach § 9a Abs. 1 HeizkostenV geschätzt.",
                "NOTICE",
            )
        )

    if heating.warm_water is not None and heating.warm_water.volume_m3 is not None:
        ww_total, _ = _reading_total(heating, heat=False)
        central = heating.warm_water.volume_m3
        gap_percent = (central - ww_total) * Decimal(100) / central
        if gap_percent > Decimal(20):
            findings.append(
                _finding(
                    "ww_meter_gap_legal_warning",
                    "Warmwasserzähler weichen um mehr als 20 % vom zentralen Zähler ab; "
                    "Mehrkostenrisiko liegt beim Vermieter.",
                    "WARNING",
                )
            )
        elif gap_percent > Decimal(10):
            findings.append(
                _finding(
                    "ww_meter_gap_notice",
                    "Warmwasserzähler weichen um mehr als 10 % ab; Anlage und Zählerstände prüfen.",
                    "NOTICE",
                )
            )

    if cost_aggregation is not None and cost_aggregation.district_heat_disclosure is not None:
        provenance.append(
            Page01bProvenance(
                "district_heat_supplier",
                "Fernwärmeversorger",
                "Energiemix, THG-Wert, Primärenergiefaktor und Steuern wurden "
                "unverändert übernommen.",
            )
        )

    renter_ids = tuple(str(line.tenancy_id) for line in core.lines)
    renter_totals = tuple(line.total for line in core.lines)
    co2_result: Co2Result | PlantCo2Result | None = plant_result or core.co2
    if plant_result is not None:
        billable = plant_result.billable_total
        landlord_amount = plant_result.landlord_amount
        landlord_percent = (
            None
            if plant_result.landlord_share_percent is None
            else int(plant_result.landlord_share_percent)
        )
        intensity = plant_result.intensity_kg_per_sqm
        module_enabled = plant_result.co2_module_enabled
        mass_grams = (
            None
            if heating.co2 is None or heating.co2.total_co2_kg is None
            else int(heating.co2.total_co2_kg * Decimal(1000))
        )
    else:
        billable = core.billable_cost
        landlord_amount = cents(0) if core.co2 is None else core.co2.landlord_amount
        landlord_percent = None if core.co2 is None else core.co2.landlord_share_percent
        intensity = None if core.co2 is None else core.co2.intensity_kg_per_sqm
        module_enabled = core.co2 is not None
        mass_grams = None if core.co2 is None else int(core.co2.total_co2_kg * Decimal(1000))

    owner_preview = (
        calculate_owner_burden_preview(
            current_owner_total=value.owner_preview_baseline,
            proposed_owner_total=core.owner_residual.total,
        )
        if value.owner_preview_baseline is not None
        else None
    )
    annual = (
        calculate_annual_comparison(value.annual_comparison)
        if value.annual_comparison is not None
        else None
    )
    ww_unmetered_owner = cents(
        int(core.owner_residual.ww_consumption)
        - sum(int(origin.ww_consumption) for origin in core.owner_residual.origins)
    )
    section12_reduction = _section12_result(
        renter_ids=renter_ids,
        gross_claims=renter_totals,
        non_consumption_claims=tuple(
            cents(int(line.heating_base) + int(line.ww_base)) for line in core.lines
        ),
        triggers=triggers,
    )
    return Page01bStatementResult(
        readiness="READY",
        values=Page01bStatementValues(
            path="SELF_BILLING",
            renter_ids=renter_ids,
            renter_totals=renter_totals,
            owner_total=core.owner_residual.total,
            source_total=source_total,
            billable_total=billable,
            co2_landlord_amount=landlord_amount,
            co2_landlord_percent=landlord_percent,
            co2_intensity=intensity,
            co2_mass_grams=mass_grams,
            co2_module_enabled=module_enabled,
            ww_unmetered_owner=ww_unmetered_owner,
            heating_result=core,
            co2_result=co2_result,
        ),
        findings=tuple(findings),
        provenance=tuple(provenance),
        device_evidence=() if device is None else device.device_lines,
        risks=_risks(triggers, renter_totals),
        annual_comparison=annual,
        cost_aggregation=cost_aggregation,
        invoice_allocations=invoice_allocations,
        device_aggregation=device,
        owner_burden_preview=owner_preview,
        oil_consumption=oil,
        section12_reduction=section12_reduction,
    )


def _mdl(value: MdlStatementInput) -> Page01bStatementResult:
    if value.branch not in ("NET", "GROSS"):
        raise HeatingInputError(f"Unbekannter MDL-Zweig: {value.branch}")
    if len(value.renter_ids) != len(value.renter_positions):
        raise HeatingInputError("MDL-Mieterkennungen und Betragspositionen müssen gleich lang sein")
    if any(position < 0 for position in (*value.renter_positions, value.owner_position)):
        raise HeatingInputError("MDL-Betragspositionen dürfen nicht negativ sein")
    if value.confirmed_total < 0:
        raise HeatingInputError("Bestätigte MDL-Gesamtsumme darf nicht negativ sein")
    tolerance = len(value.renter_positions) + 1
    difference = abs(sum(value.renter_positions) + value.owner_position - value.confirmed_total)
    annual = (
        calculate_annual_comparison(value.annual_comparison)
        if value.annual_comparison is not None
        else None
    )
    if difference > tolerance:
        return _block(
            _finding(
                "mdl_control_sum_mismatch",
                f"MDL-Kontrollsumme weicht um {difference} ct ab; Lauf ist blockiert.",
                "BLOCKER",
                field_ref="renter_positions",
            ),
            annual=annual,
        )

    co2_result: Co2Result | None = None
    if value.branch == "GROSS":
        if value.co2 is None:
            return _block(
                _finding(
                    "mdl_gross_co2_missing",
                    "Brutto-MDL-Abrechnung benötigt bestätigte CO₂-Daten vor der Skalierung.",
                    "BLOCKER",
                    field_ref="co2",
                ),
                annual=annual,
            )
        co2_result = split_co2_cost(
            total_co2_kg=value.co2.total_co2_kg,
            co2_cost=value.co2.co2_cost,
            heated_area_sqm=value.co2.heated_area_sqm,
            table=value.co2.table,
            rechtsstand=value.co2.rechtsstand,
            billing_period=value.co2.billing_period,
        )
        billable = cents(value.confirmed_total - int(co2_result.landlord_amount))
        rescaled = rescale_mdl_gross_positions(
            gross_positions=value.renter_positions,
            gross_owner=value.owner_position,
            gross_total=value.confirmed_total,
            billable_total=int(billable),
        )
        renters = rescaled.renter_totals
        owner = rescaled.owner_total
        path: Literal["MDL_NET", "MDL_GROSS"] = "MDL_GROSS"
        landlord_amount = co2_result.landlord_amount
        landlord_percent = co2_result.landlord_share_percent
        intensity = co2_result.intensity_kg_per_sqm
        mass_grams = int(co2_result.total_co2_kg * Decimal(1000))
    else:
        billable = cents(value.confirmed_total)
        renters = tuple(cents(position) for position in value.renter_positions)
        owner = cents(value.confirmed_total - sum(value.renter_positions))
        path = "MDL_NET"
        landlord_amount = cents(0)
        landlord_percent = None
        intensity = None
        mass_grams = None

    non_consumption_claims: tuple[Cents, ...] | None = None
    if value.renter_non_consumption_positions is not None:
        if path == "MDL_NET" or value.confirmed_total == 0:
            non_consumption_claims = tuple(
                cents(position) for position in value.renter_non_consumption_positions
            )
        else:
            non_consumption_claims = tuple(
                cents(
                    int(
                        (
                            Decimal(position)
                            * Decimal(int(billable))
                            / Decimal(value.confirmed_total)
                        ).quantize(Decimal(1), rounding=ROUND_HALF_UP)
                    )
                )
                for position in value.renter_non_consumption_positions
            )

    triggers = value.risks
    if not value.co2_evidence_present:
        triggers = replace(triggers, co2_disclosure_missing=True)
    risks = _risks(triggers, renters)
    section12_reduction = _section12_result(
        renter_ids=value.renter_ids,
        gross_claims=renters,
        non_consumption_claims=non_consumption_claims,
        triggers=triggers,
    )
    return Page01bStatementResult(
        readiness="READY",
        values=Page01bStatementValues(
            path=path,
            renter_ids=value.renter_ids,
            renter_totals=renters,
            owner_total=owner,
            source_total=cents(value.confirmed_total),
            billable_total=billable,
            co2_landlord_amount=landlord_amount,
            co2_landlord_percent=landlord_percent,
            co2_intensity=intensity,
            co2_mass_grams=mass_grams,
            co2_module_enabled=value.co2_evidence_present,
            ww_unmetered_owner=cents(0),
            heating_result=None,
            co2_result=co2_result,
        ),
        findings=(),
        provenance=(
            Page01bProvenance(
                "mdl_confirmed_positions",
                "Messdienstleister-Abrechnung",
                "Bestätigte Beträge wurden validiert und nicht aus Rohdaten nachgerechnet.",
            ),
        ),
        device_evidence=(),
        risks=risks,
        annual_comparison=annual,
        section12_reduction=section12_reduction,
    )


def calculate_page01b_statement(
    value: SelfBillingStatementInput | MdlStatementInput,
) -> Page01bStatementResult:
    """Run exactly one H0 path and return the shared typed result."""

    if isinstance(value, SelfBillingStatementInput):
        return _self_billing(value)
    if isinstance(value, MdlStatementInput):
        return _mdl(value)
    raise HeatingInputError("Unbekannte Page-01b-Eingabevariante")
