# AfA — purchase allocation, deduction and 15% guard

**Status:** D2 transcription prepared; awaiting Emir's approval
**Rechtsstand:** 07/2026
**Authoritative Page:**
`berkay-work/Spec-Seiten/03 · AfA (Abschreibung) 3a95fd4207318179b865c8a1c9e4b487.md`
**Fixtures:** exactly `10-F01`–`10-F34` in
`packages/rules-store/tests/berkay_10_golden.py`
**Implementation status:** specification and data-only oracle only. No AfA engine, schema, API,
screen, PDF, migration, tax export or production rules-store data is added by this slice.

This document turns a purchase, construction or unentgeltlicher Erwerb into the annual object AfA,
the deductible share, the remaining book value, the 15% guard and an annual loan-interest prefill.
It owns the calculation boundary handed to future `docs/11` and `docs/14`; it does not own Anlage-V
lines, DATEV, archive/readiness rules or full financing KPIs.

## 1. Sources, precedence and settled corrections

The transcription uses the complete Page 03, the current 180-row
`Rechtsstand-Register.csv`, all 46 Page-03 entry notes, `Non-Goals V1`, the
`README-for-Emir` arithmetic audit and all seven correspondence-retirement files. The CSV controls
structured values and flags. The per-entry Markdown exports remain explanatory evidence but have
stale flags for four rows.

`Antwort-an-Emir_01b-Uebergabe.md` § 4b establishes why the refreshed export changed checked flags.
The current CSV therefore controls: the residential rates 3%, 2% and 2.5%, plus the 15% rule, are
`geprüft`; the other 42 Page-03 rows remain `verify-before-production`. `geprüft` means the primary
text was checked, not lawyer-approved. The later Antwort 03 changed heating-factor values and flags,
not these four AfA rows.

The dated Non-Goals note says self-use reduces the AfA basis. That sentence is superseded by Page 03
R6–R9 and the settled D2 decision: self-use reduces **deductible AfA only**. It never reduces the
basis, never changes the object AfA and never extends the depreciation period. The older 10-K07
entry-note sentence that says the area ratio acts on the basis is stale for the same reason. Its CSV
metadata and its area-key convention remain current.

The audit recomputed all 34 examples as cent-exact. That validates the printed arithmetic only. It
does not clear placeholders, uncertain citations or production flags. In particular, `10-F02` is
preserved exactly as arithmetic evidence while NHK 725 EUR/m², index 180, BGF factor 1.35 and the
30% minimum remain placeholders that block production Weg B.

## 2. Legal basis and complete register surface

Legal values belong in the versioned rules store with an as-of date. They must not become constants
inside a future engine. Page 03 cites:

- § 7 Abs. 4 S. 1 Nr. 2 lit. a–c EStG for the residential 3%, 2% and 2.5% rates;
- § 7 Abs. 4 S. 1 Nr. 1 EStG for the V1-blocked business-building path;
- § 7 Abs. 4 S. 2 EStG and the BMF letter of 22.02.2023 for shorter useful-life reports;
- § 7 Abs. 1 S. 4 EStG and R 7.4 Abs. 2 EStR for first-year twelfths;
- § 7 Abs. 5a and § 7b EStG for detection-only notices, never V1 calculations;
- § 6 Abs. 1 Nr. 1a EStG, § 255 Abs. 2 S. 1 HGB and the cited BFH cases for the 15% guard;
- § 9 Abs. 1 S. 3 Nr. 1 and Nr. 7 EStG for interest and AfA as Werbungskosten;
- § 11 Abs. 2 S. 3–4 EStG for Disagio; § 255 Abs. 1 HGB for acquisition cost;
- § 11d Abs. 1 EStDV for the predecessor's basis and remaining period;
- § 42 AO and BFH IX R 12/14 for contractual purchase-price allocation;
- §§ 164, 175 Abs. 1 S. 1 Nr. 2 AO for retroactive tax-assessment consequences;
- R 7.4 Abs. 9 and R 4.2 Abs. 4 EStR for later production cost and use separation;
- the BMF purchase-price tool, ImmoWertV 2021/NHK 2010 and Anlage 1 ImmoWertV;
- § 32a EStG only for a non-exported marginal-tax display.

The Page also cites BFH IX R 26/19, IX R 12/14, IX R 25/14, IX R 15/15 and IX R 22/15. The cited
case-number/date pairs IX R 2/08, IX R 51/00 and IX R 41/17 remain `ZITAT UNSICHER`; their statements
drive fixtures, but the citations must not appear in product warnings or an advisor dossier until
checked against the BFH database.

The complete metadata mirror is `PAGE_03_REGISTER_ROWS` in the data-only oracle: each of the 46
rows carries `Wert`, `Betrag / Satz`, current CSV `Flag`, `Letzte Änderung um`, `Prüfen bis`,
`Quelle`, `Rechtsgrundlage §`, `Rechtsnatur` and `Rechtsstand`; the shared affected page is
the exact CSV value `03 · AfA (Abschreibung)` plus its Notion source URL. The exact current flag
groups are:

| Flag | Complete row identities |
| --- | --- |
| `geprüft` (4) | AfA-Satz 2% — Fertigstellung 1925 bis 2022 · AfA-Satz 2.5% — Fertigstellung vor 1925 · AfA-Satz 3% — Wohngebäude nach 31.12.2022 · Anschaffungsnahe Herstellungskosten — 15%-Grenze |
| `verify-before-production` (42) | Zwölftelung im Anschaffungs-/Herstellungsjahr · 3% Wirtschaftsgebäude · degressive AfA · 80 Jahre Gesamtnutzungsdauer · unentgeltlicher Erwerb · Schuldzinsen · Bescheidänderung · Gestaltungsmissbrauch · Zwölftelung Gebäude · Nutzflächenaufteilung · nachträgliche AK/HK · Gutachtenqualifikation · NHK 2010 · Erweiterung/wesentliche Verbesserung · Grenzsteuersatz · BMF-Verfahren · Disagio-Rechtsfolge · AfA als Werbungskosten · Anschaffungskosten · Sonderabschreibung · kürzere Nutzungsdauer · 10-K01–10-K15 · jährlich übliche Arbeiten · vertragliche Aufteilung · Schönheitsreparaturen · Darlehens-Direktzuordnung · BMF-Arbeitshilfe nicht bindend · Grundschuldkosten |

All 46 rows have Rechtsstand `07/2026`, `Prüfen bis` 05.08.2026 and a last-change timestamp of
28.07.2026 16:35 or 16:37. The exact source URLs, legal bases and legal/convention/heuristic status
are preserved in the oracle rather than shortened here.

## 3. Inputs and units

Money is integer cents. Areas are integer hundredths of a square metre. Dates are day-accurate,
while AfA arithmetic is month-granular. Rates are integer basis points. No float crosses the
boundary.

### 3.1 Object and acquisition

`afaDatensatz` contains `objektId`; `erwerbsart` (`kauf`, `neubau`, `unentgeltlich`);
`gebaeudetyp` (`efh`, `zfh`, `mfh`, `gemischt`, `gewerbe`); mandatory
`fertigstellungsjahr`; `fertigstellungsdatum` for a new build; mandatory
`uebergangNutzenLastenDatum` for a purchase; `notarvertragsDatum` as prefill only;
`wohnflaecheGesamt`; `grundstuecksflaecheM2`; and nullable `veraeusserungsDatum`.

### 3.2 Acquisition or production costs

Inputs are `kaufpreisCent`, `grunderwerbsteuerCent`, `notarGrundbuchCent` excluding mortgage-deed
cost, `grundschuldkostenCent` as financing cost, `maklerprovisionCent`, `sonstigeAnkCent`,
`beweglicheWgCent`, `herstellungskostenCent`, separately non-depreciable
`grundstueckskostenCent`, and `aussenanlagenCent` parked as a separate V2 asset.

### 3.3 Purchase-price allocation

`aufteilungsWeg` is `vertrag`, `bmf` or `gutachten`. Weg A reads
`vertragGebaeudeCent`/`vertragBodenCent`. Weg B reads a mandatory user-supplied
`bodenrichtwertCentProM2`, `bodenrichtwertStichtag`, nullable `bruttogrundflaecheM2`,
`standardstufe` (default 3), versioned `nhkCentProM2Bgf`, versioned `baupreisindexBp` and
`gesamtnutzungsdauerJahre` (Page default 80). Weg C reads `gutachtenGebaeudeanteilBp` and optional
`gutachtenDokumentId`. A missing land value is never guessed.

### 3.4 Use, reports, works and loans

Each non-overlapping `selfUsePeriod` has `vonDatum`, nullable `bisDatum`,
`selbstgenutzteFlaeche` and optional `einheitIds`. No periods means the explicit displayed default
“vollständig vermietet — stimmt das?”. A report supplies `rndGutachtenJahre`, qualification
`oebuv`/`zertifiziert`/`sonstige`, and `rndGutachtenDatum`; `sonstige` is stored but never applied.

Each 15%-guard measure requires positive `nettoCent`, mandatory `leistungBis`, a class
`instandsetzungModernisierung`, `erweiterung`, `jaehrlichUeblich` or `herstellungOriginaer`, and
`belegId`. Page 02 proposes exactly these mappings:

| Page 02 ID | AfA class proposal |
| --- | --- |
| `instandhaltung` | `instandsetzungModernisierung` |
| `erneuerung` | `instandsetzungModernisierung` |
| `schoenheitsreparaturen` | `instandsetzungModernisierung` |

`erweiterung` is never inferred. It is a mandatory fact about the building project.

Each loan has `nominalbetragCent`, `auszahlungsbetragCent`, annual `sollzinsBpProJahr`, either
`anfaenglicheTilgungBp` or `annuitaetCentProMonat`, `zinsbindungJahre`, `ersteRateDatum`, V1
`zahlungsrhythmus=monatlich`, assignment `objektAnteilig`/`direktVermieteterTeil`/
`direktSelbstgenutzterTeil`, `sondertilgung[]` and optional `bankZinsbestaetigungCent`. A bank
confirmation always wins over the prefill.

### 3.5 Recognition and predecessor fields

Detection-only fields are `betriebsvermoegen`, nullable `bauantragDatum`, nullable
`baubeginnOderKaufvertragDatum`, `effizienzNachweis` (`keiner`, `eh40`, `qng`), `objekt.denkmal`
and nullable `kernsanierungJahr`. Route U requires the predecessor's
`bemessungsgrundlageCent`, `afaSatzBp` and `kumulierteAfaCent`; if one is absent, the result is
absent and an advisor handoff is produced.

## 4. Conventions 10-K01–10-K15

1. `10-K01`: Weg B is the product default, but a supportable contractual allocation wins.
2. `10-K02`: BGF fallback is area × 1.35 for MFH or × 1.25 for EFH/ZFH; estimate, label and allow override.
3. `10-K03`: use a year-versioned construction-price index; no interpolation.
4. `10-K04`: cap residual production value at 30% when age reaches/exceeds total useful life.
5. `10-K05`: linear age reduction in full years; no modernization points or life extension in V1.
6. `10-K06`: building share below 50% or above 95% gives a notice; contract/BMF difference above 10 percentage points gives a warning; neither blocks.
7. `10-K07`: rental ratio uses usable area, never income; it affects deductibility, not basis or rate.
8. `10-K08`: denominator is hundredth-m² × month.
9. `10-K09`: the source result treats a started rental month as fully rented. `10-F11` also preserves the day-level alternative. The 59.11 EUR choice is unresolved and production-blocking.
10. `10-K10`: every generated money amount rounds `ROUND_HALF_UP` once to cents; ratios stay exact; rates use basis points.
11. `10-K11`: the final year takes the remaining book value; the same residual rule closes Disagio.
12. `10-K12`: the 15% clock uses mandatory `leistungBis`, not invoice/payment date. It is separate from Page 02 `abfluss`; no schema is approved here.
13. `10-K13`: the loan prefill uses 30/360 with monthly settlement; the bank figure wins.
14. `10-K14`: market Disagio is at most 5% with at least five years fixed interest; this is unverified administrative practice.
15. `10-K15`: 42% is display-only and never enters an exported amount.

## 5. Rules R1–R13

### R1–R3: route, costs and allocation

R1 routes `unentgeltlich` to predecessor continuation, `neubau` to production cost and `kauf` to
purchase cost. Commercial buildings hard-block; mixed use warns and labels the result approximate.
Route U calculates only with all three predecessor values.

R2 order is binding:

```text
ank = GrESt + Erwerbs-Notar/Grundbuch + Makler + sonstige ANK
basis = kaufpreis - beweglicheWg
akGesamt = basis + ank
```

Mortgage-deed cost is excluded. Movable assets must be below the purchase price. For a new build,
`akGesamt=herstellungskosten`; land stays separate and R3 is skipped.

R3 produces one exact building fraction. Weg A uses the contract split; Weg B uses R3b; Weg C uses
the report basis points. `gebaeudeAK=round_half_up(akGesamt×quote)` and `bodenAK` is the residual.
R3b calculates land value; input/derived BGF; indexed NHK; normal production value; full-year age;
residual factor `max((GND-age)/GND, 30%)`; building value; total property value; exact building
fraction. Missing land value/year, or zero total property value, hard-blocks. R3c calculates both
contract and BMF routes when inputs exist and emits only non-blocking plausibility messages.

### R4–R9: rate, annual deduction and book value

R4 chooses first: qualified shorter-life report; blocked business-building 3% case; residential
post-2022 3%; 1925–2022 2%; pre-1925 2.5%; otherwise hard block. The purchase year never determines
the rate. R4b only detects degressive AfA, § 7b, monument status and a report lead for an old,
non-core-renovated building.

R5 sums rented area-months against `wohnflaecheGesamt×12`. Excess self-use or overlapping periods
hard-block. Under the unresolved K09 source route, a month with a rental start/end is counted fully
as rented. R6 basis is building acquisition cost plus later production cost effective from its
year. Use never changes the basis.

R7 computes full annual AfA, then first/sale-year months. R8 applies the rental numerator only over
R7-allowed months. `afaNichtAbziehbar=afaJahrObjekt-afaAbziehbar`; it is lost, not postponed. R9
reduces book value by full object AfA, including private-use years. Sale and full depreciation end
the series; the final amount is the residual and book value never goes negative.

### R10–R13: later costs, guard, finance and handoff

R10 adds `erweiterung`, `herstellungOriginaer` and R11-reclassified measures to the basis at the
start of their year. The rate is unchanged and the series is not extended.

R11 sets `grenzeCent=round_half_up(gebaeudeAK×15%)`; the inclusive window is transfer date through
three years minus one day. Only `instandsetzungModernisierung` with `leistungBis` inside counts.
At 80% it warns. Above 100%, all counted measures are retroactively and fully reclassified by their
year; old maintenance deductions are reversed and the tax-assessment warning is emitted.

R12 uses a bank confirmation if present. Otherwise it derives the monthly annuity, applies special
repayment before that month's interest, rounds 30/360 interest monthly, refuses non-positive
repayment and separates interest from repayment. R12b either deducts market Disagio immediately or
spreads it through the fixed-interest period with first/final residual years. R12c deducts loan
interest fully for proven direct rental assignment, zero for direct private assignment, or by R5
area-months. Direct assignment requires separate loan and payment paths.

R13 hands future Page 04/Page 07 one object/year tuple: year, basis, rate or report life, annual full
AfA, months, object AfA, deductible/non-deductible AfA, closing book value, deductible interest and
Disagio, maintenance and the 15%-guard threshold/cumulative/window/status.

## 6. Edge cases 10-E01–10-E26

| ID | Required result | Fixture |
| --- | --- | --- |
| E01 | Missing land value hard-blocks Weg B; offer A/C and BORIS link, never estimate. | F26 |
| E02 | Missing construction year hard-blocks rate and Weg B; no 2% default. | F27 |
| E03 | Contract/BMF difference over 10 percentage points warns; contract still wins. | F03 |
| E04 | Building share outside 50–95% notices; above 95% adds the under-5%-land wording. | F28 |
| E05 | Age at/above GND uses labelled 30% minimum. | F29 |
| E06 | Missing transfer date hard-blocks; notary date is offered, never adopted silently. | F30 |
| E07 | December acquisition uses 1/12. | F08 |
| E08 | Mid-month use change preserves both K09 month and day alternatives. | F11 |
| E09 | Excess self-use area or overlapping periods hard-block. | F31 |
| E10 | Multiple non-overlapping periods sum by area-month. | F12 |
| E11 | Final year uses the remaining book value. | F13 |
| E12 | Sale year includes the started sale month, then stops. | F14 |
| E13 | Exceeding 15% reclassifies all counted costs, by year, retroactively. | F16 |
| E14 | Work ending after the window does not count; `leistungBis` controls. | F19 |
| E15 | Expansion is outside the counter but is production cost from the start. | F17 |
| E16 | Narrow, usually annual maintenance is outside the counter. | F18 |
| E17 | Unentgeltlicher Erwerb continues only with all predecessor values. | F32 |
| E18 | Residential completion after 2022 uses 3%. | F05 |
| E19 | Completion before 1925 uses 2.5%. | F06 |
| E20 | Later production cost raises basis from the start of its year. | F20 |
| E21 | Market Disagio is immediate; otherwise spread with time/residual years. | F22 |
| E22 | Special repayment applies before the next same-month interest date. | F23 |
| E23 | Part-private loan interest uses area unless direct assignment is proven. | F24 |
| E24 | Mortgage-deed notary cost leaves acquisition cost and becomes financing cost. | F25 |
| E25 | Shorter-life report applies only for `oebuv` or `zertifiziert`. | F33 |
| E26 | Movable assets leave the purchase price before allocation and are parked separately. | F34 |

## 7. Golden fixture contract

All money below is integer cents. The exact input and output dictionaries live in the data-only
oracle; this table is the complete 34-ID trace.

| Fixture | Contract |
| --- | --- |
| F01 | Acquisition cost 53,553,600; mortgage notary 45,000 excluded. |
| F02 | Weg B building 27,005,129 + land 26,548,471 = 53,553,600; four placeholders block production. |
| F03 | Contract and BMF routes reconcile; annual AfA delta 295,333. |
| F04 | 1978, 200 bp, annual AfA 540,103. |
| F05 | New build 300 bp; five-month first year 562,500. |
| F06 | 1912, 250 bp, annual AfA 750,000. |
| F07 | March transfer gives 10/12 = 450,086. |
| F08 | December gives 45,009; 12×45,009 deliberately differs from annual AfA. |
| F09 | Variante S, whole-year self-use: deductible 367,493 + private 172,610 = 540,103. |
| F10 | Variante S, rental from 1 July: 453,798 + 86,305 = 540,103. |
| F11 | Variante S, K09 month 453,798 vs day 447,887; delta 5,911; unresolved blocker. |
| F12 | Variante S, two periods: 439,414 + 100,689 = 540,103. |
| F13 | First year + 49 full years + 89,996 residual = basis. |
| F14 | August 2028 sale AfA 360,069; closing book value 24,574,665. |
| F15 | Threshold 4,050,769; cumulative 3,870,000; buffer 180,769; warning. |
| F16 | Cumulative 5,120,000; all costs reclassified by 2024/2025/2026. |
| F17 | Expansion 2,200,000: outside counter, inside later production cost. |
| F18 | Annual work 58,400, three-year 175,200: outside counter. |
| F19 | `leistungBis` separates 10 and 20 March; counterfactual 4,920,000. |
| F20 | Later production cost raises basis to 29,205,129 and annual AfA to 584,103. |
| F21 | Nine 30/360 installments: interest 1,072,748; repayment 607,255. |
| F22 | Market 1,200,000 immediately vs non-market first-year 240,000. |
| F23 | 500,000 special repayment saves 3,004 interest in 2024. |
| F24 | Variante S interest: proportional 729,911 vs direct rental 1,072,748. |
| F25 | Mortgage notary produces immediate first-year net advantage 44,547. |
| F26 | No land value: no Weg B quote, building cost or AfA. |
| F27 | No construction year: no rate, building cost or AfA. |
| F28 | 96% contract share continues with notice and warning, not block. |
| F29 | 30% minimum gives building 22,381,978 and annual AfA 447,640; placeholder blocker. |
| F30 | Missing transfer date blocks; wrong notary assumption overstates first year by 45,008. |
| F31 | Excess self-use and overlapping periods each hard-block. |
| F32 | Predecessor/successor shares 120,000 + 240,000 = 360,000; missing data means no result. |
| F33 | Qualified 25-year report gives 1,080,205; four-cent final residual. |
| F34 | Movables split first; building 26,601,718 + land 26,151,882 = 52,753,600. |

`10-F09`–`10-F12` and `10-F24` are isolated **Variante S**. They never feed Page 01/02 reference
fixtures `08-F01` or `09-F19`.

## 8. Required output wording

The 80% warning is:

> Sie haben seit dem Kauf 33.900,00 € von 40.507,69 € an Renovierungskosten erreicht (83,7 %).
> Wird die Grenze von 15 % der Gebäude-Anschaffungskosten bis zum 14.03.2027 überschritten, sind
> alle diese Kosten rückwirkend keine sofort abziehbaren Werbungskosten mehr, sondern werden über
> die Restnutzungsdauer abgeschrieben. Prüfen Sie, ob sich weitere Maßnahmen auf die Zeit nach dem
> 14.03.2027 verschieben lassen.

The exceeded warning is:

> Die 15 %-Grenze ist überschritten (51.200,00 € von 40.507,69 €). Alle Instandsetzungs- und
> Modernisierungskosten der ersten drei Jahre gelten rückwirkend als Herstellungskosten (§ 6 Abs. 1
> Nr. 1a EStG). Lokara hat die Abschreibungsgrundlage entsprechend erhöht. Bereits eingereichte
> Steuererklärungen der betroffenen Jahre müssen berichtigt werden — bitte sprechen Sie mit Ihrem
> Steuerberater.

The regular rate explanation is: “Ihr Gebäude wurde 1978 fertiggestellt → 2 % pro Jahr über 50
Jahre (§ 7 Abs. 4 Satz 1 Nr. 2 Buchst. b EStG, Stand 07/2026).” The hard-block and plausibility
copy is:

- F26: “Für die Berechnung nach der Methode des Finanzamts brauchen wir den Bodenrichtwert Ihres
  Grundstücks. Sie finden ihn kostenlos unter boris.nrw.de — Adresse eingeben, Wert in €/m²
  ablesen.”
- F27: “Ohne das Baujahr können wir weder den Abschreibungssatz noch den Gebäudeanteil bestimmen.
  Sie finden es im Kaufvertrag, im Energieausweis oder im Grundbuchauszug.”
- F28: “Ihr Kaufvertrag setzt den Grundstücksanteil mit 51,00 €/m² an. Der amtliche Bodenrichtwert
  für Ihre Lage beträgt 340,00 €/m². Ein Grundstücksanteil von unter 5 % ist gegenüber dem
  Finanzamt schwer zu halten (§ 42 AO). Lokara rechnet mit Ihrem Vertragswert weiter und
  dokumentiert die Abweichung.”
- F30: “Der Übergang von Nutzen und Lasten steht in Ihrem Kaufvertrag — meist ein bis drei Monate
  nach dem Notartermin, oft an die Kaufpreiszahlung gekoppelt. Nicht der Notartermin und nicht der
  Grundbucheintrag.”

The product-wide disclaimer remains “rechtskonform, keine Rechts- oder Steuerberatung”. No
unverified BFH case number is printed. Until § 7b values are verified, its detection-only copy is
limited to “Sonderabschreibung möglich — Steuerberater prüfen lassen”; it contains no threshold.
The qualified residual-life-report lead uses the personalized `10-F33` annual effect, not a generic
savings claim, while partner selection remains open.

## 9. Open authority gaps and production blocks

- Pull the current BMF purchase-price Excel, import/version its tables and recompute F02. Until
  then Weg B is blocked, including NHK 725 EUR/m², index 180, BGF 1.35 and minimum 30%.
- Decide K09: month-granular F11 result 453,798 or day-granular 447,887. The unresolved 5,911-cent
  difference blocks production use-change output.
- Establish the controlling EStR version for R 7.4 and R 4.2.
- Verify § 7b thresholds before any notice contains numbers.
- Verify the three uncertain BFH citations before displaying or exporting them.
- A future data model must require `leistungBis` independently of Page 02 `abfluss`; this slice
  records the contract and adds no schema.
- A future partner process may consume the personalized shorter-life-report result; no partner is
  selected here.
- The Page's old request to add `afaKlasseVorschlag` is settled at the contract level by the three
  exact proposals above. No production catalogue row changes here.

No new question file is created during D2. These gaps remain explicit in this document and oracle.

## 10. Out of scope and all 13 Page-03 Non-Goals

Owned here: R2 purchase cost; three allocation routes and Weg B; rate/detection; area-month use;
basis, annual AfA and book value; later production cost; 15% guard; annual loan-interest/Disagio
prefill and R13 handoff.

Deferred to separate `docs/11`: all Anlage-V line mappings, SKR03/SKR04 accounts, DATEV EXTF,
export archive, readiness and tax-year form data. Deferred to `docs/14`: net/return/DSCR/cashflow,
full annuity plan, forecasts, scenarios and the tax rate as a calculation input.

The complete Non-Goals V1 set is:

1. Degressive AfA under § 7 Abs. 5a (detect only; revisit V1.x).
2. § 7b special depreciation (detect only; V2).
3. Monument AfA §§ 7h, 7i, 10f, 10g (detect only; V2).
4. Full BMF-tool depth across all types/stages/regions/modernization (V1.x).
5. Automatic BORIS land-value retrieval (V1.x).
6. Per-unit AfA instead of one object record with area split (V1.x).
7. Discounted-rental limits under § 21 Abs. 2 (V2).
8. Later acquisition cost attributable to land, such as development charges (V1.x).
9. Depreciation tables for movable assets and outdoor facilities; split and park only (V2).
10. Sale-gain calculation under § 23 EStG (V2).
11. Foreign buildings, heritable building rights and usufruct (not planned).
12. Automatic `erweiterung` classification from invoice text (not planned).
13. Business assets/commercial units under § 7 Abs. 4 S. 1 Nr. 1 (hard-block V1; V2).

Also outside this Page: inheritance/gift tax, VAT/input-tax allocation, checking whether an invoice
is factually justified and tax advice.

## 11. Exact seven-file correspondence ledger

These files remain unchanged until D3. Page 03 owns no deletion.

| File | Page-03 disposition |
| --- | --- |
| `FEEDBACK-to-Berkay-01b.md` | § 4b/current-export explanation traced here; other sections remain with docs/03, docs/16 or history. |
| `FRAGEN-an-Berkay-02.md` | No Page-03 calculation correction; owner/UVI questions remain mapped to docs/03/docs/16. |
| `FRAGEN-an-Berkay-03.md` | No Page-03 calculation correction; heating corrections remain mapped to docs/03/docs/16. |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_01b-Uebergabe.md` | § 4b confirms the refreshed checked flags; only the three AfA rates and 15% rule apply here. |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_02.md` | No Page-03 delta; heating/UVI decisions are out of scope. |
| `berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_03.md` | No Page-03 delta; later heating values do not override the current Page-03 CSV rows. |
| `berkay-work/Spec-Seiten/Antworten/08_BankMatching_F03_Patch.md` | Entirely owned by docs/15; no Page-03 content. |

## 12. Source coverage gate

| Source surface | Destination | Golden evidence | Status |
| --- | --- | --- | --- |
| Metadata, purpose, dependencies | §§ 1, 10 | complete-surface test | complete |
| Norms, decisions, all K01–K15, open legal questions | §§ 2, 4, 9 | register metadata + F02/F03/F11/F33 | complete; flags retained |
| Inputs 3.1–3.8 | § 3 | F01–F34 dictionaries | complete |
| R1–R13 | § 5 | F01–F34 arithmetic checks | complete |
| E01–E26 | § 6 | exact E→F mapping | complete |
| Worked examples F01–F34 | § 7 | exact 34-ID oracle | complete |
| Output wording | § 8 | F15/F16 plus hard-block cases | complete |
| Owned/deferred/out-of-scope | § 10 | 13 non-goal identities | complete |
| Open points 1–9 | § 9 and ownership notes | blockers/proposals in oracle | complete |
| Current register CSV + 46 entry notes | § 2 | 46 complete metadata tuples; 4 checked/42 blocked | complete |
| Non-Goals V1 | § 10 | 13 exact identities | complete |
| README-for-Emir audit | §§ 1, 7, 9 | arithmetic green without clearing flags | complete |
| Antwort 01b § 4b | §§ 1–2 | current four checked flags | complete |
| Seven-file correspondence scope | § 11 | exact seven-path tuple | complete |

This gate completes transcription only. It makes no production-readiness or implementation claim.
