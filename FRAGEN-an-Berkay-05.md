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

## Seite 08 — Bank-Matching

Owning doc: `docs/15-bank-matching.md` § 4 und § 5.2.

1. **§ 5.2 — Tie-Break bei gleichen Nachkommaresten.** Die Aufteilung einer Teil-Tilgung auf die
   Nominalkomponenten nutzt Largest Remainder. Seite 08 legt nicht fest, welche Komponente den
   letzten Cent erhält, wenn zwei Reste exakt gleich sind. § 5.2 hält diese Lücke selbst fest.
   Bitte gib eine deterministische Regel vor. Vorschlag: feste Komponentenreihenfolge
   `base_rent`, `nk_advance`, `heating_advance`, `garage`.

   Lokara erfindet hier keine Reihenfolge. Die Engine wirft bei exaktem Gleichstand
   `TieBreakUnspecifiedError`. `F11` (78.704 / 13.889 / 7.407 Cent) erreicht diesen Zweig nicht,
   also ist die Regel durch keine Fixture belegt.

2. **§ 4 — „stored reference“.** Die Signaltabelle in § 4 vergibt 15 Punkte, wenn die E2E- oder
   Mandatsreferenz der Buchung zu einer „stored reference“ passt. § 3.2 (`Receivable`) und § 3.3
   (`RenterMatchingProfile`, `IbanHistory`) definieren kein solches Feld. Bitte benenne, welches
   Feld die Referenz trägt:
   a) `payment_code` aus dem `RenterMatchingProfile`,
   b) eine eigene Referenz je Forderung (`Receivable`),
   c) ein neues, bisher nicht beschriebenes Profilfeld.

   Bitte sage zusätzlich, ob eine Mandatsreferenz allein bereits zählt oder nur die
   E2E-Referenz. Bis zur Antwort liefert das Signal 0 Punkte; kein Fixture belegt es, und
   +15 kann eine Buchung von `Unmatched` auf `Needs Review` heben.

Beide Punkte bleiben `verify-before-production` und blockieren nichts anderes. Die
Matching-Gewichte und die Schwellen 40/79 bleiben unabhängig davon Lokara-Konvention und sind
keine rechtliche Grundlage für einen Treffer.

## Seite 08 — Folgefragen aus der Umsetzung (M6-C3)

Owning doc: `docs/15-bank-matching.md` §§ 3.2, 4 und 5.1.

Diese drei Punkte sind erst bei der Umsetzung von M6-C2/M6-C3 aufgetreten. Sie stehen in keiner
Quelle. **Lokara handhabt sie vorläufig so, wie unten beschrieben, und ist dadurch nicht
blockiert** — aber jede dieser Zwischenlösungen ist eine Lokara-Entscheidung ohne Quellgrundlage
und muss mit Berkay geklärt werden, bevor sie produktiv gilt. Alle drei bleiben
`verify-before-production`.

1. **Gesamtschuldnerische Mietverhältnisse — Aufteilung einer Nachzahlung.** § 3.2 legt die
   Forderung je Mieter an, `TenancyParty` lässt jedoch mehrere Mieter auf einem Mietvertrag zu
   (Ehepaar, WG), und keine Quelle sagt, wie **eine** Nachzahlung aus Seite 01 auf sie verteilt
   wird. Bitte entscheide zwischen:
   a) Gesamtschuld nach § 421 BGB: **eine** Forderung über den vollen Betrag, jeder Mieter haftet
      auf das Ganze;
   b) Aufteilung nach Kopfteilen auf je eine Forderung pro Mieter;
   c) eine andere, von dir vorgegebene Regel.

   Lokara **verweigert derzeit** die Erzeugung (HTTP 409) und wählt keinen Mieter aus. Der Grund
   ist konkret: `Session.scalar()` hätte einen beliebigen Ehepartner genommen und die übrigen
   stillschweigend verworfen — dann findet die Zahlung des anderen Ehepartners keine Forderung und
   landet ohne Warnung auf `Unmatched`. § 421 BGB ist die wahrscheinliche Antwort, aber Lokara
   setzt sie nicht ohne deine Bestätigung um.

2. **Mieterguthaben aus Überzahlung — spätere Verwendung.** § 5.1 sagt, dass ein Restbetrag nach
   vollständiger Tilgung zu Mieterguthaben wird und **nicht ausgezahlt** wird (V1, § 9). Ob dieses
   Guthaben eine **später entstehende** Forderung automatisch mindert, sagt keine Quelle. `F04`
   erzeugt genau diesen Fall mit 4.000 Cent Restguthaben. Bitte entscheide:
   a) Das Guthaben wird bei der nächsten fällig werdenden Forderung automatisch verrechnet.
   b) Das Guthaben bleibt stehen, bis der Vermieter es ausdrücklich verrechnet.
   c) Das Guthaben wird nur nachrichtlich geführt und nie verrechnet.

   Lokaras Engine- und Persistenzvertrag folgt derzeit c): das Guthaben wird in
   `payment_ledger_entry.credit_cents` festgeschrieben und mindert keine spätere Forderung von
   selbst. Der *Zahlungen*-Bildschirm ist noch nicht implementiert; die spätere Anzeige darf diese
   Zwischenlösung nur sichtbar machen, nicht erweitern. Eine automatische Verrechnung würde
   Mietergeld ohne Quellregel bewegen.

3. **Ablehnung eines Vorschlags und manuelle Zuordnung.** § 4 beschreibt nur die *Bestätigung*
   („Confirmation records the actor and time"). Nicht beschrieben ist, (i) was eine **Ablehnung**
   auslöst und ob die Buchung danach erneut bewertet werden darf, und (ii) ob der Vermieter eine
   `Unmatched`-Buchung **von Hand** einer beliebigen offenen Forderung zuordnen darf. `F05` ist
   genau dieser Fall: zwei Kandidaten mit je 30 Punkten, `Unmatched`, nichts zugewiesen.

   Lokaras Engine- und Persistenzvertrag sieht derzeit vor: eine spätere Ablehnung schreibt
   `match_confirmation.outcome` fort und verrechnet **nichts**; die Forderung bleibt unberührt.
   Matching-Service und *Zahlungen*-Bildschirm sind noch nicht implementiert, daher kann heute
   niemand dort ablehnen oder manuell zuordnen. Eine frei wählbare Zuordnung wäre ein Tilgungsweg
   ohne Quelle, also genau die erfundene Konvention, die in M6-C1 aus § 4 entfernt wurde. Für den
   Vermieter würde das in V1 bedeuten, dass er einen erkannten Zahlungseingang nicht selbst
   zuordnen kann — bitte sag, ob das so bleiben soll.

## Nicht erneut erfragt

Runde 4 hat die dort genannten Entscheidungen und Lieferungen zu Seite 01b, Seite 02, AfA,
Eichfrist, den Seite-06-Produktentscheidungen, den Seite-07-Zins- und Zielrenditefragen sowie
UVI-Datensatz und Rundung beantwortet. Diese Punkte werden hier nicht erneut gestellt.

Der vollständige Klauselkatalog mit Textkörpern und der unbestätigte
Wärmepumpen-Warmwasserabzug bleiben offen, sind aber externe Rechts-/Quellenarbeit und keine
Berkay-Nachlieferung dieser Runde.
