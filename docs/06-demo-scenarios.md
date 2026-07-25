# 06 — Demo scenarios (seed data for the pitch)

> Goal: an investor sees the **common cases** work end-to-end, live. Edge cases are deferred.
> These are **seeded fixtures** loadable with one click ("Demo-Szenario laden"). All money in cents;
> all German names/addresses realistic. Keep them in `packages/db/seed/` and reuse the engine fixtures.
> **The seed must include an `OWNER` `Membership`** linking the demo Person to the demo Account — the
> FastAPI `account_session` dependency authorizes on it, so without the membership every demo request
> 403s. (The TS seed omitted this; the Python seed `uv run lokara-seed-demo` adds it.)
>
> **One occupancy timeline drives every engine.** A renter's tenancy dates must be identical wherever
> they appear — NK allocation, heating, and the statement. (A seed once had Bernd Muster occupying all
> year in the heating section but moving out in June in the NK section.) Deriving both engines from the
> same tenancy rows isn't just consistency: it makes the **degree-day split visible on the statement**
> — unit B's heating row splits Mieter/Vermieter **585/415 ‰** (786,24 € / 557,76 €), which is exactly
> the domain depth the competitors don't show. Keep it in the demo.

## Scenario 1 — Solo landlord, clean NK + vacancy (⭐ the crown jewel)

Mirrors the canonical €1,200 golden fixture so the live demo matches the tested numbers.

- Account: `SOLO`, one Landlord ("Emir …"), one Building, 3 units.
- Unit A (50 m²) rented all year; Unit B (30 m²) renter moves out Jun 30 → vacant Jul–Dec;
  Unit C (20 m²) rented all year.
- Garbage cost €1,200.00, key = AREA.
- **Demo beat:** run the statement → shares 600 / 178.52 / (181.48 to landlord) / 240.00, reconciling
  to €1,200.00 → generate the PDF with `Rechtsstand` + disclaimer.

## Scenario 2 — Heating + CO₂ split

- Same building, central heating, consumption meters per unit, one warm-water meter.
- **Demo beat:** show §7/8 base/consumption split + §9 WW separation, then the **CO₂ 10-step**
  landlord/renter split. Point out: get this wrong and the tenant has a 3% reduction right — Lokara
  handles it as standard.

## Scenario 3 — Flexible allocation keys without data loss

- A cost initially on `UNITS`, switched to `AREA` mid-demo.
- **Demo beat:** change the key → statement re-computes → **no entered data is lost**. This is the
  literal objego/immocloud pain point being solved on screen.

## Scenario 4 — Direktzuordnung (DIRECT)

- A repair invoice inside Unit A only.
- **Demo beat:** cost assigned directly to one unit, bypassing proportional spread — shows domain depth.

## Scenario 5 — Doc-extraction (canned, M4)

- A sample Betriebskosten invoice PDF (fixture).
- **Demo beat:** upload → Vision **stub** returns prefilled fields (supplier, amount, cost type, period)
  → user confirms → it lands as a cost entry. Narrate: "real EU+AVV provider plugs in behind this same
  step; nothing changes in the flow."

## Scenario 6 — Hausverwaltung multi-tenant (if M5 is reached)

- Account: `HAUSVERWALTUNG`, 2 Landlords, 3 buildings; one EMPLOYEE assigned to only 1 building.
- **Demo beat:** the employee logs in and sees only their assigned building — proves multi-tenant
  isolation (app logic + RLS). Optional stretch for the pitch.

## Presentation notes

- Lead with Scenario 1 (numbers you can defend), then 2 (depth), then 3 (the switch pain), then 5
  (AI-native UX). 4 and 6 are "if there's time / if asked."
- Every generated document shows **`Rechtsstand MM/JJJJ`** and **"Lokara ist ein Werkzeug, keine
  Rechts- oder Steuerberatung."** — turns compliance into a trust signal in front of the investor.
- Keep a stable, pre-loaded dataset; don't type long inputs live. One click loads each scenario.
