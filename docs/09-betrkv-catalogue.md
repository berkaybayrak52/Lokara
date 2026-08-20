# BetrKV catalogue — versioned classification before allocation

**Status:** D2 transcription complete; approved and merged
**Authoritative Page:**
`berkay-work/Spec-Seiten/02 · BetrKV — Betriebskosten-Katalog 3a95fd4207318199a2c8fd9b390aacf4.md`  
**Fixtures:** exactly `09-F01`–`09-F32` in
`packages/rules-store/tests/berkay_09_golden.py`  
**Implementation status:** specification only. No catalogue or Page 02 gate is wired into production.

This document owns the deterministic step between an incoming cost position and the existing
operating-cost allocation engine. It decides whether the position is allocable, its BetrKV number,
the proposed allocation key, its object-level § 35a labour amount and the non-allocable remainder.
It does not allocate renter shares; the calculations in the fixtures only prove compatibility with
the Page 01 contract in `docs/08-statement-document.md`.

## 1. Source status and precedence

The complete Page 02, its later answer, the authoritative register CSV, Non-Goals V1 and the audit
note were reconciled on 17.08.2026. Structured values and flags would come from
`berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv`, but the current 180-row CSV contains
**no row assigned to Page 02** and no `09-K01`–`09-K11` entries. Therefore:

- all eleven Page 02 conventions remain `verify-before-production`;
- none of their values may be presented as checked law merely because the arithmetic is green;
- the catalogue may be implemented and tested later, but real output remains blocked wherever it
  depends on an unverified convention or unresolved classification;
- `berkay-work/` is not changed here. The missing register rows belong to a later authoritative
  register export.

`Antwort-an-Emir_03.md` § 2 is later than the Page and settles the one relevant correction:
`nichtUmlagefaehigGesamtCent` for the reference object is **100,800 cents**. The Page's old request
to leave Page 01 block (b) pending is superseded. D1 already carried this correction into `docs/08`
and the `08-F21` oracle.

The audit in `Anlagen/README-for-Emir.md` confirms all 32 worked examples cent-exact, but explicitly
does not clear flagged values. It also requires a nullable `afaKlasseVorschlag` catalogue field for
the 15% AfA guard. This document records the interface; approved `docs/10-afa.md` owns the exact
three proposals and explicitly refuses to infer `erweiterung`.

## 2. Legal basis and legal status

| Rule | Effect in this specification | Status at 07/2026 |
| --- | --- | --- |
| § 556 Abs. 1 BGB | Residential operating costs require a contractual allocation agreement. | statute quoted by Page; no Page 02 CSV row |
| § 556 Abs. 3 S. 1 Hs. 2 BGB | Economic-efficiency warnings are advisory and never change an amount. | statute quoted by Page; heuristic bands unverified |
| § 556a Abs. 1 S. 1 BGB | Residential area is the fallback without another agreement. | statute quoted by Page; defaults remain conventions |
| § 556a Abs. 1 S. 2 BGB | Recorded consumption or causation uses the corresponding measured key. | statute quoted by Page |
| § 560 Abs. 1 BGB | A newly arising cost needs the configured Mehrbelastungsklausel. | statute quoted by Page |
| § 1 Abs. 1 S. 2 BetrKV | Landlord self-performance may use a comparable third-party amount without VAT. | V1 non-goal |
| § 1 Abs. 2 Nr. 1–2 BetrKV | Administration and maintenance/repair are not operating costs. | catalogue exclusion |
| § 2 Nr. 1–17 BetrKV | Catalogue basis; Nr. 17 items must be specifically named in the contract. | versioned catalogue input |
| § 2 Nr. 14 Hs. 2 BetrKV | A caretaker line may not duplicate work already billed under Nr. 2–10 or 16. | warning and confirmed correction |
| § 2 Nr. 15, § 2 S. 2 BetrKV | Cable cut-off and post-01.12.2021 new-installation exclusions. | date-versioned gate |
| § 72 Abs. 2, Abs. 7 S. 1 TKG | Fibre cap: 60 EUR/year, 540 EUR total per unit, time and installation limits. | Page value; no Page 02 CSV row |
| § 35a Abs. 2–3 EStG | Carry the invoice/object labour amount; Page 01 allocates it to renters. | typical percentages are conventions |
| § 307 Abs. 2 Nr. 1 BGB | A form clause cannot turn an excluded residential cost into an operating cost. | individual-agreement question unresolved |
| §§ 6–9 HeizkostenV | Heating and warm-water costs use the service period. | content remains owned by `docs/03` |

Page 02 also relies on the cited BGH decisions for the general Betriebskosten reference, the
specific naming of Nr. 17 costs, ground-floor lift allocation, the payment principle and
full-maintenance evidence, smoke-detector rental, and garden accessibility. Exact citations remain
source provenance; they are not copied into product warning text unless their register status is
cleared.

### 2.1 Explicitly unresolved legal classifications

- `trinkwasseruntersuchung` is provisionally Nr. 2 with an additional-contract-naming warning; a
  specialist must decide whether it belongs to Nr. 17.
- `elektropruefung` is provisionally Nr. 17 and naming-required; recurring fixed-installation tests
  remain disputed against maintenance.
- an individually negotiated residential administration-cost agreement is treated conservatively
  like the invalid form-clause case until specialist review.
- only `versicherung` has a Page-provided efficiency band. The remaining catalogue bands are
  absent; the guard must stay inert when no band exists.

## 3. Versioned catalogue interface

The future rules-store row is resolved at
`leistungBis ?? belegDatum`, with inclusive day-granular validity:

```text
id: stable slug
bezeichnung: German statement label
betrkvNummer: string | null
umlagefaehig: bool
defaultSchluessel: Wohnfläche | Personenzahl | Wohneinheiten |
                    Wasserverbrauch | Heizkosten (Messdienst) | Direktzuordnung
benennungspflichtig: bool
periodenprinzip: abfluss | leistung
lohnanteilTypischProzent: integer 0..100 | null
bandbreiteEurProM2Jahr: {min, max} | null
sonderregel: keine | aufzugEg | hauswartSplit | gartenNutzbarkeit |
             schornsteinNr4a | rauchmelderMiete | kabelStichtag |
             neuanlage2021 | glasfaserCap | ungezieferVorbeugend
afaKlasseVorschlag: string | null
anlageVKategorie: string | null
gueltigVon / gueltigBis: date | null
rechtsstand: MM/YYYY
verificationFlag: geprüft | verify-before-production
```

`afaKlasseVorschlag` and `anlageVKategorie` are dependency seams, not values owned here. Prepared
`docs/10-afa.md` defines the former's exact proposals; the latter still waits for `docs/11`.

### 3.1 Allocable catalogue rows

`S` is the default key, `L` the typical labour percentage, `P` the period principle and `B` the
Nr. 17 naming flag. Every default is a proposal, not an automatic legal conclusion.

| ID | German label | BetrKV | S | L | P | B | Special rule |
| --- | --- | --- | --- | ---: | --- | --- | --- |
| `grundsteuer` | Grundsteuer | 2 Nr. 1 | Wohnfläche | — | abfluss | no | — |
| `wasserversorgung` | Wasserversorgung | 2 Nr. 2 | Wasserverbrauch | — | leistung | no | — |
| `entwaesserung` | Entwässerung | 2 Nr. 3 | Wasserverbrauch | — | leistung | no | — |
| `niederschlagswasser` | Niederschlagswasser | 2 Nr. 3 | Wohnfläche | — | abfluss | no | — |
| `trinkwasseruntersuchung` | Trinkwasseruntersuchung | 2 Nr. 2 | Wohnfläche | — | abfluss | no | unresolved classification |
| `heizkosten` | Heizkosten | 2 Nr. 4a | Heizkosten (Messdienst) | — | leistung | no | — |
| `wartung_heizung` | Wartung Heizungsanlage | 2 Nr. 4a | Heizkosten (Messdienst) | 60 | leistung | no | — |
| `brennstoffversorgung` | Brennstoffversorgungsanlage | 2 Nr. 4b | Heizkosten (Messdienst) | — | leistung | no | — |
| `waermelieferung` | Wärmelieferung (Contracting) | 2 Nr. 4c | Heizkosten (Messdienst) | — | leistung | no | — |
| `etagenheizung_wartung` | Reinigung/Wartung Etagenheizung | 2 Nr. 4d | Direktzuordnung | 70 | abfluss | no | — |
| `warmwasser` | Warmwasser | 2 Nr. 5a | Heizkosten (Messdienst) | — | leistung | no | — |
| `verbundene_anlagen` | Verbundene Heizungs-/WW-Anlage | 2 Nr. 6 | Heizkosten (Messdienst) | — | leistung | no | — |
| `aufzug` | Aufzug | 2 Nr. 7 | Wohneinheiten | 40 | abfluss | no | `aufzugEg` |
| `strassenreinigung` | Straßenreinigung | 2 Nr. 8 | Wohnfläche | — | abfluss | no | — |
| `winterdienst` | Winterdienst | 2 Nr. 8 | Wohnfläche | 60 | abfluss | no | — |
| `muellbeseitigung` | Müllbeseitigung | 2 Nr. 8 | Personenzahl | — | abfluss | no | — |
| `gebaeudereinigung` | Gebäudereinigung | 2 Nr. 9 | Wohnfläche | 83 | abfluss | no | — |
| `ungezieferbekaempfung` | Ungezieferbekämpfung | 2 Nr. 9 | Wohnfläche | 70 | abfluss | no | `ungezieferVorbeugend` |
| `gartenpflege` | Gartenpflege | 2 Nr. 10 | Wohnfläche | 83 | abfluss | no | `gartenNutzbarkeit` |
| `allgemeinstrom` | Allgemeinstrom / Beleuchtung | 2 Nr. 11 | Wohnfläche | — | abfluss | no | — |
| `schornsteinreinigung` | Schornsteinreinigung | 2 Nr. 12 | Wohneinheiten | 79 | abfluss | no | `schornsteinNr4a` |
| `versicherung` | Sach- und Haftpflichtversicherung | 2 Nr. 13 | Wohnfläche | — | abfluss | no | — |
| `hauswart` | Hauswart | 2 Nr. 14 | Wohnfläche | 80 | abfluss | no | `hauswartSplit` |
| `gemeinschaftsantenne` | Gemeinschafts-Antennenanlage | 2 Nr. 15a | Wohneinheiten | — | abfluss | no | `kabelStichtag`, `neuanlage2021` |
| `breitband_verteilanlage` | Breitband-Verteilanlage | 2 Nr. 15b | Wohneinheiten | — | abfluss | no | `kabelStichtag`, `neuanlage2021` |
| `glasfaser_bereitstellung` | Glasfaser-Bereitstellungsentgelt | 2 Nr. 15c | Wohneinheiten | — | abfluss | no | `glasfaserCap` |
| `waeschepflege` | Einrichtungen für die Wäschepflege | 2 Nr. 16 | Wohneinheiten | — | abfluss | no | — |
| `dachrinnenreinigung` | Dachrinnenreinigung | 2 Nr. 17 | Wohnfläche | 80 | abfluss | yes | — |
| `rauchwarnmelder_wartung` | Wartung Rauchwarnmelder | 2 Nr. 17 | Wohneinheiten | 63 | abfluss | yes | `rauchmelderMiete` |
| `lueftungsanlage_wartung` | Wartung Lüftungsanlage | 2 Nr. 17 | Wohnfläche | 70 | abfluss | yes | — |
| `elektropruefung` | Prüfung der Elektroanlage (DGUV V3) | 2 Nr. 17 | Wohnfläche | 80 | abfluss | yes | unresolved classification |
| `sonstige` | Sonstige Betriebskosten (frei benannt) | 2 Nr. 17 | Wohnfläche | — | abfluss | yes | — |

### 3.2 Non-allocable catalogue rows

These rows must exist so an invoice can be recorded, warned and routed to Page 01 block (b). They
never enter an allocation denominator.

| ID | German label | Basis | Later destination |
| --- | --- | --- | --- |
| `verwaltungskosten` | Verwaltungskosten, Hausverwalter-Honorar | § 1 Abs. 2 Nr. 1 BetrKV | `docs/11` |
| `instandhaltung` | Instandhaltung / Instandsetzung / Reparatur | § 1 Abs. 2 Nr. 2 BetrKV | `docs/10`/`docs/11` |
| `erneuerung` | Erneuerung / Anschaffung, including smoke-detector rent | § 1 Abs. 2 Nr. 2 BetrKV | `docs/10`/`docs/11` |
| `schoenheitsreparaturen` | Schönheitsreparaturen | § 1 Abs. 2 Nr. 2 BetrKV | `docs/10`/`docs/11` |
| `instandhaltungsruecklage` | Zuführung zur Instandhaltungsrücklage | not a current § 1 Abs. 1 cost | on use only |
| `bankgebuehren` | Kontoführung, Bankgebühren, Zahlungsverkehr | § 1 Abs. 2 Nr. 1 BetrKV | `docs/11` |
| `mietausfallwagnis` | Mietausfallwagnis | no actual cost | none |
| `rechtsverfolgung` | Rechtsverfolgung, Inkasso, Mahnkosten | § 1 Abs. 2 Nr. 1 BetrKV | `docs/11` |
| `abrechnungserstellung` | Erstellung der Betriebskostenabrechnung | § 1 Abs. 2 Nr. 1 BetrKV | `docs/11` |
| `kabel_altentgelt` | Kabelanschluss-Grundgebühren from 01.07.2024 | § 2 Nr. 15 lit. a/b BetrKV | `docs/11` |
| `antenne_neuanlage` | Antennen-/Verteilanlage erected from 01.12.2021 | § 2 S. 2 BetrKV | `docs/11` |

Non-allocable cost is not vacancy. Vacancy is the residual of an allocable line after renters are
rounded; non-allocable cost has no denominator and feeds block (b) directly.

## 4. Inputs and output boundary

All money is integer cents, dates are inclusive and day-granular, and areas are square metres with
two decimals. A cost position supplies:

```text
kostenartId, bruttobetragCent, nichtUmlagefaehigCent,
lohnanteilCent?, schluesselOverride?, wohnungId?,
leistungVon?, leistungBis?, belegNr, belegDatum, zahlungsdatum
```

The contract input supplies `umlageVereinbarung`, `benannteSonstige[]`,
`mehrbelastungsklausel`, `schluesselVereinbarung{kostenartId -> schluessel}` and
`nutzungsart`. Residential use is the only V1 path.

Each accepted position produces exactly one Page 01 input:

```text
{kostenart, betrkvNummer, schluessel,
 gesamtbetragCent = umlagefaehigCent,
 lohnanteilCent, wohnungId?, hinweis?}
```

The object also receives `nichtUmlagefaehigGesamtCent`. No renter amount is calculated here.

## 5. Binding rule order

All capping and split arithmetic is rounded `ROUND_HALF_UP` to whole cents before Page 01 receives
the integer. Renter shares are later rounded line-by-line by Page 01. The future NK switch must use
the single property-level owner residual described in `docs/02` and `docs/08`; largest remainder is
the current implementation only and remains unchanged in this documentation slice.

### R1 — Resolve the catalogue row

Resolve the version at `leistungBis ?? belegDatum`. If validity changes within the relevant period,
split the position day-exactly before continuing.

### R2 — Allocability gate

The first matching rule wins:

1. A non-allocable catalogue row sends the entire amount to block (b).
2. A contract with no allocation agreement yields zero allocable cost.
3. Commercial use hard-blocks V1.
4. A naming-required Nr. 17 item not named in one contract yields zero for that renter; the object
   denominator is unchanged.
5. An affected antenna/broadband installation from 01.12.2021 yields zero.
6. Cable costs are capped to the overlap ending 30.06.2024.
7. Fibre charges are capped in order by installation date, collection year, 6,000 cents per unit
   and year, and 54,000 cents cumulative per unit.
8. Explicit service dates cap the numerator day-exactly; the full-period object denominator stays.
9. A new cost without a Mehrbelastungsklausel yields zero.

### R3 — Clean a mixed invoice

`umlagefaehigCent = bruttobetragCent - nichtUmlagefaehigCent`. A caretaker split, smoke-detector
rent, inaccessible garden work, acute pest removal and full-maintenance deduction are visible user
proposals. Nothing is silently split. The default caretaker proposal is 75/15/10 and the default
full-maintenance deduction is 40%; both are unverified conventions.

### R4 — Choose the allocation key

Precedence is: direct `wohnungId`, contractual key, prior-year object override, actually recorded
consumption, then catalogue default. A missing consumption denominator proposes area but never
switches silently. Without confirmation, Page 01's zero-denominator guard leaves the whole amount
with the owner.

### R5–R8 — Hooks, labour, warning and handoff

- Ground-floor lift units remain included unless the contract explicitly says otherwise.
- Warn if chimney sweeping may already be included in the heating statement.
- The Nr. 14 duplicate-work guard proposes reducing the caretaker line, not the specialist invoice.
- Use an invoice labour amount before the typical percentage. Require
  `0 <= lohnanteilCent <= umlagefaehigCent`; otherwise hard-block without a partial result.
- Cost-per-area efficiency bands only warn. They never alter or block the statement.
- Hand the accepted object-level tuple and non-allocable total to Page 01.

## 6. Edge-case contract

| ID | Required result | Fixture |
| --- | --- | --- |
| `09-E01` | Unknown type routes to naming-required Nr. 17; without naming it is non-allocable. | `09-F20` |
| `09-E02` | A zero line remains in the audit protocol but is not printed. | `09-F21` |
| `09-E03` | A credit inherits its original type/key and remains a separately rounded printed line. | `09-F22` |
| `09-E04` | Labour above the allocable amount hard-blocks without partial output. | `09-F23` |
| `09-E05` | Non-allocable amount above invoice gross hard-blocks. | `09-F24` |
| `09-E06` | Missing consumption proposes area; no confirmation uses the zero-denominator result. | `09-F25` |
| `09-E07` | A new cost needs the clause and uses a day-exact numerator cap. | `09-F26` |
| `09-E08` | Full maintenance without detail proposes a warned 40% deduction. | `09-F27` |
| `09-E09` | Multi-year inspections are charged fully in the payment year. | `09-F28` |
| `09-E10` | Payment principle applies by default; heating remains service-period based. | `09-F29` |
| `09-E11` | A form clause cannot allocate an excluded residential cost. | `09-F30` |
| `09-E12` | Direct unit assignment overrides the default but retains time weighting. | `09-F31` |
| `09-E13` | Duplicate caretaker/specialist work warns and proposes reducing the caretaker line. | `09-F32` |
| `09-E14` | A mid-period catalogue change creates day-exact subpositions. | `09-F11` |

## 7. Fixture and source coverage

The oracle is data-only and imports no production module. Green arithmetic proves transcription,
not current engine behavior.

| Fixture | Rule covered | Oracle assertion |
| --- | --- | --- |
| `09-F01` | plain catalogue hit | 98,000 = 94,826 renters + 3,174 owner |
| `09-F02` | administration exclusion | 42,000 entirely block (b) |
| `09-F03` | repair exclusion | 68,000 entirely block (b) |
| `09-F04` | mixed lift invoice | 96,000 = 69,962 + 2,038 + 24,000 |
| `09-F05` | caretaker split | 120,000 = 87,085 + 2,915 + 30,000; labour 72,000 |
| `09-F06` | smoke-detector rent | 26,400 = 9,329 + 271 + 16,800; labour 6,000 |
| `09-F07` | contract key precedence | both key variants and their zero-sum delta |
| `09-F08` | mandatory measured consumption | 126,000 renters; explicit zero owner |
| `09-F09` | per-contract Nr. 17 naming | 8,400 = 5,196 + 3,204 |
| `09-F10` | cable cut-off | 43,200 entirely non-allocable |
| `09-F11` | leap-year version split | 43,200 = 21,482 + 21,718 over 182/366 days |
| `09-F12` | fibre cap | 20,700 = 17,490 + 510 + 2,700 |
| `09-F13` | new antenna installation | 3,600 entirely non-allocable |
| `09-F14` | ground-floor lift | default and contractual-exception variants |
| `09-F15` | inaccessible garden | 48,000 = 34,834 + 1,166 + 12,000; labour 30,000 |
| `09-F16` | chimney duplicate warning | 12,000 = 11,660 + 340; labour 9,500 |
| `09-F17` | § 35a chain | cost and labour both reconcile; exact half-up tie |
| `09-F18` | efficiency warning | amount remains 145,000 despite warning |
| `09-F19` | complete reference catalogue | Page 01 totals and corrected block (b) |
| `09-F20` | unknown type | unnamed and named variants |
| `09-F21` | zero line | zero protocol row plus unchanged 18,000 reference |
| `09-F22` | separate credit | -7,400 line and 54,600 net reconciliation |
| `09-F23` | invalid labour | hard block |
| `09-F24` | invalid split | hard block |
| `09-F25` | missing consumption | measured, confirmed-area and unconfirmed variants |
| `09-F26` | new cost | clause/no-clause variants and 184/365 cap |
| `09-F27` | full-maintenance proposal | 108,000 = 62,966 + 1,834 + 43,200 |
| `09-F28` | turn cost | full 18,000 in the payment year |
| `09-F29` | payment principle | 110,000 = 106,438 + 3,562 |
| `09-F30` | invalid form clause | 30,000 entirely non-allocable |
| `09-F31` | direct assignment | 6,000 = 5,490 + 510; labour 4,980 |
| `09-F32` | caretaker duplicate | 81,000 = 78,376 + 2,624; delta -9,000 |

### 7.1 Source-section trace

| Source | Destination | Disposition |
| --- | --- | --- |
| Page 02 metadata and § 1 | introduction and interface | current |
| Page 02 § 2.1–2.2 | § 2 | current provenance; no Page 02 CSV rows found |
| Page 02 § 2.3 (`09-K01`–`09-K11`) | §§ 1, 5 | current method, all `verify-before-production` |
| Page 02 § 3.1 | § 3 | current; audit adds nullable `afaKlasseVorschlag` |
| Page 02 § 3.2–3.3 | §§ 3.1–3.2 | complete 32 + 11 catalogue transcription |
| Page 02 § 3.4–3.5 | § 4 | current input contract |
| Page 02 § 4 (`R1`–`R8`) | § 5 | current binding order |
| Page 02 § 5 (`09-E01`–`09-E14`) | § 6 | complete |
| Page 02 § 6 (`09-F01`–`09-F32`) | § 7 and golden oracle | exact cent values; long examples moved to tests |
| Page 02 § 7 and Non-Goals addition | § 8 | current boundaries |
| Page 02 open point 1 | §§ 1, 7 | superseded by Antwort 03 § 2 and D1 `08-F21` |
| Page 02 open point 2 | `docs/03`/D1 | superseded; D1 reconciled the cited conflict |
| Page 02 open points 3–6 | §§ 1–2, 9 | unresolved and production-visible |
| Page 02 open point 7 | § 1 | unresolved: current CSV still has no `09-K` rows |
| `Rechtsstand-Register.csv` | §§ 1–2 | authoritative absence recorded; no flags invented |
| `Anlagen/Non-Goals V1`, Page 02 | § 8 | current |
| `Anlagen/README-for-Emir.md` | §§ 1, 3, 7 | arithmetic evidence and schema coupling retained |
| `FEEDBACK-to-Berkay-01b.md` § 7 | §§ 4, 9 | current: existing screens must not infer a key before implementation |
| `FRAGEN-an-Berkay-03.md` § 2 | §§ 1, 7 | superseded question |
| `Antwort-an-Emir_03.md` § 2 | §§ 1, 7 | current correction: block (b) = 100,800 cents |
| Other sections of the correspondence set | later assigned docs | no additional Page 02-owned rule |

## 8. Explicit non-goals and dependencies

V1 excludes mixed residential/commercial pre-deduction, VAT option and input-tax allocation,
unconfirmed automatic invoice-text classification, proof that a service was performed, landlord
self-performance valuation, unmeasured causation keys and a § 560 increase letter.

Page 01 owns denominators, day weighting, fictitious occupancy, renter rounding, owner residuals,
printed statement order, advances and deadlines. `docs/03` owns heating content. `docs/10` owns AfA
class values, `docs/11` owns Anlage-V/DATEV mappings, `docs/12` owns reusable date guards, and
`docs/13` owns clause text. OCR extraction may propose `kostenartId`, but the user must confirm it.

## 9. Implementation gap and approval gate

The shipped cost-entry and OCR review screens still use free text and deliberately derive no legal
allocation key from it. The NK engine still uses largest-remainder allocation. Neither behavior is
changed by this slice.

After Emir approves this specification, Slice C must implement the versioned rules-store catalogue,
reconcile the input model, switch NK renter lines to line-wise half-up plus the single owner
residual, prove all `09-Fxx` behavior against production code and keep every unresolved flag visible.
Until then this document and its green data oracle are specification evidence only.
