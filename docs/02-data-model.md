# 02 — Data model

> Condensed from `lokara-arch.md` §2/§3/§8. That file has the full reasoning; this is the build spec.
> **Principle:** anything that can change _during_ a period is a row with `validFrom/validTo`, never a
> scalar. Money is integer **cents**. Every domain row carries **`accountId`**.
> **Column types:** validity columns (`valid_from/valid_to`) are **day-granular `date`** — billing is
> day-weighted and the engines' `Period` is over dates. Audit/event timestamps (`created_at`,
> `invited_at`, `revoked_at`, delivery logs…) stay **`timestamptz`**.

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
- **`FORCE ROW LEVEL SECURITY` binds the owner too.** With FORCE enabled, even the table owner is
  subject to the policies — locally that's fine (migrations use a separate superuser). ⚠️ On Supabase
  the migration role is a **non-superuser owner**, so FORCE binds it as well: **seed/admin flows there
  must set the app context** (`app.account_id`) or use a role explicitly exempted. `TODO(supabase)`.

## Isolation rule: every tenant-to-tenant FK is composite on `(id, account_id)`

> **Rule.** A foreign key from one account-scoped table to another **must carry `account_id` in the
> reference** — `FOREIGN KEY (parent_id, account_id) REFERENCES parent (id, account_id)`, backed by a
> matching `UNIQUE (id, account_id)` on the parent. A bare FK on `id` alone is a defect, not a style
> choice. This is a rule about the **whole data model**, not about any one table.

CLAUDE.md rule 3 says isolation is enforced **twice**: in app logic and in Postgres RLS. Referential
integrity is a **third** enforcement point that neither of those two covers.

### Why RLS cannot close this

**Postgres enforces foreign keys with RLS bypassed.** The FK check runs as a system operation, not as
the querying role, so it does **not** see the row-level policies. Concretely:

1. A session scoped to account **B** inserts a `tenancy` and correctly stamps `account_id = B`.
2. The `WITH CHECK` policy is satisfied — the row is stamped B, so RLS lets the write through.
3. `unit_id` is set to the id of a `unit` owned by account **A**. The FK check finds that unit,
   because the check does not apply A's/B's row policies. The insert **succeeds**.

The child row is correctly isolated (B reads it, A does not). The **edge it draws is not**: a lease in
B's workspace now hangs off A's flat. Cross-account state exists, and every join downstream —
statements, allocation, PDFs — inherits it.

So `account_id` in `WITH CHECK` is **necessary but not sufficient**. There is no policy formulation
that fixes this; RLS is structurally the wrong tool for this class of leak, because the leak is not in
a row's visibility but in a constraint that never consults visibility. The only two mechanisms that do
work are:

- **Composite FK on `(id, account_id)`** — preferred. The parent gains `UNIQUE (id, account_id)`
  (redundant against its PK, and that is the point: it is what makes the pair referenceable), the
  child's FK spans both columns, and Postgres itself makes a cross-account edge unrepresentable. No
  new column is needed on the child — its `account_id` already exists and now does double duty.
- **An application-level check on every write path** — the fallback. Load the parent through an
  account-scoped query before the insert and reject a miss. Correct only if *every* write path does it,
  which is exactly the property a schema constraint gives for free and code review does not.

**Nullable parent links stay optional.** Postgres multi-column FKs default to `MATCH SIMPLE`: if any
referencing column is NULL the constraint is not checked. Since `account_id` is `NOT NULL` on every
child, an optional link (`building.landlord_id`, `meter.unit_id`, the `direct_*` columns) keeps its
"unset" meaning. Do **not** write `MATCH FULL` — it would forbid the unset case.

### Blast radius (surveyed against `packages/db/src/lokara_db/models.py`)

**15 foreign keys join two account-scoped tables, and all 15 are currently bare FKs on `id`:**

| Child → parent | Column(s) |
| --- | --- |
| `building` → `landlord` | `landlord_id` (nullable) |
| `unit` → `building` | `building_id` |
| `tenancy` → `unit` | `unit_id` |
| `tenancy_party` → `tenancy` | `tenancy_id` |
| `tenancy_party` → `renter` | `renter_id` |
| `self_use_period` → `unit` | `unit_id` |
| `statement` → `building` | `building_id` |
| `cost_entry` → `building` | `building_id` |
| `allocation_key_assignment` → `cost_entry` | `cost_entry_id` |
| `allocation_key_assignment` → `unit` | `direct_unit_id` (nullable) |
| `allocation_key_assignment` → `tenancy` | `direct_tenancy_id` (nullable) |
| `meter` → `building` | `building_id` |
| `meter` → `unit` | `unit_id` (nullable) |
| `meter_reading` → `meter` | `meter_id` |
| `heating_cost_entry` → `building` | `building_id` |

`tenancy.unit_id` is the concrete case that surfaced the rule, found while writing the isolation tests
for `tenancy` / `tenancy_party` (commit `d751897`). It is not special — it is 1 of 15.

**Plus 2 edges on `building_assignment`** (`membership_id`, `building_id`). That table carries no
`account_id` of its own today; its scope is *derived* through `membership`. A `building_assignment`
pointing at another account's building is a read-access leak, not just a bad edge — an EMPLOYEE of
account B would be granted account A's building.

> **DECISION (settled, 02.08): `building_assignment` gains an `account_id` column** — it is not left
> to the app-level fallback. Three reasons, recorded because the denormalisation looks gratuitous
> until you see the third:
>
> 1. **Every other tenant table has one.** Transitive scoping is the single odd case out; keeping it
>    special means every future reader has to learn the exception.
> 2. **An app-level check is exactly what gets forgotten** when the next endpoint is written. That is
>    the whole reason the rule exists.
> 3. **The usual objection to denormalising `account_id` is drift** — the copy silently disagreeing
>    with its parent. The composite FK
>    `(membership_id, account_id) REFERENCES membership (id, account_id)` makes drift
>    **structurally impossible**: the column cannot disagree with its membership, because a
>    disagreeing pair does not exist in the parent. The denormalisation is self-enforcing.
>
> Its RLS policy then compares the **local column** (`account_id = current_setting('app.account_id', true)`)
> instead of the `EXISTS (SELECT 1 FROM membership …)` subquery it uses today, which also makes it
> identical to every other table's policy.
>
> **Consequence for the gates:** with the column in place, `building_assignment` moves out of the
> `EXEMPT` path in `scripts/check_rls_coverage.py` and into the ordinary tenant-table loop. Verified
> live against the migrated DB by the lead: the problem count is unchanged, because the table is
> already ENABLEd + FORCEd + policied and already named in
> `packages/db/tests/test_rls_isolation.py`, so it passes all four checks the moment it enters the
> loop. Its `EXEMPT` entry becomes **dead code and should be removed when the migration lands**
> (that script is lead-owned — note it, don't edit it).

### Completeness is enforced by a gate, not by a test count

The 15 + 2 edges are **not** covered by 17 tests, and never should be — a test-per-edge list rots the
moment someone adds edge 18, and its absence is invisible.

- **`scripts/check_fk_isolation.py`** (lead-owned, not yet written) is the completeness mechanism: it
  fails on any foreign key between two account-scoped tables that is not composite on
  `(id, account_id)`. **This is what any NEW foreign key has to satisfy** — the rule is enforced at
  the schema level, once, for edges that do not exist yet.
- **`packages/db/tests/test_rls_isolation.py::TestCrossAccountForeignKeys`** is the *behavioural*
  proof that the mechanism does what this section claims: as `lokara_app` in account B's context,
  insert a row that stamps `account_id = B` (so `WITH CHECK` passes) but whose FK points at a parent
  owned by account A, and assert the **database** refuses it. Three representative shapes, chosen for
  shape and not for coverage:

  | Test | Edge | Shape it stands for |
  | --- | --- | --- |
  | `test_cross_account_unit_parent_is_rejected` | `unit.building_id → building.id` | plain `NOT NULL` child |
  | `test_cross_account_nullable_parent_is_rejected` | `meter.unit_id → unit.id` | nullable link (`MATCH SIMPLE` must keep "unset" legal) |
  | `test_cross_account_building_assignment_is_rejected` | `building_assignment.building_id → building.id` | transitive scope (no local `account_id` yet) |

  All three currently fail with `DID NOT RAISE IntegrityError` — the database accepts a row it must
  refuse. The third is written against **today's** schema (a `building_assignment` whose *membership*
  belongs to B, whose *building* belongs to A): the new `account_id` column is needed for the **fix**,
  not for the test, so the test fails for the defect rather than for a missing column.

FKs to `account.id` itself (14 — one per entry in `ACCOUNT_SCOPED_TABLES`) and the 2 to the global
`person.id` are out of scope: `account` *is* the boundary and `person` is deliberately global.
That accounts for all 33 FKs in the file: 15 tenant-to-tenant + 2 on `building_assignment` + 14 + 2.

### Reading the sketches in this file

The inline SQLAlchemy sketches elsewhere in this document predate this rule and show the bare
`ForeignKey("unit.id")` form. They are illustrative of *shape*, not of the constraint; where a sketch
crosses two account-scoped tables, the composite form above is the binding one.

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
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))   # every domain row is scoped
    unit_id: Mapped[str] = mapped_column(ForeignKey("unit.id"))
    sqm_x100: Mapped[int]                              # self-used m² × 100 — an AREA, not a flag
    kind: Mapped[SelfUseKind] = mapped_column(default=SelfUseKind.OWNER_OCCUPIED)
    note: Mapped[str | None]
    valid_from: Mapped[date]                           # validity is day-granular DATE (see principle)
    valid_to: Mapped[date | None]
    unit: Mapped["Unit"] = relationship(back_populates="self_use_periods")
    __table_args__ = (Index("ix_self_use_unit", "unit_id"), Index("ix_self_use_account", "account_id"))
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
- **Rollout:** the `allocation_key` **PG enum type ships at M0/Phase B** (parity with the Prisma M0), but
  the per-period **`AllocationKeyAssignment` table arrives with M3** plumbing — the enum exists before the
  table that uses it.

### Heating costs are a separate table — never a flag on `CostEntry`

A Betriebskosten row *has* an allocation key; a **heating cost does not** — §§7–9 HeizkostenV determine
its split (base/consumption, warm-water separation, CO₂). Putting heating on `CostEntry` would surface an
Umlageschlüssel dropdown for a cost whose split isn't the user's to choose, inviting a **legally wrong
answer**. Separate tables also keep the proven NK path untouched.

### Meters: `MeterKind` and `MeasurementUnit` are independent axes

A building's Wärmemengenzähler and a flat's Heizkostenverteiler are both `kind = HEAT`, but only the
**unit** says whether a reading may serve as the **§9 denominator**. Never infer one from the other.
`MeterReading` carries the normalized shape (`value`, `measurement_unit`, `reason`, `source`), so a
manually entered row and an MDL/adapter import are indistinguishable downstream — that's the point of
the port.

**Readings are create-only, enforced structurally.** No `superseded` / `replaced_by` / `updated_at`
column exists, and there is **no PUT/PATCH route** (asserted by a test over the OpenAPI paths), so a
correction can only be a new row; supersession is *derived* from `read_at` + `recorded_at`. Superseded
rows are shown struck through, never hidden — the audit trail is the feature.

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
