"""SQLAlchemy 2.0 models — identity three-layer + temporal core (docs/02).

Conventions:
- snake_case tables/columns. The Prisma-era quoted-PascalCase tables ("Building" …)
  coexist in the same database until Phase H removes them — no name collisions.
- Every domain row carries account_id (the isolation boundary; the RLS backstop
  lives in the Alembic migration). Person is global — Supabase Auth maps onto it.
- Day-granular validity (valid_from/valid_to) is DATE, half-open like the engines'
  Period; audit timestamps are timestamptz.
- Money is integer cents; areas are m² × 100 integers. Never floats.
- Statement is immutable + versioned: a correction inserts version n+1 and marks
  the predecessor SUPERSEDED — never UPDATE a FINALIZED row (GoBD / § 147 AO).
"""

import enum
from datetime import date, datetime

from lokara_domain import AllocationKey
from sqlalchemy import Date, DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy import Enum as SaEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from .ids import new_id


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
        Index("ix_membership_account", "account_id"),
    )


class BuildingAssignment(Base):
    __tablename__ = "building_assignment"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    membership_id: Mapped[str] = mapped_column(ForeignKey("membership.id", ondelete="CASCADE"))
    building_id: Mapped[str] = mapped_column(ForeignKey("building.id"))

    membership: Mapped["Membership"] = relationship(back_populates="building_assignments")

    __table_args__ = (UniqueConstraint("membership_id", "building_id"),)


# ── Vermieter: a DATA entity (the legal lessor on statements), not a role. ──


class Landlord(Base):
    __tablename__ = "landlord"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    legal_name: Mapped[str]
    address: Mapped[str]

    account: Mapped["Account"] = relationship(back_populates="landlords")
    buildings: Mapped[list["Building"]] = relationship(back_populates="landlord")

    __table_args__ = (Index("ix_landlord_account", "account_id"),)


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
        Index("ix_renter_account", "account_id"),
        Index("ix_renter_person", "person_id"),
    )


# ── Temporal core: Building → Unit → Tenancy. ──


class Building(Base):
    __tablename__ = "building"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    # Nullable: the Landlord entity may be filled in after the building exists.
    landlord_id: Mapped[str | None] = mapped_column(ForeignKey("landlord.id"))
    name: Mapped[str]
    street: Mapped[str]
    postal_code: Mapped[str]
    city: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    landlord: Mapped["Landlord | None"] = relationship(back_populates="buildings")
    units: Mapped[list["Unit"]] = relationship(back_populates="building")
    statements: Mapped[list["Statement"]] = relationship(back_populates="building")
    cost_entries: Mapped[list["CostEntry"]] = relationship(back_populates="building")

    __table_args__ = (Index("ix_building_account", "account_id"),)


class Unit(Base):
    __tablename__ = "unit"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    building_id: Mapped[str] = mapped_column(ForeignKey("building.id"))
    label: Mapped[str]
    # Wohnfläche in m² × 100 (integer — no floats anywhere near allocation math).
    area_sqm_x100: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    building: Mapped["Building"] = relationship(back_populates="units")
    tenancies: Mapped[list["Tenancy"]] = relationship(back_populates="unit")
    self_use_periods: Mapped[list["SelfUsePeriod"]] = relationship(back_populates="unit")

    __table_args__ = (
        Index("ix_unit_account", "account_id"),
        Index("ix_unit_building", "building_id"),
    )


class Tenancy(Base):
    """A lease over a period; valid_to NULL = still running (half-open, like Period).
    Renters attach via TenancyParty — multi-party leases are an entry ticket."""

    __tablename__ = "tenancy"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    unit_id: Mapped[str] = mapped_column(ForeignKey("unit.id"))
    valid_from: Mapped[date]
    valid_to: Mapped[date | None]
    base_rent_cents: Mapped[int]  # Kaltmiete
    advance_payment_cents: Mapped[int]  # monthly NK Vorauszahlung
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    unit: Mapped["Unit"] = relationship(back_populates="tenancies")
    parties: Mapped[list["TenancyParty"]] = relationship(back_populates="tenancy")

    __table_args__ = (
        Index("ix_tenancy_account", "account_id"),
        Index("ix_tenancy_unit", "unit_id"),
    )


class TenancyParty(Base):
    __tablename__ = "tenancy_party"

    id: Mapped[str] = mapped_column(primary_key=True, default=new_id)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    tenancy_id: Mapped[str] = mapped_column(ForeignKey("tenancy.id"))
    renter_id: Mapped[str] = mapped_column(ForeignKey("renter.id"))

    tenancy: Mapped["Tenancy"] = relationship(back_populates="parties")
    renter: Mapped["Renter"] = relationship(back_populates="tenancy_parties")

    __table_args__ = (
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
    unit_id: Mapped[str] = mapped_column(ForeignKey("unit.id"))
    sqm_x100: Mapped[int]  # self-used m² × 100 — an area, not a flag
    kind: Mapped[SelfUseKind] = mapped_column(default=SelfUseKind.OWNER_OCCUPIED)
    note: Mapped[str | None]
    valid_from: Mapped[date]
    valid_to: Mapped[date | None]

    unit: Mapped["Unit"] = relationship(back_populates="self_use_periods")

    __table_args__ = (
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
    building_id: Mapped[str] = mapped_column(ForeignKey("building.id"))
    period_start: Mapped[date]
    period_end: Mapped[date]
    version: Mapped[int] = mapped_column(default=1)
    status: Mapped[StatementStatus] = mapped_column(default=StatementStatus.DRAFT)
    total_cents: Mapped[int]
    content_hash: Mapped[str | None]  # SHA-256 of the rendered document, set on finalize (GoBD)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    building: Mapped["Building"] = relationship(back_populates="statements")

    __table_args__ = (
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
    building_id: Mapped[str] = mapped_column(ForeignKey("building.id"))
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
    cost_entry_id: Mapped[str] = mapped_column(ForeignKey("cost_entry.id"))
    key: Mapped[AllocationKey]
    # Only for key = DIRECT: the single target the cost bypasses allocation to.
    direct_unit_id: Mapped[str | None] = mapped_column(ForeignKey("unit.id"))
    direct_tenancy_id: Mapped[str | None] = mapped_column(ForeignKey("tenancy.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    cost_entry: Mapped["CostEntry"] = relationship(back_populates="key_assignments")

    __table_args__ = (
        Index("ix_aka_account", "account_id"),
        Index("ix_aka_cost_entry", "cost_entry_id"),
    )


# Tables scoped by account_id — the Alembic migration enables FORCEd RLS on each
# of these plus `account` (scoped by its own id) and `building_assignment`
# (scoped via its membership). `person` is global by design.
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
)
