# PLAN.md — Lokara roadmap

This file answers two questions:

1. What is built?
2. What comes next?

Build in the execution order below. Each slice ends green. Engines and golden fixtures come before
UI. Dates are communication events, not planning inputs.

## Current state

- M0–M4 are built and green on the v4 Python stack.
- The v4 migration is complete. The old TypeScript backend is gone. Mobile moved to M10.
- Composite foreign-key isolation and M5a identity/RLS are complete.
- Execution rows 1–3 are complete.
- Berkay's pages 06–08 exist, so M6, M8 and M10 are no longer blocked on missing specs. Their
  `verify-before-production` values remain blocked for real use.
- Row 4 is current. Its secure bootstrap foundation is complete on
  `slice/m5-bootstrap-contexts`, but the slice is not merged yet.
- Row 4 has not added a new dashboard, portal or account switcher.

---

## 1. Execution order

The order closes legal billing exposure first. Missing UVI or CO₂ disclosure can each reduce the
heating claim by 3%. Missing consumption-based billing can reduce it by 15%.

| # | Status | Work | Required result |
| --- | --- | --- | --- |
| 1 | ✅ Done 13.08.2026 | Wire R1/R5/K9 and Ho/Hu into `heating-engine` | Heating uses the required half-up allocation path. |
| 2 | ✅ Done 15.08.2026 | Eigentümer residual | One residual line per property and cost type: total minus renter shares. It always exists and is never a party or occupancy share. NK stays on largest remainder until Row 5. |
| 3 | ✅ Done 15.08.2026 | CO₂ rounding under § 5 Abs. 1 S. 3 | Annualise, round half-up to one decimal, then classify. Print the same one-decimal value in both PDF locations. |
| 4 | 🟡 In progress | M5 roles, portals, URL context and switcher | Secure bootstrap is complete on the slice. Still needed: role enforcement, owner/renter portal contexts, switcher, nested-building authorization and the `renter.person_id` negative guard. |
| 5 | Open | Page 02 → `docs/09` and BetrKV catalogue | Replace free-text cost types with a versioned umlagefähig catalogue. Transcribe the spec before changing NK rounding or allocation behaviour. |
| 6 | Open | M6 bank, ledger and finalized statements | Add actual paid advances, BGH minimum #4, immutable snapshots, one landlord overview and isolated tenant documents. |
| 7 | Open | Page 05 → `docs/12` Wächter set | Implement § 556 deadline, Eichfrist and UVI cadence through one reusable guard mechanism. |
| 8 | Open | Statement copy and citations | Resolve the remaining reviewer findings on ligatures, spacing, copy and footer citations. |
| 9 | Ready | D2 Heizspiegel comparison value | Compare heating only. Use `mittel − ww_kwh_m2`; warm-water deduction is 24 kWh/(m²·a), except heat pump ≈8 as a labelled Lokara convention. Guard non-positive results. Use the labelled 250–500 fallback for missing >500 heat-pump and pellet classes. Do not extrapolate. |
| 10 | Open | UVI | Monthly § 6a HeizkostenV information. Needs Row 4 tenant access, monthly readings and Row 9 comparison values. |
| 11 | Ready with blocked values | M7 tax export and AfA | Computation paths are specced. Placeholder register values must be verified before any real tax-adviser or Finanzamt output. |
| 12 | Open | M8 documents, M10 modules and mobile | Clause engine, tickets, activation, investment cockpit, billing and native apps. |

Row 9 is no longer blocked by the co2online licence. A real § 6a output must still be checked later.

### M7 value warning

The following remain `verify-before-production` placeholders:

- Weg B;
- all Anlage-V line numbers;
- SKR03/SKR04 accounts;
- DATEV EXTF parameters;
- three BFH case numbers marked `ZITAT UNSICHER`.

The computation paths may be built. Nothing using these values may be sent to a real Steuerberater
or Finanzamt until each value is confirmed.

---

## 2. Hard rules

1. **No calculation without its spec.** Transcribe Berkay's source into `docs/`, create the golden
   fixture, then implement. Never invent a legal value. The authoritative register currently has
   130 of 180 rows marked `verify-before-production`.
2. **Keep the demo path green.** Every milestone re-verifies database → migration → seed → statement
   → PDF. Fix or revert any break before continuing.
3. **Tag green milestone states.** Use `demo-green-<n>` only after the required gates pass.
4. **Finish one milestone or bounded slice at a time.** Do not merge half-built subsystems.
5. **Keep external services stubbed behind adapters** until their integration slice. No real keys or
   vendor SDKs in engines or domain code.
6. **Docs and code must agree.** A documented rule that code does not follow is a defect.

---

## 3. Completed foundation

### M0 — Foundations and scaffolding ✅

Built:

- Bun/Turborepo TypeScript workspace and uv Python workspace;
- Next.js web app, FastAPI API and shared packages;
- Ruff, strict mypy, pytest, ESLint, TypeScript checks, Vitest and CI;
- themed Tailwind and shadcn/ui design system;
- SQLAlchemy models, Alembic migrations and Supabase/Postgres RLS;
- API auth dependency and typed web client;
- temporal core schema with integer-cent money;
- Playwright PDF service.

The Expo mobile skeleton is not part of the completed foundation. It moved to M10.

### M1 — Operating-cost engine ✅

- Pure `packages/nk-engine`.
- Day-weighted allocation, vacancy handling and largest-remainder reconciliation.
- DIRECT, MEA and other allocation keys.
- Per-period `AllocationKeyAssignment`; changing a key does not delete entered data.
- Canonical €1,200 golden fixture passes exactly.

**Done when:** golden tests pass, totals reconcile to the cent and recalculation destroys no data.

### M2 — Heating and CO₂ engine ✅

- Pure `packages/heating-engine`.
- HeizkostenV §§ 7/8, § 9 and § 9a.
- Degree-day renter-change allocation.
- CO₂ 10-step landlord/renter split.
- Versioned ratios, tables and `Rechtsstand`.

**Done when:** heating and CO₂ fixtures pass and the statement prints the correct split with
`Rechtsstand`.

### M3 — Web vertical slice and PDF ✅

Built:

- URL-scoped landlord portal under `/a/{accountId}`;
- membership check plus RLS for account access;
- `/me`-derived navigation and demo loading;
- buildings, units, tenancies and occupancy timeline;
- cost entries, allocation keys, meters and readings;
- statement creation and NK/heating PDF download;
- autosave so leaving a flow does not lose entered data;
- statement inputs from persisted rows, not fixture constants.

**Done when:** a logged-in user can produce the correct seeded NK/heating PDF without manual database
changes.

### M4 — Document extraction demo ✅

- Shared upload → prefill → confirm flow.
- Stub Vision adapter with canned invoices.
- Per-field confidence and API-owned review threshold.
- Extraction writes nothing until the ordinary cost form is confirmed.

Not included:

- automatic allocation-key choice, which needs the Row 5 BetrKV catalogue;
- Beleg persistence, file hash and object storage.

### FK isolation slice ✅

- All 17 tenant-to-tenant foreign-key edges carry `account_id`.
- Parents expose `UNIQUE (id, account_id)`.
- Nullable links use `MATCH SIMPLE`.
- `building_assignment` carries its own structurally consistent `account_id`.
- `scripts/check_fk_isolation.py` guards future edges.

### M5a — Identity schema and RLS ✅

- Person, Account, Membership, Landlord, Renter and SelfUsePeriod model.
- Roles live on Membership. Account shape lives on Account.
- `landlord`, `self_use_period` and global `person` isolation are tested.
- Person visibility uses Membership-based RLS and denies reads without context.
- RLS coverage and the demo path are green.

---

## 4. M5 remainder — current work

### Completed on `slice/m5-bootstrap-contexts`

- JWT auth carries only the verified Person subject.
- Expiry, issuer, exact audience and authenticated role are validated.
- Account context is never trusted from the token.
- Migration `0006` adds the single bounded `app_bootstrap_contexts(text)` read.
- `GET /me` returns all live account contexts from the database.
- The token-scoped account session and `/demo/summary` are retired.
- The demo summary now uses `/a/{accountId}/summary`.
- `scripts/check_pre_context_reads.py` and 40 mutation tests enforce the boundary.
- Full gate, demo path and boundary audit are green.

This work added no new dashboard, portal or account switcher.

### Still open

- Complete the existing owner portal with role-aware context and add the renter-facing context.
- Keep context in `/a/{accountId}/…` and `/renter/{tenancyId}/…`.
- Show a context switcher only when a Person has more than one context.
- Enforce OWNER, EMPLOYEE and TAX_ADVISOR behaviour in app logic.
- Restrict EMPLOYEE access to assigned buildings. No assignments means no visibility.
- Make TAX_ADVISOR read-only.
- Validate every nested `{buildingId}` through `PathAccountSession` before work begins.
- Return a deliberate 403/404 for a foreign or unauthorized building.
- Add an OpenAPI guard proving no route writes `renter.person_id`. Only M10 activation may write it.

**Done when:** roles behave correctly; every nested building route verifies its URL context; renter
context exposes no landlord data in app logic or RLS; multiple contexts switch by URL and are
re-authorized per request; the pre-context checker stays green; no current API route writes
`renter.person_id`.

---

## 5. Later milestones

### M6 — Bank, ledger and finalized statements

- Add Redis workers and webhooks.
- Keep finAPI stubbed behind the bank adapter.
- Match transactions using IBAN, amount and payment purpose.
- Store transactions and versioned IBAN-to-renter mappings.
- Add an append-only Payment Ledger with mandatory payment date.
- Replace `Tenancy.advance_payment_cents` with temporal `AdvancePaymentPeriod` rows and backfill
  existing tenancies.
- Add BGH formal minimum #4: deduct actual paid advances and print Saldo/Nachzahlung/Guthaben.
- Keep previews live and unarchived.
- Finalization creates one immutable, reproducible snapshot with inputs, results, engine/rule
  versions, `Rechtsstand`, timestamps, hashes and archived documents.
- Corrections create `vN+1`; old versions and referenced inputs remain intact.
- Render one internal landlord overview and one separate document per eligible tenancy.
- A tenancy with zero period-clipped usage days gets no tenant document or portal entry. The landlord
  overview receives the required footnote.
- Never generate one all-renters PDF and crop or hide sections.
- Add background jobs for bank sync, 180-day reconsent cleanup and deadline watchers.

**Done when:** seeded bank transactions match; actual paid advances produce the Saldo; temporal
advances work; preview creates no archive; finalization is immutable and reproducible; landlord and
tenant documents are separated; zero-day tenancies are excluded and footnoted.

### M7 — Tax export and AfA

- Pure `packages/export-engine` for Anlage V and DATEV EXTF.
- DATEV output is byte-exact Windows-1252 with semicolons and CRLF.
- Readiness check and immutable export archive with hash and timestamp.
- Pure `packages/afa-engine`, AfA wizard, 15% guard and loan-interest prefill.
- Preserve every `verify-before-production` flag from the M7 warning above.

**Done when:** DATEV and Anlage-V golden tests pass byte-exactly and the export is archived
immutably. Production use remains blocked until flagged values are verified.

### M8 — Document and letter engine

- Versioned clause blocks and stored clause composition.
- A legal change creates a new clause version and flags affected contracts.
- Mieterhöhung, Kündigung, Mahnung and SEPA mandate.
- Destatis VPI adapter and stub Mietspiegel provider.

**Done when:** a contract is generated from versioned clauses and a clause update identifies every
affected contract.

### M9 — Reminders, email and checklists

- Shared trigger/state-machine engine for § 556, arrears, move-in/out and UVI.
- Stubbed email provider using Lokara's domain and the landlord as the From-name, with an immutable
  delivery-status ledger.
- Suppress bounced and complained-about addresses.
- Count the § 556 access deadline backwards. UVI and annual statements keep separate delivery rules.
- Three-colour delivery indicator.
- Data-driven checklist library that creates reminders.

**Done when:** the § 556 deadline escalates correctly and delivery status is visible.

### M10 — Portals, modules and native apps

- Renter activation, renter portal, tickets and tax-adviser guest access.
- Investment pipeline and seven-KPI cockpit.
- `renter.person_id` starts NULL and is written only by single-use activation-code redemption.
- Decide and enforce whether `renter.person_id` becomes immutable after activation.
- Expo mobile app using the same FastAPI API, auth model and client patterns. Capacitor/PWA remains
  the fallback if native delivery slips.
- Stripe web billing and RevenueCat mobile billing.
- Locust load test at roughly 100 concurrent users before launch.

**Done when:** activation links only the intended Person and tenancy; spent, foreign and direct-write
attempts fail; renters see only their tenancy; the investment cockpit uses the annuity schedule; the
mobile app logs in and reads one real screen.

---

## 6. Product floor

M0–M4 are the current green, demoable floor: a correct CO₂-compliant operating-cost and heating
statement from persisted user data with tenant isolation.

Protect that floor. Correctness comes before breadth. If work stops, stop at a green state.
