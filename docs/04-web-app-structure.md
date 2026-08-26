# 04 — App/API structure and delivery status

This is the canonical contract for Lokara's tracked app structure, route compatibility and delivery
status. German UI copy, feature-based organization and WCAG 2.1 AA/BFSG requirements apply to the
web app and the future mobile app. The reviewed 108-line predecessor remains available with
`git show 635acf9:docs/04-web-app-structure.md`; no separate history file is needed.

## Status model

| Status                    | Meaning                                                                                |
| ------------------------- | -------------------------------------------------------------------------------------- |
| **Shipped**               | Present on `main`; this is the current repository or runtime contract.                 |
| **Prepared but unmerged** | Implemented and verified on a named branch, but absent from `main`.                    |
| **Specified**             | The behavior is documented, but its production implementation is incomplete or absent. |
| **Future**                | Selected direction for a later milestone; not a current workspace or capability.       |

## Shipped repository structure

```text
lokara/
├─ apps/
│  ├─ api/                    # Python FastAPI modular monolith
│  └─ web/                    # Next.js App Router client; HTTP API only
├─ packages/
│  ├─ domain/                 # normalized value objects and pure shared primitives
│  ├─ nk-engine/              # pure Python NK allocation
│  ├─ heating-engine/         # pure Python heating/CO₂ calculation
│  ├─ rules-store/            # versioned rule data resolved by callers
│  ├─ matching-engine/        # pure Python docs/15 bank matching and settlement
│  ├─ guard-engine/           # pure Python docs/12 W1–W8 guard evaluation
│  ├─ afa-engine/             # pure Python AfA calculation
│  ├─ export-engine/          # pure Python Anlage-V/DATEV projections
│  ├─ uvi-engine/             # pure Python monthly UVI calculation
│  ├─ adapters/               # ports plus current stubs/adapters
│  ├─ db/                     # SQLAlchemy, Alembic and RLS
│  ├─ pdf/                    # HTML→PDF through Playwright Chromium
│  └─ ui/                     # shared TypeScript web components/tokens
├─ pyproject.toml             # explicit uv workspace members
├─ package.json               # Bun workspace: apps/web + packages/ui
└─ turbo.json
```

The uv workspace contains `apps/api` and every Python package shown above except `ui`. The Bun
workspace contains exactly `apps/web` and `packages/ui`.

Integrated M9 work connects `packages/guard-engine` to migration `0025`, account-scoped jobs/API
and `/a/{accountId}/waechter`. It is unverified on `development`, paused and production-blocked.

`apps/mobile`, KPI engines, Redis and workers are absent. `packages/afa-engine`,
`packages/export-engine` and the tax route/workspace are present; deferred M7-F repairs are
integrated but unverified. Real Supabase, Vision, bank, email and MDL providers are absent; current
external edges use local infrastructure or stubs.

### Binding dependency direction

- Engines depend only on normalized domain shapes.
- Engines import no FastAPI, SQLAlchemy, rules store or vendor SDK.
- The API resolves rules, loads normalized persistence data and calls engines/adapters.
- Web accesses data only through FastAPI and never imports the DB layer.
- TypeScript and Python workspaces meet at the HTTP/JSON contract.

## Shipped web route compatibility map

The page numbers below are compatibility anchors used by application and package source comments:
pages 1–6 preserve the M3 names, page 7 preserves the canned M4 flow and page 8 is the M6-C3c
Zahlungen screen. Do not renumber them when navigation changes.

| Page | Name                   | Current route                                                      |
| ---: | ---------------------- | ------------------------------------------------------------------ |
|    1 | Dashboard              | `/a/{accountId}`                                                   |
|    2 | Objekte                | `/a/{accountId}/objekte` and `/a/{accountId}/objekte/{buildingId}` |
|    3 | Einheit/Mietverhältnis | `/a/{accountId}/einheiten/{unitId}`                                |
|    4 | Kosten erfassen        | `/a/{accountId}/kosten`                                            |
|    5 | Zähler                 | `/a/{accountId}/zaehler`                                           |
|    6 | Abrechnung erstellen   | `/a/{accountId}/abrechnung`                                        |
|    7 | Beleg-Upload           | `/a/{accountId}/beleg`                                             |
|    8 | Zahlungen              | `/a/{accountId}/zahlungen`                                         |
|    9 | Wächter                | `/a/{accountId}/waechter`                                          |

Page 8 is owner-only, in navigation as well as in the API; see the C3c paragraph under
"Shipped API surface" below.

`/styleguide` is a separate shipped design-token/stack showcase and is not one of the numbered
pages. Neither is `/`, which enters a sole
`OWNER` or `EMPLOYEE` context and otherwise offers the caller's live contexts as URL links. A sole
`TAX_ADVISOR` context is selected deliberately rather than
entered automatically.

## Shipped UI-00 global shell

UI-00 is locally merged and changes no API, schema, calculation, money, or legal rule:

- the supplied horizontal Lokara wordmark replaces the CSS placeholder and the supplied signet is
  installed through Next.js `app/icon.png`;
- authenticated content uses one centered 1440px frame with shared responsive side spacing;
- dashboard cards keep their natural heights and the three summary cards carry the restrained
  brand accent defined by `docs/05`;
- root loading, error, and not-found states use German copy, brand tokens, visible actions, and the
  supplied wordmark;
- global metadata describes lifecycle-wide property management. Domain-specific lifecycle fields
  remain owned by UI-03, UI-05B, UI-07, and UI-08; UI-00 adds none;
- no global object filter exists. Portfolio pages remain portfolio-wide, and an individual object
  is entered through the Objekte route.

The shell and overview no longer expose URL-context or server-authorization implementation text.
UI-00 left functional feature labels unchanged; UI-01 now owns the dashboard card wording below.

## Shipped UI-01 portfolio dashboard

UI-01 replaces the single-building start page with a portfolio read model while
keeping `/a/{accountId}/summary` unchanged for its existing consumers:

- `GET /a/{accountId}/portfolio/overview` returns exactly `buildingCount`, `unitCount`,
  `occupiedUnitCount`, `vacantUnitCount`, and `mietSollCentsMonthly`;
- the API aggregates only non-archived buildings visible to the caller, uses half-open active-today
  tenancy periods, and sums Kaltmiete only; an empty visible portfolio returns five zeroes;
- the dashboard renders the real monthly Mietsoll and occupancy ratio from that server-owned read
  model. It does not rebuild money or visibility from client-side building feeds;
- payment receipts, open items, cashflow, and tasks/tickets have no approved current data source and
  therefore render explicit German unavailable states. The proposed 82/18 finance values and fixed
  5/10/20 ticket counts are intentionally inactive and are never presented as product truth;
- loading, empty, failure, demo-load/reset, Objekte, and Abrechnung paths remain explicit. Employees
  with no visible assignment receive guidance to contact the account owner, never an owner-only
  creation action.

The endpoint adds no table, migration, write path, engine call, or public type outside the five-field
HTTP response. Its boundary audit is clean after focused coverage for zero, multiple, and archived
assignments plus both exact-today tenancy boundaries.

## Shipped UI-03 Objekte, wizards and map

UI-03 repairs the drifted tenancy contract, adds five building master-data columns and moves object
and unit creation out of the inline forms into their own account-scoped routes:

- `TenancyOut` on the wire carries `advancePaymentSchedule` (a list of
  `AdvancePaymentPeriodOut`), not the removed `advancePaymentCents`/`advancePaymentEur` scalars.
  The web contract in `apps/web/src/lib/contracts.ts` now mirrors it through the exported
  `AdvancePaymentPeriodOutSchema`, so the unit detail page parses the real response instead of
  failing closed. The NK-Vorauszahlung column selects the period valid today, else the latest one,
  and shows the em dash for an empty schedule;
- creating a tenancy sends `initialAdvancePaymentCents` and `advanceDeclarationRef`, matching
  `TenancyCreate`. The declaration reference is a free provenance string with the default
  "Mietvertrag"; it is not a calculated amount and changes no money;
- migration `0026` adds `building_type` (VARCHAR with a CHECK over the four structural values, not a
  Postgres enum), `is_residential`, `country`, `latitude` and `longitude`. The three non-geo columns
  are NOT NULL with server defaults so existing insert paths, including the demo seed, keep working;
  the coordinates stay nullable. The migration reserves `0025` for the unmerged M9 branch and sets
  `down_revision = "0024"` deliberately;
- `POST /a/{accountId}/buildings` accepts `buildingType`, `isResidential`, `houseNumber` and
  `country`, joins street and house number into the existing single `street` column, and keeps the
  German five-digit `postal_code` rule unchanged. `BuildingSummary` gains `buildingType`, `latitude`
  and `longitude`;
- geocoding lives behind `lokara_adapters.geocoding.GeocodingGateway`. `DisabledGeocodingGateway` is
  the default: `geocoding_enabled` is **off** unless an operator turns it on, because public
  Nominatim is a demo-only provider with no SLA. The adapter package owns the vendor format — query
  parameters, User-Agent, response shape and coordinate validation — and stays socket-free, the same
  line `dwd.py` draws; the HTTP transport, timeout, one-request-per-second policy and response cap
  live in `apps/api/src/lokara_api/geocoding_http.py`, the only place that speaks to the provider.
  It is server-side only and returns `None` on any error, timeout, empty result or blocked network.
  Geocoding never blocks or fails building creation;
- routes `/a/{accountId}/objekte/neu` and `/a/{accountId}/objekte/{buildingId}/einheit/neu` are
  pages inside the same account-scoped segment, so the shell and server authorization enclose them.
  Both inline creation forms are gone; the list and unit list render full width behind an owner-only
  action link. Hiding the link is presentation; authorization stays server-side;
- the Liste/Karte toggle switches presentation of the same complete object list. It filters nothing
  and holds no persisted preference. Leaflet is the single new runtime dependency, bound imperatively
  in a client component so SSR never touches `window`. Objects without coordinates render a calm
  German note, never an empty surface;
- photo areas in both wizards are **intentionally inactive**: no file input, no upload request, no
  storage call. Real object storage is a later slice.

Recorded assumptions (the source spec's Build-Notes): the Nominatim User-Agent uses the placeholder
contact address `kontakt@lokara.de` until a real one is supplied; the contract-generator entry links
to `/a/{accountId}/vertraege/neu?unitId={unitId}`, a path still to be confirmed with Emir, and
renders the branded 404 until that module exists; no example photo asset was delivered, so the slots
show a token-only placeholder; the optional display-only photo slot on the detail pages was left out
to respect the minimal-invasive rule protecting the later object dashboard.

This step was implemented under the direct implementation mode recorded in `CLAUDE.md` § 10. Lint,
strict mypy, type check and the web production build pass; no test suite was run for it, so it is
**implemented; unverified — no test evidence**.

## Shipped UI-04 Objektakte

UI-04 turns the object detail page into an Objektakte fed by one server-owned
projection (`apps/api/src/lokara_api/building_dashboard.py`):

- `GET /a/{account_id}/buildings/{building_id}/dashboard` returns one `asOf`, the building master
  data, four KPIs, at most three prioritized facts, compact unit rows, three module summaries and
  the caller's allowed actions. It is a separate endpoint rather than an extension of
  `GET /buildings/{building_id}` so the lean consumers of the detail contract do not load every
  financial projection to render a unit list;
- the four KPIs are **Kaltmiete / Monat** (sum of the cold rents of tenancies active at `asOf`,
  advances excluded), **Gesamtfläche**, **Ø Kaltmiete / m²** and **Vermietungsstand**. The square-metre
  figure is weighted — total current cold rent divided by the area actually let for money, never the
  mean of per-unit prices — and is `null` with "Noch keine vermietete Fläche" when no area is let,
  never `0,00 €`;
- each unit carries exactly one state at `asOf`: `RENTED`, `VACANT`, `SELF_USE` or `GRATUITOUS`. A
  missing tenancy is no longer read as vacancy; `SelfUsePeriod` supplies the two self-use states and
  a running lease outranks them. Overlapping tenancies are surfaced on the row and suppress that
  unit's rent instead of being hidden behind an arbitrarily chosen party;
- balances come only from the authoritative `receivable` rows — `Keine Forderung`, `Ausgeglichen`
  or `N € offen`. Nothing here sums bank transactions into a payment, and **no receivable is
  generated**: the recurring rent claim and due-date rules live in `07_Zahlungen.md` and are not
  built, so an absent claim stays absent (OD10 `MUSS-INPUT`);
- facts are limited to what a module already owns: an open receivable per unit, and a move in or out
  inside a 90-day window. Severity and order are decided server-side. Statement readiness, payments
  under review and guard-derived meter hints have no persisted projection yet and produce no fact,
  rather than a guessed one;
- `GET /a/{account_id}/buildings/{building_id}/overview.pdf` renders the object overview from the
  same projection. It is owner-only and refused server-side, the renderer in
  `packages/pdf/src/lokara_pdf/building_overview.py` only formats supplied strings, and the document
  states in its footer that it is neither a Betriebskostenabrechnung nor a legal notice. The filename
  carries the object name and `asOf`; party names never enter it.

**Intentionally absent, and why.** "Objekt bearbeiten" has no control: the API exposes no building
update route and UI-03 shipped only creation wizards, so the button would link to a 404. Per-unit
usage type (OD5's split of Wohnen and Gewerbe) has no authoritative field — deriving it from a label
like "Büro" is exactly the guess the spec forbids — so the single weighted figure stands. "Vorgänge"
is omitted entirely rather than shown as an empty counter, and contacts, documents and object
activity stay absent until real persistence exists. The three demo objects of OD18 depend on the
portfolio seed, which is not implemented; the seed still carries one building.

This step was implemented under the direct implementation mode in `CLAUDE.md` § 10: ruff, strict
mypy, typecheck, lint and the production build pass, and no test suite ran, so it is
**implemented; unverified — no test evidence**.

## Shipped API surface

There is one FastAPI application. Its current route families are:

- `/health` and the environment-gated `/auth/dev-token`;
- subject-only `/me`, fixed-account `/demo/{load,reset}` and `/calc/nk` routes;
- `/a/{accountId}` summary, portfolio overview and fixed demo-statement/PDF routes;
- `/a/{accountId}` building, unit, tenancy, cost/allocation-key, meter/reading, heating-cost and
  extraction routes;
- `/a/{accountId}` bank, receivable and Page-01-handoff routes (M6-C2, owner-only).
- `/a/{accountId}` guards, guard runs, schedules, reminders, checklists and deliveries (prepared
  M9). Owners control sends and legal confirmation; employees are assigned-building scoped for
  guards/checklists; tax advisers have no M9 access.

There is no shipped bootstrap API route. JSON uses camelCase at the client boundary and snake_case
inside Python; Pydantic validates the backend boundary.

## Shipped authentication — Auth in one api.ts interceptor

- JWT verification accepts the web's HttpOnly `lokara_access_token` cookie or a Bearer token through
  the same API dependency. Future mobile uses that Bearer path with secure storage.
- JWTs carry only the verified Person subject. For every `/a/{accountId}/…` route, authorization
  comes from the URL and a live database Membership, never a token account claim. The request then
  sets its transaction-local RLS context from that URL value.
- `/me`, fixed-account demo bootstrap and `/calc/nk` remain bounded exceptions. `/me` exposes all
  live account contexts for its verified subject but grants none. The web switcher uses only those
  contexts as ordinary `/a/{accountId}` links, so every destination is authorized again by the API.
- On shipped `main`, `OWNER` retains the owner portal and `EMPLOYEE` access is restricted to assigned
  buildings; zero assignments expose no building data. Shipped M7 redirects `TAX_ADVISOR` account
  routes to `/a/{accountId}/steuern`, where the API permits reads plus adviser-profile/mapping writes
  only. The redirect is a convenience; `tax_account_session_for_path` re-verifies membership and
  `authorize_tax_action` re-checks the role on every request. The web hides building creation and
  demo load/reset for employees; this is usability, never authorization.
- The web client performs one single-flight refresh for concurrent 401 responses and replays each
  failed request once. A second 401 is returned; it does not loop.
- `ENVIRONMENT` is required. In `staging` and `production`, API startup refuses enabled dev-token
  minting, enabled demo seeding or the development secret published in `.env.example`.

Local login still uses the explicitly enabled dev-token route; no real Supabase Auth project is
wired. Demo load/reset also require their explicit flag and operate on the fixed demo account.

## Shipped M5 identity and portal entry

**Shipped on `main`:** `app_bootstrap_contexts(text)` and migration `0014` define one bounded
pre-context identity read. `GET /me` supplies the live contexts for the URL-based chooser and
switcher; no account is stored in the token or client session. M5 account switching was merged as
`a748729`. On `main`, a tax-adviser URL still shows “Steuerfunktionen werden vorbereitet”. Prepared
M7 replaces that state with the restricted `/steuern` workspace, but the branch is unmerged and
RED. `docs/02-data-model.md` owns the detailed function, role, policy, privilege and call-site
contract.

## M7 tax workspace

Merged M7 adds `/a/{accountId}/steuern`, a minimized tax-building list, normalized AfA inputs,
temporal self-use, profile/mapping forms, readiness and immutable-history evidence, and selection of
Anlage-V PDF, Anlage-V CSV or DATEV. Owner has full M7 access; adviser has read plus profile/mapping
writes; employee has none. The web suite passes `106` tests and the server generates every artifact
itself. The route is shipped, but it is not production export availability: real generation is
refused with `Export gesperrt: Die Quellen müssen zuerst geprüft werden.` while its register values
remain `verify-before-production`, and the workspace has no seeded adviser persona.

## Shipped statement and M6-B archive boundary

The current statement route is the fixed 2025 **Vermieter-Gesamtübersicht**: a landlord-only,
building-wide calculation/QA preview. It is not a Mieter-Einzelabrechnung and must not be sent to a
renter. A period longer than 12 months hard-blocks before calculation or rendering.

M6-A/M6-B ship owner-only controls for confirmed actual advances, Saldo, immutable/versioned
finalization, history and stored-document download. The separate tenant archive is independently
rendered and isolated, but is not a renter route, portal item, email/delivery feature or
legal-production approval. The live demo PDF remains unchanged.

## Bank and payment boundary: shipped through locally merged C3a

Four owner-only routes, all under `/a/{accountId}` and all behind `require_owner` on top of the
membership check the path session already performs. The URL naming an account is never
authorization by itself, and every relationship the URL carries is verified — the bank account in
the import route is looked up under the RLS-scoped session and 404s when it belongs to someone
else.

| Route | Contract |
| --- | --- |
| `POST /a/{accountId}/statements/{statementId}/receivables` | `BANKMATCH-F12`: a finalized `RECEIVABLE` settlement becomes an `nk_nachzahlung` receivable at exactly the settled cents. Copied, never recomputed. Refuses a second run for the same statement, a correcting version for a tenancy period that already has one, and a joint tenancy with more than one party. |
| `GET /a/{accountId}/receivables` | Open debts, ordered by due date. |
| `POST /a/{accountId}/bank-accounts/{bankAccountId}/transactions/import` | Pulls normalized transactions from the AIS adapter. An exact re-import of `provider_transaction_id` is skipped, not rejected. |
| `GET /a/{accountId}/bank-transactions` | Imported movements, signed cents. |

**The due date is a request field with no default.** `docs/08` flags *Zahlungsfrist bei
Nachzahlung* `verify-before-production`: the register records no statutory deadline — the claim
falls due on receipt of a proper statement — and the customary 30 days is a `Konvention`. The
handoff asks for the date and refuses without it rather than making that convention Lokara's
answer on every statement.

The C3a slice adds exactly five further owner-only API routes:

| C3a route | Contract |
| --- | --- |
| `PUT /a/{accountId}/renters/{renterId}/matching-profile` | Normalize and upsert surname and optional payment code. |
| `POST /a/{accountId}/bank-transactions/{transactionId}/match` | Run or return the transaction's immutable proposal run. |
| `GET /a/{accountId}/match-proposals` | Return transaction-grouped German reasons, lowercase decisions, ranked candidates, confirmation and ledger reference. |
| `POST /a/{accountId}/bank-transactions/{transactionId}/decision` | Record one final `confirmed`, `rejected` or `duplicate` outcome; the client cannot select a receivable. |
| `GET /a/{accountId}/payment-ledger` | Return immutable payments, reversals, credit and allocation snapshots newest first. |

These five routes and `matching_service.py` are technically complete, development-synchronized and
locally merged into `main`. C3b's three jobs are technically complete and locally merged; they add no route and no
screen.

C3c adds the one *Zahlungen* client route, `/a/{accountId}/zahlungen`, technically complete and
locally merged. It is client-only — no endpoint, no schema, no migration. It reads
the grouped proposals, the payment ledger, the bank transactions and the receivables, and writes one
final outcome through the C3a decision route. Buttons appear only on an open `NEEDS_REVIEW` row;
everything else is read-only evidence and the Zahlungsjournal has no edit, delete or reversal
control. No renter name is displayed: no route resolves a `renter_id` to a `legal_name`, so the
payer is identified by the bank `counterpart_name` and `purpose`. The nav entry is hidden for
`EMPLOYEE` because every route behind it is `require_owner` — navigation honesty, not
authorization.

Migration `0020` closes the M6-C3-0 invariant repair below these routes: signed and locked
allocation caps, renter-consistent reversals, confirmed transaction provenance for learned IBANs,
qualified trigger lookups, and observable RLS `WITH CHECK` enforcement. It changes no HTTP route or
public model. C3a joins the pure engine to these tables on local `main`. The final amended `0021` is
verified from `lokara_c3a_check`; development matches its column, constraint, trigger and
hardened-function catalog exactly after the validated transactional hand-delta.

## Shipped Beleg-Upload boundary

`POST /a/{accountId}/buildings/{buildingId}/extractions` accepts PDF/PNG/JPG files up to 10 MB and
returns a proposal from the named stub provider. Extraction writes nothing server-side. The proposal
and review-form corrections are retained in account/building-scoped browser `localStorage`, so a
reload can restore the unfinished review.

Confirmation uses the ordinary cost-creation route and creates an ordinary `CostEntry` plus its
allocation-key assignment. No Beleg file, invoice date, vendor, archive record or hash is persisted.
The extracted category is only an editable free-text label; no cost type or allocation key is
inferred as law.

`docs/09-betrkv-catalogue.md` owns the BetrKV catalogue. Slice C technically implements
classification, catalogue-backed defaults and the owner residual; its flagged authority remains
production-blocking.

## Future architecture

- M10 renter activation, `/renter/{tenancyId}`, renter-portal isolation and account-safe portal
  access are **Future**. Adviser profile, account mapping and tax functions are prepared in M7 but
  remain unmerged and incomplete.
- `apps/mobile` is **Future** at M10: Expo/React Native, the same API verification through Bearer JWT,
  secure storage, TanStack Query, Jotai, React Hook Form/Zod, i18n and shared mobile
  theming/patterns. No shared mobile UI package exists today.
- Pure KPI packages and W3/W5–W8 guard extensions wait for their approved specs and owning
  milestones. Pure AfA/export packages are prepared on the M7 branch, not shipped.
- Redis plus Celery or Arq wait for a real rate-limit, retry, sync or scheduled-delivery slice.
- Real Supabase Auth/Storage/Postgres credentials and real Vision, bank, email and MDL providers wait
  for their integration and hosting/DPA decisions and stay behind adapters.

Named future choices are not installed dependencies or shipped capabilities.

## Binding UX invariants

- One primary action, explicit labels, calm 8px-based spacing and visible loading, error and empty
  states.
- **no data loss:** unfinished web forms use account-scoped browser drafts today; a successful submit
  clears the draft. Changing an allocation-key assignment appends history and does not delete the
  entered cost.
- Destructive mutations require clear intent. Legally immutable evidence appends or versions instead
  of overwriting.
- Keyboard access, visible focus, 200% zoom, contrast and reduced-motion requirements follow
  `docs/05-design-system.md`.
- Motion is CSS-based today. Framer Motion is selected but not installed; its first use must add and
  verify it explicitly.
