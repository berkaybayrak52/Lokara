# Offene Fragen an Berkay — Runde 2

Emir · Stand 13.08.2026 · nach deiner `Antwort-an-Emir_01b-Uebergabe.md`

Danke für das Paket — F19, die DWD-Importer-Bugs, die Bekanntmachung zu K12 und Block D2 sind
alle übernommen. Vier Punkte sind offen. **Punkt 1 blockiert unseren nächsten Arbeitsschritt**,
die anderen drei blockieren erst die UVI-Umsetzung.

---

## 1. Der Eigentümer-Topf, wenn es keinen gibt ⚠️ blockierend

*Diese Frage stand in `FEEDBACK-to-Berkay-01b.md` § 9, den du noch nicht gesehen hattest — dein
Export ging drei Stunden vor dem Schreiben raus. Deshalb hier noch einmal vollständig.*

**Der Unterschied.** Dein Modell hat **einen** Eigentümer-Topf pro Liegenschaft. Unsere Engine
leitet die Parteien aus Belegungszeiträumen ab, also entsteht eine **Vermieterpartei je Einheit**
— und nur dann, wenn diese Einheit im Abrechnungszeitraum leer stand oder eigengenutzt war.

**Fall A — mehrere Vermieterparteien** (mehr als eine Einheit leer). Wir geben den
Verteilungsrest an die **erste** Vermieterpartei in deterministischer Reihenfolge, in **allen
vier Blöcken an dieselbe**. Damit erklärt eine Eigentümerzeile jeden ±ct der Abrechnung — der
eigentliche Sinn von K9. *Erste*, nicht letzte, damit das Anhängen einer Einheit den Rest nicht
verschiebt.

**Fall B — gar keine Vermieterpartei.** Voll vermietet, nichts eigengenutzt. Dann existiert kein
Eigentümer-Topf, an den R5 den Rest geben könnte. Wir geben ihn **nicht** an einen Mieter, nur
damit der Block aufgeht — genau die stille Verschiebung zwischen Mietern, die K9 verhindern
soll. Solche Blöcke rechnen bei uns vorerst weiter mit Largest-Remainder.

**Warum das kein Randfall ist:** Fall B ist der **Normalfall**. Ein voll vermietetes Haus ohne
Leerstand ist die Mehrheit unserer Zielobjekte. Deine Rundungsregel greift also gerade dort
nicht, wo die meisten Abrechnungen entstehen.

**Unsere Lesart — bitte bestätigen oder korrigieren.** Seite 01 D12 beschreibt die
Eigentümerzeile als feste Zeile der Darstellung. Wir lesen das so, dass sie **immer** existiert,
auch bei 0,00 € und ohne Leerstand, und dann Träger des Verteilungsrests ist. Wenn das stimmt,
verschwindet Fall B.

**Drei Fragen:**

1. **Existiert die Eigentümerzeile immer?** Auch bei 0,00 €, auch ohne Leerstand und ohne
   Eigennutzung — als reiner Träger des Verteilungsrests?
2. **Wenn ja: was steht als Bemessung darin?** 0 m²·Tage / 0 HKV-Einheiten, oder bleibt die
   Bemessungsspalte leer und nur der Betrag erscheint? Das entscheidet, ob eine gedruckte Quote
   auf der Seite plausibel bleibt.
3. **Wenn nein** — wenn es ohne Leerstand wirklich keinen Eigentümer-Topf gibt: wohin mit dem
   Rest? Unsere Annahme ist „dann Largest-Remainder für diesen Block", weil das die Abweichung
   jeder Partei von ihrer eigenen Quote minimiert. In deinem Sinne, oder anders?

Bis zu deiner Antwort bleibt die Konvention als **unsere** gekennzeichnet (`docs/03` § 9.2), nie
als Norm.

---

## 2. Block D2: der Heizspiegel-Normwert enthält Warmwasser, unser Vergleichswert nicht

Der CSV-Kopf sagt es ausdrücklich: *„Werte … enthalten Raumwaerme + Warmwasser."*

Bei uns ist das anders herum: § 9 HeizkostenV zwingt zur Trennung von Heizung und Warmwasser,
sobald **eine** Anlage beides versorgt. Unsere Engine erzeugt deshalb einen **reinen
Heizungs-Verbrauch** in kWh. Vergleichen wir den gegen einen Normwert, der Warmwasser enthält,
sieht **jeder** Nutzer systematisch besser aus als der Durchschnitt.

Das ist ein Fehler zugunsten des Mieters — also einer, den niemand reklamiert — auf einem
Dokument, das § 6a Abs. 2 Nr. 3 zwingend vorschreibt.

**Frage:** Wie soll D2 vergleichen?

- **(a)** Gesamt gegen Gesamt — wir addieren Heizung + Warmwasser wieder zusammen, nur für den
  Vergleich. Einfach, aber die UVI zeigt dann eine andere Größe als die Abrechnung.
- **(b)** Warmwasseranteil aus dem Normwert herausrechnen. Dann brauchen wir von dir den Ansatz:
  fester kWh/m²-Abzug, prozentual, oder je Energieträger? Und die Quelle dafür.
- **(c)** Etwas anderes.

Bitte entscheide (a), (b) oder (c) — bei (b) mit Wert und Fundstelle.

---

## 3. Block D2: die Lücke „über 500 m²"

In `Heizspiegel_2025_Vergleichswerte.csv`, letzte Zeile:
`# ueber-500 Waermepumpe und Holzpellets: im Flyer nicht abgedruckt -> aus der Voll-Tabelle`

D2 existiert, weil Block D nicht antworten kann. Ein Fallback mit eigener Lücke braucht deshalb
ein definiertes Verhalten für diese Lücke.

1. **Wann bekommst du die beiden Werte** (Wärmepumpe, Holzpellets, über 500 m²)?
2. **Was soll D2 bis dahin tun** — Vergleich weglassen (bei Abs. 2 Nr. 3 nach deiner eigenen
   Analyse nicht normkonform), auf die nächstkleinere Größenklasse 250–500 ausweichen, oder die
   Abrechnung mit einem Hinweis versehen? Wir wollen das nicht selbst erfinden.

---

## 4. co2online-Lizenz: Stand und Fristigkeit

Du schreibst, die allgemeine Nutzung mit Quellenangabe sei per Mail zugesagt, die konkrete
§ 6a-UVI-Nutzung bestätigst du noch.

Wir bauen D2 nicht in Produktion, solange dieser Punkt offen ist — der Heizspiegel wäre dann die
einzige Fremdquelle in einem gesetzlich vorgeschriebenen Dokument.

1. **Rechnest du mit einer schriftlichen Bestätigung, und bis wann?**
2. **Gibt es einen Plan B**, falls co2online die UVI-Nutzung nicht bestätigt — eine andere Quelle
   für den „normierten Durchschnittsnutzer", oder Rückfall auf „durch Vergleichstests ermittelt"
   (also Block D mit niedrigerem Schwellenwert T)?

---

## 5. Kleinigkeit: zwei Register mit identischem Dateinamen

Alter und neuer Export heißen beide
`Rechtsstand-Register 388f942f178942e9954f8e68238f91cd.csv` — gleicher Notion-Hash, anderer
Inhalt (7 Flags jetzt `geprüft`). Der Hash-Suffix suggeriert Identität, garantiert sie hier aber
nicht.

**Bitte hänge künftigen Exporten ein Datum an den Ordner- oder Dateinamen.** Bei uns entscheidet
sonst der Zufall, welches Register importiert wird.

Kein Handlungsbedarf rückwirkend — wir markieren die aktuelle Fassung auf unserer Seite.

---

## Was bei uns bis zu deiner Antwort läuft

- Frischen Export übernehmen, 7 Flags auf `geprüft` nachziehen — **mit Vermerk, dass du sie am
  13.08.2026 an den Primärquellen gegengelesen hast.** Wir wollen später unterscheiden können,
  ob `geprüft` „Normtext gelesen" oder „anwaltlich bestätigt" heißt.
- F16/F26: unser Lesefehler, wird bei uns korrigiert.
- DWD-Importer-Spec mit deinen beiden Fixes übernehmen (Importer existiert noch nicht).
- K12: 12-Monats-Klimafaktor je Abrechnungsperiode, **kein** 36-Monats-Mittel — notiert.
- K12-Registereintrag bekommt den Zusatz, dass die Bekanntmachung nominell unter GEG § 82
  verkündet ist und die endgültige Einordnung noch aussteht. Fundstelle BAnz AT 16.04.2021 B1
  ist eingetragen.
