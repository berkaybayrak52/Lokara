# 01b · Heizkosten- & CO₂-Verteilung

Blockiert: M1 · Pitch-Demo 06.08.
Emir-Prio: 1
Fixtures: 01b-F01 … 01b-F31
Nr: 01b
Optional: No
Phase: 1
Rechtsstand-Einträge: siehe [kanonisches Rechtsstand-Register](../Rechtsstand-Register/Rechtsstand-Register.csv)
Status: Fertig
Termin: 26. Juli 2026
Ziel-Datei: docs/03
Zuletzt bearbeitet von: 13. August 2026 17:13

> **Ziel-Datei:** NEU — die Roadmap sieht für diese Seite keine `docs/`-Nummer vor. Vorschlag `docs/13-heating-co2-allocation.md`; die endgültige Nummer vergibt Emir beim Transkribieren. Die Fixture-IDs sind deshalb auf die **Seitennummer** gezogen (`01b-Fxx`), nicht auf eine docs-Nummer.
> 

> **Phase / Termin:** Phase 1 · So 26.07.2026
> 

> **Fixtures:** `01b-F01 … 01b-F31`
> 

> **Braucht vorher:** `docs/03` (Umlageschlüssel-Mathematik, m²-Tage) · Seite 01 (Dokument-Layout)
> 

> **Blockiert:** M1 · Pitch-Demo 06.08.
> 

> **Schnittstelle:** Diese Seite liefert **einen €-Betrag je Mietverhältnis**. Er füllt das Feld `heizkostenMessdienstCent` der NK-Engine (Seite 01, § 3.2). Kein zweiter Kostenblock, kein Doppelabzug.
> 

> **Sprache:** Inhalt Englisch (Emir transkribiert 1:1). Deutsche Abschnittsüberschriften sind Berkays Gerüst und bleiben stehen. Rechtsbegriffe und alle Texte, die auf dem PDF landen, bleiben Deutsch.
> 

---

## 1. Zweck

Turns the fuel and operating invoices of **one heating plant** into a per-tenancy heating and hot-water amount that satisfies the HeizkostenV, after the landlord's CO₂ share has been removed under the CO2KostAufG. Two entry paths lead to the same output field: the **self-billing path** (Lokara computes, sections 4.1–4.6) and the **MDL path** (a Messdienst statement is ingested, section 4.7). This page owns the heating math; the *document* that prints it is Seite 01.

---

## 2. Rechtsgrundlage

| Rule the engine must satisfy | Norm | Rechtsstand | Rechtsnatur |
| --- | --- | --- | --- |
| Distributable operating costs of the plant (fuel, Betriebsstrom, Wartung, Reinigung, Messung, Ausstattung) | § 7 Abs. 2 HeizkostenV | 07/2026 (Fassung 16.10.2023) | Verordnung |
| 50–70 % of heating costs by consumption; remainder by area | § 7 Abs. 1 HeizkostenV | 07/2026 (Fassung 16.10.2023) | Verordnung |
| Same 50–70 % rule for hot-water costs | § 8 Abs. 1 HeizkostenV | 07/2026 (Fassung 16.10.2023) | Verordnung |
| Connected plants: Q measured by Wärmezähler; substitute equation `Q = 2,5 · V · (tw − 10)` [kWh/a] | § 9 Abs. 2 HeizkostenV | 07/2026 (verifiziert 26.07.2026 am Normtext) | Verordnung |
| Hot water not measurable: `Q = 32 · A_Wohn` [kWh/a] | § 9 Abs. 3 HeizkostenV | 07/2026 (verifiziert 26.07.2026) | Verordnung |
| Device failure → estimate from prior period or comparable rooms | § 9a Abs. 1 HeizkostenV | 07/2026 (verifiziert 26.07.2026) | Verordnung |
| Affected area > 25 % → distribute **only** by the remainder standard (§ 7 Abs. 1 S. 5, § 8 Abs. 1) | § 9a Abs. 2 HeizkostenV | 07/2026 (verifiziert 26.07.2026) | Verordnung |
| Tenant change: interim reading mandatory; remainder costs for heat by Gradtagszahlen **or** time-proportional, hot water time-proportional; no valid reading → everything by the remainder standard | § 9b Abs. 1–3 HeizkostenV | 07/2026 (verifiziert 26.07.2026) | Verordnung |
| Remote-readable devices; retrofit deadline **31.12.2026** | § 5 Abs. 2 HeizkostenV | 07/2026 | Verordnung |
| UVI — only where remote-readable devices exist; monthly from 01.01.2022 | § 6a Abs. 1 HeizkostenV | 07/2026 (verifiziert 26.07.2026 am Normtext) | Verordnung → Seite 05 |
| UVI content: consumption in kWh · comparison with previous month and same month prior year **(„soweit diese Daten erhoben worden sind")** · comparison with a normierter oder durch Vergleichstests ermittelter Durchschnittsnutzer **(ohne Vorbehalt, ohne Online-Verweis-Option)** | § 6a Abs. 2 Nr. 1–3 HeizkostenV | 07/2026 (verifiziert 26.07.2026) | Verordnung → Seite 05 |
| Information **with the annual statement** — trigger is not „fernablesbar" but „Abrechnung beruht auf Verbrauch oder HKV-Ablesewerten": Energieträgeranteil + THG + Primärenergiefaktor (Fernwärme) · Steuern/Abgaben/Zölle · Entgelte für Ausstattung, Eichung, Ablesung, Abrechnung · Kontaktdaten Verbraucherorganisationen · Streitbeilegungshinweis · Durchschnittsnutzer-Vergleich (**bei elektronischen Abrechnungen online zulässig, mit Verweis in der Abrechnung**) · witterungsbereinigter Vorjahresvergleich **in grafischer Form** | § 6a Abs. 3 S. 1 Nr. 1–5 HeizkostenV | 07/2026 (verifiziert 26.07.2026 am Normtext) | Verordnung → Layout Seite 01 |
| Der Vergleich umfasst Wärme **und** Warmwasser; witterungsbereinigt wird **nur der Wärmeverbrauch** | § 6a Abs. 3 S. 2–3 HeizkostenV | 07/2026 (verifiziert 26.07.2026) | Verordnung |
| Vermutungswirkung: anerkannte Regeln der Technik gelten als eingehalten bei Verwendung der von BMWi und BMI gemeinsam im Bundesanzeiger bekanntgemachten Vereinfachungen | § 6a Abs. 3 S. 4 HeizkostenV | 07/2026 | Verordnung — **Bekanntmachung nicht gefunden, siehe Offene Fragen** |
| Nicht verbrauchsbasierte Abrechnungen brauchen nur Abs. 3 Nr. 2 und 3 | § 6a Abs. 5 HeizkostenV | 07/2026 | Verordnung |
| Kürzungsrecht 15 % bei nicht verbrauchsabhängiger Abrechnung | § 12 Abs. 1 S. 1 HeizkostenV | 07/2026 | Verordnung |
| Kürzungsrecht 3 % ohne fernablesbare Ausstattung (§ 5 Abs. 2/3) | § 12 Abs. 1 S. 2 HeizkostenV | 07/2026 (Normtext verifiziert 27.07.2026) | Verordnung |
| Kürzungsrecht 3 % bei fehlender oder unvollständiger § 6a-Information (UVI und Abrechnungs-Informationsblock) | § 12 Abs. 1 S. 3 i. V. m. § 6a HeizkostenV | 07/2026 (Normtext verifiziert 27.07.2026) | Verordnung — Rechtsfolge („dasselbe") aus S. 2, Tatbestand aus S. 3 |
| CO₂-Kostenausweis durch den Brennstofflieferanten | § 3 CO2KostAufG | 07/2026 | Gesetz |
| CO₂-Aufteilung Wohngebäude nach 10-Stufenmodell | §§ 5–7 + Anlage CO2KostAufG | 07/2026 | Gesetz |
| Pflichtangaben in der Heizkostenabrechnung: Mieteranteil an den CO₂-Kosten, Einstufung des Gebäudes, Berechnungsgrundlagen | § 7 Abs. 3 CO2KostAufG | 07/2026 | Gesetz |
| Kürzungsrecht 3 % der Heizkosten bei fehlender Pflichtangabe — verschuldensunabhängig | § 7 Abs. 4 CO2KostAufG | 07/2026 | Gesetz |
| Nichtwohngebäude: 50/50 | § 8 CO2KostAufG | 07/2026 | Gesetz |
| Denkmal-/Milieuschutz: Vermieteranteil halbiert (Abs. 1) bzw. entfällt (Abs. 2); Nachweispflicht gegenüber dem Mieter (Abs. 3) | § 9 CO2KostAufG | 07/2026 | Gesetz |
| BEHG-Preis: 2025 Festpreis 55 €/t · 2026 Versteigerung im Korridor 55–65 €/t, Verkaufsphase 68 €, Nachkauf 2027 70 € | § 10 BEHG | 07/2026 | Gesetz |
| Vermieter trägt Darlegungs- und Beweislast für die richtige **Erfassung**; Mieter darf ohne besonderes Interesse in die Ablesebelege **auch der anderen Einheiten** Einsicht nehmen; bis dahin keine Zahlungspflicht | BGH VIII ZR 189/17 v. 07.02.2018 | 07/2026 (verifiziert 26.07.2026) | Rechtsprechung |
| Witterungsbereinigung des Heizenergieverbrauchs bei Verbrauchsausweisen — Instrument: DWD-Klimafaktoren | § 82 Abs. 3–5 GEG | 07/2026 | Gesetz (analoge Anwendung) |

### Conventions — not law, `verify-before-production`

| ID | Konvention | Warum sie eine Konvention ist |
| --- | --- | --- |
| K1 | Grundkostenanteil **30 %**, konfigurierbar 30–50 % | Das Gesetz erlaubt 50–70 % verbrauchsabhängig (§ 7 Abs. 1). 30/70 ist unsere Vorbelegung. |
| K2 | Grundkosten werden nach **m²-Tagen** verteilt (zeitanteilig) | § 9b Abs. 2 lässt für Wärme-Restkosten Gradtagszahlen **oder** zeitanteilig zu. Wir wählen zeitanteilig, weil die NK-Engine denselben Nenner benutzt. |
| K3 | **Gradtagszahltabelle (VDI, ‰/Monat):** Jan 170 · Feb 150 · Mär 130 · Apr 80 · Mai 40 · Jun 13,3 · Jul 13,3 · Aug 13,4 · Sep 30 · Okt 80 · Nov 120 · Dez 160 (Σ 1000). Gespeichert in Zehntelpromille (Σ = 10000): 1700·1500·1300·800·400·133·133·134·300·800·1200·1600. Quelle: VDI 2067 Bl. 1, Ausgabe 12/1983, Tab. 22. Korrigiert 27.07.2026 | § 9b Abs. 2 verlangt „Gradtagszahlen nach anerkannten Regeln der Technik" — die konkrete Tabelle steht nicht in der Verordnung. DB-Tabelle, nicht Code. |
| K4 | **Fallback-Emissionsfaktoren** (nur wenn der Lieferant § 3 CO2KostAufG verletzt): Erdgas 0,201 · Heizöl 0,266 · Flüssiggas 0,236 kg CO₂/kWh (alle drei aus Anlage 2 Teil 4 EBeV 2030; Flüssiggas korrigiert 27.07.2026 von 0,234) | Ersatzwerte, keine Rechtsnorm. |
| K5 | `tw` Default **60 °C** in der Ersatzgleichung des § 9 Abs. 2 | Die Norm sagt „gemessene oder geschätzte mittlere Temperatur". |
| K6 | Plausibilitätsband **5–70 kg CO₂/m²/a** | Heuristik. Löst eine Warnung aus, nie eine Blockade. |
| K7 | Öl-Bewertung mit **gewichtetem Durchschnittspreis** aus Anfangsbestand + Zukäufen; Heizwert 10 kWh/l | Die Verordnung sagt nur „verbrauchte Brennstoffe", nicht welches Bewertungsverfahren. |
| K8 | Rechnungszeiträume werden dem Abrechnungszeitraum **taggenau linear** zugeordnet | Abgrenzungsverfahren ist nicht normiert. |
| K9 | **Verteilungsrest** (Rundungsdifferenz) verbleibt beim Eigentümer, zusammen mit dem Leerstandsanteil | Folgt dem Residuum-Prinzip der Seite 01 (D12). |
| K10 | **Geräteliste wird auf der Mieterausfertigung gedruckt** (Gerätenummer, Raum, Stand alt/neu, Bewertungsfaktor, Einheiten) | Keine Norm verlangt den Einzelausweis je Heizkörper. Wir drucken ihn, weil BGH VIII ZR 189/17 die Beweislast beim Vermieter verortet und der Ausweis Einwendungen vorwegnimmt. |
| K11 | Geräteeinheiten auf **1 Nachkommastelle** gerundet; die Wohnungssumme ist die Summe der gerundeten Gerätewerte | Rechenkonvention. |
| K12 | Witterungsbereinigung mit den **DWD-Klimafaktoren** (CDC Open Data, PLZ-genau, gleitende 12-Monats-Zeiträume, Referenzort Potsdam TRY 2011) | § 6a Abs. 3 S. 3 verlangt „anerkannte Regeln der Technik", nennt aber kein Verfahren. DWD ist das Instrument des GEG-Umfelds und damit die stärkste verfügbare Wahl — bis die Bekanntmachung nach S. 4 geprüft ist. Import-Spec: `Lokara/Klimafaktoren/DWD-Klimafaktoren-Import-Spec.md`. Lizenz GeoNutzV, Quellenangabe „Quelle: Deutscher Wetterdienst" ist Pflicht. |
| K13 | Durchschnittsnutzer-Vergleich in V1 über **Verweis statt eigener Datenhaltung** | § 6a Abs. 3 Nr. 4 erlaubt den Verweis nur bei elektronischen Abrechnungen und **nur für die Jahresabrechnung** — nicht für die UVI. Zulieferung der Werte ist eine Lizenzfrage (co2online). |
| K14 | MDL-Beträge werden **nie nachgerechnet**, nur validiert | Lokara hat keine Rechtsposition, eine Messdienst-Abrechnung zu überstimmen; zwei konkurrierende Zahlen für denselben Mieter wären ein Haftungsrisiko. |

---

## 3. Inputs

All money is **integer cents**. All dates are **day-granular** (both boundary days inclusive). All areas are **m², two decimals**. Field names follow Seite 01.

### 3.1 Plant master data

| Field | Unit / type | Source |
| --- | --- | --- |
| `anlage.energietraeger` | enum {erdgas, heizoel, fluessiggas, fernwaerme, waermepumpe, biomasse} | user entry |
| `anlage.verbundeneAnlage` | boolean — hot water from the same plant? | user entry |
| `anlage.gebaeudeTyp` | enum {wohn, nichtwohn, gemischt} | user entry |
| `anlage.denkmalschutz`, `.milieuschutz` | boolean | user entry + mandatory document upload (§ 9 Abs. 3 CO2KostAufG) |
| `anlage.ausschlussNachweis` | boolean — § 9 Abs. 2 CO2KostAufG | user entry + document |
| `grundkostenAnteilProzent` | integer 30–50, default 30 | user entry / K1 |
| `objekt.plz` | string(5) | Stammdaten — key for K12 |

### 3.2 Invoices and operating costs

| Field | Unit / type | Source |
| --- | --- | --- |
| `rechnung.zeitraumVon`, `.zeitraumBis` | date | invoice / OCR |
| `rechnung.mengeKwh` | decimal, 3 dp, Hi | invoice / OCR |
| `rechnung.betragCent` | integer cents | invoice / OCR |
| `rechnung.co2Gramm` | integer gram, nullable | supplier invoice (§ 3 CO2KostAufG); null → K4 fallback |
| `rechnung.co2KostenCent` | integer cents, nullable | supplier invoice; null → price table |
| `rechnung.energiemix`, `.thgGprokWh`, `.primaerenergiefaktor`, `.steuernCent` | string / decimal / cents | supplier invoice — § 6a Abs. 3 Nr. 1 |
| `tankAnfangL`, `tankEndeL` | decimal litre | user entry (oil only) |
| `nebenkosten.betriebsstromCent`, `.wartungCent`, `.messungCent`, `.ausstattungCent`, `.sonstigeCent` | integer cents | user entry — `ausstattungCent` is a § 6a Abs. 3 Nr. 1 c) disclosure item |

### 3.3 Meters and readings

| Field | Unit / type | Source |
| --- | --- | --- |
| `heizgeraet.typ` | enum {hkv, waermezaehler, wwZaehler} | user entry |
| `heizgeraet.nummer` | string | user entry / OCR |
| `heizgeraet.raum` | string (Wohnzimmer, Bad, …) | user entry |
| `heizgeraet.bewertungsfaktor` | decimal, 2 dp (K-Wert) | user entry |
| `ablesung.wertAlt`, `.wertNeu` | decimal, 1 dp | reading |
| `ablesung.datum`, `.anlass` | date / enum {jahres, zwischen, einzug, auszug} | reading |
| `vWwM3` | decimal m³ — central hot-water volume | meter |
| `tw` | integer °C, default 60 | user entry / K5 |
| `wohnung.wwM3` | decimal m³ | meter |
| `anlage.fernablesbar` | boolean | user entry — gates § 6a Abs. 1 |

### 3.4 Rules tables

| Field | Unit / type | Source |
| --- | --- | --- |
| `co2PreisCentProTonne` | integer cents/t, per year | rules-store (§ 10 BEHG) |
| `emissionsfaktor` | decimal kg/kWh | rules-store (K4) |
| `co2Stufentabelle` | 10 rows | rules-store (Anlage CO2KostAufG) |
| `gradtagstabelle` | 12 rows, **integer Zehntelpromille**, Σ = 10000 (K3). Display value = column / 10. Do **not** store as ‰ integer — Jun/Jul/Aug are 400/3 and cannot be represented. | rules-store (K3) |
| `klimafaktor` | decimal 2 dp, key (plz, periodenende) | rules-store, DWD import (K12) |

### 3.5 MDL path

| Field | Unit / type | Source |
| --- | --- | --- |
| `mdl.dokument` | PDF / image | upload or photo |
| `mdl.gesamtkostenCent` | integer cents | OCR + **mandatory confirmation** |
| `mdl.co2Ausgewiesen` | boolean | OCR + confirmation |
| `mdl.co2KostenCent`, `.co2Gramm`, `.vermieterAnteilProzent` | cents / gram / integer | OCR + confirmation |
| `mdl.betragJeNutzeinheitCent` | integer cents, per tenancy | OCR + confirmation |
| `mdl.eigentuemeranteilCent` | integer cents | OCR + confirmation |

---

## 4. Formel

**Rounding rules, applied per step:**

| ID | Regel |
| --- | --- |
| R1 | **Money** — integer cents everywhere. `round_half_up` to whole cents, **once**, at the moment a share is assigned. Never on an already-rounded value. Identical to Seite 01. |
| R2 | **Quotas** — never rounded. Carried as exact decimals (≥ 28 significant digits). |
| R3 | **Energy** — kWh, 3 dp, `round_half_up`. |
| R4 | **Emissions** — gram (integer) internally. Display kg with 1 dp, kg/m²/a with 2 dp. **The step lookup uses the unrounded value.** |
| R5 | **Residual** — `Blockbetrag − Σ gerundete Anteile = Verteilungsrest` → owner bucket, together with the vacancy share. Can be ±1 ct per block (K9). |
| R6 | **Statutory percentages** applied to cent amounts, `round_half_up`. |
| R7 | **Device units** — 1 dp, `round_half_up` (K11). |

### H0 — path selection (runs before everything else)

```jsx
if (abrechnungsart == MDL)  → H7   // ingest, validate, pass through — no own distribution
else                        → H1 … H6
```

### H1 — Gesamtkosten der Anlage (§ 7 Abs. 2 HeizkostenV)

```jsx
gesamtCent = Σ rechnung.betragCent           // allocated per K8, see H1a
           + betriebsstromCent + wartungCent + messungCent
           + ausstattungCent + sonstigeCent
```

**H1a — period allocation (K8):** an invoice whose period only partly overlaps the billing period contributes `round_half_up(betragCent × überlappungstage / rechnungstage)`. Coverage of the billing period is reported; `< 100 %` raises a non-dismissible warning.

**H1b — oil (K7):** `verbrauchtL = tankAnfangL + Σ zukaufL − tankEndeL`. Cost basis is the weighted average price over `tankAnfangL + Σ zukaufL`. CO₂ is computed on the **consumed** quantity, never on the purchased quantity.

### H2 — CO₂ split, deducted before everything else

```jsx
co2Gramm  = Σ rechnung.co2Gramm            // fallback K4: mengeKwh × faktor × 1000
co2Cent   = Σ rechnung.co2KostenCent       // fallback: co2Gramm/1e6 × co2PreisCentProTonne   [R1]
spezifischKgProM2a = (co2Gramm / 1e6) / objekt.gesamtflaecheM2                       [R2, R4]

if (periode.nTage != 365 && != 366)
    spezifischKgProM2a *= 365 / periode.nTage          // annualise BEFORE the lookup

switch (anlage.gebaeudeTyp)
   wohn, gemischt → vermieterAnteilProzent = lookup10(spezifischKgProM2a)   // Anlage CO2KostAufG
   nichtwohn      → vermieterAnteilProzent = 50                             // § 8 CO2KostAufG

if (energietraeger in {waermepumpe, biomasse})   → CO₂ module OFF, co2AbzugVermieterCent = 0
if (denkmalschutz || milieuschutz)               → vermieterAnteilProzent /= 2   // § 9 Abs. 1
if (ausschlussNachweis)                          → vermieterAnteilProzent = 0    // § 9 Abs. 2

co2AbzugVermieterCent = round_half_up(co2Cent × vermieterAnteilProzent / 100)     [R1, R6]
umlagefaehigCent      = gesamtCent − co2AbzugVermieterCent
```

**10-Stufentabelle Wohngebäude** — rules-store table, never in code. Intervals are **left-closed, right-open**: exactly 12,00 → step 2; exactly 52,00 → step 10.

| kg CO₂/m²/a | Mieter | Vermieter |
| --- | --- | --- |
| < 12 | 100 % | 0 % |
| 12 – < 17 | 90 % | 10 % |
| 17 – < 22 | 80 % | 20 % |
| 22 – < 27 | 70 % | 30 % |
| 27 – < 32 | 60 % | 40 % |
| 32 – < 37 | 50 % | 50 % |
| 37 – < 42 | 40 % | 60 % |
| 42 – < 47 | 30 % | 70 % |
| 47 – < 52 | 20 % | 80 % |
| ≥ 52 | 5 % | 95 % |

### H3 — Warmwasser-Abtrennung (§ 9 HeizkostenV) — only if `verbundeneAnlage`

```jsx
a) WW-Wärmezähler present  → qWwKwh = measured kWh              // § 9 Abs. 2 S. 1, priority
b) WW volume meter present → qWwKwh = 2,5 × vWwM3 × (tw − 10)   // § 9 Abs. 2 S. 2        [R3]
c) no measurement          → qWwKwh = 32 × objekt.gesamtflaecheM2  // § 9 Abs. 3 + warning [R3]

anteilWw       = qWwKwh / verbrauchKwhGesamt                                      [R2]
kostenWwCent   = round_half_up(umlagefaehigCent × anteilWw)                       [R1]
kostenHzCent   = umlagefaehigCent − kostenWwCent        // complement, so the sum is exact

if (!verbundeneAnlage) { kostenHzCent = umlagefaehigCent; kostenWwCent = 0 }
```

### H4 — Grund-/Verbrauchskosten per block (§ 7 Abs. 1, § 8 Abs. 1, K1)

```jsx
grundHzCent    = round_half_up(kostenHzCent × grundkostenAnteilProzent / 100)
verbrauchHzCent = kostenHzCent − grundHzCent
grundWwCent    = round_half_up(kostenWwCent × grundkostenAnteilProzent / 100)
verbrauchWwCent = kostenWwCent − grundWwCent
```

### H5 — Geräteaggregation (runs before H6)

```jsx
einheitenGeraetSegment = round((wertNeu − wertAlt) × bewertungsfaktor, 1)          [R7]
if (wertNeu < wertAlt) → REJECT reading (see E18) — never take the absolute value

einheitenMietverhaeltnis = Σ einheitenGeraetSegment of the unit, per usage segment
einheitenWohnung         = Σ over all segments incl. vacancy
nenner                   = Σ einheitenWohnung of the plant
```

Segments are cut by `ablesung.anlass`. A tenant change needs **two** readings (Auszug **and** Einzug) — with only one, the vacancy month cannot be separated from the following tenancy. A segment without its own reading is not distributed by device but by K3 (§ 9b Abs. 3).

### H6 — Distribution to Mietverhältnisse

| Block | Key | Denominator | Tenant change |
| --- | --- | --- | --- |
| `grundHzCent`, `grundWwCent` | m²-days (K2) | `Σ wohnflaecheM2 × nutzungstage` **incl. vacancy** = `nM2Tage` | automatic |
| `verbrauchHzCent` | HKV units or Wärmezähler kWh | Σ over all units of the plant | interim reading (§ 9b Abs. 1); else K3 (§ 9b Abs. 3) |
| `verbrauchWwCent` | m³ per unit | Σ m³, or the measured central volume (see E22) | interim reading; else time-proportional (§ 9b Abs. 2) |

```jsx
anteilCent = round_half_up(blockCent × gewicht / nenner)                          [R1, R2]
rest       = blockCent − Σ anteilCent  → Eigentümer                               [R5]

heizkostenMessdienstCent[i] = grundHz[i] + verbrauchHz[i] + grundWw[i] + verbrauchWw[i]
```

**Guard:** any denominator = 0 → the block is **not** distributed; the engine raises a blocking readiness error. A silent fallback to area distribution is forbidden (see E17).

### H7 — MDL path (§ 4.7)

```jsx
M1  OCR extract → mandatory field-by-field confirmation screen. No confidence threshold
    releases a value automatically.

M2  if (mdl.co2Ausgewiesen)
        amounts are already net → co2AbzugVermieterCent = 0, NO second deduction
    else
        run H2 on mdl.gesamtkostenCent, then rescale every amount:
        nettoCent[i] = round_half_up(bruttoCent[i] × umlagefaehigCent / mdl.gesamtkostenCent)
        // exact, because the CO₂ deduction happens before both blocks are split
        residual = umlagefaehigCent − Σ nettoCent[i] − nettoEigentuemerCent → owner   [R5]

M3  control sum — BLOCKING, but the reference value depends on the branch taken in M2.
    Comparing gross OCR figures against a net total would refuse every valid run.

        toleranz = number of amount positions read (tenancies + owner), in cents

        if (mdl.co2Ausgewiesen)            // M2 net branch
            ref = umlagefaehigCent
        else                               // M2 gross branch
            ref = mdl.gesamtkostenCent

        abweichung = | Σ mdl.betragJeNutzeinheitCent + mdl.eigentuemeranteilCent − ref |

        if (abweichung == 0)          → pass
        if (abweichung <= toleranz)   → pass; the difference goes to the owner bucket [R5]
                                        and is logged — it is a rounding residual of the
                                        Messdienst, not an OCR error
        if (abweichung >  toleranz)   → statement run refused, offending field highlighted

    Rationale: a Messdienst statement rounds every position to whole cents, so a residual
    of up to one cent per position is normal and must not block. An OCR decimal shift is
    orders of magnitude larger (see F29: 313,04 €) and is still caught.

M4  output = amount per tenancy → heizkostenMessdienstCent, unchanged (K14)
    + Pflichtausweis block from mdl.co2* — or the § 7 Abs. 4 risk flag if absent (E30)
```

### H8 — § 6a Abs. 3 Nr. 5 comparison (feeds the document layer of Seite 01)

```jsx
kfAktuell  = klimafaktor(objekt.plz, periode.bis)                     // K12
kfVorjahr  = klimafaktor(objekt.plz, periode.bis − 1 Jahr)
bereinigtWaerme[j] = round(einheitenHz[j] × kf[j], 1)                 // heat only, § 6a Abs. 3 S. 3
warmwasser[j]      = ww-m³ or kWh, UNADJUSTED                        // § 6a Abs. 3 S. 2
veraenderung       = bereinigtWaerme[akt] / bereinigtWaerme[vor] − 1  // display 1 dp %
```

Both years are adjusted, each with its own KF. `KF > 1` (mild year) **raises** the adjusted value. Missing KF → print the comparison **unadjusted** with a note; never substitute 1,00. The output is a **graph**, not only a number (§ 6a Abs. 3 S. 1 Nr. 5) — layout on Seite 01.

---

## 5. Edge Cases

| # | Case | Behaviour | Fixture |
| --- | --- | --- | --- |
| E1 | Supplier states no CO₂ mass / cost (breach of § 3 CO2KostAufG) | Fallback K4 + price table, **warning**, § 7 Abs. 4 risk flag | 01b-F02 |
| E2 | `spezifisch` exactly on a step boundary (12,00 / 52,00) | Left-closed interval → the higher step | 01b-F03, 01b-F04 |
| E3 | `spezifisch` rounds up to a boundary but is below it | Lookup on the unrounded value (R4). Print the floored value, never `12,00` next to a 0 % share | 01b-F05 |
| E4 | Billing period ≠ 12 months | Annualise `× 365 / nTage` **before** the lookup | 01b-F06 |
| E5 | Nichtwohngebäude | 50/50 (§ 8 CO2KostAufG). Gemischt genutzt → step model, see Offene Fragen | 01b-F07 |
| E6 | Denkmal-/Milieuschutz | Landlord share halved (§ 9 Abs. 1); full exclusion only with stored proof (Abs. 2 + 3) | 01b-F08, 01b-F09 |
| E7 | Non-BEHG energy source (Wärmepumpe, Biomasse) | CO₂ module off, no deduction, **no** Pflichtausweis, **no** step traffic light in the UI | 01b-F10 |
| E8 | Hot water not measurable | Path c (32 kWh/m²) + warning: the flat rate systematically overstates WW in efficient buildings | 01b-F12 |
| E9 | Plant not connected | No WW split, one block only | 01b-F13 |
| E10 | `grundkostenAnteilProzent` set to 50 | Lawful; shifts money towards large and vacant units — show the owner's extra burden **before** saving | 01b-F14 |
| E11 | Tenant change **with** interim readings | Two tenancies, measured units each | 01b-F01, 01b-F27 |
| E12 | Tenant change **without** interim reading | § 9b Abs. 3 → Gradtagszahlen K3; the vacancy month's units go to the owner | 01b-F16 |
| E13 | Single device failure, affected area ≤ 25 % | § 9a Abs. 1 estimate. Arithmetic unchanged, provenance flagged on the statement | 01b-F17 |
| E14 | Failure affects > 25 % of area | § 9a Abs. 2 → the **entire** distribution by area; consumption blocks dissolve | 01b-F18 |
| E15 | Oil: purchase ≠ consumption | Tank logic K7; CO₂ on the consumed quantity | 01b-F19 |
| E16 | Fernwärme | Supplier states cost + CO₂ → pass-through; the step model is applied nonetheless | 01b-F20 |
| E17 | No consumption data at all (denominator 0) | **Hard stop.** No silent area fallback. § 12 Abs. 1 S. 1 risk (15 %) displayed | 01b-F21 |
| E18 | Negative reading delta (meter swap / rollover) | Reading rejected; two segments must be summed. Never `abs()` | 01b-F22 |
| E19 | `spezifisch` outside 5–70 kg/m²/a | Warning (K6), calculation proceeds | 01b-F23 |
| E20 | Invoice period overlaps the billing period | Linear day allocation (K8) + non-dismissible coverage warning | 01b-F24 |
| E21 | Not remote-readable / no UVI / no CO₂ disclosure | Display the 15 % / 3 % / 3 % risk amounts. **Never auto-reduce** — the reduction is the tenant's right, not the landlord's calculation | 01b-F25 |
| E22 | Σ unit WW meters ≠ measured central volume | `qWwKwh` from the central value; distribution by unit meters; the gap stays with the owner; warning if > 5 % | 01b-F26 |
| E23 | Vacancy in the billing period | Falls out automatically — the denominators are object-level. Owner bucket | 01b-F01 |
| E24 | Period > 12 months | Validation error, inherited from Seite 01 (E6) | — (Seite 01, 08-F15) |
| E25 | Multiple radiators per unit, different K-Werte | Aggregation per H5; the device list is stored and printed (K10) | 01b-F27 |
| E26 | MDL statement **with** CO₂ split shown | Amounts taken net, no second deduction | 01b-F28a |
| E27 | MDL statement **without** CO₂ split | H2 on the MDL total + proportional rescaling; round-trip loses ≤ 1 ct → owner | 01b-F28b |
| E28 | OCR misreads a value (decimal shift) | Control sum M3 fails → **run blocked** | 01b-F29 |
| E29 | MDL statement without any CO₂ information and no fuel invoice | Pflichtausweis impossible → § 7 Abs. 4 risk per tenancy, shown before dispatch | 01b-F30 |
| E30 | § 6a Abs. 3 information block incomplete | 3 % risk (§ 12 Abs. 1 S. 3). Needs the KF table (K12) and the Durchschnittsnutzer source (K13) | 01b-F31 |
| E31 | Tenant has no preceding billing period (moved in during the year) | The § 6a Abs. 3 Nr. 5 comparison does not exist. Print the note, not an empty graph | 01b-F31 |

---

## 6. BEISPIELRECHNUNG

**Reference object — identical to Seite 01:** Musterstraße 12, 50667 Köln · 01.01.–31.12.2025 (365 d) · WE-01 62 m² (Muster, 365 d) · WE-02 74 m² (Schneider bis 31.07. = 212 d; Weber ab 01.09. = 122 d; August Leerstand) · WE-03 58 m² (Beispiel, 365 d) · Σ 194 m².

m²-Tage: Muster 22.630 · Schneider 15.688 · Weber 9.028 · Beispiel 21.170 · Leerstand 2.294 · **`nM2Tage` = 70.810**.

Plant: Erdgas, verbunden. 28.000 kWh · Brennstoff 322.000 ct · Betriebsstrom 9.600 ct · Wartung 19.000 ct · invoice CO₂ 5.628 kg / 30.954 ct (= 55 €/t, Festpreis 2025) · `vWwM3` 78, `tw` 60 °C · HKV: Muster 4.100,0 · Schneider 2.520,0 · Weber 1.080,0 · Beispiel 3.050,0 (Σ 10.750,0) · WW-m³: 34 / 15 / 6 / 23 (Σ 78).

> 🔴 **Verhältnis zu `08-F01` (Seite 01) — muss Emir kennen.** `08-F01` rechnet dasselbe Objekt mit **Messdienst-Werten** (Heizkosten 314.000 ct, je Mieter 118.000 / 76.000 / 31.000 / 89.000). Das ist der **MDL-Pfad**. `01b-F01` rechnet dasselbe Objekt im **Selbstabrechner-Pfad** und kommt auf 3.382,18 € umlagefähig, davon 334.933 ct auf die Mieter. Beide sind richtig — es sind zwei Datenpfade, nicht zwei Ergebnisse desselben Pfades. **Sie dürfen nicht gegeneinander getestet werden.** Vorschlag: `08-F01` bleibt unangetastet (Golden Fixture, Excel-Orakel), und Seite 01 bekommt zusätzlich `08-F24` = dasselbe Objekt mit den Heizbeträgen aus `01b-F01`. Entscheidung siehe To-Dos.
> 

### 01b-F01 — Baseline, full pipeline (Golden Fixture)

**H1:** 322.000 + 9.600 + 19.000 = **350.600 ct = 3.506,00 €**

**H2:** `spezifisch` = 5.628 / 194 = 29,010309… → **29,01 kg/m²/a** → Stufe 27 – <32 → Vermieter **40 %**

`co2AbzugVermieterCent` = 30.954 × 0,40 = 12.381,6 → **12.382 ct = 123,82 €**

`umlagefaehigCent` = 350.600 − 12.382 = **338.218 ct = 3.382,18 €**

**H3:** path b) `qWwKwh` = 2,5 × 78 × (60 − 10) = **9.750,000 kWh** · `anteilWw` = 9.750 / 28.000 = 0,348214285714…

`kostenWwCent` = 338.218 × 0,348214285… = 117.771,64… → **117.772 (1.177,72 €)**

`kostenHzCent` = 338.218 − 117.772 = **220.446 (2.204,46 €)**

**H4:** `grundHz` = 220.446 × 0,30 = 66.133,8 → **66.134 (661,34 €)** · `verbrauchHz` = **154.312 (1.543,12 €)**

`grundWw` = 117.772 × 0,30 = 35.331,6 → **35.332 (353,32 €)** · `verbrauchWw` = **82.440 (824,40 €)**

**H6:**

| Partei | Quote m²-T | grundHz | grundWw | Quote HKV | verbrauchHz | Quote m³ | verbrauchWw |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Muster | 0,31958763 | 21.136 | 11.292 | 0,38139535 | 58.854 | 0,43589744 | 35.935 |
| Schneider | 0,22155062 | 14.652 | 7.828 | 0,23441860 | 36.174 | 0,19230769 | 15.854 |
| Weber | 0,12749611 | 8.432 | 4.505 | 0,10046512 | 15.503 | 0,07692308 | 6.342 |
| Beispiel | 0,29896907 | 19.772 | 10.563 | 0,28372093 | 43.782 | 0,29487179 | 24.309 |
| Eigentümer (Rest R5) | 0,03239655 | 2.142 | 1.144 | — | −1 | — | 0 |

Die exakte Leerstandsquote wäre 2.143 / 1.145 ct; je ein Cent wird als Verteilungsrest absorbiert, der Verbrauchsblock Heizung überschießt um 1 ct. Beides landet im Eigentümer-Bucket (K9).

**Ergebnis je Mietverhältnis (Feld `heizkostenMessdienstCent`):**

| Mieter | grundHz | verbrauchHz | grundWw | verbrauchWw | **Gesamt** |
| --- | --- | --- | --- | --- | --- |
| Muster | 21.136 | 58.854 | 11.292 | 35.935 | **127.217 = 1.272,17 €** |
| Schneider | 14.652 | 36.174 | 7.828 | 15.854 | **74.508 = 745,08 €** |
| Weber | 8.432 | 15.503 | 4.505 | 6.342 | **34.782 = 347,82 €** |
| Beispiel | 19.772 | 43.782 | 10.563 | 24.309 | **98.426 = 984,26 €** |

**Summenprobe:** 127.217 + 74.508 + 34.782 + 98.426 = **334.933** umgelegt + **3.285** Eigentümer = **338.218** ✓

**Zweite Probe:** 338.218 + 12.382 CO₂-Vermieteranteil = **350.600** = H1 ✓

### 01b-F02 — E1, CO₂ fallback, supplier gave no figures

`co2Gramm` = 28.000 kWh × 0,201 kg/kWh × 1000 = **5.628.000 g**

`co2Cent` = 5.628/1000 × 5.500 ct/t = **30.954 ct**

Both equal F01 → **all downstream results identical to F01**. Difference: warning „Lieferant hat CO₂-Angaben nicht ausgewiesen (§ 3 CO2KostAufG)" + the § 7 Abs. 4 risk flag.

⚠️ **From 2026 the fallback is unsafe.** There is no single BEHG price for 2026 (auction 55–65 €/t, sales phase 68 €, make-up 70 €). For periods ≥ 2026 the fallback must ask the user for the €/t actually paid, or block. Decision: To-Dos.

### 01b-F03 — E2, step boundary exactly 12,00

`co2Gramm` 2.328.000 → `spezifisch` = 2.328 / 194 = **12,00 exakt** → Intervall [12, 17) → **10 %**

`co2Cent` = 2.328/1000 × 5.500 = 12.804 → `abzug` = 12.804 × 0,10 = 1.280,4 → **1.280 (12,80 €)**

`umlagefaehig` = 350.600 − 1.280 = **349.320 (3.493,20 €)**

### 01b-F04 — E2, step boundary exactly 52,00

`co2Gramm` 10.088.000 → `spezifisch` = **52,00 exakt** → Stufe 10 → **95 %**

`co2Cent` = **55.484** → `abzug` = 55.484 × 0,95 = 52.709,8 → **52.710 (527,10 €)**

`umlagefaehig` = **297.890 (2.978,90 €)**

### 01b-F05 — E3, display rounds to the boundary, value does not

`co2Gramm` 2.327.900 → `spezifisch` = 11,999484535… → **naiv gerundet 12,00**, Lookup-Wert < 12 → Stufe 1 → **0 %**

`co2Cent` = 2.327,9/1000 × 5.500 = 12.803,45 → **12.803 (128,03 €)** · `abzug` = **0** · `umlagefaehig` = **350.600**

Ausgaberegel: der Pflichtausweis druckt `11,99` (abgeschnitten, nicht gerundet) — sonst kann der Mieter den 0-%-Anteil nicht nachvollziehen.

### 01b-F06 — E4, short period, annualisation

Zeitraum 01.04.–31.12.2025 = **275 Tage**, `co2Gramm` 4.200.000, `co2Cent` 23.100.

`spezifisch_roh` = 4.200 / 194 = 21,649484…

`spezifisch` = 21,649484… × 365 / 275 = **28,734770…** → **28,73** → Stufe 27 – <32 → **40 %**

Ohne Annualisierung: Stufe 17 – <22 → 20 % → Fehler von 46,20 €.

`abzug` = 23.100 × 0,40 = **9.240 (92,40 €)** · `umlagefaehig` = **341.360 (3.413,60 €)**

### 01b-F07 — E5, Nichtwohngebäude

`gebaeudeTyp = nichtwohn` → Stufenmodell übersprungen, § 8 CO2KostAufG → **50 %**

`abzug` = 30.954 × 0,50 = **15.477 (154,77 €)** · `umlagefaehig` = **335.123 (3.351,23 €)**

### 01b-F08 — E6, Denkmalschutz (§ 9 Abs. 1 CO2KostAufG)

Stufenanteil 40 % → halbiert → **20 %** · `abzug` = 30.954 × 0,20 = 6.190,8 → **6.191 (61,91 €)**

`umlagefaehig` = **344.409 (3.444,09 €)** — 61,91 € mehr auf die Mieter als in F01.

Die UI darf die Checkbox erst nach Upload eines Nachweises freigeben (§ 9 Abs. 3).

### 01b-F09 — E6, vollständiger Ausschluss (§ 9 Abs. 2 CO2KostAufG)

`vermieterAnteilProzent` = **0** · `abzug` = **0** · `umlagefaehig` = **350.600 (3.506,00 €)**

Der Pflichtausweis druckt die Emissionswerte trotzdem und nennt den Ausschlussgrund.

### 01b-F10 — E7, Wärmepumpe

Modul aus: kein `co2Gramm`, kein Lookup, `abzug` = **0**, `umlagefaehig` = **350.600**, **kein** Pflichtausweis, **keine** Stufenampel.

### 01b-F11 — H3 Pfad a), WW-Wärmezähler

`qWwKwh` = **9.100** → `anteilWw` = 9.100 / 28.000 = **0,325**

`kostenWw` = **109.921 (1.099,21 €)** · `kostenHz` = **228.297 (2.282,97 €)**

`grundHz` 68.489 · `verbrauchHz` 159.808 · `grundWw` 32.976 · `verbrauchWw` 76.945

| Mieter | grundHz | verbrauchHz | grundWw | verbrauchWw | **Gesamt** |
| --- | --- | --- | --- | --- | --- |
| Muster | 21.888 | 60.950 | 10.539 | 33.540 | **126.917** |
| Schneider | 15.174 | 37.462 | 7.306 | 14.797 | **74.739** |
| Weber | 8.732 | 16.055 | 4.204 | 5.919 | **34.910** |
| Beispiel | 20.476 | 45.341 | 9.859 | 22.689 | **98.365** |

Probe: 334.931 + 3.287 Eigentümer = **338.218** ✓

### 01b-F12 — E8, H3 Pfad c), 32 kWh/m²

`qWwKwh` = 32 × 194 = **6.208** → `anteilWw` = 0,221714285…

`kostenWw` = **74.988 (749,88 €)** · `kostenHz` = **263.230 (2.632,30 €)**

`grundHz` 78.969 · `verbrauchHz` 184.261 · `grundWw` 22.496 · `verbrauchWw` 52.492

| Mieter | grundHz | verbrauchHz | grundWw | verbrauchWw | **Gesamt** |
| --- | --- | --- | --- | --- | --- |
| Muster | 25.238 | 70.276 | 7.189 | 22.881 | **125.584** |
| Schneider | 17.496 | 43.194 | 4.984 | 10.095 | **75.769** |
| Weber | 10.068 | 18.512 | 2.868 | 4.038 | **35.486** |
| Beispiel | 23.609 | 52.279 | 6.726 | 15.478 | **98.092** |

Probe: 334.931 + 3.287 = **338.218** ✓ — Weber zahlt **+7,04 €** gegenüber F01, Muster **−16,33 €**: die Pauschale bestraft sparsame Nutzer. Der Warntext muss das sagen.

### 01b-F13 — E9, nicht verbundene Anlage

Ein Block. `grund` = 338.218 × 0,30 = 101.465,4 → **101.465 (1.014,65 €)** · `verbrauch` = **236.753 (2.367,53 €)**

| Mieter | grund (m²-T) | verbrauch (HKV) | **Gesamt** |
| --- | --- | --- | --- |
| Muster | 32.427 | 90.296 | **122.723** |
| Schneider | 22.480 | 55.499 | **77.979** |
| Weber | 12.936 | 23.785 | **36.721** |
| Beispiel | 30.335 | 67.172 | **97.507** |

Probe: 334.930 + 3.288 = **338.218** ✓

### 01b-F14 — E10, Grundkostenanteil 50 %

`grundHz` = **110.223** = `verbrauchHz` · `grundWw` = **58.886** = `verbrauchWw`

| Mieter | grundHz | verbrauchHz | grundWw | verbrauchWw | **Gesamt** |
| --- | --- | --- | --- | --- | --- |
| Muster | 35.226 | 42.039 | 18.819 | 25.668 | **121.752** |
| Schneider | 24.420 | 25.838 | 13.046 | 11.324 | **74.628** |
| Weber | 14.053 | 11.074 | 7.508 | 4.530 | **37.165** |
| Beispiel | 32.953 | 31.273 | 17.605 | 17.364 | **99.195** |

Probe: 332.740 + **5.478 Eigentümer** = **338.218** ✓ — der Leerstandsanteil des Eigentümers steigt von 32,85 € auf 54,78 €. Das ist der ehrliche Preis eines höheren Grundkostenanteils und gehört vor dem Speichern in die UI.

### 01b-F15 — H6-Zweig, Verbrauchsverteilung über Wärmezähler statt HKV

Wärmezähler kWh: Muster 9.000 · Schneider 5.250 · Weber 2.250 · Beispiel 5.000 (Σ 21.500). Alles andere wie F01.

| Mieter | Quote | verbrauchHz | übrige Blöcke (= F01) | **Gesamt** |
| --- | --- | --- | --- | --- |
| Muster | 0,41860465 | 64.596 | 68.363 | **132.959** |
| Schneider | 0,24418605 | 37.681 | 38.334 | **76.015** |
| Weber | 0,10465116 | 16.149 | 19.279 | **35.428** |
| Beispiel | 0,23255814 | 35.887 | 54.644 | **90.531** |

Probe: 334.933 + 3.285 = **338.218** ✓

### 01b-F16 — E12, Nutzerwechsel ohne Zwischenablesung (§ 9b Abs. 3)

WE-02 Jahressumme 3.600,0 Einheiten, keine Ablesung am 31.07. → K3 (Zehntelpromille, Σ = 10000):

Schneider Jan–Jul = 1700+1500+1300+800+400+133+133 = **5.966** (596,6 ‰) → 3.600 × 0,5966 = **2.147,8**

Weber Sep–Dez = 300+800+1200+1600 = **3.900** (390,0 ‰) → 3.600 × 0,3900 = **1.404,0**

August (Leerstand) = **134** (13,4 ‰) → 3.600 − 2.147,8 − 1.404,0 = **48,2 → Eigentümer**

| Mieter | Einheiten | verbrauchHz | übrige Blöcke | **Gesamt** |
| --- | --- | --- | --- | --- |
| Muster | 4.100,0 | 58.854 | 68.363 | **127.217** |
| Schneider | 2.147,8 | 30.831 | 38.334 | **69.165** |
| Weber | 1.404,0 | 20.154 | 19.279 | **39.433** |
| Beispiel | 3.050,0 | 43.782 | 54.644 | **98.426** |
| Leerstand | 48,2 | 692 | — | → Eigentümer |

Probe: 334.241 + **3.977 Eigentümer** = **338.218** ✓

Gegen F01 (echte Zwischenablesung): Schneider **−53,43 €**, Weber **+46,51 €**. Das ist das Argument, die Zwischenablesung beim Auszug in der UI zu erzwingen.

### 01b-F17 — E13, § 9a Abs. 1 Schätzung, ≤ 25 % der Fläche

Ein HKV in WE-03 fällt aus, betroffener Raum 18 m² → 18 / 194 = **9,28 % ≤ 25 %** → Schätzung zulässig.

Vorjahreswert des Geräts: **620,0 Einheiten**. WE-03 = 2.430,0 gemessen + 620,0 geschätzt = **3.050,0**.

Alle Folgewerte **identisch zu F01** (Beispiel 98.426 ct). Unterschied: die Zeile wird als `geschätzt nach § 9a Abs. 1 HeizkostenV` gekennzeichnet, mit Nennung der Schätzgrundlage. Der Test prüft **das Flag**, nicht nur den Betrag.

### 01b-F18 — E14, § 9a Abs. 2, > 25 % der Fläche

Alle Geräte in WE-03 ausgefallen, keine Vorjahreswerte. 58 / 194 = **29,90 % > 25 %** → Verbrauchsblöcke lösen sich auf, alles nach m²-Tagen.

| Mieter | Quote | **Gesamt** | Δ zu F01 |
| --- | --- | --- | --- |
| Muster | 0,31958763 | **108.090** | −19.127 |
| Schneider | 0,22155062 | **74.932** | +424 |
| Weber | 0,12749611 | **43.121** | +8.339 |
| Beispiel | 0,29896907 | **101.117** | +2.691 |

Probe: 327.260 + **10.958 Eigentümer** = **338.218** ✓

§ 12 Abs. 1 S. 1 (15 %) greift hier **nicht** — § 9a ist der gesetzlich vorgesehene Weg, kein Verstoß.

### 01b-F19 — E15, Öl-Tanklogik über zwei Kaufperioden

Eigenes Objekt B (420 m², Heizöl). Anfangsbestand 3.200 l à 92 ct = **294.400 ct** · Kauf 1: 2.500 l à 98 ct = **245.000** · Kauf 2: 2.000 l à 105 ct = **210.000**. Endbestand 2.100 l.

`verbrauchtL` = 3.200 + 2.500 + 2.000 − 2.100 = **5.600 l**

Durchschnittspreis (K7) = 749.400 / 7.700 = **97,324675… ct/l**

Brennstoffkosten = 5.600 × 97,324675… = 545.018,18… → **545.018 (5.450,18 €)**

Bestandswert Vortrag = 2.100 × 97,324675… = **204.382 (2.043,82 €)**

Probe: 545.018 + 204.382 = **749.400** ✓

Energie = 5.600 × 10 = **56.000 kWh** · `co2Gramm` = 56.000 × 0,266 × 1000 = **14.896.000 g**

`spezifisch` = 14.896 / 420 = **35,47** → Stufe 32 – <37 → **50 %**

`co2Cent` = 14.896/1000 × 5.500 = **81.928** · `abzug` = **40.964 (409,64 €)**

⚠️ **Falle, die der Test fangen muss:** CO₂ auf die **gekauften** 7.700 l ergäbe 20.482 kg → 48,77 kg/m²/a → Stufe 47 – <52 → 80 % → `abzug` 90.121 ct. Differenz **491,57 €**. Falsch zugunsten des Vermieters ist auch falsch.

### 01b-F20 — E16, Fernwärme, Durchreichung

Versorgerrechnung: Wärme 410.000 ct, darin ausgewiesene CO₂-Kosten **26.800 ct** für **4.870 kg**. Plus Betriebsstrom 9.600 + Wartung 19.000.

`gesamtCent` = **438.600 (4.386,00 €)**

`spezifisch` = 4.870 / 194 = 25,103092… → **25,10** → Stufe 22 – <27 → **30 %**

`abzug` = 26.800 × 0,30 = **8.040 (80,40 €)** · `umlagefaehig` = **430.560 (4.305,60 €)**

Durchreichung betrifft die **Zahlen**, nicht die Aufteilung — das Stufenmodell wird trotzdem gerechnet. Zusätzlich: Primärenergiefaktor und THG des Netzes sind § 6a Abs. 3 Nr. 1 a)-Pflichtangaben.

### 01b-F21 — E17, keine Verbrauchsdaten (Nenner 0)

Alle HKV-Ablesungen fehlen → `nenner` = 0. `verbrauchHzCent` (154.312) ist nicht verteilbar → **blockierender Readiness-Fehler**, kein Dokument.

Angezeigtes Risiko, falls trotzdem nach Fläche abgerechnet würde: § 12 Abs. 1 S. 1 → 15 % je Mieter, z. B. Muster 15 % von 127.217 = **19.083 ct = 190,83 €**.

Ausdrücklich verboten: stiller Rückfall auf Flächenverteilung. Das sähe korrekt aus und wäre eine 15-%-Haftung je Mieter.

### 01b-F22 — E18, negative Ablesedifferenz

WE-01, Zählertausch am 15.08. Eingegeben: alt 12.480,0 → neu 11.020,0 → Differenz **−1.460,0 → abgelehnt**.

Korrekt, zwei Segmente: Altgerät 12.480,0 → 12.900,0 = **420,0** · Neugerät 0,0 → 1.040,0 = **1.040,0** · Σ = **1.460,0**.

Regel: `delta < 0` ist nie ein Wert, sondern immer entweder ein Gerätetausch (zwei Segmente) oder ein Tippfehler.

### 01b-F23 — E19, Plausibilitätsband (K6)

a) `co2Gramm` 14.500.000 → 14.500 / 194 = **74,74 kg/m²/a** > 70 → Warnung „Wert außergewöhnlich hoch — Rechnung in kg oder t erfasst?" Rechnung läuft weiter (Stufe 10, 95 %).

b) `co2Gramm` 800.000 → **4,12 kg/m²/a** < 5 → Warnung „Wert außergewöhnlich niedrig — nur eine Teilrechnung erfasst?" Läuft weiter (Stufe 1, 0 %).

K6 ist Heuristik, nie Blockade — ein wirklich effizientes Gebäude muss abrechenbar bleiben.

### 01b-F24 — E20, Rechnungszeitraum ≠ Abrechnungszeitraum

Rechnung 360.000 ct für 01.11.2024–31.10.2025 (365 d). Abrechnungszeitraum 01.01.–31.12.2025.

Überlappung = 01.01.–31.10.2025 = **304 Tage**

Anteil = 360.000 × 304 / 365 = 299.835,6 → **299.836 (2.998,36 €)**

Deckung = 304 / 365 = **83,29 %** → Warnung „Zeitraum nicht vollständig durch Rechnungen gedeckt (61 Tage fehlen)".

K8 ist linear nach Tagen, nicht nach Gradtagen. Bei einer Lücke im Nov/Dez **unterschätzt** das die Heizkosten — die Warnung darf nicht still wegklickbar sein.

### 01b-F25 — E21, Kürzungsrechte, reine Anzeige

Bemessungsgrundlage ist der Heizkostenanteil des jeweiligen Mieters. Muster, F01 = 127.217 ct:

| Auslöser | Norm | Satz | Betrag |
| --- | --- | --- | --- |
| Keine fernablesbare Ausstattung nach dem 31.12.2026 | § 12 Abs. 1 S. 2 i. V. m. § 5 Abs. 2 | 3 % | **3.817 ct = 38,17 €** |
| § 6a-Informationen fehlen oder unvollständig | § 12 Abs. 1 S. 3 i. V. m. § 6a | 3 % | **3.817 ct = 38,17 €** |
| CO₂-Pflichtangaben verletzt | § 7 Abs. 4 CO2KostAufG | 3 % | **3.817 ct = 38,17 €** |
| Nicht verbrauchsabhängig abgerechnet | § 12 Abs. 1 S. 1 | 15 % | **19.083 ct = 190,83 €** |

Die Engine zieht **nie** ab. Sie zeigt dem Vermieter, wogegen er sich exponiert. **[UNSICHER: ob die drei 3-%-Rechte untereinander und mit den 15 % kumulieren — keine Summierung implementieren.]**

### 01b-F26 — E22, Wohnungszähler ≠ zentrales Volumen

Zentral `vWwM3` = 78; Wohnungszähler 34 + 15 + 6 + 19 = **74 m³**; Lücke 4 m³ = **5,13 %**.

**Erwartung nach der korrigierten Schwelle (K — Abweichungsschwelle Warmwasserzähler, Stand 27.07.2026): keine Meldung.** 5,13 % liegt unter der Verkehrsfehlergrenze von 10 %; eine Differenz dieser Größe ist in Bestandsgebäuden der Normalfall. Die Verteilung läuft unverändert.

Schwellen zur Abgrenzung (eigene Testfälle, ohne vollständige Verteilungsrechnung):

- **F26b** — Wohnungszähler Σ 69 m³, Lücke 9 m³ = **11,54 %** → *Hinweis*, nicht blockierend: „Differenz über der Verkehrsfehlergrenze, Anlage und Zählerstände prüfen."
- **F26c** — Wohnungszähler Σ 61 m³, Lücke 17 m³ = **21,79 %** → *Warnung* mit Rechtsfolge: Mehrkosten oberhalb von 20 % trägt nach der Rechtsprechung der Vermieter.

*(Bis 27.07.2026 lautete die Konvention „Warnung ab 5 %" und dieses Fixture erwartete bei 5,13 % eine Warnung. Die Schwelle wurde auf zweistufig 10 %/20 % korrigiert — die Erwartung hier ist entsprechend nachgezogen.)*

`qWwKwh` bleibt auf dem zentralen Wert (78 → 9.750 kWh, Blöcke wie F01). `verbrauchWwCent` 82.440 wird nach Wohnungszählern verteilt, aber mit dem **zentralen** Nenner 78:

| Mieter | m³ | verbrauchWw |
| --- | --- | --- |
| Muster | 34 | 35.935 |
| Schneider | 15 | 15.854 |
| Weber | 6 | 6.342 |
| Beispiel | 19 | 20.082 |
| unerfasst | 4 | **4.227 → Eigentümer** |

Durch 74 statt 78 zu teilen würde 42,27 € nicht erfasstes Warmwasser still auf die Mieter schieben.

### 01b-F27 — E25/E11, Geräteaggregation (Vorbedingungs-Fixture zu F01)

**WE-01 · Muster (365 d, kein Nutzerwechsel):**

| Gerät | Raum | alt | neu | Differenz | Faktor | Einheiten |
| --- | --- | --- | --- | --- | --- | --- |
| 88-1041 | Wohnzimmer | 1.240,0 | 2.110,0 | 870,0 | 1,80 | **1.566,0** |
| 88-1042 | Schlafzimmer | 880,0 | 1.512,0 | 632,0 | 1,25 | **790,0** |
| 88-1043 | Kinderzimmer | 640,0 | 1.245,0 | 605,0 | 1,60 | **968,0** |
| 88-1044 | Bad | 302,0 | 690,0 | 388,0 | 2,00 | **776,0** |
|  |  |  |  |  | **Σ** | **4.100,0** ✓ |

**WE-02 · Schneider (bis 31.07.) → Leerstand (August) → Weber (ab 01.09.):** vier Ablesungen je Gerät.

| Gerät | Raum | Faktor | 01.01. |
| --- | --- | --- | --- |
| 88-2041 | Wohnzimmer | 1,80 | 500,0 |
| 88-2042 | Schlafzimmer | 1,20 | 300,0 |
| 88-2043 | Bad | 2,00 | 150,0 |
| Gerät | Schneider | Leerstand | Weber |
| --- | --- | --- | --- |
| 88-2041 | 820,0 × 1,80 = **1.476,0** | 0,0 | 280,0 × 1,80 = **504,0** |
| 88-2042 | 520,0 × 1,20 = **624,0** | 0,0 | 180,0 × 1,20 = **216,0** |
| 88-2043 | 210,0 × 2,00 = **420,0** | 0,0 | 180,0 × 2,00 = **360,0** |
| **Σ** | **2.520,0** ✓ | **0,0** | **1.080,0** ✓ |

Der August ist **auf null gemessen** (identische Stände am 31.07. und 01.09.), nicht erschlossen. Möglich nur, weil § 9b Abs. 1 eine Ablesung bei Auszug **und** bei Einzug verlangt. Mit nur einer Ablesung am 31.07. wären rund 54 Einheiten Fremdverbrauch auf Weber gelandet.

**WE-03 · Beispiel:** 88-3041 Wohnzimmer 1,80 × 700,0 = 1.260,0 · 88-3042 Schlafzimmer 1,25 × 560,0 = 700,0 · 88-3043 Bad 2,00 × 545,0 = 1.090,0 → **Σ 3.050,0** ✓

**Objektprobe:** 4.100,0 + 3.600,0 + 3.050,0 = **10.750,0** = Nenner aus F01 ✓

Testkette: `Ablesungen → Einheiten (F27) → Verteilung (F01)`.

### 01b-F28a — E26, MDL-Pfad, CO₂ bereits aufgeteilt

Hochgeladene Messdienst-Abrechnung, OCR + Bestätigung: Gesamtkosten 350.600 · CO₂ 5.628 kg / 30.954 · Vermieteranteil 40 % = 12.382 · umlagefähig 338.218. Je Nutzeinheit: 127.217 / 74.508 / 34.782 / 98.426 · Eigentümer 3.285.

**M3-Kontrolle:** 127.217 + 74.508 + 34.782 + 98.426 + 3.285 = **338.218** ✓ → Lauf freigegeben.

`co2AbzugVermieterCent` = 0 (bereits abgezogen). Ergebnis identisch zu F01 — beide Pfade **müssen** konvergieren. Das ist der Regressionstest gegen den Doppelabzug.

### 01b-F28b — E27, MDL-Pfad ohne CO₂-Aufteilung

Abrechnung zeigt brutto 350.600 und je Nutzeinheit 131.874 / 77.236 / 36.055 / 102.029 · Eigentümer 3.405.

H2 auf 350.600: `spezifisch` 29,01 → 40 % → `abzug` **12.382** → `umlagefaehig` **338.218**

Skalierungsfaktor = 338.218 / 350.600 = **0,9646833998859…**

⚠️ **Nie den gerundeten Faktor verwenden — immer den Quotienten neu rechnen** (R2: Quoten werden nicht gerundet). Mit dem früher hier stehenden Wert 0,964689 ergibt Schneider 74.509 statt 74.508 ct, und die Kontrollsumme geht nicht mehr auf. *(Zahlendreher, korrigiert am 27.07.2026.)*

**M3-Erwartung:** Die Brutto-Positionen summieren auf 131.874 + 77.236 + 36.055 + 102.029 + 3.405 = **350.599**, also **1 ct unter** `mdl.gesamtkostenCent` = 350.600. Das ist ein Rundungsrest des Messdiensts, kein OCR-Fehler: 5 Positionen → `toleranz` = 5 ct, Abweichung 1 ct ≤ 5 → **Lauf läuft**, der Cent geht ins Eigentümer-Residuum und wird protokolliert. Referenzwert ist hier `mdl.gesamtkostenCent`, **nicht** `umlagefaehigCent` — die OCR-Werte sind in diesem Zweig brutto.

| Mieter | brutto | netto |
| --- | --- | --- |
| Muster | 131.874 | **127.217** |
| Schneider | 77.236 | **74.508** |
| Weber | 36.055 | **34.782** |
| Beispiel | 102.029 | **98.426** |

Σ Mieter = 334.933 → Residuum Eigentümer = 338.218 − 334.933 = **3.285** ✓ — identisch zu F01/F28a.

**Rundungshinweis:** die Bruttowerte summieren sich zu 350.599, einen Cent unter der ausgewiesenen Gesamtsumme. Skaliert wird deshalb immer gegen die **ausgewiesene** Summe, und das Residuum kommt aus dem Eigentümer-Bucket — nie aus den Mieterbeträgen.

### 01b-F29 — E28, OCR-Kommafehler, Kontrollsumme blockiert

OCR liest Weber als **3.478 ct** statt 34.782 ct.

Σ = 127.217 + 74.508 + 3.478 + 98.426 + 3.285 = **306.914** gegen 338.218 → **Δ 31.304 ct = 313,04 €** → **Lauf abgelehnt**, Feld Weber markiert.

Die Kontrollsumme ist ein hartes Tor, keine Warnung. Eine um 313 € zu kurze Abrechnung ist formell fehlerhaft und müsste nach Ablauf der § 556-Frist neu erstellt werden.

### 01b-F30 — E29, MDL-Abrechnung ganz ohne CO₂-Angaben

Kein CO₂-Block, keine Brennstoffrechnung verfügbar → Pflichtausweis nach § 7 Abs. 3 CO2KostAufG unmöglich → § 7 Abs. 4, 3 % je Mieter:

| Mieter | Anteil | 3 % Risiko |
| --- | --- | --- |
| Muster | 127.217 | **3.817 = 38,17 €** |
| Schneider | 74.508 | **2.235 = 22,35 €** |
| Weber | 34.782 | **1.043 = 10,43 €** |
| Beispiel | 98.426 | **2.953 = 29,53 €** |
|  |  | **Σ 10.048 = 100,48 €** |

Anzeige vor dem Versand, mit Ein-Klick-Aktion „Nachweis beim Lieferanten anfordern". Kein automatischer Abzug.

### 01b-F31 — E30/E31, § 6a Abs. 3 Nr. 5 Vorjahresvergleich

Objekt-PLZ 50667 (Köln). Verglichen werden **Heiz**einheiten; Warmwasser wird separat und **unbereinigt** ausgewiesen.

Muster: 2025 = 4.100,0 Einheiten · 2024 = 3.900,0 Einheiten

|  | 2024 | 2025 |
| --- | --- | --- |
| erfasste Einheiten (Heizung) | 3.900,0 | 4.100,0 |
| KF (PLZ 50667) | *0,98* | *1,04* |
| bereinigt | **3.822,0** | **4.264,0** |

unbereinigt: 4.100,0 / 3.900,0 − 1 = **+5,1 %** · bereinigt: 4.264,0 / 3.822,0 − 1 = **+11,6 %**

⚠️ Die beiden KF in Kursiv sind **Platzhalter**, keine DWD-Werte. Sie stehen hier für Struktur und Richtung, nicht für Zahlen. Prüfbare Eigenschaften:

1. Beide Jahre werden bereinigt, jedes mit seinem eigenen KF — nie nur das laufende Jahr.
2. Ein milderes Jahr (KF > 1) **erhöht** den bereinigten Wert.
3. Nur der Wärmeverbrauch wird bereinigt; Warmwasser läuft unverändert durch (§ 6a Abs. 3 S. 3).
4. Fehlender KF → Vergleich **unbereinigt** ausgeben plus Hinweis; **niemals** still 1,00 einsetzen.
5. Kein Vorperiodenwert (Einzug im laufenden Jahr, E31) → Hinweistext statt leerer Grafik.
6. Die Ausgabe ist eine **Grafik**, nicht nur eine Prozentzahl.

Referenz-KF aus der echten DWD-Datei `KF_20250101_20251231` (veröffentlicht 16.02.2026), als Import-Testwerte: 01067 Dresden **1,14** · 01099 **1,02** · 01328 **0,98** · 01773 Altenberg **0,83** · 02625 Bautzen **1,05** · 03042 Cottbus **1,12** · 04103 Leipzig **1,15** · 06108 Halle **1,15**. **PLZ stehen in der DWD-Datei ohne führende Null** (`1067` = `01067`) — beim Import auf fünf Stellen auffüllen, sonst fällt die Bereinigung für ganz Ostdeutschland still aus.

---

## 7. Out of Scope

### Owned here — logic that originates on this page and nowhere else

Gesamtkosten der Anlage · CO₂-Stufenermittlung und -Abzug · § 9-Warmwasserabtrennung · 30/70-Blockbildung · Geräteaggregation · Verbrauchsverteilung inkl. § 9a/§ 9b · MDL-Ingest und Kontrollsumme · Klimafaktor-Anwendung.

### Deferred — do not duplicate

| Thema | Eigentümer |
| --- | --- |
| Dokument-Layout, Abschnittsreihenfolge, Pflichthinweise, § 6a Abs. 3 Informationsblock im PDF, Grafik des Vorjahresvergleichs | **Seite 01** |
| BetrKV-Katalog, Default-Umlageschlüssel, nicht umlagefähige Kosten | **Seite 02** |
| UVI-Erzeugung und -Versand (§ 6a Abs. 1–2), Eichfristen, Nachrüstfrist-Wächter | **Seite 05** |
| m²-Tage-Mathematik, Rundungsweg, § 35a | **`docs/03`** |
| OCR-Engine (Modell, Prompts, Feldextraktion, Confidence) | OCR-Spec |
| DWD-Import (Cron, Parser, Tabelle) | `Lokara/Klimafaktoren/DWD-Klimafaktoren-Import-Spec.md` |

### Not covered by this page at all

- **Nachrechnen oder Prüfen einer Messdienst-Abrechnung gegen deren eigene Eingangsdaten.** Lokara ingestiert, validiert die Kontrollsumme und ergänzt die CO₂- und § 6a-Prüfungen, die der Vermieter ohnehin schuldet (K14).
- **Etagenheizung-Erstattungsrechner** (Mieter kauft den Brennstoff selbst, Vermieter erstattet den CO₂-Anteil) — V1 nur Hinweistext.
- **Sanierungs-/Amortisationsrechnung** hinter der Stufenampel („eine Stufe besser ≈ X €/a") — Marketing-Nudge, darf keine Zahl der Abrechnung speisen.
- **Belegeinsicht-Workflow nach BGH VIII ZR 189/17** im Mieterportal, inkl. der Datenschutzfrage beim Anzeigen fremder Verbrauchswerte — Mieterportal-Spec.
- **Prüfung von Montage, Eichung und K-Werten der Geräte.** Lokara verantwortet die Berechnung, nicht die Erfassungstechnik.