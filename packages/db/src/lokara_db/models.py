"""SQLAlchemy 2.0 models — identity three-layer + temporal core (docs/02).

Conventions:
- snake_case tables/columns. The Prisma-era quoted-PascalCase tables ("Building" …) were
  removed with the pre-migration TypeScript; nothing in the database uses them today.
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
    JSON,
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import Enum as SaEnum
from sqlalchemy.dialects.postgresql import ExcludeConstraint
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


def _scoped_tenancy_fk(child: str, column: str, parent: str) -> ForeignKeyConstraint:
    """Keep an advance edge on the parent payment/period's tenancy as well.

    Account-scoped pairs stop cross-account links.  Advance corrections and
    allocations also carry a tenancy, so their referenced row must be for that
    same tenancy: accepting a same-account but different lease would attach
    money to the wrong statement.
    """
    return ForeignKeyConstraint(
        [column, "tenancy_id", "account_id"],
        [f"{parent}.id", f"{parent}.tenancy_id", f"{parent}.account_id"],
        name=f"{child}_{column}_fkey",
        match="SIMPLE",
    )


def _scoped_account_pair_fk(child: str, column: str, parent: str) -> ForeignKeyConstraint:
    """Retain the standard account-scoped edge beside a stricter tenancy edge.

    The pair is the project-wide isolation vocabulary and remains visible to
    schema tooling.  The matching three-column advance edge above additionally
    rejects a same-account link to another tenancy.
    """
    return ForeignKeyConstraint(
        [column, "account_id"],
        [f"{parent}.id", f"{parent}.account_id"],
        name=f"{child}_{column}_account_fkey",
        match="SIMPLE",
    )


# A note on the explicit `primaryjoin=` / `foreign_keys=` on every relationship that
# sits on a `_scoped_fk` below. Left to itself, SQLAlchemy reflects the composite
# constraint and joins on **both** columns, which puts `account_id` into the local
# column set of every many-to-one relationship: it then belongs to `Meter.building`
# *and* to `Meter.unit`, and a relationship set to — or left at — `None` synchronises
# a NULL over it (`UPDATE meter SET account_id=NULL, unit_id=NULL …`). That destroys
# the tenant key of a building-level Hauptzähler (`meter.unit_id IS NULL`, the § 9
# HeizkostenV denominator) even when the caller stated `account_id` explicitly.
#
# So each relationship names only the id column it owns. `account_id` is written by
# the caller, never by a relationship — the same explicit-`account_id` rule every
# other table follows — and the composite FK in `__table_args__` is what makes a
# wrong value impossible. The constraint is unchanged and still spans both columns;
# only what the ORM *synchronises* is narrowed.
#
# Consequence: `overlaps=` is gone. It was needed because two relationships wrote the
# one shared `account_id` column; no relationship writes it any more, so nothing
# overlaps. The collections stay writable (appending sets the id column, as it always
# did) — they simply no longer supply `account_id`, which is the point.


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


class MdlBranch(enum.Enum):
    """Whether a confirmed Messdienstleister statement is net or gross of CO₂.

    The two are different arithmetic, not a display flag (`docs/03` H7): a NET
    statement already had the landlord's CO₂ share deducted and must not be
    deducted from twice, while a GROSS one is rescaled by the exact quotient
    after the split. Which one a document is cannot be inferred from its
    figures, so it is confirmed by the person reading the document.
    """

    NET = "NET"
    GROSS = "GROSS"


class FiktivbelegungMode(enum.Enum):
    """How a vacant unit's fictional person occupancy is counted (Page 01 § 4 D0).

    Source names, kept in the repository's UPPER convention:
    `letzteBelegung` → `LETZTE_BELEGUNG`, `immer1` → `IMMER_1`, `keine` → `KEINE`.
    It sits on the object (`objekt.fiktivbelegungModus`, Page 01 § 3.5), defaults
    to `LETZTE_BELEGUNG`, and `KEINE` is only lawful with a logged confirmation —
    which is why `Building` carries a waiver note and a CHECK that demands one.
    The pair is immutable after creation: changing a current scalar would rewrite
    the denominator of a closed billing period. A future changed-mode workflow
    must introduce an explicitly effective-dated resolution instead.

    `Konvention`, `verify-before-production`, Rechtsstand 07/2026. It is a Lokara
    convention over split instance case law (LG Krefeld 2 S 56/09; BGH VIII ZR
    180/12 leaves the Ansatz a Tatfrage), never settled law, and no output may
    present it as one. See `docs/02` § 5 "D0 Fiktivbelegung".
    """

    LETZTE_BELEGUNG = "LETZTE_BELEGUNG"
    IMMER_1 = "IMMER_1"
    KEINE = "KEINE"


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
        FiktivbelegungMode: SaEnum(FiktivbelegungMode, name="fiktivbelegung_mode"),
        MdlBranch: SaEnum(MdlBranch, name="mdl_branch"),
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
        back_populates="membership",
        primaryjoin="Membership.id == BuildingAssignment.membership_id",
        foreign_keys="BuildingAssignment.membership_id",
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
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    membership_id: Mapped[str]
    building_id: Mapped[str]

    membership: Mapped["Membership"] = relationship(
        back_populates="building_assignments",
        primaryjoin="Membership.id == BuildingAssignment.membership_id",
        foreign_keys="BuildingAssignment.membership_id",
    )

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
    buildings: Mapped[list["Building"]] = relationship(
        back_populates="landlord",
        primaryjoin="Landlord.id == Building.landlord_id",
        foreign_keys="Building.landlord_id",
    )

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
    tenancy_parties: Mapped[list["TenancyParty"]] = relationship(
        back_populates="renter",
        primaryjoin="Renter.id == TenancyParty.renter_id",
        foreign_keys="TenancyParty.renter_id",
    )

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
    # Page 01 § 3.5 `objekt.fiktivbelegungModus` — Stammdaten of the object, not
    # of a unit or a run, because one building bills one way (docs/02 § 5 D0).
    # Migration 0009 makes this and its waiver note immutable after creation, so
    # a later edit cannot change a historical person-key denominator.
    fiktivbelegung_mode: Mapped[FiktivbelegungMode] = mapped_column(
        default=FiktivbelegungMode.LETZTE_BELEGUNG,
        server_default=FiktivbelegungMode.LETZTE_BELEGUNG.value,
    )
    # Page 01 E18: `keine` is permitted "only with logged confirmation", after a
    # hard warning naming the case law — without the fiction the renters carry
    # 100 % of the person-keyed fixed costs, which is what BGH VIII ZR 159/05 and
    # LG Krefeld 2 S 56/09 reject. The CHECK below makes the log a precondition
    # of the mode rather than a step someone can skip.
    fiktivbelegung_waiver_note: Mapped[str | None]
    # Reset may retire a rehearsal building whose immutable cost evidence must
    # remain referentially intact. Archived buildings never enter normal
    # object routes or statement work.
    archived_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    landlord: Mapped["Landlord | None"] = relationship(
        back_populates="buildings",
        primaryjoin="Landlord.id == Building.landlord_id",
        foreign_keys="Building.landlord_id",
    )
    units: Mapped[list["Unit"]] = relationship(
        back_populates="building",
        primaryjoin="Building.id == Unit.building_id",
        foreign_keys="Unit.building_id",
    )
    statements: Mapped[list["Statement"]] = relationship(
        back_populates="building",
        primaryjoin="Building.id == Statement.building_id",
        foreign_keys="Statement.building_id",
    )
    cost_entries: Mapped[list["CostEntry"]] = relationship(
        back_populates="building",
        primaryjoin="Building.id == CostEntry.building_id",
        foreign_keys="CostEntry.building_id",
    )
    meters: Mapped[list["Meter"]] = relationship(
        back_populates="building",
        primaryjoin="Building.id == Meter.building_id",
        foreign_keys="Meter.building_id",
    )
    heating_cost_entries: Mapped[list["HeatingCostEntry"]] = relationship(
        back_populates="building",
        primaryjoin="Building.id == HeatingCostEntry.building_id",
        foreign_keys="HeatingCostEntry.building_id",
    )
    mdl_statements: Mapped[list["MdlStatement"]] = relationship(
        back_populates="building",
        primaryjoin="Building.id == MdlStatement.building_id",
        foreign_keys="MdlStatement.building_id",
    )

    __table_args__ = (
        _scoped_fk("building", "landlord_id", "landlord"),
        _scoped_pair("building"),
        CheckConstraint(
            "fiktivbelegung_mode <> 'KEINE' OR fiktivbelegung_waiver_note IS NOT NULL",
            name="ck_building_fiktivbelegung_waiver_logged",
        ),
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

    building: Mapped["Building"] = relationship(
        back_populates="units",
        primaryjoin="Building.id == Unit.building_id",
        foreign_keys="Unit.building_id",
    )
    tenancies: Mapped[list["Tenancy"]] = relationship(
        back_populates="unit",
        primaryjoin="Unit.id == Tenancy.unit_id",
        foreign_keys="Tenancy.unit_id",
    )
    self_use_periods: Mapped[list["SelfUsePeriod"]] = relationship(
        back_populates="unit",
        primaryjoin="Unit.id == SelfUsePeriod.unit_id",
        foreign_keys="SelfUsePeriod.unit_id",
    )
    meters: Mapped[list["Meter"]] = relationship(
        back_populates="unit",
        primaryjoin="Unit.id == Meter.unit_id",
        foreign_keys="Meter.unit_id",
    )

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
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    unit: Mapped["Unit"] = relationship(
        back_populates="tenancies",
        primaryjoin="Unit.id == Tenancy.unit_id",
        foreign_keys="Tenancy.unit_id",
    )
    parties: Mapped[list["TenancyParty"]] = relationship(
        back_populates="tenancy",
        primaryjoin="Tenancy.id == TenancyParty.tenancy_id",
        foreign_keys="TenancyParty.tenancy_id",
    )
    person_counts: Mapped[list["PersonCount"]] = relationship(
        back_populates="tenancy",
        primaryjoin="Tenancy.id == PersonCount.tenancy_id",
        foreign_keys="PersonCount.tenancy_id",
    )
    operating_cost_agreements: Mapped[list["OperatingCostAgreement"]] = relationship(
        back_populates="tenancy",
        primaryjoin="Tenancy.id == OperatingCostAgreement.tenancy_id",
        foreign_keys="OperatingCostAgreement.tenancy_id",
    )
    advance_payment_periods: Mapped[list["AdvancePaymentPeriod"]] = relationship(
        back_populates="tenancy",
        primaryjoin="Tenancy.id == AdvancePaymentPeriod.tenancy_id",
        foreign_keys="AdvancePaymentPeriod.tenancy_id",
    )
    advance_reconciliations: Mapped[list["AdvanceReconciliation"]] = relationship(
        back_populates="tenancy",
        primaryjoin="Tenancy.id == AdvanceReconciliation.tenancy_id",
        foreign_keys="AdvanceReconciliation.tenancy_id",
    )

    __table_args__ = (
        _scoped_fk("tenancy", "unit_id", "unit"),
        _scoped_pair("tenancy"),
        Index("ix_tenancy_account", "account_id"),
        Index("ix_tenancy_unit", "unit_id"),
    )


class AdvancePaymentPeriod(Base):
    """Append-only contractual Soll schedule; its end is the next successor's start."""

    __tablename__ = "advance_payment_period"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    tenancy_id: Mapped[str]
    amount_cents: Mapped[int]
    valid_from: Mapped[date]
    predecessor_id: Mapped[str | None]
    declaration_ref: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    tenancy: Mapped["Tenancy"] = relationship(
        back_populates="advance_payment_periods",
        primaryjoin="Tenancy.id == AdvancePaymentPeriod.tenancy_id",
        foreign_keys="AdvancePaymentPeriod.tenancy_id",
    )

    __table_args__ = (
        _scoped_fk("advance_payment_period", "tenancy_id", "tenancy", ondelete="CASCADE"),
        _scoped_tenancy_fk("advance_payment_period", "predecessor_id", "advance_payment_period"),
        _scoped_account_pair_fk(
            "advance_payment_period", "predecessor_id", "advance_payment_period"
        ),
        _scoped_pair("advance_payment_period"),
        UniqueConstraint(
            "id", "tenancy_id", "account_id", name="uq_advance_payment_period_id_tenancy_account"
        ),
        CheckConstraint("amount_cents >= 0", name="ck_advance_payment_period_non_negative"),
        UniqueConstraint(
            "tenancy_id", "valid_from", name="uq_advance_payment_period_tenancy_start"
        ),
        Index("ix_advance_payment_period_account", "account_id"),
        Index("ix_advance_payment_period_tenancy", "tenancy_id"),
    )


class AdvancePayment(Base):
    """Manually accepted money evidence. Reversals are positive rows with a direction."""

    __tablename__ = "advance_payment"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    tenancy_id: Mapped[str]
    amount_cents: Mapped[int]
    payment_date: Mapped[date]
    evidence_ref: Mapped[str]
    accepted_at: Mapped[datetime] = mapped_column(server_default=func.now())
    reversal_of_id: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        _scoped_fk("advance_payment", "tenancy_id", "tenancy"),
        _scoped_tenancy_fk("advance_payment", "reversal_of_id", "advance_payment"),
        _scoped_account_pair_fk("advance_payment", "reversal_of_id", "advance_payment"),
        _scoped_pair("advance_payment"),
        UniqueConstraint(
            "id", "tenancy_id", "account_id", name="uq_advance_payment_id_tenancy_account"
        ),
        CheckConstraint("amount_cents > 0", name="ck_advance_payment_positive"),
        Index(
            "uq_advance_payment_one_reversal",
            "reversal_of_id",
            unique=True,
            postgresql_where=text("reversal_of_id IS NOT NULL"),
        ),
        Index("ix_advance_payment_account", "account_id"),
        Index("ix_advance_payment_tenancy", "tenancy_id"),
    )


class AdvanceAllocation(Base):
    """A payment's accepted allocation to one inclusive billing period."""

    __tablename__ = "advance_allocation"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    payment_id: Mapped[str]
    tenancy_id: Mapped[str]
    period_start: Mapped[date]
    period_end: Mapped[date]
    amount_cents: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        _scoped_tenancy_fk("advance_allocation", "payment_id", "advance_payment"),
        _scoped_account_pair_fk("advance_allocation", "payment_id", "advance_payment"),
        _scoped_fk("advance_allocation", "tenancy_id", "tenancy"),
        _scoped_pair("advance_allocation"),
        CheckConstraint("amount_cents > 0", name="ck_advance_allocation_positive"),
        CheckConstraint("period_end >= period_start", name="ck_advance_allocation_period_ordered"),
        Index("ix_advance_allocation_account", "account_id"),
        Index("ix_advance_allocation_tenancy_period", "tenancy_id", "period_start", "period_end"),
    )


class AdvanceReconciliation(Base):
    """Append-only selected allocation snapshot, including an explicit empty confirmation."""

    __tablename__ = "advance_reconciliation"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    tenancy_id: Mapped[str]
    period_start: Mapped[date]
    period_end: Mapped[date]
    version: Mapped[int]
    total_cents: Mapped[int]
    supersedes_id: Mapped[str | None]
    confirmed_at: Mapped[datetime] = mapped_column(server_default=func.now())

    tenancy: Mapped["Tenancy"] = relationship(
        back_populates="advance_reconciliations",
        primaryjoin="Tenancy.id == AdvanceReconciliation.tenancy_id",
        foreign_keys="AdvanceReconciliation.tenancy_id",
    )

    __table_args__ = (
        _scoped_fk("advance_reconciliation", "tenancy_id", "tenancy"),
        _scoped_tenancy_fk("advance_reconciliation", "supersedes_id", "advance_reconciliation"),
        _scoped_account_pair_fk(
            "advance_reconciliation", "supersedes_id", "advance_reconciliation"
        ),
        _scoped_pair("advance_reconciliation"),
        UniqueConstraint(
            "id", "tenancy_id", "account_id", name="uq_advance_reconciliation_id_tenancy_account"
        ),
        CheckConstraint(
            "period_end >= period_start", name="ck_advance_reconciliation_period_ordered"
        ),
        UniqueConstraint(
            "tenancy_id",
            "period_start",
            "period_end",
            "version",
            name="uq_advance_reconciliation_version",
        ),
        Index("ix_advance_reconciliation_account", "account_id"),
        Index(
            "ix_advance_reconciliation_tenancy_period", "tenancy_id", "period_start", "period_end"
        ),
    )


class AdvanceReconciliationAllocation(Base):
    __tablename__ = "advance_reconciliation_allocation"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    reconciliation_id: Mapped[str]
    allocation_id: Mapped[str]

    __table_args__ = (
        _scoped_fk(
            "advance_reconciliation_allocation", "reconciliation_id", "advance_reconciliation"
        ),
        _scoped_fk("advance_reconciliation_allocation", "allocation_id", "advance_allocation"),
        _scoped_pair("advance_reconciliation_allocation"),
        UniqueConstraint(
            "reconciliation_id", "allocation_id", name="uq_advance_reconciliation_allocation"
        ),
        Index("ix_advance_reconciliation_allocation_account", "account_id"),
    )


class TenancyParty(Base):
    __tablename__ = "tenancy_party"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    tenancy_id: Mapped[str]
    renter_id: Mapped[str]

    tenancy: Mapped["Tenancy"] = relationship(
        back_populates="parties",
        primaryjoin="Tenancy.id == TenancyParty.tenancy_id",
        foreign_keys="TenancyParty.tenancy_id",
    )
    renter: Mapped["Renter"] = relationship(
        back_populates="tenancy_parties",
        primaryjoin="Renter.id == TenancyParty.renter_id",
        foreign_keys="TenancyParty.renter_id",
    )

    __table_args__ = (
        _scoped_fk("tenancy_party", "tenancy_id", "tenancy"),
        _scoped_fk("tenancy_party", "renter_id", "renter"),
        UniqueConstraint("tenancy_id", "renter_id"),
        Index("ix_tenancy_party_account", "account_id"),
    )


# ── Messdienstleister: a confirmed third-party statement, passed through. ──


class MdlStatement(Base):
    """A Wärmedienstleister's finished Abrechnung, as confirmed by a human.

    Not a `HeatingCostEntry`: that is an invoice Lokara bills *from*, this is a
    statement Lokara bills *with*. `docs/03` H7 — "validate and pass through;
    never recompute MDL amounts" — so the per-renter positions are stored as
    delivered and only checked against the confirmed total.

    Append-only and versioned (`CLAUDE.md` § 3.2): a correction inserts
    `version + 1` for the same building period and the earlier row stays. The
    reader takes the highest version. Nothing UPDATEs a confirmed row, because
    what was confirmed is the evidence that the figures were a human's decision
    and not Lokara's arithmetic.

    `source_ref` names the document the confirmation came from. It is required:
    a passed-through figure whose origin nobody can name is not evidence.
    """

    __tablename__ = "mdl_statement"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    building_id: Mapped[str]
    branch: Mapped[MdlBranch]
    period_from: Mapped[date]
    period_to: Mapped[date]  # exclusive
    confirmed_total_cents: Mapped[int]
    owner_position_cents: Mapped[int]
    # Off the MDL document; all three or none, and only the GROSS branch needs
    # them (a NET statement was already reduced by the landlord's share).
    co2_kg_x1000: Mapped[int | None] = mapped_column(BigInteger)
    co2_cost_cents: Mapped[int | None]
    heated_area_sqm_x100: Mapped[int | None]
    # False when the document carries no CO₂ disclosure at all — a separate
    # 3-percent risk, never silently netted against anything (`docs/03` F25).
    co2_evidence_present: Mapped[bool] = mapped_column(default=True)
    source_ref: Mapped[str]
    version: Mapped[int] = mapped_column(default=1)
    confirmed_at: Mapped[datetime] = mapped_column(server_default=func.now())

    building: Mapped["Building"] = relationship(
        back_populates="mdl_statements",
        primaryjoin="Building.id == MdlStatement.building_id",
        foreign_keys="MdlStatement.building_id",
    )
    positions: Mapped[list["MdlStatementPosition"]] = relationship(
        back_populates="statement",
        primaryjoin="MdlStatement.id == MdlStatementPosition.mdl_statement_id",
        foreign_keys="MdlStatementPosition.mdl_statement_id",
    )

    __table_args__ = (
        _scoped_fk("mdl_statement", "building_id", "building"),
        _scoped_pair("mdl_statement"),
        CheckConstraint("confirmed_total_cents >= 0", name="ck_mdl_statement_total_non_negative"),
        CheckConstraint("owner_position_cents >= 0", name="ck_mdl_statement_owner_non_negative"),
        CheckConstraint("version >= 1", name="ck_mdl_statement_version_positive"),
        CheckConstraint("period_to > period_from", name="ck_mdl_statement_period_ordered"),
        UniqueConstraint(
            "building_id",
            "period_from",
            "period_to",
            "version",
            name="uq_mdl_statement_building_period_version",
        ),
        Index("ix_mdl_statement_account", "account_id"),
        Index("ix_mdl_statement_building", "building_id"),
    )


class MdlStatementPosition(Base):
    """One renter's amount on a confirmed MDL statement, exactly as delivered."""

    __tablename__ = "mdl_statement_position"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    mdl_statement_id: Mapped[str]
    tenancy_id: Mapped[str]
    amount_cents: Mapped[int]

    statement: Mapped["MdlStatement"] = relationship(
        back_populates="positions",
        primaryjoin="MdlStatement.id == MdlStatementPosition.mdl_statement_id",
        foreign_keys="MdlStatementPosition.mdl_statement_id",
    )

    __table_args__ = (
        _scoped_fk("mdl_statement_position", "mdl_statement_id", "mdl_statement"),
        _scoped_fk("mdl_statement_position", "tenancy_id", "tenancy"),
        CheckConstraint("amount_cents >= 0", name="ck_mdl_position_non_negative"),
        UniqueConstraint(
            "mdl_statement_id", "tenancy_id", name="uq_mdl_position_statement_tenancy"
        ),
        Index("ix_mdl_position_account", "account_id"),
        Index("ix_mdl_position_statement", "mdl_statement_id"),
        Index("ix_mdl_position_tenancy", "tenancy_id"),
    )


# ── Personenzahl: a temporal count per tenancy, never a scalar on the unit. ──


class PersonCount(Base):
    """How many people a tenancy housed over a period — the Personenschlüssel input.

    A row rather than a scalar because the count changes inside a billing period
    (`CLAUDE.md` § 6): a birth, a move-out and a Rumpfperiode all have to survive
    as history, and a current-value column would silently rewrite last year's
    Abrechnung. Half-open validity like every other temporal row here.

    **Vacancy is deliberately absent from this table.** The D0 Fiktivbelegung of a
    vacant unit is derived per run from the last ended tenancy of that unit and
    the building's immutable `fiktivbelegung_mode`. The mode cannot be changed
    after creation, so a completed period cannot be recalculated under a later
    convention. A future effective-dated mode model would be an explicit new
    resolution, rather than an overwrite. This remains a flagged convention
    (`verify-before-production`), not a fact anyone observed. That is also why a
    unit vacant for a whole billing period still resolves: the tenancy that ended
    before the period keeps its rows here. See `docs/02` § 5 "D0 Fiktivbelegung",
    which records the layering decision.
    """

    __tablename__ = "person_count"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    tenancy_id: Mapped[str]
    count: Mapped[int]
    valid_from: Mapped[date]
    valid_to: Mapped[date | None]

    tenancy: Mapped["Tenancy"] = relationship(
        back_populates="person_counts",
        primaryjoin="Tenancy.id == PersonCount.tenancy_id",
        foreign_keys="PersonCount.tenancy_id",
    )

    __table_args__ = (
        _scoped_fk("person_count", "tenancy_id", "tenancy"),
        # Zero is a real entered count (an empty but still-running lease); a
        # negative one is not a Personenzahl at all.
        CheckConstraint("count >= 0", name="ck_person_count_non_negative"),
        CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="ck_person_count_period_ordered",
        ),
        # A tenant has one count on each day. The Postgres exclusion constraint
        # uses half-open dateranges, so an adjacent correction is allowed while
        # two competing counts for the same day are rejected at the DB boundary.
        # `account_id` keeps an invalid foreign-account write on the composite
        # FK path, whose explicit rejection is part of the isolation contract.
        ExcludeConstraint(
            ("account_id", "="),
            ("tenancy_id", "="),
            (text("daterange(valid_from, valid_to, '[)')"), "&&"),
            name="ex_person_count_tenancy_period_no_overlap",
            using="gist",
        ),
        Index("ix_person_count_account", "account_id"),
        Index("ix_person_count_tenancy", "tenancy_id"),
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

    unit: Mapped["Unit"] = relationship(
        back_populates="self_use_periods",
        primaryjoin="Unit.id == SelfUsePeriod.unit_id",
        foreign_keys="SelfUsePeriod.unit_id",
    )

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
    # Written once by M6-B finalization.  It is the normalized calculation and
    # selected address/instruction evidence, never a pointer back to live rows.
    finalized_snapshot: Mapped[dict[str, object]] = mapped_column(
        JSON, server_default=text("'{}'::json")
    )
    finalized_at: Mapped[datetime | None]
    supersedes_statement_id: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    building: Mapped["Building"] = relationship(
        back_populates="statements",
        primaryjoin="Building.id == Statement.building_id",
        foreign_keys="Statement.building_id",
    )

    __table_args__ = (
        _scoped_fk("statement", "building_id", "building"),
        _scoped_fk("statement", "supersedes_statement_id", "statement"),
        _scoped_pair("statement"),
        UniqueConstraint("building_id", "period_start", "period_end", "version"),
        Index("ix_statement_account", "account_id"),
    )


class DeliveryAddress(Base):
    """Append-only tenancy delivery address selected verbatim at finalization."""

    __tablename__ = "tenancy_delivery_address"
    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    tenancy_id: Mapped[str]
    addressee: Mapped[str]
    street: Mapped[str]
    postal_code: Mapped[str]
    city: Mapped[str]
    country: Mapped[str]
    version: Mapped[int]
    valid_from: Mapped[date]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        _scoped_fk("tenancy_delivery_address", "tenancy_id", "tenancy"),
        _scoped_pair("tenancy_delivery_address"),
        UniqueConstraint("tenancy_id", "version", name="uq_tenancy_delivery_address_version"),
        Index("ix_tenancy_delivery_address_account", "account_id"),
    )


class PaymentInstruction(Base):
    """Append-only owner payment/credit copy, not a bank-matching interface."""

    __tablename__ = "owner_payment_credit_instruction"
    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    version: Mapped[int]
    instruction_text: Mapped[str]
    valid_from: Mapped[date]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        _scoped_pair("owner_payment_credit_instruction"),
        UniqueConstraint(
            "account_id", "version", name="uq_owner_payment_credit_instruction_version"
        ),
        Index("ix_owner_payment_credit_instruction_account", "account_id"),
    )


class StatementArchive(Base):
    """Stored final bytes.  A renter archive always names exactly one tenancy."""

    __tablename__ = "statement_document_archive"
    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    statement_id: Mapped[str]
    audience: Mapped[str]
    tenancy_id: Mapped[str | None]
    content_bytes: Mapped[bytes]
    sha256: Mapped[str]
    mime_type: Mapped[str]
    filename: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        _scoped_fk("statement_document_archive", "statement_id", "statement"),
        _scoped_fk("statement_document_archive", "tenancy_id", "tenancy"),
        _scoped_pair("statement_document_archive"),
        UniqueConstraint(
            "statement_id", "audience", "tenancy_id", name="uq_statement_archive_audience"
        ),
        CheckConstraint(
            "(audience = 'OWNER' AND tenancy_id IS NULL) OR "
            "(audience = 'TENANT' AND tenancy_id IS NOT NULL)",
            name="ck_statement_archive_audience_tenancy",
        ),
        CheckConstraint("length(sha256) = 64", name="ck_statement_archive_sha256"),
        Index(
            "uq_statement_document_archive_owner",
            "statement_id",
            "audience",
            unique=True,
            postgresql_where=text("audience = 'OWNER' AND tenancy_id IS NULL"),
        ),
        Index("ix_statement_document_archive_account", "account_id"),
    )


class StatementSettlement(Base):
    """One immutable Saldo consequence per finalized tenant statement."""

    __tablename__ = "statement_settlement"
    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    statement_id: Mapped[str]
    tenancy_id: Mapped[str]
    amount_cents: Mapped[int]
    origin_saldo_cents: Mapped[int]
    kind: Mapped[str]  # RECEIVABLE or CREDIT_REFUND
    late_positive_exception_reason: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        _scoped_fk("statement_settlement", "statement_id", "statement"),
        _scoped_fk("statement_settlement", "tenancy_id", "tenancy"),
        _scoped_pair("statement_settlement"),
        UniqueConstraint("statement_id", "tenancy_id", name="uq_statement_settlement_tenancy"),
        CheckConstraint("amount_cents > 0", name="ck_statement_settlement_positive"),
        CheckConstraint(
            "kind IN ('RECEIVABLE', 'CREDIT_REFUND')", name="ck_statement_settlement_kind"
        ),
        Index("ix_statement_settlement_account", "account_id"),
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
    voided_at: Mapped[datetime | None]
    void_reason: Mapped[str | None]
    replaces_cost_entry_id: Mapped[str | None]
    new_cost: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    building: Mapped["Building"] = relationship(
        back_populates="cost_entries",
        primaryjoin="Building.id == CostEntry.building_id",
        foreign_keys="CostEntry.building_id",
    )
    key_assignments: Mapped[list["AllocationKeyAssignment"]] = relationship(
        back_populates="cost_entry",
        primaryjoin="CostEntry.id == AllocationKeyAssignment.cost_entry_id",
        foreign_keys="AllocationKeyAssignment.cost_entry_id",
    )
    classifications: Mapped[list["ConfirmedCostClassification"]] = relationship(
        back_populates="cost_entry",
        primaryjoin="CostEntry.id == ConfirmedCostClassification.cost_entry_id",
        foreign_keys="ConfirmedCostClassification.cost_entry_id",
    )

    __table_args__ = (
        _scoped_fk("cost_entry", "building_id", "building"),
        _scoped_fk("cost_entry", "replaces_cost_entry_id", "cost_entry"),
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

    cost_entry: Mapped["CostEntry"] = relationship(
        back_populates="key_assignments",
        primaryjoin="CostEntry.id == AllocationKeyAssignment.cost_entry_id",
        foreign_keys="AllocationKeyAssignment.cost_entry_id",
    )

    __table_args__ = (
        _scoped_fk("allocation_key_assignment", "cost_entry_id", "cost_entry"),
        _scoped_fk("allocation_key_assignment", "direct_unit_id", "unit"),
        _scoped_fk("allocation_key_assignment", "direct_tenancy_id", "tenancy"),
        Index("ix_aka_account", "account_id"),
        Index("ix_aka_cost_entry", "cost_entry_id"),
    )


# ── Page 02 — temporal agreement + human-confirmed classification. ─────────


class OperatingCostAgreement(Base):
    """Contract facts for one tenancy and effective period.

    Absence is meaningful: callers must treat it conservatively and must not
    infer an agreement from an old/current scalar on the tenancy.
    """

    __tablename__ = "operating_cost_agreement"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    tenancy_id: Mapped[str]
    allocation_agreed: Mapped[bool]
    mehrbelastung_clause: Mapped[bool]
    named_other_costs: Mapped[list[str]] = mapped_column(JSON, default=list)
    contractual_keys: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    valid_from: Mapped[date]
    valid_to: Mapped[date | None]
    revises_id: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    tenancy: Mapped["Tenancy"] = relationship(
        back_populates="operating_cost_agreements",
        primaryjoin="Tenancy.id == OperatingCostAgreement.tenancy_id",
        foreign_keys="OperatingCostAgreement.tenancy_id",
    )

    __table_args__ = (
        _scoped_fk("operating_cost_agreement", "tenancy_id", "tenancy"),
        _scoped_fk("operating_cost_agreement", "revises_id", "operating_cost_agreement"),
        CheckConstraint(
            "valid_to IS NULL OR valid_to > valid_from",
            name="ck_operating_cost_agreement_period_ordered",
        ),
        _scoped_pair("operating_cost_agreement"),
        Index("ix_operating_cost_agreement_account", "account_id"),
        Index("ix_operating_cost_agreement_tenancy", "tenancy_id"),
    )


class ConfirmedCostClassification(Base):
    """Append-only human confirmation of a Page-02 catalogue decision.

    The raw entry remains unchanged. A later correction creates another row so
    both the original confirmation and the revised evidence survive.
    """

    __tablename__ = "confirmed_cost_classification"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    cost_entry_id: Mapped[str]
    allocation_key_assignment_id: Mapped[str]
    catalogue_id: Mapped[str]
    rule_source: Mapped[str]
    rule_rechtsstand: Mapped[str]
    source_amount_cents: Mapped[int]
    allocable_cents: Mapped[int]
    non_allocable_cents: Mapped[int]
    labour_cents: Mapped[int | None]
    key: Mapped[AllocationKey | None]
    key_source: Mapped[str | None]
    findings: Mapped[list[str]] = mapped_column(JSON, default=list)
    special_rule_evidence: Mapped[dict[str, object]] = mapped_column(JSON, default=dict)
    production_blocked: Mapped[bool]
    confirmed_at: Mapped[datetime] = mapped_column(server_default=func.now())

    cost_entry: Mapped["CostEntry"] = relationship(
        back_populates="classifications",
        primaryjoin="CostEntry.id == ConfirmedCostClassification.cost_entry_id",
        foreign_keys="ConfirmedCostClassification.cost_entry_id",
    )

    __table_args__ = (
        _scoped_fk("confirmed_cost_classification", "cost_entry_id", "cost_entry"),
        _scoped_fk(
            "confirmed_cost_classification",
            "allocation_key_assignment_id",
            "allocation_key_assignment",
        ),
        CheckConstraint(
            "source_amount_cents = allocable_cents + non_allocable_cents",
            name="ck_cost_classification_reconciles",
        ),
        CheckConstraint(
            "labour_cents IS NULL OR (labour_cents >= 0 AND labour_cents <= allocable_cents)",
            name="ck_cost_classification_labour_valid",
        ),
        _scoped_pair("confirmed_cost_classification"),
        Index("ix_cost_classification_account", "account_id"),
        Index("ix_cost_classification_cost", "cost_entry_id"),
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
    # Exact K11 factor × 1000.  Every heat device (including a kWh main
    # meter) has a factor; water meters do not participate in H5.
    valuation_factor_x1000: Mapped[int | None] = mapped_column(
        BigInteger,
        default=lambda context: (
            1000 if context.get_current_parameters().get("kind") is MeterKind.HEAT else None
        ),
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    building: Mapped["Building"] = relationship(
        back_populates="meters",
        primaryjoin="Building.id == Meter.building_id",
        foreign_keys="Meter.building_id",
    )
    unit: Mapped["Unit | None"] = relationship(
        back_populates="meters",
        primaryjoin="Unit.id == Meter.unit_id",
        foreign_keys="Meter.unit_id",
    )
    readings: Mapped[list["MeterReading"]] = relationship(
        back_populates="meter",
        primaryjoin="Meter.id == MeterReading.meter_id",
        foreign_keys="MeterReading.meter_id",
    )

    __table_args__ = (
        _scoped_fk("meter", "building_id", "building"),
        _scoped_fk("meter", "unit_id", "unit"),
        _scoped_pair("meter"),
        UniqueConstraint("building_id", "serial"),
        CheckConstraint(
            "(kind = 'HEAT' AND valuation_factor_x1000 IS NOT NULL "
            "AND valuation_factor_x1000 > 0) OR "
            "(kind <> 'HEAT' AND valuation_factor_x1000 IS NULL)",
            name="ck_meter_heat_valuation_factor",
        ),
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
    # Optional exact assignment/evidence for H5.  A tenant-change reading can
    # be tied to its tenancy; an estimate carries its already normalized
    # consumption × 1000 plus the basis and source reference.
    tenancy_id: Mapped[str | None]
    estimated_consumption_x1000: Mapped[int | None] = mapped_column(BigInteger)
    estimation_basis: Mapped[str | None]
    provenance_ref: Mapped[str | None]
    recorded_at: Mapped[datetime] = mapped_column(server_default=func.now())

    meter: Mapped["Meter"] = relationship(
        back_populates="readings",
        primaryjoin="Meter.id == MeterReading.meter_id",
        foreign_keys="MeterReading.meter_id",
    )

    __table_args__ = (
        _scoped_fk("meter_reading", "meter_id", "meter"),
        _scoped_fk("meter_reading", "tenancy_id", "tenancy"),
        CheckConstraint(
            "(estimated_consumption_x1000 IS NULL AND estimation_basis IS NULL) OR "
            "(estimated_consumption_x1000 IS NOT NULL AND estimated_consumption_x1000 >= 0 "
            "AND estimation_basis IS NOT NULL)",
            name="ck_meter_reading_estimate_basis",
        ),
        Index("ix_meter_reading_account", "account_id"),
        Index("ix_meter_reading_meter", "meter_id"),
        Index("ix_meter_reading_tenancy", "tenancy_id"),
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

    building: Mapped["Building"] = relationship(
        back_populates="heating_cost_entries",
        primaryjoin="Building.id == HeatingCostEntry.building_id",
        foreign_keys="HeatingCostEntry.building_id",
    )

    __table_args__ = (
        _scoped_fk("heating_cost_entry", "building_id", "building"),
        Index("ix_heating_cost_account", "account_id"),
        Index("ix_heating_cost_building", "building_id"),
    )


# ── Bank matching, receivables and the payment ledger (docs/15, M6-C2). ──
#
# The engine that consumes these lives in `packages/matching-engine` and is already
# fixture-complete. This layer only stores what it reads and what it decided; no
# scoring, ordering or settlement rule is re-expressed here.


class BankAccount(Base):
    """One connected landlord bank account behind the AIS adapter."""

    __tablename__ = "bank_account"
    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    provider: Mapped[str]
    provider_account_id: Mapped[str]
    normalized_iban: Mapped[str]
    display_name: Mapped[str]
    consent_expires_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        _scoped_pair("bank_account"),
        UniqueConstraint(
            "account_id", "provider", "provider_account_id", name="uq_bank_account_provider"
        ),
        Index("ix_bank_account_account", "account_id"),
    )


class BankTransaction(Base):
    """docs/15 § 3.1: the immutable normalized provider movement.

    `amount_cents` is signed — a negative amount is the reversal path (§ 5.3), a
    positive one enters scoring, and zero is retained for import audit but ignored
    by matching. `bank_booking_date`, **not** `finapi_booking_date`, decides whether
    a receivable is due.

    Two different mechanisms share the word "duplicate" and must not be merged:
    `is_potential_duplicate` keeps the transaction and forces Review, while an exact
    re-import of `provider_transaction_id` is deduplicated before scoring and creates
    no second row at all. The unique constraint below is the second one.
    """

    __tablename__ = "bank_transaction"
    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    bank_account_id: Mapped[str]
    provider_transaction_id: Mapped[str]
    amount_cents: Mapped[int]
    bank_booking_date: Mapped[date]
    finapi_booking_date: Mapped[date]
    value_date: Mapped[date]
    counterpart_iban: Mapped[str | None]
    counterpart_name: Mapped[str | None]
    purpose: Mapped[str | None]
    end_to_end_reference: Mapped[str | None]
    counterpart_mandate_reference: Mapped[str | None]
    bank_transaction_code: Mapped[str | None]
    provider_type: Mapped[str | None]
    is_potential_duplicate: Mapped[bool] = mapped_column(server_default=text("false"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        _scoped_fk("bank_transaction", "bank_account_id", "bank_account"),
        _scoped_pair("bank_transaction"),
        # docs/15 § 6: a provider ID is unique only together with its account and
        # bank-account identity. Providers do not allocate ids globally, so a
        # constraint on the id alone would make one landlord's import collide
        # with another's.
        UniqueConstraint(
            "account_id",
            "bank_account_id",
            "provider_transaction_id",
            name="uq_bank_transaction_provider_identity",
        ),
        Index("ix_bank_transaction_account", "account_id"),
        Index("ix_bank_transaction_booking", "account_id", "bank_booking_date"),
    )


class Receivable(Base):
    """docs/15 § 3.2: one open debt of one renter.

    The source calls its renter field `tenant_id`; CLAUDE.md § 7 normalizes that to
    `renter_id`. The four nominal components sum to `expected_cents`.
    """

    __tablename__ = "receivable"
    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    renter_id: Mapped[str]
    tenancy_id: Mapped[str]
    source_type: Mapped[str]
    source_id: Mapped[str | None]
    period: Mapped[str]
    due_date: Mapped[date]
    expected_cents: Mapped[int]
    open_cents: Mapped[int]
    status: Mapped[str]
    category: Mapped[str]
    base_rent_cents: Mapped[int]
    nk_advance_cents: Mapped[int]
    heating_advance_cents: Mapped[int]
    garage_cents: Mapped[int]
    open_costs_cents: Mapped[int] = mapped_column(server_default=text("0"))
    open_interest_cents: Mapped[int] = mapped_column(server_default=text("0"))
    open_principal_cents: Mapped[int] = mapped_column(server_default=text("0"))
    # docs/15 § 4 awards 15 points when a transaction's E2E or mandate reference
    # matches a "stored reference" that §§ 3.2-3.3 never define. The column exists
    # so the field has a home the moment Berkay answers (FRAGEN-an-Berkay-05.md).
    # Until then `_end_to_end_signal` returns 0 and nothing writes here: binding the
    # signal to a guessed field is the invented convention M6-C1 removed.
    stored_reference: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        _scoped_fk("receivable", "renter_id", "renter"),
        _scoped_fk("receivable", "tenancy_id", "tenancy"),
        _scoped_pair("receivable"),
        # Rent only. An `nk_nachzahlung` is a settled Saldo with no rent, garage
        # or advance component, and parking it in `nk_advance_cents` to satisfy the
        # arithmetic would feed Page 01 an advance that was never paid as one
        # (docs/15 § 5.2). Migration 0018 carries the full reasoning.
        CheckConstraint(
            "category <> 'rent' OR (base_rent_cents + nk_advance_cents"
            " + heating_advance_cents + garage_cents = expected_cents)",
            name="ck_receivable_components_sum",
        ),
        CheckConstraint(
            "open_cents >= 0 AND open_cents <= expected_cents", name="ck_receivable_open_range"
        ),
        # Migration 0020 (0019 asserted only `<=`). `settlement.py:140` computes
        # `open_after = open_cents - principal`: only the principal component reduces
        # `open_cents`, so `open_cents` **is** the open principal and the relation is
        # equality, not a three-way sum. Costs and interest are bounded below only —
        # nothing in docs/15 bounds them above, and they arrive from Page 05 in M9.
        CheckConstraint(
            "open_costs_cents >= 0 AND open_interest_cents >= 0"
            " AND open_principal_cents >= 0 AND open_principal_cents = open_cents"
            " AND open_cents <= expected_cents",
            name="ck_receivable_open_components",
        ),
        CheckConstraint(
            "(status = 'settled')"
            " = (open_cents = 0 AND open_costs_cents = 0 AND open_interest_cents = 0)",
            name="ck_receivable_settled_has_nothing_open",
        ),
        CheckConstraint("status IN ('open', 'partial', 'settled')", name="ck_receivable_status"),
        CheckConstraint("category IN ('rent', 'nk_nachzahlung')", name="ck_receivable_category"),
        Index("ix_receivable_account", "account_id"),
        Index("ix_receivable_due", "account_id", "renter_id", "due_date"),
        # Migration 0019. The Page 01 handoff's "already created" guard was a SELECT
        # then an INSERT: two concurrent requests both passed it and both inserted.
        Index(
            "uq_receivable_source",
            "account_id",
            "source_type",
            "source_id",
            "tenancy_id",
            unique=True,
            postgresql_where=text("source_id IS NOT NULL"),
        ),
        # Migration 0020. A correction statement carries a *new* source_id, so the
        # index above does not cover it — one tenancy could be billed the same
        # period's Nachzahlung twice.
        Index(
            "uq_receivable_nk_nachzahlung_period",
            "account_id",
            "tenancy_id",
            "period",
            unique=True,
            postgresql_where=text("category = 'nk_nachzahlung'"),
        ),
    )


class RenterMatchingProfile(Base):
    """docs/15 § 3.3. `known_ibans` is derived from active IbanHistory rows and is
    therefore not a column — a stored copy would be a second truth to keep in sync."""

    __tablename__ = "renter_matching_profile"
    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    renter_id: Mapped[str]
    payment_code: Mapped[str | None]
    normalized_surname: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        _scoped_fk("renter_matching_profile", "renter_id", "renter"),
        _scoped_pair("renter_matching_profile"),
        UniqueConstraint("account_id", "renter_id", name="uq_renter_matching_profile_renter"),
        Index("ix_renter_matching_profile_account", "account_id"),
    )


class IbanHistory(Base):
    """docs/15 § 3.3: versioned, never overwritten (CLAUDE.md § 6).

    A non-null IBAN is learned only after a user confirms a Review proposal; null is
    never learned (`F09`).
    """

    __tablename__ = "iban_history"
    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    renter_id: Mapped[str]
    normalized_iban: Mapped[str]
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    learned_from_transaction_id: Mapped[str | None]
    confirmed_match_id: Mapped[str | None]
    confirmed_by: Mapped[str | None]
    confirmed_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        _scoped_fk("iban_history", "renter_id", "renter"),
        _scoped_fk("iban_history", "learned_from_transaction_id", "bank_transaction"),
        _scoped_pair("iban_history"),
        CheckConstraint("valid_to IS NULL OR valid_to >= valid_from", name="ck_iban_history_span"),
        # Migration 0019, docs/15 § 3.3 and F09: a non-null IBAN is learned only after
        # a user confirms a Review proposal. Without this the +60 unique-IBAN signal
        # could be created by anything able to insert.
        CheckConstraint(
            "confirmed_match_id IS NOT NULL AND confirmed_by IS NOT NULL",
            name="ck_iban_history_requires_confirmation",
        ),
        _scoped_fk("iban_history", "confirmed_match_id", "match_confirmation"),
        Index("ix_iban_history_account", "account_id"),
        Index("ix_iban_history_lookup", "account_id", "normalized_iban"),
        # Migration 0020, docs/15 § 3.3 `F07`: uniqueness is per **renter**. Two
        # active renters must be able to share one IBAN — spouses on a joint account —
        # so each receives the ambiguous signal and the result is Review. 0019's
        # per-account index made that state unrepresentable. What survives is the
        # narrower guarantee: one renter may not hold the same IBAN active twice,
        # because history is versioned and the predecessor's valid_to is closed first.
        Index(
            "uq_iban_history_active_renter",
            "account_id",
            "renter_id",
            "normalized_iban",
            unique=True,
            postgresql_where=text("valid_to IS NULL"),
        ),
    )


class MatchProposal(Base):
    """docs/15 § 4: the stored proposal, including every component signal.

    The signals are stored individually and not only as `confidence`, because a
    confidence alone cannot be re-derived or audited later, and § 4's Review ranking
    reads the components.
    """

    __tablename__ = "match_proposal"
    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    bank_transaction_id: Mapped[str]
    receivable_id: Mapped[str | None]
    renter_id: Mapped[str | None]
    # Compatibility default for older single-candidate callers. The C3a service
    # supplies every explicit engine rank; the database uniqueness rule rejects two
    # omitted ranks inside one transaction.
    rank: Mapped[int] = mapped_column(default=1)
    signal_iban: Mapped[int]
    signal_amount: Mapped[int]
    signal_code_or_surname: Mapped[int]
    signal_e2e: Mapped[int]
    signal_period: Mapped[int]
    confidence: Mapped[int]
    decision: Mapped[str]
    convention_version: Mapped[str]
    reason_de: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        _scoped_fk("match_proposal", "bank_transaction_id", "bank_transaction"),
        _scoped_fk("match_proposal", "receivable_id", "receivable"),
        _scoped_fk("match_proposal", "renter_id", "renter"),
        _scoped_pair("match_proposal"),
        CheckConstraint(
            "decision IN ('AUTO_MATCH', 'NEEDS_REVIEW', 'UNMATCHED', 'DEDUPED')",
            name="ck_match_proposal_decision",
        ),
        CheckConstraint(
            "confidence >= 0 AND confidence <= 100", name="ck_match_proposal_confidence"
        ),
        CheckConstraint("rank > 0", name="ck_match_proposal_rank_positive"),
        Index("ix_match_proposal_account", "account_id"),
        Index("ix_match_proposal_transaction", "account_id", "bank_transaction_id"),
        Index(
            "uq_match_proposal_transaction_rank",
            "bank_transaction_id",
            "rank",
            unique=True,
        ),
    )


class MatchConfirmation(Base):
    """docs/15 § 4: confirmation records the actor and time. It never rewrites the
    proposal it confirms, which is why this is a separate row."""

    __tablename__ = "match_confirmation"
    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    match_proposal_id: Mapped[str]
    outcome: Mapped[str]
    confirmed_by: Mapped[str]
    confirmed_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        _scoped_fk("match_confirmation", "match_proposal_id", "match_proposal"),
        _scoped_pair("match_confirmation"),
        CheckConstraint(
            "outcome IN ('CONFIRMED', 'REJECTED', 'DUPLICATE')",
            name="ck_match_confirmation_outcome",
        ),
        # Migration 0019: M6-C3 drives ledger entries off confirmations, so one
        # proposal confirmed twice is one payment booked twice.
        UniqueConstraint("account_id", "match_proposal_id", name="uq_match_confirmation_proposal"),
        Index("ix_match_confirmation_account", "account_id"),
    )


class PaymentLedgerEntry(Base):
    """docs/15 § 5.3: append-only. A reversal appends a compensating entry pointing
    at the original through `reverses_entry_id`; nothing is ever edited or deleted.
    The database trigger in migration 0017 is what actually enforces that."""

    __tablename__ = "payment_ledger_entry"
    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    bank_transaction_id: Mapped[str]
    match_proposal_id: Mapped[str | None]
    kind: Mapped[str]
    amount_cents: Mapped[int]
    credit_cents: Mapped[int] = mapped_column(server_default=text("0"))
    ordering_version: Mapped[str]
    reverses_entry_id: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        _scoped_fk("payment_ledger_entry", "bank_transaction_id", "bank_transaction"),
        _scoped_fk("payment_ledger_entry", "match_proposal_id", "match_proposal"),
        _scoped_fk("payment_ledger_entry", "reverses_entry_id", "payment_ledger_entry"),
        _scoped_pair("payment_ledger_entry"),
        CheckConstraint("kind IN ('PAYMENT', 'REVERSAL')", name="ck_payment_ledger_kind"),
        # Migration 0019, docs/15 § 5.3 and F06: the ledger nets to zero. A positive
        # REVERSAL, or one naming no original, cannot do that — and the table is
        # append-only, so nothing corrects it afterwards.
        CheckConstraint(
            "(kind = 'REVERSAL') = (reverses_entry_id IS NOT NULL)"
            " AND (kind <> 'REVERSAL' OR amount_cents < 0)"
            " AND (kind <> 'PAYMENT' OR amount_cents >= 0)",
            name="ck_payment_ledger_reversal_shape",
        ),
        CheckConstraint("credit_cents >= 0", name="ck_payment_ledger_credit_positive"),
        CheckConstraint(
            "kind <> 'REVERSAL' OR credit_cents = 0",
            name="ck_payment_ledger_reversal_credit_zero",
        ),
        Index("ix_payment_ledger_account", "account_id"),
        Index("ix_payment_ledger_transaction", "account_id", "bank_transaction_id"),
        # Migration 0019. Two reversals of one payment reopen twice the debt of a
        # renter who paid once, and the ledger is append-only.
        Index(
            "uq_payment_ledger_one_reversal",
            "reverses_entry_id",
            unique=True,
            postgresql_where=text("reverses_entry_id IS NOT NULL"),
        ),
    )


class PaymentAllocation(Base):
    """docs/15 §§ 5.1-5.2: what one ledger entry paid on one debt, split by
    § 367 BGB order (costs, interest, principal) and then by nominal component."""

    __tablename__ = "payment_allocation"
    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    ledger_entry_id: Mapped[str]
    receivable_id: Mapped[str]
    costs_cents: Mapped[int]
    interest_cents: Mapped[int]
    principal_cents: Mapped[int]
    base_rent_cents: Mapped[int]
    nk_advance_cents: Mapped[int]
    heating_advance_cents: Mapped[int]
    garage_cents: Mapped[int]
    resulting_status: Mapped[str]
    before_open_costs_cents: Mapped[int | None]
    before_open_interest_cents: Mapped[int | None]
    before_open_principal_cents: Mapped[int | None]
    before_open_cents: Mapped[int | None]
    before_status: Mapped[str | None]
    after_open_costs_cents: Mapped[int | None]
    after_open_interest_cents: Mapped[int | None]
    after_open_principal_cents: Mapped[int | None]
    after_open_cents: Mapped[int | None]
    after_status: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    __table_args__ = (
        _scoped_fk("payment_allocation", "ledger_entry_id", "payment_ledger_entry"),
        _scoped_fk("payment_allocation", "receivable_id", "receivable"),
        _scoped_pair("payment_allocation"),
        # Migration 0021 enforces the category-dependent component rule in an AFTER
        # trigger: rent components sum to principal, while an nk_nachzahlung keeps its
        # neutral principal and carries four zero named components.
        CheckConstraint(
            "resulting_status IN ('open', 'partial', 'settled')",
            name="ck_payment_allocation_status",
        ),
        CheckConstraint(
            "((before_open_costs_cents IS NULL"
            " AND before_open_interest_cents IS NULL"
            " AND before_open_principal_cents IS NULL"
            " AND before_open_cents IS NULL"
            " AND before_status IS NULL"
            " AND after_open_costs_cents IS NULL"
            " AND after_open_interest_cents IS NULL"
            " AND after_open_principal_cents IS NULL"
            " AND after_open_cents IS NULL"
            " AND after_status IS NULL) OR"
            " (before_open_costs_cents IS NOT NULL"
            " AND before_open_interest_cents IS NOT NULL"
            " AND before_open_principal_cents IS NOT NULL"
            " AND before_open_cents IS NOT NULL"
            " AND before_status IS NOT NULL"
            " AND after_open_costs_cents IS NOT NULL"
            " AND after_open_interest_cents IS NOT NULL"
            " AND after_open_principal_cents IS NOT NULL"
            " AND after_open_cents IS NOT NULL"
            " AND after_status IS NOT NULL))",
            name="ck_payment_allocation_projection_snapshots_complete",
        ),
        CheckConstraint(
            "before_status IS NULL OR ("
            "before_status IN ('open', 'partial', 'settled')"
            " AND after_status IN ('open', 'partial', 'settled')"
            " AND after_status = resulting_status)",
            name="ck_payment_allocation_projection_snapshot_status",
        ),
        # The kind-dependent sign rule is not a CHECK and cannot be one: whether a
        # component may be negative depends on the parent entry's `kind`, which a CHECK
        # cannot read. `reversal.py:112-123` negates every component, so 0019's blanket
        # non-negative check rejected the engine's own output; migration 0020 moved that
        # rule into `enforce_payment_allocation_cap`, which also owns the signed cap and
        # row lock. One kind-independent residue remains a CHECK: positive and negative
        # components may never cancel inside one allocation.
        CheckConstraint(
            "NOT ((costs_cents > 0 OR interest_cents > 0 OR principal_cents > 0"
            " OR base_rent_cents > 0 OR nk_advance_cents > 0"
            " OR heating_advance_cents > 0 OR garage_cents > 0)"
            " AND (costs_cents < 0 OR interest_cents < 0 OR principal_cents < 0"
            " OR base_rent_cents < 0 OR nk_advance_cents < 0"
            " OR heating_advance_cents < 0 OR garage_cents < 0))",
            name="ck_payment_allocation_no_negative_component_beside_a_positive",
        ),
        UniqueConstraint(
            "ledger_entry_id", "receivable_id", name="uq_payment_allocation_entry_receivable"
        ),
        Index("ix_payment_allocation_account", "account_id"),
        Index("ix_payment_allocation_receivable", "account_id", "receivable_id"),
    )


# Tables scoped by their own account_id column — the Alembic migration enables
# FORCEd RLS on each of these plus `account`, which is scoped by its own id.
# `building_assignment` joined this tuple with migration 0004: its scope used to be
# derived through `membership`, and the migration gave it a real NOT NULL account_id
# (docs/02 → "Isolation rule" → "Consequence for the gates"), which is precisely
# what membership of this tuple means. `person` is global by design.
ACCOUNT_SCOPED_TABLES: tuple[str, ...] = (
    "membership",
    "building_assignment",
    "landlord",
    "renter",
    "building",
    "unit",
    "tenancy",
    "tenancy_party",
    "advance_payment_period",
    "advance_payment",
    "advance_allocation",
    "advance_reconciliation",
    "advance_reconciliation_allocation",
    "tenancy_delivery_address",
    "owner_payment_credit_instruction",
    "person_count",
    "mdl_statement",
    "mdl_statement_position",
    "self_use_period",
    "statement",
    "statement_document_archive",
    "statement_settlement",
    "cost_entry",
    "allocation_key_assignment",
    "operating_cost_agreement",
    "confirmed_cost_classification",
    "meter",
    "meter_reading",
    "heating_cost_entry",
    "bank_account",
    "bank_transaction",
    "receivable",
    "renter_matching_profile",
    "iban_history",
    "match_proposal",
    "match_confirmation",
    "payment_ledger_entry",
    "payment_allocation",
)
