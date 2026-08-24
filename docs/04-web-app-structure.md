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

## Prepared but unmerged repository structure

`packages/guard-engine` is an explicit uv member on `slice/g-shared-guard-foundation`. It contains
pure W1, W2 and W4 evaluators and is absent from `main`. It has no API route, web/runtime consumer,
database record, scheduler, provider, delivery path or PDF projection.

`apps/mobile`, AfA/export/KPI engines, Redis and workers are absent. Real Supabase, Vision, bank,
email and MDL providers are also absent; current external edges use local infrastructure or stubs.
These are **Future**, not empty shipped modules.

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

Page 8 is owner-only, in navigation as well as in the API; see the C3c paragraph under
"Shipped API surface" below.

`/styleguide` is a separate shipped design-token/stack showcase and is not one of the numbered
pages. Neither is `/`, which enters a sole
`OWNER` or `EMPLOYEE` context and otherwise offers the caller's live contexts as URL links. A sole
`TAX_ADVISOR` context is selected deliberately rather than
entered automatically.

## Shipped API surface

There is one FastAPI application. Its current route families are:

- `/health` and the environment-gated `/auth/dev-token`;
- subject-only `/me`, fixed-account `/demo/{load,reset}` and `/calc/nk` routes;
- `/a/{accountId}` summary and fixed demo-statement/PDF routes;
- `/a/{accountId}` building, unit, tenancy, cost/allocation-key, meter/reading, heating-cost and
  extraction routes;
- `/a/{accountId}` bank, receivable and Page-01-handoff routes (M6-C2, owner-only).

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
- `OWNER` retains the owner portal. `EMPLOYEE` access is restricted to assigned buildings; zero
  assignments expose no building data. `TAX_ADVISOR` may use `/me` but current owner-portal routes
  are denied server-side and render the web preparation state instead. The web hides building
  creation and demo load/reset for employees; this is usability, never authorization.
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
`a748729`. A tax-adviser URL deliberately shows “Steuerfunktionen werden vorbereitet” rather than
owner navigation or content. `docs/02-data-model.md` owns the detailed function, role, policy,
privilege and call-site contract.

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

`docs/09-betrkv-catalogue.md` now **Specifies** the BetrKV catalogue. Production classification and
catalogue-backed default-key suggestions remain unimplemented.

## Future architecture

- M10 renter activation, `/renter/{tenancyId}`, renter-portal isolation and account-safe portal
  access are **Future**. Adviser profile, account mapping and tax functions remain **Future** M7
  work; the current adviser preparation state is not a tax route.
- `apps/mobile` is **Future** at M10: Expo/React Native, the same API verification through Bearer JWT,
  secure storage, TanStack Query, Jotai, React Hook Form/Zod, i18n and shared mobile
  theming/patterns. No shared mobile UI package exists today.
- Pure AfA/export/KPI packages and W3/W5–W8 guard extensions wait for their approved specs and
  owning milestones.
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
