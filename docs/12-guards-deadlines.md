# Guards and deadlines — shared trigger, escalation and resolution contract

**Status:** complete D2 transcription; approved 21.08.2026

**Authoritative source:**
`berkay-work/Spec-Seiten/05 · Wächter Fristen 3a95fd42073181038246e579777508f9.md`

**Required companion sources:**

- `berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv`
- `berkay-work/Spec-Seiten/Anlagen/Non-Goals V1 3a95fd42073181a5be79cbe2ab8e3e12.md`
- `berkay-work/Spec-Seiten/Anlagen/README-for-Emir.md`
- the seven-file correspondence-retirement set listed in § 8

**Fixtures:** exactly `12-F01`–`12-F24` in
`packages/rules-store/tests/berkay_12_golden.py`

**Implementation status:** specification only. No guard engine, reminder scheduler, provider,
schema, API, UI, e-mail, push or PDF behavior is implemented by this slice.

This document owns Page 05's reusable date, money, trigger, warning, escalation and auto-resolution
rules. All product and warning copy is German. Code structure and identifiers are English. Money is
integer cents. A legal value or convention is selected from versioned rules data by its as-of date;
it is never hard-coded in an engine.

## 1. Source status, precedence and unresolved authority

The complete Page 05, its eighteen Page-05-specific Rechtsstand rows, six shared W1/W4 rows, the
Page 05 Non-Goals section and the arithmetic audit were reconciled. The arithmetic audit confirms
all 24 printed worked examples cent-exactly. It does not clear a legal or convention flag.

The CSV controls structured values, source, legal nature, flag and Rechtsstand. Page 05 controls
the expanded rule method, German output and worked examples. No item in the seven correspondence
files supplies a later Page-05-specific correction.

The following authority gaps remain explicit and block production use of their affected paths:

- W2 lists Kaltwasser 6 years, Warmwasser 5, WMZ 5, electric meters 8 and bellows gas meters 8.
  Page 05 and the register also record an unresolved conflict with “Zähler-Spec V1”, which says
  Warmwasser and WMZ are each 6 years. This document does not choose between 5 and 6 years.
- W2's 31 December expiry convention has no final statutory citation.
- W4's month-end UVI due date is a convention; year-round cadence versus heating-season-only is
  unresolved.
- W1/W5 calendar arithmetic includes an unresolved reading of the renter objection period: same
  numbered day after 12 months versus month end.
- W7 proportional VPI calculation is a convention; proportional versus difference-based treatment
  is still marked uncertain.
- The W3, W5, W6 and W7 tenancy-law rows remain `verify-before-production`, even where the
  arithmetic audit is green.
- The object flag for a tight housing market and the state regulation list behind it are not
  supplied. W5 cannot infer the 15% path from location.
- W5 with no comparative rent runs only in `KAPPUNG_ONLY`. It never confirms that an increase is
  lawful.

The register has no authority that resolves these points. They remain visible in the result and in
the rule version used. No production code may silently default across them.

## 2. Rechtsstand register

### 2.1 Eighteen Page-05-specific rows

All eighteen rows below are `verify-before-production`. `Gesetz` or `Verordnung` identifies the
legal nature of the underlying rule; it does not override the red flag or mean lawyer-approved.
A dash in Source means the authoritative CSV supplies no external URL.

| CSV row | Value or rule | Source and legal basis | Nature · Rechtsstand |
| ---: | --- | --- | --- |
| 116 | W5 comparative rent is a nullable manual input; no procurement | — · § 558a BGB; V1 manual input, no rent-index API | Konvention · 07/2026 |
| 117 | W4 UVI due at month end | `gesetze-im-internet.de/heizkostenv/__6a.html` · § 6a Abs. 1 Nr. 2 HeizkostenV; year-round versus heating season uncertain | Konvention · 10/2023 |
| 118 | W8 threshold 30 days; lost rent = target rent × days / 30 | — · no legal basis, product heuristic | Heuristik · 07/2026 |
| 119 | W5: rent unchanged 15 months; declaration after 1 year; comparative-rent ceiling | `gesetze-im-internet.de/bgb/__558.html` · § 558 Abs. 1 BGB | Gesetz · 05/2026 |
| 120 | W5 tight market is an object flag from a state regulation; list absent | — · § 558 Abs. 3 S. 2–3 BGB with LandesVO | Konvention · 07/2026 |
| 121 | W3: 3a = two consecutive dates and arrears > one monthly rent; 3b = >2 dates and arrears ≥ two monthly rents | `gesetze-im-internet.de/bgb/__543.html` · § 543 Abs. 2 S. 1 Nr. 3 a/b BGB | Gesetz · 05/2026 |
| 122 | W5 cap: +20% in 3 years, or 15% in tight market; § 559 and operating-cost increases excluded | `gesetze-im-internet.de/bgb/__558.html` · § 558 Abs. 3 BGB | Gesetz · 05/2026 |
| 123 | W5 consent through end of second calendar month; effective from start of third; action period +3 months | `gesetze-im-internet.de/bgb/__558b.html` · § 558b Abs. 1–2 BGB | Gesetz · 05/2026 |
| 124 | W3 material arrears must strictly exceed one monthly rent | `gesetze-im-internet.de/bgb/__569.html` · § 569 Abs. 3 Nr. 1 BGB | Gesetz · 05/2026 |
| 125 | W3 monthly-rent basis is gross warm rent including advances | — · product convention | Konvention · 07/2026 |
| 126 | W1/W5 month addition D1/D4/D5, including uncertain D4 objection-period reading | `gesetze-im-internet.de/bgb/__188.html` · §§ 187, 188 BGB | Konvention · 07/2026 |
| 127 | W3 grace-period payment heals the extraordinary termination | `gesetze-im-internet.de/bgb/__569.html` · § 569 Abs. 3 Nr. 2 BGB | Gesetz · 05/2026 |
| 128 | W2 calibration validity ends on 31 December of the expiry year | — · no secure citation; usual calibration-law convention | Konvention · 07/2026 |
| 129 | W2 years: cold water 6; warm water 5; heat meter 5; electric 8; bellows gas 8; conflict with 6-year meter spec | `gesetze-im-internet.de/messev/` · MessEG § 34 / MessEV, exact annex/section uncertain | Verordnung · 07/2026 |
| 130 | W6 amount stated per step; each step at least one year unchanged; §§ 558/559 blocked | `gesetze-im-internet.de/bgb/__557a.html` · § 557a Abs. 1–2 BGB | Gesetz · 05/2026 |
| 131 | W7 proportional VPI calculation; source snapshot and basis year stored; proportional method uncertain | `www-genesis.destatis.de` · GENESIS 61111; calculation convention | Konvention · 07/2026 |
| 132 | W5/W7 money basis is net cold rent | — · §§ 558, 557b BGB | Konvention · 07/2026 |
| 133 | W7 uses Federal Statistical Office VPI; at least one year unchanged; declaration in text form | `gesetze-im-internet.de/bgb/__557b.html` · § 557b Abs. 1–3 BGB | Gesetz · 05/2026 |

### 2.2 Six shared W1/W4 rows

These rows are also assigned to Page 05 but originated as shared Page 01/01b authority. Their flags
remain unchanged.

| CSV row | Value or rule | Source and legal basis | Flag · nature · Rechtsstand |
| ---: | --- | --- | --- |
| 4 | UVI monthly from 01.01.2022 only with remote-readable equipment | `gesetze-im-internet.de/heizkostenv/__6a.html` · § 6a Abs. 1 Nr. 2 | `geprüft` · Verordnung · 07/2026 |
| 26 | operating-cost statement within 12 months; late additional claim excluded unless not attributable | `gesetze-im-internet.de/bgb/__556.html` · § 556 Abs. 3 S. 2–3 | `geprüft` · Gesetz · 07/2026 |
| 30 | remote-readability retrofit by 31.12.2026 | `gesetze-im-internet.de/heizkostenv/BJNR002610981.html` · § 5 Abs. 2 | `geprüft` · Verordnung · 07/2026 |
| 41 | renter objection period 12 months from statement receipt | `gesetze-im-internet.de/bgb/__556.html` · § 556 Abs. 3 S. 5–6 | `geprüft` · Gesetz · 07/2026 |
| 43 | 3% reduction right for missing/incomplete § 6a information | `gesetze-im-internet.de/heizkostenv/__12.html` · § 12 Abs. 1 S. 3 with § 6a | `verify-before-production` · Verordnung · 07/2026 |
| 44 | residential evidence may be made available electronically; commercial exception noted | `gesetze-im-internet.de/bgb/__556.html` · § 556 Abs. 4 | `geprüft` · Gesetz · 07/2026 |

The W4 guard does not apply the 3% reduction. It warns about the risk. Automatic application of a
renter's reduction right is an explicit non-goal.

## 3. Shared guard result contract

Every guard takes `today` as a day-exact system date and returns the source input identity, rule
version/as-of date, computed boundary or threshold, active state, German warning copy, escalation
stage and auto-resolution event. A result must preserve any uncertainty, conflict or production
block that affected it.

Date steps use calendar days/months and no rounding. `add_months(date, n)` keeps the numbered day;
if it does not exist in the target month, use that month's last day. A deadline expires at 24:00 on
the deadline date.

Money steps use integer cents. Percentage and index products round commercially to a whole cent
(`ROUND_HALF_UP`). Index values use one decimal place. Legal thresholds using “übersteigt” are
strict. The W3 basis is gross warm rent; the W5/W6/W7 basis is net cold rent.

Warnings are tools, not advice. They use “rechtskonform” and the approved no-legal-advice
disclaimer. A guard may warn, schedule or auto-resolve only the event specified below. It never
issues a termination, increase declaration or other legally binding statement.

## 4. Inputs and provider boundaries

All guards receive `today`. Their specific normalized inputs are:

| Guard | Required inputs |
| --- | --- |
| W1 | statement `period_end`; nullable `statement_delivered_on` |
| W2 | nullable `calibration_date`; medium (`cold_water`, `warm_water`, `heat_meter`, `electricity`, `gas`); versioned years by medium |
| W3 | `gross_monthly_rent_cents`; due entries `(due_date, amount_cents)[]`; payments `(date, amount_cents)[]` |
| W4 | `remote_readable`; nullable `last_uvi_sent_on`; first `start_month`; retrofit date 31.12.2026 |
| W5 | `net_cold_rent_cents`; `base_rent_3y_cents`; `last_increase_effective_on`; nullable `comparative_rent_cents`; `tight_market`; nullable `request_received_on` |
| W6 | ordered schedule `(step_effective_on, amount_cents)[]`; current target rent |
| W7 | net cold rent; base index value, basis year, reference month, provisional/final status, source and captured-at date; new VPI snapshot; last adjustment date |
| W8 | last tenancy end per unit; active-tenancy flag; target rent cents |

The Destatis provider is a V1 external edge and must be behind an adapter. It returns the reference
month, one-decimal value, basis year, provisional/final status and publication date from GENESIS
table 61111. The stored base index is a snapshot and is never refreshed silently. A basis-year
mismatch blocks calculation and asks for rebasing; this spec does not perform rebasing.

Comparative rent is a nullable manual V1 input. A future paid market-data provider may implement the
same boundary, but no provider or free nationwide rent-index lookup is promised here.

## 5. Guard rules, warnings, escalation and auto-resolution

### 5.1 W1 — § 556 operating-cost statement deadline

```text
landlord_deadline = add_months(period_end, 12)
days_until_deadline = landlord_deadline - today

90 or 30 days       -> reminder
0 days              -> last day
<0 and not delivered -> EXPIRED

if delivered:
  renter_objection_deadline = same_numbered_day(delivered_on, +12 months)
```

W1 is mandatory. Under the B2 convention, it assumes the landlord is responsible for lateness and
warns sharply; it does not assess the statutory exception.

- 30-day warning: “Noch 30 Tage: Die Betriebskostenabrechnung {Jahr} muss dem Mieter bis
  {landlord_deadline} zugehen. Danach sind Nachforderungen in der Regel ausgeschlossen (§ 556 Abs.
  3 BGB).”
- expired warning: “Frist abgelaufen: Für {Jahr} ist eine Nachforderung in der Regel
  ausgeschlossen. Ein Guthaben müssen Sie dem Mieter weiterhin auszahlen.”
- escalation: in-app at 90 days; in-app + e-mail at 30; e-mail + push at 0/expired.
- auto-resolution: `statement_delivered_on <= landlord_deadline`; event `statement_sent`.

### 5.2 W2 — meter calibration expiry

```text
if calibration_date is null:
  warning = "Eichdatum erfassen"
  no expiry calculation
else:
  valid_until = 31.12.(year(calibration_date) + years_for_medium)
  months_until_expiry = month_difference(valid_until, today)
  <= 6 -> notice
  < 0  -> exceeded, non-blocking
```

The years table is versioned rules data and remains production-blocked by the 5/6-year conflict.
The exact warning is: “Der {medium}-Zähler in {WE} ist ab {valid_until} nicht mehr geeicht. Werte
aus ungeeichten Zählern können bei der Abrechnung angreifbar sein — bitte Austausch/Nacheichung
veranlassen.”

Escalation is in-app at six months, in-app + e-mail in the expiry month, and e-mail after expiry.
It does not block a statement. A new calibration date resolves it; event `meter_replaced`.

### 5.3 W3 — § 543 payment arrears

```text
arrears_cents = sum(due open amounts) - sum(payments)
consecutive_open_dates = consecutive due dates with remaining balance > 0
threshold_3a = gross_monthly_rent_cents
threshold_3b = 2 * gross_monthly_rent_cents

arrears > 0                                      -> info
consecutive_open_dates >= 2 and arrears > 3a     -> stage 3a
consecutive_open_dates > 2 and arrears >= 3b     -> stage 3b
```

The comparisons are exact and deliberately different: 3a is strictly greater than one monthly
rent; 3b permits equality at two monthly rents but requires more than two dates.

The 3a warning is: “Der Mietrückstand von {Mieter} beträgt {arrears} € und übersteigt eine
Monatsmiete bei zwei aufeinanderfolgenden offenen Terminen — die Schwelle für eine fristlose
Kündigung wegen Zahlungsverzugs (§ 543 Abs. 2 Nr. 3a BGB) ist erreicht. Hinweis: Eine
Schonfristzahlung (§ 569 Abs. 3 Nr. 2 BGB) kann die Kündigung heilen.”

Escalation is in-app for any positive arrears, e-mail at 3a and push at 3b. A payment can lower the
stage. `12-F10` is specifically a 3b-to-3a downgrade: 235,000 − 100,000 = 135,000 cents remains
above the 85,000-cent 3a threshold. It is not a complete resolution. Event `payment_received`.

### 5.4 W4 — monthly UVI and remote-readability retrofit

```text
if not remote_readable and today <= 31.12.2026:
  show retrofit notice

if remote_readable:
  due_on = month_end(add_months(last_uvi_sent_on ?? start_month, 1))
  overdue = today >= due_on and no UVI in the current month
```

W4 applies to each renter in a remotely readable building. It is inactive for UVI when equipment
is not remote-readable; only the retrofit notice remains. The due date and cadence retain the D3
uncertainty described in § 1.

The warning is: “Für {WE} (fernablesbare Zähler) steht die monatliche Verbrauchsinformation für
{Monat} noch aus. § 6a HeizkostenV verpflichtet zur monatlichen Information des Mieters.”

Escalation is in-app when due and e-mail when overdue. Generating/sending that month's UVI resolves
the occurrence and advances the next due month; event `uvi_sent`. `docs/16` owns UVI calculation,
content, delivery document, DWD inputs and comparison rules; W4 owns only cadence and guard state.

### 5.5 W5 — § 558 comparative-rent increase

```text
earliest_declaration = add_months(last_increase_effective_on, 12)
earliest_effective   = add_months(last_increase_effective_on, 15)
cap_rate             = tight_market ? 0.15 : 0.20
cap_ceiling_cents    = half_up(base_rent_3y_cents * (1 + cap_rate))

if comparative_rent_cents is null:
  maximum_new_rent_cents = cap_ceiling_cents
  mode = KAPPUNG_ONLY
else:
  maximum_new_rent_cents = min(cap_ceiling_cents, comparative_rent_cents)
  mode = FULL_CHECK

maximum_increase_cents = max(0, maximum_new_rent_cents - net_cold_rent_cents)
active = today >= earliest_declaration and maximum_increase_cents > 0

if request_received_on:
  consent_deadline = month_end(add_months(request_received_on, 2))
  effective_on     = first_day(add_months(request_received_on, 3))
  action_deadline  = add_months(consent_deadline, 3)
```

The three-year base excludes § 559 modernization and operating-cost increases. The tight-market
flag comes from a state regulation outside this spec. W5 must not infer it.

- full-check warning: “Sie können die Miete für {WE} um bis zu {maximum_increase} € auf
  {maximum_new_rent} € erhöhen (§ 558 BGB). Begrenzt durch {Kappungsgrenze / ortsübliche
  Vergleichsmiete}.”
- cap-only warning: “Die Kappungsgrenze erlaubt für {WE} bis zu {maximum_new_rent} €
  (+{maximum_increase} €). Prüfen Sie zusätzlich selbst die ortsübliche Vergleichsmiete (z. B.
  örtlicher Mietspiegel) — die Erhöhung nach § 558 darf sie nicht übersteigen. Hinweis: Nach einer
  Modernisierung gilt § 559 als eigener Weg (hier nicht berechnet).”

Escalation is an in-app opportunity; after a request is sent, show consent/action deadlines in-app
and e-mail the action deadline. Recorded consent adjusts the target rent from `effective_on`; event
`rent_increase_consented`.

### 5.6 W6 — § 557a graduated rent

```text
active_step = latest schedule step whose effective date <= today
adjustment_due = active_step.amount_cents != current_target_rent_cents
each consecutive step interval must be >= 12 months
```

An interval below 12 months is an input validation error. The warning is “Neue Mietstaffel für
{WE} ab {step_effective_on}: {amount} €.” Escalation is in-app. Updating the target rent to the
active step auto-resolves it.

### 5.7 W7 — § 557b index rent

```text
require base_index_basis_year == new_index_basis_year
factor = new_index / base_index
new_rent_cents = half_up(net_cold_rent_cents * factor)
increase_cents = new_rent_cents - net_cold_rent_cents

active = elapsed_months >= 12
         and new_index > base_index
         and basis years match
```

A basis-year mismatch produces no money result and warns “Index umrechnen (Umbasierung)”. Deflation
or equality produces no increase. The source snapshot retains value, basis year, reference month,
status, source and capture time.

The warning is: “VPI von {base_index} auf {new_index} (+{delta_percent} %) → mögliche neue Miete
{new_rent} € (+{increase} €).” Escalation is in-app. A sent declaration plus effective adjustment
resolves it; event `index_adjustment_effective`.

### 5.8 W8 — vacancy

```text
if active_tenancy:
  inactive
else:
  vacancy_days = today - last_tenancy_ended_on
  lost_rent_cents = half_up(target_rent_cents * vacancy_days / 30)
  active = vacancy_days > 30
```

Counting starts on the day after tenancy end. The warning is: “{WE} steht seit {vacancy_days} Tagen
leer — ca. {lost_rent} € entgangene Miete.” Escalation is in-app. A new active tenancy resolves it.
The amount is product framing, not a legal loss calculation.

## 6. Edge-case contract

| Edge | Required result | Fixture |
| --- | --- | --- |
| E1 | 29 February plus 12 months clips to 28 February in a non-leap year | `12-F02` |
| E2 | W1 expired without delivery shows exclusion and continuing-credit warning | `12-F03` |
| E3 | on-time delivery resolves W1 and starts the objection deadline | `12-F04` |
| E4 | missing calibration date produces a special warning and no calculation | `12-F06` |
| E5 | W2 5-year/6-year meter conflict remains visible and production-blocking | `12-F05` |
| E6 | arrears exactly one monthly rent do not trigger 3a | `12-F08` |
| E7 | two dates at two monthly rents trigger 3a but not 3b | `12-F07` |
| E8 | a grace-period payment can downgrade the stage without fully resolving it | `12-F10` |
| E9 | equipment not remote-readable disables UVI and shows retrofit notice | `12-F12` |
| E10 | no previous UVI uses the first start month | `12-F13` |
| E11 | W5 declaration/effective waiting periods not reached remain inactive | `12-F16` |
| E12 | cap versus comparative-rent ceiling uses the lower result | `12-F14`, `12-F15` |
| E13 | tight market uses 15%, normal market 20%, only from the explicit flag | `12-F14`, `12-F15` |
| E14 | W6 schedule interval below 12 months is invalid | `12-F19` |
| E15 | W7 below 12 months since the last adjustment is inactive | `12-F21` |
| E16 | W7 deflation/equality produces no increase | rule in § 5.7; no separate printed fixture |
| E17 | W7 basis-year mismatch blocks with rebasing warning | rule in § 5.7; no separate printed fixture |
| E18 | missing comparative rent uses `KAPPUNG_ONLY` without legality confirmation | `12-F23` |
| E19 | current rent at/above the ceiling clamps the increase to zero | `12-F24` |
| E20 | active tenancy disables W8 | `12-F22` variant |

## 7. Exact fixture coverage

The oracle is data-only and imports no production module. Green checks prove transcription and
source arithmetic, not current application behavior.

| Fixture | Required oracle result |
| --- | --- |
| `12-F01` | 31.12.2026 deadline; 30 days; in-app + e-mail |
| `12-F02` | leap-day clip to 28.02.2025; 44 days; no stage |
| `12-F03` | −15 days; expired; renter credit still payable |
| `12-F04` | delivery 20.12.2026 resolves; objection deadline 20.12.2027 |
| `12-F05` | warm-water 5-year path expires 31.12.2025; 4 months; conflicting 6-year path retained |
| `12-F06` | no calibration date; no calculation; “Eichdatum erfassen” |
| `12-F07` | 170,000 cents, two dates: 3a true, 3b false |
| `12-F08` | exactly 85,000 cents: strict 3a false |
| `12-F09` | 255,000 − 20,000 = 235,000; three dates; 3b true |
| `12-F10` | 235,000 − 100,000 = 135,000; downgrade 3b → 3a, not resolution |
| `12-F11` | last UVI 31.05.2026; due 30.06.2026; overdue on 05.07.2026 |
| `12-F12` | non-remote-readable: UVI inactive, retrofit notice through 31.12.2026 |
| `12-F13` | first start month 05/2026; due 30.06.2026; not due on 03.06.2026 |
| `12-F14` | normal 20% cap: 96,000 maximum, 16,000 increase |
| `12-F15` | tight 15% cap 92,000; comparative rent limits to 88,000; 8,000 increase |
| `12-F16` | declaration 01.03.2026; effect 01.06.2026; inactive on 01.01.2026 |
| `12-F17` | consent 30.06.2026; effect 01.07.2026; action 30.09.2026 |
| `12-F18` | active 01.01.2026 step is 95,000; current target 90,000; adjustment due |
| `12-F19` | 01.06.2025 to 01.03.2026 = 9 months; invalid |
| `12-F20` | 122.3 / 118.0; 82,915.25… rounds to 82,915; increase 2,915 |
| `12-F21` | six months since adjustment; inactive |
| `12-F22` | 50 vacancy days; 90,000 × 50 / 30 = 150,000 cents; active |
| `12-F23` | comparative rent null; 96,000 cap; 16,000 increase; `KAPPUNG_ONLY` |
| `12-F24` | current 95,000 above 90,000 ceiling; increase clamps to zero |

## 8. Source and correspondence ledger

| Source | Destination | Disposition |
| --- | --- | --- |
| Page 05 metadata and § 1 | introduction and §§ 1, 3 | current scope: W1–W8, V1, blocks M9 |
| Page 05 § 2 | §§ 1–2 | complete legal basis, conventions, flags and meter conflict |
| Page 05 § 3 | § 4 | complete normalized inputs and provider boundaries |
| Page 05 § 4, W1–W8 | §§ 3–5 | formula order, money/date rules, German copy, escalation and auto-resolution complete |
| Page 05 § 5, E1–E20 | § 6 | all mapped; E16/E17 are rule-only variants because the Page prints no separate fixture |
| Page 05 § 6, `12-F01…F24` | § 7 and golden oracle | exact source IDs and results; long arithmetic moved to tests |
| Page 05 § 7 | § 9 | complete out-of-scope transcription |
| CSV rows 116–133 | § 2.1 and oracle metadata | all 18 Page-specific rows; every flag remains `verify-before-production` |
| shared CSV rows 4, 26, 30, 41, 43, 44 | § 2.2 and oracle metadata | all six shared W1/W4 rows; flags unchanged |
| Non-Goals V1, Page 05 | § 9 and oracle metadata | all ten exclusions preserved |
| `Anlagen/README-for-Emir.md` | §§ 1, 7 | 24-case exact arithmetic evidence retained; does not clear red flags |
| `FEEDBACK-to-Berkay-01b.md` | other assigned docs | no Page-05-owned correction found; retained for D3 ledger |
| `FRAGEN-an-Berkay-02.md` | `docs/03`/`docs/16` | UVI content questions are transcribed in the D2 draft, not W4 cadence; no Page-05 correction |
| `FRAGEN-an-Berkay-03.md` | other assigned docs | no Page-05-owned correction found; retained for D3 ledger |
| `Antwort-an-Emir_01b-Uebergabe.md` | `docs/03`/`docs/16` | UVI comparison/fallback content transcribed in the D2 draft, not Page-05 cadence |
| `Antwort-an-Emir_02.md` | `docs/03`/`docs/16` | UVI comparison/licence content transcribed in the D2 draft, not Page-05 cadence |
| `Antwort-an-Emir_03.md` | other assigned docs | no Page-05-owned correction found; retained for D3 ledger |
| `08_BankMatching_F03_Patch.md` | `docs/15` | no Page-05-owned correction; retained for D3 ledger |

The ledger is complete for Page 05. The files remain present until the D3 retirement gate.

## 9. Explicit non-goals and dependencies

Page 05 excludes all ten items listed by both the Page and Non-Goals V1:

1. sample letters or text blocks for reminders, termination, objections or rent increases;
2. actual e-mail or push delivery infrastructure;
3. assessment of whether a late § 556 event was outside the landlord's responsibility;
4. ordinary termination under § 573;
5. § 558a evidence generation or procurement of a local rent index;
6. § 559 modernization increase and § 556d rent-brake calculators;
7. state regulation lists for tight housing markets or smoke-detector duties;
8. VPI rebasing conversion;
9. limitation periods for additional claims under § 195 BGB; and
10. legal advice or legally binding declarations.

`docs/16` depends on W4's cadence but owns UVI calculation, content and document isolation. M6's
payment ledger supplies W3 payment events and may consume Page-05 costs/interest under the approved
bank contract. `docs/13` owns future approved letter/clause content. M9 owns actual reminders,
e-mail, push and checklists. All external providers stay behind adapters.

## 10. Approval and implementation boundary

The exact 24-case fixture surface, all Page sections, all eighteen Page-specific register rows, six
shared rows, ten non-goals and seven correspondence files are mapped. The data-only checks may prove
coverage and arithmetic, but they do not approve legal rules, resolve authority gaps or demonstrate
production behavior.

This slice changes documentation and tests only. It makes no production, schema, migration, API,
engine, adapter, UI or PDF change. Implementation remains paused until the documentation program
and Emir's later implementation authorization permit it.
