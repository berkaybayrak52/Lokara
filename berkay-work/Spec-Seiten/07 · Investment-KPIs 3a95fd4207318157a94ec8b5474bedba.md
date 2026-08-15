# 07 · Investment-KPIs

Blockiert: M10
Emir-Prio: 7
Fixtures: KPI-F01 … KPI-F14
Nr: 07
Optional: No
Phase: 5
Rechtsstand-Einträge: siehe [kanonisches Rechtsstand-Register](../Rechtsstand-Register/Rechtsstand-Register.csv)
Status: Fertig
Termin: 2. August 2026 → 4. August 2026
Ziel-Datei: NEU — Nummer vergibt Emir
Zuletzt bearbeitet von: 29. Juli 2026 13:43

> **Ziel-Datei:** `docs/NEU` — **Nummer vergibt Emir.** Bis dahin Namensraum-Präfix `KPI` (unten). Beim Transkribieren `KPI` global durch die vergebene `docs`-Nummer ersetzen (z. B. `KPI-F01` → `13-F01`).
> 

> **Phase / Termin:** Phase 5 · So 02.–Di 04.08.2026 (M10)
> 

> **Fixtures:** `KPI-F01 … KPI-F14`
> 

> **Braucht vorher:** Seite 03 (AfA — R13-Tupel `jahresAfaVollCent`, `bmgCent`, `afaSatzBp`, `gebaeudeanteilBp`; Annuitäten-Rekurrenz R12 als geteilte Engine) · Seite 02 (nicht umlagefähige Kostenarten — Verwaltung, Instandhaltung, Mietausfallwagnis) · Seite 04 (Export-Architektur „reine Sicht", Datenminimierung 11-K09) · Konzept `Lokara_Investitionsmodul_Demo.html` · `AfA-Wizard_Konzept_Entwurf.md`
> 

> **Blockiert:** nichts weiter unten — Investment-Modul ist Blatt im Baum (Add-on, 4,90 €).
> 

> **DoD:** Ein Referenz-Prüfobjekt rechnet von den Eingaben bis zu allen **7 KPIs** durch — auf den Cent, mit Annuitätenplan Monat für Monat und Summenprobe, steuerabhängige KPIs **vor/nach Steuer**. Ein Teileingabe-Fall zeigt, welche KPIs „—" werden. Der **Bank-PDF-Export** (R9) ist als deterministische Sicht mit LTV, vor/nach-Steuer-Block und Annahmen-Ausweis spezifiziert.
> 

> **Namensräume dieser Seite.** Konventionen `KPI-K01…`, Edge Cases `KPI-E01…`, Rechenschritte `R1–R10`, Fixtures `KPI-F01…`. Kollisionsfrei gegen Seite 01 (unnummeriert), 02 (`09-*`), 03 (`10-*`), 04 (`11-*`).
> 

> Sprache: content in English, wie Seite 01–04. Deutsche Fachbegriffe (Kaltmiete, Bewirtschaftung, Annuität, Grenzsteuersatz, Werbungskosten) und alle im Produkt ausgegebenen Texte bleiben unübersetzt.
> 

> **Ehrlicher Rahmen dieser Seite — zuerst lesen.** Anders als Seite 01–06 berechnet diese Seite **keinen gesetzlich definierten Wert**. Die 7 KPIs sind **Marktkonventionen und Heuristiken**, keine Normen — es gibt kein „richtiges" Faktor- oder EK-Rendite-Verfahren, nur ein gewähltes. Deshalb ist hier **fast alles `[KONVENTION]`** und `verify-before-production` (Abschnitt 2.2). Der einzige normgebundene Teil ist die **Steuer-Teilrechnung** (Steuerbemessung nach § 21/§ 9 EStG), und die rechnet diese Seite **nicht selbst neu** — sie zieht AfA und Zins aus Seite 03. Zweiter ehrlicher Punkt: Das Modul läuft auf **Prüfobjekten** (Kauf noch nicht erfolgt). „Single Source of Truth AfA-Wizard" gilt erst **nach** dem Kauf; in der Ankaufsphase sind die Steuer-Inputs überwiegend **Annahmen** (Abschnitt 3.4 + Offene Frage A).
> 

---

## 1. Zweck

This page turns a **Prüfobjekt** (a property the landlord is *considering* buying, not yet owned) into the **seven decision numbers** the investment cockpit shows: Kaufpreisfaktor, Bruttomietrendite, Nettomietrendite, Eigenkapitalrendite, Cashflow nach Steuer, DSCR und Break-Even-Miete. It fixes each KPI's **exact formula and its tax treatment (vor/nach Steuern)**, the **Annuitätenplan** that feeds Zins und Tilgung, and — the honest core — **which inputs are authoritative from the AfA-Wizard and which are per-Prüfobjekt assumptions**. Every KPI is computable from partial input: what is missing shows `—`, never a fabricated `0` (Konzept: „alle Schritte optional"). Lokara stellt Kennzahlen nebeneinander und markiert je Zeile den besseren Wert — **kein Gesamturteil, keine Kauf-/Anlageempfehlung** (KPI-K11).

Zweites Deliverable dieser Seite: ein **Bank-PDF** — eine deterministische, druckfertige **Finanzierungszusammenfassung des Prüfobjekts** (Objektdaten, Investition, Finanzierung inkl. LTV, Mieten, alle 7 KPIs mit vor/nach-Steuer-Ausweis, Annuitätenplan Jahr 1, offengelegte Annahmen + Methode). Es rechnet **nichts Neues**, sondern ist eine reine Sicht auf den KPI-Stand (KPI-K15) — dieselbe Export-Architektur wie Seite 04. Es ist eine **Selbstauskunft des Vermieters, keine Bewertung und kein Gutachten** (KPI-K14).

---

## 2. Rechtsgrundlage

### 2.1 Normen — nur mittelbar, über die Steuer-Teilrechnung

Diese Seite zitiert Normen ausschließlich, weil Cashflow **nach Steuer**, EK-Rendite und Break-Even eine Steuerbemessung brauchen. Die Werte dafür (AfA, abziehbare Zinsen) kommen fertig aus Seite 03 — hier wird **keine** AfA und **kein** Zinsabzug neu hergeleitet.

| Norm | Warum sie hier auftaucht | Rechtsstand | Rechtsnatur | Quelle |
| --- | --- | --- | --- | --- |
| § 21 EStG | V+V ist reine Überschussrechnung Einnahmen − Werbungskosten → Form der Steuerbemessung in R5 | 07/2026 | Gesetz | [lxgesetze.de/estg/21](http://lxgesetze.de/estg/21) |
| § 9 Abs. 1 S. 3 Nr. 1 + Nr. 7 EStG | Schuldzinsen und AfA senken die Steuerbemessung; **Beträge aus Seite 03 (R12/R13)** | 07/2026 | Gesetz | [lxgesetze.de/estg/9](http://lxgesetze.de/estg/9) |
| § 7 Abs. 4 EStG | linearer AfA-Satz — nur als *Annahme-Default* (2 %), wenn kein AfA-Datensatz verlinkt ist (KPI-K05) | 07/2026 | Gesetz | [lxgesetze.de/estg/7](http://lxgesetze.de/estg/7) |
| §§ 1–5 StBerG | Compliance-Linie: KPIs sind Entscheidungshilfe, **keine Steuerberatung** — kein „so sparen Sie", nur Rechnen | 07/2026 | Gesetz | — |

> **Kein Kapitalmarktrecht.** Das Direktinvestment in eine Immobilie ist **kein Finanzinstrument** i. S. d. WpHG/KWG — die 7 KPIs auszuweisen ist **keine erlaubnispflichtige Anlageberatung** (keine BaFin-Erlaubnis nötig). Trotzdem bleibt das Produkt-Wording bei „Kennzahl/Berechnung", nie bei „Empfehlung/Rendite-Garantie" (KPI-K11). **[UNSICHER: abschließende juristische Bestätigung, dass keine Erlaubnispflicht greift** — vor Launch mit dem Berater gegenprüfen (To-Do 6). Belastbar, aber eine Rechtsfrage, kein Rechenfakt.]
> 

### 2.2 Konventionen — das eigentliche Fundament dieser Seite, alle `verify-before-production`

Jede KPI-Definition ist eine Wahl. Hier stehen die Wahlen offen, statt sie als Wahrheit zu tarnen.

- **[KONVENTION] KPI-K01 — Kaufpreisfaktor auf den *Kaufpreis*, mit *Ist-Jahreskaltmiete*.** `Faktor = Kaufpreis ÷ Jahres-Ist-Kaltmiete`. **Nicht** auf die Gesamtinvestition, **nicht** auf die effektive Miete — „Verkäufer-/Maklersicht", bewusst so, weil der Faktor mit Marktangaben vergleichbar bleiben muss.
- **[KONVENTION] KPI-K02 — Bruttomietrendite = Kehrwert des Faktors.** `Brutto = Jahres-Ist-Kaltmiete ÷ Kaufpreis`. Auf den reinen Kaufpreis. Vor Steuer.
- **[KONVENTION] KPI-K03 — Nettomietrendite auf die *Gesamtinvestition*, nach *voller* Bewirtschaftung, mit *effektiver* Miete.** `Netto = (effektive Jahreskaltmiete − Bewirtschaftung_cash) ÷ Gesamtinvestition`. Unleveraged, vor Steuer, vor Finanzierung.
- **[KONVENTION] KPI-K04 — DSCR auf den Netto-Betriebsertrag (NOI), vor Steuer.** `DSCR = NOI ÷ Jahres-Kapitaldienst`, Kapitaldienst = Zins + Tilgung (volle Annuität). Banken-Kennzahl → **immer vor Steuer**. Zielband 1,20–1,35.
- **[KONVENTION] KPI-K05 — AfA-Default, wenn kein Datensatz verlinkt: Gebäudeanteil 75 %, linear 2 %.** Reine Annahme für die Ankaufsphase. Sobald ein AfA-Datensatz am Objekt hängt, **gewinnt der immer** (K06). Als „Annahme" gekennzeichnet.
- **[KONVENTION] KPI-K06 — AfA-Wizard ist Single Source of Truth, aber nur wenn vorhanden.** Reihenfolge: verlinkter AfA-Datensatz (Seite 03 R13) → sonst Wizard-Schritt-6 → sonst K05-Default. Nie zwei AfA-Werte für dasselbe Objekt.
- **[KONVENTION] KPI-K07 — KPIs rechnen einen *normalisierten 12-Monats-Volljahr*, nicht das Stub-Erstjahr.** `jahresAfaVollCent` (nicht die monatsgenaue Erstjahr-AfA) und die **ersten 12 vollen Darlehensraten**. Bewusster Unterschied zur Steuer-Seite (03/04), die taggenau das reale Jahr rechnet.
- **[KONVENTION] KPI-K08 — Eigenkapitalrendite: vor UND nach Steuer nebeneinander, beide inkl. Tilgungsanteil** *(Frage B entschieden 29.07.2026)*. Zwei Spalten: `EK-Rendite vor Steuer = (Cashflow vor Steuer + Tilgung) ÷ EK` und `nach Steuer = (Cashflow nach Steuer + Tilgung) ÷ EK`. Tilgung bleibt in beiden drin; Cash-on-Cash *ohne* Tilgung (F05 Variante C) ist nur Tooltip. Gilt konsistent auch für **Cashflow** und **Break-Even**.
- **[KONVENTION] KPI-K09 — Steuerbemessung nutzt nur *tatsächlich abzugsfähige* Bewirtschaftung.** Mietausfallwagnis und Instandhaltungs**rücklage** sind kalkulatorisch → mindern **Cashflow**, aber **nicht** die Steuerbemessung. Default-Split: `abzugsfähig = Verwaltung + tatsächliche Instandhaltung`. (Demo-Prototyp zog alles ab — hier bewusst korrigiert → To-Do 2.)
- **[KONVENTION] KPI-K10 — Break-Even hält die Bewirtschaftung absolut konstant.** Beim Auflösen nach der Miete feste Euro-Beträge (nicht %-der-Miete), sonst nichtlinear. Effektive Soll-Kaltmiete der Cashflow-Nulllinie **nach Steuer**.
- **[KONVENTION] KPI-K11 — kein Gesamturteil, keine Empfehlung.** Vergleich markiert je Zeile den besseren Wert (★), nie einen Sieger. Ampel = Abgleich gegen die **selbst gesetzte** Zielrendite. Disclaimer immer sichtbar.
- **[KONVENTION] KPI-K12 — Leerstandsannahme trennt Ist von effektiv.** `effektive Kaltmiete = Ist-Kaltmiete × (1 − Leerstandsquote)`. Faktor/Brutto nutzen **Ist** (K01/K02), Netto/DSCR/Cashflow/Break-Even nutzen **effektiv**. Default 0 %.

### 2.3 Grenzsteuersatz — Annahme, kein ermittelter Wert

- **[KONVENTION] KPI-K13 — Grenzsteuersatz Default 42 %, editierbar.** Lokara **nicht bekannt**, **nicht** aus Einkommen abgeleitet (V1). Editierbarer Regler, Default `4200 Bp`. Soli/Kirchensteuer **nicht** eingerechnet (Non-Goal). Jede steuerabhängige KPI trägt „Annahme Steuersatz X %". → **Offene Frage C.**

### 2.4 Finanzierungsdaten sind in der Ankaufsphase Schätzungen — der ehrliche Kern

- **[KONVENTION] KPI-K16 — Finanzierungs-Inputs sind vor dem Darlehensangebot Annahmen, nicht Fakten.** Zins, Tilgung, Zinsbindung und die EK/Darlehen-Aufteilung kennt der Nutzer erst **nach** Einreichen bei der Bank. Feld `finanzierungQuelle ∈ {annahme, indikativ, angebot}`, Default `annahme`. **Jede finanzierungsabhängige KPI (DSCR, Cashflow, EK-Rendite, Break-Even) trägt das Badge „Finanzierung: Annahme"**. Beruhigend: die 3 Miet-KPIs (Faktor, Brutto, Netto) hängen *nicht* an der Finanzierung. 3 finanzierungsfest, 4 schätzungsabhängig — wird nicht verwischt.
- **[KONVENTION] KPI-K17 — Zins-Sensitivitätstabelle statt Schein-Präzision einer einzelnen Rate.** Weil die Bank ohnehin ihren eigenen Zins ansetzt, rechnet R10 die vier KPIs über ein **Zinsband** (Default −100/−50/0/+50/+100 Bp). Dreht die Schwäche in einen Zinsstress-Test. Im Bank-PDF eigener Block (R9 Block 5b).
- **[KONVENTION] KPI-K18 — Interaktiver Finanzierungs-Regler (Klick auf DSCR), zwei ehrlich getrennte Achsen.** Panel mit zwei Schiebereglern (`Sollzins`, `anf. Tilgungssatz`), rechnet alle vier KPIs **live** (Engine R3→R7; R10 ist der diskrete Fall). **Zins = Stress-Achse** (höher = überall schlechter). **Tilgung = Struktur-Achse, kein Stress** — höhere Tilgung senkt DSCR/Cashflow (Liquidität), erhöht Entschuldung/EK-Rendite (Vermögen); Panel zeigt **beide Seiten gleichzeitig**, sonst framet es eine gute Sache als Verschlechterung. Guard/Clamp am Punkt, wo die Rate die Zinsen nicht deckt (E08). **Scope: Pitch-MVP** (entschieden 29.07.2026).
- **[KONVENTION] KPI-K19 — Live-Farbkodierung von DSCR und Cashflow im Reglermodus.** Beim Schieben wechseln **DSCR und Cashflow live die Farbe**. Schwellen: DSCR rot `< 1,00` · amber `1,00–1,19` · grün `≥ 1,20`; Cashflow n. St./Monat rot `< 0` · amber `0–49,99 €` · grün `≥ 50 €`. Guardrails: (a) Farbe kodiert **nur Liquidität**, kein Gesamturteil, kein Risikomaß — beim Tilgungs-Regler bleibt die Vermögens-Seite sichtbar; (b) gilt „unter Ihren Annahmen", Grün ≠ Bank-Zusage; (c) Schwellen sind Konvention, im Tooltip offengelegt.

### 2.5 Bank-PDF — Konventionen des zweiten Deliverables, alle `verify-before-production`

- **[KONVENTION] KPI-K14 — Bank-PDF ist Selbstauskunft, keine Bewertung.** Trägt sichtbar: „Vom Vermieter erstellte Zusammenfassung auf Basis eigener Angaben und Annahmen. Keine Immobilienbewertung, kein Beleihungswert, kein Gutachten, keine Bonitätsauskunft." **LTV** = `Darlehen ÷ Kaufpreis`, beschriftet als **„Auslauf zum Kaufpreis, nicht zum Beleihungswert"**. **Datenminimierung** wie Seite 04 (11-K09): **keine Mieter-Klarnamen**. KPI-Definitionen/Annahmen (K01–K13) werden mitgedruckt.
- **[KONVENTION] KPI-K15 — Bank-PDF ist reine, deterministische Sicht.** `f(Prüfobjekt-Stand, Layout) → PDF` — keine Neuberechnung. Fehlende KPIs `—` mit Fußnote (R8); ohne Finanzierung weicher Hinweis, kein Block.

---

## 3. Inputs

Geld = **integer Cent**. Sätze/Quoten = **Basispunkte (Bp)**, integer (`4200` = 42,00 %; `390` = 3,90 %) — konsistent mit Seite 03. Datum = taggenau nur für den Annuitätenplan. **Keine Fließkommazahl verlässt diese Seite;** KPI-Ausgaben sind Festkomma (Renditen in Bp, Faktor/DSCR in Hundertstel, Geld in Cent).

### 3.1 Objekt & Kauf (Prüfobjekt-Wizard Schritt 1–2)

| Feld | Typ / Einheit | Quelle |
| --- | --- | --- |
| `kaufpreisCent` | integer > 0 · **Pflicht für Faktor/Brutto** | Wizard (oder AfA-Wizard, wenn verlinkt) |
| `erwerbsnebenkostenCent` | integer ≥ 0 — GrESt (je Bundesland) + Notar/Grundbuch + Makler | Wizard (auto-Vorschlag je Bundesland) |
| `gesamtinvestitionCent` | abgeleitet = `kaufpreisCent + erwerbsnebenkostenCent` | System |
| `bundesland` | enum — steuert GrESt-Satz | Wizard |

### 3.2 Mieten (Wizard Schritt 3)

| Feld | Typ / Einheit | Quelle |
| --- | --- | --- |
| `istKaltmieteMonatCent` | integer ≥ 0 · **Pflicht für Faktor/Brutto** | Wizard |
| `sollMarktmieteMonatCent` | integer ≥ 0 · optionales Szenario | Wizard |
| `stellplatzSonstigesMonatCent` | integer ≥ 0 | Wizard |
| `leerstandBp` | integer 0–10000 · Default `0` (KPI-K12) | Wizard |

### 3.3 Bewirtschaftung, nicht umlagefähig (Wizard Schritt 4 · Kategorien aus Seite 02)

| Feld | Typ / Einheit | Steuer-abzugsfähig? (KPI-K09) |
| --- | --- | --- |
| `verwaltungCentProJahr` | integer ≥ 0 | **ja** |
| `instandhaltungCentProJahr` | integer ≥ 0 — geplante *tatsächliche* Instandhaltung | **ja** |
| `instandhaltungsruecklageCentProJahr` | integer ≥ 0 — kalkulatorische Rücklage | **nein** |
| `mietausfallwagnisCentProJahr` | integer ≥ 0 | **nein** |

> `bewirtschaftungCashCent` = Summe aller vier (mindert Cashflow). `bewirtschaftungAbzugCent` = Verwaltung + Instandhaltung (mindert Steuerbemessung).
> 

### 3.4 Finanzierung (Wizard Schritt 5) — speist den Annuitätenplan R3

| Feld | Typ / Einheit | Quelle |
| --- | --- | --- |
| `eigenkapitalCent` | integer ≥ 0 · **Pflicht für EK-Rendite** | Wizard |
| `darlehenCent` | abgeleitet = `gesamtinvestition − eigenkapital` (auto), überschreibbar | System/Wizard |
| `sollzinsBp` | integer, z. B. `390` | Wizard |
| `anfaenglicheTilgungBp` \ | `annuitaetCentProMonat` | eines von beiden · **Pflicht für DSCR/CF** |
| `zinsbindungJahre` | integer · nur Info V1 | Wizard |
| `finanzierungQuelle` | enum {annahme, indikativ, angebot} · Default `annahme` (KPI-K16) | Wizard/System |

> **Vor dem Darlehensangebot ist dieser ganze Block eine Schätzung** (KPI-K16). Kein Mangel, sondern Realität der Ankaufsphase — die KPIs rechnen damit, kennzeichnen sie als Annahme und stellen die Zins-Sensitivität daneben (K17, R10). Erst bei „Kauf abschließen" bzw. `angebot` werden aus Schätzungen belegte Werte.
> 

> Struktur = Teilmenge von Seite 03 §3.7 (`darlehen[]`), damit die Annuitäten-Rekurrenz identisch ist (K07, R3). Für ein Prüfobjekt gibt es keinen Darlehensvertrag → Wizard-Eingaben; bei „Kauf abschließen" wandern sie in den echten `darlehen[]`-Satz.
> 

### 3.5 Steuer & AfA (Wizard Schritt 6) — Provenienz ist der Kern des dritten Checklistenpunkts

| Feld | Woher (Reihenfolge, KPI-K06) | SSOT? |
| --- | --- | --- |
| `grenzsteuersatzBp` | Wizard-Regler, Default `4200` (KPI-K13) | Annahme |
| `gebaeudeanteilBp` | AfA-Datensatz R13 → sonst Wizard → sonst Default `7500` (K05) | AfA-Wizard, wenn verlinkt |
| `afaSatzBp` | AfA-Datensatz R13 → sonst Wizard → sonst Default `200` (K05) | AfA-Wizard, wenn verlinkt |
| `bmgCent` | AfA-Datensatz R13 → sonst `round_half_up(gesamtinvestition × gebaeudeanteilBp / 10000)` | AfA-Wizard, wenn verlinkt |
| `jahresAfaVollCent` | **AfA-Datensatz R13** → sonst `round_half_up(bmgCent × afaSatzBp / 10000)` | **AfA-Wizard, wenn verlinkt** |
| `zinsJahrCent`, `tilgungJahrCent`, `kapitaldienstCent`, `restschuldEndeCent` | **R3 dieser Seite** (geteilte Engine mit Seite 03 R12) | berechnet |

> **Was aus dem AfA-Wizard kommt (SSOT, *wenn verlinkt*):** `gebaeudeanteilBp`, `afaSatzBp`, `bmgCent`, `jahresAfaVollCent` — plus indirekt `kaufpreisCent`/`erwerbsnebenkostenCent`.
> 

> **Was *je Prüfobjekt* eingegeben wird:** alle Mieten, die vier Bewirtschaftungsposten, die komplette Finanzierung, der Grenzsteuersatz — und in der reinen Ankaufsphase **auch** Gebäudeanteil + AfA-Satz als Annahme.
> 

> **[UNSICHER: wie oft der SSOT-Fall in der Praxis eintritt.** Das Modul verkauft sich über die *Ankaufs*-Phase — dort existiert der AfA-Datensatz meist noch nicht. „Single Source of Truth AfA-Wizard" ist damit eher **Zielbild als Realität**; realistisch rechnen die meisten Prüfobjekte mit dem 75 %/2 %-Default. → **Offene Frage A.**]
> 

### 3.6 Bank-PDF-Kopf (nur für den Export, R9) — alles optional

| Feld | Typ / Einheit | Quelle |
| --- | --- | --- |
| `adresse`, `objekttyp`, `baujahr`, `wohnflaecheM2`, `einheiten` | string/integer · optional | Wizard Schritt 1 |
| `erstellerName` | string · optional — der Vermieter (Kopfzeile) | Account |
| `exportDatum` | date — Erstellungsdatum, gedruckt | System (heute) |
| `pdfLayoutVersion` | string — versionierte Vorlage | rules-store |

> Keine dieser Angaben beeinflusst eine KPI — sie füllen nur den PDF-Kopf. Fehlen sie, bleibt das Feld im PDF leer.
> 

---

## 4. Formel

Rundungsregel global: alle Geldbeträge sind **integer Cent**; Zwischensummen sind **exakte Integer-Addition, keine Rundung**. `round_half_up` **genau dort**, wo eine Multiplikation/Division einen Bruchteil erzeugt — jede Stelle unten markiert. KPI-Ausgaben: Renditen `round_half_up(zaehler × 10000 / nenner)` in Bp, Verhältnisse `round_half_up(zaehler × 100 / nenner)` in Hundertstel, Geld auf ganze Cent. Alle KPIs sind **reine Funktion** `f(Eingaben) → Zahl`.

**R1 — Effektive Jahreskaltmiete (Leerstand, KPI-K12).**

```
jahresIstKaltmiete   = istKaltmieteMonatCent × 12                     // exakt
effektiveJahresmiete = round_half_up(jahresIstKaltmiete × (10000 − leerstandBp) / 10000)
```

Stellplatz/Sonstiges nicht in die Miet-KPIs (Non-Goal N5); nur Kaltmiete zählt.

**R2 — Netto-Betriebsertrag (NOI).**

```
bewirtschaftungCash = verwaltung + instandhaltung + instandhaltungsruecklage + mietausfallwagnis   // exakt
bewirtschaftungAbzug = verwaltung + instandhaltung                                                  // exakt (K09)
NOI = effektiveJahresmiete − bewirtschaftungCash                     // exakt; darf negativ sein
```

**R3 — Annuitätenplan (KPI-K07, geteilte Rekurrenz mit Seite 03 R12).** Erste **12 volle Raten** ab `restschuld = darlehenCent`.

```
annuitaetMonat = annuitaetCentProMonat
                 ?? round_half_up( darlehenCent × (sollzinsBp + anfaenglicheTilgungBp) / 10000 / 12 )
restschuld = darlehenCent ; zinsJahr = 0 ; tilgungJahr = 0
für Monat m = 1..12:
    zinsMonat  = round_half_up(restschuld × sollzinsBp / 120000)      // 30/360, ein round pro Monat
    tilgung    = annuitaetMonat − zinsMonat
    restschuld = restschuld − tilgung
    zinsJahr  += zinsMonat ; tilgungJahr += tilgung
kapitaldienstCent = annuitaetMonat × 12 ; restschuldEndeCent = restschuld
Guard: tilgung <= 0 in irgendeinem Monat → HARD BLOCK (KPI-E08)
Probe: zinsJahr + tilgungJahr == kapitaldienstCent
kein Darlehen (darlehenCent == 0): annuitaetMonat = zinsJahr = tilgungJahr = kapitaldienstCent = 0
```

**R4 — AfA-Bezug (KPI-K06).** `jahresAfaVollCent` nach Reihenfolge R13 → Wizard → Default; wenn abgeleitet:

```
bmgCent          = round_half_up(gesamtinvestitionCent × gebaeudeanteilBp / 10000)   // nur wenn kein R13
jahresAfaVollCent = round_half_up(bmgCent × afaSatzBp / 10000)                        // nur wenn kein R13
```

**R5 — Steuerbemessung & Steuer (§ 21/§ 9 EStG, KPI-K09).**

```
steuerBemessungCent = effektiveJahresmiete − bewirtschaftungAbzug − zinsJahr − jahresAfaVollCent   // exakt; darf negativ sein
steuerCent = round_half_up(steuerBemessungCent × grenzsteuersatzBp / 10000)          // ein round; negativ = Verlustverrechnung
```

**R6 — Cashflow.**

```
cashflowVorSteuerJahr  = effektiveJahresmiete − bewirtschaftungCash − kapitaldienstCent   // exakt
cashflowNachSteuerJahr = cashflowVorSteuerJahr − steuerCent                               // exakt
cashflowNachSteuerMonat = round_half_up(cashflowNachSteuerJahr / 12)                      // Anzeige, ein round
```

**R7 — Die 7 KPIs.**

```
1  Kaufpreisfaktor      faktorHundertstel = round_half_up(kaufpreisCent × 100 / jahresIstKaltmiete)          // steuerneutral · K01
2  Bruttomietrendite    bruttoBp = round_half_up(jahresIstKaltmiete × 10000 / kaufpreisCent)                 // vor Steuer · K02
3  Nettomietrendite     nettoBp  = round_half_up(NOI × 10000 / gesamtinvestitionCent)                        // vor Steuer · K03
4  DSCR                 dscrHundertstel = round_half_up(NOI × 100 / kapitaldienstCent)                       // vor Steuer · K04
5  Eigenkapitalrendite  ekrVorBp  = round_half_up((cashflowVorSteuerJahr  + tilgungJahr) × 10000 / eigenkapitalCent)   // VOR  Steuer, inkl. Tilgung · K08
                        ekrNachBp = round_half_up((cashflowNachSteuerJahr + tilgungJahr) × 10000 / eigenkapitalCent)   // NACH Steuer, inkl. Tilgung · K08
6  Cashflow             cashflowVorSteuerMonat  = round_half_up(cashflowVorSteuerJahr  / 12)                  // VOR  Steuer
                        cashflowNachSteuerMonat = round_half_up(cashflowNachSteuerJahr / 12)                  // NACH Steuer (R6)
7  Break-Even-Miete
   nach Steuer:  breakEvenNachJahr = round_half_up( (bewirtschaftungCash + kapitaldienstCent
                        − round_half_up(grenzsteuersatzBp × (bewirtschaftungAbzug + zinsJahr + jahresAfaVollCent) / 10000))
                        × 10000 / (10000 − grenzsteuersatzBp) )                                               // K10
   vor Steuer:   breakEvenVorJahr  = bewirtschaftungCash + kapitaldienstCent                                 // Cashflow-vor-Steuer = 0
                 breakEvenNachMonat = round_half_up(breakEvenNachJahr / 12) ; breakEvenVorMonat = round_half_up(breakEvenVorJahr / 12)
```

> Die vier steuerneutralen/Vor-Steuer-KPIs (1–4) haben nur *einen* Wert. Nur die drei steuerabhängigen (5 EK-Rendite, 6 Cashflow, 7 Break-Even) werden **zweispaltig vor/nach Steuer** ausgewiesen (K08). Cash-on-Cash (ohne Tilgung) ist optionales Tooltip.
> 

**R9 — Bank-PDF-Aufbau (KPI-K14/K15).** Reine Funktion, keine Neuberechnung.

```
LTV / Auslauf:  ltvKaufpreisBp = round_half_up(darlehenCent × 10000 / kaufpreisCent)       // „zum Kaufpreis, nicht Beleihungswert"
                ltvGesamtBp    = round_half_up(darlehenCent × 10000 / gesamtinvestitionCent)
darlehenCent == 0 → LTV = „—", weicher Hinweis (K15)
PDF-Blöcke, feste Reihenfolge:
  1 Kopf         adresse/objekttyp/baujahr/fläche/einheiten · erstellerName · exportDatum · Disclaimer (K14)
  2 Investition  kaufpreis · erwerbsnebenkosten (aufgeschlüsselt) · gesamtinvestition
  3 Finanzierung eigenkapital · darlehen · ltvKaufpreis · ltvGesamt · sollzins · tilgung · kapitaldienst/Monat · zinsbindung
  4 Mieten/Bew.  ist-/soll-Kaltmiete · leerstandsannahme · Bewirtschaftung (4 Posten, aggregiert, keine Mieternamen · K14)
  5 KPI-Block    KPI 1–4 (ein Wert) · KPI 5–7 zweispaltig vor/nach Steuer (K08) · Badge „Finanzierung: Annahme" (K16)
  5b Zins-Sensitivität  R10-Tabelle (5 Zinsstufen) für DSCR/Cashflow/EK-Rendite/Break-Even (K17)
  6 Annuitätsplan  Jahr-1-Tabelle aus R3 (12 Zeilen)
  7 Annahmen/Methode  Steuersatz · AfA-Quelle (Wizard vs. Annahme 75%/2%) · Leerstand · Kurzdefinition K01–K13
  8 Disclaimer   K14-Volltext + „beruht auf Ihren Annahmen, ersetzt keine Beratung"
fehlende KPI → „—" mit Fußnote (R8); PDF bleibt erzeugbar
```

**R10 — Zins-Sensitivitäts-Sweep (KPI-K17).** Reine Wiederholung R3→R5→R6→R7 je Zinsstufe; nur ein Parameter variiert.

```
band = { sollzinsBp−100, −50, 0, +50, +100 }   // Default; Stufen konfigurierbar
je zinsStufe: annuität/Zins/Tilgung/Kapitaldienst neu aus R3, dann Steuer/Cashflow/KPIs
Ausgabe: 5 Zeilen; Zeile z == sollzinsBp = hervorgehobene Punkt-Schätzung
Faktor/Brutto/Netto konstant über alle Zeilen → nicht wiederholt
Zweite Achse (Tilgung, K18): identische Engine mit variablem tilgungBp bei konstantem Zins;
  zusätzlich restschuldEndeCent (Entschuldung), damit der Trade-off ehrlich sichtbar ist.
  Der interaktive Regler ist der stufenlose Fall über (zins, tilgung); Guard E08 klemmt.
```

Herleitung Break-Even (R7·7): Cashflow nach Steuer = 0 nach `R` aufgelöst — `R(1−s) = B_c + KD − s·(B_d + Zins + AfA)`, `s = grenzsteuersatzBp/10000`. Effektive Soll-Kaltmiete; bei Leerstand > 0 muss die nominale Miete höher liegen.

**R8 — Vollständigkeits-Gate.** Fehlt ein Pflicht-Input → KPI = `—`, Badge „Daten unvollständig". Nie `0` erfinden.

| KPI | braucht mindestens |
| --- | --- |
| Kaufpreisfaktor / Bruttomietrendite | `kaufpreisCent`, `istKaltmieteMonatCent` |
| Nettomietrendite |   • `erwerbsnebenkostenCent`, Bewirtschaftung |
| DSCR |   • Finanzierung (Darlehen, Zins, Tilgung) |
| Cashflow n. St. |   • Finanzierung + Bewirtschaftung + Steuersatz + AfA-Basis |
| EK-Rendite |   • `eigenkapitalCent`  • alles von Cashflow |
| Break-Even-Miete |   • Bewirtschaftung + Finanzierung + Steuersatz + AfA-Basis |

---

## 5. Edge Cases

| ID | Fall | Verhalten | Fixture |
| --- | --- | --- | --- |
| **KPI-E01** | Nur Kaufpreis + Miete (Teileingabe) | Faktor + Brutto rechnen; Rest `—`; Badge „Daten unvollständig" | KPI-F06 |
| **KPI-E02** | `kaufpreisCent == 0` oder `istKaltmiete == 0`/null | Faktor + Brutto = `—` (Division), keine `0`, kein Absturz | — (Regel) |
| **KPI-E03** | Kein Darlehen (100 % EK) | `kapitaldienst=zins=tilgung=0`; **DSCR = `n/a (kein Fremdkapital)`**; EK = Gesamtinvestition; Rest rechnet | KPI-F04 |
| **KPI-E04** | Negativer Cashflow / NOI negativ | **gültig**, rot dargestellt; Steuer darf negativ (Verlustverrechnung) sein | KPI-F10 |
| **KPI-E05** | Leerstandsquote > 0 | effektive Miete in Netto/DSCR/CF/BE; Faktor/Brutto bleiben Ist | KPI-F07 |
| **KPI-E06** | AfA-Datensatz verlinkt vs. Annahme | R13-Wert gewinnt (K06); Badge „AfA aus Wizard"; Zahlen unterscheiden sich | KPI-F08 |
| **KPI-E07** | Annuität als fester Monatsbetrag | R3 nimmt `annuitaetCentProMonat` direkt | KPI-F03 |
| **KPI-E08** | Rate deckt Zins nicht (`tilgung ≤ 0`) | **HARD BLOCK** wie Seite 03 R12 | KPI-F09 |
| **KPI-E09** | Grenzsteuersatz = 0 % | steuerCent = 0; CF n. St. = CF v. St.; Break-Even-Nenner (1−s)=1 | — (Regel) |
| **KPI-E10** | „Zeitraum ≠ 12 Monate" | **entfällt by design**: KPIs immer normalisiertes Volljahr (K07). Ausdrücklich | — |
| **KPI-E11** | Erwerbsnebenkosten unrealistisch | Warnung im Wizard, **kein Block** | — (Regel) |
| **KPI-E12** | Bank-PDF bei Teileingabe / ohne Finanzierung | PDF erzeugbar; fehlende KPIs `—`; ohne Darlehen LTV/DSCR/CF `—`  • Hinweis (K15) | KPI-F12 |
| **KPI-E13** | LTV als Beleihungswert missverstanden | PDF beschriftet LTV fest „Auslauf zum **Kaufpreis**"; kein Beleihungswert (K14) | KPI-F12 |
| **KPI-E14** | Finanzierung ist Schätzung (kein Bankangebot) | KPIs rechnen, Badge „Finanzierung: Annahme" (K16); Zins-Sensitivität daneben; kein Block | KPI-F13 |
| **KPI-E15** | Regler fährt Tilgung zu niedrig / Zins zu hoch | Panel **klemmt** am Guard (E08), Guard-Text statt negativer Tilgung | KPI-F14 |

---

## 6. BEISPIELRECHNUNG

> Alle Zwischenschritte sichtbar, Ergebnis auf den Cent. Referenz-Prüfobjekt **„MFH Musterstraße"** ist gemeinsame Basis von KPI-F01–F14.
> 

**Referenz-Prüfobjekt (Eingaben KPI-F01):** `kaufpreisCent = 42.000.000` (420.000,00 €) · Erwerbsnebenkosten GrESt NRW 6,5 % = 2.730.000 + Notar/Grundbuch 1,5 % = 630.000 → `erwerbsnebenkostenCent = 3.360.000` → `gesamtinvestitionCent = 45.360.000` (453.600,00 €). `istKaltmieteMonatCent = 265.000` (2.650,00 €) · `leerstandBp = 0`. Bewirtschaftung/Jahr: Verwaltung 360.000, Instandhaltung 300.000, Rücklage 0, Wagnis 63.600 → `bewirtschaftungCash = 723.600`, `bewirtschaftungAbzug = 660.000`. Finanzierung: `eigenkapital = 11.360.000` → `darlehen = 34.000.000` (340.000,00 €), `sollzinsBp = 390`, `anfaenglicheTilgungBp = 200`. Steuer: `grenzsteuersatzBp = 4200`, kein AfA-Datensatz → Annahme `gebaeudeanteilBp = 7500`, `afaSatzBp = 200`.

### KPI-F02 — R3 Annuitätenplan (Tilgungssatz-Verzweigung), Darlehen 340.000,00 €

`annuitaetMonat = round_half_up(34.000.000 × 590 / 120000) = round_half_up(167.166,67) = 167.167` (1.671,67 €).

| m | Restschuld vorher | Zins | Tilgung | Restschuld nachher |
| --- | --- | --- | --- | --- |
| 1 | 34.000.000 | 110.500 | 56.667 | 33.943.333 |
| 2 | 33.943.333 | 110.316 | 56.851 | 33.886.482 |
| 3 | 33.886.482 | 110.131 | 57.036 | 33.829.446 |
| 4 | 33.829.446 | 109.946 | 57.221 | 33.772.225 |
| 5 | 33.772.225 | 109.760 | 57.407 | 33.714.818 |
| 6 | 33.714.818 | 109.573 | 57.594 | 33.657.224 |
| 7 | 33.657.224 | 109.386 | 57.781 | 33.599.443 |
| 8 | 33.599.443 | 109.198 | 57.969 | 33.541.474 |
| 9 | 33.541.474 | 109.010 | 58.157 | 33.483.317 |
| 10 | 33.483.317 | 108.821 | 58.346 | 33.424.971 |
| 11 | 33.424.971 | 108.631 | 58.536 | 33.366.435 |
| 12 | 33.366.435 | 108.441 | 58.726 | 33.307.709 |

`zinsJahr = 1.313.713` · `tilgungJahr = 2.006.004 − 1.313.713 = 692.291` · `kapitaldienst = 2.006.004` · `restschuldEnde = 33.307.709`. **Probe:** 1.313.713 + 692.291 = 2.006.004 = 12 × 167.167 ✓ · Restschuld: 34.000.000 − 692.291 = 33.307.709 ✓

*Hinweis:* Kapitaldienst 20.060,04 € liegt 4 ct über der Nominal-Annuität — Folge der monatlichen Rundung (K07: Rate zuerst runden, dann 12×).

### KPI-F01 — alle 7 KPIs, Referenz-Prüfobjekt

Vorwerte: `jahresIstKaltmiete = 3.180.000` · `effektiveJahresmiete = 3.180.000` · `NOI = 3.180.000 − 723.600 = 2.456.400` · aus F02: zinsJahr 1.313.713, tilgungJahr 692.291, kapitaldienst 2.006.004. AfA (R4): `bmg = round_half_up(45.360.000 × 7500/10000) = 34.020.000`, `jahresAfaVoll = round_half_up(34.020.000 × 200/10000) = 680.400`.

Steuer (R5): `steuerBemessung = 3.180.000 − 660.000 − 1.313.713 − 680.400 = 525.887` · `steuer = round_half_up(525.887 × 0,42) = 220.873` (2.208,73 €). Cashflow (R6): `vorSteuer = 450.396` · `nachSteuer = 450.396 − 220.873 = 229.523` · `Monat = 19.127` (191,27 €).

| # | KPI | Rechnung | Ergebnis | vor/nach Steuer |
| --- | --- | --- | --- | --- |
| 1 | Kaufpreisfaktor | `round_half_up(42.000.000×100 / 3.180.000)=1.321` | **13,21** | neutral |
| 2 | Bruttomietrendite | `round_half_up(3.180.000×10000 / 42.000.000)=757` | **7,57 %** | vor |
| 3 | Nettomietrendite | `round_half_up(2.456.400×10000 / 45.360.000)=542` | **5,42 %** | vor |
| 4 | DSCR | `round_half_up(2.456.400×100 / 2.006.004)=122` | **1,22** | vor |
| 5 | Eigenkapitalrendite | nach: `(229.523+692.291)×10000/11.360.000=811` · vor: `(450.396+692.291)×10000/11.360.000=1.006` | **vor 10,06 % / nach 8,11 %** | zweispaltig, inkl. Tilgung |
| 6 | Cashflow | vor: `450.396/12=37.533` · nach: `229.523/12=19.127` | **vor +375,33 / nach +191,27 €/Mon** | zweispaltig |
| 7 | Break-Even-Miete | nach: `232.023` · vor: `(723.600+2.006.004)/12=227.467` | **vor 2.274,67 / nach 2.320,23 €/Mon** | zweispaltig |

Break-Even (R7·7): `s-Term = round_half_up(4200 × 2.654.113/10000) = 1.114.727` · `Zaehler = 2.729.604 − 1.114.727 = 1.614.877` · `breakEvenJahr = round_half_up(1.614.877×10000/5800) = 2.784.271` · `breakEvenMonat = 232.023` (2.320,23 €).

**Konsistenzprobe:** Ist-Miete 3.180.000 − 2.784.271 = 395.729 über Break-Even; Nach-Steuer-Überschuss = round_half_up(395.729 × 0,58) = 229.523 = Cashflow nach Steuer ✓ (verbindet KPI 6 und 7). Break-Even **vor** Steuer = 723.600 + 2.006.004 = 2.729.604/Jahr → 227.467 (2.274,67 €). Ehrlicher Hinweis: die Nach-Steuer-Nulllinie liegt **über** der Vor-Steuer-Nulllinie — an der Vor-Steuer-Grenze fällt noch Steuer an.

### KPI-F03 — R3 mit festem Monatsbetrag (KPI-E07), `annuitaetCentProMonat = 180.000`

`zinsJahr = 1.310.929` · `tilgungJahr = 2.160.000 − 1.310.929 = 849.071` · `restschuldEnde = 33.150.929`. **Probe:** 1.310.929 + 849.071 = 2.160.000 = 12×180.000 ✓. Höhere Rate → mehr Tilgung, weniger Restschuld; DSCR sinkt (Kapitaldienst 2.160.000 > 2.006.004).

### KPI-F04 — 100 % Eigenkapital (KPI-E03), `eigenkapital = 45.360.000`, `darlehen = 0`

`kapitaldienst = zins = tilgung = 0`. **DSCR = `n/a (kein Fremdkapital)`**. Steuer: `bemessung = 3.180.000 − 660.000 − 680.400 = 1.839.600` · `steuer = 772.632`. Cashflow: `vorSteuer = 2.456.400` · `nachSteuer = 1.683.768` · `Monat = 140.314` (1.403,14 €). EK-Rendite `= round_half_up(1.683.768×10000/45.360.000) = 371` → **3,71 %**. Break-Even `= round_half_up((723.600 − round_half_up(4200×1.340.400/10000))×10000/5800) = round_half_up(160.632×10000/5800) = 276.952`/Jahr → **230,79 €/Mon**.

**Lehrpunkt:** unhebeliert 3,71 % vs. 8,11 % mit 75 % Fremdkapital (F01) — der Leverage-Effekt sichtbar gemacht.

### KPI-F05 — EK-Rendite: die zwei ausgewiesenen Spalten + Tooltip (KPI-K08, Frage B entschieden 29.07.2026)

| Ausweis | Rechnung | Ergebnis |
| --- | --- | --- |
| **Spalte 1 — vor Steuer, inkl. Tilgung** | `(450.396 + 692.291)/11.360.000` → `round_half_up(1.005,88)` | **10,06 %** |
| **Spalte 2 — nach Steuer, inkl. Tilgung** | `(229.523 + 692.291)/11.360.000` → `round_half_up(811,46)` | **8,11 %** |
| Tooltip — Cash-on-Cash (nach Steuer, *ohne* Tilgung) | `229.523/11.360.000` → `round_half_up(202,04)` | 2,02 % |

Beide Steuer-Spalten stehen nebeneinander; die 2,02 % nur im Tooltip. Spannweite bewusst offengelegt — die Auflösung von Frage B.

### KPI-F06 — Teileingabe (KPI-E01), nur `kaufpreis` + `istKaltmiete`

`kaufpreis 31.000.000`, `istKaltmiete 115.000`. `jahresIstKaltmiete = 1.380.000`. Faktor `= round_half_up(31.000.000×100/1.380.000) = 2.246` → **22,46**. Brutto `= round_half_up(1.380.000×10000/31.000.000) = 445` → **4,45 %**. Netto = DSCR = EK-Rendite = Cashflow = Break-Even = **`—`** (R8). Badge „Daten unvollständig". Keine `0`.

### KPI-F07 — Leerstand 5 % (KPI-E05), sonst wie F01

`leerstandBp = 500` → `effektiveJahresmiete = round_half_up(3.180.000×9500/10000) = 3.021.000`. Faktor/Brutto **unverändert** (Ist-Basis) 13,21 / 7,57 %. `NOI = 2.297.400`. Netto `= 506` → **5,06 %**. DSCR `= round_half_up(2.297.400×100/2.006.004) = 115` → **1,15**. Steuer: `bemessung = 366.887` · `steuer = 154.093`. Cashflow: `vorSteuer = 291.396` · `nachSteuer = 137.303` · `Monat = 11.442` (114,42 €). EK-Rendite `= round_half_up((137.303+692.291)×10000/11.360.000) = 730` → **7,30 %**. Break-Even **2.320,23 €/Mon** (unverändert — die Nulllinie fragt „welche Miete wird gebraucht"; bei 5 % Leerstand muss die nominale Soll-Miete höher sein, K12).

### KPI-F08 — AfA aus Wizard statt Annahme (KPI-E06 / K06), sonst wie F01

Verlinkter AfA-Datensatz `jahresAfaVollCent = 512.000` (z. B. Gebäudeanteil 62 %). Gewinnt gegen Default 680.400. `steuerBemessung = 3.180.000 − 660.000 − 1.313.713 − 512.000 = 694.287` · `steuer = 291.601`. Cashflow `vorSteuer 450.396` (AfA nicht zahlungswirksam) · `nachSteuer = 158.795` · `Monat = 13.233` (132,33 €). EK-Rendite `= round_half_up((158.795+692.291)×10000/11.360.000) = 749` → **7,49 %** (vs. 8,11 % bei Annahme). **Ehrlicher Punkt:** niedrigere AfA senkt den Steuer-Shield → weniger Cashflow. Badge „AfA aus Wizard".

### KPI-F09 — Guard: Rate deckt Zins nicht (KPI-E08)

Darlehen 34.000.000, `sollzinsBp = 390`, `annuitaetCentProMonat = 100.000`. Monat 1: `zinsMonat = 110.500` > Rate 100.000 → `tilgung = −10.500 ≤ 0`. → **HARD BLOCK**: „Ihre monatliche Rate (1.000,00 €) deckt die Zinsen (1.105,00 €) nicht. Erhöhen Sie Rate oder Tilgungssatz." (identische Guard-Logik Seite 03 R12).

### KPI-F10 — Negativer Cashflow (KPI-E04), „grenzwertiges" Objekt

`kaufpreis 14.900.000`, NK 12,1 % = 1.802.900 → `gesamt 16.702.900`; `istKaltmiete 62.000` → `jahresIst 744.000`; Bewirtschaftung Verwaltung 30.000, Instandhaltung 30.000, Wagnis 14.880 → `cash 74.880`, `abzug 60.000`; `eigenkapital 4.000.000`, `darlehen 12.702.900`, `sollzinsBp 380`, `tilgungBp 200`; AfA `bmg = 12.527.175`, `afaVoll = 250.544`; `s = 4200`. Annuität `annuitaetMonat = round_half_up(12.702.900×580/120000) = 61.397`; 12-Monats-Rekurrenz: `zinsJahr = 478.240`, `tilgungJahr = 258.524`, `kapitaldienst = 736.764`. `NOI = 744.000 − 74.880 = 669.120`. Netto `= 401` → **4,01 %**. DSCR `= round_half_up(669.120×100/736.764) = 91` → **0,91**. Steuer: `bemessung = −44.784` · `steuer = round_half_up(−44.784×0,42) = −18.809` (Verlust → Erstattung, E04/E09). Cashflow: `vorSteuer = −67.644` · `nachSteuer = −48.835` · `Monat = −4.070` → **−40,70 €/Mon** (rot, gültig). EK-Rendite `= round_half_up((−48.835+258.524)×10000/4.000.000) = 524` → **5,24 %** (positiv **trotz** negativem Cashflow — der Tilgungsanteil trägt sie; Grund, warum K08 offengelegt wird). Break-Even `= round_half_up((811.644 − 331.289)×10000/5800) = 828.198`/Jahr → **690,17 €/Mon** > Ist 620,00 € → Cashflow negativ ✓.

### KPI-F11 — Summenprobe der Miet-KPIs (Kehrwert-Konsistenz)

`faktorHundertstel × bruttoBp = 1321 × 757 = 999.997 ≈ 1.000.000` (= 100 × 10000). Rundungsdrift 3 Millionstel — Cross-Check, dass beide auf derselben Ist-Miete/demselben Kaufpreis rechnen. Keine eigenständige KPI.

### KPI-F12 — Bank-PDF: LTV + vor/nach-Steuer-Block (R9, KPI-E12/E13)

LTV: `ltvKaufpreis = round_half_up(34.000.000×10000/42.000.000) = 8.095` → **80,95 %** („Auslauf zum Kaufpreis, nicht Beleihungswert"). `ltvGesamt = round_half_up(34.000.000×10000/45.360.000) = 7.496` → **74,96 %**.

| KPI | vor Steuer | nach Steuer |
| --- | --- | --- |
| Kaufpreisfaktor | 13,21 | *(steuerneutral)* |
| Bruttomietrendite | 7,57 % | *(vor)* |
| Nettomietrendite | 5,42 % | *(vor)* |
| DSCR | 1,22 | *(vor, Bankkennzahl)* |
| Eigenkapitalrendite | 10,06 % | 8,11 % |
| Cashflow/Monat | +375,33 € | +191,27 € |
| Break-Even-Miete/Monat | 2.274,67 € | 2.320,23 € |

Block 6 = Annuitätsplan aus F02. Block 7 druckt: „Steuersatz 42 % (Annahme) · AfA-Annahme 75 %/2 % · Leerstand 0 % · EK-Rendite inkl. Tilgung · **Finanzierung: Annahme (noch kein Bankangebot)**". Block 8 = Disclaimer K14. **Teileingabe (E12):** ohne Finanzierung → LTV/DSCR/Cashflow/EK-Rendite/Break-Even = `—`, PDF erzeugbar mit Hinweis. Keine Mieternamen (K14).

### KPI-F13 — Zins-Sensitivitätstabelle (R10, KPI-K17/E14), Tilgungssatz 2,0 % konstant

Jede Zeile ein vollständiger R3→R7-Durchlauf; Basiszeile 3,9 % = KPI-F01 ✓.

| Sollzins | annuität/Mon | Kapitaldienst/Jahr | Zins J1 | Tilgung J1 | DSCR | Cashflow [n.St](http://n.St)./Mon | EK-Rendite vor/nach | Break-Even [n.St](http://n.St)./Mon |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2,90 % | 138.833 | 1.665.996 | 976.889 | 689.107 | **1,47** | +356,72 € | 13,02 / 9,83 % | 2.034,96 € |
| 3,40 % | 153.000 | 1.836.000 | 1.145.302 | 690.698 | **1,34** | +274,00 € | 11,54 / 8,97 % | 2.177,59 € |
| **3,90 % (Annahme)** | **167.167** | **2.006.004** | **1.313.713** | **692.291** | **1,22** | **+191,27 €** | **10,06 / 8,11 %** | **2.320,23 €** |
| 4,40 % | 181.333 | 2.175.996 | 1.482.118 | 693.878 | **1,13** | +108,55 € | 8,58 / 7,25 % | 2.462,84 € |
| 4,90 % | 195.500 | 2.346.000 | 1.650.518 | 695.482 | **1,05** | +25,82 € | 7,09 / 6,39 % | 2.605,48 € |

Lesart fürs Bank-PDF: **selbst bei +100 Bp Zinsstress (4,90 %) bleibt DSCR ≥ 1,05 und der Cashflow positiv**. Faktor 13,21 / Brutto 7,57 % / Netto 5,42 % konstant (finanzierungsfest, K16). Live-Farbe (K19): DSCR 2,9–3,9 % grün, 4,4 %+4,9 % amber; Cashflow bis 4,4 % grün, 4,9 % amber (Puffer < 50 €).

### KPI-F14 — Tilgungs-Achse des Reglers (R10 / KPI-K18), Sollzins 3,9 % konstant

Der Beweis, warum Tilgung **kein** Stress-Parameter ist: nur `tilgungBp` variiert. Liquidität fällt, Vermögen steigt.

| anf. Tilgung | annuität/Mon | Kapitaldienst/Jahr | DSCR ↓ | Cashflow [n.St](http://n.St)./Mon ↓ | **Restschuld Ende J1** ↓ | **EK-Rendite [n.St](http://n.St).** ↑ |
| --- | --- | --- | --- | --- | --- | --- |
| 1,0 % | 138.833 | 1.665.996 | 1,47 | +476,76 € | 33.653.861 | 8,08 % |
| **2,0 % (Annahme)** | **167.167** | **2.006.004** | **1,22** | **+191,27 €** | **33.307.709** | **8,11 %** |
| 3,0 % | 195.500 | 2.346.000 | 1,05 | −94,21 € | 32.961.570 | 8,15 % |
| 4,0 % | 223.833 | 2.685.996 | 0,91 | −379,69 € | 32.615.428 | 8,18 % |

**Ehrlicher Hinweis (Pflicht-Text im Panel):** Von 1 % auf 4 % Tilgung fällt DSCR 1,47 → 0,91 und der Cashflow dreht ins Minus — **aber** die Restschuld sinkt nach einem Jahr um 1.038.433 ct mehr und die EK-Rendite steigt leicht. Liquiditäts-gegen-Vermögens-Trade-off, **kein Risikoanstieg.** EK-Rendite bewegt sich kaum (8,08→8,18 %), weil sie die Tilgung als Vermögensaufbau enthält (K08). **Clamp (E15):** ein Regler-Wert mit `annuität < erster Zins` klemmt am Guard-Punkt (Text aus F09). Live-Farbe (K19): DSCR 1,0 %+2,0 % grün, 3,0 % amber, 4,0 % rot; Cashflow ab 3,0 % rot. **Guardrail:** DSCR/Cashflow werden rot, während Restschuld/EK-Rendite besser werden — deshalb steht die Vermögens-Spalte im selben Panel. Rot beim Tilgungs-Regler = „weniger Spielraum", nicht „riskanter"; beim Zins-Regler = echte Verschlechterung.

---

## 7. Out of Scope

- **Wertsteigerung / Verkaufsszenario / IRR / Vermögensmehrung über die Haltedauer.** V1 ist eine **Ein-Jahres-Momentaufnahme**, keine mehrjährige Projektion, kein Exit. → N1.
- **Die AfA-Herleitung selbst** (Kaufpreisaufteilung, Satz, BMG, 15 %-Wächter) — vollständig auf **Seite 03**. Diese Seite **konsumiert** nur `jahresAfaVollCent`.
- **Der Steuer-Export / Anlage V / DATEV** — Seite 04. Die KPI-Steuer ist *interne Schätzung* fürs Cockpit, **kein** Wert für die Steuererklärung.
- **Restschuld-/Tilgungsverlauf über die Zinsbindung hinaus, Anschlussfinanzierung, variable Zinsen, Forward-Darlehen.** R3 rechnet die ersten 12 Raten; alles darüber V2.
- **Soli, Kirchensteuer, progressiver Effekt aufs zvE, Verlustverrechnungsbeschränkungen.** V1 nutzt einen flachen Grenzsteuersatz (K13).
- **Stellplatz-/Sonstige-Einnahmen in den Miet-KPIs**, gewerbliche Einheiten mit USt, Sanierungs-/Neubau-Kalkulation vor Kauf. → Non-Goals.
- **Kauf-/Nicht-Kauf-Empfehlung, Zielrenditen-Vorgabe, Ranking.** Lokara rechnet und stellt nebeneinander (K11).
- **Bank-PDF ist keine Bewertung.** Kein Beleihungswert, kein Verkehrswert, keine Bonitätsauskunft im bankregulatorischen Sinn, kein Gutachten. LTV = `Darlehen ÷ Kaufpreis`, nicht `÷ Beleihungswert` (K14). Zuarbeit, kein Antrag.