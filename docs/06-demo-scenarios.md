# 06 — Demo scenarios (seed data for the pitch)

> Goal: an investor sees the **common cases** work end-to-end, live. Edge cases are deferred.
> These are **seeded fixtures** loadable with one click ("Demo-Szenario laden"). All money in cents;
> all German names/addresses realistic. Keep them in `packages/db/seed/` and reuse the engine fixtures.
> **The seed must include an `OWNER` `Membership`** linking the demo Person to the demo Account — the
> FastAPI `account_session` dependency authorizes on it, so without the membership every demo request
> 403s. (The TS seed omitted this; the Python seed `uv run lokara-seed-demo` adds it.)
>
> **⚠️ `POST /demo/load` is a bootstrap exception — it must be flag-gated like `/auth/dev-token`.**
> It runs on the raw RLS-scoped session and creates the very `Account` + `OWNER Membership` that the
> `account_session` gate would otherwise require — i.e. it deliberately steps around the isolation
> check to solve the chicken-and-egg of an empty database. That is correct for a demo seed and
> **unacceptable as a reachable production endpoint**: unguarded, it lets any caller mint accounts and
> memberships. Gate it behind an explicit env flag (`DEMO_SEED_ENABLED`, off by default, **403 when
> off**), exactly as `AUTH_DEV_TOKEN` gates the dev-token endpoint, and never enable it in prod.
> Real onboarding (M5) creates the first account through the authenticated signup path instead.
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

---

# Demo personas (the multi-role story — M5/M10)

> **Goal for the investor:** show that *one identity model* covers a solo landlord, a property manager
> with staff, a renter, a tax advisor, and an investor — without a special case for any of them. This is
> the structural differentiator against objego / immocloud / vermietet.de, and it is why the schema
> looks the way it does. Supersedes Scenario 6 above, which is the HV slice of persona 1+2.

## First: portals are not roles (four independent axes)

Get this wrong and the schema rots (`CLAUDE.md` naming traps). A **portal is a navigation grouping**
derived from these four axes — never a new identity:

| Axis | Values | Determines |
| --- | --- | --- |
| **AccountShape** | `SOLO` / `HAUSVERWALTUNG` | scale + admin surface (seats, many Landlords) |
| **Role** (on `Membership`) | `OWNER` / `EMPLOYEE` / `TAX_ADVISOR` | permissions |
| **Renter link** (`Renter.person_id`) | set / unset | Mieter-portal access, scoped to **one Tenancy** |
| **Entitlement** (Tarif) | plan features | which **modules** unlock (e.g. investment) |

Consequences that must not be "fixed" later:

- **Hausverwaltung is not a separate portal.** An HV account uses the **same Vermieter Portal**; it just
  holds many `Landlord` entities, and an `EMPLOYEE` is scoped to their `BuildingAssignment` buildings.
  "Admin bei HV" = `OWNER` in an account whose shape is `HAUSVERWALTUNG`.
- **"Investor" is not a role.** The investment add-on is **entitlement-gated** inside a Vermieter
  account (Prüfobjekt → Kanban → becomes a `Building`; 7-KPI cockpit). It may appear in the menu as
  "Investor Portal", but it adds no identity — `Tarif` unlocks features, `Role` grants permissions.
- **A Mieter has no `Account`.** `Account` = the paying customer / isolation boundary. A renter is
  domain data (`Renter`) with an *optional* login via `person_id`. That is exactly what lets one
  person be a landlord in one account and a renter in another.

## The five personas, as actual rows

| # | Persona | Rows that create it | Sees |
| --- | --- | --- | --- |
| **1** | **HV Admin** | Account **A** (`shape=HAUSVERWALTUNG`, ≥2 `Landlord`, 3 buildings) · `Membership(person=hv_admin, account=A, role=OWNER)` | Vermieter Portal — all buildings, seats/roles admin |
| **2** | **HV Employee** | same Account **A** · `Membership(person=hv_staff, account=A, role=EMPLOYEE)` · `BuildingAssignment` → **exactly 1** of the 3 buildings | Vermieter Portal — **only** that building |
| **3** | **Pure Mieter** | **no Account, no Membership** · `Renter(account=A, person_id=mieter)` → `Tenancy` (+`TenancyParty`) | Mieter Portal only, one tenancy |
| **4** | **Vermieter + Mieter + Investor** | `Membership(person=emir, account=B(SOLO), role=OWNER)` · `Renter(account=A, person_id=emir)` → a Tenancy in **A** · investment module entitled on **B**'s plan | all three — **one login** |
| **5** | **Steuerberater** | `Membership(person=stb, account=B, role=TAX_ADVISOR)` — a **guest on the client's account** | StB Portal — read-only tax/export + AfA |

**Persona 4 is the headline.** It is the worked example in `lokara-arch.md` §2: one `Person`, three
roles, three scopes, no duplicate accounts. Two accounts (A and B) are enough to stage all five people.

## Demo beats (one sentence each, in this order)

1. **Persona 4 — "one login, three portals."** Switch context in the sidebar: Vermieter (his own
   building) → Mieter (the flat he rents, in someone else's account) → Investor (his prospect
   pipeline). *"Nobody else models this. A landlord is also a tenant somewhere, and often an investor."*
2. **Persona 2 — isolation you can see.** The HV employee logs in and sees **one** building of three.
   *"Enforced twice — in the API and in Postgres row-level security. We have a test that fails if we
   disable the policy."*
3. **Persona 3 — the renter side.** Activation code bound to the **Tenancy**, so a new tenant never
   sees the previous tenant's data; UVI + documents; no visibility into the landlord side at all.
4. **Persona 5 — the Steuerberater.** Read-only guest, sees tax/AfA only. *"Your StB gets access
   without you emailing a ZIP of PDFs."*
5. **Persona 1 — scale.** Many owners under one HV account, staff scoped per building.

## Unlocks (what must exist first)

| Persona | Needs |
| --- | --- |
| 1, 2 | **M5** — Person/Account/Membership + `BuildingAssignment` scoping + RLS + portal switcher |
| 4 | **M5** for the switcher; **M10** for the Mieter portal + investment module |
| 3 | **M10** — Mieterportal (activation codes, tickets, UVI) |
| 5 | **M10** — StB guest access |

⚠️ **None of these are buildable before the 06.08 pitch** (M3 is still finishing). Until then the
honest framing is: *show the model, not fake screens* — the schema, the role table above, and the
persona-4 story, backed by the isolation test. Empty or fabricated dashboards would undercut the
correctness argument that is the pitch's strongest asset.

## Seeding rules (when these get built)

- **Idempotent merge**, like `seed_demo` — re-running must not duplicate rows.
- Every persona's account gets its **`OWNER Membership`** (the API authorizes on it — see the warning
  at the top of this file).
- Stable ids (`acc_demo_hv`, `acc_demo_solo`, `person_emir`…) so the runbook can deep-link.
- One switch to load **all** personas at once — never type credentials live in front of the room.
- Reuse the same buildings/tenancies as Scenario 1 where possible, so the numbers stay defensible.

## Presentation notes

- Lead with Scenario 1 (numbers you can defend), then 2 (depth), then 3 (the switch pain), then 5
  (AI-native UX). 4 and 6 are "if there's time / if asked."
- Every generated document shows **`Rechtsstand MM/JJJJ`** and **"Lokara ist ein Werkzeug, keine
  Rechts- oder Steuerberatung."** — turns compliance into a trust signal in front of the investor.
- Keep a stable, pre-loaded dataset; don't type long inputs live. One click loads each scenario.
