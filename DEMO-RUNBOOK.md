# DEMO-RUNBOOK.md — the 06.08 pitch walkthrough

> One page, in order: get it running → click path → what to say → what to do if it breaks.
> **Rehearse this on a clean checkout at least once.** Most demo failures are environment, not code.

---

## 1. Pre-flight (do this before the room, not in it)

```bash
export PATH="$HOME/.bun/bin:$PATH"        # Homebrew's bun 1.1 shadows ~/.bun/bin (needs ≥ 1.3)
lsof -ti:3000,3001 | xargs -r kill        # kill stale servers — a stale :3001 served old code once
docker compose up -d                      # Postgres on :54322 (container lokara-db)
uv sync && bun install
uv run alembic -c packages/db/alembic.ini upgrade head
```

Start the two servers in **separate terminals** (so you can see errors):

```bash
DEMO_SEED_ENABLED=true uv run lokara-api  # ⚠️ REQUIRED — see below. FastAPI on 127.0.0.1:3001
bun run --filter @lokara/web dev          # web on :3000
```

> **⚠️ Trap 1 — `DEMO_SEED_ENABLED`.** `POST /demo/load` is **off by default in code** (it's a
> bootstrap endpoint that creates its own membership, so it's gated like `/auth/dev-token`). It's set
> to `true` in `.env`/`.env.example`, so it normally just works — but if you demo from a fresh clone
> without `.env`, or the API is started with a different environment, the button returns **403** and
> the demo dead-ends on an empty dashboard. **Click it once during pre-flight.**
>
> **⚠️ Trap 2 — never run `bun run build` while the dev server is up.** It clobbers `apps/web/.next`,
> and pages then render but never hydrate: everything looks fine and nothing responds to clicks. If it
> happens: stop dev, `rm -rf apps/web/.next`, restart. Don't run production builds on demo day.

**Green-light checklist**

- [ ] `http://localhost:3000` loads, no console errors
- [ ] Clicking **Demo-Szenario laden** succeeds (not 403)
- [ ] **Abrechnung erstellen** shows €1.200,00 reconciling and the PDF downloads
- [ ] Browser zoom at 100%, window large enough for the tables (they're wide)
- [ ] Screen-share tested — dark-on-light UI, small type; consider zoom 110–125% for the room

---

## 2. The click path

Keep it to four screens. Don't wander into pages marked **"bald"** — they're honest placeholders,
but they're not the story.

### Screen 1 — Dashboard (`/a/acc_demo_lokara`)

Start on an **empty** database if you can — the cold-start moment is good.

- Click **"Demo-Szenario laden"**.
- **Say:** *"One click seeds a realistic building — Musterstraße 12, three units, real tenancies.
  Everything from here is computed from that data, not from a slide."*

### Screen 2 — Objekte → building detail

- **Say:** *"A building holds units; a unit holds tenancies. Every one of those is a **period**, not a
  field — that's the whole reason the numbers come out right."*

### Screen 3 — Einheit / Mietverhältnis (the timeline)

- Point at the timeline bars and the tenancy table.
- **Say:** *"Renter 2 moved out on 30 June. We don't overwrite anything — the tenancy is a row with a
  start and an end. When the flat sits empty, those days belong to the landlord, not to the next
  tenant. Competitors get this wrong or make you delete data to fix it."*

### Screen 4 — Abrechnung erstellen (⭐ the money screen)

This is the pitch. Slow down here.

- Show the NK table, then the heating/CO₂ block, then click **PDF**.
- **Say:** *"€1,200 of garbage cost, allocated by area and by day. Renter 1 pays €600. Renter 2 pays
  €178.52 — only her 181 days. €181.48 lands on the landlord for the vacancy. Renter 3 pays €240.
  It reconciles to the cent — largest-remainder rounding, no lost cent, no rounding fudge."*
- Then the differentiator: *"Heating splits by degree-days, so unit B's mid-year change comes out
  **585/415 ‰** — €786,24 to the tenant, €557,76 to the landlord. And the CO₂ split follows the
  10-step model with the **Rechtsstand** printed on the statement. That's the legal depth."*
- Open the downloaded PDF: *"This is what the tenant receives."*

---

## 3. The numbers (know these cold)

| Item | Value |
| --- | --- |
| Garbage cost, 2025, key = area | **€1.200,00** (365 days) |
| Unit A — Renter 1 (50 m², 365 d) | **€600,00** |
| Unit B — Renter 2 (30 m², 181 d) | **€178,52** |
| Unit B — vacancy (30 m², 184 d) | **€181,48 → Vermieter** |
| Unit C — Renter 3 (20 m², 365 d) | **€240,00** |
| Reconciliation | sums to **exactly €1.200,00** |
| Heating/CO₂ total | **€10.300,00** |
| Unit B heating split (degree-days) | **585/415 ‰** = €786,24 / €557,76 |
| CO₂ table | 10-step, **Rechtsstand 01/2023** on the statement |

---

## 4. Say this if asked (honest answers)

- **"Is this real or hardcoded?"** — *"The allocation is computed by a tested engine; the €1,200
  example is a golden fixture that runs in CI and must reconcile to the cent. The **cost capture
  screen** isn't built yet, so the cost totals come from the seeded scenario — that's the next screen
  we're building."* **Do not claim costs were typed in.**
- **"Is it multi-tenant safe?"** — *"Every row is scoped by account, enforced twice: in the API and in
  Postgres row-level security. There's a test that proves a landlord from another account sees
  nothing — and we mutation-check it by disabling the policy to confirm the test actually fails."*
- **"Mobile?"** — *"Native iOS/Android at launch; the API is already the same one the apps will use."*
- **"Legal advice?"** — *"It's a tool, not legal or tax advice — that disclaimer is on every output."*

---

## 5. If it breaks

| Symptom | Fix |
| --- | --- |
| **403** on "Demo-Szenario laden" | `DEMO_SEED_ENABLED=true` missing — restart the API with it |
| **Page renders but nothing is clickable** | Hydration broken — a `bun run build` was run **while the dev server was live** and clobbered `.next`. Stop dev, `rm -rf apps/web/.next`, restart dev. **Never run a production build during the demo session.** |
| Dashboard empty, no error | Seed didn't run: `uv run lokara-seed-demo` |
| API unreachable / stale numbers | A stale process on :3001 — `lsof -ti:3001 \| xargs kill`, restart |
| 401 loop in the browser | Clear cookies for localhost, reload (the interceptor refreshes once by design) |
| PDF button does nothing | Chromium missing: `uv run playwright install chromium` |
| Postgres refused | `docker compose up -d`, wait, re-run `alembic upgrade head` |

**Last-resort fallback:** keep a **pre-rendered `nk-heating-statement-demo.pdf`** and screenshots of
the Abrechnung screen on the laptop. If the stack won't start, present the artifact and the numbers —
the story survives; a blank browser doesn't.

---

## 6. Don't demo these

`Kosten erfassen`, `Zähler`, and anything marked **"bald"** in the nav — not built yet.
Mobile, bank sync, tax export, contracts: **roadmap**, not screens.
