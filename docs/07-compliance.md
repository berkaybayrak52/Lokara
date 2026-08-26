# 07 — Cross-cutting compliance and delivery status

This is Lokara's living compliance contract. It separates current controls from prepared,
specified and future obligations. Approved `docs/10` owns AfA. Approved `docs/11` owns the
source-backed tax/export/archive contract; this final tax/archive reconciliation was approved and
merged with it on 21.08.2026.

The complete predecessor remains available through
`git show 635acf9:docs/07-compliance.md`; no separate history file is needed.

## Ownership and status vocabulary

`docs/07` owns cross-cutting compliance invariants, their delivery status and unresolved
pre-production obligations. Detail remains with its specialist contract:

- [`docs/02-data-model.md`](02-data-model.md) owns identity, authorization, tenant isolation,
  lifecycle records and the immutable statement model.
- [`docs/05-design-system.md`](05-design-system.md) owns accessibility, legal-disclosure tiers and
  interaction requirements.
- [`docs/08-statement-document.md`](08-statement-document.md) owns the statement audiences, formal
  minimums, output contents and current render gaps.
- `docs/10-afa.md` contains the approved AfA transcription; approved
  [`docs/11-tax-export.md`](11-tax-export.md) owns tax/export/archive rules and `docs/12` owns
  approved reusable deadline and guard rules. M7 implementation is locally merged and does
  not turn those contracts into production approval. Their details are not duplicated here.
- `docs/14-investment-kpis.md` owns the future planning KPI and deterministic Bank-PDF boundaries.
  Its flat-tax scenario is not a tax export, promised refund or substitute for `docs/11`.

Every status below describes repository delivery, not legal certainty:

| Status | Meaning |
| --- | --- |
| **Shipped** | Present on `main` in code, schema or an enforced gate. |
| **Prepared but unmerged** | Implemented on a named branch but absent from `main`; it is not a shipped control. |
| **Specified** | Documented as the contract for later implementation; it may still lack production code. |
| **Future** | Required direction is known, but the final contract or implementation is not shipped. |

## Isolation, authorization and data minimization

### Shipped

- `Account` is the paying-customer and isolation boundary. Domain rows carry `account_id`; the
  deliberate global identity exception is `Person`.
- Account-scoped tables have enabled and forced Postgres RLS, policies and isolation-test coverage.
  Foreign keys between account-scoped tables carry `account_id` as a composite edge. The enforced
  checks are
  [`scripts/check_rls_coverage.py`](../scripts/check_rls_coverage.py) and
  [`scripts/check_fk_isolation.py`](../scripts/check_fk_isolation.py); neither may be weakened to
  make a feature pass.
- Current `/a/{accountId}/...` API routes take account context from the URL, verify a live
  `Membership` in that account and set the transaction-local Postgres account context. RLS is the
  database backstop, not a substitute for the application check.

### Shipped bootstrap boundary

- The least-privilege pre-context bootstrap read is shipped on `main` through migration `0014`. It is
  the sole deployed identity path before account context, not permission to bypass account context.

### Shipped and Future

- Membership roles, role-aware behavior, assigned-building enforcement, the account switcher and
  nested-building authorization are shipped in M5.
- Renter activation, `/renter/{tenancyId}` context and renter-portal isolation remain future work.
  A hidden navigation link is never authorization.
- Each M6-B tenant archive is selected by one account- and building-valid tenancy before rendering.
  It contains no other renter's name, amount or hidden document data, and never shares the landlord
  overview's delivery channel. It is owner-only technical archive output, not renter delivery.
- Logs, exports and provider requests must contain only the personal data required for their stated
  purpose. Production logging and export implementations still have to prove this per data flow.

### M7 boundary

- Merged M7 ships owner/adviser authorization, seven forced-RLS M7 tables, identity-free normalized
  tax events, immutable readiness/archive evidence and a restricted tax workspace. The server
  generates every artifact from domain inputs and freezes the exact bytes.
- Runtime mappings, Anlage-V lines, SKR accounts, EXTF parameters and Soll/Haben orientation remain
  blocked. A merged control is not permission to send real tax output, and M7-F's read-only reviews
  have not yet run.

## Evidence, append-only capabilities and immutable finalization

### Shipped, bounded capabilities

- Membership revocation is retained instead of hard-deleting the access history.
- The API appends allocation-key assignments instead of overwriting earlier assignments.
- Tenancies have a create-only API path. A meter-reading correction appends a new reading for the
  same date and has no direct update path, although deleting its parent meter can currently delete
  the readings. These are bounded capabilities, not a database-wide immutability claim.
- M6-B ships an account/building-scoped finalized statement, immutable normalized snapshot,
  append-only version transition and stored archive bytes/hashes. It is limited to owner-only
  technical archives and does not establish legal-production approval or renter delivery.
- Draft/demo statement rendering is a live recomputation. It creates no immutable archive.

Current input APIs still include destructive paths outside the M6-B archive boundary. Lokara
therefore does not claim that all legally relevant records are already immutable, reproducible or
archived.

### Shipped M6-A/M6-B technical archive boundary

- Finalization creates one immutable, versioned snapshot containing normalized inputs, calculation
  results, engine/rule versions, each applicable `Rechtsstand`, timestamps and content hashes.
- One finalized result archives one internal landlord overview and one independently rendered
  document for each eligible tenancy. It never creates an all-renters PDF and later crops or masks
  it.
- A correction appends `vN+1`, retains and supersedes `vN`, and preserves the referenced inputs and
  archived bytes or immutable storage keys needed to reproduce every version.
- Confirmed actual advances, Saldo, settlements and the statement archive handoff are shipped in
  M6-A/M6-B. The payment ledger and bank-matching evidence shipped in M6-C2 as append-only rows
  (migrations `0017`/`0019`); M6-C3-0 migration `0020` hardens renter consistency, allocation caps,
  learned-IBAN provenance, trigger name resolution and RLS write observability. The C3a matching
  service and final `0021` are technically complete, development-synchronized and locally merged.
  C3b's job entrypoints are technically complete and locally merged: they add a
  PSD2 consent precondition to every AIS pull, write nothing outside the sync path and delete no
  append-only evidence. The C3c *Zahlungen* screen is technically complete and locally merged; it
  records one final, immutable confirm/reject/duplicate outcome and offers no way to edit or delete
  an append-only ledger entry. Renter delivery/portal remains M10. Tax/export archives are locally merged
  in M7 and append-only, with M7-F's read-only reviews still open; delivery evidence and contract
  histories arrive with their owning later milestones.

### Specified contract and merged tax-export implementation

- One accepted payment-ledger snapshot feeds two deterministic outputs: the Anlage-V overview and
  DATEV EXTF. A receivable or statement Saldo is not a tax cash event.
- Export readiness records ordered red/yellow findings and the exact input, mapping and adviser
  profile versions. A red finding blocks; a yellow finding stays visible and is never cleared by
  generation alone.
- Re-export appends an archive version containing deterministic input references, output bytes,
  rule/mapping versions, applicable `Rechtsstand`, timestamp and hash. Earlier bytes remain.
- DATEV booking text defaults to the unit instead of a renter's full name and carries a ledger
  reference. Only data needed for the adviser purpose may leave the account boundary.
- Lokara supplies calculation help and data transport. It does not submit through ELSTER, provide
  tax structuring or claim DATEV certification.
- Anlage-V lines, SKR accounts, EXTF parameters and S/H orientation, and the BFH citation remain
  `verify-before-production`; a specified calculation path cannot clear those sentinels.
- Merged M7 implements the pure calculation/readiness layer, the schema and the server-owned
  artifact adapter. Earlier boundary and statement reviews predate the final normalized M7-A/M7-B
  changes and must still be rerun; until then M7 is technically closed but not review-closed.

## Two clocks: access and data lifecycle

Access eligibility and data deletion are separate lifecycles:

1. **Access clock.** A person may see data only while the approved account or tenancy relationship
   makes that person eligible. Ending portal access does not delete the underlying records.
2. **Data-lifecycle clock.** Deletion, continued retention or access restriction is decided per data
   class and verified legal duty. Retaining a record does not grant portal access.

There is no one retention period for statements, invoices, bank data, contracts, identity data,
support records and technical logs. Page 04 records the checked, conditional § 147a AO six-year
duty above the stated positive-income threshold; it does not create a universal Lokara retention
period. Exact class periods and conflict handling remain blocked pending a separate source-backed
privacy retention schedule. No duration is inferred from a neighboring record class or an older
planning note.

## External services and deployment controls

### Shipped

- Bank, meter/MDL, Vision, email, Destatis and DATEV boundaries are Protocol-based adapters with
  fixture stubs. They normalize external formats before domain or engine code sees them; current
  stubs do not establish real-provider compliance.
- `ENVIRONMENT` is required. Staging and production startup rejects enabled dev-token/demo-seed
  switches and the published development JWT secret.

### Specified and Future pre-production obligations

- Real Supabase Auth, Storage and hosted Postgres are not wired. Local Postgres and development JWT
  operation must not be described as completed Supabase or production compliance.
- Before real personal data reaches any provider, Lokara must verify the processing basis,
  configuration, hosting location and safeguards, sign the required AVV/DPA, and record all
  sub-processors. The same review applies when a provider or hosting setup changes.
- Adapter presence, a Frankfurt placeholder or a selected EU provider is not evidence that these
  obligations are complete.

## Product claims and legal-source flags

- Product and legal/tax output use `rechtskonform`, never `rechtssicher`.
- The approved disclaimer describes Lokara, not the completeness of one artifact:
  `Lokara ist ein Werkzeug für die rechtskonforme Betriebs- und Heizkostenabrechnung, keine Rechts-
  oder Steuerberatung.`
- Product copy adds no StBerG warning and makes no lawyer- or tax-adviser-approval claim.
- `geprüft` means the primary statutory source was checked. It does not mean lawyer-approved.
  `verify-before-production` means the value or claim remains visibly blocked from real production
  use until the recorded verification is complete. A shipped calculation path does not erase that
  flag.

The rendered-output compatibility checks for these claims live in
[`scripts/assert_statement_pdf.py`](../scripts/assert_statement_pdf.py).

## Statement and deadline boundary

- The current PDF is the landlord's internal `Vermieter-Gesamtübersicht`: a building-wide
  calculation and QA view. It must not be sent to a renter.
- M6-B ships owner-only, audience-isolated technical archives with actual advances, Saldo and
  finalization evidence. They are not renter delivery, portal publication or legal-production output.
- U5 generates and immutably archives a separate German UVI renter document that an authorized
  owner can download. Prepared M9 adds default-off scheduling/email but refuses UVI sends until
  immutable PDF bytes exist; portal publication remains M10.
- [`docs/08-statement-document.md`](08-statement-document.md) owns the four formal minimums and
  records exactly what the current PDF does and does not render.
- A period longer than 12 months is a specified hard block before calculation or rendering; a
  shorter period remains day-exact. After the § 556 deadline, the landlord's late `Nachforderung`
  is suppressed while a renter `Guthaben` remains payable. Approved `docs/12` owns the shared guard
  contract. Prepared M9 supplies W1–W8 persistence, reminders and owner-controlled delivery, while
  provider `DELIVERED` remains distinct from owner-confirmed legal receipt.

## Accessibility evidence and limits

WCAG 2.1 AA, visible focus, keyboard access, scalable text, 200% zoom, reduced motion and the legal
disclosure tiers are product requirements owned by [`docs/05-design-system.md`](05-design-system.md).

For the current PDF only, the demo gate checks the tag tree and marked-content flag, German document
language, document title, searchable text, required legal copy and rendered figures. PDF tests also
check the statement's legal-disclosure carriers and contrast rules. This is current artifact-level
evidence; it is not a WCAG, BFSG or PDF/UA certification and does not establish product-wide
accessibility. The separate U5 UVI renter artifact has received artifact-level statement review,
including its renter-facing absence copy and provenance presentation. That review is not renter
delivery/publication evidence and is not a WCAG, BFSG or PDF/UA certification. Every screen and
workflow still needs its own verification.

## Explicit pre-production gaps

The following remain open requirements, not completed controls:

- the DSFA/DPIA decision and, where required, assessment;
- documented technical and organizational measures (TOMs);
- breach detection, assessment, notification and evidence handling;
- authenticated secure data export and delivery;
- the class-specific privacy retention, restriction and deletion schedule;
- completion of the parked M7-F fresh review evidence;
- production authorization, real providers/workers and an approved checklist catalogue for M9;
- real-provider configuration, hosting, AVV/DPA and sub-processor verification.

The final `docs/07` tax/archive reconciliation is approved. Production compliance remains blocked
until the other owning source-backed contracts, implementations and evidence are complete.
