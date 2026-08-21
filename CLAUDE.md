# CLAUDE.md — Lokara contract

Read this file first. Then read `PLAN.md` and the relevant file under `docs/`.

- `CLAUDE.md` defines the binding project rules.
- `PLAN.md` defines what is built and what comes next.
- `lokara-arch.md` defines the architecture.
- `AGENTS.md` defines how agents execute work.
- For calculation rules, original Pages/annexes and the Rechtsstand register feed the approved
  `docs/00`–`docs/16`; approved docs then control implementation.

The current stack is v4: FastAPI and pure Python engines, Supabase Postgres, Next.js, Bun,
Turborepo, shadcn/ui and shared TypeScript packages. There is one backend, and it is Python.

---

## 1. Communication and scope — mandatory

These rules apply to every main agent session:

1. Answer exactly what Emir asked. Do not add unrelated information, advice or work.
2. Be short and direct. Lead with the answer or result. Use simple sentences.
3. Stop at the requested stage. An explanation does not authorize a plan. A plan does not authorize
   implementation. Implementation does not authorize a commit, merge or push.
4. Be exact. Verify claims against the repository, Git state or command output. Mark anything that is
   unknown, inferred, incomplete or unverified.
5. Ask only when a missing decision would materially change the result, risk or scope. Otherwise use
   the safest reasonable assumption and continue.
6. Keep progress updates to meaningful results and real blockers. Final answers contain only the
   requested outcome, essential verification and unfinished requested work.

Do not send process diaries, raw logs, agent reports or optional next steps unless Emir asks.

---

## 2. What Lokara is

Lokara is a legally compliant German operating-cost and heating-cost statement platform for private
landlords and property managers, from one unit upward.

The responsive web app comes first. Native iOS and Android come later. There is no desktop app.

---

## 3. The three rules that override everything

### 3.1 Keep legal and money calculations pure

- Calculation engines are framework-free Python packages under `packages/*-engine`.
- Engines import no web framework, database or vendor SDK.
- Inputs are normalized dataclasses or Pydantic models.
- Outputs are deterministic and covered by golden pytest fixtures.
- Money uses integer cents and `decimal.Decimal`, never `float`.

### 3.2 Correctness and auditability beat features

- Legally relevant records are immutable and versioned. Create a new version; never overwrite.
- This includes statements, ledger entries, exports, IBAN history, email delivery and contracts.
- Store hashes where required by GoBD and § 147 AO.

### 3.3 Multi-tenant isolation is mandatory

- Every domain row carries `account_id`.
- Every request is scoped by account in app logic and Postgres RLS.
- A hidden UI link is not authorization. Each endpoint verifies the relationship carried in the URL.
- `scripts/check_rls_coverage.py` must never be weakened to make a gate pass.
- Foreign keys between account-scoped tables must also preserve account isolation.

Login has one bounded exception because it must find the Person before account context exists:

- `app_bootstrap_contexts(text)` is the only pre-context identity read.
- It is owned by a dedicated least-privilege role.
- `scripts/check_pre_context_reads.py` enforces its function, role, policy, privilege and call-site
  boundaries.
- M5 role enforcement, renter context, nested-route authorization and the account switcher remain
  separate work.

---

## 4. Calculation and legal sources

For calculations, use this order:

1. original Pages and annexes under `berkay-work/Spec-Seiten/`, plus the authoritative register;
2. their approved transcription in `docs/00`–`docs/16` and committed golden fixtures;
3. engines and application code.

Rules:

- Agents must not change `berkay-work/` without Emir's explicit permission.
- Its maintained top level contains only `Rechtsstand-Register/` and `Spec-Seiten/`.
- Retired correspondence is not source authority. Git preserves it, and `docs/03` Appendix D is
  its sole historical disposition ledger.
- Do not copy Berkay's exports into `docs/`. Transcribe the rule, inputs, formula, edge cases, legal
  basis and `Rechtsstand`.
- Every transcription names its original Page, annex or register source in `berkay-work/`.
- If no suitable `docs/` file exists, create one and link it from `README.md`.
- Turn worked examples into tests, not long documentation sections.
- If an original Page, annex or register contradicts its approved doc, stop and ask. Do not choose
  silently.
- When a confirmed spec supersedes an old rule, update every affected doc and agent instruction.
  Record the reason in the transcribed spec so the old rule is not restored later.

### Rechtsstand register

- The authoritative structured source is
  `berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv`.
- The matching Notion pages remain under `Rechtsstand-Register/Eintraege/` for explanatory notes.
- For structured values and flags, the CSV wins.
- The authoritative CSV contains 180 rows: 130 `verify-before-production` and 50 `geprüft`.
- Preserve every row's value, source, legal basis, `Rechtsnatur`, `Rechtsstand` and verification flag.
- `geprüft` means the primary statutory text was checked. It does not mean lawyer-approved.
- Never present a flagged value, uncertain citation or Lokara convention as settled law.
- Two points remain explicitly pre-legal: whether the § 6a notice published under GEG § 82 is the
  legally intended notice, and the `Konvention` classification of fallback emission factors.

The register's calculation paths may be usable while some legal values remain placeholders. Keep
those flags visible until the planned legal review is complete.

---

## 5. Locked technical decisions

Full details live in `docs/01-tech-stack-and-decisions.md`.

| Area | Decision |
| --- | --- |
| Languages | Python with strict mypy; TypeScript with `strict: true` |
| Repository | Bun + Turborepo for TypeScript; uv for Python |
| Web | Next.js App Router, React, Tailwind and shadcn/ui; no direct database access; Framer Motion is selected but not installed yet |
| Mobile | Expo / React Native against the same API; secure storage, i18n, theming and responsive patterns; later milestone |
| Client data | Jotai, TanStack Query, React Hook Form and Zod |
| Database | Supabase Postgres in Frankfurt with a signed DPA; reconsider self-hosting before real renter data; SQLAlchemy 2.0, Alembic and RLS |
| Backend | FastAPI modular monolith under `apps/api` |
| Validation | Pydantic on the backend; Zod on clients |
| PDF | HTML to PDF through Playwright Chromium |
| Infra | Redis for rate limiting and caching; Celery or Arq when M6 needs workers; Locust for load tests |
| External services | Stubbed behind adapters until the real integration slice |
| Payments | Stripe for web; RevenueCat for mobile IAP |
| Production hosting | EU/DE target, currently Hetzner; local development may run anywhere |
| Language | German UI; English code, comments, identifiers and technical docs |

Defaults marked as locked in `docs/01` are not reopened without a concrete reason.

---

## 6. Cross-cutting rules

- **Version legal rules.** AfA rates, HeizkostenV ratios, CO₂ tables, Anlage-V mappings, state tax
  values and clause versions belong in the versioned rules store. Legal outputs show
  `Rechtsstand MM/JJJJ`.
- **Use adapters at every external edge.** Bank, meter, DATEV, Destatis, email and AI/Vision formats
  are normalized before domain code or engines see them. Only the adapter knows the vendor format.
- **Tool, not advice.** Legal and tax outputs use the approved "rechtskonform, keine Rechts- oder
  Steuerberatung" disclaimer. Do not add StBerG language to the product.
- **Use one Guard/Wächter pattern.** Deadlines, Eichfrist, AfA warnings, UVI and arrears use the same
  guard and reminder mechanism.
- **Model changing facts over time.** Use `valid_from` and `valid_to` rows for tenancies, allocation
  keys, meters, self-use, IBANs and similar data. Do not replace them with current-value scalars.
- **Keep financial time axes separate.** Operating-cost billing is period-based. Tax uses cash basis
  under § 11 EStG. They are separate systems with a defined handoff.
- **Keep client auth storage separate.** Web uses an HttpOnly cookie. Mobile uses secure storage and
  Bearer JWT. Both use the same API verification and one refresh/replay flow.
- **Never trust the client.** Pydantic validates the backend boundary. Zod mirrors it for client UX.

---

## 7. Naming rules

- `Account` is the paying customer and isolation boundary.
- `Renter` is the German Mieter. Do not call a renter a tenant in the schema.
- `Role` belongs to `Membership`, never `Account`.
- `AccountShape` is `SOLO` or `HAUSVERWALTUNG`.
- Membership roles are `OWNER`, `EMPLOYEE` and `TAX_ADVISOR`.
- `Landlord` is the legal lessor on statements, not an authorization role.
- Self-use is a temporal `SelfUsePeriod`, never a `Renter` row.

---

## 8. Definition of done — engine work

Engine work is done only when:

1. The package stays pure: no framework, database or vendor imports.
2. Golden fixtures are committed and outputs are deterministic and cent-exact.
3. The canonical €1,200 allocation example in `docs/03-nk-heating-engines.md` passes.
4. Rounding follows the correct engine rule:
   - Heating rounds each renter share with `ROUND_HALF_UP`.
   - Heating prints one Eigentümer residual per property and cost type:
     `block total − sum of renter shares`.
   - For heating, that same Eigentümer line reconciles all four blocks.
   - The Eigentümer residual always exists, including `0,00 €`, and may be negative.
   - It is not a party, occupancy share or separately weighted amount.
   - NK continues to use largest remainder until the Page 02 transcription changes it.
   - If the same figure can be calculated two ways, the committed residual wins. Show any rounding
     difference; do not transfer it to a renter.
5. `mypy --strict` passes and money contains no floats.

Do not restore the superseded "heating without a landlord party" case. Berkay rejected it. The
Eigentümer line always exists. See `docs/03` § 9.2.

---

## 9. Definition of done — UI work

UI work is done only when:

1. It uses the design tokens in `docs/05-design-system.md`.
2. It meets WCAG 2.1 AA and BFSG requirements: contrast, focus, scalable text and keyboard access.
3. User-facing copy is German and labels remain explicit.
4. It follows `docs/05`: one primary action, 8px spacing, calm surfaces and 150–250ms motion using
   transform or opacity.
5. "Modern, minimal and Apple-like" is a requirement, not later polish. It must not reduce clarity.
6. Anything a landlord reads receives a statement/UI review.

---

## 10. How to work

- Follow `AGENTS.md` for lanes, agents, gates, branches and reviews.
- Follow the execution order and hard rules in `PLAN.md`.
- For calculations: transcribe the spec, create the failing golden fixture, then implement.
- No agent may write both a test and the implementation that satisfies it.
- Never leave the demo path broken. Fix or revert before moving on.
- When no rule covers a decision, prefer engine purity, then immutable/versioned data, then account
  isolation.
- Merge only green work. Commit, merge and push only at the stage Emir authorizes.

### Session summary

At the end of each main session, overwrite `LAST_OUTPUT.md`. It is a short summary, not project memory
or a source of truth. Git and tracked docs hold the durable state. Subagents never write it.

Use exactly this structure:

```markdown
# Last output — <short title>

HEAD `<commit>` on `<branch>` · `<date>`
Status: Complete | Partial | Blocked

## Wanted
## Done
## Not done
## Optional next step
```

Keep it to roughly 15 non-empty lines:

- `Wanted`: one sentence.
- `Done`: outcomes and gate results.
- `Not done`: unfinished requested work or `None`.
- `Optional next step`: one recommendation or `None`.
- Do not include prompts, transcripts, reasoning, raw logs or agent reports.
