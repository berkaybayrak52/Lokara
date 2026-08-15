# Offene Fragen an Berkay — Runde 3

Emir · Stand 14.08.2026 · nach deiner `Antwort-an-Emir_02.md`

Dein Modellwechsel beim Eigentümeranteil ist übernommen und wird gerade verdrahtet — Spec, Fixtures
und Engine in dieser Reihenfolge. Die Kontrollsummen aus deinem § 6 reproduzieren wir **exakt**,
inklusive 1858-statt-1859 und 17.531-statt-17.536. Danke besonders für § 1.4: dass die Herkunft je
Einheit erhalten bleiben muss, während das Display aggregiert, hätten wir sonst beim Kollabieren
verloren — und damit die Leerstandsaufstellung für Anlage V.

Sechs offene Punkte. **1 und 6 sind die einzigen, die etwas von dir brauchen, das wir nicht selbst
entscheiden dürfen** — und **6 blockiert unsere nächste Zeile**; 2 und 3 sind Korrekturen an deinen
eigenen Seiten, die du bereits angekündigt hast; 4 und 5 stehen seit Runde 1 offen und sind in
deiner Antwort nicht vorgekommen.

---

## 1. Der K9-Registereintrag beschreibt jetzt die falsche Rechtsnatur

`Verteilungsrest (K9)` im Rechtsstand-Register führt das **Ziel** des Verteilungsrests als
Konvention — als etwas, das wir uns aussuchen. Dein § 1.4 nimmt uns genau das aus der Hand:

> „Dass der Eigentümeranteil = Residuum ist, ist **meine feste Modellregel**, keine offene
> Konvention. Ihr müsst hier nichts ‚vorläufig als eure Konvention' markieren — setzt es fest um."

Damit zerfällt K9 in zwei Teile mit **unterschiedlicher** Rechtsnatur:

| Teil | Was | Rechtsnatur nach deinem § 1.4 |
| --- | --- | --- |
| Rundungs**richtung** | `round_half_up` je Zeile | unverändert `Konvention` / `verify-before-production` |
| **Ziel** des Rests | die eine Liegenschafts-Eigentümerzeile | **feste Modellregel**, nicht mehr unsere Wahl |

**Frage:** Ziehst du den Registereintrag nach — entweder als zwei Zeilen, oder als eine mit
präzisierter Flag-Spalte? Wir haben ihn **nicht** angefasst: `berkay-work/` ist bei uns
unveränderlich, damit unsere Transkriptionen immer gegen das diffbar bleiben, was du wirklich
geschrieben hast. Bis dahin steht die Unterscheidung nur in unserem `docs/03` § 9.2, und dort
verweist sie auf diesen Punkt.

## 2. Seite 01, `08-F21`: Block (b) steht noch auf `0,00 [Seite 02 pending]`

Deine eigene To-do-Liste auf Seite 02 (Nr. 1) sagt, dass der Wert inzwischen feststeht:
**1.008,00 €** (Verwaltungskosten 420,00 + Hauswart-Instandhaltung/Verwaltung 300,00 +
Rauchwarnmelder-Miete 168,00 + Ziergarten-Instandhaltung 120,00, aus `09-F19`).

**Frage:** Ziehst du `08-F21` nach, oder sollen wir Block (b) bei uns bis zur
Seite-02-Transkription bewusst auf `0,00` mit sichtbarem Vermerk lassen? Wir haben es vorerst als
*ausdrücklich außerhalb dieses Slices* in `docs/08` notiert, mit dem Hinweis, woher der Wert kommt —
damit die `0,00` nicht als abgeschlossener Wert missverstanden wird.

## 3. Deine D2-Spec sagt noch „Wärme+WW"

In § 2 korrigierst du dich selbst: *„meine bisherige D2-Spec ist an dieser Stelle zu korrigieren —
sie sagt aktuell ‚compare against the unit's Wärme+WW'. Das war die schlechtere Wahl."*

**Frage:** Kommt die Korrektur in die Seite selbst? Wir bauen D2 nach (b), also nach deiner Antwort
und nicht nach der Seite. Solange beide existieren und sich widersprechen, ist für einen späteren
Leser nicht erkennbar, welche gewinnt — und unsere Regel ist, dass die Seite gewinnt, nicht die
Mail. Bei uns ist der Vorrang deshalb ausdrücklich vermerkt.

## 4. Emissionsfaktor Erdgas — zwei Werte, zwei Flags (offen seit Runde 1)

Unverändert offen aus `FEEDBACK-to-Berkay-01b.md` § 4a:

- Deine Nachricht nannte Hu **0,2016** / Ho **0,1820**, das Rechtsstand-Register **0,201 / 0,181**.
  Wir rechnen mit den Registerwerten, weil das Register bei uns die Quelle ist.
- Dein `README-for-Emir.md` führt den Erdgas-Faktor unter den Einträgen, die auf
  `verify-before-production` stehen — das Register selbst flaggt ihn anders.

**Frage:** Welcher Wert und welches Flag gelten? Der Unterschied ist klein, aber er sitzt direkt vor
der CO₂-Stufenzuordnung, und dort entscheidet eine Nachkommastelle im Grenzfall über eine ganze
Stufe und damit über den Vermieteranteil.

## 5. CO₂-**Kosten**-Fallback: H2 und unser `docs/03` widersprechen sich (offen seit Runde 1)

Der **Massen**-Fallback (K4/E1) ist verdrahtet und verweigert einen Ho/Hu-Mismatch hart. Der
**Kosten**-Fallback — `co2Cent` aus einem Preis, wenn die Rechnung den Betrag nicht ausweist — ist
es nicht: zwei Regeln widersprechen sich und keine ist entschieden. Wir haben ihn deshalb bewusst
**nicht** gebaut und die Lücke in `docs/03` § 9.5 als solche vermerkt.

**Frage:** Welche Regel gilt? Solange das offen ist, verweigert die Engine lieber, als zu schätzen.

## 6. `R4` (Seite 01b) gegen § 5 Abs. 1 S. 3 CO2KostAufG — Lookup auf dem gerundeten Wert?

Das ist der Punkt, der bei uns die nächste Zeile blockiert. Wir haben **nichts** geändert.

Dein `R4` auf Seite 01b sagt (deine Formulierung):

> „**Emissions** — gram (integer) internally. Display kg with 1 dp, kg/m²/a with 2 dp. **The step
> lookup uses the unrounded value.**"

`E3` schärft das nach: *„Lookup on the unrounded value (R4). Print the floored value, never `12,00`
next to a 0 % share"*, mit `01b-F05` als ausgerechnetem Fixture.

§ 5 Abs. 1 S. 3 CO2KostAufG sagt wörtlich:

> „Der Wert des nach Satz 1 oder Satz 2 ermittelten spezifischen Kohlendioxidausstoßes ist auf die
> **erste Nachkommastelle** zu runden."

Der Satz steht vor der Einstufung und hat sonst keine Funktion — wir lesen ihn deshalb so, dass der
**gerundete** Wert der einzustufende ist. An `01b-F05` entscheidet das den Fall:

| | nach `R4`/`E3` | nach § 5 Abs. 1 S. 3 |
| --- | --- | --- |
| `spezifisch` | 11,999484535… | **12,0** |
| Stufe | 1 → **0 %** | 2 → **10 %** |
| `abzug` | 0 | **1.280** (12,80 €) |
| `umlagefaehig` | 350.600 | **349.320** |

Deine Ausgaberegel hängt mit daran: `11,99` abgeschnitten zu drucken begründest du damit, dass der
Mieter den 0-%-Anteil sonst nicht nachvollziehen kann — bei 10 % entfällt diese Begründung, und nach
S. 3 ist der ausgewiesene Wert ohnehin `12,0`.

**Frage:** Gilt `R4` weiter, oder ersetzt S. 3 ihn? Wir halten S. 3 für vorrangig — `R4` ist bei uns
als Rechenkonvention geführt, S. 3 ist Gesetzestext, und eine Hauskonvention kann eine Norm nicht
verdrängen. Wir setzen aber keine deiner Fixtures gegen deine eigene Regel außer Kraft: `01b-F05`
ist committet, und die Entscheidung ist deine.

**Zusatzfrage, falls S. 3 gilt — in welcher Reihenfolge?** Wir annualisieren nach `H2` die
Intensität und lassen die Anlage-Tabelle ungekürzt; S. 3 rundet den nach S. 1/S. 2 ermittelten Wert,
S. 4 kürzt die Tabelle. Wird also **vor oder nach** der Annualisierung gerundet? `01b-F06`
(28,734770… → 28,7) fällt in beiden Fällen in dieselbe Stufe und entscheidet es nicht. Ohne deine
Festlegung würden wir hier raten, und das tun wir nicht.

**Hinweis zur Nummerierung:** `R4` gibt es auf mehreren deiner Seiten mit unterschiedlicher
Bedeutung (01b = Emissionen, 02 = Schlüssel-Kaskade, 04 = anteiliger Split, 07 = AfA-Bezug). Gemeint
ist hier ausschließlich **`R4` auf Seite 01b**.

---

## Was bei uns läuft

- **Eigentümer-Residuum**: eine Zeile je Liegenschaft und Kostenart, immer gedruckt, ohne Quote,
  Herkunft je Einheit intern erhalten. Beide bisherigen Konventionen aus unserem `docs/03` § 9.2
  sind als **superseded** markiert und durchgestrichen dokumentiert, damit sie niemand
  „wiederherstellt".
- **Nur die Heizungs-Engine** stellt in diesem Schritt um. Die NK-Engine bleibt vorerst auf
  Largest-Remainder — nicht aus Bequemlichkeit: das Residuum-Modell **setzt** zeilenweises
  `round_half_up` voraus, denn unter Largest-Remainder summieren sich die Mieteranteile auf den
  ganzen Topf und der Eigentümer bekäme strukturell 0. Die Umstellung gehört damit in die
  Seite-02-Transkription, weil sie jede NK-Zahl bewegt.
- **D2** bauen wir nach (b), mit `mittel − ww_kwh_m2`, Wärmepumpe 8 statt 24 als klar gelabelte
  Konvention, Negativ-Guard, und `über-500` für Wärmepumpe/Pellets als **gelabelter** Rückfall auf
  250–500. Wir extrapolieren nichts.
- **`geprüft`** führen wir jetzt ausdrücklich als „Normtext an der Primärquelle gegengelesen" —
  nicht als anwaltlich bestätigt. GEG § 82 und die Rechtsnatur der Emissionsfaktoren bleiben als
  noch-nicht-final markiert.
- **Registerfassung**: die maßgebliche Fassung liegt jetzt als eine kanonische Datei unter
  `berkay-work/Rechtsstand-Register/` (7 Flags mehr auf `geprüft`). Die Datumsstempel ab dem
  nächsten Export lösen das dauerhaft.
