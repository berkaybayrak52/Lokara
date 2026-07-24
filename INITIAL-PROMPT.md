# INITIAL-PROMPT.md — paste this into Fable 5 Claude Code

---

```
You are building Lokara, a German Nebenkosten-/Betriebskostenabrechnung SaaS (web app).

Before writing any code, read these in order and treat them as binding:
1. CLAUDE.md          — the operating contract (3 hard rules, locked tech, cross-cutting rules)
2. PLAN.md            — milestones; we build M0→M10 in order, pitch cutline is M0→M3 + canned M4
3. docs/01-tech-stack-and-decisions.md — locked defaults for every flagged decision
4. docs/02-data-model.md               — identity three-layer model + temporal core + allocation keys
5. docs/04-web-app-structure.md        — monorepo layout and dependency rule
6. docs/05-design-system.md            — brand tokens (colors, Montserrat/Manrope) + WCAG/BFSG
lokara-arch.md is the deepest source of truth if anything is ambiguous.

Non-negotiables (from CLAUDE.md):
- Money/legal math lives in PURE Python engine packages (packages/*-engine): no web framework, no DB,
  no vendor SDK imports. Deterministic, integer cents + decimal.Decimal, largest-remainder rounding,
  golden tests (pytest).
- Every legally-relevant record is immutable + versioned (new version, never overwrite).
- Every domain row carries accountId; isolation is enforced in app logic AND Postgres RLS.
- Never hardcode a legal rule → versioned rules store with an as-of law date.
- Paid/external APIs (finAPI, Vision/OCR, email, payments) are STUBBED behind Python adapter port
  interfaces (Protocol) for now — no vendor SDK in any engine or domain module.
- UI copy is German; code/comments/identifiers are English. UI must meet WCAG 2.1 AA / BFSG.

Architecture note: FastAPI (`apps/api`, Python) is the backend from day 1 — a standalone HTTP/JSON API
that both this web app AND the launch-day native iOS/Android apps consume. `apps/web` (and later
`apps/mobile`) are frontend only and never touch the DB; the SQLAlchemy/DB layer lives in `apps/api`.

TASK — do M0 (Foundations & scaffolding) ONLY, then stop and summarize for my review:
- Polyglot monorepo (Bun + Turborepo for TS, uv for Python) with the layout in
  docs/04-web-app-structure.md (apps/web + apps/api + packages: nk-engine, heating-engine, domain,
  adapters, db, pdf, rules-store; plus ui/). Scaffold apps/mobile (Expo) as an empty skeleton only.
- apps/web: Next.js App Router (frontend only) with a typed HTTP client (shared api.ts auth/refresh
  interceptor) that calls apps/api. apps/api: FastAPI with a Supabase-JWT auth dependency +
  RLS-context and one health endpoint. TS strict + ESLint/Prettier; Python Ruff + mypy strict; pytest
  + Vitest; Turbo pipelines.
- Tailwind wired to the design tokens in docs/05-design-system.md (no raw hex, next/font for
  Montserrat + Manrope); initialize shadcn/ui themed to those tokens. Add one demo page proving the
  palette + fonts render, fetched through the API.
- Supabase (EU/Frankfurt) wiring + SQLAlchemy + Alembic initialized INSIDE apps/api against Supabase
  Postgres. Use env placeholders; do not commit secrets. If I haven't provided Supabase creds, scaffold
  with a local Postgres fallback and a TODO.
- SQLAlchemy models + one Alembic migration for the TEMPORAL CORE only: Building → Unit → Tenancy with
  validFrom/validTo, integer-cents money, the immutable-statement pattern, and the AllocationKey enum.
  Full identity/RBAC is M5 — stub Person/Account minimally, don't build roles yet.
- pdf package: a Playwright-for-Python HTML→PDF service that renders a placeholder statement.
- Do NOT build workers/webhooks yet — the Celery/Arq (Redis) async layer arrives at M6.

Definition of Done for M0 (from PLAN.md): `bun dev` runs web and `uv run` runs the api; the web app
reaches the API through the auth dependency; `bun run test` + `pytest` run; one Alembic migration applies;
a trivial PDF renders. Set up the adapter PORT interfaces (BankGateway, VisionGateway, EmailGateway) as
Python Protocols with stub implementations, but wire no real providers.

Work in small commits. When M0's DoD is met, stop and show me: the file tree, how to run it, and any
decision you had to make that wasn't in the docs. Do NOT start M1 until I say so.
```

---

## After M0

- Review the scaffold, add your Supabase creds, confirm `bun dev` + `uv run` (api) / `bun run test` + `pytest`.
- Then: **"Continue to M1"** → the `nk-engine`. The M1 DoD is the €1,200 golden fixture in
  `docs/03-nk-heating-engines.md` passing byte-for-byte. Insist the fixture exists and is green
  before any NK UI.
- Keep steering by milestone. If Claude Code tries to jump ahead (native app, bank, contracts) before
  its milestone, point it back to `PLAN.md` — engines and correctness first.

## Tips for driving Claude Code on this project

- One milestone per session; end each with "stop and summarize, don't start the next milestone."
- When it proposes a vendor SDK inside an engine or domain module, reject it — that violates the
  adapter rule in `CLAUDE.md`.
- Ask for the golden test output explicitly at M1/M2; the pitch's credibility is the numbers.
- If a legal number appears in code, ask it to move it to `packages/rules-store` with a `Rechtsstand`.
