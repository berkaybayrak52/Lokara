# 01 — Tech stack and locked decisions

This is the current v4 stack contract. The complete predecessor, including the pnpm migration
instructions and the original environment-guard implementation diary, remains available through
`git show 7b08f2b:docs/01-tech-stack-and-decisions.md`.

A selection can be locked while its service or package is still Future. Status follows repository
evidence, not intent.

## Current workspace membership

The root manifests use explicit members. A directory is not a workspace member merely because it is
planned or mentioned in the architecture.

| Workspace | Exact current members |
| --- | --- |
| Bun/Turborepo | `apps/web`, `packages/ui` |
| uv | `apps/api`, `packages/domain`, `packages/nk-engine`, `packages/heating-engine`, `packages/rules-store`, `packages/matching-engine`, `packages/adapters`, `packages/db`, `packages/pdf` |

Future members are separate:

- `apps/mobile` is selected for M10 but does not exist and is not a Bun member.
- No AfA, tax-export, ledger, guard or worker package is a current workspace member. Add a package
  only in the slice that defines and verifies its boundary.
- Redis/Celery/Arq, payment SDKs and real provider SDKs are not installed workspace capabilities.

`package.json` and `pyproject.toml` are authoritative for the live member lists.

## Locked stack and delivery boundary

| Area | Decision | Current delivery |
| --- | --- | --- |
| Languages | Python with strict mypy; TypeScript with `strict: true` | **Shipped** |
| Repository | Bun + Turborepo for TypeScript; uv for Python | **Shipped** |
| Backend | One FastAPI modular monolith under `apps/api` | **Shipped** |
| Web | Next.js App Router, React, Tailwind, shadcn/ui | **Shipped** |
| Client state/forms | Jotai, TanStack Query, React Hook Form, Zod | **Shipped where used on web** |
| Database | Postgres, SQLAlchemy 2.0, Alembic, forced RLS | **Shipped locally** |
| Production data platform | Supabase Cloud in Frankfurt with signed DPA; reconsider self-hosting before real renter data | **Selected, not wired** |
| Validation | Pydantic at the API boundary; Zod on clients | **Shipped** |
| PDF | HTML to PDF through Playwright Chromium | **Shipped** |
| Money | integer cents and `decimal.Decimal`, never float | **Shipped invariant** |
| Jobs/rate limits | Redis with Celery or Arq when a real worker slice needs it | **Future** |
| Mobile | Expo / React Native against the same API | **Future M10** |
| Payments | Stripe for web; RevenueCat for mobile IAP | **Future** |
| Production hosting | EU/DE target, currently Hetzner | **Selected, not deployed** |
| Product language | German UI; English code, identifiers and technical docs | **Current rule** |

Framer Motion is selected for web animation but is not installed. Husky, React Compiler, React Scan
and Locust are not current enforced capabilities unless the manifests and gates say otherwise.

## D1 — Data platform and hosting

Production targets Supabase Postgres/Auth/Storage in Frankfurt with a signed DPA. Current
development uses local Postgres and development JWT handling; no Supabase project is wired.

Before real renter data, verify the actual region, DPA, subprocessors, backup/storage path and auth
key type. Re-evaluate self-hosted Supabase on Hetzner if the hosted arrangement does not meet the
approved privacy boundary. SQLAlchemy, FastAPI, RLS and pure engines remain above that choice.

## D2 — Backend and API

FastAPI is the single HTTP/JSON backend for web and future mobile clients. `apps/web` and future
`apps/mobile` never access the database directly.

The API composes Pydantic validation, authorization, SQLAlchemy persistence, pure engines, rules,
adapters and PDF rendering. Routers are domain-oriented inside one deployable modular monolith, not
microservices.

Current database access uses blocking psycopg through synchronous handlers. Never place blocking
database or provider calls inside an `async def` path. An async driver may land later without
changing the HTTP contract.

## D3 — Payments

Stripe is the selected web subscription provider. RevenueCat is the selected mobile IAP abstraction.
Both are Future and stay behind billing adapters. Recheck current App Store and Play rules before
mobile monetization ships.

## D4 — Vision and document extraction

Vision/OCR is an adapter boundary. The current demo uses a deterministic stub and human review. A
real provider requires EU processing, an AVV/DPA, subprocessor review and an explicit data-flow
verification before customer documents are sent.

## D5 — Bank access

Lokara consumes a licensed PSD2/AIS provider; it does not become an AISP. finAPI/Tink remain
provider candidates behind the bank adapter. The current bank edge is a stub.

The Page 08 matching contract is complete, approved and merged in `docs/15`. Its oracle preserves
`BANKMATCH-F03` as the two-part E12 duplicate case. M6-C1/M6-C2 ship the pure engine, normalized bank
adapter, nine bank/receivable/matching/ledger tables and owner-scoped endpoints; M6-C3-0 hardens
their database invariants. The real provider, matching service, jobs and landlord *Zahlungen*
screen remain unshipped.

## D6 — Transactional email

Email is a delivery and evidence subsystem, not a direct SDK call from domain code. Production uses
Lokara's domain with SPF/DKIM/DMARC and an EU-capable provider selected in its owning milestone.
The current email adapter is a stub.

## D7 — Toolchain

Bun is the package manager/runtime for the explicit TypeScript workspace; Turborepo orchestrates its
tasks. uv manages the explicit Python workspace and environment. The active quality boundary is:

- Python: Ruff, strict mypy and pytest;
- TypeScript: ESLint, Prettier, strict TypeScript and Vitest;
- repository gates: `scripts/gate.sh fast|full|demo`.

There is no active pnpm migration procedure. If a tool cannot run under Bun, a bounded Node command
may be used for that tool without changing the repository package manager.

## D8 — Mobile

Expo/React Native is the selected future mobile client. It calls the same FastAPI API, uses secure
storage and Bearer JWT, and shares validation and design patterns rather than database access.
There is no shipped mobile workspace, application or launch commitment.

## D9 — Required environment guard

`ENVIRONMENT` is required and has no settings default. Allowed values are `local`, `ci`,
`staging` and `production`. Settings construction fails when staging or production uses any of:

- the dev-token endpoint;
- demo seeding;
- the published local JWT placeholder.

The process fails during application startup, before serving a request. Local commands and
`scripts/gate.sh` supply the process variable explicitly. `.env.example` publishes the local setup
value but warns not to rely on that line after copying it to `.env`: a retained `.env` value survives
process-variable deletion and can mask the missing-environment test locally.

The verification boundary is `apps/api/tests/test_environment_guard.py` plus the ordinary fast,
full and demo gates. This guard proves fail-closed configuration behavior. It does not prove a
production deployment, Supabase wiring or provider compliance.

## External-edge contract

Every bank, meter/MDL, Vision, email, Destatis, DATEV and billing edge follows the same rule:

1. define a typed port at the application boundary;
2. normalize provider data in an adapter;
3. use a deterministic stub for tests and the demo where the real provider is absent;
4. keep vendor SDKs out of domain and engine packages;
5. verify hosting, credentials, privacy and failure behavior before calling the integration
   production-ready.

## Revisit rules

Reopen a locked choice only with a concrete trigger:

- Supabase: before real renter data or when the verified hosting/DPA boundary fails.
- Redis/worker: when a queued workload is specified.
- Payment providers: at monetization, against then-current store policy.
- Provider candidates: when the owning integration slice has source-backed requirements.
- Bun: only after repeated verified toolchain failures, not for a one-off command.
- Mobile workflow: only when a required native module cannot run in the selected Expo path.
