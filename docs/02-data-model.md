# 02 — Data model

> Condensed from `lokara-arch.md` §2/§3/§8. That file has the full reasoning; this is the build spec.
> **Principle:** anything that can change _during_ a period is a row with `validFrom/validTo`, never a
> scalar. Money is integer **cents**. Every domain row carries **`accountId`**.

## Identity: the three-layer model

Do **not** put roles on the Account. Split identity into three layers so one Person can hold many
roles across accounts at once.

> Schema shown as **SQLAlchemy 2.0** declarative models (mapped against Supabase Postgres, migrated
> with Alembic). String ids are cuid/uuid; `created_at` defaults server-side; RLS policies live in
> `packages/db` alongside the models.

1. **Person** — the login (one human). Global, not owned by any account. Maps onto Supabase Auth.
2. **Account** — workspace + subscription + **isolation boundary** (_who pays_). Has a **shape**:
   `SOLO` or `HAUSVERWALTUNG` (a property of the account, not a personal role).
3. **Membership** — links Person → Account, carrying a **Role**. A Person holds many Memberships.

### Roles

- `OWNER` — full account: billing, roles, bank, all buildings. ("Admin bei HV" = OWNER in a HV account.)
- `EMPLOYEE` — only **assigned buildings** (object-level scope). Zero assignments ⇒ sees nothing.
- `TAX_ADVISOR` — read-only guest on a client's account (tax/export + AfA).
- `RENTER` is **not** in the Role enum — a renter is domain data scoped to a **Tenancy**; portal
  access is just `Renter.personId` pointing at a Person.

Not peer roles: **Hausverwaltung** = an account _shape_; **Landlord (Vermieter)** = a _data entity_
(the legal lessor on statements), separate from the person operating it.

### SQLAlchemy 2.0 (identity + relationships — verified: 9 models, 3 enums, no orphans)

```python
import enum
from datetime import datetime
from sqlalchemy import ForeignKey, UniqueConstraint, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase

class Base(DeclarativeBase): ...

class AccountShape(enum.Enum): SOLO = "SOLO"; HAUSVERWALTUNG = "HAUSVERWALTUNG"
class Plan(enum.Enum):
    TRIAL="TRIAL"; SOLO_S="SOLO_S"; SOLO_M="SOLO_M"; SOLO_L="SOLO_L"; TEAM="TEAM"; PRO="PRO"; ENTERPRISE="ENTERPRISE"
class Role(enum.Enum): OWNER="OWNER"; EMPLOYEE="EMPLOYEE"; TAX_ADVISOR="TAX_ADVISOR"   # no RENTER by design

# ── Layer 1: Identity — global ──
class Person(Base):
    __tablename__ = "person"
    id: Mapped[str] = mapped_column(primary_key=True, default=cuid)
    email: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    memberships: Mapped[list["Membership"]] = relationship(back_populates="person")
    renter_links: Mapped[list["Renter"]] = relationship(back_populates="person")

# ── Layer 2: Account — workspace + billing + isolation ──
class Account(Base):
    __tablename__ = "account"
    id: Mapped[str] = mapped_column(primary_key=True, default=cuid)
    name: Mapped[str]
    shape: Mapped[AccountShape] = mapped_column(default=AccountShape.SOLO)
    plan: Mapped[Plan] = mapped_column(default=Plan.TRIAL)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    memberships: Mapped[list["Membership"]] = relationship(back_populates="account")
    landlords: Mapped[list["Landlord"]] = relationship(back_populates="account")
    renters: Mapped[list["Renter"]] = relationship(back_populates="account")

# ── Layer 3: Membership — Person → Account, carrying a Role ──
class Membership(Base):
    __tablename__ = "membership"
    id: Mapped[str] = mapped_column(primary_key=True, default=cuid)
    person_id: Mapped[str] = mapped_column(ForeignKey("person.id"))
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    role: Mapped[Role]
    invited_at: Mapped[datetime] = mapped_column(server_default=func.now())
    accepted_at: Mapped[datetime | None]
    revoked_at: Mapped[datetime | None]                 # revoke, never hard-delete (audit)
    person: Mapped["Person"] = relationship(back_populates="memberships")
    account: Mapped["Account"] = relationship(back_populates="memberships")
    buildings: Mapped[list["BuildingAssignment"]] = relationship()   # only meaningful for EMPLOYEE
    __table_args__ = (
        UniqueConstraint("person_id", "account_id"),    # DECISION: one role per person per account (start strict)
        Index("ix_membership_account", "account_id"),
    )

class BuildingAssignment(Base):
    __tablename__ = "building_assignment"
    id: Mapped[str] = mapped_column(primary_key=True, default=cuid)
    membership_id: Mapped[str] = mapped_column(ForeignKey("membership.id", ondelete="CASCADE"))
    building_id: Mapped[str] = mapped_column(ForeignKey("building.id"))
    __table_args__ = (UniqueConstraint("membership_id", "building_id"),)

# ── Vermieter: DATA entity (legal lessor), not a role ──
class Landlord(Base):
    __tablename__ = "landlord"
    id: Mapped[str] = mapped_column(primary_key=True, default=cuid)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    legal_name: Mapped[str]
    address: Mapped[str]
    account: Mapped["Account"] = relationship(back_populates="landlords")
    buildings: Mapped[list["Building"]] = relationship()
    __table_args__ = (Index("ix_landlord_account", "account_id"),)

# ── Mieter: domain entity; portal login OPTIONAL via person_id ──
class Renter(Base):
    __tablename__ = "renter"
    id: Mapped[str] = mapped_column(primary_key=True, default=cuid)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))
    legal_name: Mapped[str]
    email: Mapped[str | None]
    person_id: Mapped[str | None] = mapped_column(ForeignKey("person.id"))  # set = renter can log into the portal
    account: Mapped["Account"] = relationship(back_populates="renters")
    person: Mapped["Person | None"] = relationship(back_populates="renter_links")
    tenancies: Mapped[list["Tenancy"]] = relationship()
    __table_args__ = (Index("ix_renter_account", "account_id"), Index("ix_renter_person", "person_id"))
```

### Decisions the schema makes explicit

1. `UniqueConstraint("person_id", "account_id")` — one role per person per account (relaxing later is
   trivial; tightening after real data is not).
2. `RENTER` is domain data (Tenancy-scoped), not a Membership role → no polymorphic nullable-scope table.
3. `EMPLOYEE` with zero `BuildingAssignment` sees nothing (deny by default).
4. Memberships are **revoked** (`revoked_at`), never deleted (GoBD + DSGVO).
5. Every domain row carries `account_id` — that column **is** the isolation boundary.
6. `Person` is global; Supabase Auth owns credentials and maps onto Person.

### Portals & active context

- Derive the menu from `person.memberships` + `person.renterLinks` **live** — never store a
  "has renter portal" flag.
- Show the context switcher **only** when a Person holds >1 context (solo users get dropped straight in).
- **Carry context in the URL**, not the session: `/a/{accountId}/…` (owner/employee/StB),
  `/renter/{tenancyId}/…` (renter). Survives tabs/refresh/bookmarks.
- **Menu is navigation, not authorization.** Every request independently verifies the Person holds the
  relationship in the URL, then scopes the query. Enforced twice: app logic **and** Postgres RLS.
- **Runtime connects as a non-owner app role.** A Postgres superuser/table-owner **bypasses RLS**, so
  the app must connect as a restricted role (e.g. `lokara_app`) for RLS to actually apply. Locally this
  is a second role via the docker init script; on Supabase it's the `DATABASE_URL` (app role, pooled)
  vs `DIRECT_URL` (migrations) split. Migrations may run as owner; **request traffic never does.**

## Temporal core: Building → Unit → Tenancy

`Building 1─N Unit 1─N Tenancy`. Tenancy has `valid_from/valid_to`.

**Multi-party leases via `TenancyParty` (M0).** A Tenancy links to its renters through a join entity,
not a direct FK — several renters can be on one lease (an entry-ticket requirement), and the link
itself can carry per-party data later. Present from M0, minimal (no portal link yet — that's
`Renter.person_id`, added at M5).

```python
class TenancyParty(Base):
    __tablename__ = "tenancy_party"
    id: Mapped[str] = mapped_column(primary_key=True, default=cuid)
    tenancy_id: Mapped[str] = mapped_column(ForeignKey("tenancy.id"))
    renter_id: Mapped[str] = mapped_column(ForeignKey("renter.id"))
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))   # scoped like every row
    __table_args__ = (UniqueConstraint("tenancy_id", "renter_id"), Index("ix_tp_account", "account_id"))
```

**Statements are immutable — versioned, never edited (M0 encoding).** A correction creates version
`n+1`; the prior version is retained. Status is an explicit lifecycle, and one `(building, period,
version)` is unique.

```python
class StatementStatus(enum.Enum):
    DRAFT = "DRAFT"; FINALIZED = "FINALIZED"; SUPERSEDED = "SUPERSEDED"

# Statement: building_id, period, version:int, status: StatementStatus, created_at, content_hash
# __table_args__ = (UniqueConstraint("building_id", "period", "version"),)
# Correction path: mark vN SUPERSEDED, insert v(N+1) DRAFT → FINALIZED. Never UPDATE a FINALIZED row.
```

## Eigennutzung (self-use) is NOT a Renter

A unit is in exactly one state at any moment:

| State       | Source                        | NK treatment        | Tax treatment                                             |
| ----------- | ----------------------------- | ------------------- | --------------------------------------------------------- |
| `RENTED`    | active `Tenancy`              | allocated to renter | income + deductible costs                                 |
| `SELF_USED` | explicit `SelfUsePeriod` (m²) | falls on landlord   | private — not deductible, reduces AfA base                |
| `VACANT`    | **derived** (neither above)   | falls on landlord   | costs stay deductible while rental intent is demonstrable |

Only `SELF_USED` is stored; `RENTED` derives from tenancies; `VACANT` is the remainder — one source of
truth per state so they can't drift.

```python
class SelfUseKind(enum.Enum): OWNER_OCCUPIED = "OWNER_OCCUPIED"; FREE_OF_CHARGE = "FREE_OF_CHARGE"

class SelfUsePeriod(Base):
    __tablename__ = "self_use_period"
    id: Mapped[str] = mapped_column(primary_key=True, default=cuid)
    unit_id: Mapped[str] = mapped_column(ForeignKey("unit.id"))
    sqm_x100: Mapped[int]                              # self-used m² × 100 — an AREA, not a flag
    kind: Mapped[SelfUseKind] = mapped_column(default=SelfUseKind.OWNER_OCCUPIED)
    note: Mapped[str | None]
    valid_from: Mapped[datetime]
    valid_to: Mapped[datetime | None]
    unit: Mapped["Unit"] = relationship(back_populates="self_use_periods")
    __table_args__ = (Index("ix_self_use_unit", "unit_id"),)
```

- Self-use is an **area with a period** (m²), not a boolean — covers partial cases (a rented room).
- **Invariant:** a day may never be both `RENTED` and `SELF_USED` — reject overlaps on write.
- **verbilligte Vermietung** (below-market to family, §21 Abs. 2 EStG) is a _real_ Tenancy — flag to a
  StB, don't model as self-use.
- **To specify before AfA:** mid-year Nutzungswechsel needs month-accurate AfA apportionment.

## Allocation keys

```python
class AllocationKey(enum.Enum):
    AREA = "AREA"                # Fläche
    PERSONS = "PERSONS"          # Personen
    CONSUMPTION = "CONSUMPTION"  # Verbrauch (metered)
    UNITS = "UNITS"              # Einheiten
    DIRECT = "DIRECT"            # Direktzuordnung — cost to exactly one unit/tenancy
    MEA = "MEA"                  # Miteigentumsanteil (WEG)
```

- **`DIRECT` is mandatory** (a repair inside flat 3 bypasses proportional allocation).
- Keys must be **freely changeable without deleting entered data** (named pain point at objego AND
  immocloud). The key lives on a **per-period `AllocationKeyAssignment`**, never on the cost row —
  changing a key re-runs the calc and cascades into no stored data.
- **Granularity:** NK allocates at **unit/tenancy** level; **AfA splits by m²** — two granularities on purpose.

## Two financial time-axes (never merge)

- **NK billing = accrual/period-based.** Costs belong to an _Abrechnungszeitraum_; day-weighted;
  vacancy → landlord.
- **Tax = cash basis.** Income/expense belong to the year money moved (§11 EStG Zufluss/Abfluss),
  10-day rule around New Year. Driven by **payment date**.
- They meet in **one** place: an NK statement's Nachzahlung/Guthaben becomes a **Payment in the
  Ledger** when actually paid. Statements feed the ledger; the ledger feeds tax.

### Payment Ledger (source of truth for tax — built at M6)

- `Payment`: **date mandatory**, amount (cents), direction, account/landlord/building/unit/renter,
  category, **source** (finAPI | manual | invoice), receipt ref, **version history**.
- `TaxCategoryMapping`: category → Anlage-V line (**year-versioned**) + SKR03 + SKR04; StB-overridable.
- Export = **pure deterministic function** `f(ledger, mapping, params) → file`. DATEV EXTF is
  Windows-1252, `;`, CRLF (the #1 footgun). Every export archived immutably with hash + timestamp.

## Other temporal/immutable entities (added as their milestones arrive)

`Meter` (+ `calibrationValidUntil` / Eichfrist), normalized `MeterReading` (`unit`, `reason`,
`source`), `AfaRecord`, `Loan`, `Reminder`, `LettingEffort` (vacancy evidence), `Ticket`,
`ExportArchive`, `SubProcessor`, `ActivationCode` (tenancy-bound, per-person, single-use),
`IbanHistory` (versioned), `EmailDelivery` (append-only), `ClauseBlock`/`ClauseVersion`/`Contract`
(composition), `ProspectObject` (Prüfobjekt → becomes Building on purchase).
