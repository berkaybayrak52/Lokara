# 02 — Data model

> Condensed from `lokara-arch.md` §2/§3/§8. That file has the full reasoning; this is the build spec.
> **Principle:** anything that can change *during* a period is a row with `validFrom/validTo`, never a
> scalar. Money is integer **cents**. Every domain row carries **`accountId`**.

## Identity: the three-layer model

Do **not** put roles on the Account. Split identity into three layers so one Person can hold many
roles across accounts at once.

1. **Person** — the login (one human). Global, not owned by any account. Maps onto Supabase Auth.
2. **Account** — workspace + subscription + **isolation boundary** (*who pays*). Has a **shape**:
   `SOLO` or `HAUSVERWALTUNG` (a property of the account, not a personal role).
3. **Membership** — links Person → Account, carrying a **Role**. A Person holds many Memberships.

### Roles
- `OWNER` — full account: billing, roles, bank, all buildings. ("Admin bei HV" = OWNER in a HV account.)
- `EMPLOYEE` — only **assigned buildings** (object-level scope). Zero assignments ⇒ sees nothing.
- `TAX_ADVISOR` — read-only guest on a client's account (tax/export + AfA).
- `RENTER` is **not** in the Role enum — a renter is domain data scoped to a **Tenancy**; portal
  access is just `Renter.personId` pointing at a Person.

Not peer roles: **Hausverwaltung** = an account *shape*; **Landlord (Vermieter)** = a *data entity*
(the legal lessor on statements), separate from the person operating it.

### Prisma (identity + relationships — verified: 9 models, 3 enums, no orphans)

```prisma
// ── Layer 1: Identity — global ──
model Person {
  id          String       @id @default(cuid())
  email       String       @unique
  name        String?
  createdAt   DateTime     @default(now())
  memberships Membership[]
  renterLinks Renter[]
}

// ── Layer 2: Account — workspace + billing + isolation ──
model Account {
  id          String       @id @default(cuid())
  name        String
  shape       AccountShape @default(SOLO)
  plan        Plan         @default(TRIAL)
  createdAt   DateTime     @default(now())
  memberships Membership[]
  landlords   Landlord[]
  renters     Renter[]
}
enum AccountShape { SOLO HAUSVERWALTUNG }
enum Plan { TRIAL SOLO_S SOLO_M SOLO_L TEAM PRO ENTERPRISE }

// ── Layer 3: Membership — Person → Account, carrying a Role ──
model Membership {
  id         String    @id @default(cuid())
  personId   String
  person     Person    @relation(fields: [personId], references: [id])
  accountId  String
  account    Account   @relation(fields: [accountId], references: [id])
  role       Role
  invitedAt  DateTime  @default(now())
  acceptedAt DateTime?
  revokedAt  DateTime?               // revoke, never hard-delete (audit)
  buildings  BuildingAssignment[]    // only meaningful for EMPLOYEE
  @@unique([personId, accountId])    // DECISION: one role per person per account (start strict)
  @@index([accountId])
}
enum Role { OWNER EMPLOYEE TAX_ADVISOR }   // no RENTER by design

model BuildingAssignment {
  id           String     @id @default(cuid())
  membershipId String
  membership   Membership @relation(fields: [membershipId], references: [id], onDelete: Cascade)
  buildingId   String
  building     Building   @relation(fields: [buildingId], references: [id])
  @@unique([membershipId, buildingId])
}

// ── Vermieter: DATA entity (legal lessor), not a role ──
model Landlord {
  id        String     @id @default(cuid())
  accountId String
  account   Account    @relation(fields: [accountId], references: [id])
  legalName String
  address   String
  buildings Building[]
  @@index([accountId])
}

// ── Mieter: domain entity; portal login OPTIONAL via personId ──
model Renter {
  id        String    @id @default(cuid())
  accountId String
  account   Account   @relation(fields: [accountId], references: [id])
  legalName String
  email     String?
  personId  String?              // set = this renter can log into the portal
  person    Person?   @relation(fields: [personId], references: [id])
  tenancies Tenancy[]
  @@index([accountId])
  @@index([personId])
}
```

### Decisions the schema makes explicit
1. `@@unique([personId, accountId])` — one role per person per account (relaxing later is trivial;
   tightening after real data is not).
2. `RENTER` is domain data (Tenancy-scoped), not a Membership role → no polymorphic nullable-scope table.
3. `EMPLOYEE` with zero `BuildingAssignment` sees nothing (deny by default).
4. Memberships are **revoked** (`revokedAt`), never deleted (GoBD + DSGVO).
5. Every domain row carries `accountId` — that column **is** the isolation boundary.
6. `Person` is global; Supabase Auth owns credentials and maps onto Person.

### Portals & active context
- Derive the menu from `person.memberships` + `person.renterLinks` **live** — never store a
  "has renter portal" flag.
- Show the context switcher **only** when a Person holds >1 context (solo users get dropped straight in).
- **Carry context in the URL**, not the session: `/a/{accountId}/…` (owner/employee/StB),
  `/renter/{tenancyId}/…` (renter). Survives tabs/refresh/bookmarks.
- **Menu is navigation, not authorization.** Every request independently verifies the Person holds the
  relationship in the URL, then scopes the query. Enforced twice: app logic **and** Postgres RLS.

## Temporal core: Building → Unit → Tenancy
`Building 1─N Unit 1─N Tenancy`. Tenancy has `validFrom/validTo`; multiple renters per tenancy
(multi-party leases are an entry-ticket requirement). Statements are **immutable** — new version, never edit.

## Eigennutzung (self-use) is NOT a Renter
A unit is in exactly one state at any moment:

| State | Source | NK treatment | Tax treatment |
|---|---|---|---|
| `RENTED` | active `Tenancy` | allocated to renter | income + deductible costs |
| `SELF_USED` | explicit `SelfUsePeriod` (m²) | falls on landlord | private — not deductible, reduces AfA base |
| `VACANT` | **derived** (neither above) | falls on landlord | costs stay deductible while rental intent is demonstrable |

Only `SELF_USED` is stored; `RENTED` derives from tenancies; `VACANT` is the remainder — one source of
truth per state so they can't drift.

```prisma
model SelfUsePeriod {
  id        String      @id @default(cuid())
  unitId    String
  unit      Unit        @relation(fields: [unitId], references: [id])
  sqmX100   Int         // self-used m² × 100 — an AREA, not a flag
  kind      SelfUseKind @default(OWNER_OCCUPIED)
  note      String?
  validFrom DateTime
  validTo   DateTime?
  @@index([unitId])
}
enum SelfUseKind { OWNER_OCCUPIED FREE_OF_CHARGE }
```
- Self-use is an **area with a period** (m²), not a boolean — covers partial cases (a rented room).
- **Invariant:** a day may never be both `RENTED` and `SELF_USED` — reject overlaps on write.
- **verbilligte Vermietung** (below-market to family, §21 Abs. 2 EStG) is a *real* Tenancy — flag to a
  StB, don't model as self-use.
- **To specify before AfA:** mid-year Nutzungswechsel needs month-accurate AfA apportionment.

## Allocation keys
```prisma
enum AllocationKey {
  AREA         // Fläche
  PERSONS      // Personen
  CONSUMPTION  // Verbrauch (metered)
  UNITS        // Einheiten
  DIRECT       // Direktzuordnung — cost to exactly one unit/tenancy
  MEA          // Miteigentumsanteil (WEG)
}
```
- **`DIRECT` is mandatory** (a repair inside flat 3 bypasses proportional allocation).
- Keys must be **freely changeable without deleting entered data** (named pain point at objego AND
  immocloud). The key lives on a **per-period `AllocationKeyAssignment`**, never on the cost row —
  changing a key re-runs the calc and cascades into no stored data.
- **Granularity:** NK allocates at **unit/tenancy** level; **AfA splits by m²** — two granularities on purpose.

## Two financial time-axes (never merge)
- **NK billing = accrual/period-based.** Costs belong to an *Abrechnungszeitraum*; day-weighted;
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
