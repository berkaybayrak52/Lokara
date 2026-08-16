# 04 — App structure (web + future mobile + API)

This file separates what exists from the selected v4 architecture. German UI copy, WCAG 2.1 AA /
BFSG requirements and the feature-based structure apply to both.

## Shipped repository structure

```
lokara/
├─ apps/
│  ├─ api/                    # Python FastAPI modular monolith
│  └─ web/                    # Next.js App Router client; HTTP API only
├─ packages/
│  ├─ domain/                 # normalized value objects and pure shared primitives
│  ├─ nk-engine/              # pure Python NK allocation
│  ├─ heating-engine/         # pure Python heating/CO₂ calculation
│  ├─ rules-store/            # versioned rule data resolved by callers
│  ├─ adapters/               # ports plus current stubs/adapters
│  ├─ db/                     # SQLAlchemy, Alembic and RLS
│  ├─ pdf/                    # HTML→PDF through Playwright Chromium
│  └─ ui/                     # shared TypeScript web components/tokens
├─ pyproject.toml             # explicit uv workspace members
├─ package.json               # Bun workspace: apps/web + packages/ui
└─ turbo.json
```

There is no `apps/mobile`, `afa-engine`, `export-engine` or `kpi-engine` today. Redis and a worker are
also not installed. They are future architecture, not empty shipped modules.

The dependency direction is binding:

- engines depend only on normalized domain shapes;
- engines import no FastAPI, SQLAlchemy, rules store or vendor SDK;
- the API resolves rules, loads normalized persistence data and calls engines/adapters;
- web accesses data only through FastAPI and never imports the DB layer;
- TypeScript and Python workspaces meet at the HTTP/JSON contract.

## Shipped web and API surface

The landlord portal uses `/a/{accountId}/…`. Context is in the URL and each API request verifies the
path relationship before setting the RLS account context.

Current screens:

1. dashboard/demo load;
2. buildings, building detail and unit/tenancy detail;
3. cost entry and time-versioned allocation-key assignment;
4. meter/readings and heating-cost entry;
5. canned receipt extraction with human review;
6. landlord statement calculation/QA view and downloadable PDF;
7. style guide.

The API is one FastAPI application with routers for health/auth/bootstrap, account context, buildings,
costs, meters/heating costs, extraction, demo data and statement calculation. JSON uses camelCase at
the client boundary and snake_case inside Python. Pydantic validates the backend boundary.

## Current authentication and M5 limits

- Web uses an HttpOnly cookie set through `/api/session`; the API also accepts Bearer JWT for the
  future mobile client. Both carriers use one verification path.
- Local demo login uses the environment-gated dev token. No Supabase project is wired yet.
- `/demo/load` and `/demo/reset` are local/demo-only, require their explicit flag and operate only on
  the fixed demo account. The owner Person/Account/Membership must already be seeded; an empty Person
  table still requires `uv run lokara-seed-demo`.
- Account Membership and RLS checks exist, but M5 role enforcement, employee building assignments in
  all routes, account switching, production onboarding and renter context are not complete.
- Renter activation and renter portal ownership remain M10. Do not add `/renter/{tenancyId}` screens
  or infer a renter Membership during D1.

## Current statement boundary

The shipped PDF is the landlord's building-wide calculation/QA overview. It must never be sent to a
renter. The complete Page 01 contract in `docs/08` requires M6 to add actual paid advances, Saldo,
immutable finalization, an internal owner overview, a vacancy annex and one independently rendered
tenant document per eligible tenancy. A period longer than 12 months hard-blocks before calculation
or rendering.

## Beleg upload boundary

`POST /a/{accountId}/buildings/{buildingId}/extractions` accepts PDF/PNG/JPG up to 10 MB and returns a
proposal from the named stub provider. Extraction stores nothing. Confirmation uses the ordinary cost
creation route after human review. Vendor name and invoice date are shown but not persisted because a
versioned Beleg/archive model does not yet exist.

No cost type or allocation key is inferred as law. Page 02 and future `docs/09` own the versioned
BetrKV catalogue and default-key suggestions.

## Selected future architecture

- `apps/mobile`: Expo/React Native client at M10, using the same API, Bearer JWT in secure storage,
  TanStack Query, Jotai, React Hook Form/Zod, i18n and shared theme patterns.
- pure AfA/export/KPI packages when their D2 specs and milestones authorize implementation;
- Redis plus Celery or Arq when a real background-work slice needs rate limits, sync, retries or
  scheduled delivery;
- real Supabase Auth/Storage/Postgres credentials after the pre-production hosting/DPA decision;
- real Vision, bank, email and MDL providers only behind existing/adapted ports.

These selections do not count as installed dependencies or shipped capabilities.

## UX invariants

- One primary action, explicit labels, calm 8px-based spacing and visible loading/error/empty states.
- Changing an allocation-key assignment does not delete the cost or source evidence.
- Mutations confirm destructive intent; immutable evidence appends instead of overwriting.
- Keyboard access, visible focus, 200% zoom, contrast and reduced-motion requirements follow
  `docs/05-design-system.md`.
- Motion is currently CSS-based. Framer Motion is selected but not installed; its first use must add
  and verify it explicitly.
