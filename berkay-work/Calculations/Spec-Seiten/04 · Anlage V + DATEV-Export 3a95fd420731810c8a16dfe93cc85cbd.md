# 04 · Anlage V + DATEV-Export

Blockiert: 🔒 M7 — zweite Hälfte
Emir-Prio: 4
Fixtures: 11-F01 … 11-F16
Nr: 04
Optional: No
Phase: 4
Rechtsstand-Einträge: Einkünfte aus Vermietung und Verpachtung — Überschussrechnung Einnahmen − Werbungskosten (../Rechtsstand-Register/Eink%C3%BCnfte%20aus%20Vermietung%20und%20Verpachtung%20%E2%80%94%20%C3%9Cbersch%203ab5fd42073181db9a54e7f345c65aeb.md), Zufluss-/Abflussprinzip + 10-Tage-Regel (Periodenzuordnung nach Zahlungsdatum) (../Rechtsstand-Register/Zufluss-%20Abflussprinzip%20+%2010-Tage-Regel%20(Periodenz%203ab5fd4207318192ac89e1309907adf6.md), Tilgungsreihenfolge bei Teilleistung (Analogie: erst Kaltmiete, dann NK-Vorauszahlung) (../Rechtsstand-Register/Tilgungsreihenfolge%20bei%20Teilleistung%20(Analogie%20ers%203ab5fd4207318138876af7670ff80a18.md), Aufbewahrungspflicht 6 Jahre ab Überschusseinkünften > 500.000 € (../Rechtsstand-Register/Aufbewahrungspflicht%206%20Jahre%20ab%20%C3%9Cberschusseink%C3%BCnft%203ab5fd42073181f79912e7ec9090b315.md), Befugnisgrenze Steuerhilfe — Ausfüllhilfe/Datentransport, keine Beratung/Übermittlung (../Rechtsstand-Register/Befugnisgrenze%20Steuerhilfe%20%E2%80%94%20Ausf%C3%BCllhilfe%20Datentra%203ab5fd42073181bbb6f5df7379b403b5.md), Weitergabe Mieter-Personendaten an StB + Datenminimierung im Buchungstext (../Rechtsstand-Register/Weitergabe%20Mieter-Personendaten%20an%20StB%20+%20Datenmini%203ab5fd42073181a9b3d1ca914b283bee.md), GoBD / Unveränderbarkeit — Export-Archiv (Hash + Zeitstempel) + Ledger-Audit-Trail (../Rechtsstand-Register/GoBD%20Unver%C3%A4nderbarkeit%20%E2%80%94%20Export-Archiv%20(Hash%20+%20Zei%203ab5fd4207318104b9f2d92c7c3221bc.md), 10-Tage-Regel — tragendes BFH-Aktenzeichen (ZITAT UNSICHER, kein Az. erfunden) (../Rechtsstand-Register/10-Tage-Regel%20%E2%80%94%20tragendes%20BFH-Aktenzeichen%20(ZITAT%20%203ab5fd42073181ab9f4dfff0ef1ad7c2.md), Anlage-V-Zeilennummern je Steuerjahr (anlage_v_layout_<JJJJ>) — PLATZHALTER, jährlich verschoben (../Rechtsstand-Register/Anlage-V-Zeilennummern%20je%20Steuerjahr%20(anlage_v_lay%203ab5fd420731818c8583de31076fe202.md), SKR03/SKR04-Default-Konten für private Vermietung — PLATZHALTER, kanzleiabhängig (../Rechtsstand-Register/SKR03%20SKR04-Default-Konten%20f%C3%BCr%20private%20Vermietung%20%203ab5fd42073181b8bbcaee27ed9d4736.md), DATEV-EXTF-Formatparameter (EXTF/700/21/Buchungsstapel/13, Win-1252, ';', CRLF, TTMM) (../Rechtsstand-Register/DATEV-EXTF-Formatparameter%20(EXTF%20700%2021%20Buchungsst%203ab5fd420731813db6acdd0eddd3b81f.md), Kaution = durchlaufender Posten (Verrechnungskonto, nie Ertrag) (../Rechtsstand-Register/Kaution%20=%20durchlaufender%20Posten%20(Verrechnungskonto%203ab5fd42073181019452d307de3ff301.md), Schuldzinsen als gekennzeichneter Vorschlagswert aus dem Tilgungsplan (nie stille Übernahme) (../Rechtsstand-Register/Schuldzinsen%20als%20gekennzeichneter%20Vorschlagswert%20a%203ab5fd420731816f939dd35e105d134b.md)
Status: Fertig
Termin: 31. Juli 2026 → 1. August 2026
Ziel-Datei: docs/11
Zuletzt bearbeitet von: 28. Juli 2026 17:10

> **Ziel-Datei:** `docs/11`
> 

> **Phase / Termin:** Phase 4 · Fr 31.07.–Sa 01.08.2026 🔒
> 

> **Fixtures:** `11-F01 … 11-F16`
> 

> **Braucht vorher:** Seite 01 (Rundungsregel `round_half_up`, Residuumsregel) · Seite 02 (Kostenarten-Katalog, umlagefähig ↔ nicht umlagefähig, Kategorie-Schlüssel `grundsteuer`, `versicherung`, `hauswart`, `heizkosten`, `muellbeseitigung`, `instandhaltung`; Katalogfeld `anlageVKategorie` ist der Platzhalter, den diese Seite füllt) · Seite 03 (R13-Tupel: `afaAbziehbarCent`, `zinsAbziehbarCent`, `disagioAbziehbarCent`, `erhaltungsaufwandCent`)
> 

> **Blockiert:** M7 (Steuer-Export ist die zweite Hälfte von M4; nichts hängt weiter unten dran)
> 

> **DoD:** Ein Referenzjahr (3 Parteien, 6 Kostenarten, 1 NK-Nachzahlung, 1 Guthaben, 1 Kaution, 3 Jahreswechsel-Zahlungen) rechnet von den Ledger-Einträgen bis zur Anlage-V-Zeilentabelle **und** bis zum EXTF-Buchungsstapel durch — auf den Cent, mit Summenprobe Einnahmen/WK und Summenprobe Soll = Haben. Emir kann `docs/11` daraus transkribieren, ohne eine Annahme zu treffen.
> 

> **Namensräume dieser Seite.** Konventionen `11-K01…`, Edge Cases `11-E01…`, Rechenschritte `R1–R9`, Fixtures `11-F01…`. Kollisionsfrei gegen Seite 01 (unnummeriert), 02 (`09-*`) und 03 (`10-*`).
> 

> Sprache: content in English, wie auf Seite 01–03. Deutsche Rechtsbegriffe, Normzitate, DATEV-Feldnamen und alle Texte, die im Produkt oder in der Exportdatei ausgegeben werden, bleiben unübersetzt.
> 

> **Zwei Deliverables, ein Ledger.** Diese Seite spezifiziert **zwei Exporte aus derselben Quelle**: die **Anlage-V-Übersicht** (PDF + CSV, für Selbstmacher/ELSTER und zur Ablage) und den **DATEV-Buchungsstapel** (EXTF-CSV, für den Steuerberater). Beide sind reine, deterministische Sichten auf das Zahlungs-Ledger — kein Export rechnet selbst. Das ist die tragende Architektur-Entscheidung (Konzept §3).
> 

---

## 1. Zweck

This page turns the payment ledger — every rent, every umlage, every paid operating cost, plus the AfA and interest tuple that Seite 03 hands over — into the **two artefacts a landlord needs once a year**: a line-by-line **Anlage-V-Übersicht** per object and tax year that maps cash flows onto the current year's form lines, and a **DATEV EXTF booking batch** the tax advisor imports without reworking it. It defines the category→line and category→account mapping, the § 11 EStG cash-basis aggregation including the 10-day rule, the split/partial-payment logic, and — the actual USP — the **Readiness-Check** that tells the user what is missing *before* an export is produced instead of after the advisor finds the holes.

---

## 2. Rechtsgrundlage

### 2.1 Normen

| Norm | Inhalt | Rechtsstand | Rechtsnatur | Quelle |
| --- | --- | --- | --- | --- |
| § 21 EStG | **Einkünfte aus Vermietung und Verpachtung** — reine Überschussrechnung Einnahmen − Werbungskosten | Fassung 2026, Stand 07/2026 | Gesetz | [lxgesetze.de/estg/21](http://lxgesetze.de/estg/21) |
| § 2 Abs. 2 S. 1 Nr. 2 EStG | Überschuss der **Einnahmen über die Werbungskosten** als Einkunftsart | 07/2026 | Gesetz | — |
| § 8 EStG | Begriff der **Einnahmen** (Zufluss von Gütern in Geld/Geldeswert) | 07/2026 | Gesetz | — |
| § 9 EStG | **Werbungskosten** — u. a. AfA (Abs. 1 S. 3 Nr. 7), Schuldzinsen (Nr. 1), Erhaltungsaufwand | 07/2026 | Gesetz | — |
| **§ 11 EStG** | **Zufluss-/Abflussprinzip** — maßgeblich ist der Zahlungszeitpunkt, nicht der Abrechnungszeitraum. Abs. 1 S. 2 / Abs. 2 S. 2: **10-Tage-Regel** für regelmäßig wiederkehrende Zahlungen um den Jahreswechsel | 07/2026 | Gesetz | [lxgesetze.de/estg/11](http://lxgesetze.de/estg/11) |
| § 366 Abs. 2 BGB | **Tilgungsreihenfolge** bei Teilleistung, wenn der Schuldner nichts bestimmt — Grundlage für die Analogie „erst Kaltmiete, dann NK-Vorauszahlung" (11-K06) | 07/2026 | Gesetz | — |
| § 147a AO | **Aufbewahrungspflicht 6 Jahre** ab > 500.000 € positiven Überschusseinkünften — Fundament des unveränderlichen Export-Archivs | 07/2026 | Gesetz | — |
| §§ 145–147 AO, GoBD | Ordnungsmäßigkeit, Unveränderbarkeit, Nachvollziehbarkeit — treffen den **Steuerberater** ab Verbuchung, nicht den Privatvermieter direkt (Konzept §7c) | GoBD i. d. F. BMF 28.11.2019, Stand 07/2026 | Verwaltungsanweisung | [bundesfinanzministerium.de](http://bundesfinanzministerium.de) |
| **§§ 1–5 StBerG** | **Befugnis zur Hilfeleistung in Steuersachen** — die Grenze, die diese Seite nie überschreitet: Lokara **rechnet und transportiert**, berät nicht und übermittelt nicht (11-K10) | Fassung 2026, Stand 07/2026 | Gesetz | — |
| Art. 6 Abs. 1 lit. c/f DSGVO | Weitergabe von Mieter-Personendaten an den StB gedeckt durch die Steuerpflicht des Vermieters; verlangt **Datenminimierung** im Buchungstext (11-K09) | Stand 07/2026 | Verordnung (EU) | — |
| § 6a HeizkostenV, § 556 BGB | nur Querverweis — Fristen/UVI liegen auf Seite 05, nicht hier | 07/2026 | — | — |

> **DATEV-EXTF ist kein Rechtsstand.** Das EXTF-Format ist eine **proprietäre Formatspezifikation der DATEV eG**, kein Gesetz und keine Verwaltungsanweisung. Es wird in 2.3 als Konvention geführt und vor Produktion gegen das DATEV Developer Portal verifiziert. „Export im DATEV-Format" ist markenrechtlich zulässig, „DATEV-zertifiziert/-Schnittstelle" **nicht** (ohne Partnerschaft) — Wording-Regel für UI und Marketing (11-K11).
> 

### 2.2 Rechtsprechung

| Entscheidung | Aussage | Bindung |
| --- | --- | --- |
| **BFH-Linie zu § 11 Abs. 1 S. 2 EStG** (10-Tage-Regel) | Regelmäßig wiederkehrende Einnahmen/Ausgaben, die **kurze Zeit** (= 10 Tage, 22.12.–10.01.) vor/nach dem Jahreswechsel zufließen/abfließen, sind dem Jahr der **wirtschaftlichen Zugehörigkeit** zuzurechnen — **nur wenn Fälligkeit UND Zahlung** in dieses Fenster fallen. Liegt die Fälligkeit außerhalb, gilt das Zahlungsjahr. | st. Rspr. |

> **[UNSICHER: konkrete Aktenzeichen der 10-Tage-Rechtsprechung.** Die **Aussage** (beide Bedingungen — Fälligkeit *und* Zahlung im Fenster) ist in Verwaltungspraxis und Literatur unstreitig und trägt die Regel in R3/11-K05. Ich gebe hier **bewusst kein Aktenzeichen** an, statt eines zu erfinden — in Betracht kommen u. a. BFH VIII R 9/09 (Umsatzsteuer-Vorauszahlung als wiederkehrende Ausgabe) und die Folgeentscheidungen zur Fälligkeitsvoraussetzung. **Vor Produktion:** ein tragendes BFH-Aktenzeichen sauber ziehen und ins Rechtsstand-Register aufnehmen, bevor es in einen Warntext oder ins StB-Dossier geschrieben wird. Die Rechenregel hängt an der Aussage, nicht am Zitat.]
> 

### 2.3 Konventionen — nicht Gesetz, `verify-before-production`

- **[KONVENTION] 11-K01 — Anlage-V-Zeilennummern sind eine jahresversionierte Datentabelle, kein Code.** Die Zeilennummern des Formulars verschieben sich nahezu jährlich. Sie werden als `anlage_v_layout_<JJJJ>` im `rules-store` geführt (siehe 3.4) und **nie hardgecodet**. Maßgeblich ist das Layout des **Steuerjahres**, nicht des Erstellungsjahres. Das Produkt druckt „Zeilennummern lt. Formular Anlage V <JJJJ>, Stand MM/JJJJ" auf jede Ausgabe.
- **[KONVENTION] 11-K02 — SKR-Kontenzuordnung ist Default + überschreibbar.** Lokara liefert je Kategorie einen Vorschlag für SKR03 und SKR04; die **verbindliche** Kontonummer bestimmt der Steuerberater (StB-Profil, 11-K08-Schreibrecht). Grund: private V+V wird in Kanzleien uneinheitlich gebucht (Überschuss-Rechnung vs. Bestandskonten) — ein hartkodiertes Konto wäre bei vielen Mandanten falsch.
- **[KONVENTION] 11-K03 — Ledger in ganzen Cent, Aggregation ist exakte Integer-Addition.** Alle Ledger-Beträge sind bereits `integer Cent`. Die Anlage-V-Summen und die DATEV-Beträge entstehen durch **verlustfreie Addition** — hier wird **nicht gerundet**. Gerundet (`round_half_up` auf ganze Cent) wird ausschließlich, wo ein Betrag anteilig aufgeteilt wird (Split ohne vorgegebene Soll-Stellung, R4), und dort **einmal**, mit Residuumsregel. Der ehrliche Punkt dieser Seite: das arithmetische Risiko ist gering — das reale Risiko ist **Klassifizierung und Periodenzuordnung**, nicht Rechengenauigkeit.
- **[KONVENTION] 11-K04 — Kaution ist durchlaufender Posten.** Kautionseingang und -rückzahlung werden im Ledger als Kategorie `kaution` geführt und von **beiden** Exporten von der Ergebnisrechnung ausgeschlossen; in DATEV laufen sie über ein **Verrechnungskonto**, nie über ein Ertragskonto. Häufigster Fehler bei Wettbewerbern.
- **[KONVENTION] 11-K05 — 10-Tage-Regel zweigleisig.** (a) **Automatische Zuordnung in der Aggregation** dort, wo eine saubere Soll-Stellung vorliegt (finAPI-gematchte Mieten mit bekanntem Fälligkeitstag). (b) **Readiness-Check-Bestätigungsflag** für alle übrigen Zahlungen im Fenster 22.12.–10.01. (manuelle Erfassung, Ausgaben ohne Soll-Stellung). Umgeordnete Zahlungen werden in Vorschau und PDF gekennzeichnet („§ 11: dem Steuerjahr X zugeordnet"). Beschlossen 17.07.2026.
- **[KONVENTION] 11-K06 — Teilzahlungs-Tilgungsreihenfolge: erst Kaltmiete, dann NK-Vorauszahlung** (§-366-Abs.-2-BGB-Analogie). Pro Account konfigurierbar; die tatsächlich verwendete Reihenfolge wird im Export dokumentiert. Beschlossen 17.07.2026.
- **[KONVENTION] 11-K07 — Schuldzinsen als gekennzeichneter Vorschlagswert.** Liegen Darlehensdaten vor, übernimmt die Anlage-V-Zinszeile den `zinsAbziehbarCent` aus Seite 03 (R12) — **immer** als „Vorschlagswert aus Ihrem Tilgungsplan — mit der Jahreszinsbescheinigung Ihrer Bank abgleichen", editierbar, im Readiness-Check als gelber Bestätigungspunkt. Nie stille Übernahme. Beschlossen 17.07.2026.
- **[KONVENTION] 11-K08 — StB-Gastzugang read-only mit einer Schreibausnahme:** dem StB-Profil (Konten-Mapping, Berater-/Mandantennummer, SKR-Wahl, Sachkontenlänge, WJ-Beginn). Genau diese Daten kennt nur der Berater.
- **[KONVENTION] 11-K09 — Datenminimierung im Buchungstext.** Default: **Einheit statt vollem Mietername** (`WE-02` statt Klarname), wo die Zuordnung erhalten bleibt; konfigurierbar. Buchungstext-Konvention: `[Art] [Einheit] [Zeitraum]`, z. B. `Miete WE-02 März 2025`. Belegfeld 1 = Lokara-Referenz (Rückverfolgbarkeit bis zum Ledger-Eintrag).
- **[KONVENTION] 11-K10 — Compliance-Linie „Ausfüllhilfe/Datentransport, keine Beratung/Übermittlung".** Anlage V = Zuarbeit zum Abtippen; DATEV = Datei zum Import. Kein ELSTER-Versand, keine Gestaltungsempfehlung. § 82b-EStDV-Hinweis und Schuldzinsen-Label sind **Prüfanregungen**, keine Empfehlungen (StBerG-Grenze).
- **[KONVENTION] 11-K11 — DATEV-EXTF-Formatparameter (verify-before-production):** Kennzeichen `EXTF`, **Header-Version 700**, **Datenkategorie 21** (Buchungsstapel), **Formatversion 13**, **Windows-1252/ANSI**, Feldtrenner Semikolon `;`, Textfelder in `"…"`, **Dezimalkomma**, Zeilenende **CRLF**, Belegdatum **TTMM**, Dateiname `EXTF_….csv`. Siehe 2.4.

### 2.4 Offene Rechts- und Formatstandsfragen dieser Seite

> **[UNSICHER: exakte Anlage-V-Zeilennummern je Steuerjahr.** Die Anlage V wurde in den letzten Jahren mehrfach umstrukturiert; die Nummern der Einzelpositionen (Mieteinnahmen, Umlagen, AfA, Schuldzinsen, Summe Einnahmen, Summe Werbungskosten, Ergebnis) **verschieben sich pro Steuerjahr**. Die in 3.4 und in den Fixtures verwendeten Nummern sind **realistische Platzhalter, keine verifizierten Formularzeilen.** Das amtliche Formular des Zieljahres erscheint erst gegen Jahresende. **Vor jedem Saisonstart: das offizielle Formular ([elster.de](http://elster.de) / Formular-Management-System des BMF) ziehen, die `anlage_v_layout_<JJJJ>`-Tabelle daraus befüllen, alle Fixtures dagegen nachrechnen.** Eine falsche Zeilennummer im Export ist ein echter Produktschaden — deshalb steht diese Unsicherheit hier ausdrücklich und wird nicht überdeckt.]
> 

> **[UNSICHER: SKR03/SKR04-Standardkonten für private Vermietung.** Die in 3.4 vorgeschlagenen Kontonummern sind **plausible Größenordnungen aus der SKR-Systematik, nicht kanzleiverifizierte Standardwerte.** V+V im Privatvermögen (Überschusseinkünfte) wird in DATEV uneinheitlich abgebildet — manche Kanzleien buchen auf Erlös-/Aufwandskonten, andere führen reine Einnahmen-Überschuss-Strukturen. **Vor Produktion:** die Default-Kontenliste mit einem echten StB (Testpartner, Konzept §9 Nr. 1) gegenprüfen und die Semantik je SKR fixieren. Bis dahin bleibt jede Nummer `verify-before-production`; das Produkt macht sie ohnehin überschreibbar (11-K02).]
> 

> **[UNSICHER: EXTF-Header-Feldliste, Versionsnummern und Festschreibungs-Feld-Semantik.** Header-Version 700 / Formatversion 13 / Kategorie 21 sind der aktuelle Arbeitsstand (Konzept §6), aber die DATEV-Feldliste ändert sich mit den Versionen, und die genaue Position/Bedeutung des **Festschreibungs-Feldes** (GoBD-relevant) ist zu klären. **Vor dem Bau:** die exakte Spec der Zielversion vom DATEV Developer Portal ([developer.datev.de](http://developer.datev.de)) ziehen und den EXTF-Generator gegen einen **echten Import in DATEV Kanzlei-Rechnungswesen** testen (Konzept §8 QA, §9 Nr. 2/3). Ohne echten Import-Test kein Launch — die eigene Validierung reicht nicht.]
> 

---

## 3. Inputs

Geld = **integer Cent**. Datum = **taggenau** (Zufluss/Abfluss ist tagesscharf, § 11 EStG). Konten = **String** (führende Nullen möglich, SKR-abhängige Länge). Sätze/Quoten kommen fertig aus Seite 03. Keine Fließkommazahl verlässt diese Seite.

### 3.1 Zahlungs-Ledger (`payment[]`, gemeinsame Quelle beider Exporte)

| Feld | Typ / Einheit | Quelle |
| --- | --- | --- |
| `paymentId` | uuid | Bestand |
| `objektId` / `einheitId` | uuid \ | `null` |
| `mieterId` | uuid \ | `null` |
| `datum` | date · **Pflicht** — Zufluss (Einnahme) bzw. Abfluss (Ausgabe) | finAPI-Bankumsatz; manuell (Default heute); Rechnungserfassung |
| `betragCent` | integer > 0 | finAPI / manuell / Rechnung |
| `richtung` | enum {einnahme, ausgabe} | abgeleitet aus Vorzeichen/Kontext |
| `kategorie` | enum aus Seite-02-Katalog + {`kaltmiete`, `nk_vorauszahlung`, `nk_nachzahlung`, `nk_guthaben`, `kaution`, `schuldzinsen`, `afa`} · **Pflicht** | Matching / Nutzer |
| `faelligkeitsdatum` | date \ | `null` — nur gesetzt bei Soll-gestützten Positionen (Mietvertrag) |
| `belegReferenz` | string | Ledger (Rückverweis) |
| `quelle` | enum {finapi, manuell, rechnung} | System |
| `version` | integer — Änderungshistorie (GoBD-Audit-Trail) | System |

> **`datum` ist das einzige harte Pflichtfeld dieser Seite.** Ohne Zahlungsdatum gibt es keine Periodenzuordnung (§ 11) und kein DATEV-Belegdatum → **HARD BLOCK** im Readiness-Check (11-E01). Mit finAPI kommt es gratis aus dem Bankumsatz; bei manueller Erfassung wird es abgefragt.
> 

### 3.2 Übergabe aus Seite 03 (`afaExportTupel`, ein Satz je Objekt und Jahr)

| Feld | Typ / Einheit | Herkunft |
| --- | --- | --- |
| `afaAbziehbarCent` | integer ≥ 0 | Seite 03, R13 |
| `zinsAbziehbarCent` | integer ≥ 0 | Seite 03, R12/R13 — **Vorschlagswert** (11-K07) |
| `disagioAbziehbarCent` | integer ≥ 0 | Seite 03, R12b |
| `erhaltungsaufwandCent` | integer ≥ 0 | Seite 03 / Belegerfassung |

> Diese Werte werden **übernommen, nicht nachgerechnet** — Single Source of Truth ist Seite 03. Fehlt der AfA-Satz zum Objekt, meldet der Readiness-Check „Objekt ohne AfA-Datensatz" (11-E06) und verlinkt den AfA-Wizard.
> 

### 3.3 StB-Profil (`stbProfil`, einmal je Steuerberater, 11-K08)

| Feld | Typ / Einheit | Quelle |
| --- | --- | --- |
| `beraternummer` | string · **Pflicht für DATEV** | StB |
| `mandantennummer` | string · **Pflicht für DATEV** | StB |
| `kontenrahmen` | enum {skr03, skr04} · Default `skr03` | StB |
| `sachkontenlaenge` | integer · Default `4` | StB |
| `wjBeginn` | date · Default `<JJJJ>0101` | StB |

### 3.4 Steuer-Mapping (`taxCategoryMapping`, rules-store, eine Tabelle bedient beide Exporte)

> **[UNSICHER — sämtliche Nummern dieser Tabelle: Zeilennummern (2.4 Abs. 1) und Kontonummern (2.4 Abs. 2). Platzhalter, `verify-before-production`.]** Struktur ist verbindlich, die konkreten Werte nicht.
> 

| `kategorie` | Seite | AnlageV-Zeile `2025` | SKR03 | SKR04 | Richtung |
| --- | --- | --- | --- | --- | --- |
| `kaltmiete` | Einnahme | `[UNSICHER: 13]` Mieteinnahmen (ohne Umlagen) | `[UNSICHER: 8100]` | `[UNSICHER: 4100]` | einnahme |
| `nk_vorauszahlung` | Einnahme | `[UNSICHER: 14]` Umlagen, verrechnet mit Vorauszahlungen | `[UNSICHER: 8105]` | `[UNSICHER: 4105]` | einnahme |
| `nk_nachzahlung` | Einnahme | `[UNSICHER: 14]` (wie Umlage, bei Zufluss) | `[UNSICHER: 8105]` | `[UNSICHER: 4105]` | einnahme |
| `nk_guthaben` | Einnahme (−) | `[UNSICHER: 14]` (mindert Umlagen) | `[UNSICHER: 8105]` | `[UNSICHER: 4105]` | ausgabe |
| `afa` | WK | `[UNSICHER: 33]` AfA (Gebäude) | `[UNSICHER: 4831]` | `[UNSICHER: 6221]` | — (kein Cashflow) |
| `schuldzinsen` | WK | `[UNSICHER: 37]` Schuldzinsen | `[UNSICHER: 8xxx]` | `[UNSICHER: 6xxx]` | ausgabe |
| `grundsteuer` | WK | `[UNSICHER: 47]` Grundsteuer/öff. Abgaben | `[UNSICHER: 4900]` | `[UNSICHER: 6300]` | ausgabe |
| `versicherung` | WK | `[UNSICHER: 48]` Versicherungen | `[UNSICHER: 4360]` | `[UNSICHER: 6400]` | ausgabe |
| `hauswart` | WK | `[UNSICHER: 49]` Verwaltungs-/Hauswartkosten | `[UNSICHER: 4210]` | `[UNSICHER: 6210]` | ausgabe |
| `heizkosten` | WK | `[UNSICHER: 50]` sonstige Kosten / Heizung | `[UNSICHER: 4240]` | `[UNSICHER: 6240]` | ausgabe |
| `muellbeseitigung` | WK | `[UNSICHER: 50]` sonstige Kosten | `[UNSICHER: 4250]` | `[UNSICHER: 6250]` | ausgabe |
| `instandhaltung` | WK | `[UNSICHER: 42]` Erhaltungsaufwand | `[UNSICHER: 4260]` | `[UNSICHER: 6260]` | ausgabe |
| `kaution` | — (durchlaufend, 11-K04) | — (nie Anlage V) | `[UNSICHER: 1590 Verrechnung]` | `[UNSICHER: 1370]` | — |
| `bank` (Gegenkonto) | — | — | `[UNSICHER: 1200]` | `[UNSICHER: 1800]` | — |

> Jede Zeile ist global als Default hinterlegt und **pro Account überschreibbar** (Kontonummern durch den StB, 11-K02). `[UNSICHER: 8xxx/6xxx]` heißt: die Kategorie existiert im Mapping, aber ich gebe kein konkretes Konto aus, weil ich keinen belastbaren Standardwert kenne — bewusst offen statt falsch gefüllt.
> 

---

## 4. Formel

Rundungsregel global: **keine Rundung in der Aggregation** — Ledger-Beträge sind Cent, Summen sind exakte Integer-Addition (11-K03). `round_half_up` auf ganze Cent nur in R4, wenn ein Betrag ohne vorgegebene Soll-Stellung anteilig gesplittet wird; dort mit Residuum. Beide Exporte sind **reine Funktion** `f(Ledger-Stand, Mapping, Parameter) → Datei` — kein Zustand im Generator, damit Golden-File-Tests byteweise vergleichbar sind.

**R1 — Periodenzuordnung (§ 11 EStG, 10-Tage-Regel).** Bestimmt je `payment` das **Steuerjahr**, in das der Betrag fällt.

```
fenster = [22.12.(J−1) … 10.01.(J+1)]           // taggenau, „kurze Zeit"
istWiederkehrend(p) = p.kategorie ∈ {kaltmiete, nk_vorauszahlung, schuldzinsen,
                                     versorger-abschlag} // regelmäßig wiederkehrend

Standard:  steuerjahr(p) = jahr(p.datum)                          // Zuflussjahr

10-Tage-Ausnahme — NUR wenn ALLE drei gelten:
   istWiederkehrend(p)
   && p.datum ∈ fenster
   && p.faelligkeitsdatum ∈ fenster                              // BFH: beide Bedingungen
   → steuerjahr(p) = jahr(p.faelligkeitsdatum)                   // wirtschaftliche Zugehörigkeit

Zweigleisig (11-K05):
   faelligkeitsdatum bekannt (finAPI-Sollstellung) → automatisch zuordnen
   faelligkeitsdatum == null && p.datum ∈ fenster   → Readiness-Flag (11-E07), Default Zuflussjahr
```

**R2 — Split einer Sammelzahlung (Soll-gestützt).** Eine Mietzahlung deckt Kaltmiete + NK-Vorauszahlung.

```
soll_km  = mietvertrag.kaltmieteCent
soll_nk  = mietvertrag.nkVorauszahlungCent
Vollzahlung (betrag == soll_km + soll_nk):
   anteil_km = soll_km ; anteil_nk = soll_nk          // exakt, keine Rundung
```

**R3 — Teilzahlung (betrag < soll, 11-K06).** Tilgungsreihenfolge erst Kaltmiete, dann NK-VZ.

```
anteil_km = min(betrag, soll_km)
rest      = betrag − anteil_km
anteil_nk = min(rest, soll_nk)
offen_km  = soll_km − anteil_km
offen_nk  = soll_nk − anteil_nk
// offene Beträge sind KEINE Buchung (keine Zahlung), erscheinen nicht im Export,
// nur als offener Posten im Ledger. Verwendete Reihenfolge wird dokumentiert.
```

**R4 — anteiliger Split ohne Soll-Stellung (Ausnahmefall).** Nur wenn keine Sollwerte vorliegen und eine Quote nötig ist:

```
anteil_a = round_half_up(betrag × quote_a_zaehler / quote_nenner)
anteil_b = betrag − anteil_a                          // Residuum, nie separat gerundet
```

**R5 — Anlage-V-Aggregation.** Je Objekt und Steuerjahr, über alle `payment` mit `steuerjahr(p) == J`.

```
für jede AnlageV-Zeile z aus anlage_v_layout_J:
   summe(z) = Σ p.betragCent  über alle p mit mapping[p.kategorie].zeile == z
              − Σ p.betragCent für nk_guthaben (mindert die Umlagen-Zeile)
   kaution ausgeschlossen (11-K04)

Einnahmen  = Σ summe(z) für z ∈ Einnahmen-Zeilen        // z. B. Zeile 13 + 14
Summe_Einnahmen(Zeile „32") = Einnahmen

Werbungskosten:
   afa-Zeile        = afaExportTupel.afaAbziehbarCent          // aus Seite 03, kein Cashflow
   schuldzinsen     = afaExportTupel.zinsAbziehbarCent         // Vorschlagswert (11-K07)
   je Kostenart z   = Σ p.betragCent (ausgabe, kategorie→z)
Summe_WK(Zeile „82") = Σ aller WK-Zeilen
Ergebnis(Zeile „84") = Summe_Einnahmen − Summe_WK            // Überschuss (+) / Verlust (−)
```

Rundung: keine — reine Cent-Addition. Jeder Zeilenbetrag ist bis zur Einzelzahlung aufklappbar (UX-Prinzip, keine Blackbox-Summe).

**R6 — DATEV-Buchungssatz je Zahlung.** Ein `payment` → ein Buchungssatz (Split → zwei).

```
Einnahme:  Umsatz = betragCent ; S/H = "S" ; Konto = bank ; Gegenkonto = mapping.ertragskonto
Ausgabe:   Umsatz = betragCent ; S/H = "S" ; Konto = mapping.aufwandskonto ; Gegenkonto = bank
Kaution:   Gegenkonto = Verrechnungskonto (11-K04), nie Ertrag
Betrag OHNE Vorzeichen, Dezimalkomma („1940,00"); Belegdatum = TTMM aus p.datum;
Belegfeld1 = p.belegReferenz; Buchungstext = "[Art] [Einheit] [Zeitraum]" (11-K09)
Kontonummern je nach stbProfil.kontenrahmen (SKR03 | SKR04)
```

> Die klassische DATEV-Konvention nennt in „Konto" das bebuchte Bestands-/Erfolgskonto und in „Gegenkonto" das Gegenkonto ohne BU-Schlüssel; S/H bezieht sich auf das **Umsatzkonto**. **[UNSICHER: Soll/Haben-Orientierung je Buchungsrichtung — vor Produktion am echten Import verifizieren (2.4 Abs. 3).** Die Beträge und die Konten-Paare stimmen; die S/H-Kennzeichnung ist der Punkt, den ein Fehlimport sofort zeigt.]
> 

**R7 — EXTF-Datei zusammensetzen (11-K11).**

```
Zeile 1  Header:  EXTF;700;21;"Buchungsstapel";13;<erzeugtAm JJJJMMTTHHMMSSFFF>;;RE;"Lokara";;
                  <beraternr>;<mandantennr>;<wjBeginn JJJJ0101>;<sachkontenlaenge>;
                  <datumVon JJJJMMTT>;<datumBis JJJJMMTT>;"<bezeichnung>";;1;;…;EUR;…
Zeile 2  Spaltenüberschriften der Buchungssätze
ab Z. 3  Buchungssätze aus R6, einer je Zeile
Encoding Windows-1252 · Trenner ";" · Text in "…" · CRLF · Dateiname EXTF_<…>.csv
```

**R8 — Readiness-Check (der USP, Phase-4-Pflichtpunkt 3).** Läuft **vor** jeder Erzeugung. Ampel; rot blockiert, gelb warnt.

```
ROT (Export blockiert):
   R-r1  Zahlung ohne datum                         → 11-E01
   R-r2  DATEV gewählt & beraternr/mandantennr fehlt → 11-E11
   R-r3  gar keine Zahlungsdaten im Zeitraum        → leere Ausgabe verhindern
GELB (Warnung, Export mit Kennzeichnung möglich):
   R-g1  Bankumsatz ohne Mieter-Zuordnung           → Zuordnungs-Dialog
   R-g2  Zahlung ohne kategorie                      → 11-E02
   R-g3  kategorie ohne Konto im Mapping             → 11-E03 / Mapping-Tabelle
   R-g4  Objekt ohne AfA-Datensatz                   → 11-E06 / AfA-Wizard
   R-g5  Jahreswechsel-Zahlung im Fenster ohne eindeutige Zuordnung → 11-E07 (bestätigen)
   R-g6  Schuldzinsen-Vorschlagswert unbestätigt     → 11-K07 (bestätigen/anpassen)
   R-g7  Lücken-Heuristik: Vertrag läuft, Monat ohne Mieteingang → Leerstand oder fehlt Buchung?
   R-g8  USt-Fall erkannt (gewerblich)               → 11-E12 (ohne BU exportiert, gekennzeichnet)
Jeder Punkt ist klickbar und führt zurück in den Check („Fix-and-return").
```

**R9 — Validierung & Summenprobe vor Ausgabe.**

```
Anlage V:  Summe_Einnahmen − Summe_WK == Ergebnis                 // Zeile 32 − 82 == 84
DATEV:     Σ Umsatz(S) über alle Sätze == Σ Umsatz(H)            // Bilanzgleichheit des Stapels
Encoding:  Umlaut-/€-Testfälle in Windows-1252 unbeschädigt
Header:    alle p.datum ∈ [datumVon, datumBis]; Pflichtfelder gesetzt
```

Eine EXTF, die beim StB-Import knallt, kostet mehr Vertrauen als gar keine (Konzept §6).

---

## 5. Edge Cases

| ID | Fall | Verhalten | Fixture |
| --- | --- | --- | --- |
| **11-E01** | `payment.datum` fehlt | **HARD BLOCK (rot).** Keine Periodenzuordnung, kein Belegdatum. Kein Default „heute" im Export — Datum wird erfasst. | 11-F… (Readiness) |
| **11-E02** | `payment.kategorie` fehlt | GELB. Zahlung erscheint nicht in Zeile/Konto, bis kategorisiert; Export mit Warnung möglich. | — |
| **11-E03** | Kategorie ohne SKR-Konto im Mapping | GELB. Verlinkt Mapping-Tabelle; DATEV-Satz wird sonst unvollständig. | 11-F14 |
| **11-E04** | NK-Nachzahlung für Vorjahr, gezahlt im Folgejahr | Zählt nach **Zahlungsjahr** (§ 11), nicht Abrechnungsjahr; Umlagen-Zeile des Zahlungsjahres. | 11-F04 |
| **11-E05a** | Januarmiete, fällig 01.01., gezahlt 28.12., beide im Fenster | 10-Tage-Regel → **Fälligkeitsjahr** (neues Jahr); aus dem alten Jahr entfernt, gekennzeichnet. | 11-F05 |
| **11-E05b** | Dezembermiete, fällig 01.12., gezahlt 05.01., beide im Fenster? | Fälligkeit **außerhalb** des Fensters → **Zahlungsjahr** (BFH: beide Bedingungen). Gegenprobe zu 11-E05a. | 11-F07 |
| **11-E05c** | Dezembermiete, fällig 31.12., gezahlt 05.01., beide im Fenster | 10-Tage-Regel → **Fälligkeitsjahr** (altes Jahr). | 11-F06 |
| **11-E06** | Objekt ohne AfA-Datensatz | GELB. AfA-Zeile bleibt leer + Hinweis „bitte ergänzen"; verlinkt AfA-Wizard. | 11-F02 |
| **11-E07** | Jahreswechsel-Zahlung im Fenster, `faelligkeitsdatum == null` | GELB-Bestätigung (11-K05b): Nutzer wählt altes/neues Steuerjahr; Default Zuflussjahr. | 11-F05 |
| **11-E08** | Teilzahlung (Zahlung < Soll) | R3: erst Kaltmiete, dann NK-VZ; offene Beträge sind keine Buchung. | 11-F09 |
| **11-E09** | Guthaben-Auszahlung an Mieter | Mindert die Umlagen-Einnahme (negativ in R5); DATEV umgekehrte Buchung. | 11-F10 |
| **11-E10** | Kaution: Eingang + Rückzahlung | Durchlaufend (11-K04): nie in Anlage V; DATEV Verrechnungskonto. | 11-F11 |
| **11-E11** | DATEV gewählt, Berater-/Mandantennummer fehlt | **HARD BLOCK (rot).** Setup-Dialog StB-Profil. | 11-F… (Readiness) |
| **11-E12** | USt-Fall (gewerbliche Vermietung, § 9 UStG-Option) | Export **ohne** BU-Schlüssel/USt-Logik, **klar gekennzeichnet**; Nutzer → StB-Hinweis. Non-Goal V1. | 11-F16 |
| **11-E13** | Überzahlung (Zahlung > Soll) | Überschuss als offener Posten/Guthaben im Ledger; gebucht wird die tatsächliche Zahlung, Split bis Soll, Rest als `mieter_guthaben`. | 11-F15 |
| **11-E14** | Umlaut/€ im Buchungstext (z. B. „Müllbeseitigung Grünstraße") | Windows-1252-Encoding-Test (ä ö ü ß €); Validierung R9 bricht bei Beschädigung ab. | 11-F12 |
| **11-E15** | Erneuter Export desselben Jahres | Neue Version im Export-Archiv, alte bleibt unverändert (GoBD-Gedanke, § 147a AO). | — |

---

## 6. BEISPIELRECHNUNG

> **Referenzobjekt — dasselbe wie Seite 01–03.** Musterstraße 12, 50667 Köln · MFH, 3 Wohneinheiten · Wohnfläche 194,00 m² (WE-01 62,00 · WE-02 74,00 · WE-03 58,00) · Fertigstellung 1978 · Erwerb Übergang N&L 15.03.2024. **AfA-Übergabe aus Seite 03 (Weg B, voller Jahresbetrag, ganzjährig vermietet):** `afaAbziehbarCent = 540103` (5.401,03 €) — deckungsgleich mit Seite 03 `jahresAfaVoll` (10-F04). `zinsAbziehbarCent = 840000` (8.400,00 €) ist ein **angenommener Referenzwert dieser Seite** (Vorschlagswert-Mechanik 11-K07); die reale Zahl liefert Seite 03 R12 objektindividuell, es gibt dort keine feste Referenz-Zinszahl.
> 

> 
> 

> **Steuerjahr = 2025** (volles Jahr, ganzjährig voll vermietet). Sollstellung je Einheit:
> 

> 
> 

> | Einheit | Kaltmiete/Monat | NK-VZ/Monat |
> 

> |---|---|---|
> 

> | WE-01 | 620,00 € (62000) | 150,00 € (15000) |
> 

> | WE-02 | 740,00 € (74000) | 180,00 € (18000) |
> 

> | WE-03 | 580,00 € (58000) | 140,00 € (14000) |
> 

> | **Σ/Monat** | **1.940,00 € (194000)** | **470,00 € (47000)** |
> 

> 
> 

> Betriebskosten 2025 (vom Vermieter gezahlt): Grundsteuer 980,00 · Versicherung 1.240,00 · Hauswart 1.800,00 · Heizkosten 3.600,00 · Müllbeseitigung 720,00 · Instandhaltung 1.500,00 €.
> 

> 
> 

> **Varianten-Regel:** Fixtures, die einen anderen Sachverhalt brauchen (Jahreswechsel, Teilzahlung, Kaution, USt), arbeiten auf einer **ausdrücklich deklarierten Variante** und fließen nie in den Referenzstrang (11-F01–F03) ein.
> 

### 11-F01 — R5, Einnahmen-Aggregation, volles Jahr

```jsx
kaltmiete_jahr = 194000 × 12 = 2328000                         (23.280,00 €)  → Zeile [UNSICHER:13]
nk_vz_jahr     =  47000 × 12 =  564000                         ( 5.640,00 €)  → Zeile [UNSICHER:14]
Summe_Einnahmen (Zeile [UNSICHER:32]) = 2328000 + 564000 = 2892000   (28.920,00 €)
```

Summenprobe: 2328000 + 564000 = 2892000 ✓ · reine Cent-Addition, keine Rundung (11-K03).

### 11-F02 — R5, Werbungskosten-Aggregation (Betriebskosten + AfA-Zeile aus Seite 03 + Schuldzinsen-Vorschlagswert)

```jsx
// Betriebskosten (Cashflow, ausgabe)
grundsteuer      =  98000     ( 980,00 €)  → Zeile [UNSICHER:47]   // = 09-F-Referenzwert Seite 02
versicherung     = 124000   (1.240,00 €)  → Zeile [UNSICHER:48]
hauswart         = 180000   (1.800,00 €)  → Zeile [UNSICHER:49]
heizkosten       = 360000   (3.600,00 €)  → Zeile [UNSICHER:50]
muellbeseitigung =  72000     ( 720,00 €)  → Zeile [UNSICHER:50]
instandhaltung   = 150000   (1.500,00 €)  → Zeile [UNSICHER:42]   // Seite 02 Block (b), nicht umlagefähig
betriebskosten_Σ = 98000+124000+180000+360000+72000+150000 = 984000   (9.840,00 €)

// aus Seite 03 übernommen bzw. angenommen
afa              = 540103   (5.401,03 €)  → Zeile [UNSICHER:33]   // Seite 03 R13, kein Cashflow
schuldzinsen     = 840000   (8.400,00 €)  → Zeile [UNSICHER:37]   // Referenzannahme, 11-K07 gelber Bestätigungspunkt

Summe_WK (Zeile [UNSICHER:82]) = 984000 + 540103 + 840000 = 2364103   (23.641,03 €)
```

Summenprobe Betriebskosten: 98000+124000+180000+360000+72000+150000 = 984000 ✓

### 11-F03 — R5/R9, Ergebnis und Summenprobe (Referenzstrang)

```jsx
Ergebnis (Zeile [UNSICHER:84]) = 2892000 − 2364103 = 527897           (5.278,97 €, Überschuss)
```

R9-Probe: Summe_Einnahmen − Summe_WK == Ergebnis → 2892000 − 2364103 = 527897 ✓

### 11-F04 — 11-E04/R1, Zuflussprinzip: NK-Nachzahlung 2024, gezahlt 2025

NK-Abrechnung 2024 ergibt Nachzahlung 340,00 €, Mieter zahlt am 14.03.2025. Nicht wiederkehrend.

```jsx
istWiederkehrend(nk_nachzahlung) = false → Standard: steuerjahr = jahr(2025-03-14) = 2025
→ fällt in die Umlagen-Zeile [UNSICHER:14] des Steuerjahres 2025, NICHT 2024
betrag = 34000   (340,00 €)   → erhöht Summe_Einnahmen 2025 auf 2892000 + 34000 = 2926000 (29.260,00 €)
```

Kennzeichnung im PDF: „§ 11: nach Zahlungsdatum dem Steuerjahr 2025 zugeordnet."

### 11-F05 — 11-E05a/R1, 10-Tage-Regel, beide Bedingungen erfüllt → Fälligkeitsjahr

Januarmiete 2026 WE-02 (Kaltmiete 740,00 €), fällig 01.01.2026, gezahlt 28.12.2025.

```jsx
istWiederkehrend(kaltmiete) = true
datum 2025-12-28 ∈ [22.12.2025 … 10.01.2026] = true
faelligkeit 2026-01-01 ∈ Fenster = true
→ ALLE drei → steuerjahr = jahr(2026-01-01) = 2026
Wirkung: 74000 (740,00 €) wird aus 2025 ENTFERNT und 2026 zugeordnet; in 2025 gekennzeichnet.
```

### 11-F06 — 11-E05c/R1, 10-Tage-Regel, Zahlung im Januar → Fälligkeitsjahr (altes Jahr)

Dezembermiete 2025 WE-02, fällig 31.12.2025, gezahlt 05.01.2026.

```jsx
datum 2026-01-05 ∈ Fenster = true · faelligkeit 2025-12-31 ∈ Fenster = true
→ steuerjahr = jahr(2025-12-31) = 2025   // gehört ins alte Jahr trotz Zahlung im Januar
74000 (740,00 €) → Steuerjahr 2025
```

### 11-F07 — 11-E05b/R1, Gegenprobe: Fälligkeit außerhalb des Fensters → Zahlungsjahr

Nachgezahlte Oktobermiete 2025 WE-02, fällig 01.10.2025, gezahlt 05.01.2026.

```jsx
datum 2026-01-05 ∈ Fenster = true
faelligkeit 2025-10-01 ∈ Fenster = FALSE            // außerhalb 22.12.–10.01.
→ Ausnahme greift NICHT → Standard: steuerjahr = jahr(2026-01-05) = 2026 (BFH-Linie)
74000 (740,00 €) → Steuerjahr 2026
```

Die drei Fälle 11-F05/06/07 zeigen: **beide** Bedingungen müssen im Fenster liegen. Genau hier irren Wettbewerber und Vermieter.

### 11-F08 — R2, Split einer Sammelzahlung (Soll-gestützt)

WE-01 zahlt 770,00 € (Kaltmiete 620 + NK-VZ 150) in einem Betrag.

```jsx
soll_km = 62000 ; soll_nk = 15000 ; betrag = 77000 == soll_km+soll_nk
anteil_km = 62000   (620,00 €)  → kaltmiete
anteil_nk = 15000   (150,00 €)  → nk_vorauszahlung
```

Summenprobe: 62000 + 15000 = 77000 ✓ · exakt, keine Rundung.

### 11-F09 — 11-E08/R3, Teilzahlung: erst Kaltmiete, dann NK-VZ (11-K06)

WE-01 zahlt nur 600,00 € gegen Soll 770,00 €.

```jsx
soll_km = 62000 ; soll_nk = 15000 ; betrag = 60000
anteil_km = min(60000, 62000) = 60000   (600,00 €)
rest      = 60000 − 60000 = 0
anteil_nk = min(0, 15000) = 0            (0,00 €)
offen_km  = 62000 − 60000 = 2000         (20,00 € offener Posten)
offen_nk  = 15000 − 0     = 15000        (150,00 € offener Posten)
```

Gebucht/exportiert werden nur die 60000 (voll auf Kaltmiete). Die offenen 2000 + 15000 sind **keine** Zahlung → erscheinen nicht im Export, nur als offener Posten im Ledger. Verwendete Reihenfolge wird im Export dokumentiert.

### 11-F10 — 11-E09/R5, Guthaben-Auszahlung mindert die Umlagen-Einnahme

NK-Abrechnung 2024 ergibt Guthaben 200,00 € zugunsten WE-03, ausgezahlt 20.02.2025.

```jsx
nk_guthaben, richtung ausgabe, betrag = 20000 (200,00 €)
Wirkung R5: Umlagen-Zeile [UNSICHER:14] = nk_vz + nk_nachzahlung − nk_guthaben
Beispiel isoliert auf Umlagen: 564000 − 20000 = 544000   (5.440,00 €)
```

DATEV: umgekehrte Buchung (Ertragsminderung / Auszahlung über Bank Haben).

### 11-F11 — 11-E10/R6, Kaution ist durchlaufend (11-K04)

Neuer Mieter WE-03 zahlt Kaution 3 × Kaltmiete = 1.740,00 € am 01.04.2025.

```jsx
kategorie = kaution, betrag = 174000 (1.740,00 €)
Anlage V:  ausgeschlossen — 0,00 € Wirkung auf Einnahmen und Ergebnis
DATEV:     Bank (S) 174000 an Kautions-Verrechnungskonto [UNSICHER:1590] (H) 174000
           NIE an ein Ertragskonto
Rückzahlung bei Auszug: exakt umgekehrt, ebenfalls ergebnisneutral.
```

### 11-F12 — R6/R7, DATEV-Buchungssätze (Einnahme + Ausgabe), Windows-1252

Mieteingang WE-02 März 2025 (920,00 € = 740 Kaltmiete + 180 NK-VZ, hier zusammengefasst auf ein Ertragskonto zur Kürze) und gezahlte Heizungsrechnung 360,00 € am 15.03.2025. SKR03, Bank `[UNSICHER:1200]`.

```
// Buchungssatz Einnahme (Umsatz ohne Vorzeichen, Dezimalkomma, Belegdatum TTMM)
Umsatz="920,00"; S/H="S"; Konto=[UNSICHER:1200 Bank]; Gegenkonto=[UNSICHER:8100 Mieterträge];
Belegdatum="1503"; Belegfeld1="MIETE-WE02-0325"; Buchungstext="Miete WE-02 März 2025"
// Buchungssatz Ausgabe
Umsatz="360,00"; S/H="S"; Konto=[UNSICHER:4240 Heizkosten]; Gegenkonto=[UNSICHER:1200 Bank];
Belegdatum="1503"; Belegfeld1="HEIZ-0325"; Buchungstext="Heizkosten Objekt Musterstr 12 März 2025"
```

Encoding-Testfall (11-E14): Buchungstext „Müllbeseitigung Grünstraße" muss in Windows-1252 unbeschädigt bleiben — Validierung R9 prüft ä ö ü ß €.

### 11-F13 — R9, DATEV-Summenprobe Soll = Haben

Ein Stapel aus 11-F12 (nur die zwei Sätze, konventionell Bank-Buchung als Doppelsatz gedacht):

```jsx
Einnahme: Soll Bank 92000  / Haben Mieterträge 92000
Ausgabe:  Soll Heizung 36000 / Haben Bank 36000
Σ Soll  = 92000 + 36000 = 128000    (1.280,00 €)
Σ Haben = 92000 + 36000 = 128000    (1.280,00 €)
Soll == Haben ✓
```

> **[UNSICHER: die konkrete S/H-Darstellung im EXTF-Einzelsatz** (ein Satz trägt Umsatz + ein S/H-Kennzeichen bezogen aufs Umsatzkonto, nicht zwei Zeilen). Die **Bilanzgleichheit** des Stapels ist die Probe; die Zeilendarstellung ist am echten Import zu verifizieren (2.4 Abs. 3).]
> 

### 11-F14 — 11-E03/R6, dieselbe Buchung unter SKR03 und SKR04

Grundsteuer-Zahlung 980,00 € am 15.02.2025.

```
SKR03: Umsatz="980,00"; S/H="S"; Konto=[UNSICHER:4900 Grundsteuer]; Gegenkonto=[UNSICHER:1200 Bank]
SKR04: Umsatz="980,00"; S/H="S"; Konto=[UNSICHER:6300 Grundsteuer]; Gegenkonto=[UNSICHER:1800 Bank]
```

Nur die Kontonummern wechseln mit `stbProfil.kontenrahmen`; Betrag, S/H, Belegdatum, Text bleiben. Fehlt das Konto im Mapping → 11-E03 (gelb).

### 11-F15 — 11-E13/R3, Überzahlung

WE-01 zahlt 800,00 € gegen Soll 770,00 €.

```jsx
anteil_km = min(80000,62000)=62000 ; rest=18000 ; anteil_nk=min(18000,15000)=15000 ; rest2=3000
gebucht: Kaltmiete 62000 + NK-VZ 15000 = 77000 (770,00 €)
ueberzahlung = 3000 (30,00 €) → kategorie mieter_guthaben, nicht Einnahme, offener Posten
```

Summenprobe: 62000 + 15000 + 3000 = 80000 ✓

### 11-F16 — 11-E12, USt-Fall (Non-Goal V1)

Gewerbeeinheit mit USt-Option § 9 UStG, Miete 1.190,00 € (1.000 netto + 190 USt).

```
Verhalten: Export OHNE BU-Schlüssel/USt-Logik. Der Bruttobetrag 119000 (1.190,00 €) wird
gebucht/aggregiert wie eine normale Einnahme, ABER klar gekennzeichnet:
„USt-Fall erkannt — dieser Export enthält keine Umsatzsteuer-Logik. Bitte mit Ihrem
Steuerberater klären." (Readiness R-g8, gelb). Keine Aufteilung netto/USt in V1.
```

Keine Rechnung — bewusst kein V1-Verhalten erfunden (Non-Goal, Konzept §2).

---

## 7. Out of Scope

Diese Seite deckt **nicht** ab (Non-Goals V1, damit niemand Verhalten annimmt):

- **ELSTER-Direktübermittlung (ERiC)** — eigenes Großprojekt (Zertifizierung, Haftung, StBerG). V3+. Lokara reicht nie selbst beim Finanzamt ein.
- **DATEV Buchungsdatenservice (REST-API)** — direkte Cloud-Übertragung statt Datei; braucht DATEV-Partnerschaft/Zertifizierung. V2. V1 = importierbare Datei.
- **Belegbild-Übergabe** (DATEV Unternehmen online / Belegbilderservice) — V2.
- **Rückkanal vom StB** (Statusabgleich, Korrekturen zurück) — V2+, Vision „bidirektionale Brücke".
- **Umsatzsteuer-Logik** (BU-Schlüssel, USt-Voranmeldung, § 9-UStG-Aufteilung) — V1 erkennt und kennzeichnet nur (11-E12), rechnet nicht.
- **§ 82b EStDV** (Verteilung größeren Erhaltungsaufwands auf 2–5 Jahre) — V1 zeigt nur neutralen Hinweistext; Verteilungslogik V2 (Konzept §8, Entität `maintenance_distributions`).
- **AfA-, Zins-, Disagio-Berechnung** — kommen fertig von **Seite 03** (Single Source of Truth); diese Seite rechnet sie nicht nach, sie übernimmt sie.
- **Umlageschlüssel, NK-Abrechnungsarithmetik, Fristen/UVI** — Seite 01/02/05. Diese Seite liest nur das Ledger und die AfA-Übergabe.
- **Verbilligte Vermietung (§ 21 Abs. 2 EStG, 66-%-Grenze)** — Non-Goal V1.
- **Kontenrahmen jenseits SKR03/SKR04** (SKR14, individuelle) — nicht V1.