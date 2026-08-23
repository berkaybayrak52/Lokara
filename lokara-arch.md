# Lokara architecture — canonical v4

This file is the concise current architecture contract. The complete predecessor, including removed
schema sketches, dated rollout notes and repeated examples, remains available exactly through
`git show 7b08f2b:lokara-arch.md`.

`CLAUDE.md` overrides this file. `PLAN.md` owns delivery order and milestone status. Detailed
contracts live in `docs/01-tech-stack-and-decisions.md` through
`docs/08-statement-document.md`; this file names their boundaries instead of duplicating them.
For calculation and legal rules, original Pages/annexes and the Rechtsstand register feed approved
`docs/00`–`docs/16`; approved docs then control code.

## Status model

| Status | Meaning |
| --- | --- |
| **Shipped** | Present on `main` and covered by current repository gates. |
| **Prepared but unmerged** | Implemented or transcribed on a named branch, but absent from `main`. |
| **Specified** | The approved or merged contract for later implementation; not proof of production behavior. |
| **Future** | Selected direction or owned work whose implementation is not present. |

### Shipped

- A Python modular monolith under `apps/api` exposes the HTTP/JSON boundary.
- `apps/web` is the responsive Next.js client; `packages/ui` is its shared TypeScript UI layer.
- Python packages provide the domain types, NK engine, heating/CO₂ engine, versioned rules,
  adapters, database layer and PDF renderer.
- Local Postgres, SQLAlchemy 2.0, Alembic, forced RLS and composite account-scoped foreign keys form
  the current persistence and isolation path.
- The demo path persists one fixed account, calculates operating and heating costs and renders the
  landlord `Vermieter-Gesamtübersicht`.
- `docs/09-betrkv-catalogue.md` and its data-only oracle are technically implemented through Slice C.
  Its flagged authority still blocks production use.

### Shipped

- The bounded least-privilege pre-context identity read is shipped on `main` through migration `0014`.
- The Page 08 bank-matching transcription is merged in `docs/15`; `BANKMATCH-F03` is resolved in
  its complete thirteen-case oracle. Production bank matching remains M6 work.

### Specified

- Page 01 and Page 01b contracts and their data-only or capability evidence live in `docs/02`,
  `docs/03` and `docs/08`; their named implementation gaps remain open.
- M6-A/M6-B ship temporal/actual advances, Saldo settlements, immutable owner-only finalization and
  separately rendered tenant archives. Bank matching, payment ledger and renter delivery/portal remain open.
- Real external providers stay behind adapter contracts and require their own integration,
  security and compliance evidence.

### Future

- Real Supabase Auth/Storage/hosted Postgres, Redis-backed rate limiting or workers, payments,
  production bank/Vision/email/DATEV/Destatis providers and native mobile apps are not wired.
- Source-backed `docs/10`–`docs/14` and `docs/16`, plus completion of `docs/15`, precede the
  related implementation. `PLAN.md` owns their sequence.

## Runtime topology

```text
Browser
  -> apps/web (Next.js, cookie session)
  -> apps/api (FastAPI, Pydantic boundary, account authorization)
       -> packages/db -> Postgres + RLS
       -> packages/nk-engine -----------\
       -> packages/heating-engine -------+-> normalized calculation result
       -> packages/rules-store ----------/
       -> packages/pdf -> Playwright/Chromium document
       -> packages/adapters -> stub or real external provider
```

There is one backend, and it is Python. The web client never accesses Postgres directly. A future
mobile client calls the same API with Bearer JWT storage rules; it does not introduce a second
backend.

## Dependency boundaries

- `packages/domain` is the shared bottom layer for money, periods, occupancy, allocation and meter
  value objects. It imports no framework, database or provider SDK.
- `packages/nk-engine` and `packages/heating-engine` depend only on the domain layer. They accept
  normalized inputs and return deterministic results. They do not import FastAPI, SQLAlchemy,
  Postgres, vendor SDKs or the PDF package.
- `packages/rules-store` resolves dated legal and convention values. Engines receive resolved
  values; they do not reach into the store.
- `packages/adapters` normalizes bank, meter/MDL, Vision, email, Destatis and DATEV edges. Only an
  adapter may know a provider format.
- `packages/db` owns SQLAlchemy models, Alembic migrations, sessions, RLS-supporting persistence
  and seed data. Domain and engine packages do not depend on it.
- `apps/api` composes authorization, persistence, engines, rules, adapters and rendering. Pydantic
  validates the backend boundary.
- `apps/web` and `packages/ui` own client interaction and presentation. Zod mirrors wire
  validation for user experience; it never replaces backend validation.
- `packages/pdf` projects frozen calculation results into documents. It may format and paginate;
  it does not recalculate legal or money rules.

`scripts/check_engine_purity.py` protects the engine boundary. The RLS and composite-FK checks
protect the current persistence boundary. The shipped pre-context checker protects the one bounded
identity read; `AGENTS.md` owns the complete gate contract.

## Identity and account isolation

- `Person` is the global human identity. `Account` is the paying customer and isolation boundary.
- A `Membership` links a Person to an Account with role `OWNER`, `EMPLOYEE` or
  `TAX_ADVISOR`. Role never belongs directly to Account.
- `AccountShape` is `SOLO` or `HAUSVERWALTUNG`; it is not an authorization role.
- A `Renter` is tenancy-linked domain data, not a membership role. One Person may be a landlord,
  renter and tax adviser in separate contexts.
- Self-use is a dated `SelfUsePeriod`, never a fake renter. Vacancy is derived where neither a
  tenancy nor self-use covers the period.
- Every account-scoped row carries `account_id`. Cross-account foreign keys preserve the account
  in the composite edge.
- Current account routes verify live membership and set transaction-local account context; forced
  Postgres RLS is the backstop. Nested-resource authorization remains Specified M5 work.
- Login is the only permitted pre-account lookup. The shipped bounded
  `app_bootstrap_contexts(text)` read does not authorize another pre-context reader.
- Tenant-document isolation is shipped for M6-B owner-only archives: select one account-valid tenancy
  before rendering and expose no other renter's visible or hidden data. It is not renter portal output.

## Financial and lifecycle time axes

Lokara keeps separate clocks because combining them produces incorrect money or access decisions:

1. **Occupancy and allocation time.** Tenancies, self-use, keys, meters, IBANs and similar changing
   facts use dated rows. Billing periods and clipped occupancy drive operating-cost allocation.
2. **Operating-cost billing time.** An Abrechnung belongs to its service period and applies the
   dated rules resolved for that calculation.
3. **Tax cash time.** Tax uses the cash basis under § 11 EStG. A statement creates an obligation;
   an accepted payment allocation creates the cash event. The handoff is explicit.
4. **Document version time.** A draft is a live preview. Finalization creates immutable versioned
   inputs, results, rule versions, timestamps, hashes and separate audience documents. Corrections
   append a new version.
5. **Access time.** A person may read data only while an approved account or tenancy relationship
   makes them eligible.
6. **Data-lifecycle time.** Retention, restriction and deletion are decided per data class and legal
   duty. Retaining a record never grants portal access.

No exact retention duration is canonical yet. Every duration remains blocked on source-backed
`docs/11` tax/archive rules and a separate source-backed privacy retention schedule.

## Subsystem ownership

| Subsystem | Canonical owner |
| --- | --- |
| Stack selections and workspace membership | `docs/01-tech-stack-and-decisions.md` |
| Identity, isolation, temporal records, statements and ledger model | `docs/02-data-model.md` |
| NK and heating/CO₂ calculation contracts | `docs/03-nk-heating-engines.md` |
| API, web routes and client structure | `docs/04-web-app-structure.md` |
| UI tokens, accessibility and legal-copy tiers | `docs/05-design-system.md` |
| Seeded demo facts and pitch truth | `docs/06-demo-scenarios.md` |
| Cross-cutting compliance and two-clock lifecycle | `docs/07-compliance.md` |
| Statement audiences, formal minimums and document projection | `docs/08-statement-document.md` |
| Milestone sequence and delivery status | `PLAN.md` |

## Cross-cutting invariants

- Money is integer cents and `decimal.Decimal`; binary floats never enter calculation logic.
- Engines are pure, deterministic and covered by source-backed golden evidence.
- Legal and convention values are versioned and show the applicable `Rechtsstand`.
  `verify-before-production` remains visible; `geprüft` is not lawyer approval.
- Legally relevant records are append-only or versioned. Corrections and reversals append evidence;
  they do not rewrite history.
- The owner residual is structural: total minus rounded renter shares. It always exists and may be
  zero or negative.
- External providers are adapters, never domain dependencies. A stub proves only the boundary, not
  production provider compliance.
- `ENVIRONMENT` has no default. Staging and production refuse dev-token/demo-seed switches and the
  published development signing secret.
- Legal/tax output describes Lokara as a tool for rechtskonforme work and states that it is not legal
  or tax advice. It never says `rechtssicher`.
- The responsive web app comes first. Native mobile is future work.
- Landlord-facing UI and statements meet the design/accessibility contract and receive human-facing
  review. The current PDF is the landlord overview, not a sendable tenant statement.
