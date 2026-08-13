# DEMO-RUNBOOK.md — the 27.08 pitch walkthrough

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
> **⚠️ Trap 1b — seed once from the CLI *before* you click it.** Run `uv run lokara-seed-demo` in
> pre-flight. Since migration `0005` the global `person` table is under a deny-by-default policy and
> is read-only for `lokara_app`, so on a **truly empty** database `POST /demo/load` **500s** — it
> merges a `Person` as its first statement (`new row violates row-level security policy for table
> "person"`). The CLI seed runs as the schema owner and is unaffected; afterwards the button merges
> an existing row, writes nothing, and works. This is the M5-remainder bootstrap hole, not a seed
> bug — see §2 Screen 1 before changing it back.
>
> **⚠️ Trap 2 — never run `bun run build` while the dev server is up.** It clobbers `apps/web/.next`,
> and pages then render but never hydrate: everything looks fine and nothing responds to clicks. If it
> happens: stop dev, `rm -rf apps/web/.next`, restart. Don't run production builds on demo day.

**Green-light checklist**

- [ ] `uv run lokara-seed-demo` has run at least once against this database (Trap 1b)
- [ ] `http://localhost:3000` loads, no console errors
- [ ] Clicking **Demo-Szenario laden** succeeds (not 403, not 500)
- [ ] **Abrechnung erstellen** shows €1.200,00 reconciling and the PDF downloads
- [ ] **Beleg-Upload** reads a test file and shows the fields — then click **Verwerfen** (see Trap 3)
- [ ] Browser zoom at 100%, window large enough for the tables (they're wide)
- [ ] Screen-share tested — dark-on-light UI, small type; consider zoom 110–125% for the room

---

## 2. The click path

Keep it to six screens, in this order. M3 and M4 are complete, so every nav entry is a real page —
but resist wandering: the story is the money screen at the end.

### Screen 1 — Dashboard (`/a/acc_demo_lokara`)

Start on a database that has been **seeded once already** — `uv run lokara-seed-demo` during
pre-flight (see §1). **Do not start from a truly empty database.** Since migration `0005`, `person`
carries a deny-by-default RLS policy and is read-only for `lokara_app`, so `POST /demo/load` — which
merges a `Person` as its first statement — **500s** on an empty `person` table. `lokara-seed-demo`
runs as the schema owner and is unaffected; once the row exists, the button's merge finds it, emits
no write, and works normally.

> **Do not "fix" this back to an empty database.** The failure is not a bug in the seed — it is the
> bootstrap hole `docs/02` hands to **M5-remainder** (finding the Person behind a Supabase Auth user
> before any account context exists needs a `SECURITY DEFINER` path or a dedicated role). Restoring
> the empty-DB start before that ships just re-breaks the demo. **The cold-start beat is weakened
> until then**: the button still runs live in front of the room, but the database is not visibly
> empty beforehand, so lead with the *data*, not with the emptiness. The scripted line below already
> does that ("One click seeds a realistic building…") — keep it, and don't ad-lib "as you can see,
> nothing here yet".

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

### Screen 4 — Zähler (why the heating numbers are defensible)

- Point at the building's **Wärmemengenzähler** (20.000 kWh) and one flat's **Heizkostenverteiler**
  (600 Einheiten), then at the **expired Eichfrist** badge on the cold-water meter.
- **Say:** *"Consumption isn't typed as a total — it's derived from opening and closing register
  readings, the same shape whether a person types them or a Messdienstleister delivers them. And
  readings are never edited: a correction is a new row that supersedes the old one, which stays
  visible. That's what makes a statement re-derivable years later."*
- Optional 20-second beat if the room is technical: open a meter's readings, enter a wrong closing
  value, show the statement move, then record a **Korrektur** and watch the numbers come back.

### Screen 5 — Beleg-Upload (the "AI-assisted UX" beat)

- Upload any PDF/PNG/JPG (the extraction is canned — every file returns the garbage invoice).
- Point at the **per-field confidence**: Betrag 97 %, Kostenart **62 % · prüfen**.
- **Say:** *"The amount was read; the cost type was inferred — so the screen sends you to the one
  field that needs a human. Nothing is written until you confirm, and confirming goes through the
  exact same form the manual entry does. An OCR miss cannot reach a statement unseen."*
- Then the honest part, which lands better than hiding it: *"Two things are deliberately not
  guessed. The Umlageschlüssel isn't derived from the cost type — that needs the BetrKV catalogue,
  and inventing German law is the one thing this product can't do. And the provider here is a stub:
  a real EU provider with an AVV swaps in behind the same interface."*
- **Then click "Verwerfen".** The screen also warns *"Möglicherweise bereits erfasst"* — the €1.200
  Müllabfuhr is already booked, which is itself a good beat: *"and it notices we already have this
  invoice."*

> **⚠️ Trap 3 — don't confirm the Müllabfuhr during the demo.** The seeded scenario already contains
> it, so confirming books it **twice** and the money screen then shows €2.400,00 instead of the
> golden €1.200,00. Either click **Verwerfen**, or — if you want to prove the extraction really
> drives the numbers — delete the Müllabfuhr on *Kosten erfassen* first, then confirm and watch the
> statement come back to €600,00 / €178,52 / €181,48 / €240,00. If it goes wrong, **Demo
> zurücksetzen** on the Dashboard restores the exact scenario.

### Screen 6 — Abrechnung erstellen (⭐ the money screen)

This is the pitch. Slow down here.

- Show the NK table, then the heating/CO₂ block, then click **PDF**.
- **Say:** *"€1,200 of garbage cost, allocated by area and by day. Renter 1 pays €600. Renter 2 pays
  €178.52 — only her 181 days. €181.48 lands on the landlord for the vacancy. Renter 3 pays €240.
  It reconciles to the cent — largest-remainder rounding, no lost cent, no rounding fudge."*
- Then the differentiator: *"Heating splits by degree-days, so unit B's mid-year change comes out
  **583,3/416,7 ‰** — €776,52 to the tenant, €554,74 to the landlord. And the CO₂ split follows the
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
| Unit B heating split (degree-days) | **583,3/416,7 ‰** = €776,52 / €554,74 |
| CO₂ table | 10-step, **Rechtsstand 01/2023** on the statement |

---

## 4. Say this if asked (honest answers)

- **"Is this real or hardcoded?"** — *"Everything on the statement is computed from rows you can see
  and edit in the app: the €1.200 cost on Kosten erfassen, the €10.300 heating invoice and the meter
  readings on Zähler. The same €1.200 case is also a golden fixture that runs in CI and must
  reconcile to the cent."* You can prove it live — change a value on Kosten or Zähler and re-run the
  Abrechnung. The seed fills those rows in one click; nothing is a constant in the code.
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

Mobile, bank sync, tax export, contracts, the Mieter/StB portals: **roadmap**, not screens. The five
personas in `docs/06` are a **model** to explain, not a UI to click — M5/M10.

Doc extraction *is* a screen now (M4), but the extraction itself is **canned**. Demo the flow and the
review gate; say the provider is a stub when you show it — the screen prints that too. Don't imply a
live OCR integration.
