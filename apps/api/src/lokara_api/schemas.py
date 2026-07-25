"""The typed HTTP contract (Pydantic) — port of the TS contract.ts.

JSON is camelCase (alias) for parity with what apps/web already consumes;
Python stays snake_case. Validate at every boundary: these models are the
only doorway between HTTP and the engine's frozen dataclasses.
"""

from datetime import date
from decimal import Decimal
from typing import Literal

from lokara_domain import AllocationKey
from pydantic import BaseModel, ConfigDict, Field
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
    co2: StatementCo2 | None
    rechtsstaende: list[str]
    disclaimer: str
