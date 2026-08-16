# DEMO-RUNBOOK.md — 27.08 pitch

Use this order: prepare → verify → click six screens → answer honestly → recover if needed.

Rehearse once from a clean checkout. Most demo failures are environment problems.

---

## 1. Prepare before the room

From the repository root:

```bash
export PATH="$HOME/.bun/bin:$PATH"        # Bun must be >= 1.3
set -a
source .env.example
set +a
export ENVIRONMENT=local
lsof -ti:3000,3001 | xargs -r kill        # stop stale servers
docker compose up -d                      # Postgres on :54322
uv sync
bun install
uv run alembic -c packages/db/alembic.ini upgrade head
uv run lokara-seed-demo                   # required once before /demo/load
```

Source `.env.example` for the demo shell. Do not copy `ENVIRONMENT` into `.env`; it must remain an
explicit process setting.

Required local values:

- `DATABASE_URL` for `lokara_app`;
- `DIRECT_URL` for migrations and owner seeding;
- `SUPABASE_JWT_SECRET` with at least 32 characters;
- `AUTH_DEV_TOKEN=true`;
- `DEMO_SEED_ENABLED=true`;
- `ENVIRONMENT=local` exported in the API process.

Start the servers in separate terminals.

### API terminal

```bash
set -a
source .env.example
set +a
export ENVIRONMENT=local
uv run lokara-api                         # http://127.0.0.1:3001
```

### Web terminal

```bash
cd apps/web
bun run dev                               # http://localhost:3000
```

### Known traps

1. **Missing environment:** the API exits during startup. Read the first validation error, restore
   the missing value and restart.
2. **Demo flag off:** `/demo/load` returns 403 when `DEMO_SEED_ENABLED` is false.
3. **Empty Person table:** run `uv run lokara-seed-demo` before using the button. `/demo/load` cannot
   create the first Person through `lokara_app`; it returns 500 on a truly empty database. This is a
   separate Person-write/onboarding limitation, not a failure of the secure login read.
4. **Build during dev:** never run `bun run build` while the dev server is running. It can overwrite
   `apps/web/.next`, leaving pages visible but unclickable. Stop dev, remove `.next`, then restart.

### Green-light checklist

- [ ] `uv run lokara-seed-demo` has run once against this database.
- [ ] <http://localhost:3000> loads without console errors.
- [ ] **Demo-Szenario laden** succeeds.
- [ ] **Abrechnung erstellen** shows €1.200,00 and downloads the PDF.
- [ ] **Beleg-Upload** reads a test file; finish with **Verwerfen**.
- [ ] Browser zoom and table width are readable on the shared screen.
- [ ] Screen sharing has been tested. Use 110–125% zoom if needed.

---

## 2. Click path

Use these six screens in order. Do not wander. The final statement is the main point.

### 1 — Dashboard (`/a/acc_demo_lokara`)

The database is already owner-seeded. Do not claim that it is empty. The button still reloads the
fixed demo scenario live.

- Click **Demo-Szenario laden**.
- Say: *"One click loads a realistic building — Musterstraße 12, three units and real tenancies.
  Everything from here is calculated from that data, not from a slide."*

### 2 — Objekte → building

- Say: *"A building contains units, and units contain tenancies. These are periods, not overwritten
  fields. That is why the calculation stays correct over time."*

### 3 — Einheit / Mietverhältnis

- Point to the timeline and tenancy table.
- Say: *"Renter 2 moved out on 30 June. The tenancy keeps its start and end. Vacancy days belong to
  the landlord, not the next renter. Nothing is deleted to correct the history."*

### 4 — Zähler

- Show the 20.000 kWh Wärmemengenzähler.
- Show one 600-unit Heizkostenverteiler.
- Show the expired Eichfrist on the cold-water meter.
- Say: *"Consumption comes from opening and closing readings. Corrections create a new row and keep
  the old one visible, so the statement remains reproducible."*

Optional technical beat: enter a wrong closing value, show the statement change, then create a
**Korrektur** and show the original result return.

### 5 — Beleg-Upload

- Upload any PDF, PNG or JPG. The stub always returns the same garbage invoice.
- Show the confidence values: Betrag 97%; Kostenart 62% and marked **prüfen**.
- Say: *"The amount was read, but the cost type needs review. Nothing is stored before confirmation,
  and confirmation uses the same form as manual entry."*
- Say: *"The allocation key is not guessed. That needs the BetrKV catalogue. The current provider is
  a stub; a real EU provider with an AVV will use the same adapter."*
- Point out the duplicate warning.
- Click **Verwerfen**.

**Do not confirm the seeded Müllabfuhr.** It would book the €1.200,00 cost twice and show €2.400,00.
If this happens, use **Demo zurücksetzen**. To prove extraction affects calculations, first delete the
existing cost, then confirm the extracted one.

### 6 — Abrechnung erstellen

Slow down here.

- Show the operating-cost table.
- Show the heating and CO₂ sections.
- Download and open the PDF.
- Say: *"€1.200 garbage cost is allocated by area and day. Renter 1 pays €600,00. Renter 2 pays
  €178,52 for 181 days. The landlord carries €181,48 for vacancy. Renter 3 pays €240,00. The total
  reconciles exactly through largest-remainder rounding."*
- Say: *"Heating uses degree days. Unit B splits 583,3/416,7 ‰: €776,52 to the renter and €554,74 to
  the landlord. CO₂ uses the 10-step model, and the Rechtsstand is printed."*
- Say: *"This PDF is the landlord's building-wide calculation and QA overview. It must never be sent
  to a renter. M6 finalization will independently create one isolated statement per eligible
  tenancy, including actual advances and balance."*

---

## 3. Numbers to know

| Item | Value |
| --- | --- |
| Garbage cost, 2025, area key | **€1.200,00** over 365 days |
| Unit A — Renter 1, 50 m², 365 days | **€600,00** |
| Unit B — Renter 2, 30 m², 181 days | **€178,52** |
| Unit B — vacancy, 30 m², 184 days | **€181,48 to landlord** |
| Unit C — Renter 3, 20 m², 365 days | **€240,00** |
| Reconciliation | **exactly €1.200,00** |
| Heating and CO₂ total | **€10.300,00** |
| Unit B heating split | **583,3/416,7 ‰ = €776,52 / €554,74** |
| CO₂ | 10 steps; **Rechtsstand 01/2023** |

---

## 4. Honest answers

**Is this real or hardcoded?**

The seed creates real database rows. The statement reads the visible cost entries, heating entry and
meter readings. The €1.200 case is also a golden CI fixture. Change a value and rerun to prove it.

**Is it multi-tenant safe?**

Every domain row is account-scoped. The API verifies access, and Postgres RLS enforces it again.
Isolation tests prove another account sees nothing. Mutation tests also prove those checks fail when
the boundary is removed.

**Mobile?**

Native iOS and Android are planned for launch. They will use the same API.

**Legal advice?**

Lokara is a tool, not legal or tax advice. The disclaimer appears on every legal output.

---

## 5. Recovery

| Problem | Action |
| --- | --- |
| API exits | Export `ENVIRONMENT=local`, load `.env.example`, read the first validation error and restart. |
| Demo button returns 403 | Restart the API with `DEMO_SEED_ENABLED=true`. |
| Demo button returns 500 on an empty DB | Run `uv run lokara-seed-demo`, then retry. |
| Page is visible but unclickable | Stop web dev, remove `apps/web/.next`, then restart. |
| Dashboard is empty | Run `uv run lokara-seed-demo`. |
| API is stale or unreachable | Run `lsof -ti:3001 \| xargs kill`, then restart the API. |
| Browser loops on 401 | Clear localhost cookies and reload. |
| PDF does not open | Run `uv run playwright install chromium`. |
| Postgres refuses connection | Run `docker compose up -d`, wait, then rerun the Alembic upgrade. |

Keep a pre-rendered `packages/pdf/output/nk-heating-statement-demo.pdf` and screenshots on the laptop.
If the stack fails, show the verified artifact and numbers.

---

## 6. Do not demo

- Mobile, bank sync, tax export, contracts or renter/tax-adviser portals. They are roadmap work.
- The five personas in `docs/06` as clickable UI. They are a model, not finished screens.
- OCR as a live integration. The screen is real, but extraction is canned. Say that clearly.
