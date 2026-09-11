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
         ├──< HeatingBillingModeVersion
         ├──< MdlStatement ──< MdlStatementPosition >── Tenancy
         └──< Statement
Tenancy ──< PersonCount
Meter ──< MeterLifecycleEvent
      ├──< MeterReading
      └──< MonthlyMeterReading ──< MonthlyMeterReadingSource >── MeterReading
Building ──< BuildingUviConfiguration
         ├──< UviBuildingMonthlyEvidence ──< UviBuildingMonthlyEvidenceSource
UviStationAssignment ──< UviMonthlyDegreeDay
Tenancy ──< UviRun >── Unit
             └──< UviDeliveryEvent
```

The outer `Person` links are deliberate global-table exceptions. Every edge between
account-scoped tables carries the same `account_id`; section 3 records the enforced pattern.

| Model area | Current shape | Status |
| --- | --- | --- |
| Identity and access | `Person`, `Account`, `Membership`, `BuildingAssignment`, `Landlord`, `Renter` | **Shipped** |
| Property and occupancy | `Building` (with `fiktivbelegung_mode` and `fiktivbelegung_waiver_note`), `Unit`, `Tenancy`, `TenancyParty`, `SelfUsePeriod`, `PersonCount` | **Shipped** |
| Operating-cost inputs | `CostEntry`, `AllocationKeyAssignment` | **Shipped** |
| Metering and heating inputs | `Meter`, `MeterLifecycleEvent`, `MeterReading`, `HeatingCostEntry`, `HeatingBillingModeVersion` | Base model **shipped**; UI-08 extensions are **implemented, partially verified** on `development`, including the `0040` invariant repair and clean boundary re-audit |
| Monthly UVI evidence, weather, configuration and archive | U4/U4b records in migrations `0022`/`0023`; U5 composes them into immutable `UviRun` inputs/results and a `GENERATED` event | **Technically implemented** for owner-side generation and document download; no scheduling, email or renter publication |
| Confirmed third-party heating statement | `MdlStatement`, `MdlStatementPosition` — validated and passed through, never recomputed (`docs/03` H7) | **Shipped** |
| Statement row | `Statement` with period, version, status, total, finalized snapshot and predecessor relation | **Shipped** for M6-B owner-only technical archives; live preview stays separate |
| Page 01 normalized result and audience projections | One calculation result projected to owner, one tenancy or tax | **Shipped** for owner-only M6-B archives; no renter portal/delivery |
| Temporal advance schedule, confirmed advances, settlements and immutable finalization | M6-A/M6-B handoff described below | **Shipped** technical archive scope; ledger/matching persistence and C3a are technically complete, development-synchronized and locally merged; C3b's job wiring is technically complete and locally merged |
| Guards, reminders, delivery and checklists | W1–W8 evaluations plus immutable reminders/resolutions, versioned schedules, exact-byte artifacts, email/status/suppression evidence and checklist events | **Technically closed 29.08.2026** on `development` in M9 migration `0025`; production blockers remain; later checkpoint verification is separate |
| AfA versions, normalized tax events, adviser/mapping versions, readiness attempts and export archive/artifacts | Seven account-scoped records in migration `0024`; exact behavior is approved in `docs/10`/`docs/11` | **Integrated on `development`** with deferred M7-F repairs; closure reviews and runtime authority remain blocked |
| Renter activation and renter portal context | Activation-code redemption writes `renter.person_id`; `/renter/{tenancyId}` uses a separate renter context | **Specified** by M10-R0; no schema, API or UI implementation yet |

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
| `TAX_ADVISOR` | M7 role: read-only tax/AfA/export access plus writes only to adviser-profile and year-mapping versions. It has no tax-event, AfA-record, readiness or generation write. Shipped on `main`, enforced by `authorize_tax_action` on every request. |
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
exists. The actual invariant is consent: the nullable link starts empty and exactly one M10
activation flow may fill it after redeeming a tenancy-bound, per-person activation code. One code
targets one `Renter` party record; it is never shared across the tenancy.

`app_bootstrap_contexts(text)` and migration `0014_bootstrap_contexts_read.py` are **shipped** on
`main`. The design uses one bounded `SECURITY DEFINER` function, a dedicated
`NOLOGIN`/`NOBYPASSRLS` owner with read access only to `person`, `membership` and `account`, and one
checked API call site. M5 also ships the live `/me` contexts, role and nested-route authorization,
and the URL-based account chooser/switcher. It does not create a renter portal. M10 must extend
this same function and its checked privilege boundary to return renter/tenancy witnesses for the
authenticated Person. A second pre-context identity function is forbidden.

`renter.person_id` is nullable and has no default. Current create APIs leave it `NULL`; no current
API route is authorized to write it. M5 owns a negative OpenAPI guard proving that absence. M10 owns
the only positive writer: redemption of a tenancy-bound, per-person, single-use activation code.
The link proves consent and intended identity, not shared account membership. Once non-null, the
link is immutable: it cannot be overwritten or cleared. A genuine correction must append immutable
correction evidence and supersede the earlier link through a separately approved flow; activation
redemption is not a correction route.

The database enforces that ordering for every role, including the table owner and migration role:
a `Renter` may only be inserted with `person_id = NULL`, and the only permitted `NULL → Person`
update is one backed by matching immutable activation-redemption evidence in the same account,
Renter, tenancy and Person context. Application permissions are not the boundary; an owner-role
connection cannot seed or repair a non-null link around the evidence rule.

### M10 renter context — binding design, not yet implemented

The renter URL is `/renter/{tenancyId}/...`. The client never supplies or receives the landlord's
account id as its authority. For every request, the API first proves that the authenticated
`Person` is linked through `renter.person_id` and `tenancy_party` to the exact tenancy named in the
URL. Only then does it derive the account internally and set both transaction-local values:
`app.account_id` for account partitioning and `app.tenancy_id` for the narrower renter boundary.
Neither value is taken from a token claim or trusted request body.

Application authorization and Postgres RLS must each enforce the same relationship. Removing the
application check in a rolled-back test must still leave a renter unable to read another tenancy in
the same account. Owner/staff/tax routes continue to use only their existing account-scoped helper;
`PathAccountSession` is not widened. A person who has both membership and renter contexts sees both
from `/me`, but each destination re-authorizes its own URL independently.

The renter database surface is an allowlist. M10 may add renter `FOR SELECT` policies only for the
rows below; every other account table remains invisible. API responses project only the fields
needed for the stated screen even where a row is RLS-visible.

| Table | Rows visible in one `app.tenancy_id` context | Explicit exclusion |
| --- | --- | --- |
| `tenancy` | Exactly the tenancy named by `app.tenancy_id`, after the Person/Renter/party witness succeeds. | Earlier, later or parallel tenancies in the same unit or account. |
| `unit` | Exactly the unit referenced by the context tenancy. | Other units in the building. |
| `building` | Exactly the building referenced by that unit; the API may project only its display name and postal address. | Other buildings and owner-only building facts or findings. |
| `renter_portal_publication` | Every append-only publication row for the context tenancy, including preserved superseded versions. | Drafts, source artifacts not explicitly published and every other tenancy. |
| `person`, `renter`, `tenancy_party` | No direct renter-context rows; the bounded bootstrap witness already proved the relationship. | Co-renter identity and relationship enumeration. |

Raw source, calculation and evidence rows are not renter-visible. In particular,
`statement_document_archive`, `renter_delivery_artifact`, `statement`, `uvi_run`,
`uvi_delivery_event`, costs, allocation rows, meters/readings, bank/ledger rows, delivery attempts,
guards and owner/tax records receive no renter `SELECT` policy. When `app.tenancy_id` is set, the
existing account-based `person` policy must not make account Persons visible. A renter downloads
only immutable bytes stored on the matching publication row. This prevents the `uvi_run`
input/result JSON, building-wide comparison evidence and the landlord's all-party statement
projection from crossing the portal boundary.

`renter_portal_publication` is a specified M10 record, not shipped schema. It must identify exactly
one account, one tenancy and one source document; copy the already archived bytes, hash, MIME type
and filename without re-rendering; store the publishing owner Membership and publication time; be
append-only; and preserve a correction/supersession chain instead of delete or update. Its source is
either a `TENANT` `COVER_LETTER`/`TENANT_STATEMENT` archive for the same tenancy or a blocker-free
frozen `UVI` delivery artifact for that tenancy. A UVI publication also appends the existing
owner-side `uvi_delivery_event(status = 'PUBLISHED')` in the same transaction, but that event is not
renter-readable. UVI publication remains blocked until M9 has produced the immutable PDF artifact
with an empty production-blocker snapshot.

R1/R3 must implement the publication record's composite foreign keys, forced RLS, `WITH CHECK`
policy and refused cross-account write proof before any portal document route is enabled. Stored
bytes must reproduce the source digest; retrieval verifies the publication digest and never follows
the source row at request time.

### Activation-code contract and refusal fixtures

One activation code belongs to exactly one account-scoped `Renter` and one tenancy in which that
Renter is a `TenancyParty`. It is not a tenancy-wide shared secret. Issuance is owner-only. The raw
code is returned only at issuance and has the wire shape `<account_id>.<secret>`, where
`account_id` is an explicitly non-secret locator and `secret` is at least 256 random bits from a
cryptographically secure generator. Persistence and logs contain only the SHA-256 hash of the
complete raw value; neither the locator nor the secret is stored as a second code field. The record
has a fixed server-generated expiry instant. It is usable only while `now < expires_at` and no
spend evidence exists.

Redemption parses the locator only to open the existing `account_scoped_session`; it is not
authorization and is never accepted as evidence that the URL tenancy, Renter or caller belongs to
that account. The hash lookup then runs behind forced RLS in that one account. A global hash lookup,
a second `SECURITY DEFINER` function and any other pre-context bypass are forbidden. A malformed,
unknown or foreign locator still performs the bounded hash/minimum-duration work and returns the
same public refusal as every other failure; it never receives a format-specific response.

Redemption is one atomic transaction. It locks the code, verifies every binding, writes the
authenticated Person to the still-null `renter.person_id`, and appends spend-once evidence naming
the code, Renter, tenancy, Person and server redemption time. Concurrent or repeated redemption can
produce only one successful link and one spend record. A failed redemption changes neither the
Renter link nor the code evidence. The clock is an explicit service/fixture input; domain logic does
not read a framework or system clock.

Refusals attributable to a real locator account append a separate immutable
`renter_activation_attempt` row after the state-changing redemption transaction refuses. It carries
`id`, `account_id`, optional `activation_code_id`, opaque `requested_tenancy_id`, verified JWT
`subject_id`, `outcome`, `code_digest` and server `attempted_at`. `subject_id` deliberately has no
Person FK because `M10-ACT-F06` records a verified subject that has no Person. The requested tenancy
is non-authoritative text, not an FK: a guessed, foreign or nonexistent URL id must be recordable
without creating a cross-account edge. A present `activation_code_id` uses a composite FK with
`account_id`. The table has forced RLS with `WITH CHECK`, is append-only, and is never renter-visible.

Known/attributable `F01`, `F02`, `F03`, `F05` and `F06` rows retain their exact internal outcome.
`F04` and `F07` with a syntactically valid locator for an existing account append
`ACTIVATION_CODE_UNKNOWN`; they do not cross RLS to discover whether another account owns the hash.
A malformed locator or one naming no existing account cannot safely be attributed to an owner and
therefore creates no account row; only structured operational logging retains that refusal. Neither
durable evidence nor logs contain the submitted raw value. Thus “no row changes” in the refusal
oracle means no Renter/code/spend mutation; the required attempt evidence is an intentional
append-only audit write where attribution is safe.

These identifiers are the complete R1 refusal oracle after Berkay's round-five answer of
11.09.2026. They define internal domain outcomes; the public response below deliberately collapses
them:

| Fixture ID | Refusal condition | Required result |
| --- | --- | --- |
| `M10-ACT-F01` | Spend evidence already exists. | `ACTIVATION_CODE_SPENT`; no row changes. |
| `M10-ACT-F02` | `now >= expires_at`. | `ACTIVATION_CODE_EXPIRED`; no row changes. |
| `M10-ACT-F03` | The requested tenancy differs from the code's tenancy or the Renter is not its party. | `ACTIVATION_TENANCY_MISMATCH`; no row changes. |
| `M10-ACT-F04` | The raw code carries a foreign account locator, or already-loaded synthetic evidence has inconsistent code/Renter/tenancy accounts. | Public live-DB path: uniform refusal and no row changes; forced RLS/composite FKs safely collapse it with an unknown code. Defensive validation of already-loaded inconsistent evidence: `ACTIVATION_ACCOUNT_MISMATCH`. |
| `M10-ACT-F05` | The target `renter.person_id` is already non-null, including when it names the caller. | `RENTER_ALREADY_LINKED`; the existing link remains unchanged and the code is not spent. |
| `M10-ACT-F06` | The verified authentication subject resolves to no `Person`. | `ACTIVATION_PERSON_UNKNOWN`; no row changes. |
| `M10-ACT-F07` | No activation-code row matches the submitted value. | `ACTIVATION_CODE_UNKNOWN`; no row changes. |

Every refusal returns HTTP `400` and the same public body. This includes a missing
`activationCode`, JSON `null`, numbers, lists and objects: request-schema validation must not return
its usual differentiated `422`. The endpoint normalizes every shape into the same minimum-duration
path, does not expose format-specific validation, and does not distinguish a missing row from a row
that fails a later check. Internal owner-visible attempt evidence retains the actual reason,
timestamp and non-secret digest only where a real locator account permits safe attribution; the
remaining refusal is retained only in structured operational logs under the same no-raw-value rule.

The live database cannot contain mismatched code/Renter/tenancy account evidence once the composite
foreign keys are active. It also cannot inspect another account's hash through forced RLS. Therefore
a foreign locator is intentionally logged and returned through the same `ACTIVATION_CODE_UNKNOWN`
live path as an unknown code. `ACTIVATION_ACCOUNT_MISMATCH` remains a defensive service outcome for
synthetic/already-loaded evidence only; implementing it must not add a global lookup or widen the
pre-context boundary.

The public German body (`M10-COPY-03`) is verbatim:

```text
Die Aktivierung war nicht möglich. Bitte prüfen Sie den Code oder wenden Sie sich an Ihre
Vermieterin oder Ihren Vermieter.
```

### Renter-facing copy boundary

The frozen `Mieter-Einzelabrechnung`/cover-letter wording in `docs/08`, the UVI document content in
`docs/16`, the UVI basis labels **„Vergleich im Gebäude“** and
**„normierter Durchschnittsnutzer“**, and the approved disclaimer/Rechtsstand rules remain
unchanged. Portal code displays those archived bytes without rewriting their legal or financial
wording.

Berkay's round-five answer of 11.09.2026 approves `M10-COPY-01…06` as `Konvention`, Rechtsstand
09/2026, `geprüft`. All portal copy uses the **Sie** form, names both
„Vermieterin oder Vermieter“, uses no gender punctuation and avoids Anglicisms. Navigation contains
no money, other-renter names or object data beyond the current unit named in the context entry.

Activation entry (`M10-COPY-01`):

```text
Seitentitel:      Mieterzugang aktivieren
Feldbezeichnung:  Aktivierungscode
Anleitung:        Geben Sie den Aktivierungscode ein, den Sie von Ihrer Vermieterin oder Ihrem
                  Vermieter erhalten haben. Der Code gilt einmalig.
Schaltfläche:     Zugang aktivieren
```

Activation success (`M10-COPY-02`):

```text
Überschrift:      Ihr Zugang ist aktiviert.
Text:             Sie sehen hier künftig Ihre Abrechnungen und Ihre monatlichen
                  Verbrauchsinformationen, sobald Ihre Vermieterin oder Ihr Vermieter sie
                  bereitstellt.
Schaltfläche:     Zu meinen Unterlagen
```

Context and navigation (`M10-COPY-04`):

```text
Kontextwechsler (Eintrag): Mietverhältnis — <Straße Hausnummer>, <Einheitsbezeichnung>
Kontextwechsler (Gruppe):  Als Mieter
Portalnavigation (Titel):  Meine Unterlagen
Navigationspunkte:         Mein Mietverhältnis · Abrechnungen · Verbrauchsinformationen
```

Headings and actions (`M10-COPY-05`):

```text
Mietverhältnis:              Mein Mietverhältnis
Abrechnungsdokumente:        Abrechnungen
UVI-Dokumente:               Verbrauchsinformationen
UVI-Einzeldokument:          Verbrauchsinformation <Monat JJJJ>
Abrechnungs-Einzeldokument:  Abrechnung <Zeitraum>
Download-Aktion:             Als PDF speichern
```

Loading, empty and error states (`M10-COPY-06`):

```text
Laden (alle drei Ansichten):
  Wird geladen …

Leer:
  Mietverhältnis          Zu Ihrem Zugang ist derzeit kein Mietverhältnis hinterlegt.
                          Bitte wenden Sie sich an Ihre Vermieterin oder Ihren Vermieter.
  Abrechnungen            Es liegen noch keine Abrechnungen für Sie bereit.
  Verbrauchsinformationen Es liegen noch keine Verbrauchsinformationen für Sie bereit.

Fehler (alle drei Ansichten, identisch):
  Die Daten konnten nicht geladen werden. Bitte versuchen Sie es später erneut.
  Schaltfläche: Erneut versuchen
```

The tenancy empty state is defensive: a successful activation should make it unreachable, but the
screen must still provide the stated instruction if the invariant is broken. These six copy slots
remove the M10-R4 copy blocker; they do not approve any schema, endpoint or UI implementation.

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
| `AdvancePaymentPeriod` | Dated contractual advance amount replacing the tenancy scalar. | **Shipped**, M6-A |
| `UnitProfileVersion` | Effective-dated use, fixed-point rooms, controlled amenities and source evidence. | **Implemented on `development`; partially verified**, UI-05B |
| `TenancyContractVersion` | Effective-dated contract classification with source evidence. | **Implemented on `development`; partially verified**, UI-05B |
| `TenancyContractPosition` | Dated garage/parking position; inclusion is `INCLUDED` or `SEPARATE`, never a boolean shortcut. | **Implemented on `development`; partially verified**, UI-05B |
| `TenancyRentChange` | Effective date, new cold-rent cents and evidence; insert-only history. | **Implemented on `development`; partially verified**, UI-05B |

Shipped validity and cost ranges use half-open dates: `valid_from` or `period_from` is included and
`valid_to` or `period_to` is excluded. Page 01's user-facing billing period is inclusive; adapters
must convert that boundary explicitly instead of mixing the two conventions.

| Shipped entity | Key fields | Constraints and meaning |
| --- | --- | --- |
| `Building` | account, optional landlord, name and address, `fiktivbelegung_mode`, nullable `fiktivbelegung_waiver_note` | Composite optional landlord edge; account-scoped root for property calculations. The mode defaults to `LETZTE_BELEGUNG` (spelling note below) and `CheckConstraint ck_building_fiktivbelegung_waiver_logged` refuses `KEINE` unless a waiver note is present. |
| `Unit` | building, label, `area_sqm_x100` | Integer area; composite building edge. |
| `Tenancy` | unit, `valid_from`, nullable `valid_to`, `base_rent_cents` | One lease identity over time; composite unit edge. Overlap refusal is a domain invariant. Contractual advance amounts come only from temporal `AdvancePaymentPeriod` rows. |
| `TenancyParty` | tenancy, renter | Unique `(tenancy_id, renter_id)` join permits several renters on one lease without duplicating the tenancy. |
| `SelfUsePeriod` | unit, `sqm_x100`, kind, note, validity | Partial-area self-use over time; composite unit edge. |
| `PersonCount` | tenancy, `count`, `valid_from`, nullable `valid_to` | Half-open Personenzahl history; composite tenancy edge. `CheckConstraint ck_person_count_non_negative` allows `0` (an empty but running lease) and rejects negatives. |
| `MdlStatement` | building, `branch`, `period_from`, exclusive `period_to`, `confirmed_total_cents`, `owner_position_cents`, nullable `co2_kg_x1000` / `co2_cost_cents` / `heated_area_sqm_x100`, `co2_evidence_present`, `source_ref`, `version`, `confirmed_at` | Composite building edge. Unique `(building_id, period_from, period_to, version)`; a correction inserts `version + 1` and the earlier row stays, so nothing UPDATEs a confirmed row. `source_ref` is required: a passed-through figure whose origin nobody can name is not evidence. |
| `MdlStatementPosition` | `mdl_statement_id`, `tenancy_id`, `amount_cents` | Composite statement and tenancy edges; unique `(mdl_statement_id, tenancy_id)`; amount non-negative. Stored as delivered — `docs/03` H7 validates and passes through, never recomputes. |

Migration `0029` adds the four UI-05B records above. Each carries `account_id`, a composite
account-safe edge to its unit or tenancy, ENABLE/FORCE RLS with `WITH CHECK`, and an append-only
database trigger. Unknown legacy profile or contract facts remain absent and render as “Nicht
dokumentiert”; neither the seed nor the read model infers them from labels or dates. Money remains
integer cents. UI-05B does not create payment truth: UI-07 now supplies its owner-only payment
projection from existing receivable facts; recurring receivable generation remains source-blocked.

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

### Resolved M6-A defect: the former `Tenancy.advance_payment_cents` scalar

The former scalar recorded only the monthly contractual Soll at tenancy creation. It could not express
an adjustment during a continuing lease, although § 560 Abs. 4 BGB permits an advance adjustment
after a statement. The old APIs exposed no tenancy update path. Ending the tenancy and opening
another one is not an acceptable workaround: statement parties are keyed by tenancy, so one
continuing renter would appear as two parties even though the consecutive periods do not overlap
and ordinary allocation checks stay green.

The scalar is not an engine input, an actual payment, or a lawful substitute for Page 01's paid
advances. M6-A replaced it with the account-scoped, composite-FK-protected
`AdvancePaymentPeriod`; the initial migration creates one open-ended period at
`tenancy.valid_from`. This is a data migration, not just a model rename.

### M6-A temporal advances and confirmed actual-advance preview

**Status:** shipped M6-A technical scope. **Source:** Page 01, § 4 minimum #4
and its `08-F02`–`08-F04`, `08-F10`, `08-F14`, `08-F16`, `08-F18`–`08-F19` oracle branches;
this document's financial-time-axis and scalar-defect rules; and the M6-A product charter dated
23.08.2026.  **Rechtsstand:** 08/2026 for the already transcribed Page-01 statement rule.
The manual-entry workflow below is a Lokara technical/product convention, not an assertion about
banking, payment-service or tax law.

M6-A replaces the tenancy scalar with the following append-only records. All records carry a
non-null `account_id`; every tenancy edge is composite `(account_id, tenancy_id)`. A route that
carries both a building and tenancy must prove that the tenancy's unit belongs to that building,
even inside one account. RLS and composite foreign keys are both required; either one alone is
insufficient.

| Record | Required fields and constraints | History/read rule |
| --- | --- | --- |
| `AdvancePaymentPeriod` | `id`, `account_id`, `tenancy_id`, non-negative `amount_cents`, `valid_from`, nullable `predecessor_id`, required `declaration_ref` and server `created_at`. The initial backfill has `predecessor_id = NULL`. | The effective end is **derived**, never stored: a period ends at the next successor's `valid_from`; no successor means open-ended. A successor must have the same account and tenancy and start after its predecessor. It is an insert, never an update of the earlier row. |
| `AdvancePayment` | `id`, `account_id`, `tenancy_id`, strictly positive `amount_cents`, `payment_date`, required non-blank `evidence_ref`, server `accepted_at`, and nullable `reversal_of_id`. | An owner-entered entry is accepted immediately in M6-A. It is immutable. A correction inserts a compensating entry that references the original entry; it does not edit or delete it. The compensating entry has the opposite allocation effect while retaining a positive recorded amount. |
| `AdvanceAllocation` | `id`, `account_id`, `payment_id`, `tenancy_id`, inclusive `period_start` and `period_end`, and positive `amount_cents`. | Allocations are immutable evidence. Each allocation belongs to the payment's tenancy/account, and the sum allocated from one payment may not exceed its positive payment amount. M6-A creates one allocation per manual payment, but the separate record keeps the later matching boundary explicit. |
| `AdvanceReconciliation` | `id`, `account_id`, `tenancy_id`, inclusive period, `version`, `total_cents`, nullable `supersedes_id`, `confirmed_at` and an immutable ordered list of allocation IDs. | `total_cents` is derived only from the accepted listed allocations (with correction signs applied). An explicitly empty allocation list is a valid confirmation of zero. The newest version for the same tenancy and billing period supersedes the earlier reconciliation without changing it. |

The tenancy-create request accepts an initial advance amount only as the input used to create the
first `AdvancePaymentPeriod`; tenancy read responses expose `advance_payment_periods`, not
`advance_payment_cents` or an `advancePaymentCents` alias. The migration must first backfill every
existing tenancy from its scalar (`valid_from`, scalar amount, no predecessor), then make the scalar
unavailable to new model/API code. A zero contractual period is valid. No update/delete endpoint
exists for any of these four record types.

M6-A does **not** introduce imported bank transactions, matching proposals, learned IBANs,
receivables, final statements, tenant portal delivery, PDF changes or a tax export. The payment entry
is immediate owner-entered evidence only; it neither proves a bank transfer nor creates a tax event.

#### Reconciliation and preview invariant

For a selected tenancy and billing period, the internal owner preview computes:

```text
confirmed_actual_advances = signed sum(accepted allocations in the current reconciliation)
saldo = subtotal - confirmed_actual_advances
```

All values are integer cents. A positive Saldo, zero Saldo and a negative Saldo are all valid
arithmetic results. If there is no current reconciliation, the projection returns its subtotal and
the reconciliation state `MISSING`, but **omits** both actual advances and Saldo. It must not infer
them from the contractual schedule, sum unconfirmed entries or use result language such as
`Nachzahlung`, `Guthaben`, `zu zahlen`, `offener Betrag` or `fällig`. This is an owner-only preview;
it is neither finalization nor a renter document.

The current projection must expose its reconciliation state and, when confirmed, the current
reconciliation identity/version, confirmed actual advances and Saldo. A correction has no effect on
an already confirmed preview until a newer reconciliation explicitly selects the corrected evidence.
This makes the before/after evidence auditable rather than silently changing an old result.

#### M6-A executable fixture map

| Fixture | Scenario and required result |
| --- | --- |
| `M6A-F01` | Migration backfills every existing tenancy into exactly one open-ended initial schedule at `tenancy.valid_from`, with the former scalar amount. The scalar is then absent from the mapped tenancy and tenancy HTTP contracts. |
| `M6A-F02` | A 12,000-cent initial period followed on 01.07 by a 15,000-cent successor keeps the initial row unchanged and reads as `[01.01, 01.07)` then `[01.07, open)`. |
| `M6A-F03` | A confirmed 28,857-cent allocation yields confirmed actual advances `28,857`; an explicitly confirmed empty list yields `0`, not missing. |
| `M6A-F04` | Without a reconciliation, preview exposes subtotal and `MISSING` only; actual advances and Saldo are absent. |
| `M6A-F05` | With subtotal `28,857`, confirmed advances `28,000` yields Saldo `857`; `28,857` yields `0`; `30,000` yields `-1,143`. |
| `M6A-F06` | Reversing a 28,000-cent entry and creating a new reconciliation changes the current confirmed total by `-28,000`; the prior reconciliation remains readable and unchanged. |
| `M6A-F07` | Foreign-account rows and a tenancy from another building cannot be read, attached, allocated or reconciled through guessed IDs; database composite edges and RLS reject cross-account links. |
| `M6A-F08` | An allocation cannot attach a payment to a different tenancy, even within one account; nor can any advance payment, allocation, reconciliation, predecessor or reversal cross an account. Every such edge rejects the link. |
| `M6A-F09` | The cumulative positive allocation amount for one payment never exceeds that payment's positive recorded amount; a second allocation that would exceed it is rejected. |
| `M6A-F10` | One original payment has at most one reversal. A second reversal is rejected and the original/reversal evidence remains unchanged. |
| `M6A-F11` | The live app role sees all five M6-A tables in account A, sees none under account B, cannot insert a foreign-account row, and cannot update or delete an A row. |
| `M6A-F12` | The owner-only preview exposes reconciliation `id` and `version` together with confirmed advances and Saldo. An assigned employee keeps the otherwise permitted statement projection, but receives none of those M6-A fields or state. |

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
`09-F01`–`09-F32` data oracle. Slice C technically implements the catalogue and Page-02 NK
integration, but this is not production closure or legal approval: missing register rows and
unresolved classifications remain `verify-before-production`.

The Page 08 bank-matching contract is **complete, approved and merged** in `docs/15`. All thirteen
cases run through the M6-C1 engine. M6-C2 ships the receivable, bank, matching-evidence and
payment-ledger schema, adapter and owner-scoped endpoints; M6-C3-0 closes the audited database
invariants through migration `0020`. C3a's service and final `0021` are technically complete,
development-synchronized and locally merged into `main`. C3b's three job entrypoints are
technically complete and locally merged into `main`; they add no table, column or migration
and read this schema only through an account-scoped session. C3c's landlord *Zahlungen* screen is
technically complete and locally merged; it is client-only and adds no table, column or migration
either.

UI-07 on `development` adds `BankTransactionClassificationEvent` through migration `0030`. Each
row records one `IGNORED` or `RESTORED` action, optional reason, actor and timestamp against the
immutable bank transaction. The table is account-scoped, uses the composite
`(bank_transaction_id, account_id)` edge, forces RLS with `WITH CHECK`, and rejects UPDATE and
DELETE. Current state is the newest event; restoring or a demo reset appends evidence instead of
rewriting history. The unified workspace remains a read model and adds no mutable summary table.

### UI-08 meters, lifecycle and heating-source choice — implemented, partially verified

Migration `0032` keeps `MeterKind` and `MeasurementUnit` as the normalized engine axes and adds the
explicit administration type `MeterDeviceType`: heat meter, heat-cost allocator, warm-water meter
or cold-water meter. The database and API enforce the type → medium/unit relation. Remote
readability is a device fact only; it never claims a connection or changes a manually entered
reading's source.

| Record | Development evidence fields | Invariant |
| --- | --- | --- |
| `Meter` | building, optional unit, explicit device type, medium/unit, serial, own label, installation place, manufacturer/model, installation date, remote-readability and calibration-data facts | `unit_id = NULL` means building-level. Serial is unique per building. Type/medium/unit and calibration facts are constrained. `DATA_AVAILABLE` requires observed date plus evidence; missing, not-applicable and review-required remain distinct. |
| `MeterLifecycleEvent` | building, meter, `INSTALLED`, `REMOVED`, `REPLACED` or `VOID`, effective date, reason and optional related meter | Append-only. Replacement links predecessor and successor and writes both device-change readings in one transaction. Hard deletion is not an API operation. |
| `MeterReading` | meter, date, fixed-point value, reason/source, note, optional tenancy/estimate provenance, optional direct predecessor and confirmation evidence | Append-only at the database trigger. Corrections require one same-meter predecessor and a reason; a direct predecessor has at most one successor. Manual API writes always persist source `MANUAL`. |
| `HeatingCostEntry` | building, backend category, amount/period, source reference, optional source-linked CO₂ facts and reasoned void state | Structured invoice input; voiding preserves the row. It never exposes an ordinary allocation key. |
| `HeatingBillingModeVersion` | building and exact period, increasing version, `LOKARA` or external provider, provider workflow and optional confirmed MDL statement | Append-only and account-scoped. An adopted external result references a confirmed statement in the same building/period; the statement path never uses internal and external heating results simultaneously. |

The API projects available billing periods and, per meter, the effective opening/closing evidence,
measured difference, incomplete reason, estimate basis/provenance or device-change exclusion. The
browser selects and renders this projection; it does not generate years, interpolate or subtract
across devices.

Calibration status comes only from the shared Page-05 G1 guard and the versioned rules store.
Approved `docs/12` supersedes the older five-year reading: applicable cold-water, warm-water and
heat meters use six years and calendar-year-end expiry at Rechtsstand 08/2026. The transition note
and missing register rows remain visible authority limits; expiry remains a warning, not an
automatic statement blocker.

Migration `0032` enables and forces RLS with `WITH CHECK` on both new tables and uses composite
account/building foreign keys. Migration `0040` makes terminal lifecycle reasons, correction
confirmation, heating-cost void reasons and external-provider names NULL-safe, and rejects provider
fields on `LOKARA` mode rows. Its heating-cost trigger rejects deletion and substantive updates,
allowing only the first atomic transition from no void to a timestamp plus nonblank reason.
All 20 rollback-only app-role regressions pass and the boundary re-audit is clean. The 05.09.2026
full and non-fresh demo gates pass `1967` Python and `188` web tests. The separate live-browser matrix and remaining
UI acceptance still prevent a full UI-08 closure claim.

### Monthly UVI evidence and archives

Migrations `0022` and `0023` persist the U4/U4b boundary defined in `docs/16`:

| Record | Durable role |
| --- | --- |
| `MonthlyMeterReading`, `MonthlyMeterReadingSource` | Immutable normalized calendar-month consumption and its raw reading links; a correction appends one direct successor. |
| `UviStationAssignment`, `UviMonthlyDegreeDay` | Persisted PLZ/month station choice and immutable monthly DWD value, including exact source/provenance and correction identity. |
| `DwdClimateFactor` | Immutable annual rolling DWD factor for one PLZ and exact period; it is not reused as monthly degree-day evidence. |
| `BuildingUviConfiguration` | Effective-dated building energy/configuration inputs with source identity, Rechtsstand and verification status. |
| `UviBuildingMonthlyEvidence`, `UviBuildingMonthlyEvidenceSource` | Immutable building-month heat/HKV evidence, its main-meter identity and authoritative raw reading links; a correction appends one direct successor. |
| `UviRun`, `UviDeliveryEvent` | Immutable normalized input/result archive, resolved source snapshots and hash, followed by append-only lifecycle evidence. |

Subsequent migrations extend this boundary without replacing archived evidence:

| Migration | Persisted extension |
| --- | --- |
| `0033` / `0034` | Admit exactly `GAS_METER + HEAT + CUBIC_METRE`, persist separate effective `calorific_factor` (Brennwert for split rows) and `condition_number`, and repair legacy gas evidence while preserving original source/history. `docs/16` § 3.2 owns the bounded legacy rule. |
| `0035` | Persist `centroid_dataset_identity` and `centroid_dataset_version` on station assignments, pinning the WZB PLZ source; the archived source snapshot retains licence/attribution provenance. |
| `0036` | Add nullable effective `BuildingUviConfiguration.warm_water_hot_temp_c` for versioned warm-water conversion; absence does not invent a temperature. |
| `0037` | Add nullable landlord `phone`, `email` and `logo` for the archived letter header. |
| `0038` | Store an immutable run `support_code`, resolved only within the authorized account/building context. |
| `0039` | Enforce one run per `(account_id, tenancy_id, month)` and one `EMAILED` claim per run; repeated generation returns the existing run without appending another `GENERATED` event. |

U5 resolves the effective correction leaf for every month it consumes, records the normalized
evidence in `UviRun`, creates only a `GENERATED` event and renders a separate German renter
document for an authorized owner to download. This is an owner-side generation/archive boundary,
not renter publication or delivery: scheduled and email delivery belong to M9, and portal
publication belongs to M10.

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

##### Round-five convention: partial self-use overlapping a vacancy

`SelfUsePeriod` stores an **area** (`sqm_x100`), not unit-level occupancy, so a self-use row can
cover part of a unit. Original Page 01 § 3.5, § 4 D0 and edge cases E17–E19 contain **no source
rule** for a partial self-use overlapping a vacancy. Berkay's round-five answer of 11.09.2026
confirms the shipped direction as a deliberate Lokara **Konvention**, Rechtsstand 09/2026,
`geprüft` for production safety. It is not settled law and has no legal source of its own. The
safety argument is asymmetric: leaving the fiction in place can only allocate more of the
person-keyed fixed cost to the owner; removing or apportioning it could charge renters on an
unsupported basis. BGH VIII ZR 159/05 and LG Krefeld 2 S 56/09 support that direction, but do not
source the product rule itself.

Source trace: derived from `docs/02` § 4, which defines `VACANT` as "neither rented nor self-used",
read together with original Page 01 § 4 D0, which runs "for each Leerstandsperiode". Shipped in
`apps/api/src/lokara_api/person_counts.py`; confirmed by Berkay's round-five answer, § 1. The new
register row `R-01-D0-02` remains pending in Berkay's authoritative CSV and is not written by
Lokara.

| Constellation | Shipped behavior | Why this direction |
| --- | --- | --- |
| **Full-unit** self-use (`sqm_x100 >= unit.area_sqm_x100`) | Those days are removed from the derived D0 vacancy: a self-used day is not a vacancy day and receives no fictional occupancy. | Follows directly from the two cited definitions; unambiguous, and the only inference in it is that the areas are comparable. |
| **Partial** self-use (`sqm_x100 < unit.area_sqm_x100`) | The day stays a vacancy day, so the fiction still applies to it, and the document carries the approved German finding below. | The conservative product convention: dropping the fiction would hand renters the whole person-keyed fixed cost; apportioning it would invent an area-weighted person count. Any uncertainty therefore burdens only the owner. |

The finding is landlord-facing copy and stays in German. Fixed parts verbatim, interpolated parts in
angle brackets:

```text
<Einheit>: Teil-Eigennutzung (<Fläche> m² von <Gesamtfläche> m²) vom <TT.MM.JJJJ> bis <TT.MM.JJJJ>. Die Leerstandstage in diesem Zeitraum werden vollständig mit Fiktivbelegung gerechnet; die anteilige Eigennutzung wird nicht gesondert abgegrenzt. Der darauf entfallende Anteil trägt der Eigentümer.
```

An open-ended self-use row (`valid_to IS NULL`) is clipped to the billing window rather than treated
as infinite. That part is the ordinary half-open temporal rule of § 4, not an assumption.

This decision does not change full-unit self-use: those days remain outside `VACANT` by definition.
The open lawyer bundle may still review the convention, but it no longer blocks production.

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

Heating and the Slice-C NK path calculate every renter block with half-up rounding and commit the
remainder to one property residual. The residual rule and renter-side half-up rounding move together:
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
| Covered tenancy | `tenancy_id`, renters/addressee, delivery address, unit, clipped usage dates and days, person/area/consumption inputs. M6-B freezes the selected address and isolated archive; renter delivery remains incomplete. |
| Actual advances | Paid cents for the period, distinct from contractual Soll. M6-A/B confirm/freeze them for final archives; locally merged C3a books accepted matches into the ledger. Round five specifies that tenancy credit remains until an explicit owner offset and suppresses covered reminder amounts; implementation is pending. C3b's job wiring is technically complete and locally merged. Confirmed zero is valid. |
| Operating-cost result | Cost identity/classification, total, key, numerator, denominator, measurement unit, rounded renter share, § 35a inputs/result, warnings and provenance. |
| Heating and CO₂ result | Every required block, ratio, numerator/denominator, device evidence, CO₂ figures, warnings and provenance defined in `docs/03`. |
| Vacancy result | Origin unit/dates, fictional occupancy basis, residual block (a), non-allocable block (b), rounding block (c) and evidence. The residual contract is settled; the full annex is not implemented. |
| Projection and archive | Audience plus exactly one tenancy for tenant output, document bytes/storage keys and hashes. **Shipped M6-B owner-only archive scope**; portal/delivery remains open. |

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

Before M6-B, the `Statement` row was an incomplete lifecycle anchor. M6-B adds the finalization
evidence described below:

| Shipped field or constraint | Meaning and limit |
| --- | --- |
| `account_id`, `building_id` | Account-scoped statement and composite building edge. |
| `period_start`, `period_end` | Stored statement period; M6-B also stores the immutable normalized snapshot. |
| `version`, `status` | Version defaults to 1; status is `DRAFT`, `FINALIZED` or `SUPERSEDED`. |
| `total_cents`, `finalized_snapshot`, `finalized_at`, `supersedes_statement_id`, `created_at` | M6-B finalization evidence; archive bytes/hashes are held in scoped archive rows. |
| Unique `(building_id, period_start, period_end, version)` | Prevents duplicate versions for one building period; M6-B transition and immutability constraints complete the append-only finalization boundary. |

```text
live inputs ── preview (no archive)
     │
     └── finalize v1: DRAFT → FINALIZED
                           │ correction
                           ├── v1 → SUPERSEDED (retained)
                           └── insert v2: DRAFT → FINALIZED
```

The lifecycle enum and uniqueness constraint are **shipped**. M6-B ships the complete technical
immutable transition, snapshot and document archive; preview and finalization have different contracts:

- A preview reads current normalized rows, calculates and renders live. It creates no archive.
- Finalization creates one immutable, reproducible snapshot for account, building, period and
  version, including normalized inputs, outputs, engine/rule versions, `Rechtsstand`, timestamps,
  hashes and archived documents or immutable storage keys.
- One result yields one internal landlord overview and one independently rendered document for each
  eligible tenancy. Lokara never creates one all-renters PDF and later crops or masks it.
- A correction appends `vN+1`, retains `vN` and records supersession. Referenced input rows and
  archived bytes cannot be destructively changed or deleted.

### M6-B — finalized, isolated statement documents

**Status:** shipped M6-B technical scope. **Sources:** approved Page 01 in
`berkay-work/Spec-Seiten/01 · Die Abrechnung 3a95fd420731816c9048ed7a517c3e9e.md`, its register
rows transcribed in `docs/08`, the M6-A advance/reconciliation contract above, and this technical
slice charter. **Rechtsstand:** 08/2026 for the Page-01 statement requirements. The timing of a
Nachforderung and any payment deadline remain `verify-before-production` in the register; this
contract neither settles them nor enables legal-production delivery.

M6-B is a technical archive, not a bank-matching, finAPI, email-delivery, renter-portal or legal
approval feature. It uses database bytes in this local slice; an object-storage adapter is deferred.
Every row below carries non-null `account_id`, uses a composite account-preserving foreign key for
each scoped parent, and is protected by RLS. A selected record is copied verbatim into the final
snapshot; later address/instruction versions cannot alter an older document.

| Record | Required fields | Append-only and isolation contract |
| --- | --- | --- |
| `Statement` finalization data | immutable normalized `finalized_snapshot` containing the selected account/building/period inputs, party outputs, selected reconciliation identity/version and total, selected delivery-address/instruction versions and values, engine/rule versions, warnings/provenance and all applicable `Rechtsstand`; `finalized_at`; nullable `supersedes_statement_id` | A finalization changes only a new/draft statement into `FINALIZED` once, with its snapshot. A correction names the latest finalized statement, marks only that predecessor `SUPERSEDED`, and inserts/finalizes `vN+1`. Neither snapshot is updated or deleted. `supersedes_statement_id` is a scoped edge to a statement in the same account, building and period. |
| `StatementDocumentArchive` | `id`, `account_id`, `statement_id`, audience (`OWNER` or `TENANT`), nullable `tenancy_id`, `content_bytes`, lowercase-hex `sha256`, `mime_type`, `filename`, `created_at` | One owner row has `tenancy_id = NULL`; one tenant row has exactly one account/building-valid tenancy. Enforce exactly one archive per `(statement, OWNER)` and per `(statement, TENANT, tenancy)` (a partial unique index is required for the NULL owner edge). Bytes, hash, MIME type, filename and timestamp are immutable; download returns these stored bytes only. |
| `StatementSettlement` | `id`, `account_id`, `statement_id`, `tenancy_id`, `kind` (`RECEIVABLE` or `CREDIT_REFUND`), positive `amount_cents`, immutable `origin_saldo_cents`, nullable `late_positive_exception_reason`, `created_at` | At most one settlement for a statement/tenancy. A positive timely Saldo creates `RECEIVABLE`; a negative Saldo creates `CREDIT_REFUND` with its absolute cents; zero creates no row. A late positive Saldo creates no settlement unless a non-blank exception reason is explicitly recorded. It is an obligation, never a payment, bank transaction or tax cash event. |
| `TenancyDeliveryAddress` | `id`, `account_id`, `tenancy_id`, `version`, `addressee`, `street`, `postal_code`, `city`, `country`, `created_at` | A new version is an insert; `(tenancy_id, version)` is unique. No update/delete/current-value flag exists. The selected version must be account-valid and is frozen verbatim in the tenant snapshot. |
| `OwnerPaymentCreditInstruction` | `id`, `account_id`, `version`, non-blank `instruction_text`, `created_at` | A new instruction is an insert; `(account_id, version)` is unique. It is technical payment/credit copy, not a bank account, matching decision or payment event. Its chosen value/version is frozen verbatim in every final snapshot that uses it. |

#### Atomic finalization and correction

The owner-only finalization command takes `building_id`, inclusive `period_start` and `period_end`,
an optional `supersedes_statement_id`, and an optional `late_positive_exception_reason`. It:

1. authorizes an `OWNER` against the URL account and building; an employee, tax adviser, renter
   route or foreign account/building is forbidden;
2. rejects a reversed/over-12-month period, overlap, missing required source data, production-blocked
   cost, hard-stop result, foreign tenancy/reference, or a rendering failure before any archive write;
3. identifies every clipped tenancy. A tenancy with zero clipped usage days is excluded from tenant
   documents and settlements, and recorded only in the owner overview footnote;
4. requires a current confirmed `AdvanceReconciliation` for **every eligible tenancy** for the same
   inclusive period. An explicitly confirmed empty allocation set is zero; missing confirmation is
   not zero;
5. computes once, selects the current address and owner instruction, independently renders one owner
   overview and one tenant document per eligible tenancy, hashes the exact bytes with SHA-256, then
   persists statement snapshot, archive rows and the applicable settlement rows in one transaction.

If any condition fails, the transaction leaves no new statement version, snapshot, archive or
settlement. Rendering every document precedes persistence so a later tenant-render failure cannot
leave a partial archive. A first finalization must not name a predecessor. A correction must name the
latest finalized version for the same account/building/inclusive period; naming an older, foreign,
different-building or already-superseded version is refused. It does not edit the predecessor or
reuse its documents.

#### Owner-only HTTP boundary

The following are the M6-B public interfaces. Their dates are inclusive at the HTTP boundary. They
are owner-only even where an employee may use the existing live preview; no renter endpoint, portal
publication, delivery/email, bank-transaction, matching or finAPI endpoint is introduced.

| Method and path | Contract |
| --- | --- |
| `POST /a/{account_id}/buildings/{building_id}/statements/finalize` | Executes the atomic command above. Body has `periodStart`, `periodEnd`, optional `supersedesStatementId`, optional `latePositiveExceptionReason`. It returns only archive metadata/history identity, never a recomputed document. |
| `GET /a/{account_id}/buildings/{building_id}/statements/history` | Lists archived statement versions for the selected period/building, including `version`, status, predecessor relation, finalization time and document metadata. |
| `GET /a/{account_id}/statement-documents/{document_id}/download` | Returns the archived `content_bytes` with stored MIME type and filename after account/owner authorization. It never recalculates or re-renders. |
| `GET`/`POST /a/{account_id}/buildings/{building_id}/tenancies/{tenancy_id}/delivery-addresses` | Reads/creates append-only tenancy delivery-address versions after verifying the tenancy belongs to that building/account. |
| `GET`/`POST /a/{account_id}/payment-credit-instructions` | Reads/creates append-only account owner-payment/credit-instruction versions. |

The UI may expose only these owner controls: append a delivery address or instruction, finalize a
selected building/period, explicitly correct the latest version, inspect history, and download an
archive. It must not present finalization as renter delivery or legal/production approval.

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

### M6-C2/C3a — bank matching, receivables and the payment ledger

Approved `docs/15` owns the calculation contract; this section owns only the persisted shape.
The engine in `packages/matching-engine` decides, and these tables store what it read and what
it decided. Nine account-scoped tables, all with FORCEd RLS and composite `(id, account_id)`
foreign keys (migration `0017`):

| Record | Minimum contract |
| --- | --- |
| `BankAccount` | `id`, `account_id`, `provider`, `provider_account_id`, `normalized_iban`, `display_name`, nullable `consent_expires_at`. Unique per `(account_id, provider, provider_account_id)`. |
| `BankTransaction` | `docs/15` § 3.1 in full: signed `amount_cents`, the three separate dates, nullable counterpart/reference/provider fields and `is_potential_duplicate`. Identity is `(account_id, bank_account_id, provider_transaction_id)` — **never the provider id alone**, because providers do not allocate ids globally. `bank_booking_date`, not `finapi_booking_date`, decides whether a receivable is due. |
| `Receivable` | `docs/15` § 3.2. The four nominal components sum to `expected_cents` (database check). `0 ≤ open_cents ≤ expected_cents`. `category` is `rent` or `nk_nachzahlung`. Carries `stored_reference`, which is **unused** — see the note below. |
| `RenterMatchingProfile` | `docs/15` § 3.3, one per `(account_id, renter_id)`. `known_ibans` is derived from active `IbanHistory` rows and is deliberately not a column: a stored copy would be a second truth to keep in sync. |
| `IbanHistory` | `docs/15` § 3.3, temporal (`valid_from`/`valid_to` are timezone-aware instants), never overwritten. A non-null IBAN is learned only after a user confirms the rank-1 Review proposal; `valid_from` equals that confirmation instant and null is never learned. |
| `MatchProposal` | `docs/15` § 4: every component signal stored individually, plus deterministic positive `rank`, `confidence`, `decision`, `convention_version` and the German reason. Rank is unique per transaction; each immutable run is inserted once, contiguous from 1, and all rows share one decision, reason and convention version. |
| `MatchConfirmation` | `docs/15` § 4: actor and time, as a separate row. Confirmation never rewrites the proposal it confirms. |
| `PaymentLedgerEntry` | `docs/15` § 5.3, append-only by database trigger. A PAYMENT cites only rank-1 `AUTO_MATCH` evidence or a rank-1 `NEEDS_REVIEW` proposal with a final `CONFIRMED` decision. A reversal appends a compensating entry linked through `reverses_entry_id`; nothing is edited or deleted. |
| `PaymentAllocation` | `docs/15` §§ 5.1–5.2: what one entry paid on one debt, split by § 367 BGB order and then by nominal component. New C3a writes store a complete before/after projection snapshot; legacy rows may keep an all-null pair and cannot be auto-reversed. Rent components sum to principal; `nk_nachzahlung` principal keeps all four named rent/advance components at zero. Append-only by the same trigger. |

**Isolation was never the gap; everything inside one account was.** `0017` got RLS and the
composite `(id, account_id)` edges right, and constrained nothing else — so a `payment_allocation`
could settle renter 2's debt from renter 1's cash, an allocation could exceed the cents its ledger
entry carried, a negative component cancelled inside the components-sum check and then fed Page 01
a negative advance, a `REVERSAL` could be positive or filed twice, `iban_history` was freely
rewritable and needed no confirmation, and two tables documented immutable were not. A boundary
audit on 23.08.2026 found all six. Migration `0019` was the answer, and a second audit on
the same day found that four of its mechanisms were missing or wrong; migration `0020`
repairs them. The table below describes the schema **as of `0020`**:

| Invariant | Mechanism |
| --- | --- |
| A row may not name a parent that contradicts its siblings — `docs/15` § 6, *"a match never moves money between renters"* | Four `BEFORE INSERT OR UPDATE` triggers: a receivable's renter must be a `tenancy_party` of its tenancy; a proposal's renter must be the debt's renter; a ledger entry's proposal must be for its own transaction; an allocation's debt must belong to the entry's renter. |
| An allocation may not settle money that never arrived | `uq_payment_allocation_entry_receivable` and a **signed, kind-aware** cap trigger taking `FOR UPDATE`. A `PAYMENT` allocation is non-negative and may not exceed its entry; a `REVERSAL` allocation is non-positive and may not give back more than its entry carried. `0019` used a blanket non-negative CHECK and compared against `abs(amount_cents)`, which rejected `reversal.py`'s own compensating rows while granting a −108.000 reversal a +108.000 budget — and returned NEW when the entry was not found, so it failed **open**. |
| A reversal has a shape — § 5.3 and `F06` net to zero | `ck_payment_ledger_reversal_shape`, a partial unique index so one payment has at most one reversal, and (`0020`) an `enforce_ledger_entry_evidence` arm requiring the reversed entry to be a `PAYMENT` in the same account whose amount is negated **exactly**. Nothing ties the two entries' `bank_transaction_id` together: § 5.3 makes the return a distinct provider movement resolved by E2E or mandate reference, so requiring one shared id would make the real shape unrepresentable. |
| A learned IBAN exists only because it was confirmed — § 3.3 and `F09` | `ck_iban_history_requires_confirmation`, a composite FK to `match_confirmation`, a trigger permitting exactly one change (closing an open period), and (`0020`) `enforce_iban_history_confirmation`: the cited confirmation must have `outcome = 'CONFIRMED'` and its proposal must name **this** renter. `0019` asserted only that a confirmation id was present, so a rejected review — or renter 1's confirmation — could mint the +60 unique-IBAN signal for renter 2. The active-mapping index is keyed `(account_id, renter_id, normalized_iban)`, not `(account_id, normalized_iban)`: § 3.3 requires two active renters to be able to share one IBAN and each receive the ambiguous signal (`F07`), which `0019` made unrepresentable. |
| Evidence documented immutable now is — § 4 and § 147 AO | `bank_transaction`, `match_proposal` and `match_confirmation` are append-only, joining `payment_ledger_entry` and `payment_allocation` from `0017`. One proposal can be confirmed once. |
| A receivable's § 367 projection columns must agree with `status` | `ck_receivable_open_components` — `open_principal_cents = open_cents` (equality, not a three-way sum: `settlement.py` computes `open_after = open_cents - principal`, so `open_cents` **is** the open principal, and a sum rule would contradict the fixture-verified engine) and `open_cents <= expected_cents`. `open_costs_cents`/`open_interest_cents` are bounded below only; nothing in `docs/15` bounds them above and they arrive from Page 05 in M9. Plus `ck_receivable_settled_has_nothing_open`. |
| The Page-01 handoff cannot double-bill | `uq_receivable_source`, and (`0020`) `uq_receivable_nk_nachzahlung_period` on `(account_id, tenancy_id, period) WHERE category = 'nk_nachzahlung'`. A correction statement is a new `source_id`, so the first index does not cover it, and the router's period guard is a bare SELECT-then-INSERT. |

Migration `0018` limits the components-sum check to `category = 'rent'`. An `nk_nachzahlung` has no
rent, garage or advance component, and § 5.2 makes the cost concrete: the paid NK-advance component
feeds the annual actual-advance total Page 01 consumes, so parking a Nachzahlung there to satisfy
the arithmetic would double-count it as an advance that was never paid.

#### C3a additions in migration `0021`

The final amended `0021` is technically verified from the disposable `lokara_c3a_check` database
and locally merged into `main`. Development matches that schema exactly after one validated
transactional hand-delta. Column types, constraints, trigger
timing/deferrability, hardened function definitions, search paths and hashes are identical; evidence
counts and all 68 legacy Auto confirmations are unchanged.

- Existing proposals receive deterministic ranks. Before future-only insert triggers are installed,
  migration validation rejects—rather than rewrites—any backfilled transaction group whose ranks
  are not contiguous from 1 or whose decision, German reason or convention version differs.
- A transaction's proposal run is insert-once and sealed. Rank is positive and unique per bank
  transaction; confirmation and PAYMENT evidence may cite only rank 1.
- Only rank-1 `NEEDS_REVIEW` may receive `CONFIRMED`, `REJECTED` or `DUPLICATE` evidence. A PAYMENT
  requires either rank-1 `AUTO_MATCH` or rank-1 confirmed Review evidence.
- Deferred reconciliation requires `credit_cents = amount_cents - assigned_cents` for PAYMENT.
  REVERSAL credit is zero and its allocations negate the original allocations; a full return also
  accounts for the original unallocated credit without fabricating a receivable allocation.
- New allocations carry a complete before/after projection pair. An all-null pair remains legal
  only for legacy compatibility and is insufficient for automatic reversal.
- `IbanHistory.valid_from`/`valid_to` are timezone-aware instants. A newly learned mapping starts at
  the exact confirmation timestamp.
- Rent principal must be classified across base rent, NK advance, heating advance and garage.
  `nk_nachzahlung` principal deliberately carries zero in all four named components, preventing a
  statement balance from being misreported as a paid advance.

The shipped Largest-Remainder tie still refuses and rolls back atomically. Round five now specifies
the versioned order `base_rent`, `nk_advance`, `heating_advance`, `garage`; implementation and its
equal-remainder fixture remain pending.

**`Receivable.stored_reference` is now a legacy placeholder, not the approved target.** Round five
replaces it with nullable `RenterMatchingProfile.sepa_mandate_reference` and
`Receivable.e2e_reference`. The first is unique within the account; the second exists only for a
Lokara-generated collection. Either match contributes the same single 15-point structured-reference
signal, never 30, and it remains additive to a purpose payment code. Until the migration, fixtures
and engine update land, nothing writes these fields and `_end_to_end_signal` correctly returns 0.

#### Closed on `0020`: six invariants the second audit re-run found

**Status:** found 23.08.2026 on `slice/m6-c3-0-invariant-repair`. As of 24.08.2026 all six
findings are repaired and proved on a fresh `0020`: R13–R18 pass, all 21 trigger functions
are hardened, and the full focused repair/RLS set is green. The verified function and trigger
hand-delta and the one missing mixed-sign CHECK are also applied to development. The focused,
full and non-fresh demo gates are green, and the PDF is unchanged. No new legal value is
introduced and no `Rechtsstand` changes.

The distinction matters here more than usual. `0019` was reported complete while two of its
central claims were false, and that is why this slice exists. A migration whose SQL has been
written is not a migration that works.

| Finding | Clause it breaks | Defect proved by the audit | Fixture |
| --- | --- | --- | --- |
| H1 | `docs/15` § 6, "a match never moves money between renters" | The first `enforce_payment_allocation_renter` draft treated a reversal's own proposal and its reversed entry as alternatives, so the proposal could shadow the original renter. The repaired rule makes the reversed payment decide and requires any proposal on the return to agree; § 5.3's valid return shape remains representable. | `M6C3R-R13` |
| H2 | `CLAUDE.md` § 3.3; `docs/15` § 6 | The 21 trigger functions inherited the caller's `search_path`, so `pg_temp` could shadow parent tables. All 21 now set `pg_catalog, public, pg_temp`; the six amended lookup bodies also use `public.*`. | `M6C3R-R14`, `M6C3R-R15` |
| M3-a | `docs/15` § 3.3 | The first confirmation trigger did not tie `learned_from_transaction_id` to the confirmed proposal's transaction. It now requires that exact provenance. Whether `normalized_iban` must equal the movement's `counterpart_iban` remains **not decided** because normalization belongs to the adapter and no source fixes the SQL comparison. | `M6C3R-R16`, `M6C3R-R17` |
| M4 | `CLAUDE.md` § 3.3, "`check_rls_coverage.py` must never be weakened" | **Repaired 24.08.2026.** Check 5's `_DEF = re.compile(r"\n(?:    )?def ")` split only at `def`, so a test's chunk swallowed whatever followed it: a table named only in the next class's docstring was reported write-tested, and `async def test_…` was not a split point at all, so a genuine refused cross-account write was invisible. Test bodies now come from `ast`, so a chunk ends where the test ends. Two regex boundaries leaked before this; a `def` is where the *next* thing starts, not where this one ends. All 38 tenant tables remain covered, so no table's coverage had been resting on glue. | `M6C3R-R20`, `M6C3R-R21` |
| M5 | `docs/15` § 6; `CLAUDE.md` § 3.3 | `BEFORE` parent triggers masked the `payment_allocation` and `iban_history` RLS policies. The three affected triggers now run `AFTER`, so `WITH CHECK` refuses a foreign write first while the triggers still fail closed for same-account defects; the cap retains its `FOR UPDATE` lock. | `M6C3R-R18` |
| M6 | `docs/15` § 5.1 | Repaired in this slice: the settled-receivable test tripped `ck_receivable_open_components` first and matched the word "settled" in the failing row's DETAIL, so `ck_receivable_settled_has_nothing_open` was never exercised. It now uses `open_cents = open_principal_cents = 0` with open costs and asserts the constraint name. | `M6C3R-R19` |

| Financial record | Current contract and owner |
| --- | --- |
| `AdvancePaymentPeriod` | Shipped M6-A: account, tenancy, amount, effective dates and version/declaration evidence. |
| `Receivable` | Shipped M6-B as `StatementSettlement`: account, finalized statement/version, tenancy, amount and immutable origin; it is not a cash event. |
| Payment event/ledger entry | M6-C2 ships `PaymentLedgerEntry` + `PaymentAllocation`. M7 materializes accepted components idempotently into immutable `TaxEvent` rows with account/building, identity-free optional unit, nullable payment/due date and category, cents, direction, receipt reference, source enum, version, component/allocation provenance and append-only correction lineage. Missing date is red; missing category is yellow. |
| Matching evidence | Shipped M6-C2 as `BankTransaction`, `MatchProposal`, `MatchConfirmation` and `IbanHistory`: normalized transaction, accepted allocation/proposal, versioned IBAN-to-renter link, duplicate/reversal history and reviewer decision where required. |
| `TaxMappingVersion` | Migration `0024`: immutable tax-year mapping snapshot with version, source, `Rechtsstand`, production block and same-year successor. All runtime lines/accounts remain blocked placeholders. |
| `TaxAdviserProfileVersion` | Migration `0024`: immutable adviser/client number, chart, account length and fiscal-year start snapshot; only owner/adviser profile writes are permitted by the API. |
| `TaxExportReadinessAttempt` | Migration `0024`: immutable object/year/kind input references, ordered findings, acknowledgements/override evidence, blockers and generated/blocked result. |
| `TaxExportArchive` + `TaxExportArtifact` | `0024`: stable account/building/year/kind stream, readiness reference, version/successor, exact bytes, `Rechtsstand` evidence, timestamp and hashes. The server generates the bytes and freezes them; a caller can never supply them. Runtime DATEV remains blocked pending official-format and real-import verification. |

### M7 record set

Migration `0024_m7_afa_tax_export.py` creates
`afa_record_version`, `tax_event`, `tax_adviser_profile_version`, `tax_mapping_version`,
`tax_export_readiness_attempt`, `tax_export_archive` and `tax_export_artifact`. Every table carries
`account_id`, forced RLS and a `WITH CHECK` policy; cross-account edges are composite, financial
evidence is append-only, and archive bytes are immutable. Deferred M7-F repairs are integrated on
`development`, but their closure reviews and verification remain open.

### Integrated M9 record set

Migration `0025_m9_guard_delivery.py` creates ten account-scoped, forced-RLS records: immutable
guard evaluations, reminders and resolutions, versioned default-off schedules, frozen renter
artifacts with SHA-256, email attempts and status events, bounce/complaint suppression events,
checklist instances and append-only item events. Composite foreign keys bind every building,
tenancy, renter, artifact and actor context. Provider delivery status is not legal receipt. This
record set is technically closed and review-clean on `development` as of 29.08.2026; production
blockers remain. The later checkpoint's gates are separate evidence, recorded in `PLAN.md`.

The statement's Saldo is BGH formal minimum #4. It must use **geleistete** advances from accepted
payment allocations, not `advance_payment_cents × months`. The temporal Soll schedule is still
needed to identify arrears and explain what was due, but it does not prove what was paid.

This separation fixes the former ambiguous phrase “statements feed the ledger”: a statement creates
an obligation; an actual payment creates the cash-basis ledger event. M6 owns bank matching,
versioned IBAN-to-renter mappings and the temporal Soll schedule needed to compare what was owed
with what moved. M7 consumes the accepted ledger snapshot and owns the separate tax-export archive.
Approved `docs/11` remains the contract; its migration and API code are locally merged and green,
with M7-F's read-only reviews still open.

## 7. Known gaps and milestone ownership

| Gap or boundary | Status | Owner |
| --- | --- | --- |
| Secure pre-context identity read (`app_bootstrap_contexts`, migration `0014`) | **Shipped** on `main` | M5 foundation |
| Role behavior, switcher, assigned-building enforcement, nested-route authorization and the no-`renter.person_id`-writer guard | **Shipped** on `main` | M5 (`a748729`) |
| Page 01 persisted calculation/extraction reconciliation | **Specified and approved**; production gaps remain | Slice B |
| Page 02 catalogue, classifications, NK half-up rounding and owner residual | Technically implemented by Slice C; flagged authority remains production-blocking | Slice C |
| Page 08 bank-matching specification | **Approved and merged** in `docs/15`; F03 resolved with all thirteen oracle cases executable | D2 / `docs/15` |
| M6-A temporal advances/confirmed actual advances and M6-B Saldo, settlements, finalization and owner-only archives | **Shipped** technical scope; no renter delivery or legal-production approval | M6-A/M6-B |
| Payment ledger, bank matching and matching evidence | **Shipped on local `main` through C3a**; service/final `0021` technically complete and development-synchronized | M6-C1/M6-C2/M6-C3-0/M6-C3a |
| Three matching jobs | **Locally merged**; no schema change, read through an account-scoped session only | M6-C3b |
| Landlord *Zahlungen* screen | **UI-07 demo core implemented on `development`; partial, with automated and focused review evidence**. Unified server read model, account/consent status, filters, pagination, proposal confirmation and append-only single/bulk ignore are live. Manual payment/assignment, anomaly engine, complete shared aggregates and the live-browser matrix remain unfinished or source-blocked. | UI-07 / M6-C3c |
| W1–W8 guards, reminders, email delivery and checklists | **Technically closed 29.08.2026 on `development`** with migration `0025`, account-scoped jobs/API and `/waechter`; delivery defaults off and real execution remains blocked | M9 / `docs/12` |
| U1–U5 monthly UVI calculation, adapters, persistent evidence/run archive and separate owner-downloadable renter document | **Technically implemented**, including later GAS/warm-water extensions; M9 scheduling on `development` refuses UVI delivery because immutable PDF bytes and production authority are missing | U1–U5 / M9 / `docs/16` |
| Renter portal publication | **Specified by M10-R0; not implemented** | M10-R3/R4 |
| Renter activation-code redemption, renter context and portal isolation | **Specified by M10-R0; not implemented** | M10-R1/R2 |
| Mid-year self-use/rental change for AfA apportionment | Merged normalized M7-A code selects month-granular 453,798 ct and separately returns object/deductible/non-deductible AfA; K09 authority remains `verify-before-production` | `docs/10-afa.md` / M7 |
| Page 04 Anlage-V/DATEV export contract | Pure engine, rules, schema, web and the server-generated artifact/API adapter are locally merged and green; runtime output stays blocked while its register values remain `verify-before-production` | M7 / `docs/11-tax-export.md` |
| Page 06 clause selection, risk and workflow-routing contract | Complete transcription approved and merged 21.08.2026; no schema, clause bodies, letter bodies or production implementation, and the missing text catalogues still block M8 | `docs/13-contract-clauses.md` / M8 |
| `Verteilungsrest (K9)` authoritative register wording | Unresolved source issue; repository copy remains untouched | Next authoritative register export |

Other later temporal or immutable records arrive only with their owning milestones: separate
normalized `Loan`/work-detail tables beyond the AfA snapshot, `LettingEffort`, tickets,
subprocessors, activation codes, clause/contract versions and prospect objects. Paused M9 work on
`development` creates guard/reminder and delivery records but does not authorize production delivery.
`docs/13` defines only their future logical references, composition evidence and risk routing; it
does not approve a schema or provide clause text. `docs/14` likewise defines only the future
Prüfobjekt snapshot, provenance, partial-result, annuity, sensitivity and Bank-PDF boundaries; it
approves no prospect schema. Their names in this inventory do not approve their final schemas.
