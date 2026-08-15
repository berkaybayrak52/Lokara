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

### SQLAlchemy 2.0 identity sketch (historical core, not a live model count)

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

- **`scripts/check_fk_isolation.py`** (lead-owned) is the completeness mechanism: it
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

  > **Since `0004` landed** all three are green, with their assertions unchanged in substance. What
  > did change (03.08): each `pytest.raises` now matches the **specific constraint name**
  > (`unit_building_id_fkey`, `meter_unit_id_fkey`, `building_assignment_building_id_fkey`) instead of
  > the generic `"foreign key constraint"`. The generic match would equally accept a rejection from
  > `*_account_id_fkey` — a different failure with a different meaning — so the test could have gone
  > on passing while the cross-account edge it names was no longer the thing being refused.

FKs to `account.id` itself (14 — one per entry in `ACCOUNT_SCOPED_TABLES`) and the 2 to the global
`person.id` are out of scope: `account` *is* the boundary and `person` is deliberately global.
That accounts for all 33 FKs in the file: 15 tenant-to-tenant + 2 on `building_assignment` + 14 + 2.

> **After migration `0004` landed** the counts read (confirmed against `pg_constraint` on the live
> schema, 03.08): **34** foreign keys — **17** composite tenant-to-tenant (the 15 above plus the 2 on
> `building_assignment`, which now has its own `account_id`), **15** to `account.id` (one per entry in
> `ACCOUNT_SCOPED_TABLES`, `building_assignment` included), **2** to `person.id`. The survey above is
> kept as written because it is the *pre-migration* blast radius; 17 / 15 / 2 / 34 is the current
> state. The 2 to `person.id` are the subject of the next subsection.

### Limit of the rule: an edge to a **global** table is outside it

> **The rule above is about tenant-to-tenant edges only.** An FK from an account-scoped table to a
> **global** table (`person`, and `account` itself) can never be composite, so it is not covered — by
> the rule, by `scripts/check_fk_isolation.py`, or by `TestCrossAccountForeignKeys`. Such an edge
> needs a **different mechanism**, chosen deliberately. This is a stated limit, not a gap to be
> discovered again by the next global table.

**The two edges that have this shape today** — both to `person`:

| Child → parent | Column | Meaning |
| --- | --- | --- |
| `membership` → `person` | `person_id` (`NOT NULL`) | which human holds this seat in the account |
| `renter` → `person` | `person_id` (nullable) | optional portal login for a Mieter (column exists; **written only at M10**, by activation-code redemption — see below) |

**Verified live against `0004` (03.08, lead + audit).** `person` carries no RLS at all
(`pg_class.relrowsecurity = f`, `relforcerowsecurity = f`, zero rows in `pg_policies`), and the write
below is **accepted**:

```sql
set app.account_id = 'acc_iso_check';
INSERT INTO renter (id, account_id, legal_name, person_id)
VALUES (…, 'acc_iso_check', 'Fremde Person', 'per_demo_owner');   -- ACCEPTED
```

`per_demo_owner` belongs to a different account. The row is correctly isolated (`account_id` is the
caller's own, so `WITH CHECK` passes and only the caller reads it), but the **edge points at a human
who has no relationship to this account** — the same class of defect the composite FK was introduced
to make unrepresentable, one step out of its reach.

**A composite FK cannot fix this, and `account_id` on `person` is not the answer.** There is nothing
to compose with: `person` has no `account_id`, and it must not get one. One human legitimately belongs
to **many** accounts — that is the entire reason Person / Account / Membership are three tables and
not two (see "Person / Account / Membership" above). Giving `person` an owner would either duplicate
the human per account (breaking one identity ↔ one Supabase Auth user) or pick one account as the
owner (breaking every other account's link). Both are worse than the leak.

**What follows from this:**

- The completeness gate is silent here **by construction** — `check_fk_isolation.py` inspects edges
  between two account-scoped tables, and this is not one. A green gate says nothing about
  `person_id`. Do not read it as coverage.
- **The finding is one sentence but two different problems**, and they do not have the same answer or
  the same milestone. Read side = "which `person` rows may this caller see". Write side = "who may
  create a `person ↔ renter` link". See the next subsection — that split is settled (03.08).
- **Before adding the next edge to a global table**, state in this file which mechanism guards it. An
  edge to a global table with no named mechanism is the defect, whether or not anyone has exploited
  it yet.

### The `person` edge splits: READ is a policy (M5a), WRITE is an ordering rule (M10)

> **DECISION (settled, 03.08).** The audit finding above was carried into `PLAN.md` as a single M5 DoD
> line — *"an insert of `renter(person_id = a person with no relationship to this account)` is
> rejected"*. That line is **withdrawn**: it is not merely hard to express, it forbids the one write
> that must be legal. What replaces it is below.

#### Why the write invariant cannot be stated, and must not be

**There is no non-circular witness.** "This person has a relationship to this account" can only be
witnessed by one of the two edges that point at `person`:

- `membership` — but a renter never holds a Membership. `Role` is staff-only by design (`OWNER` /
  `EMPLOYEE` / `TAX_ADVISOR`; see "Roles" above: *"`RENTER` is **not** in the Role enum"*). A trigger
  reading `EXISTS (SELECT 1 FROM membership WHERE person_id = NEW.person_id AND account_id =
  NEW.account_id)` would reject **every legitimate renter activation** and admit only the one case
  that deserves a second look — wiring a staff login into a renter row. The predicate is backwards.
- `renter` itself — which is the row being inserted. `EXISTS (SELECT 1 FROM renter r WHERE
  r.person_id = NEW.person_id AND r.account_id = NEW.account_id)` can never become true for a first
  link. It is a bootstrap that never starts.

**And the invariant is wrong on the merits, not just unimplementable.** At the moment of activation the
person *by definition* has no prior relationship to the account — that is what onboarding is. Worse, the
product's headline differentiator (`PLAN.md` execution order row 2, `docs/06` persona 4: *one login —
Vermieter **and** Mieter **and** Investor*) requires exactly the shape the rule would forbid: a human who
is an `OWNER` in account A being linked as a renter in account B. Enforcing the line as written would
break persona 4 in the database.

#### What the real invariant is: **consent, not scope**

`renter.person_id` is not a scoping column. This file already says what it is
(see "Identity" and the `Renter` sketch): *"portal access is just `Renter.personId` pointing at a
Person"* / *"set = renter can log into the portal"*. Writing it **grants a human login access to a
tenancy's statements**. The question it raises is *did that human consent, and did the landlord intend
this human* — an authorization question, which no referential constraint has ever been able to answer.

The model already carries the consent artifact: `ActivationCode` (**tenancy-bound, per-person,
single-use**; listed under "Other temporal/immutable entities", built at M10 — `PLAN.md` → M10,
*"Mieterportal (activation codes bound to Tenancy, per-person, single-use)"*). Redeeming a code **is**
the proof. So:

> **Rule (ordering + default), owned by M10.** `renter.person_id` is **NULL at creation** and is written
> by **exactly one** code path: redemption of an ActivationCode bound to one of that renter's tenancies.
> No trigger, no CHECK, no foreign key expresses this, and none should be added.

Its two halves are proven in two different places, because neither is a database property:

| Half | Artifact | Milestone |
| --- | --- | --- |
| NULL at creation | `renter.person_id` is nullable with no default — **already true** in `models.py` and in the migrated schema (verified 03.08). Nothing to build. | done |
| exactly one writer | **No API write path sets `person_id`** — proven the way create-only `meter_reading` is proven, by a test over the OpenAPI paths asserting absence (see "Meters" above). | M5 remainder (owns the API) |
| the writer is redemption | The redemption test: a valid single-use code sets `person_id`; a spent, foreign, or wrong-tenancy code does not. | M10 |

An ordering rule with no artifact decays into a comment. These three lines are the artifact.

#### The read side **is** expressible, and it is M5a's

Reading a `person` row through `renter` or `membership` is a join to an **already-scoped** table, and
the row being tested is not the row that creates the relationship — so none of the circularity above
applies. `person` therefore gets RLS:

> **Policy (M5a).** A caller sees a `person` row only if the row is reachable from the caller's own
> account. `person` is `ENABLE` + `FORCE ROW LEVEL SECURITY` with a policy whose `USING` is an
> `EXISTS` over `membership` scoped by `current_setting('app.account_id', true)`.

Five things the implementer must decide or respect — items 2–4 were decided when the policy was
written (`0005`, 03.08); 1 and 5 remain constraints on later work. Recorded here so the failing test
cannot be
"fixed" the wrong way:

1. **Deny by default is not negotiable.** With no `app.account_id` set, `current_setting(..., true)`
   is NULL, the `EXISTS` is false, and the caller sees zero `person` rows. Do **not** add
   `OR current_setting('app.account_id', true) IS NULL` to make a login flow work — that disables the
   policy for every unscoped connection in the system. **The login/bootstrap lookup** (find the Person
   for this Supabase Auth user, *before* any account context exists) is a genuinely different read and
   needs a genuinely different path: a `SECURITY DEFINER` function, a dedicated role, or Supabase
   Auth's own tables. `TODO(M5-remainder)`: name which.
2. **DECIDED (M5a, migration `0005`): yes — a renter link counts.** The `USING` is
   `EXISTS(membership) OR EXISTS(renter)`, both scoped by `current_setting('app.account_id', true)`.
   With `membership` alone, an account that has linked a renter's portal login cannot read that
   `person` row back through `Renter.person`: it resolves silently to `None`, and the API would need a
   `SECURITY DEFINER` escape hatch for an ordinary, legitimate read — adding a bypass so a normal read
   works is precisely the failure mode this policy exists to prevent. The disjunct widens visibility by
   no more than the account already controls: `renter` is itself account-scoped and FORCEd, so it can
   only match that account's own renters, humans it invited and whose `legal_name` it already stores.
   It gives a renter *session* nothing — see item 5.
3. **DECIDED (M5a, migration `0005`): the policy is `FOR SELECT`, so INSERT/UPDATE/DELETE have no
   policy and are denied.** `FOR ALL` derives `WITH CHECK` from `USING`, which grants no write signup
   needs — a brand-new Person has no Membership, so it fails its own policy either way — while granting
   one nobody should have: any account sharing a membership could rewrite or delete that human's
   **global** identity row, including the `email` their login hangs on, refused today only by an
   incidental FK from `membership`. Measured both ways against the live database before choosing.
   **The consequence M5-remainder inherits:** under `lokara_app`, `person` is read-only — an INSERT
   raises `InsufficientPrivilege`, an UPDATE/DELETE raises nothing and matches **0 rows**
   (SQLAlchemy turns that into `StaleDataError`). Signup, profile edits and invitations all wait on the
   bootstrap path in constraint 1.
4. **The composition with `membership_isolation` is real, and verified.** A table named inside a policy
   expression is itself subject to RLS for the querying role, so the `EXISTS` runs under
   `membership_isolation` / `renter_isolation` — with `membership_isolation` temporarily set to
   `USING (false)`, every `person` row disappeared. It is harmless only because those policies carry the
   same account predicate this one does, making the composition an intersection of identical filters.
   It is **not** free of coupling: narrowing either policy later (e.g. "you see only your own membership
   row") would silently narrow `person` visibility with it. That is why the `person` policy repeats the
   account comparison rather than leaning on the referenced table to supply it.
5. **The renter portal is not an `app.account_id` context.** Portal URLs are `/renter/{tenancyId}/…`
   (see "Portals & active context"). Whatever RLS context a renter session runs under is **M10's**
   problem; `person` RLS at M5a must not be read as having solved it. In particular, giving a renter
   session `app.account_id = <the landlord's account>` would expose every renter in that account —
   do not do that.

> **Known, accepted limit:** `person.email` is globally `UNIQUE`, and a unique-violation fires
> regardless of row visibility. Any account can therefore probe whether an email address is already
> registered. This is an enumeration oracle inherent to a global identity table (Supabase Auth has the
> same property) and is **not** closed by the policy above. Recorded, not fixed.

#### `landlord` and `self_use_period`: policies exist, coverage did not

Both tables have been `ENABLE`d, `FORCE`d and policied since migration `0001` (verified against
`pg_policies`, 03.08 — `landlord_isolation` / `self_use_period_isolation`, both
`account_id = current_setting('app.account_id', true)` in `USING` **and** `WITH CHECK`). The two
problems `scripts/check_rls_coverage.py` reports are check **4** only — *not named in
`packages/db/tests/test_rls_isolation.py`*, i.e. the policy was never exercised. M5a closes that by
naming them. `self_use_period` is the substantive one: a `SELF_USED` row written onto a foreign unit
would silently remove that unit's area from the other account's allocation base (see "Eigennutzung"),
so its `WITH CHECK` is worth a test of its own rather than a mention.

### Reading the sketches in this file

The inline SQLAlchemy sketches elsewhere in this document predate this rule and show the bare
`ForeignKey("unit.id")` form. They are illustrative of *shape*, not of the constraint; where a sketch
crosses two account-scoped tables, the composite form above is the binding one.

## Temporal core: Building → Unit → Tenancy

`Building 1─N Unit 1─N Tenancy`. Tenancy has `valid_from/valid_to`.

**Multi-party leases via `TenancyParty` (M0).** A Tenancy links to its renters through a join entity,
not a direct FK — several renters can be on one lease (an entry-ticket requirement), and the link
itself can carry per-party data later. Present from M0, minimal (no portal link yet — that's
`Renter.person_id`; the column exists, but nothing writes it before M10's activation flow).

```python
class TenancyParty(Base):
    __tablename__ = "tenancy_party"
    id: Mapped[str] = mapped_column(primary_key=True, default=cuid)
    tenancy_id: Mapped[str] = mapped_column(ForeignKey("tenancy.id"))
    renter_id: Mapped[str] = mapped_column(ForeignKey("renter.id"))
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"))   # scoped like every row
    __table_args__ = (UniqueConstraint("tenancy_id", "renter_id"), Index("ix_tp_account", "account_id"))
```

### DEFECT: `Tenancy.advance_payment_cents` is a scalar on a temporal row (fix owned by M6)

> **Rechtsstand 08/2026** (recorded 03.08.2026). This entry introduces **no legal value** — no rate,
> ratio or table enters `packages/rules-store` from it. What is dated is the statutory *reason* the
> field changes mid-lease, quoted below. Standard caveat of `docs/07` applies.

**The rule broken.** This file's opening principle, and CLAUDE.md's "Temporal by default":
*anything that can change during a period is a row with `valid_from/valid_to`, never a scalar.*
`Tenancy` obeys it for the lease itself and breaks it for the advance:

```python
advance_payment_cents: Mapped[int]   # monthly NK Vorauszahlung — models.py, NOT NULL since 0001
```

The list in the principle (*tenancies, allocation keys, meters, self-use, IBANs…*) does not name the
Vorauszahlung. It belongs on it.

**Why it changes mid-lease — by statute, not by edge case.** § 560 Abs. 4 BGB: *"Sind
Betriebskostenvorauszahlungen vereinbart worden, so kann jede Vertragspartei nach einer Abrechnung
durch Erklärung in Textform eine Anpassung auf eine angemessene Höhe vornehmen."* Either party, after
every statement, in Textform. A multi-year tenancy whose advance never moves is the exception; the
scalar models the exception and cannot express the norm. Note the shape this implies for the eventual
row: an adjustment is a **dated declaration**, so it has a `valid_from` that is a legal fact, not a
bookkeeping convenience.

**Today there is no way to record a change at all.** The value is written once, at tenancy creation
(`POST /units/{unit_id}/tenancies`), and read back on tenancy read — **there is no update endpoint on
`tenancy`, and no PUT/PATCH anywhere on the resource**. So the only expressible workaround is to end
the tenancy and open a new one with the new amount.

**That workaround produces a visibly wrong document.** The statement keys parties on
`(unit_id, tenancy_id)` (`packages/pdf` `PartyKey`; `lokara_domain.Segment`/`Occupancy` carry
`tenancy_id`). One renter, one continuous lease, one advance adjustment would therefore render as
**two parties with two shares** on a single Abrechnung — two lines where the tenant is one party.

**No gate catches it.** `build_unit_segments` rejects *overlaps*; two consecutive tenancies do not
overlap, so it returns two clean segments, the money still reconciles to the cent, and every existing
test stays green. The defect is silent by construction.

**Nothing consumes the field yet** — it is no engine input, no `StatementData` field, and no line in
the rendered PDF (it is read only for display). That is why this is recorded now: today the fix is a
schema change; once a caller depends on the scalar, it is a schema change *plus* a caller migration.

**The fix, owned by M6.** Replace the scalar with a temporal child row — working name
**`AdvancePaymentPeriod`** (`tenancy_id`, `amount_cents`, `valid_from`, `valid_to`), account-scoped
and composite-FK'd like every other tenant-to-tenant edge. **The actual design is M6's**, not this
entry's: how an adjustment records its § 560 Abs. 4 declaration, whether adjustments are immutable
versions, and how the API expresses create/read are open and deliberately not decided here. What is
decided is that the scalar goes.

**The migration cost, stated honestly.** `advance_payment_cents` is `NOT NULL` (migration `0001`) and
seeded for all three demo tenancies (220,00 / 150,00 / 110,00 € for units A/B/C), so this is a real
migration with a backfill: every existing tenancy becomes **one open-ended period**
(`valid_from = tenancy.valid_from`, `valid_to = NULL`), plus the API create and read shapes and their
Pydantic schemas. Small today; it does not get smaller.

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

## The Eigentümeranteil is a **residual line**, not a party

> **Source:** `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_02.md` § 1 (1.1–1.4), 14.08.2026, answering
> `FRAGEN-an-Berkay-02.md`. Primary rule text:
> `berkay-work/Spec-Seiten/01 · Die Abrechnung ….md` → **D0** (Fiktivbelegung), **D12**
> (Leerstandsaufstellung) and edge cases **E3**, **E17**, **E19**. Seite 01 is not otherwise
> transcribed yet; only the blocks named here are.
>
> **Rechtsnatur: fixed model rule, not a convention.** § 1.4 closes with *"Das ist meine feste
> Modellregel, keine offene Konvention. Ihr müsst hier nichts ‚vorläufig als eure Konvention'
> markieren — setzt es fest um."* So this section carries **no** `verify-before-production` flag.
> The `Fiktivbelegung bei Leerstand` register row it leans on **does** keep its flag
> (`Konvention`, Rechtsstand 07/2026) — the *residual* is settled, the *fictional occupancy count*
> that feeds a person-keyed denominator is not.

This replaces a model, it does not clarify one. Until 14.08.2026 the engines derived **one landlord
party per unit** from the vacancy/self-use segments and let that party carry the vacancy share. That
is wrong in his spec, and the two failure modes it produced (several landlord parties → *which one
holds the rounding rest?*; no landlord party at all → *no owner row exists*) are artefacts of the
derivation, not real cases.

### The rule

For one Liegenschaft and one Kostenart:

```
eigentuemeranteilCent[kostenart] = gesamtbetragCent[kostenart] − Σ mieteranteilCent[kostenart]
```

- **It is not a party.** It is a **structural reconciliation line**, one per
  `(Liegenschaft, Kostenart)`. It is never derived from occupancy, never allocated by a weight, and
  never `Bemessung × Quote`. D12: *"ALWAYS as a residual, NEVER computed separately"*.
- **It always exists**, including at `0,00 €`, including in a fully-let building with no vacancy and
  no self-use. There is no state in which a rest is "left over and has no bucket" — the bucket **is**
  the rest.
- **It may be negative.** `round_half_up` on the renter side biases the renter shares upward, so
  Σ Mieter routinely exceeds the pot by a cent or two and the residual absorbs it with a minus sign.
  −0,01 € is the ordinary output of a fully-let building, not a defect (`CLAUDE.md` DoD 4 already
  allows it).
- **Σ Mieteranteile + Eigentümeranteil = Gesamtkosten holds by construction**, per Kostenart and in
  total. That is the whole point: **one** line explains every ±ct of the statement.

### What the renters' denominator still contains

The residual is not a way of *skipping* the vacancy — the vacancy is in the **denominator**, which is
what makes the residual come out at the vacancy share rather than at zero. Per **D0**:

- **Area and unit denominators are already period-based** (`gesM2 × nTage`), so a vacant unit's
  m²-Tage / Wohneinheits-Tage stay in the denominator automatically and its share falls to the owner
  (BGH VIII ZR 159/05). **E19:** a unit vacant for the whole period stays in the Gesamtverteiler and
  is never removed from it.
- **Person-keyed denominators get the Fiktivbelegung** added before any denominator is formed
  (`nPersTage += fiktivPersonen × L.tage`). His `09-F07`: `nPersTage = 2.006 + 2 × 31 = 2.068` — the
  62 Personen-Tage of the empty unit are *in* the denominator, and 62000 − Σ Mieter = **1858** is
  therefore the vacancy share, arrived at as a rest.
- **Consumption denominators are untouched** — a vacant unit consumed nothing, so its residual on a
  consumption-keyed Kostenart is genuinely `0,00 €`. That is why his `09-F19` prints the Eigentümer
  column at `0` for Wasserversorgung, Entwässerung and Heizkosten while carrying `3174` for
  Grundsteuer. Zero there means *zero*, not *absent*.
- **Zero denominator (E3):** where a consumption key captured nothing at all, every renter share is
  `0,00 €` and the residual is the **whole** amount, with the note *"Für diese Kostenart wurden keine
  Verbrauchswerte erfasst; die Kosten verbleiben beim Eigentümer."* The cost is never silently
  re-keyed. This is the one case where the allocation primitive may not divide, and it is a rule,
  not an exception to invent at the call site.

### Display aggregates; the data keeps its origin

His § 1.4, and the constraint that makes the shape non-obvious: the Gesamtübersicht shows **one**
Eigentümer line per Liegenschaft, but the landlord needs the vacancy share **per object** for Anlage
V, so the origin may not be thrown away. D12 splits the residual into three blocks:

| Block | Meaning | Granularity |
| --- | --- | --- |
| **(a)** Leerstandsanteil | Werbungskosten § 9 EStG, Anlage V | **per empty unit and per Kostenart** — retained in the data |
| **(b)** nicht umlagefähige Kosten | Werbungskosten, a different Anlage-V line (his Seite 04) | per cost position; **not modelled yet** — Seite 02 dependency, see below |
| **(c)** Rundungsdifferenz | no economic item | belongs to **no** unit; disclosed separately |

`(a)` is each empty unit's share **computed for the annex** (its own `round_half_up`); `(c)` is what
is left: `residual − Σ (a)`. They differ, and the difference is the point — his `09-F19`: separately
computed `17.536`, as a residual `17.531`, and the **5 ct is block (c)**. The printed Eigentümer
amount is always the residual; the annex explains it. *"Aggregation im Display, Herkunft in den
Daten."*

### Shape

Not a table. The residual is **computed, never stored** — storing it would create a second place
where the statement's reconciliation can be wrong. It is a field of the engine result and a section
of the immutable `Statement` snapshot, alongside the party lines:

```python
# packages/heating-engine — the same shape the NK engine grows when Seite 02 lands.
@dataclass(frozen=True)
class OwnerResidualOrigin:
    """Block (a): one empty/self-used unit's own share of each block, for the
    Leerstandsaufstellung. Never printed on the Gesamtübersicht."""
    unit_id: str
    ...                      # one field per money column, plus the Bemessungen (Block C needs them)

@dataclass(frozen=True)
class OwnerResidual:
    """The one line per (Liegenschaft, Kostenart). Carries no quota — by shape,
    not by discipline: there is no percentage field to print."""
    ...                                          # one amount per money column, and their total
    origins: tuple[OwnerResidualOrigin, ...]     # (a) — empty tuple in a fully-let building
    rounding_difference: Cents                   # (c) = total − Σ origins.total
```

- **The renter lines carry only Mietverhältnisse.** `tenancy_id is None` disappears from the party
  list; a landlord "party" is no longer a party. That is what makes *"never computed separately"*
  structural rather than a rule someone has to remember.
- **The Bemessungen of the empty units survive on `origins`**, because § 9b Abs. 3 disclosure
  (`docs/08` Block C — Nutzerwechsel) still has to print the vacancy segment's Zeitanteil even though
  its money row is gone from the table.
- **The primitive is `distribute_cents_owner_residual(pot, renter_weights, *, owner_weight)`**
  (`packages/domain`), returning `(renter_shares, owner_cents)`. Deliberately **not**
  `distribute_cents_half_up(..., residual_index=i)`: that signature says *the owner is the party at
  index i*, which is the model this section replaces, and it lets a caller pass the owner as a party
  by accident. The new signature cannot express that.

### This is cross-engine and binding — but only `heating-engine` switches in this slice

The rule is Berkay's, for the whole Abrechnung, and it is settled. Its **application to `nk-engine`
belongs to the Seite 02 → `docs/09` transcription** and to nothing before it. Recorded here so that
the asymmetry is a dated decision and not read as an oversight:

- **The residual model requires `round_half_up` on the renter side. The two are not independent.**
  Largest-remainder distributes the *whole* pot across whatever weight list it is handed, so
  Σ over that list == pot **by construction**. Either the owner is in the list — then its amount is
  *computed separately* from a weight (D12 forbids exactly that) and a leftover cent can land on a
  renter (K9 forbids exactly that) — or it is not, and then Σ Mieter == pot and the Eigentümer line
  is structurally `0,00 €` even where a unit stood empty all year. Both readings are wrong. Half-up
  per renter share is a **prerequisite** of the residual, not a separate choice.
- His own `09-F07` variant A is the proof at one line: half-up per renter gives
  `32829 / 12712 / 3658 / 10943`, Σ `60142`, residual **1858**. Largest-remainder over the same five
  weights gives `32829 / 12712 / 3657 / 10943 / 1859` — it moves a cent off *Weber* and prints the
  owner at its own separately-computed quota. His comment: *"Gerechnet wird 1858. Residuum gewinnt."*
- Switching NK's renter rounding therefore **moves every NK figure**, and doing it here would be
  implementing a calculation from a spec that has not been transcribed — the one thing `CLAUDE.md`
  forbids. `nk-engine` keeps largest-remainder until `docs/09` exists (`CLAUDE.md` DoD 4,
  `docs/03` § 9.1 last row).

### One register row may need re-wording — reported, not rewritten

The Rechtsstand-Register row **`Verteilungsrest (K9)`** is worded as a house convention
(*"keine — reine Hauskonvention"*, `Konvention` / `verify-before-production`). Under this model the
*destination* of the Verteilungsrest is no longer ours to choose: it is D12's residual, and Berkay
has set it fest. K9's remaining content is the **rounding direction** (`round_half_up` per line,
R1/R5), which is his too. Agents may edit `berkay-work/` only with Emir's explicit permission, and
the register is imported as-is (`CLAUDE.md` precedence rule 3), so this legal mismatch is not edited
here — it is reported for the next register export.

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

## Statement preview and finalization — live draft, immutable archive

> **Design decision 08/2026; implementation belongs to M6.** Previewing is cheap and repeatable;
> finalizing is an auditable event that creates documents fit to retain and, once M6 supplies the
> actual paid advances and Saldo, send.

- **Draft preview is live and creates no archive.** It reads the current normalized rows, runs the
  engines and renders the landlord calculation overview on demand. Editing an input and previewing
  again replaces nothing because no statement version exists yet.
- **Finalization creates exactly one immutable, versioned statement snapshot** for
  `(account_id, building_id, billing_period, version)`. It contains the normalized inputs used by
  the engines; engine and rule versions plus every applicable `Rechtsstand`; calculated results and
  party lines; `created_at`; content hashes; and the archived document bytes or immutable storage
  keys with their hashes.
- **One calculation produces separate documents.** Finalization archives one internal
  **Vermieter-Gesamtübersicht** with the building-wide reconciliation and one independently rendered
  **Mieter-Einzelabrechnung per eligible covered tenancy with >0 period-clipped usage days**. The
  server selects that tenancy's data before rendering. Per Berkay Seite 01 **E8 / `08-F17`**, a
  tenancy clipped to 0 usage days gets no document and is not visible in the tenant portal; the
  Vermieter-Gesamtübersicht carries the required footnote. This case is **not vacancy** and must not
  create a landlord vacancy segment. The system never renders one all-renters PDF and then crops,
  hides or masks sections.
- **Corrections append.** A correction finalizes `vN+1`, retains `vN`, and records that `vN+1`
  supersedes `vN`; neither the snapshot nor its archived documents are overwritten.
- **Referenced inputs become retention-bound.** A cost, heating-cost row, meter reading, tenancy or
  other normalized input referenced by a finalized snapshot cannot be destructively deleted.
  Corrections append a new row or supersede the old row, preserving the bytes needed to reproduce
  every finalized version. Draft-only inputs remain editable under their ordinary domain rules.

The snapshot is not a cache of the current database. It is the complete evidence package for what
was calculated and rendered at finalization time; later previews may legitimately differ without
changing an older version.

### Payment Ledger (source of truth for tax — built at M6)

- `Payment`: **date mandatory**, amount (cents), direction, account/landlord/building/unit/renter,
  category, **source** (finAPI | manual | invoice), receipt ref, **version history**.
- `TaxCategoryMapping`: category → Anlage-V line (**year-versioned**) + SKR03 + SKR04; StB-overridable.
- Export = **pure deterministic function** `f(ledger, mapping, params) → file`. DATEV EXTF is
  Windows-1252, `;`, CRLF (the #1 footgun). Every export archived immutably with hash + timestamp.
- **The statement's Saldo block (BGH formal minimum #4) waits here.** It needs the *geleistete*
  Vorauszahlungen — what the renter actually paid — which only this ledger knows, **and** the temporal
  `AdvancePaymentPeriod` above to say what was owed when. Both are M6; the block is therefore M6, not
  a rendering task. See `docs/08` → "#4 is blocked on the M6 ledger, by decision".

## Other temporal/immutable entities (added as their milestones arrive)

`Meter` (+ `calibrationValidUntil` / Eichfrist), normalized `MeterReading` (`unit`, `reason`,
`source`), `AfaRecord`, `Loan`, `Reminder`, `LettingEffort` (vacancy evidence), `Ticket`,
`ExportArchive`, `SubProcessor`, `ActivationCode` (tenancy-bound, per-person, single-use),
`IbanHistory` (versioned), `EmailDelivery` (append-only), `ClauseBlock`/`ClauseVersion`/`Contract`
(composition), `ProspectObject` (Prüfobjekt → becomes Building on purchase).
