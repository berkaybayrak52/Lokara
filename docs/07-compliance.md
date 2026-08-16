# 07 — Compliance by design

This D1 version contains settled cross-cutting rules only. Detailed Page 04 tax/DATEV encoding,
archive classes and retention mappings belong to future `docs/11` and are not guessed here.

## Isolation and data minimization

- `Account` is the paying-customer and isolation boundary. Domain rows carry `account_id`.
- Every request verifies the relationship named in the URL and sets the Postgres RLS context. RLS is
  a second enforcement layer, not a substitute for application authorization.
- Foreign keys between account-scoped rows preserve the account boundary. Composite-FK and RLS gates
  must not be weakened to make a feature pass.
- Tenant output is selected by tenancy before rendering. It contains no other renter's name, amount
  or hidden document data. The owner overview never shares the tenant delivery channel.
- Exports and logs include only the personal data required for their purpose.

## Immutability and evidence

- Legally relevant corrections append a version; they do not overwrite finalized statements,
  ledger entries, exports, meter evidence, IBAN history, email delivery or contracts.
- A finalized statement snapshot keeps normalized inputs, engine/rule versions, every applicable
  `Rechtsstand`, calculated results, content hashes and archived document hashes/keys.
- Inputs referenced by a finalized record cannot be destructively removed. A correction appends or
  supersedes while preserving reproduction of the older version.
- Exact retention periods and tax-export archive rules are deferred to `docs/11`. Until that source
  is approved, this file does not assert a one-size-fits-all deletion date.

## External processors and adapters

- Bank, meter/MDL, Vision, email, storage and tax-export formats are normalized behind adapters.
  Vendor types never enter calculation engines.
- A real provider requires an approved processing basis, the necessary AVV/DPA, verified hosting and
  sub-processor handling before real customer data is sent.
- Supabase Frankfurt is the selected production target, not a shipped integration. Current local
  Postgres/dev JWT operation must not be described as completed Supabase compliance.

## Tool, not advice

- Product and legal/tax output use `rechtskonform`, never `rechtssicher`.
- The approved statement disclaimer describes Lokara, not the completeness of a particular artifact:
  `Lokara ist ein Werkzeug für die rechtskonforme Betriebs- und Heizkostenabrechnung, keine Rechts-
  oder Steuerberatung.`
- No product copy adds a StBerG warning or claims lawyer/tax-adviser approval.
- `geprüft` in the Rechtsstand register means the primary source was checked. It does not mean
  lawyer-approved. Every `verify-before-production` flag remains visible.

## Statement and deadline boundary

- Page 01's four formal minimums and exact output contract live in `docs/08`.
- A residential operating-cost period longer than 12 months hard-blocks before calculation or
  rendering. A shorter Rumpfperiode is allowed and day-exact.
- After the § 556 deadline, only the landlord's Nachforderung is suppressed; a tenant Guthaben stays
  payable. Detailed guard cadence/escalation belongs to `docs/12`.
- The current demo PDF is an internal landlord calculation/QA view and must not be sent to a renter.

## Accessibility

WCAG 2.1 AA, visible focus, keyboard access, scalable text, 200% zoom and reduced-motion support are
product requirements. The stricter statement verification/provenance tiers and measured token pairs
live only in `docs/05-design-system.md`.

## Deferred decisions

The DPIA/DSFA decision, TOM set, breach process, data-class retention schedule, secure data-export
workflow and detailed tax/archive duties require their own verified pre-production work. They are
requirements to close, not claims that D1 or the current demo has completed them.
