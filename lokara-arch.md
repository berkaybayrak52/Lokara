# Lokara — Architecture (v3, aligned with the canonical Notion)

---

## Terms (new/changed since v1)

- **AVV** — *Auftragsverarbeitungsvertrag* (GDPR Art. 28 data-processing agreement). Lokara is the customer's processor; a hard sales blocker if missing.
- **AISP / PSD2 / AIS** — licensed Account-Information-Service-Provider under PSD2; AIS = read bank transactions. Lokara consumes finAPI's licence, does not hold its own.
- **Ledger** — the single append-only record of money movements (cash-basis), source of truth for tax exports.
- **Accrual vs cash basis** — NK billing is *accrual* (costs belong to a billing period); tax is *cash* (income/expense belong to the year money moved, §11 EStG). Two different time models — see §3.
- **RBAC** — Role-Based Access Control (who may do what).
- **Entitlement** — whether a feature is unlocked, driven by the subscription plan (*Tarif*).
- **UVI** — *unterjährige Verbrauchsinformation*: monthly consumption info owed to tenants with remote-read meters (§6a HeizkostenV).
- **MDL** — *Messdienstleister*: metering service (Techem, ista…). Data exchanged via the ARGE/bved HeiWaKo standard.
- **Eichfrist** — legal calibration validity of a meter (heat 5 yrs, water 6 yrs) — must be tracked.
- **GoBD / §147a AO** — German bookkeeping/retention rules; drive immutable archives and retention (up to 6–10 yrs).
- **BFSG** — *Barrierefreiheitsstärkungsgesetz*: accessibility law in force since 28.06.2025 → WCAG 2.1 AA is a real requirement, not nice-to-have.

---

## 1. Stack — verdict after the Wiki

Unchanged and validated. The breadth (many backend subsystems, integrations, background jobs)
actually *strengthens* two earlier calls: a **structured NestJS backend** (modular per domain)
and a **monorepo of pure engine packages**. Additions in **bold**.

| Category | Pick | Wiki-driven note |
|---|---|---|
| Language | **TypeScript** everywhere | Money math lives in isolated, tested packages — decimal-lib + integer cents. |
| Repo | Turborepo monorepo | Now hosts *several* engine packages (nk, heating, afa, export) + adapters. |
| Web | Next.js + React + Framer Motion | Apple-like polish, **but WCAG 2.1 AA / BFSG is mandatory** (see §9). |
| Mobile | **Native iOS/Android at public launch** (Expo/RN; Capacitor/PWA fallback) | ⚠️ **Not "later" anymore** — Wiki says web-app until 25.07, then web **+ native apps together** at the Sept launch. |
| Backend/API | **NestJS** | Complex domain logic, integrations, webhooks, workers — sits *on top of* Supabase. |
| **Platform / DB / Auth / Storage** | **Supabase** (Postgres + Auth + Storage + RLS) | ⚠️ **Wiki decision** (Mieterportal page): Supabase Auth gives password + magic-link + verification + reset out of the box. Supplies Postgres, file storage, and **Row-Level Security** as the isolation backstop. |
| ORM | Prisma (against Supabase Postgres) | Migrations/DX; RLS enforces the §2 boundary underneath. |
| **Background jobs** | Graphile Worker / BullMQ | finAPI sync, 180-day reconsent cleanup, monthly UVI, deadline watchers, email retries. |
| **Transactional email** | **Modell A: Lokara is technical sender** — own domain `@lokaraimmo.de`, SPF/DKIM/DMARC, From-name = landlord | Provider: SES Frankfurt / Postmark / Brevo (EU, sub-processor). It's a **compliance-grade delivery subsystem**, not just "send mail" — see §4. |
| **Subscription billing** | **Stripe (SEPA) — to confirm** | Plan brackets + seats + add-ons; PAngV/Brutto display. Decide vs an EU-native like Paddle/Chargebee. |
| **AI / OCR / Vision** | **provider with EU processing + AVV** | Anschreiben generation **and** the doc-extraction pipeline (Beleg-OCR + migration) — **now V1/Pitch-MVP**, not later. |
| PDF | HTML→PDF (headless Chrome) / Typst | One shared document service: NK, UVI, AfA dossier, Anlage V, contracts. |
| Hosting | EU/DE | DSGVO: EU/DE hosting is the operating licence, not a preference. |

**⚠️ Supabase vs the Datenschutz page — the one real tension to resolve.** The Wiki commits to
Supabase, but the Datenschutz page is strict: *"Hosting in EU/Deutschland"* and *"a non-EU
sub-processor without guarantees = compliance break."* Supabase Inc. is US-headquartered. Two clean
resolutions:

- **Supabase Cloud, EU region (Frankfurt) + signed DPA**, listed as sub-processor in your AVV. Fast, but a US company remains in the chain — must be justified and disclosed.
- **Self-hosted Supabase on Hetzner** (it's open source) — full EU control, satisfies the page literally, more ops burden.

Pick one *before* onboarding real tenant data; it's an AVV/sub-processor-register question, and your
own page makes it a sales blocker if wrong. Everything else (NestJS + Prisma + pure engines on top,
RLS as defense-in-depth) works identically either way.

**Still open, both gated by GDPR sub-processor acceptability:** subscription-billing provider and the
AI/Vision provider. Flag, don't hardcode.

---

## 2. Identity, accounts & roles — the three-layer model

v1 had `Organization + User` — too flat. The Wiki needs solo landlords *and* Hausverwaltungen from
day 1 and, critically, **one person must be able to hold several roles at once** (a landlord who also
rents a flat elsewhere and does a friend's taxes). The fix: stop treating "role" as a property of the
Account, and split the model into three layers.

> ⚠️ **Naming trap:** "tenant" is overloaded. In SaaS, *tenant* = the isolated paying customer. In
> German rental law, *Mieter* = the renter. This doc uses **Account** (SaaS customer) and **Renter**
> (Mieter). Never call a renter a "tenant" in the schema.

### The three layers

1. **Person** — the login (one human, one identity). Global; not owned by any account.
2. **Account** — the workspace + subscription/isolation boundary; *who pays*. Every row is scoped by `accountId`. An Account has a **shape**: `SOLO` or `HAUSVERWALTUNG` — a property of the account, not a personal role.
3. **Membership (relationship)** — links a Person → a scope, carrying a **Role**. A Person holds *many* Memberships at once, across different accounts. **Roles live here — never on the Account.**

### Roles

Inside a paying account:

- `OWNER / ADMIN` — full account: billing, roles, bank, all buildings; can promote employees. ("Admin bei HV" is just this role in a `HAUSVERWALTUNG` account.)
- `EMPLOYEE` — only **assigned buildings** (object-level scope). ("Mitarbeiter bei HV" = this role.)

Cross-account relationships (same Person, other scopes):

- `RENTER` (Mieter) — scoped to **one Tenancy** in someone else's account; portal only (tickets, rent-due, meter self-readings). No seat cost, zero visibility into the landlord side.
- `TAX_ADVISOR` (Steuerberater) — read-only guest on a client's account; sees tax/export + AfA, edits only the StB profile.

Two things that are **not** peer roles:

- **Hausverwaltung** = an account *shape*, not a personal role.
- **Landlord** (*Vermieter*) = also a **data entity** (the legal lessor whose name is on statements/contracts), separate from the person operating it. Solo: one Person = Owner = the single `Landlord`. HV: many `Landlord` entities managed by staff, who may not be app users. (`Account 1─N Landlord 1─N Building`.)

### One person, many roles at once (what you asked for)

Explicitly supported. Person "Emir" can hold **three roles simultaneously**, each in a different scope, on one login:

| Context (scope) | Role |
|---|---|
| His own `SOLO` account | Owner + Landlord |
| A flat he rents, in another landlord's account | Renter |
| A client's account (he's their StB) | Tax advisor (guest) |

The **Person** has three roles; no single Account holds all three. They hang off three Memberships.
Add a fourth later (Owner of a second, Hausverwaltung account) and nothing breaks.

### Schema (Prisma)

Relation symmetry verified (9 models, 3 enums, 22 relation fields, no orphans).

```prisma
// ── Layer 1: Identity — global, not owned by any Account ──
model Person {
  id          String       @id @default(cuid())
  email       String       @unique
  name        String?
  createdAt   DateTime     @default(now())
  memberships Membership[]   // roles inside paying accounts
  renterLinks Renter[]       // portal access to tenancies elsewhere
}

// ── Layer 2: Account — workspace + billing + isolation boundary ──
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
  revokedAt  DateTime?          // revoke, never hard-delete (audit trail)
  buildings  BuildingAssignment[]   // only meaningful for EMPLOYEE

  @@unique([personId, accountId])   // DECISION: one role per person per account
  @@index([accountId])
}

enum Role { OWNER EMPLOYEE TAX_ADVISOR }   // note: no RENTER — see below

model BuildingAssignment {
  id           String     @id @default(cuid())
  membershipId String
  membership   Membership @relation(fields: [membershipId], references: [id], onDelete: Cascade)
  buildingId   String
  building     Building   @relation(fields: [buildingId], references: [id])

  @@unique([membershipId, buildingId])
}

// ── Vermieter: a DATA entity (legal lessor), not a role ──
model Landlord {
  id        String     @id @default(cuid())
  accountId String
  account   Account    @relation(fields: [accountId], references: [id])
  legalName String     // the name printed on statements & contracts
  address   String
  buildings Building[]

  @@index([accountId])
}

// ── Mieter: domain entity; portal login is OPTIONAL via personId ──
model Renter {
  id        String    @id @default(cuid())
  accountId String              // lives inside the landlord's account
  account   Account   @relation(fields: [accountId], references: [id])
  legalName String
  email     String?
  personId  String?             // ← set = this renter can log into the portal
  person    Person?   @relation(fields: [personId], references: [id])
  tenancies Tenancy[]

  @@index([accountId])
  @@index([personId])
}
```

### The decisions this schema makes explicit

Prose hid these; the schema forces an answer. Each is deliberate:

1. **`@@unique([personId, accountId])` — one role per person per account.** Starting strict: you can't be both Owner and Employee in the same account. Relaxing a unique constraint later is trivial; tightening one after real data exists is not.
2. **`RENTER` is not in the `Role` enum.** A renter is *domain data* (the name on the lease) that exists whether or not they ever log in, and its scope is a **Tenancy**, not an Account. So portal access is just `Renter.personId` pointing at a Person. This avoids a polymorphic Membership with nullable scope columns — the design that quietly breeds bugs.
3. **An `EMPLOYEE` with zero `BuildingAssignment` rows sees nothing.** Deny by default; access is granted per building, never assumed.
4. **Memberships are revoked (`revokedAt`), never deleted.** Who had access when is audit-relevant (GoBD + DSGVO).
5. **Every domain row carries `accountId`.** That column *is* the tenant-isolation boundary — scope every query by it.
6. **`Person` is global.** Better Auth owns the credential tables and maps onto `Person`; identity is never nested under an Account.

**Tradeoff to know:** "all my roles" is now two lookups — `person.memberships` (Owner/Employee/TaxAdvisor) plus `person.renterLinks` (Renter). That's honest, because they genuinely are different relationship types. If you later want one unified feed for a role-switcher UI, build a read view over both rather than merging the tables.

### Emir's three roles, as actual rows

| Table | Row |
|---|---|
| `Person` | `Emir` |
| `Membership` | `(Emir, Account A, OWNER)` — his own solo account |
| `Landlord` | `(Account A, "Emir …")` — the lessor entity on his statements |
| `Renter` | `(Account B, "Emir", personId = Emir)` → `Tenancy` in B — the flat he rents |
| `Membership` | `(Emir, Account C, TAX_ADVISOR)` — his client |

One `Person`, three roles, three scopes, no duplicate accounts.

### Eigennutzung is *not* a Renter (important trap)

If a landlord lives in one of their own units — or a unit is otherwise owner-occupied — **never create
a `Renter` row pointing at them.** It looks like the same thing in the UI and is wrong in two
expensive ways:

- **NK allocation** would treat them as a paying tenant, so their share gets billed out instead of landing on the landlord side (where vacancy-style costs belong).
- **AfA** is overstated — self-used area reduces the depreciation base proportionally (the *Teilvermietung* logic in the AfA-Wizard spec).

**Model it as unit state over time instead.** At any moment a Unit is in exactly one of three states:

| State | Source | NK treatment | Tax treatment |
|---|---|---|---|
| `RENTED` | an active `Tenancy` | allocated to that renter | income + deductible costs |
| `SELF_USED` (*Eigennutzung*) | an explicit `SelfUsePeriod` | falls on the landlord | **private** — not deductible, reduces AfA base |
| `VACANT` (*Leerstand*) | **derived** — neither of the above | falls on the landlord | costs generally stay deductible while rental intent continues |

Only `SELF_USED` is stored; `RENTED` comes from tenancies and `VACANT` is whatever's left. One
source of truth per state, so they can't drift apart.

**Decision: self-use is an area with a period, not a flag.** AfA and cost deduction are split by
**m²** (Flächenschlüssel) — the self-used area is removed from the base. Storing m² rather than a
boolean also covers partial cases (a rented-out room, an Einliegerwohnung) with no model change.

```prisma
// Eigennutzung — owner-occupied AREA over time. Never a Renter row.
model SelfUsePeriod {
  id        String      @id @default(cuid())
  unitId    String
  unit      Unit        @relation(fields: [unitId], references: [id])
  sqmX100   Int         // self-used m² × 100 — not a flag
  kind      SelfUseKind @default(OWNER_OCCUPIED)
  note      String?
  validFrom DateTime
  validTo   DateTime?

  @@index([unitId])
}

enum SelfUseKind {
  OWNER_OCCUPIED   // Eigennutzung — the landlord lives there
  FREE_OF_CHARGE   // unentgeltliche Überlassung, e.g. to a family member
}
// Unit gains the back-relation:  selfUsePeriods SelfUsePeriod[]
```

Three notes on this shape:

- **Why `kind` is an enum, not free text.** `OWNER_OCCUPIED` and `FREE_OF_CHARGE` are taxed the same *today* (no income → no deduction), but an enum is queryable, validatable, and lets the two diverge later. A note field can't be reported on. Costs nothing now.
- **`verbilligte Vermietung` does not belong here.** Renting to family below market rent is a *real* `Tenancy` with tax consequences (§21 Abs. 2 EStG thresholds) — flag it to a Steuerberater, don't model it as self-use.
- **AfA and NK deliberately use different granularity.** AfA splits by **m²**; NK allocates by **unit**. Don't force one model onto both. The edge case where one unit is *simultaneously* part self-used and part let to a separate tenancy is rare and not modelled in V1.

**Still to specify:** mid-year **Nutzungswechsel** (self-used Jan–Jun, then rented Jul–Dec) needs
**month-accurate** AfA apportionment, matching the existing first-year rule. The data model already
carries it via `validFrom/validTo`; the engine logic does not exist yet. Define it before building
the AfA module — a landlord moving out of their own flat and letting it is a common case.

**Vacancy has a condition.** Costs stay deductible during `VACANT` only while rental intent is
**demonstrable** (documented letting efforts — listings, ads, agent instructions); long vacancy
without visible effort can lose the deduction. Since Lokara already derives vacancy, the Leerstand-
Wächter should prompt the landlord to log those efforts as evidence against the vacancy period.

**Invariant to enforce:** a day may never be both `RENTED` and `SELF_USED` — reject overlapping
periods on write, don't discover it at billing time.

**Why the vacancy/self-use split matters.** Example — Unit B in 2025: rented Jan 1–Jun 30 (181 d),
empty Jul 1–Aug 31 (62 d), owner-occupied Sep 1–Dec 31 (122 d). For **NK**, both the 62 and the 122
days land on the landlord and look identical. For **tax** they diverge: the 62 vacant days' costs
generally remain deductible (rental intent continues), while the 122 self-used days are private use.
Collapse the two states into one and the NK statement still looks right while the tax export is
quietly wrong.

> Related but different, and not modelled in V1: **verbilligte Vermietung** (renting to family below
> market rent — §21 Abs. 2 EStG thresholds affect deductibility). That *is* a real tenancy, just with
> tax consequences. Flag to a Steuerberater rather than computing it. *(Tax specifics here should be
> confirmed with a StB before shipping — this is a modelling note, not tax advice.)*

### Consequences to design in now

- **Unify identity — no separate "renter user" table.** The renter portal is a permission *scope* on the same Person primitive; that's what lets a Vermieter also be a Mieter. **`Person` maps onto Supabase Auth** (password + magic-link on the same account, per the Mieterportal page).
- **Authorize per-relationship, on every request.** One login carries landlord *and* renter contexts — a renter context exposes **zero** landlord data and vice versa. Enforce it twice: in app logic **and** in **Postgres RLS** (the Supabase isolation backstop). See *Portals & active context* below.
- **Entitlements are a separate axis.** `Tarif` (plan) unlocks *features*; `Role` grants *permissions*. Keep them independent — don't collapse into one "account type".

### Portals & active context

Each role gets its own dashboard in the left-hand menu — "Vermieter Portal", "Renter Portal",
"Steuerberater Portal". Four rules govern this:

1. **Derive the menu from the Person's relationships, live.** Build it from `person.memberships` + `person.renterLinks` on each load. Never store a "has renter portal" flag — it drifts out of sync the moment a membership is revoked.

2. **Hide the switcher when there is only one context.** Most users are solo landlords with exactly one portal; a switcher is pure noise for them and fights the "understandable from 7 to 70" design goal. Render it only when the person holds **more than one** context — otherwise drop them straight into their single portal.

3. **Carry the context in the URL, not the session.**
   - `/a/{accountId}/…` — Owner / Employee / Tax-advisor portals
   - `/renter/{tenancyId}/…` — Renter portal

   A portal menu invites people to open two tabs at once (landlord in one, renter in the other).
   Session-stored "current context" breaks exactly there; URL-carried context survives tabs,
   refreshes and bookmarks. Same pattern as Slack/Notion/Linear putting the workspace in the URL.

4. **The menu is navigation, not authorization.** Hiding a link protects nothing — if the endpoint still answers when called directly, the data is still exposed. That is the most common multi-tenant security bug. Every request must **independently** verify that this Person actually holds the relationship named in the URL, then scope the query to it. Enforced twice, independently: once in the UI, once in the API.

### Renter activation & lifecycle (per the Mieterportal page)

The renter portal is now fully specced — fold these into the model:

- **Activation code is bound to the Tenancy, not the physical unit** — so a new tenant never sees the previous tenant's data. One code **per person** in the tenancy (n parties → n codes), each single-use, expiring, revocable; correct code **auto-links** (no landlord confirmation click).
- **Two onboarding paths, both live:** QR/code at contract signing (new tenancies) *and* bulk existing-tenant onboarding (serial letter / email / a leaflet with the NK statement). At launch, bulk is the **main** path — nearly all renters are existing.
- **Shared vs personal data:** documents + UVI = shared across all parties; tickets = shared with visible author; "Meine Daten" = per-person. IBAN changes are **versioned, never overwritten** (SEPA return windows + finAPI matching), and edits are audit-logged with landlord notification.
- **Move-out = two clocks** (see §6): portal *access* ends after the §556 window (final NK statement + buffer); *data deletion* runs separately per retention class. New tenant gets a fresh code; no access to prior tenant's data.

### Not a role: MeinHandwerker

Handwerker is a **separate, independent product** (own app, data, users), reached from Lokara via a
signed **token handoff** (a Mieter clicks "find a Handwerker" → redirect with a signed token that
pre-fills/auto-provisions on the other side). It is **not** a role in Lokara's model — an external
integration seam, defined later. Lokara's auth should be *able* to mint that token (cheap insurance),
without building MeinHandwerker or a shared identity provider now.

---

## 3. The two financial time-axes (the subtle, important one)

Lokara runs **two different accounting time models on the same data** — conflating them is the
classic bug:

- **NK billing = accrual / period-based.** Costs belong to an *Abrechnungszeitraum*; allocation is day-weighted; vacancy → landlord. (The v1 engine.)
- **Tax = cash basis.** Income/expense belong to the *year the money moved* (§11 EStG Zufluss/Abfluss), with the **10-day rule** around New Year for recurring rent. Driven by **payment date**, not billing period.

They meet in one place: **an NK statement's result (Nachzahlung/Guthaben) becomes a Payment in the
Ledger** when it's actually paid. So statements feed the ledger; the ledger feeds tax. Keep them as
distinct subsystems with a clear handoff, not one tangled model.

### Payment Ledger (new subsystem — source of truth for tax)

- `Payment`: **date (mandatory)**, amount (cents), direction (in/out), account/landlord/building/unit/renter, category, **source** (finAPI | manual | invoice), receipt ref, **version history**.
- `TaxCategoryMapping`: category → Anlage-V line (**year-versioned**) + SKR03 + SKR04. Defaults shipped, overridable by the StB.
- Splits (rent = Kaltmiete + NK-Vorauszahlung), pass-through items (deposits ≠ income), all live here.
- **Export = pure deterministic function** `f(ledger, mapping, params) → file`. No state in the generator → byte-exact golden tests. DATEV EXTF is **Windows-1252**, semicolon, CRLF (encoding is the #1 footgun).
- **Export archive**: every generated file stored immutably with hash + timestamp (GoBD).

---

## 4. Subsystem map

Each is a NestJS module; each heavy calculation is a **pure engine package** the module calls.
The spine is always **adapters at the edges → normalized internal models → pure engine → immutable, versioned records**.

| Subsystem | Core idea | Engine/adapter |
|---|---|---|
| **NK / operating-cost** | Day-weighted allocation, vacancy→landlord, largest-remainder rounding | `packages/nk-engine` (pure) |
| **Heating** | §§7/8 HKVO 30/70–50/50 split, §9 WW separation, §9a estimation, degree-days on renter change, CO₂ 10-step | `packages/heating-engine` (pure) |
| **Meter ingestion** | One **normalized `MeterReading`**; 3 inputs: manual, MDL (ARGE HeiWaKo), Funk-Selbstabrechner (CSV/REST). **Adapter pattern — the engine never knows the source.** Device mgmt incl. **Eichfrist tracking** | `ImportSource` + adapters |
| **UVI** | Monthly consumption info to renter portal (§6a); later send-module with **append-only send-log** + PDF snapshot | job + document service |
| **Bank (finAPI AIS)** | Consume finAPI (PSD2 licence). **Store transactions + IBAN→Renter mappings in our own DB** (finAPI users get deleted at consent expiry). Fuzzy matching (IBAN/amount/purpose) → payment status. 180-day reconsent + cleanup job | matching engine + workers |
| **Tax export** | Anlage V (PDF+CSV) + DATEV EXTF from the Ledger; Readiness-Check before export | `packages/export-engine` (pure) |
| **AfA** | Depreciation record per object (versioned, source-tagged); BMF Kaufpreisaufteilung; **15%-Wächter** budget tracker; **Loan** entity w/ amortization → interest prefill + reminders | `packages/afa-engine` (pure) |
| **Investment add-on** | **Prüfobjekt** (prospect object — a distinct entity from a managed `Building`) → Kanban pipeline → on purchase becomes a `Building` with no re-entry. 7-KPI cockpit (Nettorendite, EK-Rendite, DSCR, Cashflow-nach-Steuer, Break-Even-Miete…); **computed annuity schedule** (not OCR in V1); AfA-Wizard is single source of truth | `packages/kpi-engine` (pure) |
| **Reminder / trigger** | Classes: **Pflicht** (non-mutable, e.g. §556, Funkzähler), **Chancen** (opt-out), **Informative** (e.g. Leerstand doc), Event-chains, recurring tasks. Auto-resolve on target event; escalate in-app→email→push | trigger/state-machine engine + scheduler |
| **Tickets (Mängel)** | Renter creates w/ photos + category; status workflow; internal vs renter-visible comments; **Kostenträger flag (Mieter/Vermieter zahlt)**; rate-limit; EU photo storage + retention. "Find a Handwerker" = **token handoff to MeinHandwerker** (independent app), not an internal role | standard CRUD + object storage |
| **Document / letter engine** | **Versioned clause building-blocks** (`Schönheitsreparaturen v3`…); a contract = a *composition* of clause versions, stored. BGH change = new version + mark old "veraltet" → dashboard flags affected contracts. Also Mieterhöhung, Kündigung, Mahnung, WGB, SEPA-Mandat. VPI via **Destatis GENESIS API**; Mietspiegel **provider stub** | template/versioning engine + PDF service |
| **Doc extraction (OCR/Vision) — V1** | **One LLM/Vision pipeline** (upload → prefill → confirm) shared by **NK receipts** (Beleg-OCR) **and migration** (old contracts/statements/meter readings from PDF/photo/screenshot). ⚠️ Pulled into **Pitch-MVP/V1** | Vision adapter + review UI |
| **Email delivery (compliance-grade)** | Modell A (own domain, From-name=landlord); **bounce/complaint suppression** (shared-domain reputation); **delivery-status ledger → 3-colour Zustell-Ampel** = §556 Zugangsnachweis (proof of receipt); **Zugangs-Wächter** counts *backward* from the deadline. UVI vs NK statement have **different delivery regimes** | provider adapter + append-only delivery log |
| **Documents (render)** | Shared PDF service behind all of the above: NK/UVI/AfA-dossier/Anlage-V/contracts | PDF service |
| **Checklists** | Guided legal workflows that spawn reminders; shared data model (steps, deadlines, templates) | data-driven library |

---

## 5. Cross-cutting architectural rules (apply everywhere)

- **Never hardcode legal rules → a versioned rules/config store.** AfA rates, Grunderwerbsteuer per Bundesland, Anlage-V line numbers per year, HKVO ratios, CO₂ 10-step table, BORIS portal links, **VPI (Destatis GENESIS feed), Mietspiegel (provider stub), rental-contract clause versions**. All change; store as data with an "as-of law date" and show *"Rechtsstand MM/JJJJ"* in outputs. The Vertragsgenerator's clause-versioning is the same idea applied to contracts.
- **Immutability + versioning is system-wide** (GoBD/§147 AO): statements, ledger entries, exports, AfA records, UVI send-log, **email delivery log**, IBAN history, contract clause-sets, audit trails. New version, never overwrite; store hashes where legally relevant.
- **Adapters at every external edge.** Bank (finAPI), meter platforms, MDL, BORIS, Destatis, DATEV, AI/Vision — each normalizes to an internal model before any engine sees it. No engine imports a vendor SDK.
- **"Tool, not advice" everywhere.** Consistent "rechtskonform, keine Rechts-/Steuerberatung" disclaimers; keep the StBerG/legal-advice line out of the product.
- **Guard/Wächter is a reusable pattern.** 15%-AfA, Eichfrist, UVI-compliance, §543 arrears, §556 deadline — all "compute a warning from existing data" → one guard+reminder mechanism, not bespoke code each time.

---

## 6. Compliance-by-design (shapes the build from day 1 — not retrofittable)

The Wiki's Datenschutz page is explicit: this is the operating licence. Bake in now:

- **AVV per customer + a sub-processor register** (Supabase, finAPI, email provider, AI/Vision, error-logging each need an AVV and must be listed). A non-EU sub-processor without safeguards = compliance break — **this is exactly the Supabase decision in §1.**
- **EU/DE hosting, TLS in transit, encryption at rest, tenant isolation** (`accountId` scoping + Postgres RLS is the isolation boundary).
- **Retention-vs-deletion = the "two-clocks" model** (Mieterportal + Datenschutz pages): **Uhr A** = renter *portal access* ends after the §556 window (final NK statement + buffer); **Uhr B** = actual *deletion*, run separately **per data class**. Corrected figures: tax-relevant Buchungsbelege (NK statements, bank statements, invoices) = **8 years** (§147 AO — reduced 10→8 as of 01.01.2025); contract/deposit/handover ≈ 3 years. Deadlines **configurable, legal minimum as a hard floor (extend-only)**. On an Art. 17 deletion request that collides with a retention duty → **restrict/block, don't delete** (Art. 17(3)(b) + Art. 18), delete after the term. Beendete Mietverhältnisse → cold storage, not deletion.
- **DPIA (DSFA, Art. 35)** likely mandatory (scope + financial data) — plan it. Document **TOMs**, breach process (72h), and **Art. 20 data-export** via authenticated, expiring secure link (not a mail attachment, Art. 32).
- **Data minimization in exports** (e.g. unit label instead of renter name in DATEV Buchungstext where possible).

---

## 7. Revised build order (aligned to the real roadmap)

Roadmap from the Wiki: **MVP freeze 23.07**, **pitch 27.07 (Tolga Önal)**, web-only focus **until 25.07**,
**launch ~08.09** (web **+ native iOS/Android together**) before NK season. Small team → broad scope,
hard Tier-1 priority, iterative.

1. **Foundations (now):** Supabase (Postgres+Auth+Storage+RLS), multi-tenant `Account/Landlord/Person/Membership` + RBAC, `Building→Unit→Tenancy` temporal core, `nk-engine` + golden fixtures, PDF service. *This is the pitch core — a correct NK/heating statement.*
2. **Tier-1 engines:** heating + CO₂ (`heating-engine`), meter device mgmt + normalized `MeterReading` (add the `unit/source/monthly_uvi` columns **before** real customer data exists).
3. **Doc-extraction pipeline (now V1/Pitch-MVP):** one LLM/Vision upload→prefill→confirm flow serving both NK-receipt OCR **and** migration import. Also the onboarding on-ramp (CSV/Excel mapping).
4. **Bank + Ledger:** finAPI AIS sandbox → matching → Payment Ledger (payment date mandatory). Unlocks rent monitoring *and* tax export.
5. **Tax export:** `export-engine` (Anlage V + DATEV) + Readiness-Check + immutable archive; AfA-Wizard feeds it.
6. **Document/letter engine:** Vertragsgenerator with versioned clause blocks + SEPA mandate + VPI feed; scheduled clause-check job.
7. **Reminder/trigger engine + email-delivery subsystem + V1 checklists:** §556 countdown + Zugangs-Wächter, rent arrears, move-in/out chains, UVI reminder, bounce/complaint handling.
8. **Mieterportal, Tickets, StB guest access, Investitionsmodul add-on**, native apps **at launch** (Expo/RN; Capacitor/PWA fallback if native slips).

Rule from v1 still governs: **engines + fixtures before UI.** A wrong framework call later costs an app rewrite; it never touches the engines or the data.

> ⚠️ **Reality flag for a two-person team:** the Wiki has pulled a *lot* into V1 (native apps + OCR + doc-extraction + contract engine + investment module, all by ~Sept). That's ambitious. The pitch (27.07) only needs step 1. Guard the sequence — engines and correctness first; the launch surface can stage in behind them.

---

## 8. Core temporal data model (unchanged principle, extended)

Everything that can change *during* a period is a row with `validFrom/validTo`, never a scalar.
Extended entities: `Landlord`, `Membership`, `BuildingAssignment` (employee↔building), `SelfUsePeriod`
(m²-based, see §2), `Meter` (+ `calibrationValidUntil`), `MeterReading` (normalized: `unit`, `reason`,
`source`), `Payment` (ledger), `TaxCategoryMapping`, `AfaRecord`, `Loan`, `Reminder`, `LettingEffort`
(vacancy evidence), `Ticket`, `ExportArchive`, `SubProcessor`.
**Added this pass:** `ActivationCode` (tenancy-bound, per-person, single-use), `IbanHistory`
(versioned), `EmailDelivery` (append-only status log), `ClauseBlock` + `ClauseVersion` + `Contract`
(composition of clause versions), `ProspectObject` (Prüfobjekt → becomes `Building` on purchase).
The v1 Prisma sketch (temporal core + immutable statements + integer-cents money) stands; add the
above around it.

### Allocation keys (per *Mindestanforderungen*)

```prisma
enum AllocationKey {
  AREA         // Fläche (Wohnfläche)
  PERSONS      // Personen
  CONSUMPTION  // Verbrauch (metered)
  UNITS        // Einheiten
  DIRECT       // Direktzuordnung — cost assigned to exactly one unit/tenancy
  MEA          // Miteigentumsanteil (WEG)
}
```

Two requirements ride along with these:

- **`DIRECT` (Direktzuordnung) is mandatory and was missing from the v1 sketch.** A cost that belongs to exactly one unit (a repair inside flat 3) bypasses proportional allocation entirely. Without it, the engine can only spread costs — which is wrong for a large class of real invoices.
- **Keys must be freely changeable without deleting already-entered data.** This is a literal, named pain point at *both* objego and immocloud. It's why the key lives on a per-period `AllocationKeyAssignment` and never on the `CostEntry` itself: changing a key re-runs the calculation and never cascades into stored data.

**Granularity, now confirmed from the spec:** NK allocates at **unit / tenancy** level (that's what
`DIRECT` implies); AfA splits by **m²**. Two different granularities on purpose — see §2.

---

## 9. UI / accessibility

Design target from the Wiki: modern, minimal, Apple-like, understandable "from 7 to 70".
Resolve the minimalism-vs-clarity tension by making it measurable: **WCAG 2.1 AA + BFSG**
(contrast, focus states, scalable type, keyboard nav) from the start. Apple-style reduction for
aesthetics only — never at the cost of labels or contrast. This confirms the React + Framer Motion
choice and adds accessibility as a hard, testable requirement.

---

## 10. Worked NK allocation example (verified — carried from v1, still the crown-jewel test)

Garbage cost **€1,200.00** for 2025 (365 days), key = area, one mid-year move-out + vacancy:

| Party | Area | Days | m²·days | Share |
|---|---|---|---|---|
| Unit A — Renter 1 | 50 m² | 365 | 18,250 | €600.00 |
| Unit B — Renter 2 (out Jun 30) | 30 m² | 181 | 5,430 | €178.52 |
| Unit B — **VACANT** (Jul–Dec) | 30 m² | 184 | 5,520 | €181.48 → landlord |
| Unit C — Renter 3 | 20 m² | 365 | 7,300 | €240.00 |
| **Total** | | | 36,500 | **€1,200.00** ✓ |

Renter 2 pays only their 181 days; the vacant half-year lands on the landlord; A and C aren't
overcharged; largest-remainder rounding sums to exactly €1,200.00.
