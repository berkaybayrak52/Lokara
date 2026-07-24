# 01 — Tech stack & locked decisions (ADR-style)

Every item in `lokara-arch.md` marked "to confirm" gets a **pragmatic MVP default** here so Claude
Code is never blocked. Format: **Decision → Why → Revisit-when**.

## Stack (locked)

| Category                    | Pick                                                                   | Notes                                                                                       |
| --------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| Language                    | **Python** (backend + engines) + **TypeScript** (frontend + mobile)    | Money math in isolated tested Python packages (integer cents + `decimal.Decimal`). See D2.  |
| Repo                        | Polyglot monorepo: **Bun + Turborepo** (TS) + **uv** (Python)          | TS workspace: web, mobile, ui. Python workspace: api + engine packages (nk, heating, afa, export) + adapters. See D7. |
| Web                         | Next.js (App Router) + React + Tailwind + Framer Motion + **shadcn/ui** | Apple-like polish, **WCAG 2.1 AA / BFSG mandatory**. shadcn themed to the brand tokens.      |
| Mobile                      | **Expo / React Native**                                                | Same API + shared patterns as web. `react-native-ease` animation; responsive from the start. See D8. |
| Client state / data / forms | **Jotai** + **TanStack Query** + **React Hook Form + Zod**             | Jotai = client state, TanStack Query = server state, RHF+Zod = forms. Same on web **and** mobile. |
| DB / Auth / Storage         | **Supabase** (Postgres + Auth + Storage + RLS)                         | See D1. Auth gives password + magic-link + verification + reset.                             |
| ORM                         | **SQLAlchemy 2.0 + Alembic** against Supabase Postgres                 | RLS enforces isolation underneath. DB layer lives in `apps/api` only.                        |
| Backend / API               | **FastAPI (`apps/api`, Python) from day 1**                            | Standalone HTTP/JSON API; web + native apps consume it. Routers per domain. See D2.          |
| Runtime validation          | **Pydantic** (backend) + **Zod** (frontend/mobile)                     | Validate at every boundary; the backend is the authority.                                   |
| Async / jobs                | **Celery or Arq** on **Redis** (from M6)                               | finAPI sync, reconsent cleanup, deadline watchers, email retries.                            |
| Cache / rate-limit          | **Redis**                                                              | Response/computation caching + per-user/IP rate limiting.                                    |
| PDF                         | HTML→PDF via headless Chrome (**Playwright for Python**)               | One shared document service: NK, UVI, AfA, Anlage V, contracts.                              |
| Money                       | integer **cents** + `decimal.Decimal`                                  | Never floats. Largest-remainder rounding.                                                    |
| Testing                     | **pytest** (engines, golden fixtures) + **Vitest** (TS) + **Locust** (load) | Engines: deterministic, byte-/cent-exact. Locust simulates ~100 concurrent users.       |
| Code quality                | Python: **Ruff + mypy strict**. TS: **ESLint + Prettier + Husky + strict TS**. **React Compiler** on; **React Scan** for web perf | Enforced automatically, not by discipline.                             |
| Hosting (prod)              | EU/DE (target Hetzner)                                                 | DSGVO: EU/DE hosting is the operating licence. Dev anywhere.                                 |
| UI copy                     | **German**                                                             | Code/comments/docs/identifiers in **English**. i18n-ready (i18n lib) on web + mobile.        |

## Decisions on the flagged items

### D1 — Supabase hosting: **Supabase Cloud, EU region (Frankfurt) + signed DPA**

- **Why:** fastest path; gives Postgres + Auth + Storage + RLS out of the box; EU region + DPA
  satisfies DSGVO for the MVP. List Supabase as a **sub-processor** in the AVV.
- **Tension:** Supabase Inc. is US-HQ'd; the Datenschutz page wants EU/DE with no unguaranteed non-EU
  sub-processor. The EU region + DPA is the accepted MVP compromise.
- **Revisit-when:** **before onboarding real tenant data** — evaluate **self-hosted Supabase on
  Hetzner** (open source, full EU control). Everything above it (FastAPI + SQLAlchemy + pure engines +
  RLS) works identically either way, so this swap never touches engines.

### D2 — Backend framework: **FastAPI (`apps/api`, Python) from day 1**

- **Why:** native iOS/Android ship at public launch (~08.09) and **cannot consume Next.js server
  actions** — they need a real HTTP/JSON API. One standalone FastAPI service means web **and** native
  consume the same backend. Python is also the natural home for the **AI/OCR/Vision** work (the doc-
  extraction pipeline, Anschreiben generation), which is why the whole backend + engines are Python.
  FastAPI gives async I/O, first-class **Pydantic** validation, and auto-generated OpenAPI docs.
  Auth + RLS context are **FastAPI dependencies**; engines stay framework-free Python packages the API imports.
- **`apps/web` and `apps/mobile` are frontend only** — they call `apps/api` over HTTP; **the
  SQLAlchemy/DB layer lives in `apps/api`**, never in a client app.
- **Modular monolith:** one deployable FastAPI app, split into per-domain routers/modules with clear
  boundaries (nk, heating, ledger, tax, documents, …). Not microservices.
- **Local auth without Supabase creds:** the auth dependency verifies **HS256** against
  `SUPABASE_JWT_SECRET`; a **dev-only** `POST /auth/dev-token` (gated by `AUTH_DEV_TOKEN=true`, never in
  prod) mints a token so the guard path is exercised. Real Supabase = drop in the project's JWT secret;
  `TODO(supabase)` marks every touchpoint. ⚠️ When wiring real Supabase, check whether the project uses
  the legacy **shared-secret (HS256)** or the newer **asymmetric signing keys (JWKS, ES256/RS256)** —
  verify accordingly.
- **⚠️ Async discipline:** FastAPI is async — after every backend change, review async paths for a
  forgotten `await` or a blocking (sync) call inside an async handler. These bugs are silent.
- **Staged within this decision:** stand up the API skeleton + auth + NK endpoints at M0–M3. Add the
  **Celery/Arq (Redis)** worker/webhook layer at M6 when bank/ledger/email need it — structure from
  day 1, heavy async features when earned.
- **Revisit-when:** n/a for the framework choice; only the worker/webhook layer is staged.

### D3 — Payments: **Stripe (web) + RevenueCat (mobile), stubbed for pitch**

- **Why:** Apple/Google **require** their in-app-purchase system for digital subscriptions inside a
  mobile app — you generally can't bill Stripe there. So: **Stripe (SEPA)** for the web subscription
  (widest SEPA + invoicing, PAngV/Brutto display), **RevenueCat** as the cross-store IAP layer on
  mobile (handles receipts, renewals, entitlements across App Store + Play). Neither is needed to demo.
- **⚠️ Store-policy caveat:** what must go through IAP vs an external payment link is shifting with
  recent app-store rulings — re-check current App Store / Play policy before finalizing.
- **Revisit-when:** at the monetization milestone — for web, compare **Paddle/Chargebee** (EU-native,
  merchant-of-record handles VAT). Keep billing behind an adapter; no vendor SDK in domain code.

### D4 — AI / OCR / Vision: **adapter interface; stub for pitch; real provider EU + AVV**

- **Why:** M4 doc-extraction is demoed with canned fixtures. The real provider must offer **EU
  processing + an AVV**; it is a sub-processor. One adapter serves Anschreiben generation **and** the
  Beleg-OCR + migration pipeline.
- **Revisit-when:** before real customer documents flow — pick the EU-AVV provider; never hardcode it.

### D5 — Bank (finAPI / PSD2 AIS): **consume a licensed AISP; stub for pitch**

- **Why:** account access = PSD2/AIS, BaFin-regulated. **Never build the licence** — consume
  finAPI/Tink. For the pitch, a stub returns fake transactions behind the AIS adapter.
- **Cost note:** per-connection fees + a sub-processor for the AVV. This is Tier-2, not pitch-critical.
- **Revisit-when:** M6 — wire the real finAPI sandbox.

### D6 — Transactional email: **Modell A (own domain, From-name = landlord); provider stubbed**

- **Why:** compliance-grade delivery subsystem (§556 proof-of-receipt), not "just send mail". Own
  domain `@lokaraimmo.de` with SPF/DKIM/DMARC. Provider (SES Frankfurt / Postmark / Brevo — EU,
  sub-processor) chosen at M9; stubbed/logged until then.
- **Revisit-when:** M9.

### D7 — Toolchain: **Bun (TS side) + uv (Python side)** in one polyglot monorepo

- **Why:** the repo is polyglot now. **Bun** is the package manager + runtime + test runner for the TS
  workspace (`apps/web`, `apps/mobile`, `packages/ui`), with Turborepo orchestrating tasks. **uv** is
  the fast Python package/venv manager for the Python workspace (`apps/api` + engine packages).
- **Note:** Bun replaces the earlier pnpm/Node setup — migrate `pnpm-*`/`package.json` scripts to Bun.
  Expo + Next.js on Bun have occasional rough edges; if a tool breaks under Bun, fall back to Node for
  that one command, don't re-platform.
- **Quality gates:** Python = **Ruff + mypy strict**; TS = **ESLint + Prettier + Husky + strict TS**;
  **React Compiler** on for web + mobile; **React Scan** for web render profiling, Expo tooling for mobile.
- **Revisit-when:** if Bun causes recurring CI friction, reconsider pnpm for the TS workspace only.

### D8 — Mobile: **Expo / React Native, shared stack with web**

- **Why:** native iOS/Android ship at public launch. Expo is the fastest path to both stores from one
  RN codebase and matches the "mobile at launch" commitment. It consumes the **same FastAPI**.
- **Shared with web:** Jotai (client state), TanStack Query (server state), React Hook Form + Zod
  (forms), i18n, a shared theme, **feature-based folder structure**. Mobile-specific: `react-native-ease`
  (animation), **secure storage + Bearer JWT** (web uses cookie JWT instead).
- **Design reference:** use **Mobbin** (catalog of real app screens) when designing mobile flows.
- **Revisit-when:** if a native module Expo doesn't support is needed, evaluate a dev-client/bare workflow.

## What "stubbed behind an adapter" means (do this consistently)

For every paid/external edge (finAPI, Vision, email, billing, MDL, Destatis, DATEV):

1. Define a Python **port interface** (`class BankGateway(Protocol)`, `class VisionGateway(Protocol)`…).
2. Ship a **stub implementation** that returns fixture data (used in dev, tests, and the pitch demo).
3. Leave a `TODO(provider)` where the real EU+AVV implementation plugs in.
4. **No engine or domain module imports a vendor SDK** — only the adapter package does.
