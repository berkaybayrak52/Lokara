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
| **Integrated on `development`, unverified** | Present on the long-lived development branch without current closure evidence; absent from `main`. |
| **Specified** | The approved or merged contract for later implementation; not proof of production behavior. |
| **Future** | Selected direction or owned work whose implementation is not present. |

### Shipped foundations

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

### Integrated on `development`, unverified

- Paused M9 adds all W1–W8 projections, migration `0025`, account-scoped jobs/API, immutable
  delivery/checklist evidence, deterministic email and `/waechter`. Automation defaults off and
  source/legal, provider, UVI-artifact, checklist-catalogue and known presentation blockers prevent
  production use.
- Deferred M7-F repairs and UI-04 are also integrated here without test, audit, review, database or
  browser evidence from the consolidation.

### Other shipped capabilities

- M7 adds normalized pure `packages/afa-engine` and `packages/export-engine`, versioned AfA/export
  rules, migration `0024`, seven immutable account-scoped M7 records, the restricted tax
  API/workspace and a German Anlage-V projection. The server generates every artifact from domain
  inputs and freezes the exact bytes; archive versions and supersession run per logical export
  stream (account, building, tax year, export kind). The M7-0…M7-E foundation is present on `main`
  with its earlier slice evidence. M7-F repairs are integrated only on `development`, their closing
  reviews remain open, and real export output stays blocked while its register values remain
  `verify-before-production`.

- G1 adds the pure `packages/guard-engine` with caller-supplied W1 statement-deadline, W2
  meter-calibration and W4 UVI-cadence rules. Exactly `12-F01`–`12-F06` and `12-F11`–`12-F13`
  execute through production code. On `main` it has no API, persistence, UI, scheduler or PDF
  consumer; paused M9 adds those consumers only on `development`.

- U1 adds the pure `packages/uvi-engine`; U1b adds its explicit provenance channel and U5 carries
  the resolved evidence into the immutable run/archive, closing the former provenance gap.
  U2 supplies versioned Heizspiegel inputs. U3 supplies annual and monthly DWD normalization
  adapters. U4/U4b persist monthly readings and their raw links, station/month weather evidence,
  effective-dated building configuration, building-month evidence and immutable run/delivery rows.
  U5 composes those boundaries into owner-authorized generation, an immutable archive and a
  separate German renter document downloadable by the owner. Paused M9 scheduling on `development` refuses UVI
  delivery until immutable PDF bytes exist; renter portal publication remains M10.

- The bounded least-privilege pre-context identity read is shipped on `main` through migration `0014`.
- Page 08 bank matching is implemented. `packages/matching-engine` runs all thirteen
  `BANKMATCH` cases through real code (M6-C1), and M6-C2 adds the nine account-scoped bank,
  receivable, IBAN-history, proposal and payment-ledger tables, the `docs/15` § 3.1 adapter and the
  owner-scoped endpoints including the Page-01 handoff. M6-C3-0 migration `0020` verifies the
  audited renter, cap, provenance, trigger-resolution and RLS-write invariants. C3a connects the
  engine to Postgres and adds exactly five owner APIs; it is technically complete,
  development-synchronized and locally merged. C3b jobs and the C3c landlord *Zahlungen*
  screen are technically complete and locally merged. The screen is a client-only
  owner screen: one final confirm/reject/duplicate outcome, no manual assignment, no backend
  change. The § 4 stored-reference
  signal is deliberately inert: the field it scores against is named by § 4 and defined nowhere
  in § 3.

### Specified

- Page 01 and Page 01b contracts and their data-only or capability evidence live in `docs/02`,
  `docs/03` and `docs/08`; their named implementation gaps remain open.
- M6-A/M6-B ship temporal/actual advances, Saldo settlements, immutable owner-only finalization and
  separately rendered tenant archives; M6-C1/M6-C2 ship the matching engine, persistence and base
  owner endpoints, and M6-C3-0 closes their audited database invariants. C3a's service/final `0021`
  is technically complete, development-synchronized and locally merged. C3b jobs and the C3c *Zahlungen*
  UI are locally merged, which completes M6; M10 renter delivery/portal remains open.
- Real external providers stay behind adapter contracts and require their own integration,
  security and compliance evidence.

### Future

- Real Supabase Auth/Storage/hosted Postgres, Redis-backed rate limiting or workers, payments,
  production bank/Vision/email/DATEV/Destatis providers and native mobile apps are not wired.
- Source-backed `docs/10`–`docs/14` precede their remaining implementation. `docs/16` is
  technically implemented through U5 as described above. Production clearance remains blocked by
  the pending authoritative CSV sync for `R-UVI-01`/`R-UVI-02`, the exact monthly § 6a content
  list, unresolved legal/convention checks and the other `verify-before-production` items recorded
  there. `plz_geocoord` is the sole repository-wide PLZ-coordinate source and its vendored UVI path
  is green. M9 delivery is integrated but default-off/blocked; M10 renter publication remains
  future. The original `docs/15` scope is implemented through M6; its round-five tenancy,
  reference, tie-break, credit and identity supplement is specified but not implemented.

## Runtime topology

```text
Browser
  -> apps/web (Next.js, cookie session)
  -> apps/api (FastAPI, Pydantic boundary, account authorization)
       -> packages/db -> Postgres + RLS
       -> packages/nk-engine -----------\
       -> packages/heating-engine -------+-> normalized calculation result
       -> packages/rules-store ----------/
       -> packages/matching-engine -> deterministic match proposal + settlement
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
- `packages/guard-engine` is the prepared G1 decision layer. It depends only on `packages/domain`,
  accepts explicit source identity, `today` and caller-resolved rule bundles, and never imports the
  rules store or ambient clock. It stores and delivers nothing; later consumers belong to U and M9.
- `packages/uvi-engine` is the `docs/16` § 6a decision layer. It depends only on
  `packages/domain`, rounds the displayed kWh before deriving delta and percent, and reuses no
  rules-store table — in particular not `rules/degree_days.py`, which is the VDI 2067 § 9b
  apportionment table and a different dataset. It stores and delivers nothing.
- `packages/matching-engine` is the `docs/15` decision layer: signal scoring, the six-step decision
  order, § 366/§ 367 settlement, the Largest-Remainder principal split and reversal. It imports the
  standard library only — not even the domain package — and refuses `float` at its one import
  boundary. It stores nothing; `packages/db` holds what it read and what it decided.
- M7 adds `packages/afa-engine` and `packages/export-engine` as pure decision layers.
  They receive normalized facts plus resolved rule evidence and do not import FastAPI, SQLAlchemy,
  Postgres or rendering. `scripts/check_engine_purity.py` covers both.
- `packages/rules-store` resolves dated legal and convention values. Engines receive resolved
  values; they do not reach into the store.
- `packages/adapters` normalizes bank, meter/MDL, annual and monthly DWD, Vision, email, Destatis
  and DATEV edges. Only an adapter may know a provider format.
- `packages/db` owns SQLAlchemy models, Alembic migrations, sessions, RLS-supporting persistence
  and seed data, including U4/U4b monthly UVI evidence and archive rows. Migration `0024` adds the
  seven M7 tables; parallel heads `0025` and `0026` are joined by empty merge revision `0027` on
  `development`. Domain and engine packages do not depend on it.
- `apps/api` composes authorization, persistence, engines, rules, adapters and rendering. U5 owns
  the authorized UVI generation/archive and owner download boundary. M7 adds the tax composition
  boundary, where the server generates and freezes every artifact itself. Pydantic validates the
  backend boundary.
- `apps/web` and `packages/ui` own client interaction and presentation. Zod mirrors wire
  validation for user experience; it never replaces backend validation.
- `packages/pdf` projects frozen calculation results into documents, including the separate U5
  renter artifact and the M7 Anlage-V overview. It may format and paginate; it does not
  recalculate legal or money rules.

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
- Tenant-document isolation is shipped for M6-B owner-only archives and the U5 owner-generated UVI
  artifact: select one account-valid tenancy before rendering and expose no other renter's visible
  or hidden data. Neither boundary is renter portal output or delivery.

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

No exact retention duration is canonical yet. Approved `docs/11` and merged M7 archive code do
not supply the separate source-backed privacy retention schedule needed to close that boundary.

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
| AfA calculation, allocation, self-use and financing handoff | `docs/10-afa.md` |
| Tax-event readiness, Anlage-V/DATEV and export archives | `docs/11-tax-export.md` |
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
