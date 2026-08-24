# 06 — Current demo contract

> **Status: living specification.** This file owns the seeded demo facts, expected figures, pitch
> truth and delivery status. The reviewed 334-line predecessor remains available exactly through
> `git show 635acf9:docs/06-demo-scenarios.md`; no separate history file is needed.

## Ownership

| Source | Owns |
| --- | --- |
| `docs/06-demo-scenarios.md` | Seeded demo facts, expected figures, pitch truth and delivery status |
| `DEMO-RUNBOOK.md` | Setup, the six-screen click order, narration and recovery |
| `docs/03-nk-heating-engines.md` | NK and heating/CO₂ calculation rules and legal sources |
| `docs/08-statement-document.md` | Statement projections, content and Page 01 delivery gaps |
| `docs/02-data-model.md` | Identity row shapes, roles, isolation and temporal data |
| `docs/04-web-app-structure.md` | Routes and application structure |

## Delivery status

| Status | Demo capability |
| --- | --- |
| **Shipped** | One fixed `SOLO` owner account; the six-screen seeded path; Scenarios 1–5; the 2025 landlord calculation and PDF |
| **Shipped** | The secure M5 bootstrap read; it changes identity lookup, not onboarding or the visible demo |
| **Shipped** | M6-A/M6-B owner-only technical archive controls: actual advances, Saldo, immutable finalization and one isolated archive per eligible tenancy; no renter delivery/portal |
| **Green outside the six-screen demo** | M6-C1/M6-C2/C3-0/C3a are shipped on local `main`; C3a service and five owner APIs are technically complete and development-synchronized; C3b's matching jobs and the C3c *Zahlungen* screen are locally merged. None of the three is part of the six-screen path. |
| **Future** | Scenario 6, the five-persona identity demo, role-aware account switching, renter/tax-adviser portals, investment entitlement and mobile |

Green demo figures prove the current seeded path. They do not close Page 01 or Page 01b for
production.

## Shipped pitch path

The narrow path remains these six screens:

1. **Dashboard** — load the fixed demo account.
2. **Objekte** — show Musterstraße 12 and its three units.
3. **Einheit/Mietverhältnis** — show the dated tenancy and vacancy.
4. **Zähler** — show the building and flat meter evidence, including the expired cold-water meter.
5. **Beleg-Upload** — show the canned extraction proposal and human review gate.
6. **Abrechnung erstellen** — show the calculated figures and download the landlord PDF.

`DEMO-RUNBOOK.md` owns the exact clicks and words. Pitch claims stay limited to this truth: the seed
creates real database rows, the API reads them, and the NK and heating/CO₂ engines calculate the
shown result. Receipt extraction is canned. The PDF is not a tenant statement.

## Scenario 1 — Solo landlord, clean NK + vacancy

The canonical 2025 fixture is:

- one `SOLO` account and one owner membership;
- Musterstraße 12 with units A/B/C of **50/30/20 m²**;
- units A and C rented all year;
- unit B's renter leaves on **30.06.2025**, so the landlord carries the vacancy from 01.07.;
- one **1.200,00 € Müllabfuhr** `CostEntry`, allocated by `AREA`;
- one connected `bank_account` — *Mietkonto Musterstraße 12*, id `bank_acc_demo` — added by M6-C2.
  It exists because `StubBankGateway` serves exactly that id and the composite
  `(bank_account_id, account_id)` foreign key needs a real target; without it the transaction
  import has nothing to import into. It changes no statement figure and appears in no document.

| Party | Expected share |
| --- | ---: |
| Unit A renter | **600,00 €** |
| Unit B renter, 181 days | **178,52 €** |
| Unit B landlord vacancy, 184 days | **181,48 €** |
| Unit C renter | **240,00 €** |
| Reconciled total | **1.200,00 €** |

### One occupancy timeline drives every engine

The tenancy rows supply the dates for NK, heating and the statement. Unit B must therefore show the
same renter/landlord boundary everywhere. Its heating consumption is split by degree days at
**583,3/416,7 ‰**. Page 01b K3 rounds the renter's 145,825 device units to **145,8** and assigns
the exact **104,2** device-unit residual to the landlord. The resulting shares are
**776,39 € / 554,87 €**; their **1.331,26 €** pot is unchanged. No demo layer carries a second
occupancy timeline.

## Scenario 2 — Heating + CO₂ split

The same building carries one central gas-heating fixture for 2025.

### Scenario 2 — the fuel, the emissions and the CO₂ price

| Seeded fact | Exact value |
| --- | ---: |
| Fuel | **Erdgas** |
| Energy quantity | **20.000 kWh Hu** |
| Supplier-stated CO₂ mass | **4.000 kg** |
| Supplier-stated CO₂ cost | **261,80 €** |
| Heating and warm-water total | **10.300,00 €** |
| Heated area | **100 m²** |
| Emissions intensity | **40,0 kg CO₂/m²/a** |
| CO₂ band result | **60 % landlord / 40 % renters** |
| CO₂ landlord share | **157,08 €** |
| Allocable heating cost | **10.142,92 €** |
| Unit B renter/vacancy split | **583,3/416,7 ‰ → 145,8/104,2 units = 776,39 € / 554,87 €** |

Meter evidence is fixed with the scenario:

- building Wärmemengenzähler: **20.000 kWh**;
- building warm-water meter: **40 m³**;
- flat Heizkostenverteiler: **600/250/150 HKV units**;
- flat warm-water meters: **20/12/8 m³**;
- one expired **cold-water** meter, used only as the Eichfrist warning example.

### The demo's energy reference

The **20.000 kWh are Heizwert (Hu)** and the supplier-stated mass remains **4.000 kg**. The fallback
emission factors do not run when supplier data exists. The engine performs no Ho/Hu conversion; an
energy quantity and any applicable factor must already use the same reference. Detailed rules and
legal sources stay in `docs/03`.

### Settled realism boundary

The **1.200,00 €** garbage cost is the canonical fixture. The **10.300,00 €** heating total is kept
stable for the demo but is not presented as typical. Reopen that total only after a source-backed
heating-invoice composition specification exists; until then, do not invent a replacement total.

## Scenario 3 — Flexible allocation keys without data loss

**Shipped, optional outside the narrow runbook path.** The `Kosten` screen exposes this capability. A
cost's latest append-only key assignment drives the next calculation. Switching `UNITS` to `AREA`
recalculates the statement without changing or losing the entered `CostEntry`.

## Scenario 4 — Direktzuordnung (`DIRECT`)

**Shipped, optional outside the narrow runbook path.** A cost may be assigned directly to one unit
instead of being spread proportionally.

## Scenario 5 — Beleg-Upload

**Shipped with a canned stub.** Any accepted PDF, PNG or JPG drives the same stub response.

- Extraction writes nothing server-side.
- The proposal and the user's corrections survive temporarily in browser `localStorage`.
- Vendor and invoice date are shown but are not persisted.
- Period and allocation key are form defaults; they are not extracted from the document.
- Confirmation uses the ordinary cost-entry endpoint and creates an ordinary `CostEntry` with its
  allocation-key assignment.
- No uploaded file, archive record or file hash is stored.

The screen is a human review gate, not proof of a live OCR provider or document archive.

## Bootstrap and reset limits

The local pitch process requires explicit configuration: `ENVIRONMENT=local`,
`AUTH_DEV_TOKEN=true` and `DEMO_SEED_ENABLED=true`. `ENVIRONMENT` has no default. In `staging` or
`production`, the API refuses to start with a demo/dev switch enabled; with demo seeding disabled,
`/demo/load` and `/demo/reset` return 403.

An empty database still needs `uv run lokara-seed-demo` once. `/demo/load` runs through the
RLS-scoped application role and cannot create the first `Person`; after the owner seed exists, load
and reset operate only on the fixed `acc_demo_lokara` account. They are pitch utilities, not
production signup, onboarding or account creation.

The shipped M5 foundation adds migration `0014` and the bounded `app_bootstrap_contexts(text)`
identity read. It does not add a `Person` write, production onboarding, a new dashboard, a portal
or an account switcher.

## Current statement boundary

The current PDF is the fixed-2025 landlord **`Vermieter-Gesamtübersicht`**. It is never a tenant
statement and must not be sent to a renter. It shows the building-wide calculation and QA view,
including its `Rechtsstand` and the required tool-not-advice disclaimer.

M6-A/M6-B ship the owner-only technical archive boundary: actual paid advances, Saldo, immutable
finalization and one isolated archive per eligible tenancy. It does not change the demo PDF or add
renter delivery/portal. C3a's matching service is technically complete, development-synchronized
and locally merged, but it, C3b's jobs and the C3c landlord *Zahlungen* screen are not part of this
six-screen path. C3c adds a navigable screen and leaves the demo at six: the seed is unchanged and
no statement figure, allocation or rendered byte depends on it. C3b gives the demo bank account a computed PSD2 consent so the AIS pull still
works; no statement figure and no PDF byte depends on it. The statement period contract also
remains in `docs/08`: a shorter
Rumpfperiode is valid, while a period over 12 months hard-blocks before calculation or rendering.

## Future demo

### Scenario 6 — Hausverwaltung and five personas

**Future; not clickable today.** Hausverwaltung is an `AccountShape`, not a role or separate portal.
Roles live on `Membership`; the supported membership roles are `OWNER`, `EMPLOYEE` and
`TAX_ADVISOR`. A renter is linked domain data, not a membership role. Investor access is unlocked by
an entitlement, not an identity role. Detailed row shapes remain in `docs/02`.

The future demo covers five people without changing those rules:

1. an HV owner/admin with all account buildings;
2. an HV employee restricted to assigned buildings;
3. a renter with access only through their tenancy;
4. one person who is a landlord, renter and entitlement-gated investor in different contexts;
5. a read-only tax adviser guest on the client's account.

M5 owns membership enforcement, employee building scope and account switching. M10 owns renter
activation/portal and tax-adviser portal work; the investment module also remains future.

When persona seeding is implemented, it must be idempotent, use stable IDs, create an `OWNER`
membership for each account, load all personas with one switch and reuse Scenario 1 data where
possible. Until those unlocks ship, presentation stays on the stable six-screen dataset; future
persona beats are descriptions, not live-demo claims.

## Predecessor coverage

The exact predecessor is the archival source for removed dates, re-base narration and repeated
derivations: `git show 635acf9:docs/06-demo-scenarios.md`.

| Predecessor material | Living home |
| --- | --- |
| Current contract and bootstrap warnings | Delivery status; Bootstrap and reset limits |
| Scenarios 1–5 | Shipped pitch path and the matching scenario sections |
| Fuel physics, Ho/Hu decision and realism analysis | Scenario 2 facts, energy reference and settled realism boundary; detailed rules in `docs/03` |
| Scenario 6 | Future demo |
| Persona axes and identity consequences | Future demo; detailed row shapes in `docs/02` |
| Five persona rows, beats and unlocks | Future demo; milestones in `PLAN.md` |
| Current and future seeding rules | Scenario 1; Bootstrap and reset limits; Future demo |
| Presentation notes and recovery instructions | Pitch truth here; execution in `DEMO-RUNBOOK.md` |
| Dated implementation diary and repeated legal derivations | Exact Git snapshot above; authoritative current rules in `docs/03` and `docs/08` |
