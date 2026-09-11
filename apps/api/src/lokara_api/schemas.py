"""The typed HTTP contract (Pydantic) — port of the TS contract.ts.

JSON is camelCase (alias) for parity with what apps/web already consumes;
Python stays snake_case. Validate at every boundary: these models are the
only doorway between HTTP and the engine's frozen dataclasses.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from lokara_domain import (
    DEVICE_TYPE_FACTS,
    AllocationKey,
    CalibrationDataState,
    ExternalHeatingStatus,
    HeatingBillingMode,
    HeatingCostCategory,
    MeasurementUnit,
    MeterDeviceType,
    MeterKind,
    MeterLifecycleEventType,
    ReadingReason,
    ReadingSource,
    RemoteReadability,
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


class PortfolioOverviewResponse(ApiModel):
    building_count: int = Field(ge=0)
    unit_count: int = Field(ge=0)
    occupied_unit_count: int = Field(ge=0)
    vacant_unit_count: int = Field(ge=0)
    miet_soll_cents_monthly: int = Field(ge=0)


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
    """A supplied consumption value, with the Maßeinheit it was counted in.

    The unit rides on the row that carries the value (docs/08 →
    "`MeasurementUnit` travels with the value"): a side channel lets the two
    disagree, and the disagreement surfaces as a wrong unit on a
    Verbrauchsabrechnung. Optional, and absence is not silent — the engine
    resolves the key's unit to None and the statement prints no denominator at
    all rather than a guessed one. Mixed units on one key are an engine input
    error, which this router answers with 422.
    """

    unit_id: str
    tenancy_id: str | None
    value: Decimal
    measurement_unit: MeasurementUnit | None = None


class NkIneligibleTenancyPeriodIn(ApiModel):
    tenancy_id: str
    period: PeriodIn
    cost_id: str | None = None


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
    ineligible_tenancy_periods: list[NkIneligibleTenancyPeriodIn] = Field(default_factory=list)


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


class MeRenterContext(ApiModel):
    tenancy_id: str


class MeResponse(ApiModel):
    person_id: str
    email: str
    # Empty ⇒ no live membership yet (e.g. before the demo scenario is loaded).
    accounts: list[MeAccount]
    renter_contexts: list[MeRenterContext]


class RenterOverviewResponse(ApiModel):
    tenancy_id: str
    valid_from: date
    valid_to: date | None
    unit_label: str
    building_name: str
    street: str
    postal_code: str
    city: str


class RenterPortalPublicationCreate(ApiModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="forbid",
    )

    tenancy_id: str = Field(min_length=1)
    statement_archive_id: str | None = None
    renter_delivery_artifact_id: str | None = None
    supersedes_publication_id: str | None = None

    @model_validator(mode="after")
    def exactly_one_source(self) -> "RenterPortalPublicationCreate":
        source_count = sum(
            source_id is not None
            for source_id in (
                self.statement_archive_id,
                self.renter_delivery_artifact_id,
            )
        )
        if source_count != 1:
            raise ValueError("Genau eine Dokumentquelle muss angegeben werden.")
        return self


class RenterPortalPublicationOut(ApiModel):
    id: str
    tenancy_id: str
    source_kind: Literal["STATEMENT_ARCHIVE", "UVI_ARTIFACT"]
    document_type: Literal["COVER_LETTER", "TENANT_STATEMENT", "UVI"]
    filename: str
    mime_type: str
    sha256: str
    published_at: datetime
    supersedes_publication_id: str | None
    download_url: str


class RenterPortalPublicationList(ApiModel):
    documents: list[RenterPortalPublicationOut]


class RenterActivationCodeOut(ApiModel):
    activation_code_id: str
    activation_code: str
    expires_at: datetime


class RenterActivationRedeemIn(ApiModel):
    # The route normalizes every JSON shape itself so FastAPI cannot expose its
    # usual field-specific 422 validation oracle for this public secret.
    activation_code: object | None = None


class RenterActivationRedeemOut(ApiModel):
    ok: Literal[True]
    tenancy_id: str
    renter_id: str


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


class CostCreate(ApiModel):
    # A catalogue identity is a human confirmation, never an OCR inference.
    catalogue_id: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=200)
    amount_cents: int = Field(gt=0)
    period_from: date
    period_to: date  # exclusive
    invoice_date: date | None = None
    payment_date: date | None = None
    service_from: date | None = None
    service_to: date | None = None
    non_allocable_cents: int = Field(default=0, ge=0)
    labour_cents: int | None = Field(default=None, ge=0)
    key_override: AllocationKey | None = None
    direct_unit_id: str | None = None
    direct_tenancy_id: str | None = None
    special_rule_evidence: dict[str, object] = Field(default_factory=dict)
    replaces_cost_id: str | None = None
    new_cost: bool = False

    @model_validator(mode="after")
    def _period_order(self) -> "CostCreate":
        if self.period_to <= self.period_from:
            raise ValueError("period_to must be after period_from")
        if (self.service_from is None) != (self.service_to is None):
            raise ValueError("service_from and service_to must be supplied together")
        if (
            self.service_from is not None
            and self.service_to is not None
            and self.service_to <= self.service_from
        ):
            raise ValueError("service_to must be after service_from")
        return self


class CostCataloguePositionOut(ApiModel):
    catalogue_id: str
    label: str
    betrkv_number: str | None
    default_key: AllocationKey | None
    naming_required: bool
    allocable: bool


class CostCatalogueResponse(ApiModel):
    positions: list[CostCataloguePositionOut]


class CostEntryOut(ApiModel):
    id: str
    label: str
    amount_cents: int
    amount_eur: str
    period_from: date
    period_to: date
    key: AllocationKey | None  # null for documented non-allocable costs
    key_label: str | None
    direct_unit_id: str | None
    direct_tenancy_id: str | None
    # Length of the append-only assignment history — re-keying grows this and
    # deletes nothing.
    assignment_count: int
    catalogue_id: str | None = None
    classification_findings: list[str] = Field(default_factory=list)
    production_blocked: bool = False
    voided_at: datetime | None = None
    void_reason: str | None = None
    replaces_cost_id: str | None = None


class CostVoid(ApiModel):
    reason: str = Field(min_length=1, max_length=500)


class CostVoidOut(ApiModel):
    id: str
    voided_at: datetime
    successor_workflow_target: str


class CostListResponse(ApiModel):
    costs: list[CostEntryOut]


class OperatingCostAgreementIn(ApiModel):
    allocation_agreed: bool
    mehrbelastung_clause: bool = False
    named_other_costs: list[str] = Field(default_factory=list)
    contractual_keys: dict[str, AllocationKey] = Field(default_factory=dict)
    valid_from: date
    valid_to: date | None = None
    revises_id: str | None = None

    @model_validator(mode="after")
    def _ordered(self) -> "OperatingCostAgreementIn":
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("valid_to must be after valid_from")
        return self


class OperatingCostAgreementOut(OperatingCostAgreementIn):
    id: str
    tenancy_id: str
    created_at: datetime


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
    """One party's heating share.

    The four column figures are `None` on a confirmed Messdienstleister
    passthrough: that document states a total per party and no §§ 7/8/9 column
    split, and `docs/03` H7 forbids recomputing one. Nullable rather than
    `"0,00 €"` or `"—"`, because a money field that carries a placeholder is
    indistinguishable from a real zero to everything downstream.
    """

    party_label: str
    is_landlord: bool
    heating_base_eur: str | None
    heating_consumption_eur: str | None
    ww_base_eur: str | None
    ww_consumption_eur: str | None
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
    building_type: Literal[
        "WOHN_UND_GESCHAEFTSHAUS",
        "WOHNHAUS",
        "GEWERBEIMMOBILIE",
        "EINFAMILIENHAUS",
    ]
    is_residential: bool
    street: str = Field(min_length=1, max_length=200)
    house_number: str = Field(min_length=1, max_length=20)
    postal_code: str = Field(pattern=r"^\d{5}$")
    city: str = Field(min_length=1, max_length=100)
    country: str = Field(default="Deutschland", min_length=1, max_length=100)

    @model_validator(mode="after")
    def _composed_street_fits_database_column(self) -> "BuildingCreate":
        if len(f"{self.street} {self.house_number}") > 200:
            raise ValueError("street and house number together must not exceed 200 characters")
        return self


class BuildingSummary(ApiModel):
    id: str
    name: str
    street: str
    postal_code: str
    city: str
    unit_count: int
    building_type: str
    latitude: float | None
    longitude: float | None


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


# ── UI-04 Objekt-Dashboard read model ────────────────────────────────────────
#
# One server-owned projection. Every money, area, state and priority value is
# decided here; the browser renders what it is given and derives nothing.


class BuildingDashboardOccupancy(ApiModel):
    rented: int
    vacant: int
    self_use: int
    total: int


class BuildingDashboardUsageKpi(ApiModel):
    usage_type: Literal["RESIDENTIAL", "COMMERCIAL", "OTHER"]
    usage_label: str
    rented_area_sqm_x100: int
    rented_area_sqm: float
    cold_rent_cents_monthly: int
    cold_rent_eur_monthly: str
    avg_cold_rent_cents_per_sqm: int | None
    avg_cold_rent_eur_per_sqm: str | None


class BuildingDashboardKpis(ApiModel):
    cold_rent_cents_monthly: int
    cold_rent_eur_monthly: str
    total_area_sqm_x100: int
    total_area_sqm: float
    rented_area_sqm_x100: int
    rented_area_sqm: float
    # None, never 0,00 €: no rented area means the ratio has no meaning.
    avg_cold_rent_cents_per_sqm: int | None
    avg_cold_rent_eur_per_sqm: str | None
    occupancy: BuildingDashboardOccupancy
    usage_breakdown: list[BuildingDashboardUsageKpi]


class BuildingDashboardFact(ApiModel):
    """One prioritized fact. The server owns severity and order."""

    id: str
    category: Literal["OPEN_RECEIVABLE", "MOVE_OUT", "MOVE_IN"]
    severity: Literal["info", "attention"]
    text: str
    unit_id: str | None
    unit_label: str | None
    action_label: str | None
    action_href: str | None
    event_date: date | None


class BuildingDashboardBalance(ApiModel):
    status: Literal["SETTLED", "OPEN", "NONE"]
    open_cents: int
    open_eur: str
    label: str


class BuildingDashboardNextEvent(ApiModel):
    kind: Literal["MOVE_IN", "MOVE_OUT"]
    event_date: date
    label: str


class BuildingDashboardUnit(ApiModel):
    id: str
    label: str
    area_sqm_x100: int
    area_sqm: float
    state: Literal["RENTED", "VACANT", "SELF_USE", "GRATUITOUS"]
    state_label: str
    party_names: list[str]
    # docs/02 forbids overlapping tenancies. Surfacing the conflict beats hiding
    # it behind an arbitrarily chosen party (04_Objekt-Dashboard.md OD9).
    has_tenancy_overlap: bool
    cold_rent_cents: int | None
    cold_rent_eur: str | None
    balance: BuildingDashboardBalance | None
    next_event: BuildingDashboardNextEvent | None


class BuildingDashboardModuleFact(ApiModel):
    label: str
    value: str


class BuildingDashboardModule(ApiModel):
    key: Literal["payments", "costs_and_statement", "meters"]
    title: str
    available: bool
    # Set when `available` is false. An honest sentence, never a synthetic zero.
    unavailable_reason: str | None
    facts: list[BuildingDashboardModuleFact]
    action_label: str | None
    action_href: str | None


class BuildingDashboardPermissions(ApiModel):
    can_edit: bool
    can_create_unit: bool
    can_export_pdf: bool


class BuildingDashboardResponse(ApiModel):
    as_of: date
    id: str
    name: str
    street: str
    postal_code: str
    city: str
    country: str
    building_type: str
    building_type_label: str
    is_residential: bool
    unit_count: int
    kpis: BuildingDashboardKpis
    facts: list[BuildingDashboardFact]
    facts_total: int
    units: list[BuildingDashboardUnit]
    modules: list[BuildingDashboardModule]
    permissions: BuildingDashboardPermissions


class TenancyCreate(ApiModel):
    renter_name: str = Field(min_length=1, max_length=200)
    valid_from: date
    valid_to: date | None = None  # exclusive; None = open-ended
    base_rent_cents: int = Field(ge=0)
    initial_advance_payment_cents: int = Field(ge=0)
    advance_declaration_ref: str = Field(min_length=1, max_length=500)


class TenancyOut(ApiModel):
    id: str
    renter_names: list[str]
    valid_from: date
    valid_to: date | None
    base_rent_cents: int
    base_rent_eur: str
    advance_payment_schedule: list["AdvancePaymentPeriodOut"]
    active_today: bool


class AdvancePaymentPeriodOut(ApiModel):
    id: str
    amount_cents: int
    amount_eur: str
    valid_from: date
    valid_to: date | None
    predecessor_id: str | None
    declaration_ref: str


class AdvancePaymentCreate(ApiModel):
    amount_cents: int = Field(gt=0)
    payment_date: date
    evidence_ref: str = Field(min_length=1, max_length=500)
    period_start: date
    period_end: date


class AdvanceScheduleSuccessorCreate(ApiModel):
    amount_cents: int = Field(ge=0)
    valid_from: date
    declaration_ref: str = Field(min_length=1, max_length=500)


class AdvancePaymentOut(ApiModel):
    id: str
    allocation_id: str
    amount_cents: int
    payment_date: date
    evidence_ref: str
    reversal_of_id: str | None


class AdvanceReconciliationCreate(ApiModel):
    allocation_ids: list[str] = Field(default_factory=list)


class AdvanceReconciliationOut(ApiModel):
    id: str
    version: int
    total_cents: int
    allocation_ids: list[str]


class TenancyPreviewChoice(ApiModel):
    id: str
    label: str


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


class UnitProfileVersionCreate(ApiModel):
    effective_from: date
    usage_type: Literal["RESIDENTIAL", "COMMERCIAL", "OTHER"]
    rooms_x100: int | None = Field(default=None, ge=0)
    amenities: list[
        Literal[
            "BALCONY",
            "TERRACE",
            "ELEVATOR",
            "CELLAR",
            "FITTED_KITCHEN",
            "BARRIER_REDUCED",
        ]
    ] = Field(default_factory=list)
    amenity_note: str | None = Field(default=None, max_length=500)
    evidence_ref: str = Field(min_length=1, max_length=500)


class TenancyContractVersionCreate(ApiModel):
    effective_from: date
    contract_type: Literal[
        "RESIDENTIAL_OPEN_ENDED",
        "RESIDENTIAL_FIXED_TERM",
        "COMMERCIAL_OPEN_ENDED",
        "COMMERCIAL_FIXED_TERM",
        "OTHER",
    ]
    evidence_ref: str = Field(min_length=1, max_length=500)


class TenancyContractPositionCreate(ApiModel):
    position_type: Literal["GARAGE", "PARKING"]
    inclusion_type: Literal["INCLUDED", "SEPARATE"]
    label: str | None = Field(default=None, max_length=200)
    monthly_amount_cents: int | None = Field(default=None, ge=0)
    valid_from: date
    valid_to: date | None = None
    evidence_ref: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def _position_is_consistent(self) -> "TenancyContractPositionCreate":
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("valid_to must be after valid_from")
        if self.inclusion_type == "SEPARATE" and self.monthly_amount_cents is None:
            raise ValueError("a separate position needs a monthly amount")
        return self


class TenancyRentChangeCreate(ApiModel):
    effective_from: date
    new_base_rent_cents: int = Field(ge=0)
    evidence_ref: str = Field(min_length=1, max_length=500)


class UnitDashboardWriteResponse(ApiModel):
    id: str


class UnitDashboardProfile(ApiModel):
    version: int | None
    usage_type: str | None
    usage_label: str
    rooms_x100: int | None
    rooms_display: str | None
    amenities: list[str]
    amenity_labels: list[str]
    amenity_note: str | None
    evidence_ref: str | None


class UnitDashboardParty(ApiModel):
    id: str
    name: str
    email: str | None


class UnitDashboardContractPosition(ApiModel):
    id: str
    position_type: str
    position_label: str
    inclusion_type: str
    inclusion_label: str
    label: str | None
    monthly_amount_cents: int | None
    monthly_amount_eur: str | None


class UnitDashboardRentChange(ApiModel):
    effective_from: date
    new_base_rent_cents: int
    new_base_rent_eur: str
    evidence_ref: str


class UnitDashboardTenancy(ApiModel):
    id: str
    parties: list[UnitDashboardParty]
    valid_from: date
    valid_to: date | None
    contract_type: str | None
    contract_type_label: str
    contract_evidence_ref: str | None
    cold_rent_cents: int
    cold_rent_eur: str
    cold_rent_per_sqm_eur: str | None
    advance_payment_cents: int
    advance_payment_eur: str
    total_monthly_cents: int
    total_monthly_eur: str
    positions: list[UnitDashboardContractPosition]
    last_rent_change: UnitDashboardRentChange | None


class UnitDashboardHistorySegment(ApiModel):
    kind: Literal["RENTED", "VACANT", "SELF_USE", "GRATUITOUS"]
    label: str
    valid_from: date
    valid_to: date | None
    party_names: list[str]
    current: bool


class UnitDashboardDocument(ApiModel):
    id: str
    statement_id: str
    document_type: str
    filename: str
    sha256: str
    size_bytes: int
    created_at: datetime
    download_href: str


class UnitDashboardModule(ApiModel):
    key: Literal["PAYMENTS", "PORTAL", "MESSAGES", "DOCUMENTS"]
    available: bool
    unavailable_reason: str | None


class UnitDashboardAction(ApiModel):
    key: str
    label: str
    href: str


class UnitDashboardPermissions(ApiModel):
    can_edit_profile: bool
    can_create_tenancy: bool
    can_record_contract_facts: bool


class UnitDashboardResponse(ApiModel):
    as_of: date
    id: str
    label: str
    area_sqm_x100: int
    area_sqm_display: str
    building_id: str
    building_name: str
    building_address: str
    state: Literal["RENTED", "VACANT", "SELF_USE", "GRATUITOUS", "CONFLICT"]
    state_label: str
    profile: UnitDashboardProfile
    current_tenancy: UnitDashboardTenancy | None
    history: list[UnitDashboardHistorySegment]
    history_total: int
    history_has_more: bool
    documents: list[UnitDashboardDocument]
    modules: list[UnitDashboardModule]
    primary_action: UnitDashboardAction | None
    permissions: UnitDashboardPermissions


# ── Zähler (docs/04 M3 page 5) ───────────────────────────────────────────────


class GasConversionCreate(ApiModel):
    """Exact supplier-invoice facts used to convert gas volume to heat."""

    calorific_factor_kwh_per_m3: Decimal = Field(gt=0, max_digits=12, decimal_places=6)
    condition_number: Decimal = Field(gt=0, max_digits=12, decimal_places=6)
    valid_from: date
    valid_to: date | None = None
    supplier_invoice_reference: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def _period_is_ordered(self) -> "GasConversionCreate":
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("gas conversion valid_to must be after valid_from")
        if not self.supplier_invoice_reference.strip():
            raise ValueError("gas conversion supplier reference is required")
        self.supplier_invoice_reference = self.supplier_invoice_reference.strip()
        return self


class GasConversionOut(ApiModel):
    calorific_factor_kwh_per_m3: Decimal
    condition_number: Decimal
    valid_from: date
    valid_to: date | None
    supplier_invoice_reference: str
    source_type: Literal["SUPPLIER_INVOICE"]
    source_id: str
    rechtsstand: Literal["08/2026"]
    verification_status: Literal["verify-before-production"]
    configuration_id: str
    supersedes_configuration_id: str | None


class MeterCreate(ApiModel):
    """One immutable device identity; replacement is one atomic workflow."""

    unit_id: str | None = None
    device_type: MeterDeviceType | None = None
    kind: MeterKind | None = None
    measurement_unit: MeasurementUnit | None = None
    serial: str = Field(min_length=1, max_length=100)
    label: str | None = Field(default=None, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    manufacturer: str | None = Field(default=None, max_length=200)
    model: str | None = Field(default=None, max_length=200)
    installed_on: date
    remote_readability: RemoteReadability = RemoteReadability.UNKNOWN
    calibration_data_state: CalibrationDataState
    calibration_date: date | None = None
    calibration_evidence_ref: str | None = Field(default=None, max_length=500)
    # Legacy input remains accepted during migration, but never drives a new
    # calculation. UI-08 stores the observed calibration date instead.
    calibration_valid_until: date | None = None
    # Exact K11 factor × 1000. Heat devices default to the neutral 1.000.
    valuation_factor_x1000: int | None = Field(default=None, gt=0)
    creation_mode: Literal["NEW", "EXISTING", "REPLACEMENT"] = "NEW"
    replaces_meter_id: str | None = None
    replacement_date: date | None = None
    old_final_value_x1000: int | None = Field(default=None, ge=0)
    new_initial_value_x1000: int | None = Field(default=None, ge=0)
    replacement_reason: str | None = Field(default=None, max_length=500)
    gas_conversion: GasConversionCreate | None = None

    @model_validator(mode="after")
    def _unit_matches_kind(self) -> "MeterCreate":
        if self.device_type is None:
            if self.kind is None or self.measurement_unit is None:
                raise ValueError("device_type is required")
            matches = [
                device
                for device, facts in DEVICE_TYPE_FACTS.items()
                if facts == (self.kind, self.measurement_unit)
            ]
            if len(matches) != 1:
                raise ValueError("kind and measurement_unit do not identify one device type")
            self.device_type = matches[0]
        expected_kind, expected_unit = DEVICE_TYPE_FACTS[self.device_type]
        if self.kind is not None and self.kind is not expected_kind:
            raise ValueError("device_type does not match kind")
        if self.measurement_unit is not None and self.measurement_unit is not expected_unit:
            raise ValueError("device_type does not match measurement_unit")
        self.kind = expected_kind
        self.measurement_unit = expected_unit
        if self.device_type is MeterDeviceType.GAS_METER:
            if self.gas_conversion is None:
                raise ValueError("gas_conversion is required for GAS_METER")
        elif self.gas_conversion is not None:
            raise ValueError("gas_conversion is only valid for GAS_METER")
        if expected_kind is not MeterKind.HEAT and self.valuation_factor_x1000 is not None:
            raise ValueError("valuation_factor_x1000 is only valid for HEAT meters")
        if self.calibration_data_state is CalibrationDataState.DATA_AVAILABLE:
            if self.calibration_date is None or not self.calibration_evidence_ref:
                raise ValueError("calibration_date and evidence are required")
        elif self.calibration_date is not None or self.calibration_evidence_ref is not None:
            raise ValueError("calibration facts are only valid with DATA_AVAILABLE")
        if self.creation_mode == "REPLACEMENT":
            required = (
                self.replaces_meter_id,
                self.replacement_date,
                self.old_final_value_x1000,
                self.new_initial_value_x1000,
                self.replacement_reason,
            )
            if any(value is None or value == "" for value in required):
                raise ValueError("replacement requires old meter, date, both readings and reason")
            if self.replacement_date != self.installed_on:
                raise ValueError("replacement_date must equal installed_on")
        elif any(
            value is not None
            for value in (
                self.replaces_meter_id,
                self.replacement_date,
                self.old_final_value_x1000,
                self.new_initial_value_x1000,
                self.replacement_reason,
            )
        ):
            raise ValueError("replacement fields require creation_mode REPLACEMENT")
        return self


class MeterLifecycleCreate(ApiModel):
    effective_on: date
    reason: str = Field(min_length=1, max_length=500)


class MeterLifecycleOut(ApiModel):
    id: str
    event_type: MeterLifecycleEventType
    effective_on: date
    reason: str | None
    related_meter_id: str | None
    created_at: datetime


class MeterReadingCreate(ApiModel):
    """Create-only: a correction is a NEW reading, never an edit of this one."""

    read_at: date
    # Register value × 1000 (fixed point) — parsed from German input at the
    # form edge, exactly like money is parsed to cents.
    value_x1000: int = Field(ge=0)
    reason: ReadingReason
    source: ReadingSource = ReadingSource.MANUAL
    note: str | None = Field(default=None, max_length=500)
    supersedes_reading_id: str | None = None
    confirmation_note: str | None = Field(default=None, max_length=500)
    confirmed_finding_codes: list[str] = Field(default_factory=list)
    tenancy_id: str | None = None
    estimated_consumption_x1000: int | None = Field(default=None, ge=0)
    estimation_basis: str | None = Field(default=None, min_length=1, max_length=500)
    provenance_ref: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def _estimate_has_basis(self) -> "MeterReadingCreate":
        if (self.estimated_consumption_x1000 is None) != (self.estimation_basis is None):
            raise ValueError("estimated_consumption_x1000 and estimation_basis belong together")
        if self.reason is ReadingReason.CORRECTION:
            if self.supersedes_reading_id is None or not self.confirmation_note:
                raise ValueError("a correction requires its target and a reason")
        elif self.supersedes_reading_id is not None:
            raise ValueError("only a correction may supersede a reading")
        if self.reason is ReadingReason.DEVICE_CHANGE:
            raise ValueError("use the atomic replacement workflow for a device change")
        return self


class ReadingPlausibilityFinding(ApiModel):
    code: str
    severity: Literal["NOTICE", "WARNING", "BLOCKER"]
    message: str
    requires_confirmation: bool


class ReadingPlausibilityResponse(ApiModel):
    findings: list[ReadingPlausibilityFinding]
    suggested_tenancy_id: str | None


class MeterReadingOut(ApiModel):
    id: str
    read_at: date
    value_x1000: int
    value_display: str  # German-formatted, e.g. "1.800" or "241,5"
    reason: ReadingReason
    source: ReadingSource
    note: str | None
    supersedes_reading_id: str | None
    confirmation_note: str | None
    tenancy_id: str | None
    estimated_consumption_x1000: int | None
    estimation_basis: str | None
    provenance_ref: str | None
    recorded_at: datetime
    # True when a later reading for the same date replaced this one. The row
    # stays visible — an append-only log shows its own history.
    superseded: bool


class MeterConsumptionReading(ApiModel):
    id: str
    read_at: date
    value_x1000: int
    value_display: str
    source: ReadingSource


class MeterConsumptionPeriod(ApiModel):
    period_from: date
    period_to: date
    period_label: str
    status: Literal["MEASURED", "INCOMPLETE", "ESTIMATED", "NOT_APPLICABLE"]
    opening_reading: MeterConsumptionReading | None
    closing_reading: MeterConsumptionReading | None
    consumption_x1000: int | None
    consumption_display: str | None
    finding: str | None
    estimation_basis: str | None
    provenance_ref: str | None


class MeterOut(ApiModel):
    id: str
    unit_id: str | None
    unit_label: str | None  # null = building-level (Hauptzähler)
    device_type: MeterDeviceType
    device_type_label: str
    kind: MeterKind
    kind_label: str
    measurement_unit: MeasurementUnit
    unit_symbol: str  # "kWh", "m³", "Einheiten"
    serial: str
    label: str | None
    location: str | None
    manufacturer: str | None
    model: str | None
    installed_on: date
    lifecycle_status: Literal["ACTIVE", "REMOVED", "REPLACED", "VOID"]
    lifecycle_ended_on: date | None
    related_meter_id: str | None
    lifecycle_events: list[MeterLifecycleOut]
    remote_readability: RemoteReadability
    calibration_data_state: CalibrationDataState
    calibration_date: date | None
    calibration_evidence_ref: str | None
    calibration_valid_until: date | None
    valuation_factor_x1000: int | None
    valuation_factor_display: str | None
    gas_conversion: GasConversionOut | None
    # Computed, never stored (CLAUDE.md: guards are derived from data).
    calibration_status: Literal[
        "EXPIRED",
        "EXPIRING_SOON",
        "VALID",
        "MISSING_DATA",
        "NOT_APPLICABLE",
        "REVIEW_REQUIRED",
    ]
    calibration_message: str | None
    calibration_rechtsstand: str | None
    calibration_production_blockers: list[str]
    readings: list[MeterReadingOut]  # newest first
    consumption_periods: list[MeterConsumptionPeriod]
    # Consumption over the billing period, from the effective opening/closing
    # readings; null when the pair is missing or unusable (→ § 9a estimate).
    period_consumption_display: str | None


class MeterListResponse(ApiModel):
    meters: list[MeterOut]
    period_label: str


class MeterWorkspaceUnit(ApiModel):
    id: str
    label: str
    active_meter_count: int
    warning_count: int
    tenancies: list["MeterWorkspaceTenancy"]
    meters: list[MeterOut]


class MeterWorkspaceTenancy(ApiModel):
    id: str
    label: str
    valid_from: date
    valid_to: date | None


class MeterWorkspaceBuilding(ApiModel):
    id: str
    name: str
    address: str
    active_meter_count: int
    expired_count: int
    missing_data_count: int
    building_meters: list[MeterOut]
    units: list[MeterWorkspaceUnit]


class MeterWorkspacePermissions(ApiModel):
    can_write: bool


class MeterWorkspaceResponse(ApiModel):
    as_of: datetime
    period_label: str
    buildings: list[MeterWorkspaceBuilding]
    expired_meter_ids: list[str]
    permissions: MeterWorkspacePermissions


class HeatingCostCreate(ApiModel):
    category: HeatingCostCategory
    label: str = Field(min_length=1, max_length=200)
    amount_cents: int = Field(gt=0)  # total, incl. the CO₂ portion
    period_from: date
    period_to: date  # exclusive
    co2_kg_x1000: int | None = Field(default=None, ge=0)
    co2_cost_cents: int | None = Field(default=None, ge=0)
    source_ref: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def _period_order(self) -> "HeatingCostCreate":
        if self.period_to <= self.period_from:
            raise ValueError("period_to must be after period_from")
        if self.co2_cost_cents is not None and self.co2_cost_cents > self.amount_cents:
            raise ValueError("co2_cost_cents cannot exceed the total amount")
        return self


class HeatingCostOut(ApiModel):
    id: str
    category: HeatingCostCategory
    label: str
    amount_cents: int
    amount_eur: str
    period_from: date
    period_to: date
    co2_kg_x1000: int | None
    co2_kg_display: str | None
    co2_cost_cents: int | None
    co2_cost_eur: str | None
    source_ref: str | None
    voided_at: datetime | None
    void_reason: str | None


class HeatingCostListResponse(ApiModel):
    heating_costs: list[HeatingCostOut]
    readiness: Literal["COMPLETE", "MISSING_INFORMATION", "REVIEW_REQUIRED"]
    findings: list[str]


class HeatingCostVoid(ApiModel):
    reason: str = Field(min_length=1, max_length=500)


class HeatingBillingModeCreate(ApiModel):
    period_from: date
    period_to: date
    mode: HeatingBillingMode
    provider_name: str | None = Field(default=None, max_length=200)
    provider_reference: str | None = Field(default=None, max_length=200)
    external_status: ExternalHeatingStatus | None = None
    mdl_statement_id: str | None = None
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _mode_shape(self) -> "HeatingBillingModeCreate":
        if self.period_to <= self.period_from:
            raise ValueError("period_to must be after period_from")
        if self.mode is HeatingBillingMode.LOKARA:
            if any(
                value is not None
                for value in (
                    self.provider_name,
                    self.provider_reference,
                    self.external_status,
                    self.mdl_statement_id,
                )
            ):
                raise ValueError("LOKARA mode cannot carry external provider data")
        elif not self.provider_name or self.external_status is None:
            raise ValueError("external mode requires provider and workflow status")
        if (
            self.external_status is ExternalHeatingStatus.UEBERNOMMEN
            and self.mdl_statement_id is None
        ):
            raise ValueError("adoption requires a confirmed MDL statement")
        return self


class HeatingBillingModeOut(ApiModel):
    id: str
    building_id: str
    period_from: date
    period_to: date
    version: int
    mode: HeatingBillingMode
    provider_name: str | None
    provider_reference: str | None
    external_status: ExternalHeatingStatus | None
    mdl_statement_id: str | None
    note: str | None
    created_at: datetime


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

    catalogue_id: str
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


class StatementFinding(ApiModel):
    code: str
    message: str
    severity: Literal["NOTICE", "WARNING", "BLOCKER"]
    dismissible: bool


class StatementProvenance(ApiModel):
    code: str
    source: str
    detail: str


class StatementDeviceEvidence(ApiModel):
    device_id: str
    unit_id: str
    room: str
    measurement_unit: MeasurementUnit
    valuation_factor: str
    allocation_kind: Literal["PARTY", "OWNER", "ANNUAL_UNSEGMENTED"]
    target_id: str | None
    opening: str | None
    closing: str | None
    units: str
    estimated: bool
    estimation_basis: str | None
    reading_reasons: list[str]
    reading_sources: list[str]
    provenance_refs: list[str]


class StatementReductionRisk(ApiModel):
    code: str
    percent: str
    amounts_eur: list[str]
    message: str


class StatementAnnualComparison(ApiModel):
    state: Literal["READY", "RAW_FALLBACK", "NO_PRIOR"]
    current_heat: str
    previous_heat: str | None
    current_heat_adjusted: str | None
    previous_heat_adjusted: str | None
    current_warm_water: str | None
    previous_warm_water: str | None
    raw_change_percent: str | None
    adjusted_change_percent: str | None
    graph_required: bool
    note: str | None


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
    # Which input produced the heating figures. `docs/08`: "MDL pass-through and
    # self-billing are different inputs" — the reader has to be able to tell,
    # because one was calculated here and the other was confirmed from a
    # third-party document.
    heating_path: Literal["SELF_BILLING", "MDL_NET", "MDL_GROSS"] | None
    # German sentence naming the confirmed source document, on the MDL paths.
    heating_source_note: str | None
    heating_readiness: Literal["READY", "BLOCKED"]
    heating_findings: list[StatementFinding]
    heating_provenance: list[StatementProvenance]
    heating_device_evidence: list[StatementDeviceEvidence]
    heating_reduction_risks: list[StatementReductionRisk]
    annual_comparison: StatementAnnualComparison | None
    co2: StatementCo2 | None
    rechtsstaende: list[str]
    disclaimer: str


class StatementProjectionParty(ApiModel):
    """One party line of one cost, as the selected audience may see it."""

    party_label: str
    is_landlord: bool
    weight_display: str
    amount_cents: int
    amount_eur: str


class StatementProjectionCost(ApiModel):
    cost_id: str
    label: str
    key_label: str
    total_cents: int
    total_eur: str
    lines: list[StatementProjectionParty]


class StatementProjectionResponse(ApiModel):
    """One calculation projected to one audience (Page 01 § 4 D1, docs/02 § 5).

    Deliberately not `DemoStatementResponse` with a filter flag: the tenant view
    must be built from the selected result, never rendered whole and cropped
    (`docs/08` § 3). A field that is absent here cannot be leaked by a client
    that forgets to hide it.

    Advance evidence is owner-preview-only. An employee may calculate an
    assigned building's projection, but must not receive its advance evidence,
    reconciliation identity, or saldo.
    """

    audience: Literal["OWNER", "TENANT", "TAX"]
    tenancy_id: str | None
    building_name: str
    building_address: str
    period_label: str
    costs: list[StatementProjectionCost]
    heating_lines: list[StatementHeatingLine]
    # OWNER and TAX only; a renter's document carries no Eigentümeranteil.
    owner_residual_cents: int | None
    subtotal_cents: int | None
    actual_advances_cents: int | None
    saldo_cents: int | None
    advance_reconciliation_state: Literal["MISSING", "CONFIRMED"] | None
    reconciliation_id: str | None
    reconciliation_version: int | None
    findings: list[str]
    rechtsstaende: list[str]
    disclaimer: str


# ── M6-B finalized documents ────────────────────────────────────────────────


class DeliveryAddressCreate(ApiModel):
    addressee: str = Field(min_length=1, max_length=200)
    street: str = Field(min_length=1, max_length=200)
    postal_code: str = Field(min_length=1, max_length=30)
    city: str = Field(min_length=1, max_length=100)
    country: str = Field(min_length=1, max_length=100)
    valid_from: date


class PaymentInstructionCreate(ApiModel):
    payment_text: str = Field(min_length=1, max_length=2000)
    credit_text: str = Field(min_length=1, max_length=2000)
    valid_from: date


class FinalizeStatementCreate(ApiModel):
    period_start: date
    period_end: date
    draft_id: str | None = None
    draft_version: int | None = Field(default=None, ge=1)
    supersedes_statement_id: str | None = None
    late_positive_exception_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def period_is_ordered(self) -> "FinalizeStatementCreate":
        if self.period_end < self.period_start:
            raise ValueError("Das Ende liegt vor dem Beginn des Abrechnungszeitraums.")
        if (self.draft_id is None) != (self.draft_version is None):
            raise ValueError("Entwurf und Entwurfsversion müssen gemeinsam angegeben werden.")
        return self


class FinalizedDocumentOut(ApiModel):
    id: str
    audience: Literal["OWNER", "TENANT"]
    tenancy_id: str | None
    document_type: Literal["OWNER_OVERVIEW", "COVER_LETTER", "TENANT_STATEMENT"]
    filename: str
    sha256: str


class StatementHistoryOut(ApiModel):
    id: str
    version: int
    status: Literal["FINALIZED", "SUPERSEDED"]
    period_start: date
    period_end: date
    content_hash: str | None
    finalized_at: datetime | None
    supersedes_statement_id: str | None
    documents: list[FinalizedDocumentOut]


class FinalizeStatementOut(StatementHistoryOut):
    settlements: list[dict[str, object]]


# ── UI-05A resumable statement workflow ─────────────────────────────────────


class StatementDraftCreate(ApiModel):
    building_id: str
    period_start: date
    period_end: date
    title: str | None = Field(default=None, max_length=240)
    correction_of_statement_id: str | None = None
    correction_reason: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def period_is_ordered(self) -> "StatementDraftCreate":
        if self.period_end < self.period_start:
            raise ValueError("Das Ende liegt vor dem Beginn des Abrechnungszeitraums.")
        return self


class StatementDraftUpdate(ApiModel):
    version: int = Field(ge=1)
    title: str | None = Field(default=None, max_length=240)
    current_step: int | None = Field(default=None, ge=1, le=6)
    selected_unit_ids: list[str] | None = None
    overrides: dict[str, object] | None = None
    correction_reason: str | None = Field(default=None, max_length=1000)


class StatementDraftOut(ApiModel):
    id: str
    building_id: str
    building_name: str
    title: str
    period_start: date
    period_end: date
    status: Literal["DRAFT", "REVIEW_REQUIRED", "READY", "FINALIZED", "CANCELLED"]
    current_step: int
    version: int
    selected_unit_ids: list[str]
    overrides: dict[str, object]
    final_statement_id: str | None
    correction_of_statement_id: str | None
    correction_reason: str | None
    created_at: datetime
    updated_at: datetime


class StatementRecordOut(ApiModel):
    id: str
    kind: Literal["DRAFT", "FINAL"]
    building_id: str
    building_name: str
    title: str
    unit_count: int
    period_start: date
    period_end: date
    status: str
    result_summary: str
    created_at: datetime
    updated_at: datetime


class StatementPeriodSuggestionOut(ApiModel):
    period_start: date
    period_end: date
    label: str
    reason: str


class StatementReadinessFindingOut(ApiModel):
    code: str
    area: str
    severity: Literal["INFO", "WARNING", "BLOCKER"]
    entity_type: str | None = None
    entity_id: str | None = None
    message: str
    correction_route: str | None = None
    allowed_actions: list[str] = Field(default_factory=list)
    provenance: str | None = None


class StatementDraftUnitOut(ApiModel):
    unit_id: str
    tenancy_id: str | None
    label: str
    usage: str
    party: str
    period_label: str
    person_count: str
    area_sqm: str
    contractual_advance_cents: int | None
    actual_advances_cents: int | None
    saldo_cents: int | None
    included: bool
    status: Literal["READY", "WARNING", "BLOCKER"]


class StatementDraftCostOut(ApiModel):
    cost_id: str
    label: str
    period_label: str
    amount_cents: int
    allocable_cents: int
    allocation_key: str
    status: Literal["READY", "WARNING", "BLOCKER"]


class StatementDraftDocumentOut(ApiModel):
    key: str
    tenancy_id: str | None
    recipient: str
    document_type: str
    readiness: Literal["READY", "BLOCKED"]


class StatementDraftReadinessOut(ApiModel):
    draft: StatementDraftOut
    overall_status: Literal["DRAFT", "REVIEW_REQUIRED", "READY", "FINALIZED"]
    findings: list[StatementReadinessFindingOut]
    units: list[StatementDraftUnitOut]
    costs: list[StatementDraftCostOut]
    documents: list[StatementDraftDocumentOut]
    nk_total_cents: int | None
    heating_total_cents: int | None
    allocable_total_cents: int | None
    owner_total_cents: int | None
    heating_path: str | None


class MdlPositionIn(ApiModel):
    """One renter's amount as the Messdienstleister document states it."""

    tenancy_id: str
    amount_cents: int = Field(ge=0)


class MdlStatementCreate(ApiModel):
    """A confirmed Messdienstleister statement (docs/03 H7, docs/08 § 8).

    Every figure here is transcribed from a document a human read and
    confirmed — Lokara validates and passes it through, and never recomputes
    it. The control sum is checked server-side, which is what turns an OCR
    decimal shift into a block instead of a wrong statement (`01b-F29`).

    The CO₂ triple is required for the GROSS branch and forbidden for NET: a
    net document already had the landlord's share deducted, and deducting again
    is the defect `01b-F28a` exists to prevent.
    """

    branch: Literal["NET", "GROSS"]
    period_from: date
    period_to: date  # inclusive in the request, like every other period here
    confirmed_total_cents: int = Field(ge=0)
    owner_position_cents: int = Field(ge=0)
    positions: list[MdlPositionIn]
    source_ref: str = Field(min_length=1, max_length=200)
    co2_kg_x1000: int | None = None
    co2_cost_cents: int | None = None
    heated_area_sqm_x100: int | None = None
    co2_evidence_present: bool = True

    @model_validator(mode="after")
    def check_shape(self) -> "MdlStatementCreate":
        if self.period_to < self.period_from:
            raise ValueError("Das Ende des Abrechnungszeitraums liegt vor seinem Anfang.")
        if not self.positions:
            raise ValueError("Eine MDL-Abrechnung braucht mindestens eine Mieterposition.")
        seen = {position.tenancy_id for position in self.positions}
        if len(seen) != len(self.positions):
            raise ValueError("Jedes Mietverhältnis darf nur eine Position haben.")
        co2 = (self.co2_kg_x1000, self.co2_cost_cents, self.heated_area_sqm_x100)
        if self.branch == "GROSS" and any(value is None for value in co2):
            raise ValueError(
                "Eine Brutto-MDL-Abrechnung braucht CO₂-Menge, CO₂-Kosten und beheizte Fläche."
            )
        if self.branch == "NET" and any(value is not None for value in co2):
            raise ValueError(
                "Eine Netto-MDL-Abrechnung enthält den Vermieteranteil bereits; "
                "CO₂-Werte dürfen hier nicht erneut angesetzt werden."
            )
        return self


class MdlStatementOut(ApiModel):
    id: str
    branch: Literal["NET", "GROSS"]
    period_label: str
    confirmed_total_cents: int
    owner_position_cents: int
    position_count: int
    source_ref: str
    version: int
