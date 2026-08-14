# Antwort auf deine Fragen Runde 2 — Berkay

Berkay · Stand 14.08.2026 · Antwort auf `FRAGENanBerkay02.md`

An Emir **und** an Claude im Lokara-Repo. Wo unten „ihr" steht, meine ich die Engine-Seite.

Vorab, weil es das ganze Dokument prägt: Ich habe jede Zahl und jede Regel hier **mehrfach und aus
mehreren Richtungen gegengeprüft** (Herleitung, Gegenrechnung, Größenordnungs-Plausibilität,
Grenzfälle). Wo eine Aussage nur *plausibel*, aber nicht *bewiesen* ist, steht das ausdrücklich dabei.
Der letzte Abschnitt (§6, „Selbstprüfung") listet die Kontrollen offen auf, damit ihr sie
nachvollziehen und selbst nachrechnen könnt — bitte tut das, verlasst euch nicht auf mein Wort.

---

## 1. Der Eigentümer-Topf — das ist kein Randfall, sondern ein Modellunterschied ⚠️

Eure Fall-A/Fall-B-Aufteilung entsteht, weil eure Engine und meine Spec den Eigentümeranteil
**unterschiedlich denken**. Das ist die eigentliche Ursache, nicht die Rundung. Wenn wir das Modell
angleichen, verschwinden **beide** Fälle. Bitte lest diesen Abschnitt ganz, bevor ihr Code anfasst.

### 1.1 Wie mein Modell den Eigentümeranteil definiert

In meiner Spec ist der Eigentümeranteil **keine Partei** und wird **nicht aus Belegungszeiträumen
abgeleitet**. Er ist eine **strukturelle Abstimmungszeile pro Liegenschaft und Kostenart** — ein
reines Residuum:

```
eigentuemeranteilCent[kostenart] = gesamtbetragCent[kostenart] − Σ mieteranteilCent[kostenart]
```

Quelle: Seite 01, Block **D12**, wörtlich: *„ALWAYS as a residual, NEVER computed separately"*.
Der Grund dafür ist genau das, was ihr mit K9 schützen wollt: Wenn der Eigentümeranteil das
Residuum ist, dann erklärt **eine** Zeile jeden ±ct der Abrechnung, und die Kontrollsumme

```
Σ umgelegt + Eigentümeranteil = Gesamtkosten
```

geht **per Konstruktion** auf 0 auf. Es gibt in meinem Modell keinen Zustand, in dem ein Rest
„übrig bleibt und keinen Topf hat" — der Topf **ist** der Rest.

### 1.2 Warum euer Fall A und Fall B entstehen — und wie sie verschwinden

Ihr leitet Parteien aus Belegung ab und bekommt dadurch:

- **eine Vermieterpartei je leerstehender/eigengenutzter Einheit** → euer Fall A (mehrere Töpfe),
- **null Vermieterparteien bei Vollvermietung** → euer Fall B (kein Topf).

In meinem Modell gibt es **immer genau einen** Eigentümer-Topf pro Liegenschaft — unabhängig von
Leerstand, unabhängig von Belegung. Deshalb:

> **Bitte kollabiert die aus Belegung abgeleiteten Vermieterparteien zu einem einzigen
> Liegenschafts-Residuum pro Kostenart.** Nicht „erste Partei in deterministischer Reihenfolge",
> sondern **eine** Residuumszeile, die es strukturell immer gibt.

Damit ist Fall A gelöst (es gibt nur einen Topf, also keine Frage „welcher zuerst") **und** Fall B
gelöst (der Topf existiert auch bei Vollvermietung). Eure Sorge — „stille Verschiebung zwischen
Mietern, wenn der Rest an einen Mieter geht" — ist vollkommen richtig und wird durch dieses Modell
gerade **verhindert**: Der Rest landet immer beim Eigentümer, nie bei einem Mieter. Kein
Largest-Remainder-Sonderweg für „Fall B" nötig, weil es Fall B nicht mehr gibt.

### 1.3 Eure drei konkreten Fragen

**Frage 1 — Existiert die Eigentümerzeile immer? → Ja.**
Auch bei 0,00 €, auch ohne Leerstand, auch ohne Eigennutzung. Beweis aus meinem eigenen Fixture
**08-F06** (Vermieter-Gesamtübersicht): dort steht die Eigentümerspalte für *Wasserversorgung,
Entwässerung und Heizkosten* explizit auf **`0,00`**, während sie bei Grundsteuer 31,74 € trägt.
Die Zeile ist die Kontrollsummen-/Residuumszeile und wird immer gedruckt.

**Frage 2 — Was steht als Bemessung darin? → Keine gedruckte Quote.**
Der **Betrag** ist immer das Residuum, nie „Bemessung × Quote". Zwei Unterfälle:

- **Mit Leerstand/Eigennutzung:** Die Zeile trägt die **Fiktivbelegung** (D0) der leeren Einheiten
  als Bemessung — m²-Tage / Personen-Tage / HKV-Einheiten der fiktiven Belegung. Aber der
  ausgewiesene Betrag bleibt das Residuum. Beweis Fixture **08-F22**: das Residuum ist **1858**,
  *nicht* die separat gerechneten **1859** — Kommentar in der Spec: „residual wins". Und **08-F21**
  (Leerstandsaufstellung): separat gerechnet 17.536, als Residuum 17.531, die 5 ct Differenz sind
  die zeilenweise Rundung und werden als Block (c) offen ausgewiesen.
- **Ohne Leerstand, ohne Eigennutzung:** Bemessung 0 bzw. leer. Die Zeile trägt dann nur die
  **Rundungsdifferenz** (Block c) — typischerweise wenige Cent, oft 0,00 €.

> **Wichtig fürs Rendering:** Druckt in der Eigentümerzeile **keine** Quote/Prozentzahl. Eine
> gedruckte Quote würde eine Verteilungsbasis suggerieren, die es nicht gibt — der Betrag ist ein
> Rest, keine Quote. Bemessungsspalte bei der Eigentümerzeile also leer lassen (bzw. nur die
> Fiktivbelegungs-Bemessung zeigen, wo es eine gibt), und **nur den Betrag** ausweisen.

**Frage 3 — Wenn es keinen Topf gäbe, wohin mit dem Rest?**
Entfällt, weil der Topf in meinem Modell immer existiert (siehe 1.2). Euer Largest-Remainder-Vorschlag
für den Rest ist damit **nicht** nötig und soll **nicht** verwendet werden — der Rest geht in das
Liegenschafts-Residuum, in **allen vier Blöcken in dieselbe Zeile**. Das ist genau euer eigener
Wunsch aus Fall A, nur ohne die Mehrdeutigkeit „welche Partei".

### 1.4 Ein Detail, das ihr nicht verlieren dürft

Das **Display** zeigt einen Eigentümer-Topf pro Liegenschaft. Die **steuerliche Anlage**
(Leerstandsaufstellung, D12) schlüsselt den (a)-Teil — Leerstandsanteil als Werbungskosten — aber
weiterhin **je leerer Einheit und Kostenart** auf, weil der Vermieter das für Anlage V je Objekt
braucht. Also intern die Herkunft je Einheit mitführen, im Gesamtübersicht-Display zu **einer**
Zeile aggregieren. Der (c)-Teil (Rundungsdifferenz) gehört keiner Einheit und wird separat
ausgewiesen. Das ist kein Widerspruch zu 1.1 — Aggregation im Display, Herkunft in den Daten.

**Rechtsnatur:** Dass der Eigentümeranteil = Residuum ist, ist **meine feste Modellregel**, keine
offene Konvention. Ihr müsst hier nichts „vorläufig als eure Konvention" markieren — setzt es fest um.

---

## 2. Block D2: Warmwasser — Entscheidung (b), mit Quelle und Grenzfall

**Entscheidung: (b).** Warmwasser aus dem Normwert herausrechnen, damit **beide Seiten reine
Heizung** sind. Begründung in einem Satz: Die Blöcke A/B/C zeigen dem Mieter reine Heizung (WW ist
nach §9 HeizkostenV abgetrennt); vergliche D2 gegen einen Wärme+WW-Normwert, wären die eigene Zahl
des Mieters und der Vergleichswert **zwei verschiedene Größen** und die Prozentzahl irreführend.

Das heißt zugleich: **meine bisherige D2-Spec ist an dieser Stelle zu korrigieren** — sie sagt aktuell
„compare against the unit's Wärme+WW". Das war die schlechtere Wahl. Bitte auf (b) umstellen.

### 2.1 Der Abzug — Wert und Quelle

Ihr habt nach „fester kWh/m²-Abzug, prozentual oder je Energieträger, und die Quelle" gefragt.
Antwort: **fester kWh/m²-Abzug je Energieträger.**

co2online beziffert den Warmwasser-Anteil in der Heizspiegel-Methodik selbst: für Gebäude mit
**dezentraler** Warmwasserbereitung wird ein Warmwasser-**Zuschlag** von **24 kWh/(m²·a)**
addiert (Korb Erdgas/Heizöl/Fernwärme/Holzpellets, ~11 ct/kWh). Umgekehrt gelesen: genau diese
**24 kWh/(m²·a)** stecken als Warmwasser in den `mittel`-Werten für zentrale WW-Bereitung. Also:

```
mittel_waerme_only[energietraeger] = mittel[energietraeger] − ww_kwh_m2[energietraeger]
```

mit `ww_kwh_m2`:

| Energieträger | ww_kwh_m2 (a) | Herkunft |
| --- | --- | --- |
| Erdgas | 24 | co2online Heizspiegel-Methodik (dezentral-Zuschlag) |
| Heizöl | 24 | dito |
| Fernwärme | 24 | dito (co2online nennt Fernwärme im selben Korb) |
| Holzpellets | 24 | dito |
| **Wärmepumpe** | **≈ 8** | **abweichend — siehe 2.2, Konvention, mit co2online bestätigen** |

Quelle: co2online gGmbH, Heizspiegel-Methodik (Warmwasser-Zuschlag dezentrale Bereitung),
`co2online.de/energie-sparen/heizspiegel/…`. **Verifikations-TODO:** den Wert je Heizspiegel-Jahrgang
gegen die dann aktuelle Methodik prüfen — co2online hat ihn über die Jahre verändert (früher ~18).
In den `rules-store` unter K13 mit As-of-Jahr, wie die Normwerte selbst.

### 2.2 Der Grenzfall, den der Pentest gefunden hat: Wärmepumpe ⚠️

Ein flacher 24er-Abzug ist für Wärmepumpe **falsch** und hätte einen unsinnigen Wert erzeugt. Nachweis:

```
Wärmepumpe, Klasse 80–150, mittel = 36 kWh/m²·a
36 − 24 = 12 kWh/m²·a reine Heizung   → unplausibel niedrig
```

Grund: Heizspiegel-Wärmepumpenwerte sind **Strom**-kWh (Endenergie nach COP), Verbrenner-Werte sind
Brennstoff-kWh. Der WW-Wärmebedarf von ~24 kWh/m² erscheint bei der Wärmepumpe nur mit dem Faktor
1/JAZ als Strom. Bei JAZ ≈ 3 → **≈ 8 kWh/(m²·a)**:

```
36 − 8 = 28 kWh/m²·a reine Heizung   → plausibel
```

Deshalb der abweichende Wert 8 in der Tabelle. Er ist eine **Konvention** (JAZ-Annahme), klar so
gelabelt, und sollte mit co2online bestätigt werden — co2online nennt für Wärmepumpen einen eigenen,
niedrigeren WW-Zuschlag (dort als €/m² statt kWh/m²). **Guard einbauen:**
`if (mittel − ww) <= 0 → data-quality-flag, nicht rendern`.

### 2.3 Physik-Bonus von (b): die Monatsverteilung wird sogar korrekter

Ein zweiter Grund für (b), der über die reine Konsistenz hinausgeht: D2 verteilt den Jahres-Normwert
über `dd_share(Monat)` (Gradtagsanteil). Warmwasser ist aber **übers Jahr ungefähr konstant**
(im Sommer wird auch geduscht), Raumwärme ist saisonal. Unter (a) würde man WW fälschlich mit dem
Heiz-Gradtagsprofil saisonalisieren. Unter (b) wird WW **vorher** herausgerechnet und nur die reine
Heizung mit `dd_share` verteilt — das ist physikalisch richtiger. (b) ist also nicht nur konsistenter,
sondern in der Monatszerlegung schlicht korrekter.

### 2.4 Golden Tests, die ihr dafür setzen müsst

- Norm-Herleitung je Energieträger: `mittel − ww_kwh_m2` gegen erwartete Wärme-only-Werte.
- Wärmepumpe-Sonderwert (8, nicht 24) — eigener Test, damit niemand ihn versehentlich auf 24 zieht.
- Negativ-Guard `(mittel − ww) <= 0`.
- Ein Ende-zu-Ende-Beispiel (neu gerechnet, ersetzt das alte Wärme+WW-Beispiel):

```
Erdgas, Klasse 250–500, mittel 114 → Wärme-only 114 − 24 = 90 kWh/m²·a
Einheit 80 m², Januar, dd_share(Jan) = 0,19
norm_annual = 90 × 80            = 7.200 kWh/a
norm_month  = 7.200 × 0,19       = 1.368 kWh
kwh_current (reine Heizung, Jan) =  1.500 kWh   (Block-A-Ausgabe, NICHT Wärme+WW)
delta = 1.500 − 1.368 = +132 kWh ; pct = 132 / 1.368 × 100 = +9,6 %
Ausweis: „normierter Durchschnittsnutzer 1.368 kWh, +132 kWh, +9,6 %,
          Quelle: co2online gGmbH (Heizspiegel)"
```

Wichtig im Test festhalten: `kwh_current` ist die **reine-Heizung**-Zahl aus Block A — genau die
Zahl, die der Mieter auch in A/B/C sieht. Damit sind beide Seiten dieselbe Größe.

---

## 3. Block D2: die Lücke „über 500 m²"

Kleine Korrektur zu eurer Frage: Die Klasse **über-500 ist nicht komplett leer**. In der CSV stehen
über-500-Werte für **Erdgas, Heizöl und Fernwärme**. Es fehlen **nur zwei Zellen**: **Wärmepumpe**
und **Holzpellets** in über-500. Die Lücke ist also eng.

**Wichtig — diese zwei Werte sind öffentlich nicht verfügbar.** Ich habe die offizielle
Heizspiegel-2025-Tabelle (Abrechnungsjahr 2024) gegengeprüft: Wärmepumpe und Holzpellets stimmen
für 80–150 / 150–250 / 250–500 **exakt** mit unserer CSV überein — und für **über-500 sind beide in
der veröffentlichten Tabelle nicht enthalten** („fehlt"). Sie wurden also nicht nur im Flyer
weggelassen, sondern sind im öffentlichen Datensatz gar nicht abgedruckt (co2online hat für diese
seltene Kombination vermutlich zu dünne Datenbasis). Die Kommentarzeile in der CSV
(„aus der Voll-Tabelle nachtragen") ist damit **überholt** — eine öffentliche Voll-Tabelle mit
diesen zwei Zellen existiert nicht.

**Woher die Werte dann kommen:** nur direkt von co2online. Berkay fragt die zwei Zellen (über-500
Wärmepumpe + Holzpellets, alle vier Stufen niedrig/mittel/erhöht/zu-hoch) per Mail bei **Frau Weikamp
(Leitung Geschäftsfeldentwicklung und Kooperationen, co2online)** an — gebündelt mit der ohnehin
geplanten Lizenz-Mail (§6a-UVI-Nutzung). Bis die Antwort da ist, gilt der Fallback unten.
**Bitte keine Werte selbst extrapolieren** — die Größenklassen sind nicht monoton (siehe unten),
eine Hochrechnung wäre in einem §6a-Dokument nicht vertretbar.

> **Emir: bau den Fallback als Übergangslösung fest in den MVP ein** (250–500 mit sichtbarem Label,
> siehe unten). Nicht auf die co2online-Antwort warten — der MVP muss diese zwei Kombinationen jetzt
> schon normkonform bedienen. Sobald Berkay die Werte hat, werden nur die zwei CSV-Zellen ergänzt und
> der Fallback greift für sie automatisch nicht mehr.

**Was D2 bis dahin tun soll:** Auf die nächstkleinere Klasse **250–500 ausweichen**, mit **sichtbarem
Label** („Vergleichswert der Größenklasse 250–500 m²; für über 500 m² liegt für diesen Energieträger
noch kein Wert vor"). Begründung: §6a Abs. 2 Nr. 3 hat **keine** Ausweichklausel — genau deshalb gibt
es D2 überhaupt. „Vergleich weglassen" oder „nur Hinweis ohne Wert" = faktisch omit = nicht normkonform.
Ein gelabelter Nachbarklassen-Wert ist normkonform (es wird ein Wert gezeigt) und ehrlich (die
Abweichung ist ausgewiesen).

**Ehrlicher Vorbehalt fürs Label:** Die Werte sind über die Größenklassen **nicht monoton** (Beispiel
Fernwärme: 250–500 = 112, über-500 = 87). 250–500 ist also ein vernünftiger, aber **nicht garantiert
konservativer** Näherungswert. Deshalb das sichtbare Label statt stiller Einsetzung — der Mieter (und
ihr) sollt sehen, dass hier eine Nachbarklasse benutzt wurde. Betrifft ohnehin nur Wärmepumpe/Pellets
in Gebäuden über 500 m² — seltener Eckfall, aber sauber zu behandeln.

---

## 4. co2online-Lizenz — erledigt, bitte durchbauen

Die Zusage reicht mir. Wir bauen D2 in Produktion. Sobald wir ein fertiges Produkt haben, schicken
wir **Frau Weikamp (Leitung Geschäftsfeldentwicklung und Kooperationen, co2online)** einen echten
Beispiel-Output der §6a-UVI und lassen es gegenzeichnen — das ist der Nachweis, den wir archivieren.
In dieselbe Mail kommen die zwei fehlenden über-500-Werte (siehe §3). **Kein Blocker mehr, bitte D2 fertig durchziehen.** Die
Pflicht-Quellenangabe „Quelle: co2online gGmbH (Heizspiegel)" bleibt überall Pflicht, wo ein
D2-Wert erscheint, ebenso das Label „normierter, gebäudebezogener Richtwert" (nie
Angemessenheitsurteil).

**Plan B nur als spätere Härtung, nicht jetzt umsetzen:** Wenn wir die Abhängigkeit von einer
einzelnen Fremdquelle in einem Pflichtdokument später ganz loswerden wollen, ist der Kandidat die
amtliche Bekanntmachung „Regeln für Energieverbrauchswerte im Wohngebäudebestand" (29.03.2021, BAnz
AT 16.04.2021 B1) — dieselbe, die wir schon für K12 nutzen. Ob deren Vergleichswerte nach
Größenklasse granular genug sind, ist offen und muss geprüft werden. Das ist ein *nice-to-have für
später*, kein aktueller Arbeitsschritt.

---

## 5. Zwei Register mit identischem Dateinamen

Zugestimmt, kein Streitpunkt. Ich hänge künftigen Exporten ein **Datum** an Ordner- und Dateiname
(`…_2026-08-14`). Rückwirkend kein Handlungsbedarf — nehmt bei euch die aktuelle Fassung (7 Flags
`geprüft`) als maßgeblich.

---

## Zur `geprüft`-Semantik (euer Punkt aus „Was bei uns läuft")

Bestätigt, und bitte genau so bei euch vermerken: **`geprüft` heißt bei mir immer „Normtext an der
Primärquelle gegengelesen" — nicht „anwaltlich bestätigt".** Mehr kann es zu diesem Zeitpunkt auch
nicht heißen. Der Plan ist, mit dem **kompletten Rechtsstand-Register** zu einem Anwalt zu gehen; der
prüft dann die juristische Einordnung im Ganzen. Zwei Punkte sind ausdrücklich **noch nicht** final
und sollen so markiert bleiben:

- die §6a-Abs.-3-S.-4-Bekanntmachung ist nominell unter **GEG §82** verkündet; ob sie juristisch *die*
  §6a-Bekanntmachung ist, klärt der Anwalt. Fundstelle BAnz AT 16.04.2021 B1 ist eingetragen.
- die Rechtsnatur der Emissionsfaktoren bleibt **`Konvention`** (Nutzung als Fallback = Designwahl).

Damit könnt ihr `geprüft` sauber als „Normtext gelesen" führen und die anwaltliche Bestätigung später
als zweite Stufe nachziehen.

---

## 6. Selbstprüfung / Pentest — damit ihr es nachrechnen könnt

Ich habe die Ergebnisse dieses Dokuments so gegengeprüft; bitte verifiziert selbst nach:

1. **Eigentümer-Residuum, Kontrollsumme.** F01/F06: `10.550,69 umgelegt + 175,31 Eigentümer =
   10.726,00`. Geht auf 0 auf. ✓
2. **Residuum schlägt Einzelrechnung.** F21: separat 17.536 vs. Residuum 17.531 (5 ct
   Rundungsdifferenz als Block c). F22: 1858 vs. 1859. In beiden Fällen „residual wins" — bestätigt,
   dass der Betrag Rest ist, keine Quote. ✓
3. **Eigentümerzeile bei 0.** F06 zeigt Eigentümerspalte = 0,00 für Wasser/Heizkosten → Zeile
   existiert auch ohne Leerstand. ✓
4. **WW-Abzug, Größenordnung je Klasse (Verbrenner):**
   Erdgas 80–150: 121 − 24 = 97 · 250–500: 114 − 24 = 90 · Heizöl 80–150: 165 − 24 = 141 ·
   Fernwärme 250–500: 112 − 24 = 88 · Pellets 80–150: 148 − 24 = 124. Alle plausibel
   (Raumwärme ~70–85 % des Gesamtwerts). ✓
5. **WW-Abzug, Wärmepumpe:** flacher 24er-Abzug ergibt 36 − 24 = 12 → unplausibel → Ausnahme
   nötig → 8er-Abzug ergibt 28 → plausibel. Grenzfall gefunden und behandelt. ✓ (mit co2online
   zu bestätigen)
6. **Negativ-Guard** `(mittel − ww) ≤ 0`: kann nur bei Wärmepumpe mit falschem 24er-Abzug auftreten;
   mit 8er-Abzug bleibt der kleinste Wert (WP 250–500: 30 − 8 = 22) positiv. Guard trotzdem drin. ✓
7. **Monatszerlegung:** WW wird vor `dd_share` abgezogen → WW nicht saisonalisiert → korrekter als (a). ✓
8. **Quelle 24 kWh/m²:** Herleitung gegengerechnet — co2online €2,65/m² ÷ 11 ct/kWh = 24,1 kWh/m² →
   der €- und der kWh-Wert sind konsistent. ✓ (Jahrgangs-Aktualität bleibt Verifikations-TODO)

Die einzigen zwei Stellen, die ich als **nicht endgültig bewiesen** kennzeichne: der
Wärmepumpen-WW-Wert (Konvention, JAZ-Annahme) und die Jahrgangs-Aktualität der 24 kWh/m². Beides ist
klar gelabelt und blockiert den Bau nicht.

---

## Kurz-Checkliste für euch

1. Eigentümerparteien zu **einem** Liegenschafts-Residuum je Kostenart kollabieren; Zeile immer
   drucken, keine Quote, Herkunft je Einheit für die Leerstandsaufstellung intern mitführen.
2. D2 auf **(b)** umstellen: `mittel − ww_kwh_m2[energietraeger]`; Werte-Tabelle (24 / WP 8) in
   `rules-store` K13; Golden Tests + Negativ-Guard; co2online-Quellenangabe + Richtwert-Label.
3. über-500 Wärmepumpe/Pellets: die zwei Werte sind öffentlich nicht verfügbar (offizielle
   Heizspiegel-2025-Tabelle gegengeprüft) → Fallback 250–500 mit Label, bis co2online sie liefert.
   Nicht selbst extrapolieren.
4. co2online: kein Blocker, durchbauen.
5. `geprüft` bei euch als „Normtext gelesen" führen; zwei Einträge (GEG §82, Emissionsfaktoren)
   als noch-nicht-anwaltlich markieren.
