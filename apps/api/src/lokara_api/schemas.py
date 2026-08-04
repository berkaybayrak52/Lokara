"""The typed HTTP contract (Pydantic) — port of the TS contract.ts.

JSON is camelCase (alias) for parity with what apps/web already consumes;
Python stays snake_case. Validate at every boundary: these models are the
only doorway between HTTP and the engine's frozen dataclasses.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from lokara_domain import (
    CANONICAL_UNITS,
    AllocationKey,
    MeasurementUnit,
    MeterKind,
    ReadingReason,
    ReadingSource,
)
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic.alias_generators import to_camel


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class HealthResponse(ApiModel):
    status: Literal["ok"]
    service: Literal["lokara-api"]
    timestamp: str


class DevTokenResponse(ApiModel):
    access_token: str
    expires_in_seconds: int


# ── Demo summary (German demo page contract) ──────────────────────────────────


class DemoTenancySummary(ApiModel):
    unit_label: str
    # Display-only m² (area_sqm_x100 / 100) — a JSON number for TS-contract
    # parity. Never a money value: those stay integer cents / Decimal.
    area_sqm: float
    renter_names: list[str]
    valid_from: str
    valid_to: str | None
    base_rent_eur: str


class DemoSummaryResponse(ApiModel):
    account_name: str
    building_name: str
    building_address: str
    unit_count: int
    tenancies: list[DemoTenancySummary]


# ── NK statement calculation ──────────────────────────────────────────────────


class PeriodIn(ApiModel):
    """Half-open [valid_from, valid_to) — valid_to null = open-ended."""

    valid_from: date
    valid_to: date | None = None


class NkUnitIn(ApiModel):
    unit_id: str
    area_sqm_x100: int = Field(gt=0)
    mea_x10000: int | None = Field(default=None, gt=0)


class NkOccupancyIn(ApiModel):
    unit_id: str
    tenancy_id: str | None  # null = explicit landlord/self-use period
    period: PeriodIn


class NkPersonCountIn(ApiModel):
    tenancy_id: str
    count: int = Field(gt=0)
    period: PeriodIn


class NkConsumptionIn(ApiModel):
    unit_id: str
    tenancy_id: str | None
    value: Decimal


class NkCostIn(ApiModel):
    cost_id: str
    label: str
    amount_cents: int = Field(ge=0)
    key: AllocationKey
    direct_unit_id: str | None = None
    direct_tenancy_id: str | None = None


class NkCalcRequest(ApiModel):
    billing_period: PeriodIn  # must be bounded — the engine rejects open periods
    units: list[NkUnitIn]
    occupancies: list[NkOccupancyIn]
    costs: list[NkCostIn]
    person_counts: list[NkPersonCountIn] = Field(default_factory=list)
    consumptions: list[NkConsumptionIn] = Field(default_factory=list)


class NkShareLineOut(ApiModel):
    cost_id: str
    unit_id: str | None
    tenancy_id: str | None  # null = landlord line (vacancy/self-use)
    amount_cents: int
    amount_eur: str


class NkCalcResponse(ApiModel):
    lines: list[NkShareLineOut]
    total_cents: int
    total_eur: str


# ── /me — the Person's relationships (drives the left nav) ───────────────────


class MeAccount(ApiModel):
    id: str
    name: str
    role: str
    shape: str


class MeResponse(ApiModel):
    person_id: str
    # Empty ⇒ no live membership yet (e.g. before the demo scenario is loaded).
    # TODO(M5): list every account once a person-scoped RLS policy exists; today
    # this can only see the token-claimed account's membership.
    accounts: list[MeAccount]


class DemoLoadResponse(ApiModel):
    ok: Literal[True]
    account_id: str


# ── Kosten erfassen (docs/04 M3 page 4) ──────────────────────────────────────


class KeyChoice(ApiModel):
    """A key selection — shared by cost creation and later re-assignment.
    DIRECT requires a target; every other key must not carry one."""

    key: AllocationKey
    direct_unit_id: str | None = None
    direct_tenancy_id: str | None = None

    @model_validator(mode="after")
    def _direct_target_consistency(self) -> "KeyChoice":
        has_target = self.direct_unit_id is not None or self.direct_tenancy_id is not None
        if self.key is AllocationKey.DIRECT and not has_target:
            raise ValueError("DIRECT requires direct_unit_id or direct_tenancy_id")
        if self.key is not AllocationKey.DIRECT and has_target:
            raise ValueError("Only DIRECT may carry a direct target")
        return self


class CostCreate(KeyChoice):
    label: str = Field(min_length=1, max_length=200)
    amount_cents: int = Field(gt=0)
    period_from: date
    period_to: date  # exclusive

    @model_validator(mode="after")
    def _period_order(self) -> "CostCreate":
        if self.period_to <= self.period_from:
            raise ValueError("period_to must be after period_from")
        return self


class CostEntryOut(ApiModel):
    id: str
    label: str
    amount_cents: int
    amount_eur: str
    period_from: date
    period_to: date
    key: AllocationKey  # the CURRENT assignment (latest row wins)
    key_label: str
    direct_unit_id: str | None
    direct_tenancy_id: str | None
    # Length of the append-only assignment history — re-keying grows this and
    # deletes nothing.
    assignment_count: int


class CostListResponse(ApiModel):
    costs: list[CostEntryOut]


# ── The demo statement (Abrechnung erstellen, M3 slice) ──────────────────────


class StatementNkLine(ApiModel):
    party_label: str
    is_landlord: bool  # vacancy/self-use share — lands on the Vermieter
    weight_display: str  # human-scale Bemessung (e.g. "18.250" m²·Tage)
    amount_cents: int
    amount_eur: str


class StatementNkCost(ApiModel):
    label: str
    key_label: str  # German Umlageschlüssel label
    amount_cents: int
    amount_eur: str
    lines: list[StatementNkLine]


class StatementHeatingLine(ApiModel):
    party_label: str
    is_landlord: bool
    heating_base_eur: str
    heating_consumption_eur: str
    ww_base_eur: str
    ww_consumption_eur: str
    total_cents: int
    total_eur: str


class StatementCo2(ApiModel):
    intensity_display: str  # kg CO₂/m²/Jahr, German decimal formatting
    landlord_share_percent: int
    landlord_amount_eur: str
    renter_amount_eur: str
    rechtsstand: str


# ── Objekte / Einheiten / Mietverhältnisse (M3 CRUD) ─────────────────────────


class BuildingCreate(ApiModel):
    name: str = Field(min_length=1, max_length=200)
    street: str = Field(min_length=1, max_length=200)
    postal_code: str = Field(pattern=r"^\d{5}$")
    city: str = Field(min_length=1, max_length=100)


class BuildingSummary(ApiModel):
    id: str
    name: str
    street: str
    postal_code: str
    city: str
    unit_count: int


class BuildingListResponse(ApiModel):
    buildings: list[BuildingSummary]


class UnitCreate(ApiModel):
    label: str = Field(min_length=1, max_length=200)
    # m² × 100 fixed point (docs/02: never floats near allocation math);
    # bounded to 10,000 m² — beyond that it's a data-entry error, not a unit.
    area_sqm_x100: int = Field(gt=0, le=1_000_000)


class UnitSummary(ApiModel):
    id: str
    label: str
    area_sqm: float  # display only
    tenancy_count: int
    occupied_today: bool


class BuildingDetailResponse(ApiModel):
    id: str
    name: str
    street: str
    postal_code: str
    city: str
    units: list[UnitSummary]


class TenancyCreate(ApiModel):
    renter_name: str = Field(min_length=1, max_length=200)
    valid_from: date
    valid_to: date | None = None  # exclusive; None = open-ended
    base_rent_cents: int = Field(ge=0)
    advance_payment_cents: int = Field(ge=0)


class TenancyOut(ApiModel):
    id: str
    renter_names: list[str]
    valid_from: date
    valid_to: date | None
    base_rent_cents: int
    base_rent_eur: str
    advance_payment_cents: int
    advance_payment_eur: str
    active_today: bool


class SelfUsePeriodOut(ApiModel):
    kind: str
    valid_from: date
    valid_to: date | None


class UnitDetailResponse(ApiModel):
    id: str
    label: str
    area_sqm: float
    building_id: str
    building_name: str
    tenancies: list[TenancyOut]  # newest first — the timeline
    self_use_periods: list[SelfUsePeriodOut]


# ── Zähler (docs/04 M3 page 5) ───────────────────────────────────────────────


class MeterCreate(ApiModel):
    """A device. unit_id null = a building-level Hauptzähler."""

    unit_id: str | None = None
    kind: MeterKind
    measurement_unit: MeasurementUnit
    serial: str = Field(min_length=1, max_length=100)
    label: str | None = Field(default=None, max_length=200)
    calibration_valid_until: date | None = None  # Eichfrist; null = nicht eichpflichtig

    @model_validator(mode="after")
    def _unit_matches_kind(self) -> "MeterCreate":
        """Water is always counted in m³, and only a heat device may count kWh
        or HKV units — a Kaltwasserzähler in kWh is a data-entry error, and one
        that reached the DB would silently corrupt the § 9 denominator."""
        expected = CANONICAL_UNITS.get(self.kind)
        if expected is not None and self.measurement_unit is not expected:
            raise ValueError(f"{self.kind.value} is measured in {expected.value}")
        if self.kind is MeterKind.HEAT and self.measurement_unit is (MeasurementUnit.CUBIC_METRE):
            raise ValueError("HEAT is measured in KWH or HKV_UNITS")
        return self


class MeterReadingCreate(ApiModel):
    """Create-only: a correction is a NEW reading, never an edit of this one."""

    read_at: date
    # Register value × 1000 (fixed point) — parsed from German input at the
    # form edge, exactly like money is parsed to cents.
    value_x1000: int = Field(ge=0)
    reason: ReadingReason
    source: ReadingSource = ReadingSource.MANUAL
    note: str | None = Field(default=None, max_length=500)


class MeterReadingOut(ApiModel):
    id: str
    read_at: date
    value_x1000: int
    value_display: str  # German-formatted, e.g. "1.800" or "241,5"
    reason: ReadingReason
    source: ReadingSource
    note: str | None
    recorded_at: datetime
    # True when a later reading for the same date replaced this one. The row
    # stays visible — an append-only log shows its own history.
    superseded: bool


class MeterOut(ApiModel):
    id: str
    unit_id: str | None
    unit_label: str | None  # null = building-level (Hauptzähler)
    kind: MeterKind
    kind_label: str
    measurement_unit: MeasurementUnit
    unit_symbol: str  # "kWh", "m³", "Einheiten"
    serial: str
    label: str | None
    calibration_valid_until: date | None
    # Computed, never stored (CLAUDE.md: guards are derived from data).
    calibration_status: Literal["EXPIRED", "EXPIRING_SOON", "VALID", "NOT_APPLICABLE"]
    readings: list[MeterReadingOut]  # newest first
    # Consumption over the billing period, from the effective opening/closing
    # readings; null when the pair is missing or unusable (→ § 9a estimate).
    period_consumption_display: str | None


class MeterListResponse(ApiModel):
    meters: list[MeterOut]
    period_label: str


class HeatingCostCreate(ApiModel):
    label: str = Field(min_length=1, max_length=200)
    amount_cents: int = Field(gt=0)  # total, incl. the CO₂ portion
    period_from: date
    period_to: date  # exclusive
    co2_kg_x1000: int | None = Field(default=None, ge=0)
    co2_cost_cents: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _period_order(self) -> "HeatingCostCreate":
        if self.period_to <= self.period_from:
            raise ValueError("period_to must be after period_from")
        if self.co2_cost_cents is not None and self.co2_cost_cents > self.amount_cents:
            raise ValueError("co2_cost_cents cannot exceed the total amount")
        return self


class HeatingCostOut(ApiModel):
    id: str
    label: str
    amount_cents: int
    amount_eur: str
    period_from: date
    period_to: date
    co2_kg_x1000: int | None
    co2_kg_display: str | None
    co2_cost_cents: int | None
    co2_cost_eur: str | None


class HeatingCostListResponse(ApiModel):
    heating_costs: list[HeatingCostOut]


# ── Beleg-Upload / Extraktion (docs/04 M4, canned) ───────────────────────────


class ExtractionFieldOut(ApiModel):
    """One extracted value, ready to render: already formatted for German
    display, with the confidence the provider reported for *that* field.

    ``needs_review`` is decided here, not in the client — the threshold is a
    product rule and belongs on one side of the wire.
    """

    id: str
    label: str
    value: str
    # Integer percent, not a float or a Decimal-as-string: the client only ever
    # displays it, and integers keep the wire unambiguous.
    confidence_percent: int
    needs_review: bool
    # False for values the confirm step cannot yet persist (see the router).
    stored: bool
    note: str | None = None


class ExtractionPrefill(ApiModel):
    """Exactly the CostCreate shape — the review form starts from this and
    submits through the ordinary Kosten erfassen endpoint. Nothing here is
    written until the user confirms."""

    label: str
    amount_cents: int
    period_from: date
    period_to: date
    key: AllocationKey


class ExtractionDuplicate(ApiModel):
    cost_id: str
    label: str
    amount_eur: str


class ExtractionOut(ApiModel):
    document_name: str
    provider_label: str
    document_confidence_percent: int
    fields: list[ExtractionFieldOut]
    prefill: ExtractionPrefill
    # German names of the fields the document does NOT supply — their prefill
    # values are form defaults, and saying so is the difference between a
    # suggestion and a silent guess.
    not_extracted: list[str]
    duplicate: ExtractionDuplicate | None


class DemoStatementResponse(ApiModel):
    building_name: str
    building_address: str
    period_label: str
    nk_costs: list[StatementNkCost]
    nk_total_cents: int
    nk_total_eur: str
    nk_input_total_cents: int  # reconciliation: must equal nk_total_cents
    heating_lines: list[StatementHeatingLine]
    heating_total_cents: int
    heating_total_eur: str
    heating_input_total_cents: int  # reconciliation: must equal heating_total_cents
    # Set when the heating inputs are incomplete: heating_lines is then empty
    # and this German sentence says what is missing. Never a silent zero.
    heating_missing_reason: str | None
    co2: StatementCo2 | None
    rechtsstaende: list[str]
    disclaimer: str
