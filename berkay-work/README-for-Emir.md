# README for Emir — Audit of the Calculations spec (as of 2026-07-29)

Read this once before you transcribe the Notion pages into Claude Code. It's the summary of a
full recompute + legal-check pass over spec pages 01b and 02–08, plus the Rechtsstand-Register
and the three sub-pages.

---

## Bottom line

**0 calculation errors.** All 183 worked examples were recomputed programmatically (Python
`Decimal`, `round_half_up`, integer cents, row by row) — every final cent value, every sum
check, every owner residual, every delta check holds.

| Page | Fixtures | Status |
|---|---|---|
| 01b Heating/CO₂ | 31 (F01–F31) | exact |
| 02 BetrKV catalog | 32 (09-F01–F32) | exact |
| 03 AfA | 34 (10-F01–F34) | exact |
| 04 Anlage V + DATEV | 16 (11-F01–F16) | exact |
| 05 Guards/deadlines | 24 (12-F01–F24) | exact |
| 06 Contract clauses | 19 (CLAUSES-F01–F19) | exact |
| 07 Investment KPIs | 14 (KPI-F01–F14) | exact |
| 08 Bank matching | 13 (BANKMATCH-F01–F13) | exact |

The arithmetic is solid. You can take the printed cent values directly as test oracles
(assert expected-values).

---

## What you must NOT treat as truth when transcribing

The spec flags these itself with `[UNSICHER]` / `verify-before-production`. They are
**placeholders of realistic magnitude, not verified values.** The computation paths are right,
the numbers are not:

- **Page 03 (AfA), Weg B / BMF sachwert:** NHK 725 €/m², building-price index 180, BGF factor
  1.35, minimum residual 30 %. Before production, pull the BMF Arbeitshilfe Excel and recompute
  `10-F02` against it. Without that step Weg B is not production-ready.
- **Page 04 (Anlage V), all numbers:** the Anlage-V line numbers (13/14/32/33/37/42/47–50/82/84)
  and the SKR03/SKR04 account numbers are placeholders. Pull the official form per tax year,
  fill `anlage_v_layout_<JJJJ>`. Cross-check the SKR accounts with a real tax advisor.
- **Page 04, DATEV EXTF:** header version 700 / category 21 / format version 13 and the S/H
  orientation must be tested against a **real import into DATEV Kanzlei-Rechnungswesen**. No
  real import test, no launch.
- **BFH case numbers:** three on page 03 (`IX R 2/08`, `IX R 51/00`, `IX R 41/17`) and the
  10-day-rule case number on page 04 sit in the register with `ZITAT UNSICHER`. The *statements*
  carry the calculation rules, the *case numbers* are unverified — **do not put them into warning
  texts or the tax-advisor dossier** until checked against the BFH database.
- **Page 07 (KPIs):** almost everything is convention (KPI-K01…K19), not law. The 42 % marginal
  tax rate and the 75 %/2 % AfA assumption are defaults, not derived values.

---

## Test rules you need to know (or correct fixtures will fail)

These fixture pairs compute **the same property with exactly one different input** and must
**never be asserted against each other**:

- `08-F01` (MDL path, metering-service heating costs) ↔ `01b-F01` (self-billing path). Both
  correct, two data paths. `08-F24` is the bridge (same building, heating line from 01b-F01).
- `10-F09`–`10-F12` and `10-F24` run on "Variante S" (WE-01 owner-occupied). On page 01/02
  WE-01 is rented year-round → never assert against `08-F01` / `09-F19`.
- Fixtures with elevator/fibre/PV (page 02) and new-build/pre-1925 (page 03) run on declared
  variants → they never feed the reference strand.

Two deliberate granularity divergences — do not mix them in code:
- **Area-days** (page 01/02, day-accurate) vs. **area-months** (page 03 `10-K08`, month-granular,
  because § 7 Abs. 1 S. 4 EStG is month-granular).
- **Accounting period principle:** `abfluss` (page 02, `09-K07`) vs. `leistungBis` (page 03
  `10-K12`, 15 % guard). Data-model consequence: **`leistungBis` must be filled even when the
  operating-cost page doesn't need it** — otherwise the guard silently falls back to the invoice
  date (`10-F19`: ten days = €49,200).

---

## Rechtsstand-Register: flag state after this audit

**8 entries flipped to `geprüft`** (value verified against the primary source):

| Entry | Source |
|---|---|
| Emission factor natural gas 0.201 / heating oil 0.266 / LPG 0.236 | EBeV 2030 Annex 2 Part 4 (No. 6 / 3b / 5b) |
| AfA rate 3 % / 2 % / 2.5 % | § 7 Abs. 4 S. 1 Nr. 2 a/b/c EStG |
| Acquisition-related production costs, 15 % threshold | § 6 Abs. 1 Nr. 1a EStG |
| Rent brake § 556d until 2029-12-31 | extension act, in force 2025-07-23 |

The three emission factors keep Rechtsnatur **Konvention** — only the *use as a fallback* is a
design choice; the number itself is the EBeV standard value.

**Deliberately left red** (do not flip without your own verification):
- All genuine conventions/heuristics (KPI-K*, 09-K*, 10-K*, bank-matching signal weights).
- Tenancy-law deadlines (§§ 543/558/557a/b) — fixtures use them correctly, but Berkay keeps
  tenancy law conservative as the most volatile driver.
- § 12 / § 6a HeizkostenV reduction rights, BGB §§ 362/366/367 — current law, but not
  personally re-read this session. Verifiable candidates for the next pass.
- All placeholders (Anlage-V lines, SKR, EXTF, unverified case numbers).

---

## One non-calculation finding: broken tables

In **Non-Goals V1** (page-06 section) the HTML tables
are broken: literal `n` instead of line breaks (`n<tr>n<td>`) plus orphaned `</table>` tags.
Renders in Notion as garbage. Not a calc/legal error, but fix it before the pitch — the affected
content (commercial-lease clauses, § 559 window, grace-period flag) is otherwise unreadable.

---

## Clear before transcription

None of this blocks the pitch, but these depend on you/Emir before code goes to production:

1. Assign the target `docs` number for page 01b → globally rename fixtures `01b-Fxx` / `KPI-*`.
2. Fix `docs/03 § 11` (row-wise rounding + fictitious occupancy — the file is wrong, Notion is right).
3. Page 02 needs a column `afaKlasseVorschlag` (3.1) for the 15 % guard.
4. Make `leistungBis` mandatory in the data model (see above).

---

**Takeaway for you:** the arithmetic is green — you can take the fixtures 1:1 as tests. The risks
are exclusively in (a) the flagged placeholder numbers, (b) the unverified case numbers, (c) the
data-model couplings above — not in the calculation core.
