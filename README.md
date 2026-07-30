# Lokara

## Running the app

> **Stack (v4):** FastAPI (Python) backend + Python engines · Supabase Postgres · Next.js + shadcn (web)
> · Expo (mobile, not yet built) · Bun + Turborepo (TS) · uv (Python).

```bash
# prerequisites: Node >= 22, Bun >= 1.3, uv (Python 3.13 pinned via .python-version), Docker
cp .env.example .env
docker compose up -d                                    # local Postgres fallback (TODO(supabase))
uv sync                                                 # Python workspace: api + engines + db
bun install                                             # TS workspace: apps/web + packages/ui
uv run playwright install chromium                      # Chromium for the PDF renderer (once)
uv run alembic -c packages/db/alembic.ini upgrade head   # schema incl. RLS
uv run lokara-seed-demo                                 # demo scenario (Musterstraße 12)
```

Then start the two servers in separate terminals:

```bash
DEMO_SEED_ENABLED=true uv run lokara-api    # FastAPI on 127.0.0.1:3001
bun run --filter @lokara/web dev            # web on :3000
```

Then open <http://localhost:3000> — it resolves the caller's relationships and enters the
portal. The design-token/stack showcase lives on at `/styleguide`.

For the pitch walkthrough and its traps, see `DEMO-RUNBOOK.md`. For the gates and the agent
system, see `AGENTS.md`.

> **Bun on PATH:** needs **≥ 1.3** (text lockfile, reliable `--filter`). A stale Homebrew `bun` can
> shadow a newer `~/.bun/bin/bun`; if `bun --version` looks old, prepend it:
> `export PATH="$HOME/.bun/bin:$PATH"` (same shim issue pnpm had).

Other commands: `bun run test` · `bun run lint` · `bun run typecheck` · `bun run build` ·
`uv run pytest` · `uv run ruff check .` · `uv run mypy` ·
`uv run lokara-pdf-demo` (renders the NK + heating statement to `packages/pdf/output/`) ·
`scripts/gate.sh fast|full|demo` (everything the DoDs require, as one command).

> No Supabase project is wired yet. `.env.example` documents the Frankfurt placeholders;
> until credentials exist, docker-compose Postgres + the dev-token endpoint
> (`AUTH_DEV_TOKEN=true`) stand in. Search for `TODO(supabase)`.

---

# Kickoff docs

The planning + spec set to bootstrap the **Lokara web app** with Claude Code (Fable 5).
Put this whole folder at your repo root and open Claude Code there.

## Read order

1. **`CLAUDE.md`** — the operating contract (auto-read by Claude Code). The 3 hard rules + locked tech.
2. **`PLAN.md`** — milestones M0→M10; the pitch cutline is **M0→M3 + a canned M4**.
   **Start here for current work.**
3. **`MIGRATION-PLAN.md`** — the record of the v4 rebuild that produced the current tree.
4. **`lokara-arch.md`** — canonical architecture (v3), the deepest source of truth.
5. **`docs/`** — modular specs:
   - `00-product-overview.md` — what/why/who, competitive thesis, pitch framing
   - `01-tech-stack-and-decisions.md` — locked defaults for every flagged decision (ADR-style)
   - `02-data-model.md` — identity three-layer model, temporal core, allocation keys, two time-axes
   - `03-nk-heating-engines.md` — the crown-jewel engine specs + the €1,200 golden fixture
   - `04-web-app-structure.md` — monorepo layout, routes, M3 pages
   - `05-design-system.md` — brand tokens (colors, Montserrat/Manrope) + WCAG/BFSG
   - `06-demo-scenarios.md` — seeded example cases for the investor demo
   - `07-compliance.md` — DSGVO, two-clocks retention, "tool not advice", immutability
   - `08-statement-document.md` — the Abrechnung's formal content (⏳ awaiting the Notion spec)

## The one-paragraph version

Build the money/legal math as **pure, golden-tested engine packages**; keep everything
**immutable + versioned** and **`accountId`-scoped (app + RLS)**; **stub every paid API behind an
adapter**; ship a **correct CO₂-compliant NK/heating statement to PDF** with seeded demo scenarios for
the **06.08 pitch**; then stage in the full foundation milestone by milestone.
