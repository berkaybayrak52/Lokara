"""SQLAlchemy 2.0 models — identity three-layer + temporal core (docs/02).

Conventions:
- snake_case tables/columns. The Prisma-era quoted-PascalCase tables ("Building" …)
  coexist in the same database until Phase H removes them — no name collisions.
- Every domain row carries account_id (the isolation boundary; the RLS backstop
  lives in the Alembic migration). Person is global — Supabase Auth maps onto it.
- Every foreign key between two account-scoped tables is composite on
  (id, account_id) — see `_scoped_fk` below and docs/02 → "Isolation rule".
- Day-granular validity (valid_from/valid_to) is DATE, half-open like the engines'
  Period; audit timestamps are timestamptz.
- Money is integer cents; areas are m² × 100 integers. Never floats.
- Statement is immutable + versioned: a correction inserts version n+1 and marks
  the predecessor SUPERSEDED — never UPDATE a FINALIZED row (GoBD / § 147 AO).
"""

import enum
from datetime import date, datetime

from lokara_domain import (
    AllocationKey,
    MeasurementUnit,
    MeterKind,
    ReadingReason,
    ReadingSource,
)
from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
    func,
    select,
)
from sqlalchemy import Enum as SaEnum
from sqlalchemy.engine.default import DefaultExecutionContext
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .ids import new_id


def _scoped_fk(
    child: str, column: str, parent: str, *, ondelete: str | None = None
) -> ForeignKeyConstraint:
    """`FOREIGN KEY (column, account_id) REFERENCES parent (id, account_id)`.

    docs/02 → "Isolation rule". Postgres enforces referential integrity with RLS
    **bypassed**: the check runs as a system operation and never consults a policy.
    A row that stamps its own `account_id` correctly — and so passes `WITH CHECK` —
    can still point this link at a parent owned by another account. Spanning both
    columns is what makes such an edge unrepresentable; the parent carries the
    matching `UniqueConstraint("id", "account_id")` that this pair references.

    `match="SIMPLE"` is explicit and load-bearing: `account_id` is NOT NULL, so
    MATCH FULL would demand all-or-nothing across the two columns and silently turn
    every optional link (`meter.unit_id`, `building.landlord_id`, the `direct_*`
    columns) into a mandatory one. SIMPLE leaves an unset link unchecked and every
    set link checked, which is exactly the intended meaning.

    The name matches the single-column constraint this replaced (migration 0004),
    so the schema reads the same as before — same edge, wider reference.
    """
    return ForeignKeyConstraint(
        [column, "account_id"],
        [f"{parent}.id", f"{parent}.account_id"],
        name=f"{child}_{column}_fkey",
        ondelete=ondelete,
        match="SIMPLE",
    )


def _scoped_pair(parent: str) -> UniqueConstraint:
    """`UNIQUE (id, account_id)` — redundant against the primary key, and that is
    the point: a composite FK can only target a unique constraint, so this is what
    makes the *pair* referenceable by `_scoped_fk`."""
    return UniqueConstraint("id", "account_id", name=f"uq_{parent}_id_account")


def _account_id_of_membership(context: DefaultExecutionContext) -> str | None:
    """Derive `building_assignment.account_id` from the membership it links.

    The column is a denormalisation of `membership.account_id` (decision: docs/02 →
    "Isolation rule"), and it cannot drift, because the composite FK
    `(membership_id, account_id) → membership (id, account_id)` means a disagreeing
    pair does not exist in the parent. Deriving it here means a caller never has to
    restate what the membership already says.

    The lookup runs on the inserting connection, so it is subject to the same RLS
    context as the write: a membership the caller cannot see yields NULL, and the
    NOT NULL column refuses the row. The refusal stays in the database — one
    enforcement point, not a second one in Python that could disagree with it.
    """
    # `current_parameters` rather than `get_current_parameters()`: the latter is
    # unannotated in SQLAlchemy (mypy --strict rejects the call), and the two differ
    # only for multi-valued INSERT constructs, which this mapping never emits.
    parameters = context.current_parameters or {}
    membership_id = parameters.get("membership_id")
    account_id: str | None = context.connection.scalar(
        select(Membership.account_id).where(Membership.id == membership_id)
    )
    return account_id


# A note on the `overlaps=` arguments below: a composite FK makes each relationship
# carry `account_id` into its child alongside the id link, so a child with two
# scoped parents (meter → building + unit, tenancy_party → tenancy + renter) has two
# relationships writing that one column. SQLAlchemy warns about the shape because
# the two writers could disagree — here they cannot: either both parents are in the
# same account, or the composite FK rejects the row outright. `overlaps=` records
# that the sharing is intended; it silences nothing else.


class AccountShape(enum.Enum):
    SOLO = "SOLO"
    HAUSVERWALTUNG = "HAUSVERWALTUNG"


class Plan(enum.Enum):
    TRIAL = "TRIAL"
    SOLO_S = "SOLO_S"
    SOLO_M = "SOLO_M"
    SOLO_L = "SOLO_L"
    TEAM = "TEAM"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


class Role(enum.Enum):
    """No RENTER by design — a renter is domain data scoped to a Tenancy (docs/02)."""

    OWNER = "OWNER"
    EMPLOYEE = "EMPLOYEE"
    TAX_ADVISOR = "TAX_ADVISOR"


class StatementStatus(enum.Enum):
    DRAFT = "DRAFT"
    FINALIZED = "FINALIZED"
    SUPERSEDED = "SUPERSEDED"


class SelfUseKind(enum.Enum):
    OWNER_OCCUPIED = "OWNER_OCCUPIED"
    FREE_OF_CHARGE = "FREE_OF_CHARGE"


class Base(DeclarativeBase):
    # SQLAlchemy's documented idiom is a plain class attribute (read once at
    # mapper configuration, never mutated).
    type_annotation_map = {  # noqa: RUF012
        datetime: DateTime(timezone=True),
        date: Date(),
        AccountShape: SaEnum(AccountShape, name="account_shape"),
        Plan: SaEnum(Plan, name="plan"),
        Role: SaEnum(Role, name="role"),
        StatementStatus: SaEnum(StatementStatus, name="statement_status"),
        SelfUseKind: SaEnum(SelfUseKind, name="self_use_kind"),
        AllocationKey: SaEnum(AllocationKey, name="allocation_key"),
        MeterKind: SaEnum(MeterKind, name="meter_kind"),
        MeasurementUnit: SaEnum(MeasurementUnit, name="measurement_unit"),
        ReadingReason: SaEnum(ReadingReason, name="reading_reason"),
        ReadingSource: SaEnum(ReadingSource, name="reading_source"),
    }


# ── Layer 1: Person — the login (one human). Global, not owned by any account. ──


class Person(Base):
    __tablename__ = "person"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    memberships: Mapped[list["Membership"]] = relationship(back_populates="person")
    renter_links: Mapped[list["Renter"]] = relationship(back_populates="person")


# ── Layer 2: Account — workspace + billing + the isolation boundary. ──
# NOT the German Mieter (that is Renter) and carries no personal role.


class Account(Base):
    __tablename__ = "account"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    name: Mapped[str]
    shape: Mapped[AccountShape] = mapped_column(default=AccountShape.SOLO)
    plan: Mapped[Plan] = mapped_column(default=Plan.TRIAL)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    memberships: Mapped[list["Membership"]] = relationship(back_populates="account")
    landlords: Mapped[list["Landlord"]] = relationship(back_populates="account")
    renters: Mapped[list["Renter"]] = relationship(back_populates="account")


# ── Layer 3: Membership — Person → Account, carrying the Role. ──


class Membership(Base):
    __tablename__ = "membership"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    person_id: Mapped[str] = mapped_column(ForeignKey("person.id"))
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    role: Mapped[Role]
    invited_at: Mapped[datetime] = mapped_column(server_default=func.now())
    accepted_at: Mapped[datetime | None]
    revoked_at: Mapped[datetime | None]  # revoke, never hard-delete (GoBD + DSGVO)

    person: Mapped["Person"] = relationship(back_populates="memberships")
    account: Mapped["Account"] = relationship(back_populates="memberships")
    building_assignments: Mapped[list["BuildingAssignment"]] = relationship(
        back_populates="membership"
    )  # only meaningful for EMPLOYEE; zero assignments ⇒ sees nothing

    __table_args__ = (
        # DECISION (docs/02): one role per person per account — start strict.
        UniqueConstraint("person_id", "account_id"),
        _scoped_pair("membership"),
        Index("ix_membership_account", "account_id"),
    )


class BuildingAssignment(Base):
    """Which of the account's buildings an EMPLOYEE membership may work on.

    `account_id` is a copy of `membership.account_id`. It is denormalised on
    purpose (docs/02 → "Isolation rule"): transitive scoping made this the one
    tenant table whose RLS policy joined another table, and — more importantly —
    left its `building_id` unchecked against any account at all, so an assignment
    could grant an employee of account B a building owned by account A. The copy
    cannot drift, because the composite FK to `membership (id, account_id)` means a
    disagreeing pair does not exist in the parent.
    """

    __tablename__ = "building_assignment"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(
        ForeignKey("account.id"), default=_account_id_of_membership
    )
    membership_id: Mapped[str]
    building_id: Mapped[str]

    membership: Mapped["Membership"] = relationship(back_populates="building_assignments")

    __table_args__ = (
        _scoped_fk("building_assignment", "membership_id", "membership", ondelete="CASCADE"),
        _scoped_fk("building_assignment", "building_id", "building"),
        UniqueConstraint("membership_id", "building_id"),
        Index("ix_building_assignment_account", "account_id"),
    )


# ── Vermieter: a DATA entity (the legal lessor on statements), not a role. ──


class Landlord(Base):
    __tablename__ = "landlord"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    legal_name: Mapped[str]
    address: Mapped[str]

    account: Mapped["Account"] = relationship(back_populates="landlords")
    buildings: Mapped[list["Building"]] = relationship(back_populates="landlord")

    __table_args__ = (
        _scoped_pair("landlord"),
        Index("ix_landlord_account", "account_id"),
    )


# ── Mieter: domain entity; portal login OPTIONAL via person_id (set at M5). ──


class Renter(Base):
    __tablename__ = "renter"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    legal_name: Mapped[str]
    email: Mapped[str | None]
    person_id: Mapped[str | None] = mapped_column(ForeignKey("person.id"))

    account: Mapped["Account"] = relationship(back_populates="renters")
    person: Mapped["Person | None"] = relationship(back_populates="renter_links")
    tenancy_parties: Mapped[list["TenancyParty"]] = relationship(back_populates="renter")

    __table_args__ = (
        _scoped_pair("renter"),
        Index("ix_renter_account", "account_id"),
        Index("ix_renter_person", "person_id"),
    )


# ── Temporal core: Building → Unit → Tenancy. ──


class Building(Base):
    __tablename__ = "building"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    # Nullable: the Landlord entity may be filled in after the building exists.
    landlord_id: Mapped[str | None]
    name: Mapped[str]
    street: Mapped[str]
    postal_code: Mapped[str]
    city: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    landlord: Mapped["Landlord | None"] = relationship(back_populates="buildings")
    units: Mapped[list["Unit"]] = relationship(back_populates="building")
    statements: Mapped[list["Statement"]] = relationship(back_populates="building")
    cost_entries: Mapped[list["CostEntry"]] = relationship(back_populates="building")
    meters: Mapped[list["Meter"]] = relationship(back_populates="building")
    heating_cost_entries: Mapped[list["HeatingCostEntry"]] = relationship(
        back_populates="building"
    )

    __table_args__ = (
        _scoped_fk("building", "landlord_id", "landlord"),
        _scoped_pair("building"),
        Index("ix_building_account", "account_id"),
    )


class Unit(Base):
    __tablename__ = "unit"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    building_id: Mapped[str]
    label: Mapped[str]
    # Wohnfläche in m² × 100 (integer — no floats anywhere near allocation math).
    area_sqm_x100: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    building: Mapped["Building"] = relationship(back_populates="units")
    tenancies: Mapped[list["Tenancy"]] = relationship(back_populates="unit")
    self_use_periods: Mapped[list["SelfUsePeriod"]] = relationship(back_populates="unit")
    meters: Mapped[list["Meter"]] = relationship(back_populates="unit", overlaps="meters")

    __table_args__ = (
        _scoped_fk("unit", "building_id", "building"),
        _scoped_pair("unit"),
        Index("ix_unit_account", "account_id"),
        Index("ix_unit_building", "building_id"),
    )


class Tenancy(Base):
    """A lease over a period; valid_to NULL = still running (half-open, like Period).
    Renters attach via TenancyParty — multi-party leases are an entry ticket."""

    __tablename__ = "tenancy"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    unit_id: Mapped[str]
    valid_from: Mapped[date]
    valid_to: Mapped[date | None]
    base_rent_cents: Mapped[int]  # Kaltmiete
    advance_payment_cents: Mapped[int]  # monthly NK Vorauszahlung
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    unit: Mapped["Unit"] = relationship(back_populates="tenancies")
    parties: Mapped[list["TenancyParty"]] = relationship(
        back_populates="tenancy", overlaps="tenancy_parties"
    )

    __table_args__ = (
        _scoped_fk("tenancy", "unit_id", "unit"),
        _scoped_pair("tenancy"),
        Index("ix_tenancy_account", "account_id"),
        Index("ix_tenancy_unit", "unit_id"),
    )


class TenancyParty(Base):
    __tablename__ = "tenancy_party"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    tenancy_id: Mapped[str]
    renter_id: Mapped[str]

    tenancy: Mapped["Tenancy"] = relationship(
        back_populates="parties", overlaps="tenancy_parties"
    )
    renter: Mapped["Renter"] = relationship(
        back_populates="tenancy_parties", overlaps="parties,tenancy"
    )

    __table_args__ = (
        _scoped_fk("tenancy_party", "tenancy_id", "tenancy"),
        _scoped_fk("tenancy_party", "renter_id", "renter"),
        UniqueConstraint("tenancy_id", "renter_id"),
        Index("ix_tenancy_party_account", "account_id"),
    )


# ── Eigennutzung: an AREA with a period, never a Renter row (docs/02). ──
# Only SELF_USED is stored; RENTED derives from tenancies; VACANT is the remainder.


class SelfUsePeriod(Base):
    __tablename__ = "self_use_period"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    # docs/02's sketch omits account_id here, but "every domain row carries
    # account_id" (same doc, principle 1) and the RLS plan scopes this table by it.
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    unit_id: Mapped[str]
    sqm_x100: Mapped[int]  # self-used m² × 100 — an area, not a flag
    kind: Mapped[SelfUseKind] = mapped_column(default=SelfUseKind.OWNER_OCCUPIED)
    note: Mapped[str | None]
    valid_from: Mapped[date]
    valid_to: Mapped[date | None]

    unit: Mapped["Unit"] = relationship(back_populates="self_use_periods")

    __table_args__ = (
        _scoped_fk("self_use_period", "unit_id", "unit"),
        Index("ix_self_use_account", "account_id"),
        Index("ix_self_use_unit", "unit_id"),
    )


# ── Immutable statement pattern. ──


class Statement(Base):
    """A generated Abrechnung. Rows are never updated or deleted — a correction
    inserts version n+1 and marks the predecessor SUPERSEDED (the only permitted
    status transition; enforced in app logic)."""

    __tablename__ = "statement"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    building_id: Mapped[str]
    period_start: Mapped[date]
    period_end: Mapped[date]
    version: Mapped[int] = mapped_column(default=1)
    status: Mapped[StatementStatus] = mapped_column(default=StatementStatus.DRAFT)
    total_cents: Mapped[int]
    content_hash: Mapped[str | None]  # SHA-256 of the rendered document, set on finalize (GoBD)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    building: Mapped["Building"] = relationship(back_populates="statements")

    __table_args__ = (
        _scoped_fk("statement", "building_id", "building"),
        UniqueConstraint("building_id", "period_start", "period_end", "version"),
        Index("ix_statement_account", "account_id"),
    )


# ── Kosten erfassen (docs/04 M3 page 4). ──


class CostEntry(Base):
    """One operating cost of a building over a period (half-open, like every
    validity range). The allocation key is deliberately NOT a column here — it
    lives in versioned AllocationKeyAssignment rows, so re-keying a cost never
    touches (let alone deletes) the entered data."""

    __tablename__ = "cost_entry"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    building_id: Mapped[str]
    label: Mapped[str]
    amount_cents: Mapped[int]
    period_from: Mapped[date]
    period_to: Mapped[date]  # exclusive
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    building: Mapped["Building"] = relationship(back_populates="cost_entries")
    key_assignments: Mapped[list["AllocationKeyAssignment"]] = relationship(
        back_populates="cost_entry"
    )

    __table_args__ = (
        _scoped_fk("cost_entry", "building_id", "building"),
        _scoped_pair("cost_entry"),
        Index("ix_cost_entry_account", "account_id"),
        Index("ix_cost_entry_building", "building_id"),
    )


class AllocationKeyAssignment(Base):
    """The Umlageschlüssel of one cost, as an append-only version history:
    changing the key INSERTs a new row (latest created_at wins) — the old
    assignment stays for the audit trail, and no cost data is ever deleted."""

    __tablename__ = "allocation_key_assignment"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    cost_entry_id: Mapped[str]
    key: Mapped[AllocationKey]
    # Only for key = DIRECT: the single target the cost bypasses allocation to.
    direct_unit_id: Mapped[str | None]
    direct_tenancy_id: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    cost_entry: Mapped["CostEntry"] = relationship(back_populates="key_assignments")

    __table_args__ = (
        _scoped_fk("allocation_key_assignment", "cost_entry_id", "cost_entry"),
        _scoped_fk("allocation_key_assignment", "direct_unit_id", "unit"),
        _scoped_fk("allocation_key_assignment", "direct_tenancy_id", "tenancy"),
        Index("ix_aka_account", "account_id"),
        Index("ix_aka_cost_entry", "cost_entry_id"),
    )


# ── Zähler (docs/04 M3 page 5): meters, readings, heating-system costs. ──


class Meter(Base):
    """A measuring device. ``unit_id`` NULL = a building-level Hauptzähler
    (the Wärmemengenzähler whose kWh are the § 9 HeizkostenV denominator).

    ``calibration_valid_until`` is the **Eichfrist** (MessEG/MessEV): 5 years
    for Wärme- and Warmwasserzähler, 6 for Kaltwasserzähler. It is NULL for
    Heizkostenverteiler, which are not eichpflichtig — a null therefore means
    "not applicable", never "unknown". Whether it has expired is *computed*
    from it, never stored (CLAUDE.md: one guard pattern, no denormalized flags).
    """

    __tablename__ = "meter"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    building_id: Mapped[str]
    unit_id: Mapped[str | None]
    kind: Mapped[MeterKind]
    measurement_unit: Mapped[MeasurementUnit]
    serial: Mapped[str]  # Zählernummer as printed on the device
    label: Mapped[str | None]  # e.g. "Küche" when a flat has several
    calibration_valid_until: Mapped[date | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    building: Mapped["Building"] = relationship(back_populates="meters", overlaps="meters")
    unit: Mapped["Unit | None"] = relationship(
        back_populates="meters", overlaps="building,meters"
    )
    readings: Mapped[list["MeterReading"]] = relationship(back_populates="meter")

    __table_args__ = (
        _scoped_fk("meter", "building_id", "building"),
        _scoped_fk("meter", "unit_id", "unit"),
        _scoped_pair("meter"),
        UniqueConstraint("building_id", "serial"),
        Index("ix_meter_account", "account_id"),
        Index("ix_meter_building", "building_id"),
        Index("ix_meter_unit", "unit_id"),
    )


class MeterReading(Base):
    """A point-in-time register value — **create-only**.

    A wrong value is corrected by inserting a new row for the same ``read_at``
    with ``reason = CORRECTION``; the later ``recorded_at`` wins and the
    original stays as evidence. Nothing here is ever UPDATEd or deleted, which
    is what lets a statement be re-derived exactly as it was billed.

    ``value_x1000`` is the register value × 1000 (integer, like every other
    fixed-point quantity here) — 241,5 m³ is stored as 241500. Floats never
    touch a consumption that ends up in money.
    """

    __tablename__ = "meter_reading"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    meter_id: Mapped[str]
    read_at: Mapped[date]
    value_x1000: Mapped[int] = mapped_column(BigInteger)
    reason: Mapped[ReadingReason]
    source: Mapped[ReadingSource]
    note: Mapped[str | None]
    recorded_at: Mapped[datetime] = mapped_column(server_default=func.now())

    meter: Mapped["Meter"] = relationship(back_populates="readings")

    __table_args__ = (
        _scoped_fk("meter_reading", "meter_id", "meter"),
        Index("ix_meter_reading_account", "account_id"),
        Index("ix_meter_reading_meter", "meter_id"),
    )


class HeatingCostEntry(Base):
    """The heating-system invoice for a period (Brennstoff, Wartung,
    Betriebsstrom …).

    Deliberately NOT a `CostEntry`: heating costs carry no Umlageschlüssel —
    §§ 7–9 HeizkostenV dictate their split, so offering an AllocationKey here
    would be legally wrong. The CO₂ figures come off the same fuel invoice
    (mandatory disclosure since 2023) and drive the CO2KostAufG split; both are
    nullable because a Wärmelieferung invoice may not state them.
    """

    __tablename__ = "heating_cost_entry"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    building_id: Mapped[str]
    label: Mapped[str]
    amount_cents: Mapped[int]  # total, INCLUDING the CO₂ portion below
    period_from: Mapped[date]
    period_to: Mapped[date]  # exclusive
    co2_kg_x1000: Mapped[int | None] = mapped_column(BigInteger)
    co2_cost_cents: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    building: Mapped["Building"] = relationship(back_populates="heating_cost_entries")

    __table_args__ = (
        _scoped_fk("heating_cost_entry", "building_id", "building"),
        Index("ix_heating_cost_account", "account_id"),
        Index("ix_heating_cost_building", "building_id"),
    )


# Tables scoped by their own account_id column — the Alembic migration enables
# FORCEd RLS on each of these plus `account` (scoped by its own id) and
# `building_assignment`. The latter carries account_id too since migration 0004,
# but stays out of this tuple: it is not domain data, it is the employee↔building
# grant, and docs/02 keeps it listed as its own case. `person` is global by design.
ACCOUNT_SCOPED_TABLES: tuple[str, ...] = (
    "membership",
    "landlord",
    "renter",
    "building",
    "unit",
    "tenancy",
    "tenancy_party",
    "self_use_period",
    "statement",
    "cost_entry",
    "allocation_key_assignment",
    "meter",
    "meter_reading",
    "heating_cost_entry",
)
