# 06 · Vertragsklauseln — Risiko-Memo

Blockiert: M8
Emir-Prio: 6
Fixtures: CLAUSES-F01 … CLAUSES-F19
Nr: 06
Optional: No
Phase: 5
Rechtsstand-Einträge: Kappungsgrenze Standard (§ 558) (../Rechtsstand-Register/Kappungsgrenze%20Standard%20(%C2%A7%20558)%203ab5fd42073181718297c4eb2704c46d.md), Kappungsgrenze angespannter Markt (§ 558) (../Rechtsstand-Register/Kappungsgrenze%20angespannter%20Markt%20(%C2%A7%20558)%203ab5fd420731813baffecf4ec5315c0a.md), Modernisierung Umlagesatz (§ 559) (../Rechtsstand-Register/Modernisierung%20Umlagesatz%20(%C2%A7%20559)%203ab5fd420731819a86e6deb3d5b36058.md), Modernisierung Kappung (§ 559) (../Rechtsstand-Register/Modernisierung%20Kappung%20(%C2%A7%20559)%203ab5fd42073181eb942ad3b686985cd4.md), Mietpreisbremse (§ 556d) (../Rechtsstand-Register/Mietpreisbremse%20(%C2%A7%20556d)%203ab5fd420731811fa1c0e56454065f08.md), Kaution (§ 551) (../Rechtsstand-Register/Kaution%20(%C2%A7%20551)%203ab5fd42073181e8b745de2b099a4459.md), Kleinreparaturen Einzelgrenze (../Rechtsstand-Register/Kleinreparaturen%20Einzelgrenze%203ab5fd42073181ceaca7d74fe9d478fb.md), Kleinreparaturen Jahresgrenze (../Rechtsstand-Register/Kleinreparaturen%20Jahresgrenze%203ab5fd4207318172819ffc3cff6b15c0.md), Verzugsschwelle fristlose Kündigung (../Rechtsstand-Register/Verzugsschwelle%20fristlose%20K%C3%BCndigung%203ab5fd420731814ab88adca8f911de93.md), Schonfristzahlung ordentliche Kündigung (geplant) (../Rechtsstand-Register/Schonfristzahlung%20ordentliche%20K%C3%BCndigung%20(geplant)%203ab5fd42073181859260f050e08df737.md), Schriftform Staffel-/Indexklausel (../Rechtsstand-Register/Schriftform%20Staffel-%20Indexklausel%203ab5fd420731811db820e864b417049d.md), Formzwang befristeter Vertrag über 1 Jahr (../Rechtsstand-Register/Formzwang%20befristeter%20Vertrag%20%C3%BCber%201%20Jahr%203ab5fd42073181499f7bfe5fd1bf4b52.md), Signatur-Gate V1 (../Rechtsstand-Register/Signatur-Gate%20V1%203ab5fd42073181acad3ce9984a4844f8.md), § 556d Handling (Produkt) (../Rechtsstand-Register/%C2%A7%20556d%20Handling%20(Produkt)%203ab5fd42073181de837fd0316600aa4b.md), Staffelmiete Mindestintervall (§ 557a) (../Rechtsstand-Register/Staffelmiete%20Mindestintervall%20(%C2%A7%20557a)%203ab5fd42073181d08c43d0415317ef1c.md), Indexmiete VPI-Bindung (§ 557b) (../Rechtsstand-Register/Indexmiete%20VPI-Bindung%20(%C2%A7%20557b)%203ab5fd420731816dbbb3eaeb945332c9.md), SEPA-Lastschriftmandat — Einzug/Verfall (../Rechtsstand-Register/SEPA-Lastschriftmandat%20%E2%80%94%20Einzug%20Verfall%203ac5fd420731811a9bcef0e3e3421b9b.md)
Status: Fertig
Ziel-Datei: NEU (Nummer vergibt Emir beim Transkribieren)
Zuletzt bearbeitet von: 29. Juli 2026 14:06

<aside>
📜

**Ziel-Datei:** NEU — Nummer vergibt Emir · **Modul:** M8 · **Rechtsstand-Basis:** 07/2026 · **Fixtures:** CLAUSES-F01 … CLAUSES-F19

</aside>

## 1. Zweck

Versionierter Katalog der Mietvertrags-Klauselbausteine plus die drei Aktionsvorlagen (Mieterhöhung / Kündigung / Mahnung). Je Baustein weiß das Produkt: aktuell wirksam?, welche BGH-Linie greift?, was ist in Kombination unwirksam?, und — für die numerischen Vorlagen — die exakte Arithmetik samt rechtlicher Voraussetzungen. Quelle der Wahrheit für den Vertragsgenerator (Klausel-Zusammenstellung) und die Wächter-/Reminder-Engine (löst Erhöhungs-/Kündigungs-Workflows aus).

## 2. Rechtsgrundlage

- **Schönheitsreparaturen** — § 535 BGB (Grundlast Vermieter) + Formularklausel-Rechtsprechung · 07/2026 · BGH-sensibel.
- **Kleinreparaturen / Bagatellklausel** — kein gesetzlicher Deckel; § 307 BGB Inhaltskontrolle · 07/2026 · Beträge [KONVENTION], nicht Gesetz.
- **Kaution** — § 551 BGB (max 3 Nettokaltmieten, 3 Raten) · 07/2026 · Gesetz.
- **Staffelmiete** — § 557a BGB · 07/2026 · Gesetz.
- **Indexmiete** — § 557b BGB (VPI Destatis) · 07/2026 · Gesetz · [UNSICHER: Mietrecht II / BT-Drs. 21/6807 plant Einschränkungen, noch nicht in Kraft].
- **Betriebskosten-Umlage / Vorauszahlung** — § 556, § 556 Abs. 2 BGB · 07/2026 · Gesetz.
- **Tierhaltung** — § 535 BGB + BGH (Generalverbot unwirksam) · 07/2026 · BGH-sensibel.
- **Schrift-/Textform** — § 126, § 126a (QES), § 126b BGB · 07/2026 · Gesetz.
- **Formzwang befristet über 1 Jahr** — § 550 BGB · 07/2026 · Gesetz.
- **Formzwang Staffel-/Indexklausel** — § 557a Abs. 1, § 557b Abs. 1 („schriftlich") · 07/2026 · Gesetz.
- **Mieterhöhung Vergleichsmiete** — § 558 BGB; Kappung 20 %/3 J., 15 % per LandesVO · 07/2026 · Gesetz + Verordnung; 15 %-Gebiet [KONVENTION: je Land, verify-before-production].
- **Mieterhöhung Modernisierung** — § 559 BGB; 8 % p. a.; Deckel 3 €/m² (2 €/m² wenn Ausgangsmiete unter 7 €/m²) in 6 J. · 07/2026 · Gesetz.
- **Mietpreisbremse** — § 556d BGB; +10 %, verlängert bis 31.12.2029 · 07/2026 · Gesetz.
- **Fristlose Kündigung Zahlungsverzug** — § 543 Abs. 2 Nr. 3, Schwelle § 569 Abs. 3 Nr. 1, Schonfrist § 569 Abs. 3 Nr. 2 · 07/2026 · Gesetz · [UNSICHER: Schonfrist-Ausweitung auf ordentliche Kündigung, BT-Drs. 21/6807, am 09.07.2026 nicht in Kraft].
- **Ordentliche Kündigung** — § 573 (berechtigtes Interesse), Fristen § 573c BGB · 07/2026 · Gesetz.
- **Mahnung / Verzug** — § 286 BGB · 07/2026 · Gesetz.

<aside>
⚠️

**Rundungsregel global:** jeder Rechenschritt kaufmännisch auf ganze **Cent** (half-up). Zwischenwerte werden nicht vorgerundet, außer explizit angegeben.

</aside>

## 3. Inputs

| Input | Einheit / Typ | Quelle |
| --- | --- | --- |
| clauseBlockId + version | string / semver | Rules-Table (Klauselkatalog) |
| nettokaltmiete | Cent (int) | Nutzereingabe / Vertrag |
| gesamtmiete (warm) | Cent (int) | Nutzereingabe / Vertrag |
| wohnflaeche | m² (dezimal) | Nutzereingabe |
| ortsuebliche_vergleichsmiete | Cent (int, Monatswert) | Mietspiegel / Gutachten / 3 Vergleichswohnungen |
| kappungsgrenze_prozent | 20 oder 15 (int) | Rules-Table (LandesVO-Flag) |
| vpi_alt, vpi_neu | Indexpunkte (dezimal, Basis 2020=100) | Destatis / Rules-Table |
| letzte_aenderung_datum | Datum (taggenau) | Vertragshistorie |
| modernisierungskosten_wohnung | Cent (int) | Nutzereingabe |
| staffel_schritte[] | {Datum, Betrag Cent} | Vertrag |
| kleinrep_einzelgrenze, kleinrep_jahresgrenze | Cent (int) | Rules-Table [KONVENTION] |
| rueckstand[] | {Monat, Soll Cent, Ist Cent} | Bank-Matching / Sollstellung |
| mpb_ausnahme | enum {keine, Vormiete, Neubau_ab_01.10.2014, umfassende_Modernisierung} | Nutzer-Checkbox |
| mpb_erklaerung_ts | Datum/Zeit (gespeichert) | System (Audit) |
| sepa_mandatsreferenz | string (max 35 Zeichen, SEPA-Rulebook) | Nutzereingabe (Vertrag) |
| sepa_mandatsdatum | Datum (taggenau) | Nutzereingabe (Vertrag) |
| eigennutzung | bool (Checkbox) | Nutzer-Checkbox (Wizard) |
| eigennutzung_periode | {von, bis} optional | Nutzereingabe -> Seite 03 SelfUsePeriod |

## 4. Formel

- **B1 — Staffelmiete (§ 557a):** `mieteSchritt_n = betrag_n` (absolut genannt). Vorbedingung: Intervall zum Vorschritt ≥ 12 Monate; sonst Schritt unwirksam, Miete bleibt auf Vorschritt.
- **B2 — Indexmiete (§ 557b):** `neueMiete = round(alteMiete × vpi_neu / vpi_alt)`. Vorbedingung: ≥ 12 Monate seit letzter Änderung; Index amtlich veröffentlicht.
- **B3 — § 558 Vergleichsmiete:** `ziel = min(vergleichsmiete, round(aktuelleMiete × (1 + kappung/100)))`; `erhoehung = ziel − aktuelleMiete`. B3a: kappung=20. B3b: kappung=15. Vorbedingung: unverändert ≥ 12 Monate, Wirksamkeit frühestens 15 Monate nach letzter Erhöhung; Begründungsmittel beigefügt.
- **B4 — § 559 Modernisierung:** `jahresumlage = round(kosten × 0,08)`; `monatlich = round(jahresumlage / 12)`; `deckel = (ausgangsmiete_pro_m2 unter 700 ? 200 : 300) × wohnflaeche`; `erhoehung = min(monatlich, deckel)`. B4a: 3-€-Deckel. B4b: 2-€-Deckel.
- **B5 — Kleinreparaturen:** je Reparatur `anrechenbar = (kosten ≤ einzelgrenze ? kosten : 0)` (voller Betrag entfällt bei Überschreitung, kein Spitzenausgleich); `summe = Σ anrechenbar`, gedeckelt auf `jahresgrenze`.
- **B6 — Kaution:** `max = 3 × nettokaltmiete`; `rate = round(max / 3)` (3 Raten, 1. bei Mietbeginn).
- **B7 — § 543 fristlos:** B7a (2 Termine): Verzug an 2 aufeinanderfolgenden Terminen und Rückstand über 1 Monatsmiete. B7b (längerer Zeitraum): Rückstand ≥ 2 Monatsmieten.
- **B8 — § 556d Anfangsmiete (Neuvermietung):** `hoechstmiete = round(vergleichsmiete × 1,10)`; Überschreitung erzeugt Warnung (warn-only, siehe E9), keine Blockade.

## 5. Edge Cases

- **E1** — Indexrückgang (`vpi_neu unter vpi_alt`): [UNSICHER: § 557b erlaubt Anpassung beiderseits; Vermieter senkt i. d. R. nicht, Mieter kann Senkung verlangen — Produktverhalten offen]. Nutzer-Infobox siehe Punkt 6.
- **E2** — Staffelschritt-Intervall unter 12 Monaten → Schritt unwirksam.
- **E3** — § 558: Vergleichsmiete unter der Kappungsgrenze → Vergleichsmiete bindet. **Gilt nur im Mieterhöhungs-Workflow (laufendes Mietverhältnis), nicht bei Vertragsaufstellung** — dort ist allein § 556d relevant (siehe E9, F16/F17).
- **E4** — § 559: monatliche Umlage überschreitet Deckel → auf Deckel gekappt.
- **E5** — Kleinreparatur über Einzelgrenze → 0 anrechenbar (kein Spitzenausgleich).
- **E6** — § 543: Rückstand knapp unter 2 Monatsmieten → keine fristlose Kündigung.
- **E7** — Schonfristzahlung innerhalb 2 Monaten nach Rechtshängigkeit → fristlose Kündigung wird unwirksam; ordentliche bleibt wirksam [UNSICHER: bis Mietrecht II in Kraft].
- **E8 — Signatur-Gate:** einfache Digitalsignatur nur freigeschaltet, wenn der Vertrag weder Staffel- (§ 557a) noch Indexklausel (§ 557b) enthält. Sonst blockt das Gate und verweist auf Papier oder QES (QES nicht in V1). Grund: § 557a/b verlangen für die Klausel selbst Schriftform; einfache E-Sig = Textform → Klausel unwirksam. Version-Trigger: QES-Integration in V2 öffnet das Gate.
- **E9 — § 556d warn-only:** vereinbarte Miete über Höchstmiete → keine Blockade. Hinweis + Checkbox (Nutzer wählt Ausnahme oder „keine"). Auswahl + Zeitstempel gespeichert. Nutzer kann fortfahren.
- **E10 — SEPA-Mandat (Vertrags-Wizard):** Felder `sepa_mandatsreferenz` + `sepa_mandatsdatum` optional. Validierung: Mandatsdatum nicht in der Zukunft; Referenz max 35 Zeichen, je Mandat eindeutig. V1 speichert und zeigt nur an — **kein Lastschrifteinzug** (finAPI AIS-only; PIS + Gläubiger-ID nicht in V1). Fehlt ein Feld → kein Blocker, Mandat gilt als unvollständig, ein späterer Einzug wäre gesperrt.
- **E11 — Eigennutzung-Flag (Vertrags-Wizard):** `eigennutzung = true` → kein Mietverhältnis, keine Mieteinnahme; die Miethöhe-Klauseln (Staffel/Index/§ 558/§ 559/§ 556d) entfallen. Der Flag routet steuerlich an Seite 03 (AfA-Bemessungsgrundlage m²-anteilig je `SelfUsePeriod` gekürzt) und Seite 04 (keine Anlage-V-Einnahme). Keine Steuer-Mathematik auf Seite 06. Teil-/Zeit-Eigennutzung → Fläche + Periode an Seite 03.

## 6. Beispielrechnung

**CLAUSES-F01 — Staffelmiete (B1)**

```
Schritt 1 = 80000 ct; Klausel +2500 ct je 12 M
Schritt 2 (nach 12 M) = 80000 + 2500 = 82500 ct (825,00 €)
Betrag absolut, Intervall 12 M -> wirksam
```

**CLAUSES-F02 — Indexmiete (B2)**

```
alteMiete 90000 ct; vpi_alt 118,5; vpi_neu 122,7
Faktor = 122,7 / 118,5 = 1,03544304
90000 x 1,03544304 = 93189,8734 -> round -> 93190 ct (931,90 €)
Vorbedingung 12 M erfuellt
```

**CLAUSES-F03 — § 558, 20 % (B3a)**

```
aktuell 70000; vergleichsmiete 90000; kappung 20
Kappe = round(70000 x 1,20) = 84000
ziel = min(90000, 84000) = 84000
erhoehung = 84000 - 70000 = 14000 ct (140,00 €); neue Miete 84000 ct
```

**CLAUSES-F04 — § 558, 15 % (B3b)**

```
aktuell 70000; vergleichsmiete 90000; kappung 15
Kappe = round(70000 x 1,15) = 80500
ziel = min(90000, 80500) = 80500
erhoehung = 10500 ct (105,00 €); neue Miete 80500 ct
```

**CLAUSES-F05 — § 559, 3-€-Deckel (B4a)**

```
kosten 2000000 ct; wohnflaeche 60 m2; ausgangsmiete 800 ct/m2 (>= 700 -> 3-€-Deckel)
jahresumlage = round(2000000 x 0,08) = 160000
monatlich = round(160000 / 12) = round(13333,33) = 13333
deckel = 300 x 60 = 18000
erhoehung = min(13333, 18000) = 13333 ct (133,33 €)
```

**CLAUSES-F06 — § 559, 2-€-Deckel (B4b)**

```
kosten 2000000; wohnflaeche 60 m2; ausgangsmiete 650 ct/m2 (unter 700 -> 2-€-Deckel)
monatlich = 13333 (wie F05)
deckel = 200 x 60 = 12000
erhoehung = min(13333, 12000) = 12000 ct (120,00 €) -- Deckel greift
```

**CLAUSES-F07 — Kleinreparaturen (B5)**

```
einzelgrenze 10000 ct [KONVENTION]; jahresgrenze = 6 % x Jahresnettokaltmiete [KONVENTION]
jahresgrenze = round(0,06 x 12 x 70000) = 50400
Reparaturen: 8000, 9500, 12000, 7000, 9000
Einzelfilter: 12000 > 10000 -> 0
anrechenbar: 8000 + 9500 + 7000 + 9000 = 33500
33500 <= 50400 -> Mieter 33500 ct (335,00 €), Vermieter 12000 ct
```

**CLAUSES-F08 — Kaution (B6)**

```
nettokaltmiete 70000; max = 3 x 70000 = 210000; rate = round(210000 / 3) = 70000
Ergebnis: 210000 ct (2.100,00 €) in 3 x 70000 ct (700,00 €)
Summenprobe 3 x 70000 = 210000 OK
```

**CLAUSES-F09 — § 543 fristlos, 2 Termine (B7a)**

```
gesamtmiete 85000; Monat 1 + 2 je 0 gezahlt; rueckstand = 170000
Schwelle: ueber 1 x 85000 = 85000
170000 > 85000 -> fristlose Kuendigung zulaessig
```

**CLAUSES-F10 — § 543 fristlos, laengerer Zeitraum (B7b)**

```
gesamtmiete 85000; 5 Monate je 50000 statt 85000 -> shortfall 35000/M
rueckstand = 5 x 35000 = 175000; Schwelle 2 x 85000 = 170000
175000 >= 170000 -> zulaessig
```

**CLAUSES-F11 — Indexrueckgang (E1)**

```
alteMiete 90000; vpi_alt 118,5; vpi_neu 117,0
Faktor = 117,0 / 118,5 = 0,98734177
90000 x 0,98734177 = 88860,759 -> round -> 88861 ct (888,61 €) rechnerisch
[UNSICHER: ob/dass gesenkt wird -- nur auf Verlangen des Mieters]
```

<aside>
ℹ️

**Nutzer-Infobox zu E1 (deutsch, wird angezeigt):** Ihr Preisindex ist gesunken. Bei der Indexmiete (§ 557b BGB) wirkt der Index grundsätzlich in beide Richtungen. Eine Mietsenkung erfolgt aber nur, wenn Ihr Mieter sie ausdrücklich verlangt — von sich aus müssen Sie nichts tun. Lokara nimmt hier keine automatische Anpassung vor. [UNSICHER: finales Produktverhalten offen — siehe Frage 1 an Emir]

</aside>

**CLAUSES-F12 — Staffel-Intervall unter 12 M (E2)**

```
Schritt 2 auf 82500 datiert 10 M nach Schritt 1
Intervall 10 M unter 12 M -> Schritt unwirksam
Miete bleibt 80000 ct (800,00 €)
```

**CLAUSES-F13 — § 558 Vergleichsmiete bindet (E3, Mieterhöhungs-Workflow)**

```
aktuell 70000; vergleichsmiete 75000; kappung 20
Kappe = 84000; ziel = min(75000, 84000) = 75000
erhoehung = 75000 - 70000 = 5000 ct (50,00 €)
-- Vergleichsmiete, nicht Kappungsgrenze, ist bindend
```

**CLAUSES-F14 — § 559 Deckel ueber 6 Jahre kumulativ (E4)**

```
M1: +13333 ct/M (F05). M2 zwei Jahre spaeter, gleiche Kosten: weitere 13333
kumulativ 26666 > deckel 18000 (3 €/m2 x 60)
zweite Erhoehung gekappt: 18000 - 13333 = 4667 ct (46,67 €) Restspielraum
[UNSICHER: 6-Jahres-Fenster-Startzeitpunkt taggenau je Massnahme -- Emir bestaetigen]
```

**CLAUSES-F15 — Signatur-Gate (E8)**

```
Vertrag mit Staffelklausel, Abschluss per einfacher E-Signatur (Textform)
§ 557a I verlangt Schriftform; Textform unter Schriftform -> Klausel unwirksam
wirtschaftliche Folge: Staffel entfaellt, Miete = Anfangsmiete 80000 ct statt Staffelverlauf
Gate: Digitalsignatur GESPERRT -> kein Cent-Ergebnis, Nutzer auf Papier/QES geleitet
```

**CLAUSES-F16 — § 556d warn-only ohne Ausnahme (B8, E9)**

```
vergleichsmiete 90000; hoechstmiete = round(90000 x 1,10) = 99000
vereinbart 105000 > 99000; mpb_ausnahme = keine
-> Warnung: 6000 ct (60,00 €) ueber Hoechstmiete nach § 556d; Mieter kann ueberzahlten Teil zurueckfordern
Nutzer kann fortfahren; gespeichert: Warnung angezeigt + keine Ausnahme erklaert
keine Kappung durch Lokara
```

**CLAUSES-F17 — § 556d mit erklaerter Ausnahme (B8, E9)**

```
gleiche Zahlen; Nutzer setzt mpb_ausnahme = Vormiete
-> Hinweis: Ausnahme Vormiete erklaert; Lokara prueft diese nicht
gespeichert: Vormiete + Zeitstempel als Selbstauskunft
keine Kappung -- vereinbarte 105000 bleibt stehen
```

<aside>
⚖️

**Reichweite der Checkbox (ehrlich):** die Selbstauskunft macht eine überhöhte Miete rechtlich **nicht** wirksam — sie dokumentiert nur, dass der Vermieter eine Ausnahme behauptet hat. Trifft die Ausnahme nicht zu, bleibt die Miete gekappt und rückforderbar. Lokaras Absicherung = „gewarnt + Selbstauskunft protokolliert", nicht „Miete legalisiert".

</aside>

**CLAUSES-F18 — SEPA-Mandat erfassen (E10)**

```
mandatsreferenz = "MIETE-2026-WE02-014" (19 Zeichen, <= 35) -> gueltig
mandatsdatum = 2026-07-28 (<= heute) -> gueltig
Ergebnis: Mandat gespeichert, Status "vollstaendig, kein Einzug in V1"
Edge (ungueltig): mandatsdatum = 2026-09-01 (Zukunft) -> abgelehnt, Feld rot, kein Blocker fuer Vertrag
kein Cent-Ergebnis (reine Datenerfassung; Lastschrifteinzug erst mit PIS + Glaeubiger-ID)
```

**CLAUSES-F19 — Eigennutzung-Flag Routing (E11)**

```
eigennutzung = true; wohnflaeche 60 m2; periode ganzjaehrig
-> kein Mietverhaeltnis: nettokaltmiete/gesamtmiete entfallen, Miethoehe-Klauseln inaktiv
-> Routing Seite 03: AfA-Bemessungsgrundlage um 60 m2 / Gesamtflaeche je SelfUsePeriod kuerzen
-> Routing Seite 04: keine Anlage-V-Einnahme fuer diese Einheit
Cent-Ergebnis dieser Seite: 0 (Steuerberechnung liegt auf Seite 03/04)
```

## 7. Out of Scope

Gewerberaummietverträge; WEG-/Sondereigentumsvereinbarungen; Staffel-/Index-Mischklauseln (bewusst ausgeschlossen); individuell ausgehandelte (nicht formulierte) Klauseln (keine Inhaltskontrolle nötig); anwaltliche Wirksamkeitsprüfung im Einzelfall (nur Katalog-Bausteine, kein Rechtsrat); QES-Integration für formgebundene Verträge (V1 nutzt einfache Signatur nur ohne Staffel/Index); automatische Prüfung/Berechnung der § 556d-Ausnahmen (nur Selbstauskunft + Warnung); Modernisierungs-**ankündigung** (§ 555c, Fristen) → liegt bei M9 Wächter; Mietpreisbremsen-Rüge/Auskunft des Mieters. SEPA-Lastschrift-Einzug/-Ausführung (V1 nur Speicherung der Mandatsdaten, kein Einzug — PIS + Gläubiger-ID verschoben); die steuerliche Berechnung der Eigennutzung selbst (AfA-Basis-Kürzung auf Seite 03, Anlage-V-Wirkung auf Seite 04 — hier nur der Flag).