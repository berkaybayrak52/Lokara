# Contract clauses — selection, risk and workflow routing

**Status:** D2 transcription prepared for Emir's review; not approved or implemented

**Rechtsstand:** 07/2026

**Authoritative Page:**
`berkay-work/Spec-Seiten/06 · Vertragsklauseln — Risiko-Memo 3ab5fd420731813799c0c1b419eac4f3.md`

**Fixtures:** exactly `CLAUSES-F01`–`CLAUSES-F19` in
`packages/rules-store/tests/berkay_13_golden.py`

**Implementation status:** specification and data-only oracle only. No clause body, letter body,
rules data, schema, migration, API, engine, adapter, UI, signature integration, payment execution or
production contract generator is added by this slice.

This document defines future selection, compatibility, warning and routing contracts for
residential form clauses. Page 06 supplies the arithmetic and legal-risk decisions below, but it
does **not** supply a complete clause-text/version catalogue or complete Mieterhöhung-, Kündigung-
or Mahnung bodies. Those missing sources still block M8 implementation.

## 1. Sources, precedence, correction and arithmetic audit

The transcription uses the complete Page 06, all 17 Page-06 rows in the current 180-row
`Rechtsstand-Register.csv`, the seven Page-06 entries in `Non-Goals V1`, its later Wizard-field
note, the `README-for-Emir` audit and all seven correspondence-retirement files. The CSV controls
structured register values and flags.

The audit recomputed all 19 Page-06 examples with `Decimal`, integer cents and half-up rounding and
found the printed arithmetic exact. That proves only the examples. It does not approve the eight
flagged register rows, resolve the Page's `[UNSICHER]` items, provide missing text catalogues or
demonstrate production behavior.

One Page-06 statement is superseded by the approved Page-03 contract. E11 and the dated Non-Goals
note say self-use reduces the AfA basis. `docs/10-afa.md` controls that tax calculation: the basis
stays unchanged and self-use reduces **deductible AfA only**. `docs/11-tax-export.md` controls tax
income and receives no rental income for a self-used unit. Page 06 only records and routes the
`SelfUsePeriod`; it performs no tax arithmetic. This confirmed correction must not be restored from
the older wording.

## 2. Legal basis and complete register surface

Page 06 cites:

- § 535 BGB and form-clause case law for cosmetic repairs;
- § 307 BGB for small-repair clause review, with no statutory euro ceiling;
- § 551 BGB for the deposit maximum and installments;
- §§ 557a and 557b BGB for graduated and index rent;
- § 556 and § 556 Abs. 2 BGB for operating-cost allocation and advances;
- § 535 BGB plus BGH case law for the ban on a general pet prohibition;
- §§ 126, 126a and 126b BGB for written, qualified-electronic and text form;
- § 550 BGB for a fixed term over one year;
- §§ 558 and 558a BGB plus the applicable state regulation for comparative-rent increases;
- § 559 BGB for modernization increases;
- § 556d BGB for the rent brake;
- §§ 543 Abs. 2 Nr. 3 and 569 Abs. 3 Nr. 1–2 BGB for arrears termination and grace payment;
- §§ 573 and 573c BGB for ordinary termination and its periods; and
- § 286 BGB for default and reminders.

These citations define the Page's risk surface. They do not provide the missing clause or action
texts. Product output continues to use the approved `rechtskonform, keine Rechts- oder
Steuerberatung` boundary.

The complete CSV metadata is mirrored field for field in `PAGE_06_REGISTER_ROWS`. The summary is:

| Register row | Amount/rule | Flag | Legal nature · Rechtsstand |
| --- | --- | --- | --- |
| Schriftform Staffel-/Indexklausel | QES or paper; simple e-signature is insufficient | `geprüft` | Gesetz · 07/2026 |
| Mietpreisbremse (§ 556d) | +10% over comparative rent; through 31.12.2029 | `geprüft` | Gesetz · 07/2026 |
| Kappungsgrenze angespannter Markt (§ 558) | 15% in 3 years; territory per state regulation | `verify-before-production` | Verordnung · 07/2026 |
| Formzwang befristeter Vertrag über 1 Jahr | written form; breach makes it indefinite, not void | `geprüft` | Gesetz · 07/2026 |
| Verzugsschwelle fristlose Kündigung | >1 monthly rent over two dates or ≥2 over longer period | `geprüft` | Gesetz · 07/2026 |
| Indexmiete VPI-Bindung (§ 557b) | Destatis VPI; ≥12 months; text-form declaration | `verify-before-production` | Gesetz · 07/2026 |
| Kappungsgrenze Standard (§ 558) | 20% in 3 years | `geprüft` | Gesetz · 07/2026 |
| Kleinreparaturen Jahresgrenze | about 6% of annual net cold rent | `verify-before-production` | Konvention · 07/2026 |
| Schonfristzahlung ordentliche Kündigung (geplant) | planned extension was not in force on 09.07.2026 | `verify-before-production` | Gesetz · 07/2026 |
| Modernisierung Umlagesatz (§ 559) | 8% p.a. of attributable cost | `geprüft` | Gesetz · 07/2026 |
| Signatur-Gate V1 | simple e-signature only without graduated/index rent | `verify-before-production` | Konvention · 07/2026 |
| Kleinreparaturen Einzelgrenze | about €100 per repair | `verify-before-production` | Konvention · 07/2026 |
| Staffelmiete Mindestintervall (§ 557a) | amount stated; each step unchanged ≥12 months | `geprüft` | Gesetz · 07/2026 |
| § 556d Handling (Produkt) | warning plus recorded self-declaration; no block | `verify-before-production` | Konvention · 07/2026 |
| Kaution (§ 551) | max three net cold rents, payable in three installments | `geprüft` | Gesetz · 07/2026 |
| Modernisierung Kappung (§ 559) | €3/m², or €2/m² below €7/m², in six years | `geprüft` | Gesetz · 07/2026 |
| SEPA-Lastschriftmandat — Einzug/Verfall | collection needs creditor ID/PIS; stated expiry 36 months | `verify-before-production` | Verordnung · 07/2026 |

The exact flag count is nine `geprüft` and eight `verify-before-production`. `geprüft` means the
primary statutory text was checked, not lawyer-approved. The § 556d row is also confirmed by
`Antwort-an-Emir_01b-Uebergabe.md` § 4b. That correspondence does not clear the adjacent warn-only
product convention.

## 3. Future logical contracts — no schema approval

All money is integer cents. VPI points, square metres and rates use `Decimal`, never float. Dates
are day-accurate unless the approved owning document defines another axis. The shapes below are
logical implementation boundaries, not database or API schemas.

The complete Page-06 input inventory is:

| Input | Unit/type | Source and ownership |
| --- | --- | --- |
| `clauseBlockId`, `version` | string, immutable version | future rules catalogue; bodies missing |
| `nettokaltmiete` | integer cents | user/contract |
| `gesamtmiete` | integer cents | user/contract; arrears basis shared with `docs/12` |
| `wohnflaeche` | decimal m² | user; Page 03 owns tax use |
| `ortsuebliche_vergleichsmiete` | integer monthly cents | manual evidence/provider; `docs/12` owns guard state |
| `kappungsgrenze_prozent` | integer 20 or 15 | versioned rule/state flag; 15% coverage blocked |
| `vpi_alt`, `vpi_neu` | decimal index points, basis 2020=100 in the source fixture | Destatis/rules adapter |
| `letzte_aenderung_datum` | day-accurate date | contract history; `docs/12` owns date arithmetic |
| `modernisierungskosten_wohnung` | integer cents | user input |
| `staffel_schritte[]` | date plus absolute integer-cent amount | contract schedule |
| `kleinrep_einzelgrenze`, `kleinrep_jahresgrenze` | integer cents | blocked rules-store conventions |
| `rueckstand[]` | month, Soll cents, Ist cents | future payment ledger/open items; `docs/12` owns guard state |
| `mpb_ausnahme` | `keine`, `Vormiete`, `Neubau_ab_01.10.2014`, `umfassende_Modernisierung` | user self-declaration |
| `mpb_erklaerung_ts` | timestamp | audit evidence |
| `sepa_mandatsreferenz` | string, at most 35 characters | optional user input |
| `sepa_mandatsdatum` | day-accurate date | optional user input |
| `eigennutzung` | boolean | Wizard routing flag, not tax arithmetic |
| `eigennutzung_periode` | optional start/end | routes to Page-03 `SelfUsePeriod` |

### 3.1 Versioned clause reference

A future contract composition refers to a clause by stable block ID and immutable version, plus
validity period, source version, `Rechtsstand`, verification flag and compatibility metadata. A
legal change creates a new version and identifies affected compositions; it never overwrites the
old reference.

The actual clause body and its approved version catalogue are absent from Page 06. A reference may
therefore be represented for future design, but no production block can be populated or rendered
from this transcription.

### 3.2 Contract composition

A composition freezes selected version references, the applicable property/tenancy inputs, the
compatibility result, signature route, warnings, acknowledgements and source versions. It must
reject a graduated/index mixed composition. It routes fixed-term, graduated-rent and index-rent
form requirements to the gate instead of treating the final document as universally signable.

Page 06 owns clause selection, compatibility warnings and routing. It does not own operating-cost
classification (`docs/09`), AfA (`docs/10`), tax income (`docs/11`) or reusable dates and guard
states (`docs/12`).

### 3.3 Compatibility and signature gate

The future gate returns an ordered result for each selected combination:

```text
selectedClauseVersions, conflicts, requiredForm, allowedSignatureRoute,
blocking, legalSources, verificationFlags, affectedContractReferences
```

- Graduated and index rent are mutually exclusive.
- A simple e-signature is blocked for graduated or index clauses; route to paper or future QES.
- QES is not a V1 capability.
- The register also names a fixed term over one year, but Page 06 supplies no corresponding worked
  signature fixture. That coverage gap remains explicit before implementation.

### 3.4 Immutable risk result

Every evaluation returns the input and rule versions, deterministic values, ordered findings,
severity, blocking/warn-only state, required acknowledgement, legal/convention label and
`Rechtsstand`. A risk result records what Lokara checked; it does not state that a contract or rent
is legally effective.

The § 556d self-declaration records the chosen exception and timestamp. It does not verify the
exception or legalize an excessive rent. Index decline remains informational with no automatic
adjustment until its product behavior is approved.

### 3.5 SEPA mandate capture

The future optional capture stores mandate reference and mandate date together. Reference length
is at most 35 characters and unique per mandate; the date cannot be in the future. One missing
field marks the mandate incomplete but does not block the contract. V1 stores and displays the
result only. It performs no collection; PIS and creditor ID remain absent.

The register's 36-month expiry statement remains `verify-before-production`. Page 06 supplies no
expiry workflow or fixture, so storage must not silently present that rule as approved behavior.

### 3.6 Action-workflow input

The future Page-06 output may package the chosen route, amounts, source references, warning/risk
result and acknowledged facts as input to a Mieterhöhung-, Kündigung- or Mahnung workflow.
`docs/12` owns date arithmetic, thresholds, guard state and trigger timing; Page 06 consumes those
results without duplicating them.

No complete action-letter body exists in the source. Page 06 therefore approves workflow inputs
and routing only, not generation or sending of a legally complete declaration.

## 4. Formula decisions B1–B8

Global Page-06 rounding is half-up to whole cents. Intermediate values stay exact unless a step
explicitly says to round.

### B1 — graduated rent (§ 557a)

Each schedule step states an absolute rent. The interval from the preceding step must be at least
12 months. An earlier step is ineffective and rent remains at the preceding amount. During a
graduated-rent period, the Page's compatibility contract excludes the competing index route.

### B2 — index rent (§ 557b)

```text
new_rent_cents = half_up(old_rent_cents * new_vpi / old_vpi)
```

The change needs at least 12 months since the last change and an officially published index.
Index points are `Decimal`. The input basis year must be compatible; rebasing remains outside the
Page and `docs/12` owns the corresponding guard behavior.

### B3 — comparative-rent increase (§ 558)

```text
cap = half_up(current_rent_cents * (1 + cap_percent / 100))
target = min(comparative_rent_cents, cap)
increase = target - current_rent_cents
```

B3a uses 20%; B3b uses 15% only where a current state regulation applies. The rent must have been
unchanged for at least 12 months and become effective no earlier than 15 months after the last
increase; the required justification accompanies the request. `docs/12` owns those dates, the
three-year lookback, consent/action dates and guard state. The 15% territory list is absent.

### B4 — modernization increase (§ 559)

```text
annual = half_up(attributable_cost_cents * 0.08)
monthly = half_up(annual / 12)
cap_per_sqm_cents = starting_rent_per_sqm_cents < 700 ? 200 : 300
six_year_cap_cents = cap_per_sqm_cents * area_sqm
increase = min(monthly, remaining_six_year_cap_cents)
```

B4a covers the €3/m² cap and B4b the €2/m² cap. The cap is cumulative across six years. The exact
day on which the six-year window starts for each measure remains unresolved.

### B5 — small repairs

For each repair, charge the full cost only when it does not exceed the single-repair limit;
otherwise charge zero, with no excess-only split. Sum accepted repairs and cap the result at the
annual limit. Both source defaults—about €100 per repair and about 6% of annual net cold rent—are
conventions and remain blocked.

### B6 — deposit (§ 551)

Maximum deposit is three net cold monthly rents, payable in three installments with the first due
at tenancy start. F08 is exactly divisible and checks the installment sum. The source gives no cent
residual rule for a maximum not divisible by three; implementation needs a source-backed split
before claiming that untested case.

### B7 — immediate termination for arrears

- B7a: arrears on two consecutive due dates and strictly more than one gross monthly rent.
- B7b: over a longer period, arrears at least two gross monthly rents.

Page 06 owns the risk/routing result. `docs/12` owns event-driven open-item arithmetic, threshold
state, cure events and reminder timing.

### B8 — § 556d initial rent

```text
maximum_rent_cents = half_up(comparative_rent_cents * 1.10)
```

An agreed rent above the result creates a warning, not a block or automatic cap. The user chooses
an exception or `keine`; choice and timestamp are recorded. Lokara does not verify the exception.

## 5. Edge cases E1–E11

| ID | Required result | Fixture/owner |
| --- | --- | --- |
| E1 | A falling index yields the exact calculated lower rent, but Lokara performs no automatic adjustment; final product behavior remains open. | F11 |
| E2 | A graduated step below 12 months is ineffective; prior rent remains. | F12 |
| E3 | In an existing-tenancy § 558 workflow, comparative rent binds when below the cap. Contract setup uses § 556d instead. | F13 |
| E4 | Cumulative § 559 increases are limited to the remaining six-year cap; window start remains open. | F14 |
| E5 | A repair over the single limit contributes zero, not the limit or excess. | F07 |
| E6 | Arrears just below two monthly rents do not satisfy B7b. | B7/test boundary; `docs/12` state owner |
| E7 | Timely grace payment cures the immediate termination; ordinary termination remains effective under the stated 07/2026 position. Planned Mietrecht-II change remains unapproved. | risk route; `docs/12` cure state |
| E8 | Simple e-signature is blocked for graduated/index clauses and routes to paper/future QES. | F15 |
| E9 | § 556d excess is warn-only; record exception self-declaration and timestamp, never legal approval. | F16–F17 |
| E10 | SEPA fields are optional; future date is invalid but does not block the contract; incomplete mandate blocks any later collection. | F18 |
| E11 | Self-use creates no tenancy and disables rent clauses; route area/period to Page 03 and zero rental income to Page 04. Basis-reduction wording is superseded. | F19; `docs/10`/`docs/11` |

The E1 user information says the price index fell, the index can work in both directions, and no
automatic adjustment is made. Its legal/product wording remains marked uncertain and must not be
promoted into final product copy before approval.

## 6. Exact golden fixture contract

| Fixture | Contract |
| --- | --- |
| `CLAUSES-F01` | €800.00 plus €25.00 after 12 months gives absolute step €825.00. |
| `CLAUSES-F02` | 90,000 × 122.7 / 118.5 half-up = 93,190 cents. |
| `CLAUSES-F03` | § 558 at 20% caps 70,000 to 84,000; increase 14,000. |
| `CLAUSES-F04` | § 558 at 15% caps 70,000 to 80,500; increase 10,500. |
| `CLAUSES-F05` | 8% of 2,000,000 = 160,000 annually; monthly 13,333; €3/m² cap does not bind. |
| `CLAUSES-F06` | Same monthly amount, but €2/m² cap binds at 12,000. |
| `CLAUSES-F07` | Unverified 10,000/6% limits: 12,000 repair contributes zero; renter total 33,500. |
| `CLAUSES-F08` | Deposit maximum 210,000 in three installments of 70,000; sum reconciles. |
| `CLAUSES-F09` | Two missed 85,000 installments exceed the strict one-rent threshold. |
| `CLAUSES-F10` | Five 35,000 shortfalls total 175,000, meeting the 170,000 threshold. |
| `CLAUSES-F11` | Falling index calculates 88,861 cents; no automatic adjustment and behavior open. |
| `CLAUSES-F12` | Ten-month step is ineffective; rent remains 80,000. |
| `CLAUSES-F13` | Comparative rent 75,000 binds below cap 84,000; increase 5,000. |
| `CLAUSES-F14` | First 13,333 leaves 4,667 under the 18,000 cumulative cap. |
| `CLAUSES-F15` | Graduated clause plus simple e-signature blocks and routes to paper/future QES. |
| `CLAUSES-F16` | Agreed 105,000 is 6,000 over the 99,000 § 556d value; warn-only, no cap. |
| `CLAUSES-F17` | Claimed prior-rent exception is stored with timestamp but not verified. |
| `CLAUSES-F18` | A 19-character reference and non-future date store a complete, non-collecting mandate; future date is field-invalid only. |
| `CLAUSES-F19` | Full-year self-use creates no tenancy, reduces deductible AfA through Page 03, leaves the AfA basis unchanged and gives Page-04 rental income zero. |

## 7. Explicit authority gaps and production blocks

1. Page 06 provides no complete clause-text/version catalogue.
2. It provides no complete Mieterhöhung, Kündigung or Mahnung bodies.
3. All eight `verify-before-production` register rows remain blocked.
4. Final index-decline behavior remains unresolved.
5. The day-accurate start of the § 559 six-year window remains unresolved.
6. State-regulation coverage for the 15% cap is absent.
7. Small-repair single and annual defaults remain unverified conventions.
8. Planned Mietrecht-II changes to index rent and grace-payment effects were not in force under the
   source's stated dates and require a new as-of check before production.
9. SEPA mandate expiry remains unverified and has no workflow fixture.
10. The fixed-term-over-one-year signature route has no worked fixture.
11. The source has no cent-residual rule for a deposit maximum not divisible by three.

The routing/risk transcription may be reviewed independently. M8 implementation remains blocked
until a separate source-backed clause and action-template catalogue exists.

## 8. Exactly seven Page-06 Non-Goals and eleven source exclusions

The complete Page-06 section of `Non-Goals V1` contains exactly seven items:

| Non-Goal | Source reason | Affected Page · revisit |
| --- | --- | --- |
| Commercial-space clauses | Different form regime (BEG IV: text form since 01.01.2025) and content control from residential leases. | 06 · V2 |
| Graduated/index mixed clauses in one contract | §§ 557a and 557b are mutually exclusive; composition enforces either/or. | 06 · not planned |
| QES integration for form-bound contracts | V1 has only simple text-form signature; graduated/index and fixed terms over one year are gated. | 06 · V2 |
| Automatic checking/calculation of § 556d exceptions | Prior rent, new build and comprehensive modernization are facts; V1 records self-declaration, warning and storage only. | 06 · V2 |
| Individual lawyer effectiveness review | Catalogue blocks are a tool boundary, not individual legal advice. | 06 · not planned |
| Individually negotiated non-form clauses | The catalogue covers form clauses; separately negotiated terms do not need AGB content control. | 06 · not planned |
| Modernization announcement under § 555c | Belongs to the M9 guard/reminder flow, not the clause catalogue. | 06, 05 · with Page 05 |

Page 06's own Out-of-Scope paragraph contains exactly eleven exclusions:

1. commercial lease contracts;
2. condominium/special-ownership agreements;
3. graduated/index mixed clauses;
4. individually negotiated clauses;
5. individual lawyer effectiveness review;
6. QES integration;
7. automatic § 556d exception checking/calculation;
8. modernization announcement under § 555c;
9. renter rent-brake complaint/information request;
10. SEPA collection/execution; and
11. the self-use tax calculation itself.

The later Wizard-field note confirms that capture of the SEPA fields and self-use flag is in scope,
while collection and tax calculation remain outside Page 06.

## 9. Exact seven-file correspondence ledger

These files remain unchanged until D3. Page 06 owns no deletion.

| File | Page-06 disposition |
| --- | --- |
| `FEEDBACK-to-Berkay-01b.md` | Heating owner-residual/self-use presentation question; no Page-06 clause rule. |
| `FRAGEN-an-Berkay-02.md` | Repeats the owner-residual/self-use presentation question; no Page-06 clause rule. |
| `FRAGEN-an-Berkay-03.md` | Heating/UVI follow-up; no Page-06-owned correction. |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_01b-Uebergabe.md` | § 4b confirms the § 556d +10% and 31.12.2029 checked register value; remaining content belongs to heating/UVI/register history. |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_02.md` | Owner-residual/UVI decisions; no Page-06-owned correction. |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_03.md` | Later heating decisions; no Page-06-owned correction. |
| `berkay-work/Spec-Seiten/Antworten/08_BankMatching_F03_Patch.md` | Bank-matching F03 correction only; no Page-06 rule. |

## 10. Complete source coverage

| Source surface | Destination | Fixture/evidence |
| --- | --- | --- |
| Metadata, purpose and target module | header and §§ 1, 3, 7 | exact 19-ID namespace; M8 block |
| Legal basis | § 2 | register mirror and blocked legal/convention labels |
| Inputs | § 3 and B/E contracts | fixture fields use cents, `Decimal`, dates and enums |
| B1–B8 | § 4 | F01–F10 and F16–F17 |
| E1–E11 | § 5 | F07, F11–F19 plus explicit delegated guard states |
| `CLAUSES-F01…F19` | § 6 | exact data-only oracle and arithmetic checks |
| Page Out of Scope | § 8 | exact eleven-item tuple |
| Current Page-06 register rows | § 2 | exact 17-row, nine/ eight flag checks |
| `Non-Goals V1`, Page 06 | § 8 | exact seven-item tuple |
| `README-for-Emir` | §§ 1, 6–7 | exact arithmetic; does not clear source flags |
| Seven correspondence files | § 9 | exact path tuple and dispositions |
| Approved Page-03/04/05 ownership | §§ 1, 3–5 | compatibility checks against docs/10, docs/11 and docs/12 oracles |

## 11. Approval and implementation boundary

This slice changes documentation and tests only. Green data-only checks prove transcription
coverage and arithmetic, not current production behavior or legal approval. It adds no clause body,
letter template, production rule, schema, migration, API, engine, adapter, UI, signature or SEPA
execution. No implementation may start from this document alone while the missing text catalogues
and explicit authority gaps remain.
