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
and `/a/{accountId}/waechter`. M9 technically closed with clean reviews on 29.08.2026;
production blockers remain. The later checkpoint has separate verification recorded in `PLAN.md`.

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

## Owner UVI workspace — technically complete locally

The contract below was implemented and technically verified on `slice/uvi-owner-ui` as of
11.09.2026 and is locally merged into `main` as `f576a50`. Full checks, production build, the non-fresh demo path and
bounded UI/boundary reviews pass. Responsive/keyboard and 200% CSS scaling checks pass. Live
metadata and missing-configuration handling are verified; browser success states use intercepted
responses, while backend/PDF suites cover generation, archives and rendering. The existing demo
account has no configured monthly UVI success case. Production restrictions remain unchanged;
see `PLAN.md` and `HANDOFF.md` for evidence and limits.

The mobile shell uses compact 72px icon navigation below 768px without replacing the stored
desktop preference. The UVI form permits wrapped controls/actions and reserves header space for
the reminder bell. The default month derives from the server workspace timestamp.

The owner entry `UVI` sits after `Zähler` in the sidebar and opens
`/a/{accountId}/uvi`, titled **Verbrauchsinformation (UVI)**. Employees and tax advisers have
no UVI navigation or generation controls; the existing owner authorization on both backend
endpoints remains decisive. This bounded UI exposes the U5 generation/download contract in
`docs/16` §§ 10–12; it changes no calculation, legal value, authority flag or Rechtsstand.

- Inputs are **Objekt**, **Einheit**, **Mietverhältnis** and **Monat**. The first three use
  live account-scoped `GET /a/{accountId}/meter-workspace` metadata, including tenancy dates.
  No fixture or synthetic reading is submitted as an input. Changing the object clears unit
  and tenancy; changing the unit clears tenancy. Any selection/month change hides the prior
  result so another tenancy or month never appears to own its PDF.
- One explicit primary action, **UVI erstellen / öffnen**, calls
  `POST /a/{accountId}/buildings/{buildingId}/uvi-runs` with exactly `tenancyId` and
  `targetMonth`; the month control's `YYYY-MM` becomes `YYYY-MM-01`. No generation occurs on
  page load or selection. Pending generation disables duplicate submits. HTTP 200 reopens the
  existing archived tenancy/month run; HTTP 201 creates it using the same backend contract.
- The validated response carries `runId`, `documentUrl`, `productionBlocked` and
  `unresolvedConflicts`. **PDF herunterladen** uses the authenticated API transport base
  (default same-origin `/api/backend`) and the returned account-scoped document path. A blocked
  response shows **Nicht für den produktiven Versand freigegeben**, all returned conflicts and
  **Es wird keine E-Mail versendet.** A downloaded engineering PDF does not clear any production
  blocker. Generation errors, including HTTP 422 and its server detail, are visible and retryable;
  no success/PDF is fabricated for failed requests.
- Portfolio preview is read-only for this workflow: show a clear **Vorschau** notice, suppress
  generation and PDF success, and provide a full-navigation link **Live-Daten öffnen** to the
  same account's `/uvi?preview=0`. If the environment forces preview, that flag still wins and
  the UI must not claim the link can override it. Unsupported preview mutations must never
  fall through to the real backend.
- Loading, retryable metadata failure and empty object/unit/tenancy states use explicit German
  copy. Labels, focus, contrast, spacing and the single primary action follow `docs/05`.

No scheduler, email send, renter portal publication, new history endpoint, ingestion wizard,
engine, schema or backend input change is authorized by this UI contract. The `docs/16` production
authority/content/cadence limitations and M9's missing frozen delivery artifact remain open.

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
  the coordinates stay nullable. UI-03 migration `0026` and M9 migration `0025` are parallel
  children of `0024`; empty merge revision `0027` joins them on `development`;
- `POST /a/{accountId}/buildings` accepts `buildingType`, `isResidential`, `houseNumber` and
  `country`, joins street and house number into the existing single `street` column, and keeps the
  German five-digit `postal_code` rule unchanged. `BuildingSummary` gains `buildingType`, `latitude`
  and `longitude`;
- geocoding lives behind `lokara_adapters.geocoding.GeocodingGateway`.
  `PlzGeocodingGateway` is the production default: it resolves the building's exact five-digit PLZ
  offline from the pinned vendored centroid dataset, and an unknown or malformed PLZ fails loudly
  with `422` before the building is created. `geocoding_enabled` is **off** unless an operator turns
  it on; when enabled, Nominatim is only an optional finer-precision address fallback after the PLZ
  has resolved, because the public provider is demo-only and has no SLA. The adapter package owns
  the provider format — query parameters, User-Agent, response shape and coordinate validation —
  and stays socket-free, the same line `dwd.py` draws; the HTTP transport, timeout,
  one-request-per-second policy and response cap live in
  `apps/api/src/lokara_api/geocoding_http.py`, the only place that speaks to the provider. It is
  server-side only and returns `None` on any provider error, timeout, empty result or blocked
  network, so optional address refinement never blocks creation and the offline PLZ centroid remains
  the fallback;
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

This step was implemented under the former direct implementation mode. Later checkpoint full/demo
gates are green (05.09.2026: `1967` Python, `188` web tests), with clean boundary and focused
statement/UI re-reviews. It is **implemented; partially verified**; the separate live-browser
acceptance matrix remains outstanding.

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
activity stay absent until real persistence exists. The portfolio seed now supplies the three OD18
demo objects; the remaining absent modules still wait on real persistence.

This step was implemented under the former direct implementation mode. The 05.09.2026 checkpoint
full/demo gates now supply automated evidence, with clean boundary and focused statement/UI
re-reviews. It remains **implemented; partially verified** pending the separate live-browser matrix
and its recorded source-blocked scope.

## UI-07 payment workspace on `development`

UI-07 replaces the earlier browser join with owner-only server projections:

- `GET /a/{account_id}/payment-workspace/accounts` returns connected account labels, masked IBANs,
  provider labels and consent state. The current model has no persisted sync-run record, so
  `last_sync_at` stays `null` and sync stays `idle`; productive finAPI OAuth, reconnect and provider
  configuration remain source-blocked;
- `GET /a/{account_id}/payment-workspace/transactions` returns one authoritative row per immutable
  bank transaction, including transactions without proposals. It uses stable booking-date/ID order,
  an opaque row-ID cursor, 50-row pages, a 100-day default window, server counts,
  account/search/date/direction/status filters, renter/unit/building context and
  ledger/classification history;
- `POST /a/{account_id}/bank-transactions/{transaction_id}/classification` and the page-local bulk
  route append `IGNORED` or `RESTORED` events. They never rewrite a bank transaction and refuse a
  booked ledger transaction. Migration `0030` supplies the account-scoped composite FK, ENABLE/FORCE
  RLS with `WITH CHECK`, and an update/delete refusal trigger;
- `/a/{accountId}/zahlungen` renders one compact list, server counts and filters, a single inline
  current-account/consent summary, page-local safe selection, and a 400px right detail drawer with
  Escape close and focus return. It deliberately does not render one status card per Mietkonto;
  the default all-account view shows only the nearest consent expiry, while a selected account shows
  its own masked IBAN and expiry. Existing review proposals can still be confirmed through the
  shipped matching service. Unit dashboards expose the same account-scoped workspace to owners;
- the seed persists three property-labelled Mietkonten and 50 traceable rows over roughly 100 days.
  Three prior rent months contribute 33 settled payments and nine classified outgoing movements;
  the current month retains full, partial, review, unmatched, possible-duplicate and ignored cases.
  The default list reads all three accounts; the account filter scopes the same server projection.
  Re-seeding restores the visible ignored state by appending evidence; it does not erase prior
  classification history.

The source's `MUSS-INPUT` rules remain binding. UI-07 does not invent recurring rent due dates or
joint-liability rules, a post-rejection manual-assignment meaning, later credit use, cash receipt
evidence, or productive finAPI configuration. The free manual-assignment/payment wizard,
overpayment decision flow, historical anomaly engine and complete shared account/object/reminder
aggregates are also unfinished. The primary “Zahlung erfassen” action therefore stays disabled.
The later checkpoint full/demo gates pass, and focused web regressions and the statement/UI
re-review cover drawer focus trapping, background suppression and valid navigation controls.
The complete live-browser/zoom/accessibility matrix remains outstanding; UI-07 remains a partial
demo core, not a completed payment specification.

## Shipped API surface

There is one FastAPI application. Its current route families are:

- `/health` and the environment-gated `/auth/dev-token`;
- subject-only `/me`, fixed-account `/demo/{load,reset}` and `/calc/nk` routes;
- `/a/{accountId}` summary, portfolio overview and fixed demo-statement/PDF routes;
- `/a/{accountId}` building, unit, tenancy, cost/allocation-key, meter/reading, heating-cost and
  extraction routes;
- `/a/{accountId}` bank, receivable and Page-01-handoff routes (M6-C2, owner-only).
- `/a/{accountId}` guards, guard runs, schedules, reminders, checklists and deliveries (implemented
  M9; technical close 29.08.2026). Owners control sends and legal confirmation; employees are assigned-building scoped for
  guards/checklists; tax advisers have no M9 access.
- Owner-only `POST /a/{accountId}/buildings/{buildingId}/uvi-runs` creates an archived run (`201`)
  or returns the existing account/tenancy/month run (`200`) without another generated event.
  `GET …/uvi-runs/support/{supportCode}` resolves support evidence in the authorized scope;
  `GET …/uvi-runs/{runId}/document` renders the archived document snapshot as a PDF. This download
  is not the frozen byte artifact required for M9 UVI delivery.

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
`a748729`. The restricted `/steuern` workspace is present. Deferred M7-F repairs are integrated on
`development`, but remain unverified and production-blocked. `docs/02-data-model.md` owns the
detailed function, role, policy, privilege and call-site contract.

## M10-R2 renter entry — implemented and verified

M10-R0 fixes the renter boundary; `docs/02-data-model.md` owns the full data and refusal contract.
M10-R1 activation is shipped. Migration `0042`, the R2 overview route and the renter RLS context
are implemented and verified on `slice/m10-r2-renter-context`; the M10-R3 publication boundary and
M10-R4 portal UI remain pending. All `116` focused DB/API/checker tests pass; RLS covers `76`
tables, FK isolation covers `152` edges and the pre-context checker is clean. The mandatory
boundary audit is clean with rollback-only probes, and the full gate passes `2021` Python and `210`
web tests. No `.lokara-red` sentinel remains; migration `0043` remains pending.

- `/me` keeps its existing `accounts` list unchanged and adds `renterContexts`; each item contains
  only `tenancyId`. A dual-role Person receives both. The same bounded
  `app_bootstrap_contexts(text)` function returns explicitly typed `SUBJECT`, `MEMBERSHIP` and
  `RENTER_TENANCY` rows. A second pre-context identity read is forbidden.
- Renter pages live under `/renter/{tenancyId}/...`, never `/a/{accountId}`. The API proves the
  authenticated Person → Renter → TenancyParty → exact URL tenancy chain before deriving the
  account internally and setting transaction-local `app.account_id` plus `app.tenancy_id`.
- The owner/staff/tax session helper and every `/a/{accountId}` route remain unchanged. The context
  switcher lists renter destinations only when the authenticated Person has them; a link itself
  grants no access.
- `GET /renter/{tenancyId}` is the R2 overview endpoint. It returns exactly `tenancyId`,
  `validFrom`, `validTo`, `unitLabel`, `buildingName`, `street`, `postalCode` and `city`. It exposes
  no account/unit/building/Person/Renter id, party list, rent/payment, cost, meter, bank, guard,
  owner finding, tax or raw-evidence field.
- The database read allowlist in R2 is exactly the context tenancy, its unit and its building.
  All renter-context writes are refused. Same-account other-tenancy denial is proved at the API
  and by a rollback-only RLS probe with the application query filter removed.
- Publication copies already archived bytes, hash, MIME type and filename into one append-only
  tenancy-scoped portal record. Statement sources are `TENANT` cover-letter or tenant-statement
  archives; UVI sources must be blocker-free frozen artifacts. A download reads and verifies only
  the publication bytes. Nothing is recalculated, re-rendered or selected from source rows or raw
  `uvi_run` JSON for a renter.
- Drafts, merely generated or emailed artifacts, production-blocked artifacts, owner overviews,
  other parties and every other tenancy remain invisible in both application authorization and
  RLS. The landlord's all-party calculation view is never a portal source.
- `renter.person_id` has one positive writer: successful single-use activation redemption. After
  activation it is immutable; a genuine correction appends separately approved evidence rather
  than updating or clearing the link.

The activation service contract has seven enumerated refusal fixtures in `docs/02`: spent, expired,
wrong tenancy, wrong account, already-linked Renter, unknown Person and unknown code. Every refusal
uses one non-success HTTP status, externally equalized processing and the same public text; there is
no format-specific prevalidation that reveals code existence. The real reason is owner-audit
evidence only.

Berkay approved `M10-COPY-01…06` on 11.09.2026. The exact activation, success, generic-refusal,
context-switcher, navigation, heading, PDF-action, loading, empty and error strings are owned by
`docs/02`. The UI uses them verbatim, keeps the **Sie** form, names
„Vermieterin oder Vermieter“, uses no gender punctuation or Anglicisms and shows no amount,
co-renter name or unrelated object data in navigation. M10-R4 is no longer copy-blocked; its schema,
API and UI remain unimplemented.

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

### UI-05A development workflow — implemented, partially verified

On `development`, UI-05A extends page 6 without replacing the M6-B archive model:

- `/a/{accountId}/abrechnung` lists resumable drafts and finalized versions;
- `/a/{accountId}/abrechnung/neu` creates a building/period-scoped draft;
- `/a/{accountId}/abrechnung/{draftId}` is the six-step, autosaving workflow;
- `/a/{accountId}/abrechnung/archiv/{statementId}` reads stored versions and starts a linked
  correction draft without changing predecessor bytes.

The owner-only API adds statement records, period suggestions, version-checked draft create/read/
update/cancel/finalize operations and a server-owned readiness projection. A readiness status
change advances the same optimistic version; unexpected server faults remain server errors instead
of being presented as incomplete billing inputs. Draft previews use
`GET /a/{accountId}/buildings/{buildingId}/statements/preview.pdf` with one explicit tenancy and
either `COVER_LETTER` or `TENANT_STATEMENT`. Finalization still uses the existing M6-B route and now
archives one owner overview plus a separate cover letter and tenant statement per eligible tenancy.
Downloads return stored bytes and hashes; no archive page recalculates a document.

M9 annual-statement delivery accepts only archived `TENANT_STATEMENT` documents. A separately
archived `COVER_LETTER` is never a complete annual statement source.

Migration `0028` adds the account/building-scoped `statement_draft` table with ENABLE/FORCE RLS and
a `WITH CHECK` policy, and adds the archived document type without rewriting append-only rows.
Unresolved Page-02 authority remains a visible warning: affected technical-demo PDFs carry a
non-production watermark. Email delivery and renter-portal actions remain inactive. This work was
built in the former direct implementation mode. The later full/demo gates and clean boundary and
focused statement/UI re-reviews add verification evidence; the separate interactive-browser matrix
and source-blocked scope remain open.

### UI-05B unit dashboard — implemented, partially verified

`/a/{accountId}/einheiten/{unitId}` now consumes
`GET /a/{account_id}/units/{unit_id}/dashboard`. One server-owned `asOf` resolves the unit state,
current tenancy, every separate party, current cold rent, current advance, total monthly amount,
rent per square metre, contract positions, newest-first occupancy history, allowed actions and up
to five existing finalized tenant archives. The browser displays these decisions and does not use
its clock to rebuild gaps or financial values.

The current tenancy precedes a collapsed history. Unit profile and tenancy-create forms appear only
after an owner action; they are not permanent side panels. Profile writes append a
`UnitProfileVersion`. Separate owner-only endpoints append contract versions, garage/parking
positions and documented rent changes. The UI converts an inclusive “Letzter Miettag” to the
database's exclusive end boundary at the form edge. Unknown legacy facts stay “Nicht dokumentiert”.

UI-07 now supplies the owner-only payment projection from existing receivable facts. The renter
portal waits until M10, and messages until a real model and policy exist. Documents list only stored immutable archives and
offer no upload control. Migration `0029` supplies the four account-scoped temporal tables. Ruff,
strict mypy, web lint, typecheck, production build, local migration/seed and an authenticated live
API read pass. Later checkpoint full/demo gates and clean boundary/focused statement/UI re-reviews
provide partial verification. The separate live-browser acceptance matrix remains outstanding.

### UI-06 Kosten — implemented, partially verified

`/a/{accountId}/kosten` is now a full-width, object-local list with one billing-year filter and a
dedicated `/a/{accountId}/kosten/neu?objektId={buildingId}` creation route. Cross-year entries appear
in every touched year. The wizard keeps its account/object-scoped browser draft, separates the
server-owned BetrKV identity from an optional display label, applies the catalogue default key and
sends `keyOverride` only when the owner changes it. Receipt extraction is visible only as an
inactive beta mode; its existing route remains available but is no longer in navigation.

`GET /a/{accountId}/cost-catalogue` exposes the current versioned catalogue's display facts. Cost
responses expose the persisted classification findings and `productionBlocked`; the client only
maps those server codes to German display copy. `POST /a/{accountId}/costs/{costId}/void` is the sole
list removal action and requires a reason. The broken hard-delete client path is gone.

Migration `0031` permits a confirmed non-allocable classification to omit an allocation-key
assignment. Such a cost persists with zero allocable cents and is skipped before renter-allocation
input is built; no fallback key is invented and no engine formula changes. The local migration,
allocable create with an effective override, non-allocable create, active-list read and reasoned
void flow pass. An active non-allocable probe left the statement's 120,000-cent NK input and sole
allocable cost unchanged before it was voided. Ruff, strict mypy, web lint, typecheck and production
build pass. The later full/demo gates and focused copy/navigation regressions are green, and the
statement/UI re-review is clean. The complete interactive browser/zoom/accessibility matrix remains
outstanding.

### UI-08 Zähler — implemented, partially verified

`/a/{accountId}/zaehler` now reads one account-scoped workspace containing every visible,
non-archived object, every unit including empty ones, building/unit meters, lifecycle history,
calibration guards, readings and server-projected consumption periods. The full-width accessible
hierarchy is object → building meters/units → meter. Active and historical devices are separated;
the backend-owned expired list drives the focus-safe previous/next jump. Owner writes are absent in
read-only views.

`/a/{accountId}/zaehler/neu` is one route and one form with an account/object-scoped draft. It
collects the explicit device type, fixed server-validated unit, exact location and own label,
manufacturer/model, installation date, remote-readability and distinct calibration-data states.
Replacement is one API transaction linking both devices and appending old-final/new-initial
readings. Removal and controlled void append lifecycle events; no meter DELETE route remains.

Manual readings use today's local date, show the current device and last effective value, and run a
server preflight for lifecycle, duplicate-date, rollback, correction-target and tenancy context.
Warnings require explicit confirmation and persist that confirmation; blockers cannot be written.
Corrections append a linked successor. Available periods and measured/incomplete/estimated/
not-applicable consumption evidence come from the backend, including exact opening and closing
rows, missing-input reason and estimate provenance.

Per object/period, append-only `HeatingBillingModeVersion` rows select Lokara or an external
provider. An external result becomes authoritative only through the existing confirmed MDL
statement path in the same object and period; the statement service suppresses the parallel
internal result. Internal heating inputs are categorized, source-linked and backend-readiness
projected. Radio connectivity, provider sync and upload/OCR remain intentionally inactive; the OCR
segment is disabled and has no file input or request.

Migrations `0033`/`0034` add the approved gas-volume tuple and split conversion evidence. Migration
`0040` closes nullable reason/confirmation/provider checks and permits heating-cost updates only
for the first reasoned void; invoice evidence cannot otherwise change or be deleted. All 20
rollback-only boundary regressions pass, and the boundary re-audit is clean. The 05.09.2026
full/demo gates pass `1967` Python and `188` web tests; focused GAS/navigation checks and the
statement/UI re-review are green. The required 1280/1440/1920 px, keyboard and 200% zoom matrix
remains outstanding, so this is partial verification, not complete UI-08 closure.

## Bank and payment boundary: shipped through locally merged C3a

Four owner-only routes, all under `/a/{accountId}` and all behind `require_owner` on top of the
membership check the path session already performs. The URL naming an account is never
authorization by itself, and every relationship the URL carries is verified — the bank account in
the import route is looked up under the RLS-scoped session and 404s when it belongs to someone
else.

| Route                                                                   | Contract                                                                                                                                                                                                                                                                                                       |
| ----------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `POST /a/{accountId}/statements/{statementId}/receivables`              | `BANKMATCH-F12`: a finalized `RECEIVABLE` settlement becomes an `nk_nachzahlung` receivable at exactly the settled cents. Copied, never recomputed. Refuses a second run for the same statement, a correcting version for a tenancy period that already has one, and a joint tenancy with more than one party. |
| `GET /a/{accountId}/receivables`                                        | Open debts, ordered by due date.                                                                                                                                                                                                                                                                               |
| `POST /a/{accountId}/bank-accounts/{bankAccountId}/transactions/import` | Pulls normalized transactions from the AIS adapter. An exact re-import of `provider_transaction_id` is skipped, not rejected.                                                                                                                                                                                  |
| `GET /a/{accountId}/bank-transactions`                                  | Imported movements, signed cents.                                                                                                                                                                                                                                                                              |

**The due date is a request field with no default.** `docs/08` flags _Zahlungsfrist bei
Nachzahlung_ `verify-before-production`: the register records no statutory deadline — the claim
falls due on receipt of a proper statement — and the customary 30 days is a `Konvention`. The
handoff asks for the date and refuses without it rather than making that convention Lokara's
answer on every statement.

The C3a slice adds exactly five further owner-only API routes:

| C3a route                                                        | Contract                                                                                                              |
| ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `PUT /a/{accountId}/renters/{renterId}/matching-profile`         | Normalize and upsert surname and optional payment code.                                                               |
| `POST /a/{accountId}/bank-transactions/{transactionId}/match`    | Run or return the transaction's immutable proposal run.                                                               |
| `GET /a/{accountId}/match-proposals`                             | Return transaction-grouped German reasons, lowercase decisions, ranked candidates, confirmation and ledger reference. |
| `POST /a/{accountId}/bank-transactions/{transactionId}/decision` | Record one final `confirmed`, `rejected` or `duplicate` outcome; the client cannot select a receivable.               |
| `GET /a/{accountId}/payment-ledger`                              | Return immutable payments, reversals, credit and allocation snapshots newest first.                                   |

These five routes and `matching_service.py` are technically complete, development-synchronized and
locally merged into `main`. C3b's three jobs are technically complete and locally merged; they add no route and no
screen.

C3c adds the one _Zahlungen_ client route, `/a/{accountId}/zahlungen`, technically complete and
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

- M10 renter activation, `/renter/{tenancyId}` and renter-context isolation are implemented and
  verified through M10-R2. Renter document publication and portal screens remain pending in
  M10-R3/R4. Adviser profile, account mapping and tax functions exist, while deferred M7-F repairs
  on `development` remain unverified and production-blocked.
- `apps/mobile` is **Future** at M11: Expo/React Native, the same API verification through Bearer JWT,
  secure storage, TanStack Query, Jotai, React Hook Form/Zod, i18n and shared mobile
  theming/patterns. No shared mobile UI package exists today.
- Pure KPI packages wait for their approved implementation milestone. W3/W5–W8 guard work is
  technically closed on `development` through M9 on 29.08.2026; its production blockers remain. Pure AfA/export packages
  are present; M7-F closure remains deferred.
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
