# 00 — Product overview

## In one sentence
Lokara is a modern, trustworthy SaaS for **legally-compliant German Nebenkosten-/Betriebskosten-
abrechnung** (operating-cost & heating-cost statements) for **private landlords and property managers
(Hausverwaltungen)** — from a single unit upward, no cap — competing on **domain depth, fair pricing,
and AI-assisted UX**.

## Who it's for
Broad from day 1: private small/mid landlords (≥1 unit, no upper limit) **and** Hausverwaltungen
(multi-user). One person can hold several roles at once (landlord who also rents a flat and does a
friend's taxes) — the identity model is built for this (see `docs/02-data-model.md`).

## Why now
Incumbents (objego, immocloud, vermietet.de) have known, painful weaknesses: **data loss**, **price
bait-and-switch**, **domain gaps** (no sub-meters, weak heating), and **slow UX**. There's a live
churn wave (objego pricing revolt, vermietet.de migration chaos). Lokara occupies that gap. Launch
targets **before the NK season (from September)**.

## The competitive thesis
Mandatory features only buy parity. Lokara wins on five levers competitors can't quickly counter:

1. **Trust & fair-price DNA as a weapon** — transparent prices, price guarantee (no retroactive
   upgrades), all units included (no licence-per-garage trap), no subscription trap, fair cancellation.
2. **Domain depth nobody delivers** — sub-meters, clean heating, freely changeable allocation keys,
   >12-month and interim statements, multi-party leases. Lokara's Excel heritage; the industry blind spot.
3. **Speed & AI-native UX** — fast interface + strong receipt OCR — while **keeping human support**,
   which competitors are automating away.
4. **Painless switch + data guarantee** — import from objego/immocloud/vermietet.de/Excel as an
   onboarding feature; export guaranteed anytime; data-integrity promise.
5. **Human support + tax-advisor bridge** — bidirectional DATEV/Steuerberater interface as real lock-in.

> ⚠️ Reality check baked into strategy: **human support** is a strong *brand* differentiator but a
> cost/scaling load for a 2-person team — reframe as a premium tier or deliberate early-phase edge,
> not an unconditional always-on guarantee. The **DATEV/tax-advisor bridge** is the more durable moat.

## The "entry ticket" (parity requirements — see `docs/07-compliance.md` & arch)
Without these, Lokara isn't even considered: complete **rechtskonforme** NK statement with all common
allocation keys; **CO₂ split (CO2KostAufG)**; bank connection (finAPI, PSD2/AISP — consumed, not
built); integrated heating incl. external MDL data; meter/sub-meter management; freely changeable keys
without data loss; **autosave / no data loss**; rent-monitoring & dunning; Anlage-V/DATEV export;
fast/stable operation; **data export anytime (DSGVO portability)**; usable mobile web; multi-party
leases; reachable human support.

> **"Tool, not advice."** Everything is *rechtskonform / nach aktueller Rechtslage* — **never
> "rechtssicher"** (a liability trap). State in AGB: Lokara is a tool, not legal or tax advice.

## Status & team
Concept/planning phase; an Excel tool already serves as lead-gen. Small team (developer Emir back
full-time). Broad scope, hard Tier-1 prioritisation required. Pitch **27.07** (Tolga Önal).

## Pitch framing
Demo a *mostly-real* app with stubs where APIs cost money (finAPI, Vision, email, billing) and
**seeded example scenarios** for the common cases. The crown jewel to show live: a **correct,
CO₂-compliant NK/heating statement rendered to PDF**. See `docs/06-demo-scenarios.md`.
