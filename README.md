# Lokara — kickoff docs

The planning + spec set to bootstrap the **Lokara web app** with Claude Code (Fable 5).
Put this whole folder at your repo root and open Claude Code there.

## Read order
1. **`INITIAL-PROMPT.md`** — the exact first message to paste into Claude Code (kicks off M0).
2. **`CLAUDE.md`** — the operating contract (auto-read by Claude Code). The 3 hard rules + locked tech.
3. **`PLAN.md`** — milestones M0→M10; the pitch cutline is **M0→M3 + a canned M4**.
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

## The one-paragraph version
Build the money/legal math as **pure, golden-tested engine packages**; keep everything
**immutable + versioned** and **`accountId`-scoped (app + RLS)**; **stub every paid API behind an
adapter**; ship a **correct CO₂-compliant NK/heating statement to PDF** with seeded demo scenarios for
the **27.07 pitch**; then stage in the full foundation milestone by milestone.
