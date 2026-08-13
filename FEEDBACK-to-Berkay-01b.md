# Feedback zu Seite 01b — Stand nach Transkription und Implementierung

Emir · nach dem Merge von `slice/berkay-01b-rules`

Antworte gern auf Deutsch — die Zweisprachigkeit war bisher kein Problem.

---

## Kurzfassung

Seite 01b ist transkribiert und implementiert. Vier Regeländerungen sind eingebaut, 422 Tests
grün. Dein Ho/Hu-Vorschlag wurde **unverändert übernommen**.

Unten: **eine echte Abweichung** (01b-F19), **zwei Fehlalarme von unserer Seite** (F16/F26 —
unser Lesefehler, deine Zahlen stimmen), **zwei Inkonsistenzen innerhalb deiner Unterlagen**,
und **vier Punkte, die noch bei dir offen sind**.

---

## 1. Übernommen — dein Ho/Hu-Design, unverändert

Die Bezugsgröße reist auf beiden Seiten mit: das Faktorobjekt trägt `bezug: "Ho" | "Hu"`, die
kWh-Eingabe trägt dieselbe Angabe, Rechnungen sind Ho → es wird direkt der Ho-Faktor benutzt.
**Kein Umrechnungsschritt irgendwo.**

Zwei Gründe, warum das besser war als die ×0,903-Korrektur:

- Es spiegelt ein Muster, das wir schon haben — die Maßeinheit reist beim Zählerstand mit,
  statt stromabwärts angenommen zu werden. Ein Bezugs-Mismatch ist jetzt ein harter Fehler,
  nicht eine stille Fehlinterpretation.
- Es macht die Frage 0,90 vs. 0,903 gegenstandslos, weil nie umgerechnet wird.

Ebenfalls aus 01b übernommen: **K3** (deine VDI-Tabelle), **R1/R5/K9** (`round_half_up` je
Anteil, Verteilungsrest an den Eigentümer) und **H2** (annualisieren, dann ungekürzte Tabelle) —
letzteres ersetzt unsere bisherige Lesart von § 5 Abs. 1 S. 4.

---

## 2. Eine echte Abweichung — `01b-F19`, Gegenbeispiel

Nur das **Gegenbeispiel** („Falle") am Ende, nicht die Hauptrechnung. Die Hauptrechnung
(5.600 l, Ø 97,324675 ct/l, 545.018 / 204.382, Probe 749.400) reproduziert exakt.

Nachgerechnet für CO₂ auf die **gekauften** 7.700 l:

```
Energie   = 7.700 × 10                     = 77.000 kWh
co2Gramm  = 77.000 × 0,266 × 1000          = 20.482.000 g  = 20.482 kg   ✓ (wie im Spec)
spezifisch= 20.482 / 420                   = 48,766…  → Stufe 47–<52 → 80 %  ✓
co2Cent   = 20.482/1000 × 5.500            = 112.651 ct
abzug     = round_half_up(112.651 × 0,80)  = 90.121 ct
```

**Spec sagt `abzug` = 90.204 ct. Wir kommen auf 90.121 ct. Differenz 83 ct.**

Folgefehler: die im Spec genannte Differenz **492,40 €** wäre nach unserer Rechnung
**491,57 €** (90.121 − 40.964 = 49.157 ct).

Die Aussage der Falle bleibt natürlich unberührt — der Fehler ist groß und geht zu Lasten des
Mieters. Nur die beiden Zahlen wären zu korrigieren.

---

## 3. Zwei Fehlalarme — unser Lesefehler, nicht deiner

Wir hatten zunächst `01b-F16` und `01b-F26` als abweichend gemeldet. **Das war falsch, und der
Grund ist lehrreich genug, um ihn festzuhalten.**

Bei `01b-F26` steht für den unerfassten Rest **4.227 ct**. Wir hatten 4.228 gerechnet:

| Weg | Ergebnis |
| --- | --- |
| `round_half_up(82.440 × 4 / 78)` — als eigener Anteil gerechnet | 4.228 |
| **82.440 − (35.935 + 15.854 + 6.342 + 20.082)** — als Verteilungsrest nach K9 | **4.227** ✓ |

Der Eigentümer-Eimer ist **kein gerundeter Anteil, sondern der Verteilungsrest**. Genau das
sagt K9, und deine Zahl ist die richtige. Unsere Implementierung hatte an dieser Stelle die
Anteilsformel auch auf den Eigentümer angewandt — das ist bei uns ein Bug, kein Spec-Fehler,
und wird korrigiert.

`01b-F16` haben wir daraufhin komplett nachgerechnet (Nenner 10.750,0; Muster 58.854 ·
Schneider 30.831 · Weber 20.154 · Beispiel 43.782 · Leerstand 692; Summe 154.313, Rest 0). Es
reproduziert **exakt**. Ebenfalls kein Befund.

Damit steht: **von 31 Fixtures auf 01b weicht genau eines ab, und nur in seinem
Gegenbeispiel.** Dein „0 Rechenfehler" hält im Kern.

---

## 4. Zwei Inkonsistenzen innerhalb deiner Unterlagen

**4a — Emissionsfaktor Erdgas, zwei Werte.**
Deine Nachricht: Hu **0,2016** / Ho **0,1820**.
Das Rechtsstand-Register: **0,201 / 0,181**.

Wir haben das **Register** genommen, weil bei uns die Regel gilt: das Register ist die
strukturierte Quelle, die Prosa ist Kommentar. Welcher Wert soll maßgeblich sein? Dieselbe
Frage für Heizöl und Flüssiggas.

**4b — Flag-Widerspruch.**
Dein `README-for-Emir` führt den Erdgas-Emissionsfaktor unter den 8 Einträgen, die auf
**`geprüft`** gesetzt wurden. Die Registerzeile steht weiterhin auf
**`verify-before-production`**.

Wir haben `verify-before-production` durchgereicht (konservativ). Einer der beiden Stände
müsste angepasst werden.

---

## 5. Was wir mit deinen Seiten gemacht haben — und warum nicht kopiert

Wir kopieren deine `.md`-Dateien **nicht** in `docs/`, sondern transkribieren sie:

- Es sind Notion-Exporte mit Hash-Suffixen und URL-kodierten Links auf `.csv`-Dateien, die es
  bei uns nicht gibt.
- Sie adressieren „Seite 01b", nicht `docs/03` — das globale Umbenennen der Fixtures stand ja
  selbst in deiner README als To-do für uns.
- Abschnitt 6 sind 183 durchgerechnete Beispiele. Bei uns gehören die in die Testsuite, nicht
  in ein Dokument.
- Eine wörtliche Kopie hinterließe zwei nicht synchronisierte Fassungen jeder Regel.

**Dein Ordner liegt unverändert im Repo und gilt als unantastbar** — so lässt sich jede
Transkription jederzeit gegen das diffen, was du tatsächlich geschrieben hast. Niemand editiert
darin, auch keine Tippfehler.

**Eine Ausnahme:** das Rechtsstand-Register (CSV) geht fast unverändert in unseren
`rules-store` — es ist bereits strukturierte Daten.

**Jeder Wert behält seine Flags:** Rechtsnatur, Rechtsstand, Quell-URL sowie
`verify-before-production` vs. `geprüft`. Nichts wird bei der Transkription zur Tatsache
befördert. Bei uns liegen 137 von 180 Einträgen weiterhin auf `verify-before-production`.

---

## 6. Nebenbei: K3 hat eine sichtbare Zahl bewegt

Deine Korrektur der Gradtagszahltabelle hat die Nutzerwechsel-Aufteilung in unserem Demo
verschoben: **585/415 ‰ → 583,3/416,7 ‰**, in Euro 778,79/552,47 → **776,52/554,74**.

Die Summe bleibt gleich (1.331,26 €) — es ist eine Um-Verteilung, keine Preisänderung. Nur
damit du es weißt, falls du irgendwo einen älteren Screenshot siehst.

---

## 7. Als Nächstes: Seite 02 (BetrKV)

Das ist bei uns der Punkt mit dem besten Aufwand-Nutzen-Verhältnis, weil **zwei bereits
gebaute Screens darauf warten**: die Kostenerfassung und der OCR-Prüfschritt nehmen heute ein
freies Textfeld, und wir haben bewusst **keinen** Umlageschlüssel aus der Kostenart abgeleitet,
solange der Katalog fehlt — eine geratene Zuordnung wäre erfundenes Recht.

---

## 8. Vier Punkte, die noch bei dir liegen

1. **CO₂-Preis ab 2026.** In deinen Non-Goals als offen vermerkt — kein Einheitspreis, Korridor
   55–65 €/t, Verkaufsphase 68 €, Nachkauf 70 €. Wir können keinen Zeitraum ab 2026 rechnen,
   bis das entschieden ist. Nutzerabfrage oder harte Blockade?
2. **§ 6a Abs. 3 S. 4 Bekanntmachung** — in deiner Rechtsgrundlagen-Tabelle als „nicht
   gefunden" markiert. Inzwischen geklärt?
3. **`DWD-Klimafaktoren-Import-Spec.md`** — in K12 referenziert, liegt dem Ordner nicht bei.
4. **K13 / Durchschnittsnutzer.** Wir haben deine Lesart übernommen: der Verweis ist nur für
   die **Jahresabrechnung** zulässig, **nicht** für die UVI. Damit braucht die UVI echte
   Vergleichswerte — das ist eher eine Datenbeschaffungs- als eine Rechenfrage. Hast du eine
   Vorstellung, woher die kommen, bevor wir die vierstellige Objektzahl für eigene Werte haben?
