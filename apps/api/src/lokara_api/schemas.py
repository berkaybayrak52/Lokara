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
