# Tax export — Anlage V overview and DATEV EXTF

**Status:** D2 transcription complete; approved and merged 21.08.2026

**Rechtsstand:** 07/2026

**Authoritative Page:**
`berkay-work/Spec-Seiten/04 · Anlage V + DATEV-Export 3a95fd420731810c8a16dfe93cc85cbd.md`

**Fixtures:** exactly `11-F01`–`11-F16` in
`packages/rules-store/tests/berkay_11_golden.py`

**Implementation status:** specification and data-only oracle only. No export engine, rules data,
schema, API, screen, adapter, archive, PDF or production DATEV output is added by this slice.

This document defines two deterministic future outputs from one payment ledger: an
`Anlage-V-Übersicht` as PDF/CSV and a DATEV EXTF booking batch. Neither output calculates its own
source amounts. Both consume accepted ledger entries, year-versioned mappings, the Page-03 AfA
handoff and an adviser profile. The readiness check runs before generation and keeps missing or
unverified facts visible.

## 1. Sources, precedence and arithmetic audit

The transcription uses the complete Page 04, all 13 Page-04 rows in the current 180-row
`Rechtsstand-Register.csv`, their entry notes, the Page-04 section of `Non-Goals V1`, the
`README-for-Emir` audit and all seven correspondence-retirement files. The CSV controls structured
values and flags. No correspondence file contains a later Page-04 calculation or format correction.

The audit recomputed all 16 Page-04 examples as cent-exact. That verifies only the printed
arithmetic. It does **not** verify the Anlage-V line numbers, SKR accounts, EXTF field parameters,
Soll/Haben orientation or the missing BFH case citation. Those values remain production-blocking.

`Non-Goals V1` owns exactly eight Page-04 Non-Goals. Page 04 also says that AfA/interest/Disagio
calculation and operating-cost allocation remain on their owning Pages; those are dependency
boundaries, not two additional Page-04 Non-Goals.

## 2. Legal basis and complete register surface

Page 04 cites § 21 and § 2 Abs. 2 S. 1 Nr. 2 EStG for the V+V surplus calculation; §§ 8, 9 and 11
EStG for income, Werbungskosten and the cash basis; § 366 Abs. 2 BGB for the stated partial-payment
analogy; § 147a AO for the conditional six-year retention duty; §§ 145–147 AO and the GoBD for
traceability after booking; §§ 1–5 StBerG for the product boundary; and Art. 6 Abs. 1 lit. c/f DSGVO
for adviser disclosure with data minimization. § 6a HeizkostenV and § 556 BGB are cross-references
only and add no tax-export formula here.

The Page states the settled 10-day-rule proposition: a regularly recurring item is assigned to its
economic year only when both due date and payment date fall in the 22 December–10 January window.
The supporting BFH file number remains deliberately absent. It must not appear in a warning or
adviser dossier before verification.

The complete Page-04 register metadata is mirrored in `PAGE_04_REGISTER_ROWS`: every row carries
`Wert`, `Betrag / Satz`, current CSV `Flag`, `Letzte Änderung um`, `Prüfen bis`, `Quelle`,
`Rechtsgrundlage §`, `Rechtsnatur` and `Rechtsstand`. All rows have Rechtsstand `07/2026` and last
change `28. Juli 2026 17:16`. The exact current groups are:

| Flag | Complete row identities |
| --- | --- |
| `geprüft` (7) | GoBD/Unveränderbarkeit archive · partial-payment order under § 366 Abs. 2 BGB · § 11 cash basis/10-day rule · adviser disclosure/data minimization · StBerG product boundary · V+V surplus calculation · conditional § 147a AO retention |
| `verify-before-production` (6) | deposit clearing treatment · DATEV EXTF parameters · interest proposal convention · Anlage-V line placeholders · uncertain BFH citation · SKR03/SKR04 account placeholders |

`geprüft` means the primary text was checked, not lawyer-approved. It does not convert an adjacent
implementation convention into settled law.

## 3. Future inputs and immutable outputs

All money is integer cents. Dates are day-accurate. Account numbers are strings because leading
zeros and length depend on the selected chart. No float crosses the boundary.

### 3.1 Payment ledger

Each accepted payment event supplies:

```text
paymentId, accountId, objektId, einheitId?, mieterId?, datum?, betragCent,
richtung, kategorie?, faelligkeitsdatum?, belegReferenz, quelle, version
```

- `betragCent` is positive; `richtung` is `einnahme` or `ausgabe`.
- `quelle` is `finapi`, `manuell` or `rechnung`.
- Categories come from Page 02 plus `kaltmiete`, `nk_vorauszahlung`, `nk_nachzahlung`,
  `nk_guthaben`, `kaution`, `schuldzinsen` and `afa`.
- Missing `datum` is a red hard block. Missing `kategorie` is a yellow readiness finding, so the
  future normalized pre-export view must be able to represent that incomplete state.
- `faelligkeitsdatum` is nullable and is used for the 10-day rule only when a supported due item
  exists. `belegReferenz` provides the trace back to the ledger entry.
- Every correction appends a version; this document approves no schema or mutation endpoint.

### 3.2 Page-03 handoff

For one object and tax year, Page 04 receives, without recalculation:

```text
afaAbziehbarCent, zinsAbziehbarCent, disagioAbziehbarCent, erhaltungsaufwandCent
```

The interest value is always a marked proposal from the loan plan and needs confirmation against
the annual bank certificate. A missing AfA record is yellow, leaves the AfA line empty and links to
the future AfA workflow. Page 04 never reconstructs the Page-03 basis, rate or loan schedule.

The reference aggregation maps `afaAbziehbarCent` and `zinsAbziehbarCent`. The source names
`disagioAbziehbarCent` and `erhaltungsaufwandCent` as handoff fields but supplies no separate
Anlage-V rows for them; `instandhaltung` also exists as a ledger category. A future mapping must
settle the lines and prevent maintenance double-counting before those two values enter an export.

### 3.3 Tax-adviser profile

The future `stbProfil` carries `beraternummer`, `mandantennummer`, `kontenrahmen` (`skr03` or
`skr04`), `sachkontenlaenge` and `wjBeginn`. The first two are required only when DATEV is selected;
their absence is a red hard block. SKR03, four-digit accounts and 1 January are source defaults,
not approved schema defaults. The `TAX_ADVISOR` guest remains read-only except for this profile's
mapping and adviser parameters.

### 3.4 Year-versioned tax mapping

One versioned `TaxCategoryMapping` serves both outputs:

```text
taxYear, category, anlageVLine?, skr03Account?, skr04Account?, direction,
validFrom, validTo?, verificationFlag, sourceVersion,
accountOverride?, overrideByTaxAdvisor?, overrideAt?
```

The structure is binding for future implementation. Every concrete 2025 line and SKR account in
the source table is a realistic placeholder and remains `verify-before-production`. The selected
layout follows the **tax year**, not the file-creation year, and every overview states the form year
and source status.

The reference categories are `kaltmiete`, `nk_vorauszahlung`, `nk_nachzahlung`, `nk_guthaben`,
`afa`, `schuldzinsen`, `grundsteuer`, `versicherung`, `hauswart`, `heizkosten`,
`muellbeseitigung`, `instandhaltung`, `kaution` and `bank`. This is not a completed mapping for every
Page-02 catalogue row.

### 3.5 Readiness result

The future readiness result is immutable evidence for one attempted export. It records the export
kind, object, tax year, input/mapping/profile versions, ordered findings, severity (`rot` or `gelb`),
acknowledgements, chosen tax-year override where allowed, and whether generation was blocked.

Red findings are: payment without date; DATEV without adviser/client number; and no payment data in
the requested period. Yellow findings are: unmatched party; missing category; missing account;
missing AfA record; unresolved year-window assignment; unconfirmed interest proposal; expected-rent
gap; and detected VAT case. Every finding returns to its owning correction flow.

### 3.6 Export result and archive

The future pure boundary is:

```text
f(ledgerSnapshot, afaHandoff, mappingVersion, adviserProfileVersion, parameters)
  -> AnlageVOverviewBytes | DatevExtfBytes
```

An archive version freezes those input references, the readiness result, tax year, rule and mapping
versions, applicable `Rechtsstand`, generated bytes, filename, timestamp and content hash. Re-export
creates `vN+1`; it never overwrites `vN`. The archive contract does not by itself establish a
universal retention period: § 147a AO's checked six-year rule is conditional, and the separate
privacy retention schedule remains unresolved.

## 4. Conventions 11-K01–11-K11

1. `11-K01`: Anlage-V lines are year-versioned rules data, never engine constants.
2. `11-K02`: SKR03/SKR04 accounts are adviser-overridable defaults; the source values are blocked placeholders.
3. `11-K03`: ledger aggregation is exact integer-cent addition; only an unscheduled proportional split rounds once, half-up, with a residual.
4. `11-K04`: deposits are excluded from the Anlage-V result and use a clearing account in DATEV; the convention remains flagged.
5. `11-K05`: supported due items apply the 10-day rule automatically; other window payments need a yellow user decision and otherwise stay in the payment year.
6. `11-K06`: a partial aggregate rent payment is applied to cold rent first and advance operating costs second; the used order is documented.
7. `11-K07`: deductible interest is a marked, editable Page-03 proposal and requires confirmation.
8. `11-K08`: the tax adviser may write only the adviser profile and account mapping inside otherwise read-only guest access.
9. `11-K09`: booking text defaults to unit instead of full renter name; format is `[Art] [Einheit] [Zeitraum]`, and Belegfeld 1 carries the Lokara reference.
10. `11-K10`: Lokara provides calculation help and data transport, not ELSTER submission, tax advice or tax structuring.
11. `11-K11`: the working EXTF profile is `EXTF`/700/category 21/format 13, Windows-1252, semicolon, quoted text, decimal comma, CRLF, `TTMM` and `EXTF_*.csv`; every parameter remains blocked pending the official target-version specification and a real DATEV import.

## 5. Rules R1–R9

### R1 — tax-year assignment

Default to the calendar year of `datum`. For regularly recurring cold rent, operating-cost
advance, interest or supplier advance, switch to the due-date year only when payment and due date
both fall within the relevant 22 December–10 January window. A window payment without a due date
stays in the payment year until the yellow finding is confirmed.

### R2–R4 — payment splits

R2 splits a full supported rent payment into its exact cold-rent and operating-cost-advance Soll
amounts. R3 applies a partial payment to cold rent first, then the advance; unpaid Soll remains an
open item and is never exported as cash. An overpayment is split only up to Soll and the remainder
becomes `mieter_guthaben`, not income. R4 is the exceptional split without Soll:

```text
shareA = round_half_up(amount * numeratorA / denominator)
shareB = amount - shareA
```

The residual is never rounded separately.

### R5 — Anlage-V aggregation

For one object and tax year, sum ledger cents by the selected year-layout line. `nk_guthaben`
reduces the advance/settlement line and deposits are excluded. The reference calculation adds
Page-03 AfA and proposed interest without recalculation. Disagio and maintenance stay unmapped until
§ 3.2's line/deduplication gap is settled. Income minus Werbungskosten equals result. Every total
remains expandable to its individual ledger and handoff sources.

### R6–R7 — DATEV booking batch

One payment yields one booking row; a split yields one row per component. Amounts have no sign and
use a decimal comma. Receipt date is `TTMM`; Belegfeld 1 is the ledger reference; booking text uses
11-K09. Deposits use the clearing account. R7 places the rows after the EXTF header and column line
and writes Windows-1252 with CRLF.

The source's concrete account pairs and the S/H flag relative to the Umsatzkonto remain
**unverified**. No real EXTF may be produced from this oracle until both the official format and a
real Kanzlei-Rechnungswesen import prove them.

### R8 — readiness

Run readiness before generation. Any red finding blocks. Yellow findings remain visible in the
preview and archive, and may require acknowledgement; they are never silently cleared by export.

### R9 — validation

- Anlage V: income minus Werbungskosten equals result.
- DATEV arithmetic evidence: paired debit and credit totals reconcile.
- Windows-1252 preserves `ä ö ü ß €`; line endings are CRLF.
- All payment dates fit the declared batch period and required header values are present.

The debit/credit equality proves the source arithmetic only. It does not validate the blocked EXTF
single-row S/H representation.

## 6. Edge cases 11-E01–11-E15

| ID | Required result | Fixture |
| --- | --- | --- |
| E01 | Missing payment date is red and blocks both exports; never default it during export. | readiness contract |
| E02 | Missing category is yellow; no line/account assignment until fixed. | readiness contract |
| E03 | Missing selected-SKR account is yellow and links to mapping. | F14 |
| E04 | Prior-year NK settlement paid later belongs to its payment year. | F04 |
| E05a | January rent due 01.01 and paid 28.12: both in window, so new due year. | F05 |
| E05b | Old October rent paid 05.01: due date outside window, so payment year. | F07 |
| E05c | December rent due 31.12 and paid 05.01: both in window, so old due year. | F06 |
| E06 | Missing AfA record is yellow; line empty and workflow linked. | F02/readiness |
| E07 | Window payment without due date is yellow and defaults to payment year pending confirmation. | readiness contract |
| E08 | Partial payment exports only received cents; unpaid Soll stays open. | F09 |
| E09 | Paid renter credit reduces the advance/settlement income line. | F10 |
| E10 | Deposit receipt/refund is result-neutral and uses the clearing account. | F11 |
| E11 | DATEV without adviser/client number is red. | readiness contract |
| E12 | VAT case is yellow; V1 exports gross without BU/VAT logic and prints the required warning. | F16 |
| E13 | Overpayment splits to Soll and `mieter_guthaben`; the full movement still reconciles. | F15 |
| E14 | Umlauts and euro sign survive Windows-1252; invalid encoding blocks. | F12 |
| E15 | Re-export appends an immutable archive version and retains the old bytes. | archive contract |

The base namespace remains exactly `11-E01`–`11-E15`; E05 contains three explicit subcases.

## 7. Golden fixture contract

Every amount below is integer cents. Variant fixtures never change the reference strand.

| Fixture | Contract |
| --- | --- |
| F01 | Annual cold rent 2,328,000 + advances 564,000 = income 2,892,000. |
| F02 | Six cash costs total 984,000; plus AfA 540,103 and proposed interest 840,000 = WK 2,364,103. |
| F03 | 2,892,000 − 2,364,103 = result 527,897. |
| F04 | 2024 NK settlement 34,000 paid 14.03.2025 belongs to 2025; reference income becomes 2,926,000. |
| F05 | January 2026 rent paid 28.12.2025 is assigned to 2026 when due 01.01.2026. |
| F06 | December 2025 rent paid 05.01.2026 is assigned to 2025 when due 31.12.2025. |
| F07 | October 2025 rent paid 05.01.2026 remains in payment year 2026 because due date is outside the window. |
| F08 | Full WE-01 payment 77,000 splits 62,000 cold rent + 15,000 advance. |
| F09 | Partial 60,000 goes entirely to cold rent; open items are 2,000 and 15,000. |
| F10 | Credit payout 20,000 reduces annual advances from 564,000 to 544,000. |
| F11 | Deposit 174,000 has zero Anlage-V effect and uses the blocked clearing-account placeholder. |
| F12 | Income 92,000 and heating cost 36,000 preserve booking fields and `Müllbeseitigung Grünstraße ä ö ü ß €` in Windows-1252/CRLF. |
| F13 | Paired debit and credit totals are each 128,000; EXTF S/H presentation remains blocked. |
| F14 | Grundsteuer 98,000 keeps amount/date/text while only blocked SKR03/SKR04 account placeholders differ. |
| F15 | Payment 80,000 = cold rent 62,000 + advance 15,000 + renter credit 3,000. |
| F16 | VAT case stays gross at 119,000, is yellow and carries no BU key or net/VAT split. |

## 8. Required output and compliance wording

- Every moved year is visibly marked: `§ 11: dem Steuerjahr <Jahr> zugeordnet` with its payment
  context.
- The interest line says it is a proposed value from the user's repayment plan and must be checked
  against the bank certificate.
- A VAT case says: `USt-Fall erkannt — dieser Export enthält keine Umsatzsteuer-Logik. Bitte mit
  Ihrem Steuerberater klären.`
- The product-wide disclaimer remains `rechtskonform, keine Rechts- oder Steuerberatung`. No extra
  StBerG warning or approval claim is added to product copy.
- UI and marketing may say `Export im DATEV-Format`; they must not say `DATEV-zertifiziert` or
  `DATEV-Schnittstelle` without the required relationship.
- Booking text defaults to the unit, not the renter's full name. Data not needed by the adviser is
  not exported.
- No unverified Anlage-V line, account, EXTF parameter, S/H orientation or BFH file number is
  presented as production-ready.

## 9. Explicit production blocks

1. Pull each target year's official Anlage V and version its exact lines before season start.
2. Validate every default SKR03/SKR04 account and its semantics with a real tax adviser.
3. Pull the official target-version EXTF field list, header and Festschreibung semantics.
4. Prove account pairing and Soll/Haben orientation with a real DATEV Kanzlei-Rechnungswesen import.
5. Verify a controlling BFH file number for the 10-day-rule proposition before displaying it.
6. Keep the Page-03 AfA handoff blockers visible; Page 04 cannot clear Weg B or K09 uncertainty.
7. The exact class-specific privacy retention schedule remains a separate source-backed gap.
8. Assign Anlage-V lines for Disagio and handed-off maintenance and prevent double-counting against
   ledger `instandhaltung` before those fields enter an export.

The calculation paths may later be implemented behind these sentinels. Real output remains blocked
where it depends on them.

## 10. Exactly eight Page-04 Non-Goals and dependency boundaries

The complete Page-04 Non-Goals from `Non-Goals V1` are:

1. ELSTER direct transmission through ERiC (V3+).
2. DATEV Buchungsdatenservice/REST transfer (V2).
3. Receipt-image transfer to DATEV Unternehmen online/Belegbilderservice (V2).
4. Return channel from the adviser into Lokara (V2+).
5. VAT logic, BU keys, § 9 UStG split and input-tax allocation (V2); V1 only detects and warns.
6. § 82b EStDV multi-year maintenance distribution (V2); V1 gives a neutral review prompt only.
7. Charts beyond SKR03/SKR04 (not planned for V1).
8. Discounted-rental deduction under § 21 Abs. 2 EStG (V2).

Page 04 also has exactly two delegated source boundaries: AfA/interest/Disagio calculations arrive
from Page 03; operating-cost keys, NK allocation arithmetic, deadlines and UVI remain with Pages
01, 02 and 05. These are source boundaries, not additional Page-04 Non-Goals.

## 11. Exact seven-file correspondence ledger

These files remain unchanged until D3. Page 04 owns no deletion.

| File | Page-04 disposition |
| --- | --- |
| `FEEDBACK-to-Berkay-01b.md` | Heating/CO₂ implementation feedback; no Page-04 rule. |
| `FRAGEN-an-Berkay-02.md` | Owner-residual/UVI questions; no Page-04 rule. |
| `FRAGEN-an-Berkay-03.md` | Heating/UVI follow-up; its Page-04 R4 name collision is only a warning about namespaces. |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_01b-Uebergabe.md` | Heating/UVI corrections and current-register explanation; no Page-04 delta. |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_02.md` | Owner-residual/UVI decisions; no Page-04 delta. |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_03.md` | Later heating decisions; no Page-04 delta. |
| `berkay-work/Spec-Seiten/Antworten/08_BankMatching_F03_Patch.md` | Owned by `docs/15`; it does not alter the Page-04 payment-ledger export rules. |

## 12. Source coverage gate

| Source surface | Destination | Golden evidence | Status |
| --- | --- | --- | --- |
| Metadata, purpose, dependencies and two-output architecture | §§ 1, 3 | source-surface test | complete |
| Norms, case-law gap and K01–K11 | §§ 2, 4, 8–9 | register/blocker tuples | complete; flags retained |
| Inputs and future contracts | § 3 | contract-surface constants | complete; no schema claim |
| R1–R9 | § 5 | F01–F16 arithmetic/format checks | complete |
| E01–E15, including E05a–c | § 6 | exact edge map + readiness/archive checks | complete |
| Worked examples F01–F16 | § 7 | exact 16-ID oracle | complete |
| Output wording and format | § 8 | F05/F12/F16 + blocked-format checks | complete |
| Open format/legal questions | § 9 | exact blocker identities | complete; unresolved |
| Page-04 scope and eight Non-Goals | § 10 | exact eight-item tuple | complete |
| Current register CSV + 13 entry notes | § 2 | 13 complete metadata tuples; 7 checked/6 blocked | complete |
| README-for-Emir audit | §§ 1, 7, 9 | arithmetic green without clearing flags | complete |
| Seven-file correspondence scope | § 11 | exact seven-path tuple | complete |

This gate completes transcription only. It makes no production-readiness or implementation claim.
