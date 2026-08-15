# Non-Goals V1

Besitzer/-in: Bahri Berkay Bayrak

> Explizite Nicht-Ziele sind so wertvoll wie die Regeln: sie verhindern, dass Claude Code Verhalten für bewusst verschobene Fälle erfindet.
> 

> Wird während des Schreibens der Seiten 01–08 laufend ergänzt. Finalisierung: Phase 6, Mi 05.08.2026.
> 

> **Stand 26.07.2026:** befüllt aus Seite 01 und Seite 01b. Seiten 02–08 kommen noch dazu.
> 

## Aus Seite 01 · Die Abrechnung

| Nicht-Ziel | Begründung | Betroffene Seite | Wiedervorlage |
| --- | --- | --- | --- |
| WEG-Einzelabrechnung (Hausgeldabrechnung) | Anderes Rechtsregime (WEG statt Mietrecht), anderer Adressat, eigener Wirtschaftsplan. Kein Overlap mit der Betriebskostenabrechnung. | 01 | nach V1 |
| Gewerbliche Einheiten mit Umsatzsteuerausweis | Erfordert Option zur USt, Vorsteueraufteilung und Netto/Brutto-Logik durch die gesamte Engine. | 01, 02 | V2 |
| Verbilligte Vermietung (§ 21 Abs. 2 EStG) | Betrifft die Werbungskosten-Seite, nicht die Umlage. Gehört zu AfA/Anlage V. | 03, 04 | V2 |
| Fremdwährung | Alle Beträge sind Cent in EUR. Keine Wechselkurslogik. | alle | nicht geplant |
| Staffel-/Indexmiete-Auswirkungen auf Vorauszahlungen | Vorauszahlungen kommen als Summe in die Engine; ihre Herleitung ist Vertragsthema. | 01, 06 | V1.x |
| Sammelabrechnung über mehrere Objekte in einem Dokument | Nenner sind objektbezogen. Ein Dokument = ein Objekt = eine Periode. | 01 | nicht geplant |
| Ausgabesprache außer Deutsch | Rechtstexte und Pflichthinweise sind deutschsprachig normiert. | 01 | nicht geplant |
| Anspruchsbegrenzung bei extremem Leerstand (§§ 241 Abs. 2, 242 BGB, BGH VIII ZR 9/14) | Einzelfallabwägung, nicht formelhaft abbildbar. Die HeizkostenV bleibt anwendbar; wir rechnen normal und weisen nicht auf eine mögliche Begrenzung hin. | 01 | Fachanwalt, nach V1 |
| Nicht umlagefähige Kosten im Leerstandsanhang (Block b) | Verwaltung und Instandhaltung sind noch keine Kostenpositionen im Datenmodell — Abhängigkeit von Seite 02, kein Mangel der Seite 01. Rendert bis dahin als 0,00 € mit Hinweis. | 01, 02 | mit Seite 02 |

## Aus Seite 01b · Heizkosten- & CO₂-Verteilung

| Nicht-Ziel | Begründung | Betroffene Seite | Wiedervorlage |
| --- | --- | --- | --- |
| Nachrechnen oder Prüfen einer Messdienst-Abrechnung gegen deren eigene Eingangsdaten | Lokara hat keine Rechtsposition, eine Messdienst-Abrechnung zu überstimmen. Zwei konkurrierende Zahlen für denselben Mieter wären ein Haftungsrisiko, kein Feature (K14). Wir ingestieren, validieren die Kontrollsumme und ergänzen die CO₂- und § 6a-Prüfungen. | 01b | nicht geplant |
| Etagenheizung-Erstattungsrechner (Mieter kauft den Brennstoff, Vermieter erstattet den CO₂-Anteil) | Eigener Rechenweg nach § 6 CO2KostAufG mit eigenem Belegfluss. V1 nur Hinweistext. | 01b | V2 |
| Nichtwohngebäude jenseits des 50/50-Splits | Das angekündigte Stufenmodell für Nichtwohngebäude ist zum Rechtsstand 07/2026 nicht in Kraft. Kein Verhalten für eine Norm erfinden, die es nicht gibt. | 01b | bei Inkrafttreten |
| Sanierungs-/Amortisationsrechnung hinter der Stufenampel („eine Stufe besser ≈ X €/a") | Marketing-Nudge. Darf niemals eine Zahl der Abrechnung speisen. | 01b | V1.x, getrennt vom Rechenkern |
| ARGE-3.10-Import, bved-Webservices | Nach dem Pitch. Bis dahin manuelle Erfassung bzw. OCR. | 01b | nach 06.08.2026 |
| OCR-Engine-Interna (Modell, Prompts, Feldextraktion, Confidence-Handling) | Eigene Spec. Seite 01b definiert nur, **was** extrahiert werden muss und welche Kontrollsumme den Lauf freigibt. | 01b | OCR-Spec |
| Automatische Anwendung der Kürzungsrechte (15 % / 3 %) | Die Kürzung ist ein Recht des Mieters, keine Berechnung des Vermieters. Wir zeigen das Risiko an und ziehen nie ab. | 01b, 05 | nicht geplant |
| Prüfung von Montage, Eichung und K-Werten der Erfassungsgeräte | Lokara verantwortet die Berechnung, nicht die Erfassungstechnik. Haftungsabgrenzung, im Modul als Hinweistext. | 01b | nicht geplant |
| Belegeinsicht-Workflow im Mieterportal (BGH VIII ZR 189/17), inkl. Anzeige fremder Verbrauchswerte | Datenschutzfrage muss vorab geklärt werden: der BGH gibt dem Mieter Einsichtsrecht, die DSGVO begrenzt die Anzeige. Nicht nebenbei entscheidbar. | 01b, Mieterportal | Mieterportal-Spec |
| Eigene Durchschnittsnutzer-Vergleichswerte aus Lokara-Daten | § 6a Abs. 2 Nr. 3 erlaubt „durch Vergleichstests ermittelt" ausdrücklich — aber erst mit belastbarer Fallzahl, dokumentierter Methodik und datenschutzrechtlicher Grundlage für die Aggregation über Vermieter hinweg. Bei kleiner Grundgesamtheit ist der Wert angreifbar. | 01b | ab vierstelliger Objektzahl |
| CO₂-Preis-Fallback für Zeiträume ab 2026 | Ab 2026 gibt es keinen Einheitspreis (Korridor 55–65 €/t, Verkaufsphase 68 €, Nachkauf 70 €). Eine Tabellen-Schätzung würde der Rechnung widersprechen. Entweder Nutzerabfrage oder Blockade — Entscheidung offen. | 01b | To-Do Berkay |

## Aus Seite 02 · BetrKV — Betriebskosten-Katalog

| Nicht-Ziel | Begründung | Betroffene Seite | Wiedervorlage |
| --- | --- | --- | --- |
| Vorwegabzug bei gemischt genutzten Objekten (Wohnen + Gewerbe) | Erfordert eine zweite Nennerebene je Kostenart und die Bewertung, ob die Gewerbeeinheit „erhebliche Mehrkosten" verursacht — eine Tatfrage, keine Formel. R2 Schritt 3 blockiert Gewerbeeinheiten hart. | 02, 01 | V2 |
| Umsatzsteuer-Option und Vorsteueraufteilung | Zieht sich durch jede Kostenart und jede Anlage-V-Zeile. Bestätigt den bestehenden Non-Goal aus Seite 01. | 02, 01, 04 | V2 |
| Automatische Kostenart-Erkennung aus dem Rechnungstext ohne Bestätigung | Der Katalog schlägt vor, der Nutzer bestätigt. Eine falsch erkannte Kostenart erzeugt eine formal fehlerhafte Abrechnung, die der Mieter angreifen kann. | 02 | nicht geplant |
| Prüfung, ob eine Rechnung sachlich berechtigt ist | Lokara prüft die Umlagefähigkeit, nicht die Leistungserbringung. Haftungsabgrenzung. | 02 | nicht geplant |
| Eigenleistung des Vermieters nach § 1 Abs. 1 S. 2 BetrKV (fiktiver Fremdvergleichswert ohne USt) | Erfordert eine belastbare Marktpreisableitung und ist prüfungsanfällig. V1 nimmt nur belegte Fremdrechnungen. | 02 | V1.x |
| Umlage nach dem Verursacherprinzip jenseits der erfassten Verbräuche (§ 556a Abs. 1 S. 2 Alt. 2) | Setzt eine Verursachungserfassung voraus, die kein Vermieter hat. | 02 | nicht geplant |
| Mieterhöhung wegen gestiegener Betriebskosten (§ 560 Abs. 1) als Dokument | Seite 02 prüft nur, ob eine neue Kostenart umlagefähig ist. Das Erhöhungsschreiben ist ein eigenes Dokument. | 02, 06 | V1.x |

## Aus Seite 03 · AfA (Abschreibung)

| Nicht-Ziel | Begründung | Betroffene Seite | Wiedervorlage |
| --- | --- | --- | --- |
| Degressive AfA (§ 7 Abs. 5a EStG) | Restwertkaskade + Wechseloption zur linearen AfA + Prüfung des Erwerbsfensters. Der Hinweis in `R4b` liefert 80 % des Nutzens für 5 % des Aufwands. | 03, 04, 07 | V1.x |
| Sonderabschreibung § 7b EStG | Setzt EH40/QNG-Nachweise, Baukostenobergrenze und Bemessungsgrundlagen-Kappung voraus; die Wertgrenzen sind nicht verifiziert. Nur Erkennung in `R4b`. | 03 | V2 |
| Denkmal-AfA (§§ 7h, 7i, 10f, 10g EStG) | Erfordert die Bescheinigung der Denkmalbehörde und die Aufteilung in begünstigte und nicht begünstigte Aufwendungen. | 03 | V2 |
| BMF-Arbeitshilfe in voller Tiefe (alle Gebäudetypen, Standardstufen 1–5, Regionalfaktoren, Modernisierungspunkte) | Datenprojekt mit Pflegeaufwand bei jedem BMF-Update, kein Formelprojekt. V1 deckt EFH/ZFH/MFH, Standardstufe 3, ohne Regionalfaktor. | 03 | V1.x |
| Automatischer Bodenrichtwert-Abruf (BORIS-D/VBORIS) | Je Bundesland unterschiedliche Schnittstellen, sechs Portale sind noch nicht verifiziert. V1: Portal-Link + manuelle Eingabe, `10-E01` blockiert ohne Wert. | 03 | V1.x |
| AfA je Einheit statt je Objekt | Bei Teileigentum ist ein Datensatz je Einheit richtig; V1 führt einen Datensatz je Objekt und teilt über Flächen. Bei getrennt erworbenen Einheiten ist das falsch. | 03 | V1.x |
| Verbilligte Vermietung (§ 21 Abs. 2 EStG, 66 %/50 %-Grenzen) | Bestätigt den bestehenden Non-Goal aus Seite 01. Die Kürzung des Werbungskostenabzugs träfe auch die AfA und die Zinsen dieser Seite. | 03, 04 | V2 |
| Nachträgliche Anschaffungskosten am Grund und Boden (Erschließungsbeiträge) | Erhöhen den nicht abschreibbaren Anteil; V1 erfasst sie nicht getrennt und würde sie fälschlich der AfA zuschlagen. | 03 | V1.x |
| Bewegliche Wirtschaftsgüter (Einbauküche, Markise, Photovoltaik) und Außenanlagen als eigene Wirtschaftsgüter | Eigene AfA-Tabellen und Nutzungsdauern. Seite 03 **spaltet sie ab** (`10-F34`) und parkt sie — die Kürzung der Gebäude-BMG passiert also zwingend, die Abschreibung des Guts nicht. | 03 | V2 |
| Veräußerungsgewinn § 23 EStG | `R9` liefert den Restbuchwert und beendet die Reihe. Spekulationsfrist, Gewinnermittlung und Rückgängigmachung der AfA gehören nicht hierher. | 03, 07 | V2 |
| Gebäude im Ausland, Erbbaurecht, Nießbrauch | Jeweils eigene Bemessungsgrundlagen-Logik. | 03 | nicht geplant |
| Automatische Klassifizierung `erweiterung` aus dem Rechnungstext | Eine falsch als Erhaltungsaufwand klassifizierte Erweiterung erzeugt einen unrichtigen Sofortabzug — Haftungsrisiko ohne Nutzergewinn. Pflichtabfrage in der UI. | 03, 02 | nicht geplant |
| Betriebsvermögen (§ 7 Abs. 4 S. 1 Nr. 1 EStG, 3 %) und gewerbliche Einheiten | `R1` blockiert `gebaeudetyp = gewerbe` hart — konsistent zu Seite 02 `R2` Schritt 3. | 03, 02 | V2 |

## Aus Seite 04 · Anlage V + DATEV-Export

| Nicht-Ziel | Begründung | Betroffene Seite | Wiedervorlage |
| --- | --- | --- | --- |
| ELSTER-Direktübermittlung (ERiC) | Eigenes Großprojekt: Zertifizierung, Haftung, StBerG-Grenze. Lokara reicht nie selbst beim Finanzamt ein. | 04 | V3+ |
| DATEV Buchungsdatenservice (REST-API) | Direkte Cloud-Übertragung statt Datei — braucht DATEV-Partnerschaft/Zertifizierung. V1 = importierbare Datei, die jede Kanzlei einlesen kann. | 04 | V2 |
| Belegbild-Übergabe (DATEV Unternehmen online / Belegbilderservice) | Zusammen mit dem Buchungsdatenservice. | 04 | V2 |
| Rückkanal vom StB (Statusabgleich, Korrekturen zurück nach Lokara) | Vision „bidirektionale Brücke"; braucht V2-Infrastruktur. | 04 | V2+ |
| Umsatzsteuer-Logik (BU-Schlüssel, § 9 UStG-Option, Vorsteueraufteilung) | Bestätigt den bestehenden Non-Goal aus Seite 01/02. V1 erkennt und kennzeichnet den USt-Fall nur (11-E12), rechnet ihn nicht. | 04, 01, 02 | V2 |
| § 82b EStDV (Verteilung größeren Erhaltungsaufwands auf 2–5 Jahre) | Jahresübergreifende Zustandsführung (`maintenance_distributions`). V1 zeigt nur einen neutralen Hinweistext (Prüfanregung, StBerG-Grenze). | 04, 03 | V2 |
| Kontenrahmen jenseits SKR03/SKR04 (SKR14, individuelle) | Zwei Standardrahmen decken die private Vermietung ab; alles darüber ist Kanzlei-Sonderfall. | 04 | nicht geplant |
| Verbilligte Vermietung (§ 21 Abs. 2 EStG, 66-%-Grenze) | Bestätigt den bestehenden Non-Goal aus Seite 01/03. Die Kürzung des Werbungskostenabzugs träfe auch die Anlage-V-Summen dieser Seite. | 04, 03 | V2 |

## Aus Seite 05 · Wächter / Fristen

| Nicht-Ziel | Begründung | Betroffene Seite | Wiedervorlage |
| --- | --- | --- | --- |
| Musterschreiben / Textbausteine (Mahnung, Kündigung, Einwendung, Erhöhungsschreiben) | Rechtliche Prüfung und Erstellung sind ein eigener Flow. W5/W3 liefern Fristen und Schwellen, nicht die Texte. | 05, 06 | nach V1 |
| Tatsächlicher Versand (E-Mail-/Push-Infrastruktur) | Seite 05 definiert nur Auslöse-Logik und Eskalationsstufe, nicht den Zustellkanal. | 05 | V1.x |
| „Nicht zu vertreten"-Beurteilung (§ 556 III 3 und 6) | Einzelfallabwägung, nicht formelhaft. Software nimmt den Regelfall an und warnt scharf (KONVENTION-B2). | 05 | nicht geplant |
| Ordentliche Kündigung § 573 | Niedrigere Schwellen und Interessenabwägung. W3 deckt nur den Zahlungsverzug nach § 543 / § 569. | 05 | V2 |
| § 558a Begründungsmittel / Mietspiegel-Beschaffung | Ortsübliche Vergleichsmiete ist Input; keine kostenlose flächendeckende API. VergleichsmieteProvider-Platzhalter, sonst manuelle Eingabe. | 05 | V2 |
| § 559 Modernisierungsmieterhöhung und § 556d Mietpreisbremse | Eigene Rechenmodule. § 559 ist ein separater Weg, nicht durch die ortsübliche Vergleichsmiete gedeckelt. | 05 | W9/W10, nach V1 |
| LandesVO-Listen (angespannter Markt § 558 III 2; Rauchmelderpflicht) | Objekt-Flags. VO-Listen je Bundesland werden nicht mitgeliefert. | 05 | nicht geplant |
| VPI-Umbasierungs-Umrechnung bei Basisjahrwechsel | W7 blockt bei Basisjahr-Mismatch; die Umrechnung alter auf neue Basis ist ein eigener Schritt. | 05 | V2 |
| Verjährung von Nachforderungen (§ 195 BGB) | Eigener Wächter, nicht Teil der Fristenseite. | 05 | V1.x |
| Rechtsberatung / rechtsverbindliche Erklärungen | Software liefert Hinweise, keine Kündigungserklärung. Haftungsabgrenzung. | 05 | nicht geplant |

## Aus Seite 06 · Vertragsklauseln

<table header-row="true">n<tr>n<td>Nicht-Ziel</td>n<td>Begründung</td>n<td>Betroffene Seite</td>n<td>Wiedervorlage</td>n</tr>n<tr>n<td>Gewerberaum-Klauseln</td>n<td>Anderes Formregime (BEG IV: Textform seit 01.01.2025) und andere Inhaltskontrolle als bei Wohnraum.</td>n<td>06</td>n<td>V2</td>n</tr>n<tr>n<td>Staffel-/Index-Mischklauseln in einem Vertrag</td>n<td>§ 557a und § 557b schließen sich gegenseitig aus; eine Kombination ist unwirksam. Der Generator erzwingt Entweder-oder.</td>n<td>06</td>n<td>nicht geplant</td>n</tr>n<tr>n<td>QES-Integration für formgebundene Verträge</td>n<td>V1 bietet nur einfache Signatur (Textform). Staffel/Index (§ 557a/b) und befristet über 1 J. (§ 550) werden gegatet statt digital signiert.</td>n<td>06</td>n<td>V2</td>n</tr>n<tr>n<td>Automatische Prüfung/Berechnung der § 556d-Ausnahmen</td>n<td>Vormiete/Neubau/umfassende Modernisierung sind Tatfragen. In-Scope ist nur die Nutzer-Selbstauskunft (Checkbox) + Warnung + Speicherung, keine Rechtmäßigkeitsprüfung.</td>n<td>06</td>n<td>V2</td>n</tr>n<tr>n<td>Anwaltliche Wirksamkeitsprüfung im Einzelfall</td>n<td>Nur Katalog-Bausteine, kein Rechtsrat. Haftungsabgrenzung.</td>n<td>06</td>n<td>nicht geplant</td>n</tr>n<tr>n<td>Individuell ausgehandelte (nicht formulierte) Klauseln</td>n<td>Keine AGB-Inhaltskontrolle nötig; der Katalog deckt nur Formularklauseln.</td>n<td>06</td>n<td>nicht geplant</td>n</tr>n<tr>n<td>Modernisierungsankündigung (§ 555c, Fristen)</td>n<td>Liegt bei M9 Wächter/Fristen, nicht beim Klauselkatalog.</td>n<td>06, 05</td>n<td>mit Seite 05</td>n</tr>n</table>

</table>

</table>

</table>

---

## Seite 07 · Investment-KPIs (Stand 29.07.2026)

Investment-Modul (Add-on, 4,90 €). Bewusst ausgeschlossen aus V1:

- **N1 — Keine mehrjährige Projektion**, kein Wiederverkauf, kein IRR/Kapitalwert, keine Wertsteigerung. V1 ist eine Ein-Jahres-Momentaufnahme (normalisiertes Volljahr).
- **N2 — Keine AfA-Berechnung** (nur Seite 03) und kein 15 %-Wächter auf dieser Seite. Diese Seite konsumiert nur `jahresAfaVollCent`.
- **N3 — Kein Soli, keine Kirchensteuer**, keine Progressions-/Verlustverrechnungsgrenzen; flacher Grenzsteuersatz (KPI-K13).
- **N4 — Keine variablen Zinsen**, Anschlussfinanzierung, Forward-Darlehen, Sondertilgungs-Optimierung. R3 rechnet die ersten 12 Raten fix.
- **N5 — Stellplatz/Sonstige-Einnahmen** nicht in den Miet-KPIs; gewerbliche Einheiten mit USt ausgeschlossen.
- **N6 — Keine Kauf-/Anlageempfehlung**, kein Gesamtsieger im Vergleich, keine Zielrendite-Defaults. Lokara rechnet und stellt nebeneinander (KPI-K11).
- **N7 — Bank-PDF liefert keinen Beleihungs-/Verkehrswert**, keine Bonitätsauskunft, kein Gutachten; kein automatischer Versand an die Bank (nur Download durch den Nutzer).
- **N8 — Kein automatischer Abruf realer Bankkonditionen**, kein Zins-Vergleichsrechner, keine Anbindung an Finanzierungsvermittler. Zins/Tilgung bleiben Nutzereingabe; die Sensitivität (KPI-K17) variiert nur den angenommenen Satz, sie prognostiziert keinen Marktzins.

**Nachtrag Wizard-Felder Seite 06 (28.07.2026):**

- **SEPA-Lastschrift-Einzug/-Ausführung** — V1 speichert nur die Mandatsdaten (Referenz, Datum); der Einzug braucht PIS + Gläubiger-ID und ist verschoben. Betroffen: 06, Bankanbindung. Wiedervorlage V1.x.n- **Eigennutzungs-Flag** ist In-Scope (Erfassung im Wizard), aber die steuerliche Wirkung (AfA-Basis-Kürzung, keine Anlage-V-Einnahme) liegt auf Seite 03/04, nicht auf Seite 06.

## Aus Seite 08 · Bank-Matching

| Nicht-Ziel | Begründung | Betroffene Seite | Wiedervorlage |
| --- | --- | --- | --- |
| Auszahlung von Guthaben (PIS) | V1 nur AIS. Die Engine markiert ein Guthaben, zahlt es nicht aus. Bestätigt den bestehenden PIS-Non-Goal aus Seite 06/07. | 08, Bankanbindung | V1.x |
| SEPA-Lastschrifteinzug durch Lokara | Findet nicht statt — der Mieter pusht die Zahlung (Dauerauftrag). Lokara zieht nicht ein. | 08 | V1.x (mit PIS) |
| Verzugszinsen-/Mahnkostenberechnung selbst | Liegt bei Seite 05 (§ 543-Wächter). Seite 08 konsumiert nur deren offene Posten in § 367-Reihenfolge. | 08, 05 | mit Seite 05 |
| Mieterübergreifende Verrechnung / Kontokorrent | Jede Zahlung bleibt genau einem Mieter zugeordnet. Keine Saldierung über Mieter hinweg. | 08 | nicht geplant |
| Automatisches Anlegen einer Forderung für eine im Verwendungszweck genannte, nicht existierende Periode | Nennt der Zweck eine Periode ohne Sollstellung, wird keine Forderung erzeugt — der Betrag geht ins Guthaben. Sonst würde die Engine Forderungen erfinden. | 08 | nicht geplant |
| Kategorisierung von Ausgaben/Belegen aus Kontobewegungen | Seite 08 ordnet nur Zahlungseingänge Mietern zu. Ausgabenerfassung ist Rechnungserfassung. | 08 | nicht geplant |