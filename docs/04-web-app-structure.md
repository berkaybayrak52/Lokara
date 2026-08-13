# 04 — App structure (web + mobile + API)

> **Frontend:** Next.js (App Router) + React + Tailwind + Framer Motion + shadcn/ui (web) and Expo /
> React Native (mobile). **Backend:** FastAPI (Python). Responsive, WCAG 2.1 AA / BFSG. German UI copy;
> English code. This doc defines the polyglot monorepo layout and the M3 routes/pages.

## Polyglot monorepo layout (Bun + Turborepo for TS · uv for Python)

```
lokara/
├─ apps/
│  ├─ web/                     # [TS] Next.js App Router — FRONTEND ONLY, calls apps/api over HTTP
│  ├─ mobile/                  # [TS] Expo / React Native — FRONTEND ONLY, same API, shared patterns
│  └─ api/                     # [PY] FastAPI — the standalone HTTP/JSON API (web + mobile consume it)
│                              #   routers per domain (modular monolith), Supabase-JWT auth +
│                              #   RLS context as FastAPI dependencies; SQLAlchemy/DB layer lives here;
│                              #   Celery/Arq (Redis) workers/webhooks added at M6
├─ packages/                   # mostly [PY] backend packages + one [TS] ui package
│  ├─ nk-engine/               # [PY] M1 — pure NK allocation engine + golden fixtures (pytest)
│  ├─ heating-engine/          # [PY] M2 — heating + CO₂ engine + fixtures
│  ├─ export-engine/           # [PY] M7 — Anlage V + DATEV (pure)
│  ├─ afa-engine/              # [PY] M7 — depreciation (pure)
│  ├─ kpi-engine/              # [PY] M10 — investment KPIs (pure)
│  ├─ rules-store/             # [PY] versioned legal rules/config (HKVO, CO₂ table, Anlage-V lines…)
│  ├─ domain/                  # [PY] normalized value objects shared by engines + adapters
│  ├─ adapters/                # [PY] bank, vision, email, mdl, destatis, datev — ports + stubs
│  ├─ db/                      # [PY] SQLAlchemy models, Alembic migrations, RLS policies
│  ├─ pdf/                     # [PY] HTML→PDF document service (Playwright for Python)
│  └─ ui/                      # [TS] shadcn/ui components themed to the brand tokens (docs/05)
├─ CLAUDE.md
├─ PLAN.md
├─ lokara-arch.md
└─ docs/
```

> **Two workspaces, one repo.** The TS side (`apps/web`, `apps/mobile`, `packages/ui`) is a **Bun +
> Turborepo** workspace. The Python side (`apps/api` + the Python `packages/*`) is a **uv** workspace.
> Because `packages/ui` is TypeScript, the **uv workspace lists its members explicitly** (not a
> `packages/*` glob) so it excludes `packages/ui`. The two workspaces meet only over the HTTP API
> contract — never by importing each other's code.
>
> The Python packages were built **in place** alongside the TS scaffold they replaced (same
> directories, per the v4 migration — `git log --oneline pre-migration..phase-h-done`); that scaffold
> was removed at the end of it, so each directory above now holds exactly one implementation in the
> language its label names.

**Dependency rule:** `engine` packages depend only on `domain`. Nothing in `packages/*-engine`
imports `db`, `adapters`, `ui`, or any vendor SDK. **`apps/api` (FastAPI)** wires engines + db +
adapters and exposes them as HTTP endpoints; **`apps/web` and `apps/mobile` call that API and never
touch SQLAlchemy/DB directly.** `packages/db` is imported by `apps/api` only.

**Rules-store direction:** the shapes of legal rule-values (ratios, tables) live in `domain`;
`rules-store` **depends on `domain`** and supplies the data. Engines **do not import `rules-store`** —
the caller (`apps/api`) resolves the values for the as-of law date and passes them in as parameters. So
the graph is `domain ← rules-store`, `domain ← engines`, and `api → {rules-store, engines, domain}`.

## Feature-based structure (web + mobile)

Inside each client app, organize **by feature, not by type** — a feature folder owns its components,
hooks, state, and API calls (`features/nk-statement/…`, `features/tenancy/…`, `features/renter-portal/…`).
Same convention on web and mobile so patterns transfer. This mirrors the backend's per-domain routers.

## Routing & context (M3 + M5)

- Owner / Employee / Tax-advisor: `/a/{accountId}/…`
- Renter portal: `/renter/{tenancyId}/…`
- Context is **in the URL**, never the session. The left-menu is derived live from the Person's
  relationships and is **navigation only** — every request re-authorizes independently (app + RLS).

## Pages for the pitch vertical slice (M3)

Vermieter portal (`/a/{accountId}`), German labels:

1. **Dashboard** — overview cards (buildings, open statements, deadlines). One-click "load demo scenario".
2. **Objekte** (Buildings) — list → detail; create Building → Unit → Tenancy.
3. **Einheit / Mietverhältnis** — unit detail with tenancy timeline (`validFrom/validTo`), self-use
   periods, meters.
4. **Kosten erfassen** — cost entries; pick allocation key per cost per period (incl. DIRECT); autosave.
5. **Zähler** — meter + reading management (manual entry for the slice; adapters later).
6. **Abrechnung erstellen** — run the NK + heating/CO₂ statement; preview the computed shares +
   reconciliation; **generate PDF**.
7. **Beleg-Upload** (M4, canned) — upload a sample invoice → prefilled fields → confirm.

## UX requirements that are non-negotiable

- **Autosave / no data loss on abort** — an entry-ticket requirement; objego lost users' data.
- **Changing an allocation key never deletes entered data** — re-runs the calc only.
- **Fast + stable**, no perceptible latency — the universal competitor pain point.
- **Understandable "from 7 to 70"** — explicit labels, generous white space, but never hide controls
  or drop contrast for the sake of minimalism (see `docs/05-design-system.md`).

## State & data

- The web + mobile apps call the **FastAPI** service (`apps/api`) over HTTP; the API validates the
  Supabase JWT in a **dependency**, sets the RLS context, and calls the engine packages. No DB access
  from any client.
- **`account_session` dependency = the isolation spine.** It opens the RLS-scoped transaction
  (`app.account_id` GUC, non-owner role) **and** verifies the caller holds a **live `Membership`** in
  the claimed account before yielding — **403** otherwise. That's the "enforced twice" rule made
  concrete: app-logic membership check **and** Postgres RLS on the same request.
- **JSON casing:** the API speaks **camelCase** JSON (Pydantic aliases) to match the TS/Zod clients,
  while Python/DB stay **snake_case** — the Pydantic boundary translates. Engine validation errors
  surface as **422**.
- **Server state → TanStack Query** (caching, refetch, loading/error, request dedup so nothing
  double-fires). **Client state → Jotai** (atomic). **Forms → React Hook Form + Zod.** Same libraries
  on web and mobile.
- **Auth in one `api.ts` interceptor:** web sends the JWT via HttpOnly cookie, mobile via Bearer from
  secure storage. On a 401 the interceptor refreshes once, replays the failed requests, and never
  double-fires — **concurrent 401s share a single in-flight refresh**, and a second 401 surfaces to the
  caller instead of looping. Responses are **Zod-parsed**, so API drift fails loudly. The auth hook
  layer is separate per platform (cookie vs secure storage).
- **The web token never touches JS.** A Next **route handler (`/api/session`)** exchanges credentials
  server-side and sets the **HttpOnly** cookie (`lokara_access_token`) — a small BFF seam, so XSS can't
  read the token. `TODO(supabase)`: swap the dev-token exchange for the real Supabase session at M5.
- **The API accepts either transport, verified identically:** `Authorization: Bearer …` (mobile) **or**
  the HttpOnly cookie (web) — one verification path, two carriers.
- Forms optimistic + autosave; long-running work (PDF, later OCR/bank) goes through API jobs
  (Celery/Arq on Redis from M6).
- All queries scoped by `accountId`; RLS is the backstop from M5. The same API endpoints serve the
  launch-day native iOS/Android apps.

## Statement output

The PDF service (`packages/pdf`) is **one shared service** behind NK, UVI, AfA dossier, Anlage V, and
contracts. For M3 it renders the NK + heating/CO₂ statement with the `Rechtsstand MM/JJJJ` stamp and
the "Tool, keine Rechts-/Steuerberatung" disclaimer.

## Beleg-Upload — upload → prefill → confirm (M4)

`/a/{accountId}/beleg`. One pipeline for NK-receipt OCR **and** later migration import, behind the
Phase D `VisionGateway` port. For the pitch the implementation is `StubVisionGateway`: every upload
returns the canned garbage invoice (€ 1.200,00, Stadtreinigung Frankfurt GmbH, 15.12.2025).

**Endpoint:** `POST /a/{accountId}/buildings/{buildingId}/extractions` (multipart, ≤ 10 MB,
PDF/PNG/JPG). Returns a proposal. **There is no confirm endpoint** — the review form posts to the
ordinary `POST /buildings/{id}/costs`.

### The three rules this screen encodes

1. **Extraction writes nothing.** The response is a proposal; the entry is created only by the
   normal Kosten erfassen call, after a human has seen the values. Web and API share one form
   contract (`features/kosten/cost-form.ts` / `CostCreate`), so a prefilled entry clears exactly the
   bar a typed one does — an OCR miss cannot become a wrong statement unnoticed.
2. **No cost type is invented.** The extracted category becomes the same **free-text label** the
   manual form already takes. Mapping a category to a BetrKV type — and to that type's default
   Umlageschlüssel — needs the **cost-type catalogue, which is a pending spec** (`docs/08`,
   "BetrKV cost-type catalogue"). Until it exists with a `Rechtsstand`, the key is reported in
   `notExtracted` and defaults to the form's own default, visibly.
3. **The provider is named as a stub.** `providerLabel` says so and the UI prints it, so no screen
   can imply an integration that is absent. A real provider (EU processing + AVV, listed
   sub-processor) swaps in behind the same Protocol.

### Confidence is per field

A single document-level score cannot answer the one question the review step exists to answer —
*which* value should I check? The port therefore returns both: `confidence` (how well the document
was read) and `field_confidences` (per value). In the stub `cost_category` sits far below the rest
because it is **inferred, not read**. The `needs_review` threshold lives on the **API**
(`LOW_CONFIDENCE_PERCENT`), so the rule has one home rather than one per client.

### Not yet stored

`vendor_name` and `invoice_date` are extracted and shown, but `CostEntry` has no column for either,
so confirming discards them — the UI says so per field rather than hiding it. They belong to a
**Beleg record** (file + hash + issuer + document date, GoBD / § 147 AO), which needs object storage
and its own spec; it is not part of the canned M4 slice.

### No data loss

The review step is autosaved like every other form (`useFormDraft`), and the **extraction itself**
is persisted alongside it — otherwise a reload would restore corrections into a form that no longer
exists. A new upload replaces both: fresh results must never appear under stale edits.
