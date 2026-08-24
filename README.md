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

> **On Linux, add `--with-deps`:** `uv run playwright install --with-deps chromium`. The flag also
> installs the system libraries headless Chromium needs, and it is what CI runs
> (`.github/workflows/ci.yml`). **macOS does not need it** — the plain command above is enough there.

> **Reusing a Postgres volume created before this repo mounted `init-app-role.sql`?** Then the
> `lokara_app` role does not exist, the API cannot connect, and the web app shows
> **`Keine Verbindung zur API.`** One command fixes it — see [Troubleshooting](#troubleshooting).

Then start the two servers in separate terminals:

```bash
uv run lokara-api                           # FastAPI on 127.0.0.1:3001
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

## Troubleshooting

### `Keine Verbindung zur API.` — usually a missing `lokara_app` role, not an API bug

The app connects to Postgres as **`lokara_app`**, a non-superuser, so the `FORCE`d RLS policies
actually bind (`DATABASE_URL="postgresql://lokara_app:lokara@localhost:54322/lokara"` in
`.env.example`; migrations run as the owner `lokara` via `DIRECT_URL`). If that role does not exist,
the API cannot open a connection, `GET /me` fails, and the web portal renders the red
**`Keine Verbindung zur API.`** note. It reads like the API is down. It usually isn't.

Why the role can be missing: `docker-compose.yml` mounts `packages/db/scripts/init-app-role.sql` into
the container as `/docker-entrypoint-initdb.d/10-init-app-role.sql`, and Postgres runs
`docker-entrypoint-initdb.d` scripts **only when it initialises a fresh data directory** — i.e. only
when the `lokara-pgdata` volume is created. A volume that already existed before that mount was added
never saw the script, and `docker compose up -d` will never run it on that volume.

Run it by hand against the existing database:

```bash
docker compose exec -T db psql -U lokara -d lokara \
  -f /docker-entrypoint-initdb.d/10-init-app-role.sql
```

**Running it after `alembic upgrade head` is fine — better, even.** The script's
`GRANT … ON ALL TABLES IN SCHEMA public` then covers the tables Alembic has already created; the
`ALTER DEFAULT PRIVILEGES` lines only reach tables created *afterwards*, so a role created before the
migrations relies on those defaults alone.

**It is idempotent, so re-run it whenever you are unsure.** `CREATE ROLE` sits behind an
`IF NOT EXISTS` check and the rest are re-grants; the script's own header says it is *"safe to re-run
manually on an existing database"*.

(`scripts/verify_demo_path.sh --fresh` destroys and recreates the volume, so the init script runs and
this failure cannot occur there. Without `--fresh` it uses the volume you already have.)

### Four checks, in order

Each answers one question; the first bad answer is your problem.

1. **`docker compose ps`** — is the db container up and healthy?
   Anything other than `running (healthy)` for `lokara-db` (missing, restarting, `unhealthy`) means
   Postgres never came up; read `docker compose logs db`. Nothing below can pass until this does.

2. **`docker compose exec -T db psql -U lokara -d lokara -c '\du'`** — does `lokara_app` exist?
   If the role list does not contain `lokara_app`, this is exactly the case above: run the init
   script. (A connection error here instead means step 1 lied — the container is up but Postgres is
   not accepting connections.)

3. **`curl -s localhost:3001/health`** — is the API process up?
   Expect `{"status":"ok","service":"lokara-api","timestamp":"…"}`. *Connection refused* → the API is
   not running: `uv run lokara-api`. Note this endpoint does **not** touch the database — a green
   `/health` next to a broken portal is the normal picture when the role is missing, which is why
   step 2 comes first.

4. **`curl -s -X POST localhost:3001/auth/dev-token`** — does the auth path work?
   Expect `{"accessToken":"eyJ…","expiresInSeconds":…}` — camelCase, the API's wire convention, not the
   `access_token` of the OAuth spec. This is the endpoint the web app's `/api/session` route proxies
   to mint the session cookie. `403 {"detail":"Dev tokens are disabled"}` means the API was started without
   `AUTH_DEV_TOKEN=true` — `.env.example` sets it, so the usual cause is a missing or stale `.env`
   (step 1 of the setup block is `cp .env.example .env`).

---

# The specs, and the order to read them

Lokara is specified before it is built: `CLAUDE.md` forbids implementing a calculation from memory or
from a pasted spec, so every number that reaches a statement traces back to a file below. Read them
top to bottom.

## Read order

`LAST_OUTPUT.md` sits outside this read order. It is Emir's short tracked summary window after a
session. It does not coordinate work or override Git, `PLAN.md` or the living specifications.

1. **`CLAUDE.md`** — the operating contract (auto-read by Claude Code). The 3 hard rules + the locked
   tech decisions + the two Definitions of Done.
2. **`AGENTS.md`** — how work is actually executed here: six agents with **disjoint write scopes**
   (no agent may both write a test and satisfy it), and the deterministic gates underneath them —
   `scripts/gate.sh`, `scripts/verify_demo_path.sh`, and the engine-purity / RLS-coverage /
   FK-isolation / PDF-fingerprint checks. A slice declares the red window that the
   no-agent-writes-both rule makes unavoidable in `.lokara-red`
   (`scripts/check_red_sentinel.py`): announced at `fast`, fatal at `full`.
   Gates are trusted; agents are not.
3. **`PLAN.md`** — milestones M0→M10 with binding DoDs. **Start here for what to build next.**
   M0–M5 and M6-A/M6-B/M6-C1/M6-C2/M6-C3-0/M6-C3a are built and green on local `main`. C3a is
   technically complete, development-synchronized and locally merged. C3b's scheduler port and
   three job entrypoints are technically complete and locally merged; the C3c
   *Zahlungen* screen is next. Nothing is pushed.
   Work follows PLAN's **execution order** — ranked by *what closes the legally-required surface
   first* — rather than the milestone numbering. **It carries no deadline on purpose:** dates in
   `lokara-arch.md` are communication events (when something gets shown), never planning inputs,
   and they do not reorder the work.
4. **`lokara-arch.md`** — canonical current architecture (v4); `PLAN.md` owns delivery order.
5. **`DEMO-RUNBOOK.md`** — the demo walkthrough beat by beat, plus the traps that have bitten before.
6. **`docs/`** — modular specs:
   - `00-product-overview.md` — what/why/who, competitive thesis, pitch framing
   - `01-tech-stack-and-decisions.md` — locked defaults for every flagged decision (ADR-style)
   - `02-data-model.md` — canonical detailed identity, isolation, temporal property, statement and
     ledger contract, with shipped/spec/future status kept explicit
   - `03-nk-heating-engines.md` — canonical NK and Page 01b heating/CO₂ engine contract, fixtures,
     legal flags, shipped capabilities and end-to-end gaps
   - `04-web-app-structure.md` — canonical app/API structure, route and delivery-status contract
   - `05-design-system.md` — canonical brand, component, accessibility and interaction contract
   - `06-demo-scenarios.md` — canonical seeded-demo, pitch-path, figure and delivery-status contract
   - `07-compliance.md` — canonical cross-cutting compliance, two-clock lifecycle and delivery-status contract
   - `08-statement-document.md` — canonical Page 01 statement, audience, disclosure, fixture and delivery-status contract
   - `09-betrkv-catalogue.md` — Page 02's versioned operating-cost catalogue, allocability gate,
     allocation-key precedence, non-allocable routing, 14 edge cases and exact 32-fixture trace.
   - `10-afa.md` — Page 03's purchase-cost, purchase-price-allocation, AfA, self-use, 15%-guard and
     annual financing contract, with all 34 source-backed fixtures transcribed.
   - `11-tax-export.md` — Page 04's approved payment-ledger, Anlage-V overview, DATEV EXTF,
     readiness and immutable export-archive contract, with all 16 source-backed fixtures transcribed;
     all line, account and format placeholders remain blocked.
   - `12-guards-deadlines.md` — Page 05's shared guard contract for deadlines, arrears, UVI,
     rent adjustments and vacancy, with all 24 source-backed fixtures transcribed.
   - `13-contract-clauses.md` — Page 06's clause-selection, compatibility, warning and workflow-
     routing contract, with all 19 source-backed fixtures transcribed; complete clause and action-
     letter bodies remain missing and block implementation.
   - `14-investment-kpis.md` — Page 07's seven planning KPIs, financing/AfA provenance,
     sensitivity axes and deterministic Bank-PDF view, with exactly 14 data-only fixtures;
     conventions and missing concept sources remain blocked.
   - `15-bank-matching.md` — Page 08's approved normalized transaction, scoring, settlement,
     reversal and duplicate-handling contract, with all 13 source-backed fixtures plus the current
     M6-C1/M6-C2/M6-C3-0 boundary plus the technically complete, development-synchronized and
     locally merged C3a service/API boundary.
   - `16-uvi.md` — UVI monthly-consumption, comparison, DWD import, Heizspiegel fallback,
     tenant-document and delivery-evidence contract, with source-named data-only fixtures.

## The one-paragraph version

Build the money/legal math as **pure, golden-tested engine packages**; keep everything
**immutable + versioned** and **`accountId`-scoped (app + RLS)**; **stub every paid API behind an
adapter**; ship a **correct CO₂-compliant NK/heating statement to PDF** with seeded demo scenarios;
then stage in the full foundation milestone by milestone toward public launch.
