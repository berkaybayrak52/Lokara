# Offene Quellenfragen an Berkay — Runde 5

Emir · Stand 23.08.2026 · nach der Antwort in `Antwort-an-Emir_04.md`

Diese Liste enthält nur nach Runde 4 noch offene Punkte, die Berkay selbst beantworten oder
nachliefern kann. Die genannten Zieldokumente behalten bis dahin ihren offenen Status und ihre
Produktionssperren.

## Seite 01 — Fiktivbelegung und Eigennutzung

Owning doc: `docs/02-data-model.md` § 5 „D0 Fiktivbelegung“, Unterabschnitt
„Assumption, not a transcribed rule: self-use overlapping a vacancy“.

1. Was gilt, wenn eine **anteilige** Eigennutzung (`SelfUsePeriod` ist eine Fläche in m², kein
   Flag) auf einen Leerstandszeitraum derselben Einheit trifft? Seite 01 § 3.5, § 4 D0 und die
   Edge Cases E17–E19 enthalten dazu keine Regel, und im Register gibt es keinen Eintrag dafür.
   Bitte entscheide zwischen:
   a) Die Fiktivbelegung entfällt anteilig zur eigengenutzten Fläche.
   b) Die Fiktivbelegung entfällt für diese Tage vollständig.
   c) Die Fiktivbelegung bleibt für diese Tage unverändert bestehen.

   Lokara rechnet derzeit nach c), ausdrücklich als `Annahme` und
   `verify-before-production`, nicht als Quellregel. Eine volle Eigennutzung nimmt die Tage
   bereits aus dem Leerstand heraus.

2. Falls c) bestätigt wird: Soll der Hinweis auf dem Dokument stehen bleiben? Falls ja, bestätige
   oder ersetze bitte diesen exakten Wortlaut:

   ```text
   <Einheit>: Teil-Eigennutzung (<Fläche> m² von <Gesamtfläche> m²) vom <TT.MM.JJJJ> bis <TT.MM.JJJJ>. Leerstandstage in diesem Zeitraum werden mit Fiktivbelegung gerechnet; die anteilige Eigennutzung ist nicht abgegrenzt.
   ```

## Rechtsstand-Register — behauptete Größenänderung

Owning scope: Source/Register reconciliation.

1. In Runde 4 steht „Registergröße 51 → 62“. Bitte benenne genau, welches Register oder welcher
   Teilbestand gemeint ist, welche Zählregel gilt und welche elf Einträge dazugehören. Das
   autoritative `berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv` hat 180 Zeilen und
   wird aufgrund dieser Angabe nicht geändert.

## Seite 07 — fehlende Begleitdateien

Owning doc: `docs/14-investment-kpis.md` / Page-07-Planung.

1. Bitte sende oder liefere die in Runde 4 als geliefert bezeichneten Dateien erneut:
   `Lokara_Investitionsmodul_Demo.html` und `AfA-Wizard_Konzept_Entwurf.md`. Sie sind im
   Repository nicht vorhanden; ihr Inhalt wird nicht rekonstruiert.

## Nicht erneut erfragt

Runde 4 hat die dort genannten Entscheidungen und Lieferungen zu Seite 01b, Seite 02, AfA,
Eichfrist, den Seite-06-Produktentscheidungen, den Seite-07-Zins- und Zielrenditefragen sowie
UVI-Datensatz und Rundung beantwortet. Diese Punkte werden hier nicht erneut gestellt.

Der vollständige Klauselkatalog mit Textkörpern und der unbestätigte
Wärmepumpen-Warmwasserabzug bleiben offen, sind aber externe Rechts-/Quellenarbeit und keine
Berkay-Nachlieferung dieser Runde.
