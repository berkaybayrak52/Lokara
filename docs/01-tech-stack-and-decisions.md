# 01 — Tech stack & locked decisions (ADR-style)

Every item in `lokara-arch.md` marked "to confirm" gets a **pragmatic MVP default** here so Claude
Code is never blocked. Format: **Decision → Why → Revisit-when**.

## Stack (locked)

| Category            | Pick                                                    | Notes                                                                              |
| ------------------- | ------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| Language            | TypeScript, `strict: true`                              | Money math in isolated tested packages (integer cents + `decimal.js`).             |
| Repo                | Turborepo + **pnpm**                                    | Hosts several engine packages (nk, heating, afa, export) + adapters.               |
| Web                 | Next.js (App Router) + React + Tailwind + Framer Motion | Apple-like polish, **WCAG 2.1 AA / BFSG mandatory**.                               |
| DB / Auth / Storage | **Supabase** (Postgres + Auth + Storage + RLS)          | See D1. Auth gives password + magic-link + verification + reset.                   |
| ORM                 | Prisma against Supabase Postgres                        | RLS enforces isolation underneath.                                                 |
| Backend / API       | **NestJS (`apps/api`) from day 1**                      | Standalone HTTP/JSON API; web + native apps consume it. Prisma lives here. See D2. |
| Background jobs     | Graphile Worker / BullMQ (from M6)                      | finAPI sync, reconsent cleanup, deadline watchers, email retries.                  |
| PDF                 | HTML→PDF via headless Chrome (Playwright)               | One shared document service: NK, UVI, AfA, Anlage V, contracts.                    |
| Money               | integer **cents** + `decimal.js`                        | Never floats. Largest-remainder rounding.                                          |
| Testing             | Vitest (+ golden fixtures for engines)                  | Engines: deterministic, byte-/cent-exact.                                          |
| Hosting (prod)      | EU/DE (target Hetzner)                                  | DSGVO: EU/DE hosting is the operating licence. Dev anywhere.                       |
| UI copy             | **German**                                              | Code/comments/docs/identifiers in **English**.                                     |

## Decisions on the flagged items

### D1 — Supabase hosting: **Supabase Cloud, EU region (Frankfurt) + signed DPA**

- **Why:** fastest path; gives Postgres + Auth + Storage + RLS out of the box; EU region + DPA
  satisfies DSGVO for the MVP. List Supabase as a **sub-processor** in the AVV.
- **Tension:** Supabase Inc. is US-HQ'd; the Datenschutz page wants EU/DE with no unguaranteed non-EU
  sub-processor. The EU region + DPA is the accepted MVP compromise.
- **Revisit-when:** **before onboarding real tenant data** — evaluate **self-hosted Supabase on
  Hetzner** (open source, full EU control). Everything above it (NestJS + Prisma + pure engines + RLS)
  works identically either way, so this swap never touches engines.

### D2 — Backend framework: **NestJS (`apps/api`) from day 1**

- **Why:** native iOS/Android ship at public launch (~08.09) and **cannot consume Next.js server
  actions** — they need a real HTTP/JSON API. Building server actions now would mean rebuilding them as
  an API for mobile in weeks. One standalone NestJS API means web **and** native consume the same
  backend. It's also the natural home for guards (Supabase-JWT auth + RLS context), validation,
  webhooks, and workers. Engines stay framework-free packages the API imports.
- **`apps/web` is frontend only** — it calls `apps/api` over HTTP; **Prisma lives in `apps/api`**, never
  in the web app.
- **Staged within this decision:** stand up the API skeleton + auth + NK endpoints at M0–M3. Add
  BullMQ workers/webhooks at M6 when bank/ledger/email actually need them — structure from day 1,
  heavy async features when earned.
- **Revisit-when:** n/a for the framework choice; only the worker/webhook layer is staged.

### D3 — Subscription billing: **Stripe (SEPA) as default, stubbed for pitch**

- **Why:** widest SEPA + invoicing support; PAngV/Brutto display handled. Not needed to demo.
- **Revisit-when:** at the monetization milestone — compare **Paddle/Chargebee** (EU-native,
  merchant-of-record handles VAT). Keep billing behind an adapter; no Stripe SDK in domain code.

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

## What "stubbed behind an adapter" means (do this consistently)

For every paid/external edge (finAPI, Vision, email, billing, MDL, Destatis, DATEV):

1. Define a TypeScript **port interface** (`interface BankGateway`, `interface VisionGateway`…).
2. Ship a **stub implementation** that returns fixture data (used in dev, tests, and the pitch demo).
3. Leave a `TODO(provider)` where the real EU+AVV implementation plugs in.
4. **No engine or domain module imports a vendor SDK** — only the adapter package does.
