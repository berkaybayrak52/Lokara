# Offene Quellenfragen an Berkay — Runde 4

> **ÜBERHOLT — nicht aktuelle Autorität.** Die aktuelle offene Fragenliste ist
> [`FRAGEN-an-Berkay-05.md`](FRAGEN-an-Berkay-05.md). Runde 4 bleibt nur als historischer Stand
> erhalten.

Emir · Stand 21.08.2026 · nach Abschluss des Dokumentationsprogramms D1–D3

Diese Liste enthält nur Entscheidungen oder fehlende Quelldateien, die du liefern kannst. Die
genannten Zieldokumente behalten bis dahin den offenen Status und alle Produktionssperren.

## Seite 01 — Fiktivbelegung und Eigennutzung

Owning doc: `docs/02-data-model.md` § 5 „D0 Fiktivbelegung“, Unterabschnitt
„Assumption, not a transcribed rule: self-use overlapping a vacancy“.

1. Was gilt, wenn eine **anteilige** Eigennutzung (`SelfUsePeriod` ist eine Fläche in m², kein
   Flag) auf einen Leerstandszeitraum derselben Einheit trifft? Seite 01 § 3.5, § 4 D0 und die
   Edge Cases E17–E19 enthalten dazu keine Regel, und im Register gibt es keinen Eintrag dafür.
   Bitte entscheide zwischen drei Möglichkeiten und liefere die Quelle dazu:
   a) die Fiktivbelegung entfällt anteilig zur eigengenutzten Fläche;
   b) die Fiktivbelegung entfällt für diese Tage vollständig;
   c) die Fiktivbelegung bleibt für diese Tage unverändert bestehen.

   Lokara rechnet derzeit nach c) — als ausdrücklich gekennzeichnete Annahme, nicht als
   Quellregel. Begründung der gewählten Richtung: bei a) oder b) müsste eine flächengewichtete
   Personenzahl erfunden werden bzw. die Mieter trügen die personenbezogenen Fixkosten allein,
   was BGH VIII ZR 159/05 und LG Krefeld 2 S 56/09 gerade ablehnen. Eine **volle**
   Eigennutzung nimmt die Tage dagegen aus dem Leerstand heraus; das folgt bereits aus der
   Definition „weder vermietet noch eigengenutzt“ und ist keine Annahme.

2. Falls c) bestätigt wird: soll der Hinweis auf dem Dokument stehen bleiben, und wenn ja, mit
   welchem Wortlaut? Lokara gibt derzeit aus: „<Einheit>: Teil-Eigennutzung (<Fläche> m² von
   <Gesamtfläche> m²) vom <TT.MM.JJJJ> bis <TT.MM.JJJJ>. Leerstandstage in diesem Zeitraum werden
   mit Fiktivbelegung gerechnet; die anteilige Eigennutzung ist nicht abgegrenzt.“

## Seite 01b — Heizkosten und CO₂

Owning docs: `docs/03-nk-heating-engines.md` § 7 Punkte 12 und 14 sowie
`docs/08-statement-document.md` § 5 “Die Eigentümerzeile”.

1. Welche Formulierung soll Block (c), die reine Rundungsdifferenz des Eigentümer-Residuums, in
   Aufstellung und Ausgabe genau tragen?
2. Sollen die drei 3-%-Kürzungsrechte untereinander kumulieren? Seite 01b F25 untersagt das
   Zusammenrechnen mit dem 15-%-Recht; ein Registereintrag beschreibt die 3-%-Rechte als kumulativ.

## Seite 02 — BetrKV-Katalog

Owning doc: `docs/09-betrkv-catalogue.md` §§ 1 und 2.1.

1. Bitte liefere die fehlenden Registerzuordnungen `09-K01`–`09-K11` mit Wert, Quelle,
   Rechtsnatur, Rechtsstand und Flag.
2. Welche Katalogentscheidung gilt für `trinkwasseruntersuchung`: Nr. 2 oder Nr. 17?
3. Welche Katalogentscheidung gilt für `elektropruefung`: Nr. 17 oder nicht umlagefähige
   Instandhaltung?
4. Soll eine individuell ausgehandelte Verwaltungskostenvereinbarung im Wohnraum im Katalog immer
   nicht umlagefähig bleiben, oder gibt es dafür eine gelieferte Quellregel?
5. Bitte liefere die noch fehlenden Wirtschaftlichkeitsbänder oder bestätige, dass außer
   `versicherung` keine weiteren Bänder Teil des Katalogs sein sollen.

## Seite 03 — AfA

Owning doc: `docs/10-afa.md` § 9.

1. Welche K09-Regel gilt beim Nutzungswechsel: voller angefangener Vermietungsmonat
   (`453.798` ct) oder tagesgenaue Aufteilung (`447.887` ct)?

## Seite 05 — Wächter und Fristen

Owning doc: `docs/12-guards-deadlines.md` § 1.

1. Bitte gleiche die widersprüchlichen Quellen zur Eichfrist ab: gelten für Warmwasserzähler und
   Wärmemengenzähler fünf oder sechs Jahre?

## Seite 06 — Vertragsklauseln

Owning doc: `docs/13-contract-clauses.md` § 7.

1. Was soll das Produkt bei einem fallenden Index tun: nur den niedrigeren Wert zeigen oder einen
   konkreten Folgeschritt anbieten?
2. An welchem Ereignistag beginnt das kumulative Sechsjahresfenster nach § 559?
3. Wie wird ein nicht durch drei teilbarer Kautionshöchstbetrag centgenau auf drei Raten verteilt?
4. Bitte liefere ein Worked Example für den Signaturweg eines befristeten Vertrags über mehr als
   ein Jahr.
5. Bitte liefere den vollständigen versionierten Klauselkatalog und die vollständigen Textkörper
   für Mieterhöhung, Kündigung und Mahnung.

## Seite 07 — Investment-KPIs

Owning doc: `docs/14-investment-kpis.md` §§ 1–2 und 11.

1. Welcher Zins steuert das künftige Steuerszenario: der abzugsfähige Zins aus Seite 03 R13 oder
   der Planungszins aus Seite 07 R3?
2. Bitte liefere die in Seite 07 genannten, derzeit fehlenden Dateien
   `Lokara_Investitionsmodul_Demo.html` und `AfA-Wizard_Konzept_Entwurf.md`.
3. Welche Zielrendite- und Default-Policy soll gelten? Bitte liefere die Werte samt Quelle und
   Kennzeichnung als Annahme oder Regel.

## UVI

Owning doc: `docs/16-uvi.md` §§ 7, 8.2 und 16.

1. Bitte liefere den exakten monatlichen DWD-Datensatz und die verbindliche Stations-/PLZ-Zuordnung
   für Block C.
2. Welche Rundungsreihenfolge gilt im Block-C-Beispiel: exakter Quotient mit `-5,4 %` oder
   angezeigte Werte mit `-5,5 %`?
3. Bitte bestätige den Wärmepumpen-Warmwasserabzug von `8 kWh/(m²·a)` und liefere die Regel, wie
   dieser sowie der 24er-Abzug je Heizspiegel-Jahr aktuell gehalten werden.
