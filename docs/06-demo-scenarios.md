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
> — unit B's heating row splits Mieter/Vermieter **583,3/416,7 ‰** (776,52 € / 554,74 €), which is exactly
> the domain depth the competitors don't show. Keep it in the demo.
>
> ⚠️ **Those two euro figures moved on 05.08.2026** (they were 786,24 € / 557,76 €) and nothing about
> the degree-day split changed. The CO₂ figures of the demo building were wrong on their face — see
> *"Scenario 2 … the fuel, the emissions and the CO₂ price"* below — and the CO₂-Vermieteranteil is
> deducted **before** the renter-facing split, so correcting it moves every heating euro downstream.
> The **585/415 ‰ ratio itself is unchanged**: 778,79 / 552,47 is still exactly 585 : 415.
>
> ⚠️ **And they moved once more with K3 (Berkay Seite 01b), to `776,52 € / 554,74 €` — landed 13.08.2026.** The degree-day
> table becomes VDI 2067 Bl. 1, 12/1983, Tab. 22, so Jan–Jun is **583,3 ‰** and Jul–Dez **416,7 ‰**
> instead of 585/415 (`docs/03` → *"Seite 01b … (2) K3"*). The split itself is unchanged; only the
> table under it is. **Recomputed under both rounding methods — the demo chain is bit-identical under
> largest-remainder and under R5/K9 — so this pair moves for exactly one reason, K3.** The figures in
> `DEMO-RUNBOOK.md`, `scripts/assert_statement_pdf.py` and the PDF goldens are re-based in the same
> pass as the engine change, not before it.

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

### Scenario 2 — the fuel, the emissions and the CO₂ price

> **Rechtsstand 08/2026** (transcribed 05.08.2026). This section fixes **demo fixture values**, not
> legal values: the statutory figures it checks against are transcribed in `docs/03` →
> *"Where `total_co2_kg` and `co2_cost` come from"*, with their legal basis. Nothing here enters
> `packages/rules-store` and no engine reads it.

**The defect this replaces.** The demo printed `CO₂-Emissionen des Gebäudes 2.000 kg` and
`CO₂-Kosten 300,00 €`. That implies **150 €/t** — nearly three times the 2025 rate — and, against the
demo's own `20.000 kWh`, an emission factor of **0,1 kg CO₂/kWh**, about half of natural gas. Both are
readable off the page in one step by anyone with a property background. Found by `statement-reviewer`,
promoted by the lead on 05.08.2026.

**The demo building burns Erdgas** (central gas boiler; **one** Wärmemengenzähler for the
Liegenschaft, **Heizkostenverteiler** in the three flats, one warm-water meter per flat plus a shared
one). Stated here because the emission factor is meaningless without it, and because `HeatingInput`
carries no fuel field — the fuel is a property of the *scenario*, not of the engine.

> Corrected 06.08.2026. This sentence previously read *"one Wärmemengenzähler per unit"*, which
> contradicted `packages/adapters/.../meter.py` `_SPEC` and `DEMO-RUNBOOK.md` — the flats carry
> `MeasurementUnit.HKV_UNITS`, only `met_heat_main` is `KWH`. No figure moved: the 20.000 kWh that
> feeds the emission factor and § 9's denominator is the *building* meter either way. The distinction
> became load-bearing with slice 5, because the unit of the flats' Bemessung is now printed
> (`docs/08` → *"`MeasurementUnit` travels with the value"*), and it would have been printed wrong.

| Figure | Value | Where it comes from |
| --- | --- | --- |
| Energiegehalt der Lieferung | **20.000 kWh** | unchanged — it is also § 9's denominator |
| Emissionsfaktor (implied) | **0,200 kg CO₂/kWh** (heizwertbezogen) | 4.000 kg ÷ 20.000 kWh |
| Brennstoffemissionen | **4.000 kg** | `Co2Input.total_co2_kg`; § 3 Abs. 1 Nr. 1 CO2KostAufG figure |
| CO₂-Kosten | **261,80 €** | 4,000 t × **65,45 €/t** = 55,00 €/t (§ 10 Abs. 2 BEHG, 2025) + 19 % USt (§ 3 Abs. 3 CO2KostAufG) |
| beheizte Fläche | **100 m²** | 50 + 30 + 20, unchanged |
| Emissionsintensität | **40,0 kg CO₂/m²/Jahr** | 4.000 ÷ 100 |
| Einstufung | **37 bis unter 42 kg CO₂/m²/Jahr** → Vermieteranteil **60 %** | Anlage CO2KostAufG via `packages/rules-store` |
| CO₂-Vermieteranteil / Mieteranteil | **157,08 € / 104,72 €** | 60 / 40 of 261,80 €, exact — no rounding remainder |
| umlagefähige Kosten | **10.142,92 €** | 10.300,00 € − 157,08 € |

Every one of those checks in one step, which is the whole requirement:

- 261,80 € ÷ 4,000 t = **65,45 €/t** → 55 € + 19 % USt → the 2025 BEHG rate, gross, as a renter's
  invoice states it.
- 4.000 kg ÷ 20.000 kWh = **0,200 kg CO₂/kWh** → Erdgas. The EBeV 2030 Anlage 2 standard value is
  0,20088 kg CO₂/kWh (`docs/03`); the demo is **0,44 % below** it, which is inside the spread of real
  Erdgas-H qualities and inside what a supplier states under § 3 Abs. 1 Nr. 3 CO2KostAufG. It is a
  supplier figure, not the standard value, and the demo does not claim otherwise.
- 4.000 kg ÷ 100 m² = **40,0 kg CO₂/m²/Jahr** → Stufe 7 of the Anlage (37 bis unter 42) → 60 %.

**The Einstufung moved from *17 bis unter 22* (20 %) to *37 bis unter 42* (60 %), and that is forced,
not chosen.** The demo building burns 20.000 kWh on 100 m² = 200 kWh/m²/a. With *any* fossil fuel that
lands near 40 kg CO₂/m²/a; the old 20 kg/m²/a was only reachable by an emission factor no fuel has.
Per the lead's constraint — *"do not bend the physics to protect a fixture"* — the band moves. Both
bounds are comfortably clear of 40,0, so the step selection stays an unambiguous golden, and 40,0 is
already at one decimal place, so the demo does **not** depend on the unimplemented § 5 Abs. 1 S. 3
rounding (`docs/03` → *"Known gap"*, `PLAN.md` → *Carried over from the pitch-era order, not yet ranked*).

**Story value, unexpectedly better.** A building at 40 kg CO₂/m²/a is a Sanierungsfall, the statute
puts **60 %** of the CO₂ cost on the landlord, and that is exactly the incentive the CO2KostAufG was
written to create. The demo now shows the law biting instead of a token 20 %.

### The demo's energy reference (Ho/Hu) — DECIDED 12.08.2026, it does not re-base

> **DECISION (lead, delegated and taken).** **The demo does NOT re-base its CO₂ mass. It declares its
> 20.000 kWh as Heizwert (Hu) and keeps 4.000 kg.** Closed decision; it does not get re-argued.

`docs/03` → *"Seite 01b … (4) Ho/Hu"* introduces the rule that an energy quantity carries its
reference (Brennwert Ho / Heizwert Hu), that the emission factor carries the same one, that there is
**no conversion step anywhere**, and that a mismatch is a hard error. Two facts make the demo immune
to it:

- **The demo's CO₂ mass is supplier-stated** (§ 3 Abs. 1 Nr. 1 CO2KostAufG) — it is an input the
  landlord copies off the invoice, exactly as `docs/03` requires.
- **The K4 emission factors are `nur Fallback`.** The register says so in the value itself: they apply
  **only** where the supplier has failed to state the mass. A fallback that never fires cannot change
  a figure.

So the Ho/Hu rule changes **nothing** in the demo, and it gets exercised by its own fixtures instead —
which is where a rule about a fallback belongs. This also keeps exactly **one** re-base in this slice
(the heating pair, from K3). If a figure looks wrong afterwards there is one cause to look at, not two.

**The consequence if this is ever revisited — written down so the trade-off is visible instead of
rediscovered.** Restating the demo as a real Erdgas invoice would make the 20.000 kWh **Ho**. The
consistent supplier mass at the register's Ho factor (0,181 kg CO₂/kWh) is then ≈ **3.620 kg**, the
intensity ≈ **36,2 kg CO₂/m²/a**, and the building crosses from *37 bis unter 42* into
**_32 bis unter 37_ — landlord share 60 % → 50 %**. That is a smaller CO₂-Vermieteranteil, a different
Einstufung on the page, and a re-base of every heating euro downstream (the CO₂ share is deducted
first). It would also weaken the story recorded below — the building would no longer be the
Sanierungsfall the 60 % step makes it. Not a reason on its own; recorded so the cost is priced.

### The two implausible totals — SETTLED, they stay

> **DECISION (settled, 06.08.2026, lead).** *"103 €/m²/a is wrong, the €1.200 Müll fixture cannot move
> because it is a `CLAUDE.md` definition-of-done, and re-basing every heating euro a second time is not
> worth it before a real spec lands."* Both figures **stay exactly as they are**. This is a closed
> decision, not a pending item: it does not get re-derived, re-argued or "quickly fixed" in a later
> session. The one thing that reopens it is named at the end of this section.

The two figures, and why a reviewer flags them:

- **Heizkosten 10.300,00 € on 100 m² = 103 €/m²/a** (typical 15–25). Worse: 10.300 € for 20.000 kWh is
  0,515 €/kWh, roughly four times a gas tariff, and only part of the invoice is fuel.
- **Müllabfuhr 1.200,00 € on 100 m² = 12 €/m²/a** (typical ~2).

The analysis stays on the record because it is **what makes the decision defensible**, not because the
question is still open:

- The €1.200 garbage figure is the **canonical allocation example** of `docs/03` and a `CLAUDE.md`
  definition-of-done. It may not move, full stop — no cost/benefit weighing enters here.
- Fixing the heating total means choosing a new `total_cost`, which moves **every heating euro a second
  time** and re-bases the goldens in `scripts/assert_statement_pdf.py`, `DEMO-RUNBOOK.md` and four test
  files again. The CO₂ re-base of 05.08.2026 already spent that cascade once.
- **What a fix would cost, priced out so nobody has to price it again:** one decision on a plausible
  invoice (≈ 2.400 € Brennstoff + ≈ 600 € Wartung/Betriebsstrom/Messdienst ⇒ `total_cost` ≈ 3.000 €,
  i.e. 30 €/m²/a), then the same cascade in one pass.

**What reopens it — and it is the only thing that does:** a **real heating-invoice spec** landing, i.e.
a transcribed breakdown of what a Heizkostenabrechnung invoice actually contains (Brennstoff, Wartung,
Betriebsstrom, Messdienst, Schornsteinfeger …) with its legal basis, in `docs/03`. At that point the
demo's `total_cost` is derived from the spec rather than chosen, the cascade is paid once against a
committed source, and the pitch figure becomes defensible instead of merely stable. Until that spec
exists, changing the number would be swapping one invented figure for another — and `PLAN.md` hard
rule 1 says the invented one is the defect, not the unfixed one.

Two consequences worth stating out loud, because both are argued from every few sessions:

- **The pitch narration does not have to hide it.** The demo is *the landlord's calculation view*
  (`docs/08` → "Interim framing"), and the invoice total is an input a landlord types in — not a figure
  Lokara computes. Nothing on the page claims 10.300,00 € is typical.
- **Nothing downstream is wrong because of it.** Every ratio the demo exists to show — 30/70, the § 9
  separation, 583,3 : 416,7, the CO₂ Einstufung — is scale-free, so an implausible input scales the euro
  amounts and falsifies no rule.

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

⚠️ **None of these are buildable before the 27.08 pitch** (M3 is still finishing). Until then the
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
