# 02 — Data model

This is Lokara's canonical, living data-model contract. It describes current repository truth,
approved interfaces that production must still implement, and milestone-owned gaps. Superseded
chronology remains available in Git with
`git show 635acf9:docs/02-data-model.md`; it is not part of the active specification.

## Reading guide and status vocabulary

Every status in this file describes repository delivery, not legal certainty. A rule may be shipped
and still carry `verify-before-production`; an approved specification may still have no production
implementation.

| Status | Meaning |
| --- | --- |
| **Shipped** | Present on `main` in the current model, migration, engine or enforced gate. |
| **Capability shipped** | A bounded reusable behavior is present and green, but its larger end-to-end workflow is not closed. |
| **Prepared but unmerged** | Implemented and verified on a named branch, but absent from `main`; do not treat it as deployed schema or API. |
| **Specified** | Documented as the contract for later implementation; its review state is stated separately. Data-only oracles validate transcription, not production behavior. |
| **Future** | Direction and milestone ownership are known, but the final schema or API shape is not yet approved or shipped. |

## 1. Global principles and model map

- Money is integer cents. Fixed-point measurements use scaled integers; engines use
  `decimal.Decimal`, never `float`.
- Every domain row carries `account_id`. `Account` is the isolation boundary; `Person` is the
  deliberate global identity exception.
- A fact that can change during a period is a dated row, not a mutable current-value scalar.
  Validity is day-granular `date`; audit and event times use `timestamptz`.
- Legal and financial records are append-only or versioned. A correction creates a successor and
  preserves the facts and bytes used by the earlier result.
- Billing-period allocation and tax cash-basis accounting are separate systems with one explicit
  ledger handoff.

The live SQLAlchemy definitions are in
[`packages/db/src/lokara_db/models.py`](../packages/db/src/lokara_db/models.py). This file owns the
model contract; `models.py` owns the exact shipped columns and constraints.

```text
global identity                         account-isolated domain

Person ──< Membership >── Account ──< Landlord ──< Building ──< Unit
  │             │                                      │          │
  │             └──< BuildingAssignment >──────────────┘          ├──< Tenancy
  │                                                               │       └──< TenancyParty >── Renter
  └──────────────────────────────────────────────────────────────────────────────┘
                                                                  ├──< SelfUsePeriod
                                                                  └──< Meter

Building ──< CostEntry ──< AllocationKeyAssignment
         ├──< HeatingCostEntry
         ├──< MdlStatement ──< MdlStatementPosition >── Tenancy
         └──< Statement
Tenancy ──< PersonCount
Meter ──< MeterReading
```

The outer `Person` links are deliberate global-table exceptions. Every edge between
account-scoped tables carries the same `account_id`; section 3 lists all 22 enforced edges.

| Model area | Current shape | Status |
| --- | --- | --- |
| Identity and access | `Person`, `Account`, `Membership`, `BuildingAssignment`, `Landlord`, `Renter` | **Shipped** |
| Property and occupancy | `Building` (with `fiktivbelegung_mode` and `fiktivbelegung_waiver_note`), `Unit`, `Tenancy`, `TenancyParty`, `SelfUsePeriod`, `PersonCount` | **Shipped** |
| Operating-cost inputs | `CostEntry`, `AllocationKeyAssignment` | **Shipped** |
| Metering and heating inputs | `Meter`, `MeterReading`, `HeatingCostEntry` | **Shipped** |
| Confirmed third-party heating statement | `MdlStatement`, `MdlStatementPosition` — validated and passed through, never recomputed (`docs/03` H7) | **Shipped** |
| Statement row | `Statement` with period, version, status, total and optional content hash | **Shipped**, but not the complete Page 01 snapshot/finalization contract |
| Page 01 normalized result and audience projections | One calculation result projected to owner, one tenancy or tax | **Capability shipped** — server-side selection exists (`OWNER`/`TENANT`/`TAX`); the immutable finalized snapshot does not |
| Temporal advance schedule, receivables, payment ledger and immutable finalization | M6 handoff described below | **Future** |
| Tax mapping, adviser profile, readiness result and export archive | Future M7 records; exact behavior is approved in `docs/11` | **Specified** |
| Renter activation and renter portal context | Activation-code redemption writes `renter.person_id` | **Future**, M10 |

These principles decide ambiguous additions:

| Question | Required answer |
| --- | --- |
| Can the fact change within a billing period? | Give it its own dated row; do not overwrite a current-value scalar. |
| Does one account-scoped row point to another? | Carry `account_id` through a composite foreign key as well as RLS and application scoping. |
| Does the value affect money or legal output? | Use integers/`Decimal`, retain rule provenance, and freeze the inputs and output at finalization. |
| Is the record a correction? | Append a successor and retain the earlier evidence; do not destructively edit history. |

## 2. Identity, roles, portal contexts, and renter activation

Lokara separates one human, one paid workspace and the relationship between them:

| Entity | Scope and invariant | Current shape |
| --- | --- | --- |
| `Person` | One global login mapped to Supabase Auth; no `account_id`. | Unique email, optional name, memberships and optional renter links. |
| `Account` | Paying workspace and isolation boundary. | `shape` is `SOLO` or `HAUSVERWALTUNG`; plan and billing belong here. |
| `Membership` | Person-to-account authorization relationship. | Exactly one membership per `(person_id, account_id)`; role is `OWNER`, `EMPLOYEE` or `TAX_ADVISOR`; revocation is retained. |
| `BuildingAssignment` | Object-level scope for an `EMPLOYEE`. | Zero assignments means no building visibility. It carries its own structurally consistent `account_id`. |
| `Landlord` | Legal lessor printed on statements. | Account-scoped data entity, never an authorization role. |
| `Renter` | Mieter domain record. | Account-scoped; access attaches through tenancies, not a `Membership` role. |

`RENTER` is not a role. `HAUSVERWALTUNG` is an account shape. A person may be staff in one account
and a renter in another.

Roles belong to `Membership` because authorization describes a person's relationship to one
account, not a permanent property of the person or account. The same human can therefore be an
`OWNER` in account A, a `TAX_ADVISOR` in account B and a renter in account C without duplicating the
login or assigning contradictory roles to an account. The shipped uniqueness constraint on
`(person_id, account_id)` deliberately starts with one staff role per person per account. Relaxing
that later is possible; recovering an unambiguous role after allowing duplicates is harder.
Membership lifecycle dates retain invitation, acceptance and revocation; revocation replaces hard
deletion so historical authorization and attribution remain explainable.

| Role or concept | Authorization meaning |
| --- | --- |
| `OWNER` | Full account scope: billing, roles, bank data and every building. |
| `EMPLOYEE` | Only assigned buildings. Zero `BuildingAssignment` rows means no building access. |
| `TAX_ADVISOR` | Read-only guest access for tax, export and AfA work, except the future adviser-owned profile and account-mapping fields specified in `docs/11`. |
| `RENTER` | Not a `Role`; it is an account-scoped person/tenancy domain relationship. |
| `Landlord` | Legal lessor data printed on a statement, never an authorization role. |

### Portals & active context

- Derive available contexts live from memberships and renter links; never store a `has_portal` flag.
- Keep owner/staff/tax context in `/a/{accountId}/…` and renter context in
  `/renter/{tenancyId}/…`. The URL survives tabs and bookmarks; the session does not select the
  authorization scope.
- Show a context switcher only when more than one authorized context exists.
- Navigation is not authorization. Every request verifies the relationship named in the URL, then
  scopes both application queries and Postgres RLS.
- Request traffic uses the restricted app role. Migrations use the owner connection. `FORCE ROW
  LEVEL SECURITY` means Supabase owner/admin flows must still use a deliberately authorized path.

Migration `0005`,
[`0005_person_read_isolation.py`](../packages/db/alembic/versions/0005_person_read_isolation.py), is
**shipped**. `person` is `ENABLE` + `FORCE ROW LEVEL SECURITY` with a `FOR SELECT` policy. A person is
visible when reachable through an account-scoped `Membership` **or** an account-scoped `Renter`.
With no `app.account_id`, both witnesses fail and reads return no person rows. The policy grants no
insert, update or delete access to the global identity row.

The policy deliberately does not filter revoked memberships. A revoked colleague must remain
readable for historical attribution; permission to act is a separate current-membership check. The
policy's `EXISTS` queries are themselves evaluated through the RLS policies on `membership` and
`renter`, so narrowing either policy later can also narrow person visibility and must be reviewed as
one change.

### The `person` edge splits: READ is a policy (M5a), WRITE is an ordering rule (M10)

The two shipped foreign keys to the global identity table have different meanings:

| Edge | Required mechanism |
| --- | --- |
| `membership.person_id → person.id` | Account-scoped `Membership` is a read witness under migration `0005`; staff writes are not granted through the person RLS policy. |
| `renter.person_id → person.id` | Account-scoped `Renter` is a read witness; the future write is authorized by activation-code redemption, not by a composite constraint or pre-existing membership. |

The write invariant cannot be “the person already belongs to this account.” A legitimate renter may
have no earlier relationship to the landlord's account, and may simultaneously own another account.
`Membership` would reject that valid case; the new `Renter` row cannot witness itself before it
exists. The actual invariant is consent: the nullable link starts empty and exactly one future M10
flow may fill it after redeeming a tenancy-bound, per-person, single-use activation code.

`app_bootstrap_contexts(text)` and migration `0006_bootstrap_contexts_read.py` are **prepared but
unmerged** on `slice/m5-bootstrap-contexts`. They are not part of `main`. The prepared design uses one
bounded `SECURITY DEFINER` function, a dedicated `NOLOGIN`/`NOBYPASSRLS` owner with read access only
to `person`, `membership` and `account`, and one checked API call site. It does not create a renter
portal or account switcher.

`renter.person_id` is nullable and has no default. Current create APIs leave it `NULL`; no current
API route is authorized to write it. M5 owns a negative OpenAPI guard proving that absence. M10 owns
the only positive writer: redemption of a tenancy-bound, per-person, single-use activation code.
The link proves consent and intended identity, not shared account membership. M10 also owns renter
URL authorization and the decision whether the link becomes immutable after activation.

## 3. Account isolation and composite-FK rules

### Isolation rule

Every foreign key between two account-scoped tables is composite:

```text
FOREIGN KEY (parent_id, account_id)
REFERENCES parent (id, account_id)
```

The parent exposes `UNIQUE (id, account_id)`. Nullable links use Postgres `MATCH SIMPLE`, so an
optional `parent_id = NULL` stays legal while `account_id` remains non-null.

This is structural enforcement in addition to application scoping and RLS. Postgres checks foreign
keys outside row-policy visibility; a bare `parent_id` foreign key could therefore let a row in
account B point to a parent in account A even when the new row itself passes RLS.

Migration `0004`,
[`0004_composite_account_scoped_fks.py`](../packages/db/alembic/versions/0004_composite_account_scoped_fks.py),
is **shipped**:

- `building_assignment.account_id` exists, is non-null and is constrained against both its
  membership and building;
- all **22** tenant-to-tenant foreign keys carry `account_id`;
- all scoped parents expose the matching pair;
- [`scripts/check_fk_isolation.py`](../scripts/check_fk_isolation.py) guards future edges and is
  green on the migrated database.

The complete shipped tenant-to-tenant edge set is:

| # | Child → parent | Child reference | Constraint detail |
| ---: | --- | --- | --- |
| 1 | `building` → `landlord` | `(landlord_id, account_id)` | `landlord_id` nullable |
| 2 | `unit` → `building` | `(building_id, account_id)` | required |
| 3 | `tenancy` → `unit` | `(unit_id, account_id)` | required |
| 4 | `tenancy_party` → `tenancy` | `(tenancy_id, account_id)` | required |
| 5 | `tenancy_party` → `renter` | `(renter_id, account_id)` | required |
| 6 | `self_use_period` → `unit` | `(unit_id, account_id)` | required |
| 7 | `statement` → `building` | `(building_id, account_id)` | required |
| 8 | `cost_entry` → `building` | `(building_id, account_id)` | required |
| 9 | `allocation_key_assignment` → `cost_entry` | `(cost_entry_id, account_id)` | required |
| 10 | `allocation_key_assignment` → `unit` | `(direct_unit_id, account_id)` | direct target nullable |
| 11 | `allocation_key_assignment` → `tenancy` | `(direct_tenancy_id, account_id)` | direct target nullable |
| 12 | `meter` → `building` | `(building_id, account_id)` | required |
| 13 | `meter` → `unit` | `(unit_id, account_id)` | building-level meter when null |
| 14 | `meter_reading` → `meter` | `(meter_id, account_id)` | required |
| 15 | `heating_cost_entry` → `building` | `(building_id, account_id)` | required |
| 16 | `building_assignment` → `membership` | `(membership_id, account_id)` | required; delete cascades |
| 17 | `building_assignment` → `building` | `(building_id, account_id)` | required |
| 18 | `meter_reading` → `tenancy` | `(tenancy_id, account_id)` | optional Page 01b segment target |
| 19 | `person_count` → `tenancy` | `(tenancy_id, account_id)` | required |
| 20 | `mdl_statement` → `building` | `(building_id, account_id)` | required |
| 21 | `mdl_statement_position` → `mdl_statement` | `(mdl_statement_id, account_id)` | required |
| 22 | `mdl_statement_position` → `tenancy` | `(tenancy_id, account_id)` | required |

`building_assignment.account_id` is intentional denormalization. Deriving scope only through
`membership` cannot prove that the assigned building belongs to the same account. The two composite
constraints prove that the copied account matches both parents, so it cannot drift. Its RLS policy
can consequently use the same local-column predicate as every other account-scoped table.

#### Consequence for the gates

The isolation guarantee is not maintained by a hand-written test per edge. The schema checker
discovers every foreign key between tables in `ACCOUNT_SCOPED_TABLES` and fails any edge that is not
composite. Database tests then prove representative required, nullable and assignment shapes reject
cross-account parents. A green test count without the discovery gate would not cover a newly added
edge.

Foreign keys to `account.id` and the two edges to global `person.id` are outside this composite rule.
The account edge terminates at the isolation boundary and therefore cannot be composite. `Person`
must remain global because one Supabase Auth identity can participate in many accounts. Giving it an
`account_id` would either duplicate the human or incorrectly choose one account as owner. Migration
`0005` protects reads with a relationship policy, and the M5/M10 ordering protects the future
renter-link write. The composite-FK gate is silent about these global edges by design, not because
they are safe without a separate mechanism. A new edge to any global table must name its own read
and write mechanisms before it is accepted.

The global uniqueness of `person.email` remains an accepted enumeration limit: a unique-constraint
failure can reveal that an address exists even when the row is not visible through RLS.

## 4. Temporal property model, self-use, allocation keys, and meters

### Temporal core

The shipped property graph is:

```text
Building 1 ── N Unit 1 ── N Tenancy N ── N Renter
                                  via TenancyParty
```

| Entity | Temporal or structural rule | Status |
| --- | --- | --- |
| `Building` | Belongs to one account; optional legal `Landlord`. | **Shipped** |
| `Unit` | Belongs to one building; area is `area_sqm_x100`. | **Shipped** |
| `Tenancy` | Dated lease; several renters attach through `TenancyParty`. | **Shipped** |
| `TenancyParty` | Account-scoped tenancy-to-renter join; supports multi-party leases. | **Shipped** |
| `SelfUsePeriod` | Dated area (`sqm_x100`) and kind; never represented by a renter. | **Shipped** |
| `PersonCount` | Dated Personenzahl per tenancy; half-open validity, never a scalar on the unit. Vacancy is deliberately absent — D0 is derived per run. | **Shipped** |
| `MdlStatement` | A confirmed third-party Messdienstleister statement, append-only and versioned per building period. | **Shipped** |
| `MdlStatementPosition` | One renter's amount on that statement, stored as delivered and never recomputed. | **Shipped** |
| `AdvancePaymentPeriod` | Dated contractual advance amount replacing the tenancy scalar. | **Future**, M6 |

Shipped validity and cost ranges use half-open dates: `valid_from` or `period_from` is included and
`valid_to` or `period_to` is excluded. Page 01's user-facing billing period is inclusive; adapters
must convert that boundary explicitly instead of mixing the two conventions.

| Shipped entity | Key fields | Constraints and meaning |
| --- | --- | --- |
| `Building` | account, optional landlord, name and address, `fiktivbelegung_mode`, nullable `fiktivbelegung_waiver_note` | Composite optional landlord edge; account-scoped root for property calculations. The mode defaults to `LETZTE_BELEGUNG` (spelling note below) and `CheckConstraint ck_building_fiktivbelegung_waiver_logged` refuses `KEINE` unless a waiver note is present. |
| `Unit` | building, label, `area_sqm_x100` | Integer area; composite building edge. |
| `Tenancy` | unit, `valid_from`, nullable `valid_to`, base rent, `advance_payment_cents` | One lease identity over time; composite unit edge. Overlap refusal is a domain invariant. |
| `TenancyParty` | tenancy, renter | Unique `(tenancy_id, renter_id)` join permits several renters on one lease without duplicating the tenancy. |
| `SelfUsePeriod` | unit, `sqm_x100`, kind, note, validity | Partial-area self-use over time; composite unit edge. |
| `PersonCount` | tenancy, `count`, `valid_from`, nullable `valid_to` | Half-open Personenzahl history; composite tenancy edge. `CheckConstraint ck_person_count_non_negative` allows `0` (an empty but running lease) and rejects negatives. |
| `MdlStatement` | building, `branch`, `period_from`, exclusive `period_to`, `confirmed_total_cents`, `owner_position_cents`, nullable `co2_kg_x1000` / `co2_cost_cents` / `heated_area_sqm_x100`, `co2_evidence_present`, `source_ref`, `version`, `confirmed_at` | Composite building edge. Unique `(building_id, period_from, period_to, version)`; a correction inserts `version + 1` and the earlier row stays, so nothing UPDATEs a confirmed row. `source_ref` is required: a passed-through figure whose origin nobody can name is not evidence. |
| `MdlStatementPosition` | `mdl_statement_id`, `tenancy_id`, `amount_cents` | Composite statement and tenancy edges; unique `(mdl_statement_id, tenancy_id)`; amount non-negative. Stored as delivered — `docs/03` H7 validates and passes through, never recomputes. |

### Eigennutzung (self-use) is NOT a Renter

Only explicit self-use is stored. Rental state derives from tenancies and vacancy is the uncovered
area-time remainder, so three mutable state flags can never drift apart.

| State | Source | Operating-cost treatment | Tax treatment |
| --- | --- | --- | --- |
| `RENTED` | Active `Tenancy` | Allocated to its renter tenancy. | Rental income and applicable deductible costs. |
| `SELF_USED` | Explicit `SelfUsePeriod` area | Falls to the owner residual. | Private use reduces deductible AfA, not the AfA basis. |
| `VACANT` | Neither rented nor self-used | Falls to the owner residual while staying in applicable denominators. | Costs may remain deductible while rental intent is evidenced. |

A unit-area day must not be both rented and self-used; overlapping tenancies in the same unit also
block. Partial self-use is an area, not a boolean. Below-market family letting remains a real
tenancy and is flagged for tax review rather than converted into self-use. Mid-year change between
self-use and rental is specified by `docs/10-afa.md` as an unresolved production choice: the Page
preserves both month-accurate and day-accurate results and blocks production until one is approved.

### DEFECT: `Tenancy.advance_payment_cents` is a scalar on a temporal row

The shipped scalar records only the monthly contractual Soll at tenancy creation. It cannot express
an adjustment during a continuing lease, although § 560 Abs. 4 BGB permits an advance adjustment
after a statement. Current APIs expose no tenancy update path. Ending the tenancy and opening
another one is not an acceptable workaround: statement parties are keyed by tenancy, so one
continuing renter would appear as two parties even though the consecutive periods do not overlap
and ordinary allocation checks stay green.

The scalar is not an engine input, an actual payment, or a lawful substitute for Page 01's paid
advances. M6 must introduce an account-scoped, composite-FK-protected `AdvancePaymentPeriod` with at
least tenancy, amount, `valid_from` and `valid_to`; define how a dated adjustment and its versions are
recorded; migrate create/read API schemas; and remove the scalar only after backfill. Every existing
tenancy becomes one open-ended period beginning at `tenancy.valid_from` with its current scalar
amount. This is a data migration, not just a model rename.

### Allocation keys

`AllocationKey` and `AllocationKeyAssignment` are **shipped**, not future M3 work. A cost keeps its
entered amount and period in `CostEntry`; changing its key appends an assignment and preserves the
old row. Supported keys are `AREA`, `PERSONS`, `CONSUMPTION`, `UNITS`, `DIRECT` and `MEA`.
`DIRECT` identifies exactly one unit or tenancy and bypasses proportional allocation.

| Record | Shipped fields relevant to allocation | Contract |
| --- | --- | --- |
| `CostEntry` | building, label, `amount_cents`, half-open `period_from`/`period_to`, `created_at` | Entered cost and period are not rewritten when the key changes. |
| `AllocationKeyAssignment` | cost, key, nullable direct unit, nullable direct tenancy, `created_at` | Append-only history; the latest assignment wins. A `DIRECT` assignment selects exactly one target; proportional keys select neither. |

NK allocation works at unit/tenancy granularity. AfA later splits by area; these are deliberately
different granularities. The database supplies composite protection for both optional direct
targets. Application validation owns the mutually exclusive target rule because the current table
has no shipped check constraint for it.

Heating costs remain in `HeatingCostEntry`, never a flagged `CostEntry`. HeizkostenV determines their
split; presenting an ordinary allocation-key selector for them would model a choice the user does
not have.

Page 02 is merged in [`docs/09-betrkv-catalogue.md`](09-betrkv-catalogue.md) with the exact
`09-F01`–`09-F32` data oracle. Merge is **specified**, not production closure or legal approval: no
production catalogue or Page 02 gate is wired, and the missing register rows and unresolved
classifications remain `verify-before-production`. Slice C owns production NK eligibility,
classification, renter half-up allocation and owner-residual integration.

The Page 08 bank-matching contract is **complete, approved and merged** in `docs/15`. That approved
doc and its oracle resolve `BANKMATCH-F03` as E12 and distinguish potential-duplicate Review from
silent same-ID re-import dedupe. The thirteen-case oracle supplies
no current receivable, ledger or bank-matching implementation.

### Meters: `MeterKind` and `MeasurementUnit` are independent axes

`Meter.kind` and `Meter.measurement_unit` are independent. A building heat meter and a unit heat-cost
allocator can share a kind while only the measurement unit determines whether a reading can serve
as a denominator. Conversely, the same unit such as cubic metres can belong to cold- or warm-water
devices, so the unit alone does not identify the device.

| Record | Shipped evidence fields | Invariant |
| --- | --- | --- |
| `Meter` | building, optional unit, kind, measurement unit, serial, label, `calibration_valid_until`, optional exact `valuation_factor_x1000` | `unit_id = NULL` means building-level meter. Serial is unique per building. Every heat meter has a positive factor; migration `0006` backfills the neutral **1.000**. Water factors remain null. Expiry is derived, never stored as a flag. |
| `MeterReading` | meter, `read_at`, `value_x1000`, reason, source, note, optional tenancy, optional `estimated_consumption_x1000` plus basis, provenance reference, `recorded_at` | Point-in-time, fixed-point and create-only. Unit and kind come from the referenced meter. Estimates require their basis; tenancy uses an account-scoped composite FK. |
| `HeatingCostEntry` | building, label, amount, period, optional CO₂ mass and cost | Separate invoice input; it never exposes an ordinary allocation key. |

Readings are create-only by shipped API shape and model design: there is no replacement pointer or
update timestamp and no PUT/PATCH route. A wrong value is corrected by inserting a new reading for
the same `read_at` with reason `CORRECTION`; later `recorded_at` evidence wins while the original
remains visible, including as struck-through history where the UI shows it. Adapter and manual
sources normalize into the same downstream shape. Effective corrections, tenant-change segments,
estimates, device replacements and provenance survive the adapter boundary and feed the shared
Page 01b result. A meter's calibration deadline feeds the shared
guard system; null means not applicable for a device such as a heat-cost allocator, not “unknown.”

## 5. Owner residual and Page 01 statement model

### The Eigentümeranteil is a residual line, not a party

This model is fixed by original Page 01 D0/D12 and edge cases E3, E17 and E19, and preserved in
approved `docs/03` § 9.2. It is a model rule, not a Lokara convention. The fictional person count
that can feed a vacancy denominator retains its own `verify-before-production` flag; that does not
make the residual destination optional.

For every property and cost type:

```text
renter share i = round_half_up(total cost × renter weight i / full denominator)
owner residual = total cost − sum(renter shares)
```

- It is one structural reconciliation line, not a landlord party, occupancy share, separately
  weighted amount or stored mutable total.
- It always exists, including `0.00 EUR` in a fully let building, and may be negative when half-up
  renter rounding exceeds the pot by cents.
- `sum(renter shares) + owner residual = total cost` holds by construction per cost type and in
  total.
- It carries no quote, percentage or `Bemessung`; the type must not offer such fields.

The residual does not remove vacancy from allocation. The full denominator still contains each
applicable owner-side basis:

| Allocation basis | Vacancy/self-use treatment |
| --- | --- |
| Area | Vacant/self-used area-days remain in the total area-days. |
| Units | Vacant/self-used unit-days remain in the total unit-days. |
| Persons | The approved fictional-person occupancy is added before forming person-days. |
| Consumption | No invented consumption is added. A vacant unit with no consumption can contribute `0.00 EUR` to this cost type. |
| Zero denominator | Every renter share is zero; the complete amount remains in the owner residual with the required “no consumption values recorded” warning. The cost is not silently re-keyed. |

#### D0 Fiktivbelegung — the vacancy person count is derived, and it is a flagged convention

Source: original Page 01 § 3.5, § 4 D0 and edge cases E17/E18/E19, plus the register row
`Fiktivbelegung bei Leerstand`. **Rechtsstand 07/2026**, `Rechtsnatur: Konvention`, status
`verify-before-production`. It is a Lokara convention over split instance case law, not settled law,
and no output may present it as settled law.

| Item | Rule |
| --- | --- |
| Inputs | each vacancy period of a unit (derived — the days no tenancy covers, never stored), the unit's last known person count, and the building's Fiktivbelegung mode. |
| Modes | `letzteBelegung` (default), `immer1`, `keine`. |
| Count | `letzteBelegung` → `max(1, last known person count of that unit)`; `immer1` → `1`; `keine` → `0`, permitted only with a logged confirmation after the E18 hard warning naming the case law. |
| Formula | `fictional person-days = count × vacancy days`, day-exact, added to the person-day denominator **before** any share is formed. |
| Destination | the owner residual. The fictional occupancy is a denominator weight only: never a party line, never a `Renter`, never a `SelfUsePeriod`. |
| Other bases | Area, Units and Consumption are untouched by D0 — see the table above. |
| Legal basis | BGH VIII ZR 159/05 (the vacant unit stays in the Gesamtverteiler); LG Krefeld 2 S 56/09 (fictional occupancy under the person key). BGH VIII ZR 180/12 expressly treats the Ansatz as a Tatfrage of the individual case and does **not** settle it. Literature splits between “1 Person” (Schmidt-Futterer § 556a Rn. 76) and the unit's average occupancy (AG Köln WuM 2002, 28; Sternel NZM 2006, 811). |
| Edge cases | an unknown or zero last count yields `1`, so the derived branch can never collapse to the `keine` denominator; a unit vacant for the whole period has no in-period history, so its last count comes from **before** the billing period; `keine` makes the renters carry the whole person-keyed fixed cost, which is the constellation the cited decisions reject. |

Fixtures: `08-F21` (31 vacancy days × 2 persons = 62 person-days), `08-F22` (`2.006` → `2.068`
person-days) and `08-F23` (`730` of `2.190` person-days).

**One rule, two spellings — the mapping is fixed here so they cannot drift.** The source and the
prose above use the Page 01 names; the shipped `FiktivbelegungMode` enum in
[`models.py`](../packages/db/src/lokara_db/models.py) uses the repository's UPPER convention. Neither
spelling is changed — this table is the only permitted translation between them:

| Page 01 / register / prose | Database enum member and stored value |
| --- | --- |
| `letzteBelegung` (default) | `LETZTE_BELEGUNG` |
| `immer1` | `IMMER_1` |
| `keine` | `KEINE` |

The mode sits on `Building` (Page 01 § 3.5 `objekt.fiktivbelegungModus`), not on a unit or a run,
because one object bills one way. `KEINE` requires `Building.fiktivbelegung_waiver_note`, enforced by
`CheckConstraint ck_building_fiktivbelegung_waiver_logged` — the E18 log is a precondition of the
mode, not a step a caller can skip.

**Decided in Slice B — the adapter derives, the engine receives.** The layer was left open when the
rule was transcribed. It is now settled as shape 1 of the two that were recorded:

1. **Adapter derives, engine receives** — chosen. `PersonCountPeriod.tenancy_id` is `str | None`
   and carries an optional `unit_id`, exactly as `ConsumptionValue` already attributes a value to
   the landlord. The engine weights the supplied count by days and puts it on the landlord side;
   the mode, the `max(1, …)` minimum and the `keine` confirmation live in the composition layer
   that can read history.
2. **Engine derives** — rejected. It would put the mode and the unit's last known count into
   `NkInput`, which makes a *required* history input out of something the engine cannot obtain: a
   unit vacant for a whole period needs a count from **before** the billing period. That is a
   persistence dependency inside a package whose purity rule exists to forbid exactly that.

Why it was not a free choice: the count is derived from a person-count history, and the engine is
framework- and history-free by contract (`CLAUDE.md` § 3.1). Shape 2 would have had the pure
package depend on a lookup it cannot perform. Shape 1 keeps one versioned `Rechtsstand` on the
convention by keeping the whole convention — mode, minimum, waiver — in one composition module
rather than splitting it across the boundary.

What this does **not** relax: the count is still derived, never a magic number a caller invents,
and no fixture may hand the engine a bare fictional count as one. Fixtures pin the outcome — the
composition of the person-day denominator and the fact that the fictional weight lands on the
landlord side — and only the one helper that builds the landlord row names an input field.

Persistence: `person_count` rows are per tenancy. The D0 landlord rows are **derived per run and
never stored**, which is what "the adapter derives" means. A unit vacant for the whole period still
resolves, because the tenancy that ended before the period keeps its `person_count` rows.

##### Assumption, not a transcribed rule: self-use overlapping a vacancy

`SelfUsePeriod` stores an **area** (`sqm_x100`), not unit-level occupancy, so a self-use row can
cover part of a unit. Original Page 01 § 3.5, § 4 D0 and edge cases E17–E19 contain **no rule** for
a partial self-use overlapping a vacancy, and the register has no row for it. What ships is
therefore a **Lokara assumption**, `Rechtsnatur: Annahme`, status `verify-before-production`,
awaiting source confirmation. It has no legal source of its own: it inherits the surrounding D0
convention's **Rechtsstand 07/2026** and was recorded in 08/2026. It is not settled law, it is not
a transcribed source rule, and no output may present it as either.

Source trace: derived from `docs/02` § 4, which defines `VACANT` as "neither rented nor self-used",
read together with original Page 01 § 4 D0, which runs "for each Leerstandsperiode". Shipped in
`apps/api/src/lokara_api/person_counts.py`. Raised as an open source question in
`FRAGEN-an-Berkay-04.md` → "Seite 01 — Fiktivbelegung und Eigennutzung".

| Constellation | Shipped behavior | Why this direction |
| --- | --- | --- |
| **Full-unit** self-use (`sqm_x100 >= unit.area_sqm_x100`) | Those days are removed from the derived D0 vacancy: a self-used day is not a vacancy day and receives no fictional occupancy. | Follows directly from the two cited definitions; unambiguous, and the only inference in it is that the areas are comparable. |
| **Partial** self-use (`sqm_x100 < unit.area_sqm_x100`) | The day stays a vacancy day, so the fiction still applies to it, and the document carries a German finding saying the partial self-use was not separated out. | The conservative direction, deliberately chosen: dropping the fiction would hand the renters the whole person-keyed fixed cost, which is the constellation BGH VIII ZR 159/05 and LG Krefeld 2 S 56/09 reject. Apportioning it would invent an area-weighted person count that no source defines. |

The finding is landlord-facing copy and stays in German. Fixed parts verbatim, interpolated parts in
angle brackets:

```text
<Einheit>: Teil-Eigennutzung (<Fläche> m² von <Gesamtfläche> m²) vom <TT.MM.JJJJ> bis <TT.MM.JJJJ>. Leerstandstage in diesem Zeitraum werden mit Fiktivbelegung gerechnet; die anteilige Eigennutzung ist nicht abgegrenzt.
```

An open-ended self-use row (`valid_to IS NULL`) is clipped to the billing window rather than treated
as infinite. That part is the ordinary half-open temporal rule of § 4, not an assumption.

What a confirmed source rule would have to settle: whether a partial self-use suppresses the fiction
pro rata, suppresses it entirely, or leaves it untouched as shipped. Until then the assumption
stands and the finding is the disclosure that it was applied.

The landlord overview displays one aggregate owner line, but the immutable data retains why it
exists:

| Residual block | Meaning | Required granularity |
| --- | --- | --- |
| (a) vacancy share | Potential § 9 EStG/Anlage V evidence | Each vacant unit and cost type, separately half-up rounded for the annex. |
| (b) non-allocable cost | Owner-side operating cost with separate tax classification | Each cost position; Page 02 supplies classification. |
| (c) rounding difference | Reconciliation only, no economic unit | No unit: printed residual minus the sum of separately rounded origin amounts. |

The displayed residual always wins if the aggregate and separately rounded origins differ. Origin
rows keep unit, dates, cost type, applicable bases and their separately calculated amounts for the
landlord-only vacancy schedule. They are not party lines and never appear in a tenant projection.

The primitive
[`distribute_cents_owner_residual`](../packages/domain/src/lokara_domain/money.py) and the
[`OwnerResidual` result shape](../packages/heating-engine/src/lokara_heating_engine/inputs.py) are
**shipped** for heating. The result has one aggregate residual, origin rows and a rounding-difference
field; no owner percentage exists.

#### This is cross-engine and binding

Heating already calculates every renter block with half-up rounding and commits the remainder to one
property residual. NK still uses its shipped largest-remainder path until Slice C implements the
reviewed Page 02 contract. The residual rule and renter-side half-up rounding must move together:
largest remainder allocates the entire pot across its weight list, which would either treat the
owner as a separately weighted party or force a zero residual. Both contradict the normalized model.
For heating, the same one owner result reconciles all four displayed blocks and the combined
party-total row; it is not recreated independently for each table.

The Rechtsstand Register row `Verteilungsrest (K9)` still describes the destination as a house
convention. Berkay's later Page 01/answers fix the destination as this residual model. The source
register wording remains unresolved and must be corrected only in an authoritative register export;
this repository does not rewrite `berkay-work/`.

### Page 01 statement model

Page 01 is **specified**: its full D1 source trace and exact `08-F01`–`08-F24` data oracle are
transcribed and approved in [`docs/08-statement-document.md`](08-statement-document.md) and this
file. Approval closes the specification, not production implementation.

One normalized calculation must produce one immutable result and explicit audience projections:

1. Select one account, building and inclusive billing period. A period longer than 12 months blocks
   before calculation or rendering; leap years retain their actual days.
2. Carry property facts, clipped tenancies, cost and heating results, meter evidence, vacancy
   origins, warnings/provenance, rule versions and every applicable `Rechtsstand`.
3. Compute renter lines and the unconditional owner residual once.
4. Project that result to `OWNER`, `TENANT(tenancy_id)` or `TAX` before rendering. A missing or
   foreign tenancy fails; it never falls back to an owner view.

| Required normalized shape | Contract and implementation boundary |
| --- | --- |
| Calculation identity | Account, building, inclusive period and calculation/version identity. Basic persisted fields exist; the exact Page 01 input is not complete. |
| Property header | Legal landlord, object address, total area, unit count, creation date, engine/rule versions and every applicable register `Rechtsstand`. |
| Covered tenancy | `tenancy_id`, renters/addressee, delivery address, unit, clipped usage dates and days, person/area/consumption inputs. Temporal tenancy exists; delivery and isolated projection remain incomplete. |
| Actual advances | Paid cents for the period, distinct from contractual Soll. **Future M6 ledger work**; never nullable when a tenant document is finalized, while confirmed zero is valid. |
| Operating-cost result | Cost identity/classification, total, key, numerator, denominator, measurement unit, rounded renter share, § 35a inputs/result, warnings and provenance. |
| Heating and CO₂ result | Every required block, ratio, numerator/denominator, device evidence, CO₂ figures, warnings and provenance defined in `docs/03`. |
| Vacancy result | Origin unit/dates, fictional occupancy basis, residual block (a), non-allocable block (b), rounding block (c) and evidence. The residual contract is settled; the full annex is not implemented. |
| Projection and archive | Audience plus exactly one tenancy for tenant output, document bytes/storage keys and hashes. **Future M6 work**. |

Finalization must enforce all of these together:

- a covered tenancy with zero clipped usage days creates no tenant document or portal item, creates
  no owner vacancy segment, and is explained in the landlord overview;
- overlapping tenancies in one unit block before calculation or rendering;
- a mid-period renter change produces separate, isolated projections with no names, amounts or
  documents crossing between tenancies;
- confirmed actual advances, including an explicit zero, are present before a tenant document can
  finalize; missing is not treated as zero;
- the owner residual is recomputed from the result and never accepted as a second mutable input;
- a tenant projection requires one existing, account- and building-valid `tenancy_id`; a missing or
  foreign id fails instead of falling back to the owner projection;
- corrections append a new finalized version and keep every input and archived byte needed to
  reproduce the older version.

Page 01 block (b) for `08-F21` is `100800` cents. Page 02 owns its BetrKV classification and the
future tax specification owns its Anlage-V mapping.

## 6. Immutable finalization, financial time axes, and M6 ledger handoff

The shipped `Statement` row is an incomplete lifecycle anchor:

| Shipped field or constraint | Meaning and limit |
| --- | --- |
| `account_id`, `building_id` | Account-scoped statement and composite building edge. |
| `period_start`, `period_end` | Stored statement period. The complete normalized snapshot is absent. |
| `version`, `status` | Version defaults to 1; status is `DRAFT`, `FINALIZED` or `SUPERSEDED`. |
| `total_cents`, optional `content_hash`, `created_at` | Basic output total and document hash slot, not all calculation/document evidence. |
| Unique `(building_id, period_start, period_end, version)` | Prevents duplicate versions for one building period. It does not by itself enforce append-only finalization. |

```text
live inputs ── preview (no archive)
     │
     └── finalize v1: DRAFT → FINALIZED
                           │ correction
                           ├── v1 → SUPERSEDED (retained)
                           └── insert v2: DRAFT → FINALIZED
```

The current enum and uniqueness constraint are **shipped**; the complete immutable transition,
snapshot and document archive are **future M6**. Preview and finalization have different contracts:

- A preview reads current normalized rows, calculates and renders live. It creates no archive.
- Finalization creates one immutable, reproducible snapshot for account, building, period and
  version, including normalized inputs, outputs, engine/rule versions, `Rechtsstand`, timestamps,
  hashes and archived documents or immutable storage keys.
- One result yields one internal landlord overview and one independently rendered document for each
  eligible tenancy. Lokara never creates one all-renters PDF and later crops or masks it.
- A correction appends `vN+1`, retains `vN` and records supersession. Referenced input rows and
  archived bytes cannot be destructively changed or deleted.

### Financial time axes

| Axis | Event and date | Output |
| --- | --- | --- |
| Operating-cost billing | Cost/occupancy overlap with the billing period; day-weighted. | Renter share, owner residual and statement Saldo. |
| Contractual advance Soll | Effective period of each `AdvancePaymentPeriod`. | What the renter was required to pay; arrears comparison only. |
| Actual advances | Accepted payment allocations whose payment dates and purpose fall into the relevant reconciliation. | What Page 01 deducts from the renter's share. |
| Tax cash basis | Date money actually moved under § 11 EStG, including the separate 10-day rule around New Year. | Tax ledger, Anlage-V mapping and exports. |

These axes meet through explicit references; one amount never substitutes for another.

### Payment Ledger

M6 owns the handoff in this order:

1. Finalize Page 01 using actual paid advances and calculate the tenant Saldo.
2. A positive finalized Saldo creates an account-scoped **receivable**. It does not itself create a
   payment or tax cash event. A negative Saldo is the corresponding tenant credit/refund obligation.
3. An imported or manual money movement, once matched and accepted, creates append-only ledger
   entries with payment date, amount, direction, account/property/party dimensions, category state,
   source, receipt reference and version history. Missing payment date is a tax-export hard block;
   an uncategorized movement remains representable but produces a yellow readiness finding.
4. The ledger, not the statement or receivable, feeds tax and deterministic exports through a
   year-versioned `TaxCategoryMapping`.

| Future record | Minimum contract and owner |
| --- | --- |
| `AdvancePaymentPeriod` | M6: account, tenancy, amount, effective dates and version/declaration evidence. |
| `Receivable` | M6: account, finalized statement/version, tenancy, amount, due state and immutable origin. |
| Payment event/ledger entry | M6: payment date state, integer cents, direction, account, landlord/building/unit/renter dimensions as applicable, category state, source (`finAPI`, manual or invoice), receipt reference and version history. Missing date is red; missing category is yellow before tax export. |
| Matching evidence | M6: normalized transaction, accepted allocation/proposal, versioned IBAN-to-renter link, duplicate/reversal history and reviewer decision where required. |
| `TaxCategoryMapping` | M7: tax-year category to Anlage-V line plus SKR03/SKR04, validity/source version and tax-adviser override provenance. All current lines/accounts remain blocked placeholders. |
| Tax-adviser profile | M7: adviser/client number, chart, account length and fiscal-year start; write access is limited to these adviser-owned export parameters. |
| Readiness result | M7: immutable ordered red/yellow findings, acknowledgements, input/mapping/profile versions and blocked/generated outcome. |
| Export archive | M7: deterministic input references, output bytes, version, `Rechtsstand`, timestamp and hash. Re-export appends a version. Working DATEV EXTF encoding is Windows-1252 with semicolons and CRLF, still blocked pending official-format and real-import verification. |

The statement's Saldo is BGH formal minimum #4. It must use **geleistete** advances from accepted
payment allocations, not `advance_payment_cents × months`. The temporal Soll schedule is still
needed to identify arrears and explain what was due, but it does not prove what was paid.

This separation fixes the former ambiguous phrase “statements feed the ledger”: a statement creates
an obligation; an actual payment creates the cash-basis ledger event. M6 owns bank matching,
versioned IBAN-to-renter mappings and the temporal Soll schedule needed to compare what was owed
with what moved. M7 consumes the accepted ledger snapshot and owns the separate tax-export archive;
approved `docs/11` adds no schema or API.

## 7. Known gaps and milestone ownership

| Gap or boundary | Status | Owner |
| --- | --- | --- |
| Secure pre-context identity read (`app_bootstrap_contexts`, migration `0006`) | **Prepared but unmerged** on `slice/m5-bootstrap-contexts` | M5, after documentation and Slices A–C |
| Role behavior, switcher, assigned-building enforcement, nested-route authorization and the no-`renter.person_id`-writer guard | **Future** | M5 remainder |
| Page 01 persisted calculation/extraction reconciliation | **Specified and approved**; production gaps remain | Slice B |
| Page 02 production catalogue, classifications, NK half-up rounding and owner residual | Merged specification; production missing and flags remain | Slice C |
| Page 08 bank-matching specification | **Approved and merged** in `docs/15`; F03 resolved with all thirteen oracle cases executable | D2 / `docs/15` |
| Temporal advances, actual advances, receivables, ledger, Saldo and immutable separated finalization | **Future** | M6 |
| Renter activation-code redemption, renter context and portal isolation | **Future** | M10 |
| Mid-year self-use/rental change for AfA apportionment | Specified with unresolved month/day authority choice; no implementation | `docs/10-afa.md` / M7 |
| Page 04 Anlage-V/DATEV export contract | Complete transcription approved and merged 21.08.2026; no production implementation | D2 / `docs/11-tax-export.md` |
| Page 06 clause selection, risk and workflow-routing contract | Complete transcription approved and merged 21.08.2026; no schema, clause bodies, letter bodies or production implementation, and the missing text catalogues still block M8 | `docs/13-contract-clauses.md` / M8 |
| `Verteilungsrest (K9)` authoritative register wording | Unresolved source issue; repository copy remains untouched | Next authoritative register export |

Other later temporal or immutable records arrive only with their owning milestones: `AfaRecord`,
`Loan`, shared guard/reminder records, `LettingEffort`, tickets, export archives, subprocessors,
activation codes, IBAN history, delivery logs, clause/contract versions and prospect objects.
`docs/13` defines only their future logical references, composition evidence and risk routing; it
does not approve a schema or provide clause text. `docs/14` likewise defines only the future
Prüfobjekt snapshot, provenance, partial-result, annuity, sensitivity and Bank-PDF boundaries; it
approves no prospect schema. Their names in this inventory do not approve their final schemas.
