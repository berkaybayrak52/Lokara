# Antwort auf dein 01b-Feedback — Übergabe & Änderungen

Berkay · Stand 13.08.2026 · als Antwort auf `FEEDBACK-to-Berkay-01b.md`

Danke fürs gründliche Feedback. Ich habe alles gegengeprüft — die Zahlen an den **Primärquellen**
(EBeV 2030, EStG, BGB, § 6a HeizkostenV im Volltext, DWD-Datensatz, Heizspiegel). Unten steht pro
Punkt, was gilt, **was sich seit meinem letzten Export geändert hat**, und was **du** noch tun/ein­
bauen musst. Wo etwas nicht 100 % geklärt ist, sage ich das ausdrücklich — nichts ist beschönigt.

---

## 0. Das Wichtigste zuerst

**Der `verify-before-production`/`geprüft`-Widerspruch (dein Punkt 4b) ist kein Datenfehler — mein
Export war veraltet.** Ich hatte die Flags am 26.–28.07. in Notion auf `geprüft` gesetzt, aber der
`.md`-Export, den du transkribiert hast, war **älter als diese Änderung**. In der Live-Notion stehen
die betroffenen Einträge längst auf `geprüft`. Du bekommst mit diesem Paket einen **frischen Export**
— damit erledigt sich 4b von selbst.

Vier echte Deltas gegenüber deinem Stand:
1. **F19** korrigiert (deine Rechnung war richtig).
2. **DWD-Importer: zwei Bugs**, die deinen ersten Lauf gecrasht hätten — korrigiert.
3. **UVI/Block D2**: neuer Normwert-Fallback für den Durchschnittsnutzer (war eine echte Lücke).
4. Flags: alle 8 sind primärquellenverifiziert und in Notion `geprüft`.

---

## 1. Übernommen (dein §1) — unverändert
Ho/Hu, K3, R1/R5/K9, H2: nichts geändert, alles wie besprochen. Kein Handlungsbedarf.

## 2. F19 — du hast recht, korrigiert
Nachgerechnet auf die gekauften 7.700 l:
`co2Cent = 20.482/1000 × 5.500 = 112.651 ct`; `abzug = round_half_up(112.651 × 0,80) = 90.121 ct`.
Der Spec-Wert 90.204 folgt aus keinem Eingangswert (impliziert co2Cent 112.755) → Zahlendreher.
**In Notion (Seite 01b) korrigiert: `abzug` 90.204 → 90.121 ct, Differenz 492,40 € → 491,57 €.**
Deine 90.121 war also korrekt. Wenn du die zwei Zahlen bei dir schon gefixt hast: passt, wir sind
deckungsgleich.

## 3. F16/F26 — bestätigt, euer Lesefehler
Meine Zahlen (4.227 als Verteilungsrest nach K9; F16 reproduziert exakt) stimmen. Der Eigentümer-
Eimer ist Verteilungsrest, kein gerundeter Anteil. Bei euch zu korrigieren, kein Spec-Fehler.

## 4a. Emissionsfaktor — Register gilt
Der Wert **0,201 (Hu) / 0,181 (Ho)** im Register ist korrekt und belegt. Die 0,2016/0,1820 aus
meiner Nachricht waren nur gröber gerundet — **nimm das Register**, nicht die Nachricht.

## 4b. Flags — alle 8 primärquellenverifiziert
Ich habe jeden der acht „geprüft"-Einträge am Normtext gegengelesen:

| Eintrag | Wert | Primärquelle |
|---|---|---|
| Erdgas | 0,201 | EBeV 2030 Anl. 2 Teil 4 Nr. 6 (0,0558 t/GJ × 0,0036) |
| Heizöl EL | 0,266 | Nr. 3b (0,074) |
| Flüssiggas | 0,236 | Nr. 5b (0,0655) |
| AfA Wohngeb. n. 2022 | 3 % | § 7 Abs. 4 S. 1 Nr. 2 a EStG |
| AfA 1925–2022 | 2 % | Nr. 2 b |
| AfA vor 1925 | 2,5 % | Nr. 2 c |
| Anschaffungsnahe HK | 15 % netto/3 J. | § 6 Abs. 1 Nr. 1a EStG |
| Mietpreisbremse | +10 %, bis 31.12.2029 | § 556d (in Kraft 23.07.2025) |

Der Erdgas-Umrechnungsfaktor 3,2508 GJ/MWh = 3,6 × 0,903 steht wörtlich in der EBeV — die Hu/Ho-
Fußnote ist damit belegt. Rechtsnatur bleibt bei den Emissionsfaktoren `Konvention` (Nutzung als
Fallback ist Designwahl), bei AfA/15 %/§ 556d `Gesetz`. **Alle stehen in Notion auf `geprüft`** →
im frischen Export korrekt enthalten. Bitte deinen `verify-before-production`-Stand entsprechend
nachziehen.

## 5. DWD-Import-Spec (dein §8.3) — existiert + zwei Bugs behoben ⚠️ wichtig für dich
Die `DWD-Klimafaktoren-Import-Spec.md` lag nur in einem anderen Ordner (`Lokara/Klimafaktoren/`),
deshalb fehlte sie in deinem Export — liegt jetzt bei. Ich habe die CSV an der echten Datei
`KF_20250101_20251231.csv` (8.234 Zeilen) verifiziert. Dabei **zwei Fehler im Referenz-Importer**
gefunden, die deinen ersten Lauf abgebrochen hätten:

1. **Spaltennamen.** Die CSV-Kopfzeile ist `DatAnf;DatEnd;PLZ;KF` — **nicht** die XML-Feldnamen
   (`KLFK_POLZ`, `KLIMAFAKTOR`, `VON_DATUM`, `BIS_DATUM`). Der alte Importer las die XML-Namen →
   `KeyError`. Korrigiert auf:
   ```python
   plz = rec["PLZ"].zfill(5)
   kf  = float(rec["KF"].replace(",", "."))
   ... rec["DATANF"] ... rec["DATEND"]   # nach .upper()
   ```
   (Wer den XML-Pfad nimmt, benutzt weiter die XML-Namen.)
2. **Plausibilitätsband zu eng.** Der reale KF-Bereich ist **0,49–1,33**. Die alte Untergrenze
   `0.50` hätte den echten Wert 0,49 abgewiesen und den **ganzen Import abgebrochen**. Geändert auf
   `0.40 <= kf <= 1.80`.

Bestätigt gut: Trennzeichen `;`, Encoding ASCII (latin-1 sicher), Punkt-Dezimal in der `.csv`
(Komma nur in `_k.csv`), PLZ ohne führende Null, **alle 9 Fixtures exakt** (01067→1,14 usw.).
`LETZTER-STAND.md` habe ich richtiggestellt (die am 26.07. „vermisste" Datei lag seit 15.07. im
Verzeichnis).

## 6. § 6a Abs. 3 S. 4 Bekanntmachung (dein §8.2) — existiert
Die gemeinsame BMWi/BMI-Bekanntmachung existiert: **„Regeln für Energieverbrauchswerte im
Wohngebäudebestand", vom 29.03.2021, BAnz AT 16.04.2021 B1.** Ihre Witterungsbereinigungs-Methode
(Nummer 3.2) ist **`EVhb = EVh · fKlima`**, fKlima = arithmetisches Mittel der **DWD-Klimafaktoren**
(Referenzort Potsdam, `dwd.de/klimafaktoren`); Warmwasser wird nicht bereinigt. **Das ist exakt euer
K12.** Damit liegt K12 innerhalb der Vermutungswirkung — es wird stärker, nicht überworfen.

**Eine Feinheit, damit kein Fehler entsteht:** die Bekanntmachung rechnet für *Energieausweise* mit
einem maßgeblichen Zeitraum ≥ 36 Monate und dem Mittel aus ≥ 3 Klimafaktoren. Für den **§ 6a-
Vorjahresvergleich** (UVI/Abrechnung) gilt das **nicht** — dort vergleicht man zwei einzelne
Abrechnungsjahre, jedes mit seinem eigenen 12-Monats-KF. Euer „gleitende 12-Monats-Zeiträume"-
Ansatz ist dafür richtig; die 36-Monats-Mittelung **nicht** in den Jahresvergleich übernehmen.

Offen (Anwaltspunkt, nicht blockierend): die Bekanntmachung ist nominell unter GEG § 82 verkündet;
ob sie juristisch *die* § 6a-Abs.-3-S.-4-Bekanntmachung ist, klärt ein Fachanwalt. Fürs Register:
Fundstelle **BAnz AT 16.04.2021** eintragen.

## 7. CO₂-Preis ab 2026 (dein §8.1) — enger als gedacht
Kein genereller Blocker. Der CO₂-Kostenanteil kommt im **Regelfall direkt von der Lieferanten­
rechnung** (§ 3 CO2KostAufG-Pflichtausweis) → OCR liest den **€-Betrag**, kein Preis-Parameter, keine
2026-Preisentscheidung nötig. Der Preis wird **nur im Fallback K4** gebraucht (Lieferant hat den
Ausweis verletzt → `co2Cent = Tonnen × Preis`). Genau das ist der F19-Fall (Fixtures backen 55 €/t =
5.500 ct/t ein). Für 2026 dort: **Nutzerabfrage, keine harte Blockade**. Wichtig für die Engine:
`co2Cent` aus dem ausgewiesenen €-Betrag **übernehmen**, nicht aus kg × Preis nachrechnen, wenn der
Betrag auf der Rechnung steht.

## 8. K13 / Durchschnittsnutzer + UVI (dein §8.4) — echte Lücke geschlossen (Block D2)
Deine Lesart stimmt und ist am Normtext bestätigt:
- **§ 6a Abs. 2 Nr. 3 (UVI, monatlich):** Durchschnittsnutzer-Vergleich **ohne Ausweichklausel**,
  ohne „soweit erhoben", ohne Online-Verweis.
- **§ 6a Abs. 3 Nr. 4 (Jahresabrechnung):** derselbe Vergleich, aber bei **elektronischer**
  Abrechnung darf er online liegen + Verweis in der Abrechnung.

Der Fehler, den wir beide übersehen hatten: Block D der UVI-Spec zeigte bei zu wenigen
vergleichbaren Einheiten „nicht aussagekräftig / omit" — das ist bei Abs. 2 Nr. 3 **nicht
normkonform** (keine Ausweichklausel). Gelöst über den **zweiten erlaubten Weg** des Gesetzes:
„**normierter** *oder* durch Vergleichstests ermittelter Durchschnittsnutzer".

**Neu in `Emir_Spec_UVI.md`: Block D2 — Normwert-Fallback.**
- `n_comparable ≥ T` → Block D (Objekt-Querschnitt, wie bisher).
- `n_comparable < T` → **Block D2**: normierter Durchschnittsnutzer aus dem **Heizspiegel** (co2online).
- Rechnung: `norm_annual = heizspiegel[Jahr][Energieträger][Größenklasse].mittel × Wohnfläche`;
  `norm_month = norm_annual × Gradtagsanteil(Monat)` (K3); dann Delta/%.
- Werte-Tabelle liegt bei: `Klimafaktoren/Heizspiegel_2025_Vergleichswerte.csv` (Größenklassen
  80–150 / 150–250 / 250–500 / über 500 m², Spalte `mittel`, enthält Raumwärme + Warmwasser).
- **Pflicht-Quellenangabe** „Quelle: co2online gGmbH (Heizspiegel)", wo der Wert erscheint.

⚠️ **Zu respektieren:** co2online kennzeichnet den Heizspiegel als **Gebäude**-Referenz, *nicht*
geeignet zur Bewertung einer einzelnen Wohnung oder der Angemessenheit (SGB). Der D2-Wert ist daher
als „normierter, gebäudebezogener Richtwert" zu labeln — nie als Angemessenheitsurteil. Die Lizenz
(Nutzung mit Quellenangabe) hat co2online uns per Mail zugesagt; die genaue § 6a-UVI-Nutzung bestätigt
Berkay noch mit dem Kontakt.

---

## 9. Was du (Emir) konkret tun musst

1. **Frischen Export übernehmen** (01b + Rechtsstand-Register) → Flags = `geprüft`, F19 = 90.121.
   Deinen `verify-before-production`-Stand für die 8 Einträge nachziehen.
2. **DWD-Importer patchen**: CSV-Spaltennamen (`PLZ`/`KF`/`DATANF`/`DATEND`) + Plausibilitätsband
   `0.40–1.80`. Siehe korrigierte `DWD-Klimafaktoren-Import-Spec.md`, Abschnitt 4.
3. **UVI**: Block D2 implementieren (normierter Fallback), Heizspiegel-CSV in den `rules-store` (K13)
   importieren, Quellenangabe + „gebäudebezogener Richtwert"-Label rendern.
4. **CO₂-Preis**: sicherstellen, dass `co2Cent` bei ausgewiesenem €-Betrag aus der Rechnung
   übernommen wird; 2026-Preis nur im Fallback K4 als Nutzerabfrage.
5. **K12**: 12-Monats-KF je Abrechnungsperiode verwenden — **nicht** das 36-Monats-Mittel der
   Bekanntmachung (das ist Energieausweis-Logik).

## 10. Offen bei Berkay (nicht bei dir, nicht blockierend)
- co2online: § 6a-UVI-Nutzung + die zwei im Flyer fehlenden „über 500 m²"-Werte (Wärmepumpe,
  Holzpellets) bestätigen lassen; Mail als Lizenznachweis archivieren.
- § 6a-Bekanntmachung juristisch final einordnen; Fundstelle BAnz 16.04.2021 ins Register.
- Kosmetik: kaputte HTML-Tabellen in „Non-Goals V1" und „Offene Fragen an Emir" vor dem Pitch fixen.

## 11. Dateien in diesem Paket
- `01b · Heizkosten- & CO₂-Verteilung …md` (frisch, F19 korrigiert)
- `Rechtsstand-Register/` (frisch, Flags `geprüft`)
- `DWD-Klimafaktoren-Import-Spec.md` (2 Importer-Fixes + Verifikations-Notiz)
- `Heizspiegel_2025_Vergleichswerte.csv` (Normwerte für Block D2)
- `LETZTER-STAND.md` (richtiggestellt)
- `Emir_Spec_UVI.md` (**neu: Block D2**)
