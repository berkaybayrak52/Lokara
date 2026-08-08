# 07 — Compliance-by-design

> The Datenschutz page treats this as the **operating licence**, not a feature. It is not
> retrofittable — bake it in from day 1. Full reasoning in `lokara-arch.md` §6.

## Terms

- **AVV** — Auftragsverarbeitungsvertrag (GDPR Art. 28 data-processing agreement). Lokara is the
  customer's processor; missing = hard sales blocker.
- **DPIA / DSFA** (Art. 35) — data-protection impact assessment; likely mandatory here (scope +
  financial data).
- **TOM** — technical & organizational measures.
- **GoBD / §147 AO** — German bookkeeping/retention rules → immutable archives + retention terms.
- **BFSG** — accessibility law in force since 28.06.2025 → WCAG 2.1 AA is a real requirement.

## Non-negotiables to build in now

- **AVV per customer + a sub-processor register.** Every external processor needs an AVV and must be
  listed: **Supabase, finAPI, email provider, AI/Vision, error logging.** A non-EU sub-processor
  without safeguards = compliance break — this is exactly the Supabase EU-region decision (`docs/01` D1).
- **EU/DE hosting, TLS in transit, encryption at rest, tenant isolation** (`accountId` scoping +
  Postgres RLS is the isolation boundary).
- **Retention vs deletion = "two-clocks" model:**
  - **Uhr A** — renter _portal access_ ends after the §556 window (final NK statement + buffer).
  - **Uhr B** — actual _deletion_, run separately **per data class**:
    - tax-relevant Buchungsbelege (NK statements, bank statements, invoices) = **8 years**
      (§147 AO — reduced 10→8 as of 01.01.2025);
    - contract / deposit / handover ≈ **3 years**.
  - Deadlines **configurable, legal minimum as a hard floor (extend-only)**.
  - Art. 17 deletion request that collides with a retention duty → **restrict/block, don't delete**
    (Art. 17(3)(b) + Art. 18); delete after the term. Ended tenancies → cold storage, not deletion.
- **DPIA planned; TOMs documented; breach process (72h);** Art. 20 data export via an **authenticated,
  expiring secure link** (not a mail attachment, Art. 32).
- **Data minimization in exports** (e.g. unit label instead of renter name in DATEV Buchungstext).

## "Tool, not advice" (product-wide)

- Everything is **"rechtskonform / nach aktueller Rechtslage"**, **never "rechtssicher"** (liability
  trap — a large share of statements are formally challengeable in court).
- Consistent disclaimer on every legal/tax output: _"Lokara ist ein Werkzeug, keine Rechts- oder
  Steuerberatung."_ Keep the StBerG/legal-advice line out of the product.
- **The claim is about the tool, never about the artifact.** A per-document form — *"Dieses Dokument
  wurde rechtskonform erstellt"* — attests that *this* statement is legally complete, which no
  document may say while a BGH formal minimum is unrendered. The statement's exact rendered wording,
  the constraint and the rejected alternatives: `docs/08` → *"The disclaimer states what Lokara is,
  never that this Abrechnung is complete"*.

## Accessibility (BFSG / WCAG 2.1 AA)

A compliance requirement, not just design — see `docs/05-design-system.md` for the per-screen
checklist (contrast, focus states, scalable type, keyboard nav, reduced motion). Likely exempt as a
micro-enterprise at launch, but the threshold will be crossed — build it in, don't retrofit.

## Immutability & versioning (system-wide, GoBD/§147 AO)

New version, never overwrite — for statements, ledger entries, exports, AfA records, UVI send-log,
email delivery log, IBAN history, contract clause-sets, audit trails. Store hashes where legally
relevant. This is rule #2 in `CLAUDE.md`.
