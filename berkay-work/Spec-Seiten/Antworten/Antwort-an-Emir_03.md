# Antwort an Emir — Runde 3

Berkay · 15.08.2026 · Antwort auf `FRAGENanBerkay03.md`

Danke für § 1.4-Umsetzung und die exakte Reproduktion der Kontrollsummen (1858, 17.531). Genau so.

---

## Zum Prozess — bitte zuerst lesen

Wir bauen ein MVP und müssen zügig durch. Eine eigene .md pro Detail, die meine nächste Zeile blockiert, ist zu langsam. Ab jetzt:

- Ist ein Punkt durch eine meiner bereits geschriebenen Seiten oder To-dos **eindeutig** auflösbar (wie 2 und 3): zieh es nach und bau weiter, frag nicht. Notier die Auflösung sichtbar, ich widerspreche, falls nötig.
- Findest du zwei meiner Konventionen im Widerspruch, die **rechnerisch dieselbe Zahl** liefern: nimm die klarere, labele sie, weiter.
- Offene Punkte **gebündelt** schicken, nicht einzeln blockierend. Warte nicht auf mich, wenn du unter Vorbehalt bauen und später umflaggen kannst.

Eine Ausnahme, und die meine ich ernst: **Punkt 6 war richtig, so zu eskalieren.** Ein Konflikt zwischen meiner Hauskonvention und Gesetzestext, der über 0 % vs. 10 % Vermieteranteil entscheidet, ist kein Kleinkram — das ist genau die Sorte Fehler, die vor Produktion gefunden werden muss. Solche Punkte flaggst du weiter hart. Die „frag-nicht"-Regel gilt für triviale Bestätigungen, nicht für Norm-gegen-Konvention.

---

## 1. K9-Registereintrag — Rechtsnatur nachziehen

Ja, zieh nach. Aufteilung stimmt:

- **Rundungsrichtung** (`round_half_up` je Zeile): bleibt `Konvention` / `verify-before-production`.
- **Ziel des Rests** (die eine Liegenschafts-Eigentümerzeile): **feste Modellregel**, keine Konvention.

Umsetzung: `berkay-work/` bleibt unverändert — richtig, dass ihr das nicht anfasst. Setz die Unterscheidung in deiner Transkription (`docs/03` § 9.2) fest um; ich ziehe den Registereintrag beim nächsten Export als **zwei Zeilen** nach (getrennte Flag-Spalte je Teil). Bis dahin gilt deine § 9.2-Fassung als maßgeblich, nicht der alte K9-Einzeleintrag.

## 2. Seite 01, `08-F21` Block (b)

**1.008,00 €.** Zieh es nach. Zusammensetzung wie von dir genannt (Verwaltung 420 + Hauswart 300 + Rauchwarnmelder 168 + Ziergarten 120 aus `09-F19`). `0,00 [Seite 02 pending]` ist erledigt — kein Vermerk mehr nötig, der Wert steht.

## 3. D2-Spec „Wärme+WW"

Korrektur gilt. Bau D2 nach **(b)**: `mittel − ww_kwh_m2`. Meine alte D2-Formulierung „compare against the unit's Wärme+WW" ist damit **überholt** — hier gewinnt ausnahmsweise die Antwort über die Seite, ich ziehe die Seite selbst beim nächsten Export nach. Vermerk den Vorrang, wie ihr es tut. Wärmepumpe 8 statt 24, Negativ-Guard, `über-500`-Rückfall auf 250–500 als gelabelt: alles bestätigt.

## 4. Emissionsfaktor Erdgas

Nimm die **präzisen Werte**: Hu **0,2016**, Ho **0,1820**. Register auf diese Werte aktualisieren (Register bleibt eure einzige Quelle — Mechanik unverändert, nur der Wert wird geschärft). Grund: auf 3 Nachkommastellen vorzurunden verschiebt genau am Stufenrand, und die Rundung gehört erst in S. 3, nicht in den Faktor.

Flag: bleibt **`verify-before-production`** (README-Fassung gewinnt). Ich behaupte hier keine rechtliche Endgültigkeit — der Faktor ist erst final, wenn GEG § 82 / Rechtsnatur der Emissionsfaktoren bestätigt sind.

## 5. CO₂-**Kosten**-Fallback (H2 vs. `docs/03` § 9.5)

Eure Entscheidung ist richtig: **nicht bauen, Engine verweigert.** `co2Cent` aus einem Preis zu schätzen, wenn die Rechnung den Betrag nicht ausweist, ist rechtlich zu heikel und ein Randfall — im MVP verweigern wir lieber, als zu raten. Lass die Lücke in `docs/03` § 9.5 als bewusst-offen stehen. Der Massen-Fallback (K4/E1) mit hartem Ho/Hu-Mismatch-Refusal bleibt wie gebaut.

## 6. `R4` (Seite 01b) vs. § 5 Abs. 1 S. 3 CO2KostAufG

**S. 3 gewinnt. R4 wird ersetzt.** Ihr lest es richtig: eine Hauskonvention verdrängt keine Norm. Der nach S. 1/S. 2 ermittelte spezifische Wert ist nach S. 3 auf die erste Nachkommastelle zu runden, und **der gerundete Wert ist der einzustufende**. R4 („step lookup uses the unrounded value") gilt für Seite 01b nicht mehr.

Konsequenz an `01b-F05` — committe die neuen Werte, meine alte Fixture ist damit überholt:

| | alt (R4/E3) | neu (S. 3) |
| --- | --- | --- |
| `spezifisch` | 11,999484… | **12,0** |
| Stufe | 1 → 0 % | **2 → 10 %** |
| `abzug` | 0 | **1.280** |
| `umlagefaehig` | 350.600 | **349.320** |

Ausgaberegel zieht mit: **drucke den gerundeten Wert `12,0`**, nicht das abgeschnittene `11,99`. Meine 0-%-Begründung („Mieter kann den Anteil sonst nicht nachvollziehen") entfällt bei 10 % — und nach S. 3 ist der ausgewiesene Wert ohnehin 12,0.

**Reihenfolge (Zusatzfrage):** erst annualisieren (H2), **dann** runden (S. 3), dann einstufen. Der „spezifische Kohlendioxidausstoß" in kg/m²/a ist bereits die annualisierte Intensität — genau die rundet S. 3. S. 4 kürzt danach die Anlage-Tabelle, ungekürzt annualisiert. Also: Annualisierung → Rundung 1 Nachkommastelle → Stufe. `01b-F06` (28,7347… → 28,7) bleibt in derselben Stufe, konsistent.

Intern weiter Gramm-Integer für Emissionen — nur der einzustufende spezifische Wert wird nach S. 3 gerundet.

---

## Zusammengefasst zum Bauen

1. K9 als zwei Zeilen, Ziel = feste Modellregel — setz § 9.2 fest um.
2. `08-F21` (b) = 1.008,00.
3. D2 nach (b), alte Wärme+WW-Formel überholt.
4. Erdgas 0,2016 / 0,1820, Flag `verify-before-production`.
5. Kosten-Fallback nicht bauen, Verweigerung bleibt.
6. S. 3 vor R4, `01b-F05` neu (Stufe 2 / 10 % / 349.320), Ausgabe `12,0`, Reihenfolge annualisieren→runden→einstufen.

Tempo halten. Für triviale Bestätigungen entscheide selbst und flagge. Für echte Norm-Konflikte wie 6: weiter melden.
