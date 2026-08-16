# CLAUDE.md — Lokara Web App

> This is the operating contract for anyone (human or AI — Artificial Intelligence) building Lokara.
> Read this first, then `PLAN.md`, then the relevant file under `docs/`.
> The single deepest source of truth is `lokara-arch.md` (canonical architecture, v3).

> **The stack is v4.** A **Python FastAPI** backend (`apps/api`) + **Python** engine packages
> (`packages/*-engine`), **Supabase Postgres**, a **Bun** TS/JS (TypeScript/JavaScript) workspace for
> web + mobile (`apps/web`, `packages/ui`), and **shadcn/ui**. There is one backend and it is Python.
> `git log --oneline pre-migration..phase-h-done` records how the tree got here — the migration
> plan itself was retired once it was complete. When code and docs disagree, the docs win.

---

## Communication and scope — mandatory

These rules apply to every main agent session:

1. **Answer exactly what Emir asked. Do not add unrelated information, suggestions or work.**
2. **Be short and direct.** Lead with the answer or result. Use simple sentences. Avoid long
   introductions, repeated context, complex wording and unnecessary technical detail.
3. **Stay inside the requested stage.** If Emir asks for an explanation, explain only. If he asks for
   a plan, do not implement. If he authorizes implementation, complete and verify that scope without
   expanding it.
4. **Be exact.** Check the repository, Git state or gate output before making a factual claim. Clearly
   state when something is unknown, inferred, incomplete or not verified.
5. **Ask only when necessary.** Ask a question only when the missing answer would materially change
   the result, create risk or expand the authorized scope. Otherwise use the safest reasonable
   assumption and continue.
6. **Keep progress and final messages small.** During work, report only meaningful progress or a real
   blocker. The final answer contains the outcome, essential verification and unfinished requested
   work. Do not include a process diary, raw logs, agent reports or optional next steps unless Emir
   asks for them.

These are requirements, not tone preferences. Correct work with an unfocused or needlessly long
answer is not a complete result.

---

## What Lokara is (one line)

A modern, trustworthy SaaS (Software as a Service) for **legally-compliant German Nebenkosten- /
Betriebskostenabrechnung** (operating-cost & heating-cost statements) for private landlords **and**
property managers (Hausverwaltungen) — from 1 unit upward, no cap — competing on **domain depth,
fair pricing, and AI-assisted UX** (User Experience) against objego, immocloud, vermietet.de.

We are building the **responsive Web App first**. Native iOS/Android come at public launch (separate,
later milestone). No desktop apps.

---

## The three rules that override everything

1. **The money/legal math is the product — keep it in pure, framework-free Python engine packages
   with golden tests (pytest).** Engines (`packages/*-engine`, Python) import no web framework, no
   vendor SDK (Software Development Kit), no database. They take normalized inputs (plain dataclasses
   / Pydantic models) and return deterministic outputs. A wrong framework choice later costs an app
   rewrite; it must never touch an engine or the data.

2. **Correctness and auditability beat features.** Every legally-relevant record (statements, ledger
   entries, exports, IBAN (International Bank Account Number) history, email delivery, contracts) is
   **immutable + versioned** — new version, never overwrite. Store hashes where legally relevant
   (GoBD — Grundsätze zur ordnungsmäßigen Führung und Aufbewahrung von Büchern, Aufzeichnungen und
   Unterlagen in elektronischer Form sowie zum Datenzugriff; § 147 AO — Abgabenordnung, the German
   Fiscal Code).

3. **Multi-tenant isolation is not optional.** Every domain row carries `accountId`. Scope every
   query by it. Enforce isolation **twice**: in app logic **and** in Postgres Row-Level Security
   (RLS). Hiding a UI (User Interface) link protects nothing — the endpoint must independently verify
   the caller holds the relationship in the URL (Uniform Resource Locator).

   > **What it means.** *Multi-tenant* = one deployment and one database serving every paying
   > customer at once; here a "tenant" is an **Account** (a private landlord, or a Hausverwaltung).
   > Two competing Hausverwaltungen's buildings, renters and statements live in the **same tables, in
   > adjacent rows**, separated by nothing but `account_id`. *Isolation* is the guarantee that one can
   > never read the other's rows.
   >
   > *Not optional* is about cost of failure. A wrong figure in a statement is a bug you fix; showing
   > Account A the renters of Account B is a personal-data breach under the DSGVO
   > (Datenschutz-Grundverordnung) — reportable within 72 hours, and fatal to a product sold on
   > trustworthiness. So it is never traded against a deadline the way a feature is.
   >
   > *Twice*, because the first enforcement is human: one forgotten `WHERE account_id = …`, on one
   > tired evening, leaks rows. RLS does not get tired. That is what `scripts/check_rls_coverage.py`
   > guards, and why nothing in it may be relaxed.
   >
   > *Hiding a UI link protects nothing*, because a hidden button is only a button that is not drawn
   > — anyone can still type `GET /buildings/123`. The endpoint must verify ownership of `123` on
   > every request rather than trust that the client only asks for what it was offered.
   >
   > **Pending in execution-order Row 4:** the M5 pre-context read will be the one sanctioned hole in
   > this fence, because login must identify a Person before account context exists. Current `main`
   > has neither that unscoped read nor `scripts/check_pre_context_reads.py`; Row 4 owns the design,
   > its fixtures and the checker. Until they land, no unscoped database read is permitted.

---

## The calculation spec lives in `berkay-work/` and is the source of truth

For **calculation rules**, the precedence is `berkay-work/` → `docs/` → the engines.
Berkay's spec supersedes `docs/` and the code where they disagree. (`lokara-arch.md` stays
canonical for *architecture*; this rule is about numbers, formulas and legal values.)

1. **`berkay-work/` is committed and immutable to agents unless Emir explicitly authorises a
   controlled change.** Its clean current view has exactly two top-level folders:
   `Rechtsstand-Register/` and `Spec-Seiten/`. Agents never fix, reorganise or replace Berkay's
   material on their own. An authorised reorganisation or source update preserves the prior bytes in
   Git history, so every transcription can still be checked against what he actually sent.

2. **Do not copy his `.md` files into `docs/` — transcribe them.** They are Notion exports with hash
   suffixes and URL-encoded links to `.csv` files that will not exist; they address "Seite 01b", not
   `docs/03`; their section 6 is 183 worked examples that belong in `tests/`, not in a doc; and the
   Non-Goals page has broken HTML tables he flagged himself. A verbatim copy also creates two
   unsynced copies of every rule — exactly the drift `docs-reconciler` exists to find.
   **Every transcribed `docs/` file carries a header line naming its source file in `berkay-work/`.**

3. **One exception: the Rechtsstand register.** It is already structured data — a CSV
   (Comma-Separated Values) file of 180 rows: Wert, Betrag/Satz, Flag, Quelle, Rechtsgrundlage,
   Rechtsnatur, Rechtsstand. Import it into `rules-store` nearly as-is — no prose transformation.

   The matching Notion pages remain under `Rechtsstand-Register/Eintraege/` because some contain
   explanatory notes not represented in the CSV. For structured fields and flags, the CSV wins.

   > **There is one authoritative file:**
   > **`berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv`**. It is the later export Berkay
   > named as maßgeblich (`Spec-Seiten/Antworten/Antwort-an-Emir_02.md` § 5). The earlier export,
   > preserved in Git history, differed in **7 rows** that later moved from
   > `verify-before-production` to `geprüft`.

4. **Every value lands with its flag intact.** Rechtsnatur (Gesetz / Verordnung / Konvention /
   Heuristik), Rechtsstand, source URL, and `verify-before-production` vs `geprüft`. **130 of the
   180 rows are `verify-before-production`**, the other 50 `geprüft`, in the authoritative copy
   named in rule 3; the figure was 137 in the earlier one, and quoting that number is the first
   symptom of reading the superseded export. His `Spec-Seiten/Anlagen/README-for-Emir.md` lists what
   must **not** be treated as verified: Anlage-V line numbers, SKR03/SKR04
   (Standardkontenrahmen) accounts, DATEV EXTF
   (the DATEV export text format) parameters, and three BFH (Bundesfinanzhof, the Federal Fiscal
   Court) case numbers marked `ZITAT UNSICHER`. **Transcribing a flagged value as fact is the error
   to avoid** —
   the computation paths are right, the numbers are placeholders of realistic magnitude.

   > **What `geprüft` means, in his words**
   > (`berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_02.md`, 14.08.2026):
   > *"Normtext an der Primärquelle gegengelesen"* — the statutory text was read at the primary
   > source. It does **not** mean a lawyer confirmed the legal classification, and no output may
   > imply that it does. Legal review is a **second stage**, planned once the Rechtsstand register
   > is complete and taken to a lawyer as a whole. Two entries stay explicitly pre-legal even so:
   > the **§ 6a Abs. 3 S. 4 Bekanntmachung**, promulgated under **GEG § 82** (BAnz AT 16.04.2021
   > B1) — whether it is legally *the* § 6a Bekanntmachung is the lawyer's question — and the
   > **Rechtsnatur of the emission factors**, which stays `Konvention` because using them as a
   > fallback is a design choice, not a norm.

5. **Do not be conservative about editing existing `.md` files.** `docs/03`, `docs/06`, this file,
   `DEMO-RUNBOOK.md` and `.claude/agents/statement-reviewer.md` all carry rules his spec overrides.
   Change them. Record the reason for each change in the transcribed `docs/` file, so that a later
   reader does not "restore" a rule that was deliberately superseded.

---

## Locked tech decisions (MVP — Minimum Viable Product — defaults; see `docs/01-tech-stack-and-decisions.md`)

| Area                                                    | Decision                                                                                                                                                                                                                                                                        |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Language                                                | **Python** (backend + engines, `mypy` strict) + **TypeScript** (frontend + mobile, `strict: true`)                                                                                                                                                                             |
| Repo                                                    | Polyglot monorepo: **Bun + Turborepo** for the TS side (web, mobile, ui); **uv** for the Python side (api, engines)                                                                                                                                                            |
| Web                                                     | Next.js (App Router) + React + Tailwind + **shadcn/ui** — **frontend only** (no direct DB access). Framer Motion is selected for the first real animation slice but is not installed today.                                                                                  |
| Mobile                                                  | **Expo / React Native** — same API (Application Programming Interface) + shared patterns as web. `react-native-ease` (animation), **secure storage + Bearer JWT** (JSON Web Token; JSON = JavaScript Object Notation), i18n (internationalization), theme, responsive from the start |
| Client state / data / forms                             | **Jotai** (client state) + **TanStack Query** (server state) + **React Hook Form + Zod** (forms) — on **both** web and mobile                                                                                                                                                   |
| Money math                                              | Pure Python packages: integer **cents** + `decimal.Decimal`; never floats                                                                                                                                                                                                     |
| DB / Auth / Storage                                     | **Supabase Cloud, EU (European Union) region (Frankfurt)** + signed DPA (Data Processing Agreement) (revisit self-hosted before real tenant data)                                                                                                                              |
| ORM (Object-Relational Mapper)                          | **SQLAlchemy 2.0 + Alembic** against Supabase Postgres; RLS underneath. Models and migrations live server-side in `packages/db`, consumed by `apps/api`; client apps never touch the DB.                                                                                     |
| Backend / API                                           | **FastAPI (`apps/api`, Python) from day 1** — one standalone HTTP (HyperText Transfer Protocol) / JSON API that both the web app **and** the launch-day native iOS/Android apps consume. Routers per domain (modular monolith); **FastAPI dependencies** for Supabase-JWT auth + RLS context. Async workers (Celery/Arq on Redis) added when M6 needs them. |
| Runtime validation                                      | **Pydantic** (backend) + **Zod** (frontend/mobile) — validate at every boundary                                                                                                                                                                                               |
| Infra                                                   | **Redis** — rate-limiting + caching. **Locust** — load testing (simulate ~100 concurrent users)                                                                                                                                                                               |
| PDF (Portable Document Format)                          | HTML (HyperText Markup Language) → PDF via headless Chrome (**Playwright for Python**)                                                                                                                                                                                        |
| Paid/expensive APIs (finAPI, Vision/OCR (Optical Character Recognition), email, payments) | **Stubbed behind adapters** for the pitch. Payments: **Stripe (web) + RevenueCat (mobile IAP — In-App Purchase)**. Real providers are flagged, EU + AVV (Auftragsverarbeitungsvertrag, the data-processing agreement) required. Never hardcode a vendor SDK into an engine or domain module. |
| Hosting (prod)                                          | EU/DE — European Union / Germany (target Hetzner). Local/dev is fine anywhere.                                                                                                                                                                                                                                  |
| UI copy language                                        | **German**. Code, comments, docs, identifiers: **English**.                                                                                                                                                                                                                   |

Anything marked "to confirm" in `lokara-arch.md` has a pragmatic default locked in
`docs/01-tech-stack-and-decisions.md`. Build around the default; don't reopen it without a reason.

---

## Cross-cutting rules (apply everywhere)

- **Never hardcode a legal rule.** AfA (Absetzung für Abnutzung — tax depreciation) rates, HKVO
  (Heizkostenverordnung) ratios, CO₂ 10-step table, Anlage-V line numbers per year,
  Grunderwerbsteuer per Bundesland, clause versions → a **versioned rules/config store**
  with an "as-of law date". Show `Rechtsstand MM/JJJJ` (Monat/Jahr) in every legal output.
- **Adapters at every external edge.** Bank (finAPI), meter platforms/MDL (Messdienstleister —
  metering services such as Techem, ista), DATEV, Destatis (Statistisches Bundesamt), AI/Vision
  each normalize to an internal model _before_ any engine sees it.

  > **What an adapter is.** The module that sits where we touch something we do not control, whose
  > one job is translation: the outside format becomes *our* shape before anything else sees it, and
  > the adapter is the only file in the tree that knows the foreign format exists. Two halves — the
  > **port**, a `Protocol` stating the shape we demand (`MeterGateway.list_readings(...) ->
  > tuple[MeterReading, ...]` in `packages/adapters/src/lokara_adapters/meter.py`), and the
  > **implementation** satisfying it: `StubMeterGateway` on fixtures today, the real provider later.
  > Six ports exist: bank, vision, meter, datev, destatis, email.
  >
  > **Why it is a rule.** (1) It is what keeps rule 1 true — if the heating engine parsed HeiWaKo
  > (the ARGE/bved metering-exchange format) itself, swapping ista for Techem would mean editing the
  > file that computes money. (2) A vendor swap stays in one file; `meter.py` says it outright:
  > *"only this module ever parses that format"*. (3) Downstream stops branching — a hand-typed
  > reading, an MDL delivery and a radio self-read all arrive as one `MeterReading`, so persistence,
  > statement and tests have one case, not three. (4) The demo and CI run with no network, no
  > credentials and no invoice, because the stub **is** the pitch implementation and the real one
  > merely replaces it. (5) It localizes the legal question: every external provider is a
  > sub-processor needing an AVV, and when adapters are the only outbound edges, the list of what
  > leaves the system is a directory listing.
- **"Tool, not advice."** Every legal/tax output carries a consistent
  _"rechtskonform, keine Rechts- oder Steuerberatung"_ disclaimer. Keep the StBerG
  (Steuerberatungsgesetz) line out of the product.
- **Guard/Wächter is one reusable pattern.** § 556 deadline, Eichfrist, 15 %-AfA, UVI (unterjährige
  Verbrauchsinformation), arrears → all "compute a warning from existing data" → one guard+reminder
  mechanism, not bespoke code each time.
- **Temporal by default.** Anything that changes _during_ a period is a row with `validFrom/validTo`,
  never a scalar (tenancies, allocation keys, meters, self-use, IBANs…). See `docs/02-data-model.md`.
- **Two financial time-axes never merge.** NK (Nebenkosten) billing = accrual/period-based. Tax =
  cash basis (§ 11 EStG — Einkommensteuergesetz, payment date). Distinct subsystems, one clean
  handoff. See `docs/02-data-model.md` §"Two time-axes".
- **Auth tokens differ per client, one flow.** Web stores the JWT in an **HttpOnly cookie**; mobile
  stores it in **secure storage** and sends it as a **Bearer** token. Access/refresh handled in one
  shared **`api.ts` interceptor**: on a 401 (HTTP Unauthorized), refresh once, replay the failed
  requests, and never double-fire. The auth hook layer is separate per platform (cookie vs secure
  storage); the API verifies the Supabase JWT the same way for both.
- **Never trust the client.** Validate every request body with **Pydantic** on the backend; mirror the
  shape with **Zod** on the client. The backend is the authority.

---

## Naming traps (get these wrong and the schema rots)

- **Account** = the paying SaaS customer / isolation boundary. **Renter** = the German _Mieter_.
  Never call a renter a "tenant" in the schema ("tenant" is overloaded).
- **Role lives on the Membership, never on the Account.** `AccountShape` (SOLO / HAUSVERWALTUNG) is a
  property of the account; a personal role (OWNER / EMPLOYEE / TAX_ADVISOR) is a Membership.
- **Landlord (Vermieter)** = a data entity (the legal lessor on statements), _not_ a role.
- **Eigennutzung (self-use)** is a `SelfUsePeriod` (m²-based, over time), **never** a Renter row.

---

## Definition of done for any engine work

1. Pure Python package, no web-framework/DB/vendor imports.
2. Golden fixtures committed (pytest); output is byte-/cent-exact and deterministic.
3. The canonical **€1,200 garbage-cost allocation example** (`docs/03-nk-heating-engines.md`) passes.
4. **Rounding depends on the engine, and the split is deliberate.**
   - **Heating (`heating-engine`):** `round_half_up` per renter share at assignment; the
     **Eigentümeranteil** is the **residual**, `Blockbetrag − Σ Mieteranteile`
     (`distribute_cents_owner_residual`). It is **one line per Liegenschaft** — for heating, the
     same line across all four blocks — **never a party**, never derived from occupancy, and
     never computed from a weight. It **always exists**, including at `0,00 €` in a fully-let
     building, and it may be **negative**: `round_half_up` biases the renter shares upward, so a
     block routinely overshoots its pot by a cent and the owner absorbs it with a minus sign.
     Totals reconcile to the cent **once the residual is counted** — it is *inside* the sum, not
     an exception to it. (Berkay R1/R5/K9 + `Antwort-an-Emir_02.md` § 1; `docs/03` § 9.2.)
   - **NK (`nk-engine`):** **largest-remainder**, unchanged. (`distribute_cents`.)
   - **Where a figure can be computed two ways, the residual wins.** A per-unit recomputation that
     disagrees by a cent is the Rundungsdifferenz — Berkay's own oracle is `1858`, not the
     separately computed `1859` (`09-F07`), and `17.531`, not `17.536` (`08-F21`). Disclose the
     difference; never chase it, and never hand it to a renter to make a block reconcile.

   *Why the two engines differ, so nobody reads it as an oversight:* the residual model **requires**
   half-up on the renter side — under largest-remainder the renters' shares sum to the whole pot,
   leaving the owner structurally `0`, so the two are incompatible rather than merely different.
   Switching NK is therefore what the Seite 01/02 transcription must carry, because it moves every
   NK figure. There is no correctness pressure to rush it: the canonical €1,200 fixture is
   **identical under both methods** — 600,00 / 178,52 / 181,48 / 240,00, residual exactly 0 — so
   the change did not move it, and nobody may claim it did. NK switches when page 01/02 lands.

   > **Superseded 14.08.2026.** This bullet used to carry a third case: *"one heating case stays
   > largest-remainder — a block with no landlord party."* Berkay **explicitly rejected** it
   > (§ 1.3 Frage 3: *"soll nicht verwendet werden"*), because in his model there is no such case
   > — the Eigentümerzeile exists even when nothing is vacant. Do not restore it. `docs/03` § 9.2
   > carries the full record of what was removed and why.
5. `mypy --strict` clean; money is `decimal.Decimal` + integer cents, never `float`.

## Definition of done for any UI work

1. Uses the design tokens in `docs/05-design-system.md` (no ad-hoc colors/fonts); shadcn components are
   themed to those tokens, never left on their defaults.
2. Meets **WCAG (Web Content Accessibility Guidelines) 2.1 level AA / BFSG
   (Barrierefreiheitsstärkungsgesetz)**: contrast, visible focus states, scalable type, keyboard nav.
3. German UI copy; labels are explicit (Apple-style reduction is aesthetic only, never at the cost of
   a clear label or contrast).
4. Meets the **Look & feel / motion principles** in `docs/05` — one primary action per screen, 8px
   spacing, calm surfaces, 150–250ms ease-out motion (transform/opacity only). "Modern, minimal,
   Apple-like" is a requirement, not a later polish pass; a screen that feels flat or cluttered isn't done.

---

## How to work

- **`AGENTS.md` is how work is executed here** — the deterministic gates (`scripts/gate.sh`,
  `scripts/verify_demo_path.sh`, the purity/RLS/PDF checks) and the six agents with disjoint write
  scopes. No agent may both write a test and satisfy it.
- Follow `PLAN.md`. Milestone DoDs (Definitions of Done) are binding; **engines + fixtures before
  UI**. The build order is the **execution order** in `PLAN.md` — ranked by what closes the
  legally-required surface first, not by investor value ÷ risk and not by the milestone numbering —
  and its **hard rules** apply: no calculation without its transcribed spec + golden fixture, the
  demo path is re-verified every milestone, tag each green state, stubs stay stubs.
- **Never leave the demo path broken.** If a change breaks clean-DB → seed → statement → PDF, fix or
  revert before moving on. A working demo beats a broader broken one.
- When a decision isn't covered here or in `docs/`, prefer the choice that (a) keeps engines pure,
  (b) keeps data immutable/versioned, (c) keeps `accountId` scoping intact — in that order.

- **Never implement a calculation from a pasted spec or from memory.** Transcribe it into the matching
  `docs/` file first — inputs, formula, edge cases, legal basis, **`Rechtsstand`** — then turn its
  worked example into a golden fixture, then write the code. If no `docs/` file fits, add one and link
  it from `README.md`.
- **If a new spec contradicts `docs/`, stop and ask.** Don't silently pick one; a `docs/` rule may
  encode a decision the newer spec hasn't caught up with.
- **At the end of every main session, overwrite `LAST_OUTPUT.md`** at the repo root. It is Emir's
  short summary window. It is not a prompt source, coordination layer, project memory or source of
  truth. Git and the tracked docs hold the durable state. The summary must be understandable without
  the chat and use exactly this structure:

  ```markdown
  # Last output — <short title>

  HEAD `<commit>` on `<branch>` · `<date>`
  Status: Complete | Partial | Blocked

  ## Wanted
  ## Done
  ## Not done
  ## Optional next step
  ```

  Keep the whole summary to roughly 15 non-empty lines. Use short bullets. `Wanted` is one sentence.
  Put outcomes and gate results under `Done`. Put blockers or unfinished work under `Not done`;
  write `None` when there are none. The final section contains at most one recommendation; write
  `None` when no next step is useful. It is never an instruction or commitment. Do not include
  transcripts, prompts, long logs, reasoning or raw agent reports.
  **This is the main session's file, not an agent's.** Subagents report to the main session and never
  write it. `.claude/hooks/write-scope.sh` and its `.codex` mirror enforce that boundary.
