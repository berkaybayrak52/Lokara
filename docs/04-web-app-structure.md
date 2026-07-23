# 04 — Web-app structure

> Next.js (App Router) + React + Tailwind + Framer Motion. Responsive, WCAG 2.1 AA / BFSG.
> German UI copy; English code. This doc defines the monorepo layout and the M3 routes/pages.

## Monorepo layout (Turborepo + pnpm)

```
lokara/
├─ apps/
│  ├─ web/                     # Next.js App Router — FRONTEND ONLY, calls apps/api over HTTP
│  └─ api/                     # NestJS — the standalone HTTP/JSON API (web + native consume it)
│                              #   modules per domain, Supabase-JWT auth guard + RLS context,
│                              #   Prisma lives here; BullMQ workers/webhooks added at M6
├─ packages/
│  ├─ nk-engine/               # M1 — pure NK allocation engine + golden fixtures
│  ├─ heating-engine/          # M2 — heating + CO₂ engine + fixtures
│  ├─ export-engine/           # M7 — Anlage V + DATEV (pure)
│  ├─ afa-engine/              # M7 — depreciation (pure)
│  ├─ kpi-engine/              # M10 — investment KPIs (pure)
│  ├─ rules-store/             # versioned legal rules/config (HKVO, CO₂ table, Anlage-V lines…)
│  ├─ domain/                  # normalized value objects shared by engines + adapters
│  ├─ adapters/                # bank, vision, email, mdl, destatis, datev — ports + stubs
│  ├─ db/                      # Prisma schema, migrations, RLS policies
│  ├─ pdf/                     # HTML→PDF document service (Playwright)
│  └─ ui/                      # design-system components (tokens from docs/05)
├─ CLAUDE.md
├─ PLAN.md
├─ lokara-arch.md
└─ docs/
```

**Dependency rule:** `engine` packages depend only on `domain`. Nothing in `packages/*-engine`
imports `db`, `adapters`, `ui`, or any vendor SDK. **`apps/api` (NestJS)** wires engines + db +
adapters and exposes them as HTTP endpoints; **`apps/web` calls that API and never touches Prisma/DB
directly.** `packages/db` is imported by `apps/api` only.

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
- The web app calls the **NestJS API** (`apps/api`) over HTTP; the API validates the Supabase JWT in a
  guard, sets the RLS context, and calls the engine packages. No DB access from `apps/web`.
- Forms optimistic + autosave; long-running work (PDF, later OCR/bank) goes through API jobs (BullMQ from M6).
- All queries scoped by `accountId`; RLS is the backstop from M5. The same API endpoints serve the
  launch-day native iOS/Android apps.

## Statement output
The PDF service (`packages/pdf`) is **one shared service** behind NK, UVI, AfA dossier, Anlage V, and
contracts. For M3 it renders the NK + heating/CO₂ statement with the `Rechtsstand MM/JJJJ` stamp and
the "Tool, keine Rechts-/Steuerberatung" disclaimer.
