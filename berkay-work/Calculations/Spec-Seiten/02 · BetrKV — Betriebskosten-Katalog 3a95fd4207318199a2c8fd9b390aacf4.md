# 02 · BetrKV — Betriebskosten-Katalog

Blockiert: M4 · Demo-Realismus
Emir-Prio: 2
Fixtures: 09-F01 … 09-F32
Nr: 02
Optional: No
Phase: 2
Status: Fertig
Termin: 27. Juli 2026 → 28. Juli 2026
Ziel-Datei: docs/09 + packages/rules-store
Zuletzt bearbeitet von: 28. Juli 2026 12:54

> **Ziel-Datei:** `docs/09` + `packages/rules-store`
> 

> **Phase / Termin:** Phase 2 · Mo 27.07.–Di 28.07.2026
> 

> **Fixtures:** `09-F01 … 09-F32`
> 

> **Braucht vorher:** Seite 01 (`docs/08-statement-document`) — Umlageschlüssel, Rundungsregel, Residuumsregel
> 

> **Blockiert:** M4 · Demo-Realismus · Seite 01 D12 Block (b) · Seite 04 (Anlage-V-Zeilenzuordnung)
> 

> **DoD:** Katalog vollständig mit Rechtsstand, bereit für `packages/rules-store`.
> 

> **Erfüllt (27.07.2026):** 32 Fixtures, 14 Edge Cases, 11 Konventionen. Alle Eigentümerresiduen gegen `08-F01` gegengerechnet — 10 von 10 identisch.
> 

> **Namensräume dieser Seite.** Seite 01 nummeriert ihre Konventionen nicht, Seite 01b benutzt `K1–K14`. Um beide Kollisionen zu vermeiden, präfixt diese Seite alles mit ihrer Ziel-`docs`-Nummer: Konventionen `09-K01…`, Edge Cases `09-E01…`, Rechenschritte `R1–R8`, Fixtures `09-F01…`. Kollisionsfrei per Konstruktion; Emir kann die IDs direkt als Testnamen übernehmen.
> 

> Sprache: content in English, wie auf Seite 01. Deutsche Rechtsbegriffe, Normzitate, Kostenartennamen und alle im Produkt ausgegebenen Texte bleiben unübersetzt.
> 

## 1. Zweck

This page is the single source of truth that turns an incoming invoice into three machine-readable facts — **is this cost allocable at all, under which BetrKV number, and by which Umlageschlüssel** — plus the labour share for § 35a EStG and the non-allocable remainder that Seite 01 prints in block (b) of the Leerstandsaufstellung.

## 2. Rechtsgrundlage

### 2.1 Normen

| Norm | Inhalt | Rechtsstand | Rechtsnatur | Quelle |
| --- | --- | --- | --- | --- |
| § 556 Abs. 1 BGB | Umlage von Betriebskosten setzt eine **Vereinbarung** voraus; Begriffsdefinition über die BetrKV | 07/2026 | Gesetz | [gesetze-im-internet.de](http://gesetze-im-internet.de) |
| § 556 Abs. 3 S. 1 Hs. 2 BGB | **Wirtschaftlichkeitsgebot** | 07/2026 | Gesetz | — |
| § 556a Abs. 1 S. 1 BGB | Ohne Vereinbarung: Umlage **nach Wohnfläche** | 07/2026 | Gesetz | — |
| § 556a Abs. 1 S. 2 BGB | Verbrauchs- oder verursachungsabhängig **erfasste** Kosten sind nach Verbrauch/Verursachung umzulegen | 07/2026 | Gesetz | — |
| § 560 Abs. 1 BGB | **Neu entstandene** Betriebskosten nur bei vereinbarter Mehrbelastungsklausel | 07/2026 | Gesetz | — |
| § 1 Abs. 1 S. 2 BetrKV | Eigenleistung des Vermieters ansetzbar in Höhe einer Fremdleistung, **ohne Umsatzsteuer** | Fassung 16.10.2023, Stand 07/2026 | Verordnung | [lxgesetze.de/betrkv/1](http://lxgesetze.de/betrkv/1) |
| § 1 Abs. 2 Nr. 1 BetrKV | **Verwaltungskosten** sind keine Betriebskosten | Fassung 16.10.2023, Stand 07/2026 | Verordnung | [lxgesetze.de/betrkv/1](http://lxgesetze.de/betrkv/1) |
| § 1 Abs. 2 Nr. 2 BetrKV | **Instandhaltungs- und Instandsetzungskosten** sind keine Betriebskosten | Fassung 16.10.2023, Stand 07/2026 | Verordnung | [lxgesetze.de/betrkv/1](http://lxgesetze.de/betrkv/1) |
| § 2 Nr. 1–17 BetrKV | Abschließender Katalog der Betriebskostenarten | Fassung 16.10.2023, Stand 07/2026 | Verordnung | [lxgesetze.de/betrkv/2](http://lxgesetze.de/betrkv/2) |
| § 2 Nr. 14 Hs. 2 BetrKV | **Doppelansatzverbot Hauswart**: Arbeitsleistungen nach Nr. 2–10 und 16 dürfen nicht zusätzlich angesetzt werden | 07/2026 | Verordnung | — |
| § 2 Nr. 15 lit. a/b BetrKV | Antennen-/Breitband-Nutzungsentgelte und Grundgebühren nur **bis zum 30. Juni 2024** | 07/2026 | Verordnung | — |
| § 2 Nr. 15 lit. c BetrKV | Glasfaser-Verteilanlage: Betriebsstrom   **• Bereitstellungsentgelt nach § 72 Abs. 1 TKG**, Voraussetzung freie Anbieterwahl | 07/2026 | Verordnung | — |
| § 2 S. 2 BetrKV | Für Anlagen, die **ab 01.12.2021** errichtet wurden, ist Nr. 15 lit. a und b **nicht anzuwenden** | 07/2026 | Verordnung | — |
| § 72 Abs. 2 TKG | Bereitstellungsentgelt **max. 60 €/Jahr und 540 € gesamt je Wohneinheit**, max. 5 Jahre, verlängerbar auf max. 9 Jahre; ab 300 € Gesamtkosten Begründungspflicht | Fassung 12.05.2026, Stand 07/2026 | Gesetz | [lxgesetze.de/tkg/72](http://lxgesetze.de/tkg/72) |
| § 72 Abs. 7 S. 1 TKG | Gilt nur für Glasfaserinfrastrukturen, die **spätestens am 31.12.2027** errichtet worden sind | 07/2026 | Gesetz | — |
| § 35a Abs. 2, 3 EStG | Steuerermäßigung für haushaltsnahe Dienstleistungen und Handwerkerleistungen (**Lohnanteil**) | 07/2026 | Gesetz | — |
| § 307 Abs. 2 Nr. 1 BGB | Formularklausel, die von § 556 Abs. 1 BGB abweicht, ist unwirksam | 07/2026 | Gesetz | — |
| §§ 6–9 HeizkostenV | Zwingendes **Leistungsprinzip** für verbrauchsabhängige Heiz- und Warmwasserkosten | Fassung 16.10.2023, Stand 07/2026 | Verordnung | — |

### 2.2 Rechtsprechung

| Entscheidung | Aussage | Bindung |
| --- | --- | --- |
| **BGH VIII ZR 137/15 v. 10.02.2016** | Zur Umlage genügt — auch formularmäßig — die Vereinbarung, der Mieter trage „die Betriebskosten". Keine Aufzählung der einzelnen Arten nötig. | st. Rspr. |
| **BGH VIII ZR 167/03 v. 07.04.2004** (Dachrinnenurteil) | **Sonstige Betriebskosten (Nr. 17) müssen im Mietvertrag konkret benannt sein.** Ein pauschaler Verweis auf Nr. 17 genügt nicht. | st. Rspr. |
| **BGH VIII ZR 103/06 v. 20.09.2006** | Aufzugskosten dürfen **auch auf Erdgeschossmieter** formularmäßig umgelegt werden, unabhängig vom konkreten Nutzen. | st. Rspr. |
| **BGH VIII ZR 27/07 v. 20.02.2008** | (a) **Abflussprinzip** ist zulässig. (b) Beim Pauschalabzug nicht umlagefähiger Anteile aus Hauswartkosten genügt **einfaches Bestreiten** des Mieters; dann muss der Vermieter aufschlüsseln. | st. Rspr. |
| **BGH VIII ZR 379/20 v. 11.05.2022** | **Mietkosten für Rauchwarnmelder sind keine umlagefähigen Betriebskosten** (verdeckte Anschaffungskosten). Wartungskosten bleiben umlagefähig. | st. Rspr. |
| **BGH VIII ZR 135/03 v. 26.05.2004** | Gartenpflegekosten sind umlagefähig, soweit die Fläche den Mietern **zugänglich** ist; ausschließlich dem Vermieter oder einem einzelnen Mieter vorbehaltene Flächen bleiben draußen. | st. Rspr. |

### 2.3 Konventionen — nicht Gesetz, `verify-before-production`

- **[KONVENTION] 09-K01 — Default-Umlageschlüssel je Kostenart.** Das Gesetz gibt nur zwei Schlüssel vor: Wohnfläche als Auffangregel (§ 556a Abs. 1 S. 1) und Verbrauch, **soweit erfasst** (S. 2). Personenzahl, Wohneinheiten und Direktzuordnung sind ausschließlich Vereinbarungssache. Unsere Default-Tabelle in 3.2 ist deshalb eine **Vorbelegung, keine Rechtsfolge** — immer überschreibbar.
- **[KONVENTION] 09-K02 — Schlüssel-Gedächtnis.** Kaskade: `Vertragsvereinbarung > Objekt-Override des Vorjahres > Katalog-Default`. Der Vorjahresvorrang verhindert, dass ein Katalog-Update stillschweigend die Abrechnung eines Bestandsobjekts ändert.
- **[KONVENTION] 09-K03 — Unbekannte Kostenart.** Kein Treffer in Nr. 1–16 → Route auf Nr. 17, `benennungspflichtig = true`, Default-Schlüssel Wohnfläche.
- **[KONVENTION] 09-K04 — Pauschalabzug 40 % bei Vollwartungsverträgen** ohne Leistungsverzeichnis. Die Rechtsprechung akzeptiert Bandbreiten von etwa 20–50 %; wir nehmen die mieterfreundlichere Mitte. Nie automatisch, immer Vorschlag mit Warnung (BGH VIII ZR 27/07).
- **[KONVENTION] 09-K05 — Turnuskosten.** Mehrjährig anfallende Prüfungen (Trinkwasser, Elektroprüfung, Aufzug-Hauptprüfung) werden **voll im Zahlungsjahr** angesetzt, nicht auf den Turnus verteilt.
- **[KONVENTION] 09-K06 — Zeitanteilige Kappung.** `leistungVon/leistungBis` einer Kostenposition kappt den umlagefähigen Betrag tagesgenau; die Verteilung läuft weiter über die **ungekürzten** Objekt-Nenner der Gesamtperiode.
- **[KONVENTION] 09-K07 — Periodenprinzip objektweit einheitlich.** `abfluss` als Default für alle Kostenarten außer den verbrauchsabhängigen Heiz-/Warmwasserkosten (dort zwingend `leistung`). Wechsel nur zum Beginn eines Abrechnungszeitraums, protokolliert.
- **[KONVENTION] 09-K08 — Wirtschaftlichkeits-Bandbreiten** je Kostenart in €/m²/Jahr. Reine Heuristik ohne Quelle, **nie blockierend**, nur Hinweis.
- **[KONVENTION] 09-K09 — Hauswart-Default-Split 75 / 15 / 10** (Betriebskosten / Instandhaltung / Verwaltung), wenn kein Leistungsverzeichnis vorliegt.
- **[KONVENTION] 09-K10 — Typischer Lohnanteil je Kostenart** als Vorbelegung für § 35a. Der tatsächliche Ausweis auf der Rechnung hat immer Vorrang.
- **[KONVENTION] 09-K11 — Nr.-14-Wächter kürzt die Hauswart-Position,** nicht die Fachrechnung, wenn dieselbe Arbeitsleistung doppelt erfasst ist. Die speziellere Nummer gewinnt.

## 3. Inputs

All money is **integer cents**. All dates are **day-granular** (both boundary days inclusive). All areas are **m², two decimals**. Same conventions as Seite 01 — no divergence.

### 3.1 `rules-store` — Katalogzeile (`betriebskostenart`)

| Feld | Typ / Einheit | Quelle |
| --- | --- | --- |
| `id` | slug, stabil, z. B. `grundsteuer` | rules-store |
| `bezeichnung` | text (deutsch, erscheint auf der Abrechnung) | rules-store |
| `betrkvNummer` | text, z. B. `2 Nr. 1`, `2 Nr. 4a`, `2 Nr. 17` · `null` = nicht umlagefähig | § 2 BetrKV |
| `umlagefaehig` | boolean | § 2 BetrKV / § 1 Abs. 2 BetrKV |
| `defaultSchluessel` | enum {Wohnfläche, Personenzahl, Wohneinheiten, Wasserverbrauch, Heizkosten (Messdienst), Direktzuordnung} | 09-K01 |
| `benennungspflichtig` | boolean — true bei allen Nr.-17-Arten | BGH VIII ZR 167/03 |
| `periodenprinzip` | enum {abfluss, leistung} | 09-K07 / HeizkostenV |
| `lohnanteilTypischProzent` | integer 0–100 · `null` wenn nie Lohnanteil | 09-K10 |
| `bandbreiteEurProM2Jahr` | `{min, max}` decimal · `null` | 09-K08 |
| `sonderregel` | enum {keine, aufzugEg, hauswartSplit, gartenNutzbarkeit, schornsteinNr4a, rauchmelderMiete, kabelStichtag, neuanlage2021, glasfaserCap, ungezieferVorbeugend} | diese Seite |
| `gueltigVon` / `gueltigBis` | date · `null` = offen | Rechtsstand-Register |
| `rechtsstand` | `MM/YYYY` | Rechtsstand-Register |
| `anlageVKategorie` | text — Platzhalter, füllt Seite 04 | Seite 04 |

### 3.2 Katalog — umlagefähige Kostenarten

`S` = Default-Schlüssel · `L` = typischer Lohnanteil % (§ 35a) · `P` = Periodenprinzip · `B` = benennungspflichtig

| `id` | Bezeichnung | BetrKV | S | L | P | B | Sonderregel |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `grundsteuer` | Grundsteuer | 2 Nr. 1 | Wohnfläche | — | abfluss | nein | keine |
| `wasserversorgung` | Wasserversorgung | 2 Nr. 2 | Wasserverbrauch | — | leistung | nein | keine |
| `entwaesserung` | Entwässerung | 2 Nr. 3 | Wasserverbrauch | — | leistung | nein | keine |
| `niederschlagswasser` | Niederschlagswasser | 2 Nr. 3 | Wohnfläche | — | abfluss | nein | keine |
| `trinkwasseruntersuchung` | Trinkwasseruntersuchung | 2 Nr. 2 | Wohnfläche | — | abfluss | nein | keine |
| `heizkosten` | Heizkosten | 2 Nr. 4a | Heizkosten (Messdienst) | — | leistung | nein | keine |
| `wartung_heizung` | Wartung Heizungsanlage | 2 Nr. 4a | Heizkosten (Messdienst) | 60 | leistung | nein | keine |
| `brennstoffversorgung` | Brennstoffversorgungsanlage | 2 Nr. 4b | Heizkosten (Messdienst) | — | leistung | nein | keine |
| `waermelieferung` | Wärmelieferung (Contracting) | 2 Nr. 4c | Heizkosten (Messdienst) | — | leistung | nein | keine |
| `etagenheizung_wartung` | Reinigung/Wartung Etagenheizung | 2 Nr. 4d | Direktzuordnung | 70 | abfluss | nein | keine |
| `warmwasser` | Warmwasser | 2 Nr. 5a | Heizkosten (Messdienst) | — | leistung | nein | keine |
| `verbundene_anlagen` | Verbundene Heizungs-/WW-Anlage | 2 Nr. 6 | Heizkosten (Messdienst) | — | leistung | nein | keine |
| `aufzug` | Aufzug | 2 Nr. 7 | Wohneinheiten | 40 | abfluss | nein | `aufzugEg` |
| `strassenreinigung` | Straßenreinigung | 2 Nr. 8 | Wohnfläche | — | abfluss | nein | keine |
| `winterdienst` | Winterdienst | 2 Nr. 8 | Wohnfläche | 60 | abfluss | nein | keine |
| `muellbeseitigung` | Müllbeseitigung | 2 Nr. 8 | Personenzahl | — | abfluss | nein | keine |
| `gebaeudereinigung` | Gebäudereinigung | 2 Nr. 9 | Wohnfläche | 83 | abfluss | nein | keine |
| `ungezieferbekaempfung` | Ungezieferbekämpfung | 2 Nr. 9 | Wohnfläche | 70 | abfluss | nein | `ungezieferVorbeugend` |
| `gartenpflege` | Gartenpflege | 2 Nr. 10 | Wohnfläche | 83 | abfluss | nein | `gartenNutzbarkeit` |
| `allgemeinstrom` | Allgemeinstrom / Beleuchtung | 2 Nr. 11 | Wohnfläche | — | abfluss | nein | keine |
| `schornsteinreinigung` | Schornsteinreinigung | 2 Nr. 12 | Wohneinheiten | 79 | abfluss | nein | `schornsteinNr4a` |
| `versicherung` | Sach- und Haftpflichtversicherung | 2 Nr. 13 | Wohnfläche | — | abfluss | nein | keine |
| `hauswart` | Hauswart | 2 Nr. 14 | Wohnfläche | 80 | abfluss | nein | `hauswartSplit` |
| `gemeinschaftsantenne` | Gemeinschafts-Antennenanlage | 2 Nr. 15a | Wohneinheiten | — | abfluss | nein | `kabelStichtag`, `neuanlage2021` |
| `breitband_verteilanlage` | Breitband-Verteilanlage | 2 Nr. 15b | Wohneinheiten | — | abfluss | nein | `kabelStichtag`, `neuanlage2021` |
| `glasfaser_bereitstellung` | Glasfaser-Bereitstellungsentgelt | 2 Nr. 15c | Wohneinheiten | — | abfluss | nein | `glasfaserCap` |
| `waeschepflege` | Einrichtungen für die Wäschepflege | 2 Nr. 16 | Wohneinheiten | — | abfluss | nein | keine |
| `dachrinnenreinigung` | Dachrinnenreinigung | 2 Nr. 17 | Wohnfläche | 80 | abfluss | **ja** | keine |
| `rauchwarnmelder_wartung` | Wartung Rauchwarnmelder | 2 Nr. 17 | Wohneinheiten | 63 | abfluss | **ja** | `rauchmelderMiete` |
| `lueftungsanlage_wartung` | Wartung Lüftungsanlage | 2 Nr. 17 | Wohnfläche | 70 | abfluss | **ja** | keine |
| `elektropruefung` | Prüfung der Elektroanlage (DGUV V3) | 2 Nr. 17 | Wohnfläche | 80 | abfluss | **ja** | keine |
| `sonstige` | Sonstige Betriebskosten (frei benannt) | 2 Nr. 17 | Wohnfläche | — | abfluss | **ja** | keine |

> ⚠️ **[UNSICHER: `trinkwasseruntersuchung` — Zuordnung.** Wir routen die Legionellenprüfung nach TrinkwV auf § 2 Nr. 2 („Kosten des Betriebs einer hauseigenen Wasserversorgungsanlage"). Eine BGH-Entscheidung dazu existiert nicht; ein Teil der Literatur verortet sie unter Nr. 17 — dann wäre sie **benennungspflichtig**. Fachanwalt-Frage, `docs/07`. Bis zur Klärung zeigt die UI beim Anlegen einen Hinweis, die Kostenart zusätzlich im Mietvertrag zu benennen.]
> 

> ⚠️ **[UNSICHER: `elektropruefung`.** Die Umlagefähigkeit der wiederkehrenden Prüfung ortsfester Anlagen ist instanzgerichtlich uneinheitlich (Abgrenzung Betriebskosten ↔ Instandhaltung). Wir führen sie als Nr. 17 mit Benennungspflicht und Warnhinweis. Fachanwalt-Frage.]
> 

**Aufzug-Lohnanteil 40 %** ist die Vorbelegung für den **Wartungs**anteil, nicht für den Betriebsstrom. Liegt eine Rechnung mit ausgewiesenem Lohnanteil vor, gewinnt sie (09-K10).

### 3.3 Katalog — nicht umlagefähige Positionen

Diese Zeilen existieren **im Katalog**, mit `umlagefaehig = false`. Nur so können sie erfasst, gewarnt und an Seite 01 D12 Block (b) sowie an Seite 04 (Werbungskosten) übergeben werden. Ohne sie bliebe Block (b) dauerhaft `0,00 €`.

| `id` | Bezeichnung | Grundlage | Zielverwendung |
| --- | --- | --- | --- |
| `verwaltungskosten` | Verwaltungskosten, Hausverwalter-Honorar | § 1 Abs. 2 Nr. 1 BetrKV | Werbungskosten, Anlage V |
| `instandhaltung` | Instandhaltung / Instandsetzung / Reparatur | § 1 Abs. 2 Nr. 2 BetrKV | Werbungskosten, Anlage V |
| `erneuerung` | Erneuerung / Anschaffung (inkl. **Rauchwarnmelder-Miete**) | § 1 Abs. 2 Nr. 2 BetrKV; BGH VIII ZR 379/20 | AfA bzw. Werbungskosten |
| `schoenheitsreparaturen` | Schönheitsreparaturen | § 1 Abs. 2 Nr. 2 BetrKV | Werbungskosten |
| `instandhaltungsruecklage` | Zuführung zur Instandhaltungsrücklage | keine laufenden Kosten i. S. d. § 1 Abs. 1 | erst bei Verwendung |
| `bankgebuehren` | Kontoführung, Bankgebühren, Zahlungsverkehr | § 1 Abs. 2 Nr. 1 BetrKV | Werbungskosten |
| `mietausfallwagnis` | Mietausfallwagnis | keine tatsächlich entstandenen Kosten | — |
| `rechtsverfolgung` | Rechtsverfolgung, Inkasso, Mahnkosten | § 1 Abs. 2 Nr. 1 BetrKV | Werbungskosten |
| `abrechnungserstellung` | Erstellung der Betriebskostenabrechnung | § 1 Abs. 2 Nr. 1 BetrKV | Werbungskosten |
| `kabel_altentgelt` | Kabelanschluss-Grundgebühren ab 01.07.2024 | § 2 Nr. 15 lit. a/b BetrKV | Werbungskosten |
| `antenne_neuanlage` | Antennen-/Verteilanlage, errichtet ab 01.12.2021 | § 2 S. 2 BetrKV | Werbungskosten |

> **Abgrenzung, die niemand verwechseln darf:** *nicht umlagefähig* (Block b) ≠ *Leerstandsanteil* (Block a). Der Leerstandsanteil entsteht aus einer **umlagefähigen** Kostenart, für die es keinen Mieter gibt; er fällt als Residuum an (Seite 01 D12). Nicht umlagefähige Kosten sind nie Teil eines Verteilers und haben keinen Nenner.
> 

### 3.4 Eingaben je Kostenposition

| Feld | Typ / Einheit | Quelle |
| --- | --- | --- |
| `kostenartId` | slug → 3.2 / 3.3 | Nutzereingabe, OCR-Vorschlag |
| `bruttobetragCent` | integer ≥ 0 (Gutschrift: < 0) | Rechnung |
| `nichtUmlagefaehigCent` | integer ≥ 0 — herausgerechneter Anteil aus derselben Rechnung | Nutzereingabe, Leistungsverzeichnis |
| `umlagefaehigCent` | integer — abgeleitet: `bruttobetragCent − nichtUmlagefaehigCent` | Engine |
| `lohnanteilCent` | integer ≥ 0, ≤ `umlagefaehigCent` | Rechnung, sonst 09-K10 |
| `schluesselOverride` | enum \ | `null` |
| `wohnungId` | uuid \ | `null` — nur bei Direktzuordnung |
| `leistungVon` / `leistungBis` | date \ | `null` |
| `belegNr`, `belegDatum`, `zahlungsdatum` | text / date | Rechnung |

### 3.5 Eingaben je Mietverhältnis (Vertragsebene)

| Feld | Typ | Quelle |
| --- | --- | --- |
| `umlageVereinbarung` | enum {pauschalBetriebskosten, einzelaufzaehlung, keine} | Mietvertrag |
| `benannteSonstige[]` | slug[] — welche Nr.-17-Arten der Vertrag konkret benennt | Mietvertrag |
| `mehrbelastungsklausel` | boolean | Mietvertrag (§ 560 Abs. 1 BGB) |
| `schluesselVereinbarung{kostenartId → schluessel}` | map | Mietvertrag (§ 556a Abs. 1) |
| `nutzungsart` | enum {wohnraum, gewerbe} | Mietvertrag |

## 4. Formel

Runden erst am Ende der Verteilung, **zeilenweise, `round_half_up` auf ganze Cent** — identisch zu Seite 01, Abschnitt 4. Diese Seite rundet selbst nur an einer Stelle: bei der Kappung in R2 und R3. Alle Kürzungen werden **vor** der Verteilung auf ganze Cent gerundet, damit der Verteiler mit einem Integer arbeitet.

**R1 — Kostenart auflösen.**

```jsx
katalogzeile = rulesStore.lookup(kostenartId, stichtag)
if katalogzeile == null: → 09-K03 (Route Nr. 17, benennungspflichtig, Wohnfläche)
stichtag = kostenposition.leistungBis ?? kostenposition.belegDatum
```

Der Katalog wird **tagesgenau versioniert** aufgelöst (`gueltigVon`/`gueltigBis`). Fällt ein Versionswechsel in den Abrechnungszeitraum, wird die Position in R2 gesplittet.

**R2 — Umlagefähigkeits-Gate.** Reihenfolge ist bindend; der erste Treffer entscheidet.

```jsx
1  katalogzeile.umlagefaehig == false                 → umlagefaehigCent = 0, alles nach Block (b)
2  vertrag.umlageVereinbarung == keine                → 0, Hinweis § 556 Abs. 1 BGB
3  vertrag.nutzungsart == gewerbe                     → HARD BLOCK (Non-Goal V1)
4  katalogzeile.benennungspflichtig
   && kostenartId ∉ vertrag.benannteSonstige          → 0 für DIESES Mietverhältnis (nicht für das Objekt)
5  sonderregel == neuanlage2021
   && anlage.errichtetAb >= 01.12.2021                → 0 (§ 2 S. 2 BetrKV)
6  sonderregel == kabelStichtag                       → tagesgenaue Kappung auf Zeitraum ∩ [.. , 30.06.2024]
7  sonderregel == glasfaserCap                        → Kappung nach § 72 Abs. 2 TKG (siehe R2c)
8  kostenposition.leistungVon/Bis gesetzt             → Kappung nach 09-K06
9  neu entstandene Kostenart
   && !vertrag.mehrbelastungsklausel                  → 0 (§ 560 Abs. 1 BGB)
sonst                                                 → umlagefaehigCent unverändert
```

*R2c — Glasfaser-Cap, in dieser Reihenfolge:* Errichtung ≤ 31.12.2027 · Erhebungsjahr ≤ 5 (bzw. ≤ 9 mit begründeter Verlängerung) · `≤ 6000 ct` je Wohneinheit und Jahr · kumuliert `≤ 54000 ct` je Wohneinheit. Jede verletzte Bedingung kappt auf den zulässigen Wert; der Rest geht in Block (b).

**R3 — Bereinigung gemischter Rechnungen.**

```jsx
umlagefaehigCent = bruttobetragCent − nichtUmlagefaehigCent
sonderregel == hauswartSplit && kein Leistungsverzeichnis → Vorschlag 09-K09 (75/15/10)
sonderregel == rauchmelderMiete   → Mietanteil zwingend nach (b), BGH VIII ZR 379/20
sonderregel == gartenNutzbarkeit  → Flächenanteil ohne Mieterzugang nach (b)
sonderregel == ungezieferVorbeugend → einmalige Bekämpfung eines akuten Befalls nach (b)
Vollwartungsvertrag ohne LV        → Vorschlag 09-K04 (40 %)
```

Nie automatisch. Jeder Split ist ein Vorschlag mit sichtbarer Herkunft; der Nutzer bestätigt.

**R4 — Schlüssel bestimmen (Kaskade, 09-K02).**

```jsx
if kostenposition.wohnungId != null              → Direktzuordnung          (überschreibt alles)
else if vertrag.schluesselVereinbarung[kostenart] → dieser Schlüssel        (§ 556a Abs. 1 S. 1 Hs. 1)
else if objekt.vorjahresSchluessel[kostenart]     → dieser Schlüssel        (09-K02)
else if verbrauchErfasst(kostenart, objekt)       → Verbrauchsschlüssel     (§ 556a Abs. 1 S. 2, zwingend)
else                                              → katalogzeile.defaultSchluessel (09-K01)
```

`verbrauchErfasst` ist wahr, wenn für die Kostenart **im Objekt** Zähler- oder Messdienstwerte vorliegen. Fehlen sie, schlägt der Katalog Wohnfläche vor — er wechselt nie selbst.

**R5 — Sonderregel-Hooks nach der Schlüsselwahl.**

```jsx
aufzugEg          → EG-Einheiten bleiben im Verteiler (BGH VIII ZR 103/06),
                    Ausnahme nur bei ausdrücklicher Vertragsregelung
schornsteinNr4a   → wenn dieselben Kehrgebühren bereits in der Heizkostenabrechnung
                    stehen: Warnung, Nutzer entscheidet (§ 2 Nr. 12 a. E.)
hauswartSplit     → Nr.-14-Wächter, siehe 09-K11
```

**R6 — Lohnanteil § 35a.**

```jsx
lohnanteilCent = rechnung.ausgewiesenerLohn
                 ?? round_half_up(umlagefaehigCent × lohnanteilTypischProzent / 100)
Guard: 0 ≤ lohnanteilCent ≤ umlagefaehigCent, sonst HARD BLOCK
```

Die Verteilung des Lohnanteils auf die Mieter macht **Seite 01** (`anteil35aCent`), nicht diese Seite. Wir liefern nur den objektbezogenen Betrag.

**R7 — Wirtschaftlichkeits-Wächter (§ 556 Abs. 3 S. 1 Hs. 2 BGB).**

```jsx
kennzahl = umlagefaehigCent / objekt.gesamtflaecheM2        // ct/m²/Jahr
if bandbreiteEurProM2Jahr != null && kennzahl außerhalb      → WARNUNG, nie blockierend
```

**R8 — Übergabe an Seite 01.** Pro Kostenposition genau ein Tupel:

```jsx
{ kostenart, betrkvNummer, schluessel, gesamtbetragCent = umlagefaehigCent,
  lohnanteilCent, wohnungId?, hinweis? }
```

plus je Objekt eine Summe `nichtUmlagefaehigGesamtCent` → Seite 01 D12 Block (b). Diese Seite verteilt nichts und rundet keine Mieteranteile.

## 5. Edge Cases

| ID | Fall | Verhalten | Fixture |
| --- | --- | --- | --- |
| **09-E01** | Kostenart im Katalog nicht gefunden | Route Nr. 17 (09-K03); ohne Benennung im Vertrag `0` | 09-F20 |
| **09-E02** | `bruttobetragCent == 0` | Katalogauflösung läuft, Zeile wird **nicht gedruckt**, im Protokoll geführt | 09-F21 |
| **09-E03** | Negative Position (Gutschrift, Rückerstattung) | erbt Kostenart und Schlüssel der Ursprungsposition; **eigene gedruckte Zeile, eigene Rundung** — nie vorab saldiert | 09-F22 |
| **09-E04** | `lohnanteilCent > umlagefaehigCent` | HARD BLOCK, kein Dokument | 09-F23 |
| **09-E05** | `nichtUmlagefaehigCent > bruttobetragCent` | HARD BLOCK | 09-F24 |
| **09-E06** | Verbrauchsschlüssel, aber keine Verbrauchsdaten im Objekt | Katalog **schlägt** Wohnfläche vor; ohne Bestätigung greift der Nenner-0-Guard von Seite 01 (08-F12) | 09-F25 |
| **09-E07** | Kostenart entsteht erstmals im laufenden Zeitraum | ohne Mehrbelastungsklausel `0`; mit Klausel tagesanteilige Kappung (09-K06) | 09-F26 |
| **09-E08** | Vollwartungsvertrag ohne Leistungsverzeichnis | Vorschlag 40 % Abzug (09-K04) + Warnung „einfaches Bestreiten genügt" | 09-F27 |
| **09-E09** | Turnuskosten (Trinkwasser, Elektroprüfung) | voll im Zahlungsjahr (09-K05), Hinweis auf den Turnus | 09-F28 |
| **09-E10** | Rechnung betrifft einen anderen Zeitraum als die Abrechnung | `abfluss` → im Zahlungsjahr; `leistung` → periodengerecht gesplittet | 09-F29 |
| **09-E11** | Formularvertrag legt eine nach § 1 Abs. 2 BetrKV ausgeschlossene Kostenart um | Klausel unwirksam (§ 307 Abs. 2 Nr. 1 BGB), `0`, Warnung | 09-F30 |
| **09-E12** | `wohnungId` gesetzt | Direktzuordnung überschreibt jeden Katalog-Default; Katalog liefert nur noch `umlagefaehig` und Lohnanteil | 09-F31 |
| **09-E13** | Hauswart-Leistungsverzeichnis enthält Arbeiten nach Nr. 2–10 oder 16, die separat abgerechnet sind | Warnung; Default-Vorschlag: Hauswart-Position kürzen (09-K11) | 09-F32 |
| **09-E14** | Katalogversion wechselt innerhalb des Abrechnungszeitraums | Position wird tagesgenau in zwei Teilpositionen gesplittet | 09-F11 |

## 6. BEISPIELRECHNUNG

> **Referenzobjekt — identisch zu Seite 01, bewusst kein neues.** Musterstraße 12, 50667 Köln · Zeitraum 01.01.2025–31.12.2025 (365 Tage) · WE-01 62 m² (Erdgeschoss), WE-02 74 m², WE-03 58 m² (Σ 194 m²) · 3 Einheiten, 4 Mietverhältnisse, ein Wechsel zum 01.08./01.09., ein Monat Leerstand.
> 

> Nenner: `nM2Tage = 194 × 365 = 70.810` · `nPersTage = 2.006 + 2 × 31 = 2.068` (Fiktivbelegung D0) · `nWasser = 203 m³` · `nAnzWE = 3` · `nTage = 365`.
> 

| Mietverhältnis | m² | Zeitraum | Tage | Pers. | m²-Tage | P-Tage | m³ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Muster (WE-01, EG) | 62 | ganzjährig | 365 | 3 | 22.630 | 1.095 | 95 |
| Schneider (WE-02) | 74 | 01.01.–31.07. | 212 | 2 | 15.688 | 424 | 48 |
| Weber (WE-02) | 74 | 01.09.–31.12. | 122 | 1 | 9.028 | 122 | 19 |
| Beispiel (WE-03) | 58 | ganzjährig | 365 | 1 | 21.170 | 365 | 41 |
| *Leerstand WE-02 August* | 74 | 01.08.–31.08. | 31 | 2 (fiktiv) | 2.294 | 62 | 0 |

> **Varianten-Regel:** Fixtures, die Kostenarten brauchen, die das Referenzobjekt nicht hat (Aufzug, Glasfaser, Photovoltaik), arbeiten auf einer **ausdrücklich deklarierten Variante**. Diese Varianten fließen nie in `09-F19` und damit nie in `08-F01` ein.
> 

### 09-F01 — R1/R2, Katalogtreffer ohne Sonderregel (Grundsteuer)

Rechnung „Grundsteuer 2025" 98000, `kostenartId = grundsteuer`. R1 findet `2 Nr. 1`, `umlagefaehig = true`, `defaultSchluessel = Wohnfläche`, `benennungspflichtig = false`. R2 läuft ohne Treffer durch, R3 ändert nichts, R4 nimmt den Katalog-Default, R6 setzt `lohnanteilCent = 0`.

```jsx
umlagefaehigCent = 98000 − 0 = 98000
schluessel       = Wohnfläche                            // 09-K01, kein Override
Muster    = 98000 × 22630 / 70810 = 31.319,58 → 31320    (313,20 €)
Schneider = 98000 × 15688 / 70810 = 21.711,96 → 21712    (217,12 €)
Weber     = 98000 ×  9028 / 70810 = 12.494,62 → 12495    (124,95 €)
Beispiel  = 98000 × 21170 / 70810 = 29.298,97 → 29299    (292,99 €)
Σ Mieter  = 94826 · Eigentümer (Residuum) = 98000 − 94826 = 3174   (31,74 €)
```

Summenprobe: 94826 + 3174 = 98000 ✓ — **identisch zu `08-F01`.**

### 09-F02 — R2 Schritt 1, § 1 Abs. 2 Nr. 1 BetrKV (Verwaltungskosten)

Rechnung der Hausverwaltung 42000, `kostenartId = verwaltungskosten`.

```jsx
katalogzeile.umlagefaehig = false → R2 Schritt 1 greift
umlagefaehigCent          = 0
nichtUmlagefaehigCent     = 42000                        (420,00 €)
Alle vier Mieteranteile   = 0 · kein Nenner, keine Verteilung, keine gedruckte Zeile
→ Seite 01 D12 Block (b) = 42000
```

Summenprobe: 0 + 42000 = 42000 ✓ — **Dies ist der erste Betrag, der Seite 01 Block (b) von `0,00 € [Seite 02 pending]` löst.**

### 09-F03 — R2 Schritt 1, § 1 Abs. 2 Nr. 2 BetrKV (Instandsetzung)

*Variante: Referenzobjekt + Aufzug.* Rechnung „Aufzug — Störungsbeseitigung Steuerplatine" 68000, `kostenartId = instandhaltung`.

```jsx
umlagefaehigCent      = 0
nichtUmlagefaehigCent = 68000                            (680,00 €)
→ Block (b) = 68000 · Anlage V: Erhaltungsaufwand (Seite 04)
```

Der Unterschied zu 09-F02 ist nicht die Rechenlogik, sondern die **Anlage-V-Zeile**. Deshalb sind es zwei Katalogzeilen und nicht eine.

### 09-F04 — R3, gemischte Rechnung auf einem Beleg

*Variante: Referenzobjekt + Aufzug.* Rechnung des Aufzugsdienstes 96000, Leistungsverzeichnis: Wartung 72000, Reparatur Türantrieb 24000.

```jsx
bruttobetragCent      = 96000
nichtUmlagefaehigCent = 24000                            // Reparatur, § 1 Abs. 2 Nr. 2
umlagefaehigCent      = 96000 − 24000 = 72000
schluessel            = Wohneinheiten                    // Katalog-Default
je Einheit und Jahr   = 72000 / 3 = 24000
Muster    = 24000 × 365 / 365 = 24.000,00 → 24000        (240,00 €)
Schneider = 24000 × 212 / 365 = 13.939,73 → 13940        (139,40 €)
Weber     = 24000 × 122 / 365 =  8.021,92 →  8022         (80,22 €)
Beispiel  = 24000 × 365 / 365 = 24.000,00 → 24000        (240,00 €)
Σ Mieter  = 69962 · Eigentümer = 72000 − 69962 = 2038     (20,38 €)
```

Kontrolle des Residuums: der August-Leerstand wäre `24000 × 31 / 365 = 2038,36`. Gerechnet wird **2038**, nicht 2038,36 — das Residuum gewinnt (Seite 01 D12). Summenprobe: 69962 + 2038 + 24000 = 96000 ✓

### 09-F05 — R3, Hauswart-Split nach § 2 Nr. 14

Hauswartvertrag 120000/Jahr. Leistungsverzeichnis liegt vor: 75 % Betriebskosten-Tätigkeit, 15 % Instandhaltung/Kleinreparaturen, 10 % Mieterkorrespondenz/Verwaltung.

```jsx
nichtUmlagefaehigCent = 120000 × 0,15 + 120000 × 0,10 = 18000 + 12000 = 30000
umlagefaehigCent      = 120000 − 30000 = 90000
lohnanteilCent        = 90000 × 80 / 100 = 72000         // 09-K10
schluessel            = Wohnfläche
Muster    = 90000 × 22630 / 70810 = 28.762,89 → 28763    (287,63 €)
Schneider = 90000 × 15688 / 70810 = 19.939,56 → 19940    (199,40 €)
Weber     = 90000 ×  9028 / 70810 = 11.474,65 → 11475    (114,75 €)
Beispiel  = 90000 × 21170 / 70810 = 26.907,22 → 26907    (269,07 €)
Σ Mieter  = 87085 · Eigentümer = 90000 − 87085 = 2915     (29,15 €)
```

Summenprobe: 87085 + 2915 + 30000 = 120000 ✓ — **`umlagefaehigCent = 90000` und `lohnanteilCent = 72000` sind exakt die Werte, die `08-F01` voraussetzt.** Seite 02 leitet her, was Seite 01 bisher als gegeben annahm.

### 09-F06 — R3, Rauchwarnmelder: Miete ≠ Wartung (BGH VIII ZR 379/20)

Rechnung des Dienstleisters 26400: Miete 15 Geräte × 1120 = 16800, Funktionsprüfung/Wartung 9600.

```jsx
nichtUmlagefaehigCent = 16800     // BGH VIII ZR 379/20: verdeckte Anschaffungskosten
umlagefaehigCent      =  9600
lohnanteilCent        = 9600 × 63 / 100 = 6048 → Rechnung weist 6000 aus → 6000 gewinnt
schluessel            = Wohneinheiten · je Einheit 9600 / 3 = 3200
Muster    = 3200 × 365 / 365 = 3.200,00 → 3200            (32,00 €)
Schneider = 3200 × 212 / 365 = 1.858,63 → 1859            (18,59 €)
Weber     = 3200 × 122 / 365 = 1.069,59 → 1070            (10,70 €)
Beispiel  = 3200 × 365 / 365 = 3.200,00 → 3200            (32,00 €)
Σ Mieter  = 9329 · Eigentümer = 9600 − 9329 = 271          (2,71 €)
```

Summenprobe: 9329 + 271 + 16800 = 26400 ✓ — deckungsgleich mit `08-F01`. Ohne diese Trennung hätte der Vermieter 168,00 € zu viel umgelegt.

### 09-F07 — R4, Vertragsvereinbarung schlägt Katalog-Default

Müllbeseitigung 62000. Katalog-Default `Personenzahl`; alle vier Mietverträge vereinbaren „Umlage nach Wohnfläche" (§ 556a Abs. 1 S. 1 Hs. 1). Beide Wege durchgerechnet.

```jsx
// A — Katalog-Default (Personenzahl), Stand 08-F01
Muster    = 62000 × 1095 / 2068 = 32.828,82 → 32829       (328,29 €)
Schneider = 62000 ×  424 / 2068 = 12.711,80 → 12712       (127,12 €)
Weber     = 62000 ×  122 / 2068 =  3.657,64 →  3658        (36,58 €)
Beispiel  = 62000 ×  365 / 2068 = 10.942,94 → 10943       (109,43 €)
Σ = 60142 · Eigentümer = 1858
// getrennt gerechnet wäre der Leerstandsanteil 62000 × 62 / 2068 = 1858,80 → 1859.
// Gerechnet wird 1858. Residuum gewinnt.

// B — Vertragsschlüssel (Wohnfläche)
Muster    = 62000 × 22630 / 70810 = 19.814,43 → 19814     (198,14 €)
Schneider = 62000 × 15688 / 70810 = 13.736,14 → 13736     (137,36 €)
Weber     = 62000 ×  9028 / 70810 =  7.904,76 →  7905      (79,05 €)
Beispiel  = 62000 × 21170 / 70810 = 18.536,08 → 18536     (185,36 €)
Σ = 59991 · Eigentümer = 2009

// Delta B − A
Muster −13015 · Schneider +1024 · Weber +4247 · Beispiel +7593 · Eigentümer +151
```

Summenprobe A: 60142 + 1858 = 62000 ✓ · B: 59991 + 2009 = 62000 ✓ · Δ-Probe: −13015 + 1024 + 4247 + 7593 + 151 = **0** ✓

Die Schlüsselwahl verschiebt hier 130,15 € allein bei einer Partei. Deshalb ist 09-K01 als Konvention markiert und der Vertrag hat immer Vorrang.

### 09-F08 — R4, zwingender Verbrauchsschlüssel (§ 556a Abs. 1 S. 2)

Wasserversorgung 126000. Kein Schlüssel im Vertrag vereinbart, aber Wohnungswasserzähler vorhanden → `verbrauchErfasst = true`. Der Auffangschlüssel Wohnfläche ist damit **gesperrt**, nicht bloß überschrieben.

```jsx
schluessel = Wasserverbrauch                             // § 556a Abs. 1 S. 2, zwingend
Muster    = 126000 × 95 / 203 = 58.965,52 → 58966        (589,66 €)
Schneider = 126000 × 48 / 203 = 29.793,10 → 29793        (297,93 €)
Weber     = 126000 × 19 / 203 = 11.793,10 → 11793        (117,93 €)
Beispiel  = 126000 × 41 / 203 = 25.448,28 → 25448        (254,48 €)
Σ Mieter  = 126000 · Eigentümer = 0
```

Summenprobe: 126000 + 0 = 126000 ✓ — Der Eigentümeranteil ist **0**, weil der Nenner die Summe der tatsächlich erfassten Verbräuche ist und die leerstehende Einheit nichts verbraucht hat. Genau so steht es in `08-F01`.

### 09-F09 — R2 Schritt 4, Nr. 17 ohne Benennung (BGH VIII ZR 167/03)

Dachrinnenreinigung 8400, `betrkvNummer = 2 Nr. 17`, `benennungspflichtig = true`. Die Verträge WE-01 und WE-03 benennen „Dachrinnenreinigung" ausdrücklich, der Vertrag zu WE-02 nicht. **Die Prüfung läuft je Mietverhältnis, nicht je Objekt** — der Nenner bleibt objektbezogen.

```jsx
schluessel = Wohnfläche
Muster    = 8400 × 22630 / 70810 = 2.684,54 → 2685        (26,85 €)
Schneider = benannt? nein → 0
Weber     = benannt? nein → 0
Beispiel  = 8400 × 21170 / 70810 = 2.511,34 → 2511        (25,11 €)
Σ Mieter  = 5196 · Eigentümer = 8400 − 5196 = 3204        (32,04 €)
```

Summenprobe: 5196 + 3204 = 8400 ✓ — Der Eigentümer trägt WE-02 **und** den August-Leerstand. Die fehlende Benennung wirkt wie Leerstand, nicht wie eine Kürzung des Verteilers.

### 09-F10 — R2 Schritt 6, Kabelanschluss nach dem 30.06.2024

Kabelanschluss-Grundgebühren 43200, Abrechnungszeitraum 01.01.–31.12.2025.

```jsx
Zeitraum ∩ [.. , 30.06.2024] = ∅
umlagefaehigCent      = 0
nichtUmlagefaehigCent = 43200                            (432,00 €)
Warntext: „Kosten des Kabelanschlusses sind seit dem 01.07.2024 nicht mehr umlagefähig
           (§ 2 Nr. 15 lit. a, b BetrKV)."
```

Summenprobe: 0 + 43200 = 43200 ✓

### 09-F11 — 09-E14, Katalogversionswechsel im Abrechnungszeitraum

Dieselbe Position, Abrechnungszeitraum **01.01.2024–31.12.2024** (366 Tage, Schaltjahr). Die Katalogzeile `breitband_verteilanlage` hat `gueltigBis = 2024-06-30`. R1 löst tagesgenau auf, R2 Schritt 6 kappt.

```jsx
tageUmlagefaehig = 01.01.2024 … 30.06.2024 = 31+29+31+30+31+30 = 182
umlagefaehigCent      = 43200 × 182 / 366 = 21.481,97 → 21482   (214,82 €)
nichtUmlagefaehigCent = 43200 − 21482      = 21718              (217,18 €)
schluessel = Wohneinheiten
```

Summenprobe: 21482 + 21718 = 43200 ✓

Die Kappung wird auf ganze Cent gerundet, **bevor** verteilt wird — sonst hätte der Verteiler einen nicht-ganzzahligen Zähler und Seite 01 könnte die Zeile nicht mehr aus gedruckten Werten nachrechnen.

### 09-F12 — R2c, Glasfaser-Bereitstellungsentgelt über der Kappungsgrenze

*Variante: Referenzobjekt + Glasfaser-Verteilanlage, errichtet 04/2024, Erhebungsjahr 2 von 5, freie Anbieterwahl gegeben.* Der Betreiber stellt 20700 für 3 Wohneinheiten in Rechnung = 6900 je Einheit und Jahr.

```jsx
Prüfung 1  Errichtung 04/2024 ≤ 31.12.2027                        ✓ (§ 72 Abs. 7 S. 1 TKG)
Prüfung 2  Erhebungsjahr 2 ≤ 5                                     ✓ (§ 72 Abs. 2 S. 3)
Prüfung 3  je Einheit und Jahr 6900 > 6000                         ✗ → Kappung auf 6000
Prüfung 4  kumuliert 2 × 6000 = 12000 ≤ 54000                      ✓ (§ 72 Abs. 2 S. 2)
umlagefaehigCent      = 3 × 6000 = 18000                          (180,00 €)
nichtUmlagefaehigCent = 20700 − 18000 = 2700                       (27,00 €)
schluessel = Wohneinheiten · je Einheit 18000 / 3 = 6000
Muster    = 6000 × 365 / 365 = 6.000,00 → 6000                    (60,00 €)
Schneider = 6000 × 212 / 365 = 3.484,93 → 3485                    (34,85 €)
Weber     = 6000 × 122 / 365 = 2.005,48 → 2005                    (20,05 €)
Beispiel  = 6000 × 365 / 365 = 6.000,00 → 6000                    (60,00 €)
Σ Mieter  = 17490 · Eigentümer = 18000 − 17490 = 510               (5,10 €)
```

Summenprobe: 17490 + 510 + 2700 = 20700 ✓

Die Kappung ist **je Wohneinheit**, nicht je Objekt. Ein Objekt mit einer teuren und zwei billigen Einheiten darf nicht quersubventionieren.

### 09-F13 — R2 Schritt 5, Neuanlage ab 01.12.2021 (§ 2 S. 2 BetrKV)

*Variante: Referenzobjekt + Gemeinschafts-Antennenanlage, errichtet 03/2022.* Betriebsstrom der Anlage 3600.

```jsx
sonderregel = neuanlage2021 · anlage.errichtetAb = 2022-03-01 ≥ 2021-12-01
→ § 2 S. 2 BetrKV: Nr. 15 lit. a und b nicht anzuwenden
Ausweichprüfung Nr. 15 lit. c: Glasfaser? nein → greift nicht
umlagefaehigCent      = 0
nichtUmlagefaehigCent = 3600                              (36,00 €)
```

Summenprobe: 0 + 3600 = 3600 ✓ — Das ist die **härteste Falle des Katalogs**: dieselbe Kostenart ist bei einer Altanlage umlagefähig und bei einer Neuanlage nicht. Deshalb ist `anlage.errichtetAb` ein Pflichtfeld, sobald `sonderregel = neuanlage2021` gesetzt ist.

### 09-F14 — R5, Aufzug und Erdgeschoss (BGH VIII ZR 103/06)

*Variante: Referenzobjekt + Aufzug, `umlagefaehigCent = 72000` aus 09-F04.* WE-01 liegt im Erdgeschoss und hat keinen Kellerzugang über den Aufzug.

```jsx
// A — Default: keine EG-Ausnahme (BGH VIII ZR 103/06) → identisch zu 09-F04
Muster 24000 · Schneider 13940 · Weber 8022 · Beispiel 24000 · Σ 69962 · Eigentümer 2038

// B — nur bei ausdrücklicher Vertragsregelung: WE-01 ausgenommen, nAnzWE_aufzug = 2
je Einheit = 72000 / 2 = 36000
Muster    = 0                                                    (0,00 €)
Schneider = 36000 × 212 / 365 = 20.909,59 → 20910               (209,10 €)
Weber     = 36000 × 122 / 365 = 12.032,88 → 12033               (120,33 €)
Beispiel  = 36000 × 365 / 365 = 36.000,00 → 36000               (360,00 €)
Σ = 68943 · Eigentümer = 3057

// Delta B − A
Muster −24000 · Schneider +6970 · Weber +4011 · Beispiel +12000 · Eigentümer +1019
```

Summenprobe A: 69962 + 2038 = 72000 ✓ · B: 68943 + 3057 = 72000 ✓ · Δ-Probe: −24000 + 6970 + 4011 + 12000 + 1019 = **0** ✓

Der Default ist **A**. Variante B wird nur aktiv, wenn `vertrag.schluesselVereinbarung` die Ausnahme trägt — die UI warnt dabei, dass die Ausnahme rechtlich nicht erforderlich ist.

### 09-F15 — R5, Gartenpflege und Nutzbarkeit (BGH VIII ZR 135/03)

Gartenrechnung 48000. Das Leistungsverzeichnis weist 12000 für den ausschließlich vom Eigentümer genutzten Ziergarten hinter WE-01 aus; diese Fläche ist für Mieter nicht zugänglich.

```jsx
nichtUmlagefaehigCent = 12000     // BGH VIII ZR 135/03, keine Zugänglichkeit
umlagefaehigCent      = 48000 − 12000 = 36000
lohnanteilCent        = 36000 × 83 / 100 = 29880 → Rechnung weist 30000 aus → 30000 gewinnt
schluessel            = Wohnfläche
Muster    = 36000 × 22630 / 70810 = 11.505,15 → 11505    (115,05 €)
Schneider = 36000 × 15688 / 70810 =  7.975,82 →  7976     (79,76 €)
Weber     = 36000 ×  9028 / 70810 =  4.589,86 →  4590     (45,90 €)
Beispiel  = 36000 × 21170 / 70810 = 10.762,89 → 10763    (107,63 €)
Σ Mieter  = 34834 · Eigentümer = 36000 − 34834 = 1166     (11,66 €)
```

Summenprobe: 34834 + 1166 + 12000 = 48000 ✓ — `umlagefaehigCent = 36000` und `lohnanteilCent = 30000` sind exakt die Werte aus `08-F01`.

### 09-F16 — R5, Schornsteinreinigung und § 2 Nr. 12 a. E.

Kehrgebühren 12000. Der Wächter vergleicht gegen die Positionen der Heizkostenabrechnung.

```jsx
heizkostenabrechnung.positionen ∋ "Schornsteinfeger"? → nein
→ keine Doppelerfassung, umlagefaehigCent = 12000
lohnanteilCent = 12000 × 79 / 100 = 9480 → Rechnung weist 9500 aus → 9500 gewinnt
schluessel     = Wohneinheiten · je Einheit 12000 / 3 = 4000
Muster    = 4000 × 365 / 365 = 4.000,00 → 4000           (40,00 €)
Schneider = 4000 × 212 / 365 = 2.323,29 → 2323           (23,23 €)
Weber     = 4000 × 122 / 365 = 1.336,99 → 1337           (13,37 €)
Beispiel  = 4000 × 365 / 365 = 4.000,00 → 4000           (40,00 €)
Σ Mieter  = 11660 · Eigentümer = 12000 − 11660 = 340      (3,40 €)

// Gegenfall: die Heizkostenabrechnung enthält "Schornsteinfeger 12000"
→ WARNUNG (nicht blockierend): „Diese Kehrgebühren sind möglicherweise bereits in der
   Heizkostenabrechnung enthalten (§ 2 Nr. 12 BetrKV). Doppelte Umlage prüfen."
   Default-Vorschlag: Position auf 0 setzen. Der Nutzer entscheidet.
```

Summenprobe: 11660 + 340 = 12000 ✓ — identisch zu `08-F01`.

### 09-F17 — R6, Lohnanteil § 35a je Kostenart

Gebäudereinigung 54000, Rechnung weist Lohnanteil 45000 aus. Die Verteilung des Lohnanteils macht Seite 01; hier wird die Kette geprüft.

```jsx
umlagefaehigCent = 54000 · lohnanteilCent = 45000 · Quote 45000/54000 = 5/6
Muster    = 54000 × 22630 / 70810 = 17.257,73 → 17258    (172,58 €)
Schneider = 54000 × 15688 / 70810 = 11.963,73 → 11964    (119,64 €)
Weber     = 54000 ×  9028 / 70810 =  6.884,79 →  6885     (68,85 €)
Beispiel  = 54000 × 21170 / 70810 = 16.144,33 → 16144    (161,44 €)
Σ Mieter  = 52251 · Eigentümer = 1749

// § 35a je Mieter (Seite 01, hier zur Verifikation)
Muster    = 17258 × 5 / 6 = 14.381,67 → 14382            (143,82 €)
Schneider = 11964 × 5 / 6 =  9.970,00 →  9970             (99,70 €)
Weber     =  6885 × 5 / 6 =  5.737,50 →  5738             (57,38 €)   // round_half_up
Beispiel  = 16144 × 5 / 6 = 13.453,33 → 13453            (134,53 €)
Σ § 35a   = 43543 · Rest beim Eigentümer = 45000 − 43543 = 1457
```

Summenprobe Kosten: 52251 + 1749 = 54000 ✓ · Summenprobe § 35a: 43543 + 1457 = 45000 ✓

Weber liegt exakt auf `,5` — hier wird `round_half_up` sichtbar. `round_half_even` hätte 5737 ergeben und die Summenprobe um 1 Cent verschoben.

### 09-F18 — R7, Wirtschaftlichkeits-Wächter

Sach- und Haftpflichtversicherung 145000 auf 194 m².

```jsx
kennzahl = 145000 / 194 = 747,42 ct/m²/Jahr = 7,4742 €/m²/Jahr
bandbreiteEurProM2Jahr[versicherung] = { min: 1,50, max: 4,50 }   // 09-K08, Heuristik
7,4742 > 4,50 → WARNUNG
Warntext: „Die Versicherungskosten liegen mit 7,47 €/m² deutlich über dem üblichen
           Rahmen. Nach § 556 Abs. 3 S. 1 BGB gilt das Wirtschaftlichkeitsgebot —
           prüfen Sie die Police. Die Abrechnung wird dadurch nicht gesperrt."
umlagefaehigCent bleibt 145000 · Verteilung unverändert:
Muster 46340 · Schneider 32125 · Weber 18487 · Beispiel 43351 · Σ 140303 · Eigentümer 4697
```

Summenprobe: 140303 + 4697 = 145000 ✓ — Der Wächter ist reine Anzeige. **Er darf niemals eine Zahl der Abrechnung verändern**, sonst rechnet Lokara dem Vermieter seine Kosten weg.

### 09-F19 — R8, vollständiger Katalog-Lauf des Referenzobjekts

Alle 13 Kostenarten aus `08-F01` durch R1–R8, plus die vier nicht umlagefähigen Positionen aus 09-F02, 09-F05, 09-F06 und 09-F15. Kein Aufzug, keine Glasfaser — dies ist das echte Referenzobjekt.

| Kostenart | BetrKV | Schlüssel | umlagefähig | Lohn § 35a | Σ Mieter | Eigentümer |
| --- | --- | --- | --- | --- | --- | --- |
| Grundsteuer | 2 Nr. 1 | Wohnfläche | 98000 | 0 | 94826 | **3174** |
| Wasserversorgung | 2 Nr. 2 | Wasserverbrauch | 126000 | 0 | 126000 | **0** |
| Entwässerung | 2 Nr. 3 | Wasserverbrauch | 84000 | 0 | 84000 | **0** |
| Müllbeseitigung | 2 Nr. 8 | Personenzahl | 62000 | 0 | 60142 | **1858** |
| Straßenreinigung | 2 Nr. 8 | Wohnfläche | 18000 | 0 | 17417 | **583** |
| Gebäudereinigung | 2 Nr. 9 | Wohnfläche | 54000 | 45000 | 52251 | **1749** |
| Gartenpflege | 2 Nr. 10 | Wohnfläche | 36000 | 30000 | 34834 | **1166** |
| Allgemeinstrom | 2 Nr. 11 | Wohnfläche | 24000 | 0 | 23222 | **778** |
| Schornsteinreinigung | 2 Nr. 12 | Wohneinheiten | 12000 | 9500 | 11660 | **340** |
| Versicherung | 2 Nr. 13 | Wohnfläche | 145000 | 0 | 140303 | **4697** |
| Hauswart | 2 Nr. 14 | Wohnfläche | 90000 | 72000 | 87085 | **2915** |
| Rauchwarnmelder (Wartung) | 2 Nr. 17 | Wohneinheiten | 9600 | 6000 | 9329 | **271** |
| Heizkosten | 2 Nr. 4a | Heizkosten (Messdienst) | 314000 | 0 | 314000 | **0** |
| **Σ umlagefähig** |  |  | **1.072.600** | **162.500** | **1.055.069** | **17.531** |

```jsx
Summenprobe Umlage:  1055069 + 17531 = 1072600 ✓        (10.726,00 €)
// deckungsgleich mit 08-F01: „404914 + 245571 + 116007 + 288577 = 1.055.069"

Block (b), nicht umlagefähig:
  verwaltungskosten (09-F02)                      42000   (420,00 €)
  hauswart — Instandhaltung + Verwaltung (09-F05) 30000   (300,00 €)
  erneuerung — Rauchwarnmelder-Miete (09-F06)     16800   (168,00 €)
  instandhaltung — Ziergarten (09-F15)            12000   (120,00 €)
  ─────────────────────────────────────────────────────
  nichtUmlagefaehigGesamtCent                    100800  (1.008,00 €)

Rechnungsvolumen gesamt: 1072600 + 100800 = 1173400     (11.734,00 €)
```

Summenprobe gesamt: 1.055.069 + 17.531 + 100.800 = **1.173.400** ✓

> 🔴 **Für Emir — Seite 01 muss hier nachziehen.** `08-F21` druckt heute `(b) nicht umlagefähige Kosten 0,00 [Seite 02 pending]`. Mit dieser Seite steht der Wert: **1.008,00 €**. Die Leerstandsaufstellung des Referenzobjekts lautet danach `(a) 175,31 € · (b) 1.008,00 € · (c) Rundungsdifferenz`. Die Anlage-V-Zeilenzuordnung für (b) liefert Seite 04.
> 

### 09-F20 — 09-E01, Kostenart nicht im Katalog

Rechnung „Concierge-Service Empfangsdienst" 24000. Kein Treffer in Nr. 1–16.

```jsx
09-K03: betrkvNummer = 2 Nr. 17 · benennungspflichtig = true · defaultSchluessel = Wohnfläche
R2 Schritt 4: "Concierge-Service" ∈ vertrag.benannteSonstige? → nein bei allen vier
umlagefaehigCent      = 0
nichtUmlagefaehigCent = 24000                            (240,00 €)

// Gegenfall: alle vier Verträge benennen "Concierge-Service"
Muster    = 24000 × 22630 / 70810 = 7.670,10 → 7670       (76,70 €)
Schneider = 24000 × 15688 / 70810 = 5.317,22 → 5317       (53,17 €)
Weber     = 24000 ×  9028 / 70810 = 3.059,91 → 3060       (30,59 €)
Beispiel  = 24000 × 21170 / 70810 = 7.175,26 → 7175       (71,75 €)
Σ = 23222 · Eigentümer = 778
```

Summenprobe A: 0 + 24000 = 24000 ✓ · B: 23222 + 778 = 24000 ✓

Der Katalog erfindet **nie** eine Umlagefähigkeit. Eine unbekannte Kostenart ist im Zweifel nicht umlagefähig, und die UI sagt dem Vermieter genau, welche Vertragsformulierung fehlt.

### 09-F21 — 09-E02, Betrag 0

Die Gemeinde hat die Straßenreinigungsgebühr für 2025 erlassen. Position bleibt im Katalogprotokoll, damit der Vorjahresvergleich nicht abreißt.

```jsx
// A — bruttobetragCent = 0
umlagefaehigCent = 0 · alle Anteile 0 · Eigentümer 0
gedruckte Zeile: keine        // Seite 01 D2 druckt keine Nullzeilen
Katalogprotokoll: "strassenreinigung · 2 Nr. 8 · Wohnfläche · 0 · nicht gedruckt"

// B — Referenzfall bruttobetragCent = 18000
Muster    = 18000 × 22630 / 70810 = 5.752,58 → 5753       (57,53 €)
Schneider = 18000 × 15688 / 70810 = 3.987,91 → 3988       (39,88 €)
Weber     = 18000 ×  9028 / 70810 = 2.294,93 → 2295       (22,95 €)
Beispiel  = 18000 × 21170 / 70810 = 5.381,44 → 5381       (53,81 €)
Σ = 17417 · Eigentümer = 583
```

Summenprobe A: 0 + 0 = 0 ✓ · B: 17417 + 583 = 18000 ✓ — Kein Division-durch-Null-Risiko: der Nenner bleibt 70810, nur der Zähler ist 0.

### 09-F22 — 09-E03, Gutschrift

Die Kommune erstattet 7400 wegen reduzierten Restmüllvolumens. Die Gutschrift **erbt** `kostenartId = muellbeseitigung` und damit den Schlüssel Personenzahl; sie bekommt eine eigene gedruckte Zeile und eine eigene Rundung.

```jsx
Muster    = −7400 × 1095 / 2068 = −3.918,28 → −3918       (−39,18 €)
Schneider = −7400 ×  424 / 2068 = −1.517,21 → −1517       (−15,17 €)
Weber     = −7400 ×  122 / 2068 =   −436,56 →  −437        (−4,37 €)
Beispiel  = −7400 ×  365 / 2068 = −1.306,09 → −1306       (−13,06 €)
Σ Mieter  = −7178 · Eigentümer = −7400 − (−7178) = −222    (−2,22 €)

// Netto-Wirkung Müllbeseitigung
Mieter     = 60142 − 7178 = 52964                         (529,64 €)
Eigentümer =  1858 −  222 =  1636                          (16,36 €)
```

Summenprobe: 52964 + 1636 = 54600 = 62000 − 7400 ✓

Zeilenweise Rundung gilt auch für die Gutschriftzeile. Bei **identischem Schlüssel** führen Vorab-Saldierung und zeilenweise Rechnung hier zufällig zum selben Ergebnis (nachgerechnet für alle vier Parteien). Abweichen können sie, sobald Kostenposition und Gutschrift unterschiedliche Schlüssel haben. Regel bleibt: **nie vorab saldieren** (Seite 01, `08-F11`).

### 09-F23 — 09-E04, Lohnanteil größer als der umlagefähige Betrag

Gartenpflege, `umlagefaehigCent = 36000`, Nutzer trägt `lohnanteilCent = 40000` ein (er hat den Bruttobetrag der Rechnung abgeschrieben).

```jsx
Guard R6: 0 ≤ 40000 ≤ 36000 ? → verletzt
HARD BLOCK · kein Dokument · kein Teilergebnis
Meldung: „Der Lohnanteil (400,00 €) ist größer als der umlagefähige Betrag (360,00 €).
          Der Lohnanteil nach § 35a EStG ist ein Teil dieses Betrags, nicht zusätzlich."
```

Blockiert, weil ein zu hoher Lohnanteil dem Mieter eine Steuerermäßigung bescheinigt, die er nicht hat — das ist eine Falschbescheinigung, kein Rundungsfehler.

### 09-F24 — 09-E05, nicht umlagefähiger Anteil größer als die Rechnung

Hauswart, `bruttobetragCent = 120000`, Nutzer trägt `nichtUmlagefaehigCent = 130000` ein.

```jsx
Guard R3: umlagefaehigCent = 120000 − 130000 = −10000 < 0 → verletzt
HARD BLOCK
Meldung: „Der herausgerechnete Anteil (1.300,00 €) übersteigt den Rechnungsbetrag
          (1.200,00 €)."
```

Ein negativer `umlagefaehigCent` würde bei Seite 01 als Gutschrift verteilt und dem Mieter Geld zurückgeben, das nie geflossen ist.

### 09-F25 — 09-E06, Verbrauchsschlüssel ohne Verbrauchsdaten

Entwässerung 84000, `defaultSchluessel = Wasserverbrauch`.

```jsx
// A — Verbräuche erfasst (Referenzfall)
Muster    = 84000 × 95 / 203 = 39.310,34 → 39310         (393,10 €)
Schneider = 84000 × 48 / 203 = 19.862,07 → 19862         (198,62 €)
Weber     = 84000 × 19 / 203 =  7.862,07 →  7862          (78,62 €)
Beispiel  = 84000 × 41 / 203 = 16.965,52 → 16966         (169,66 €)
Σ = 84000 · Eigentümer = 0

// B — nWasser = 0, keine Zähler erfasst · Katalog schlägt Wohnfläche vor, Nutzer bestätigt
Muster    = 84000 × 22630 / 70810 = 26.845,36 → 26845    (268,45 €)
Schneider = 84000 × 15688 / 70810 = 18.610,25 → 18610    (186,10 €)
Weber     = 84000 ×  9028 / 70810 = 10.709,67 → 10710    (107,10 €)
Beispiel  = 84000 × 21170 / 70810 = 25.113,40 → 25113    (251,13 €)
Σ = 81278 · Eigentümer = 2722

// C — nWasser = 0, Nutzer bestätigt nicht
Nenner-0-Guard von Seite 01 greift: alle Anteile 0, Eigentümer 84000, Hinweiszeile
```

Summenprobe A: 84000 + 0 = 84000 ✓ · B: 81278 + 2722 = 84000 ✓ · C: 0 + 84000 = 84000 ✓

Der Katalog **schlägt vor und wechselt nie selbst**. Ein stiller Wechsel von Verbrauch auf Fläche verschiebt hier bis zu 124,65 € je Partei, ohne dass es jemand sieht.

### 09-F26 — 09-E07, neu entstandene Betriebskostenart (§ 560 Abs. 1 BGB)

*Variante: Referenzobjekt + Photovoltaik-Anlage, in Betrieb ab 01.07.2025.* Wartungsvertrag 9600 für ein volles Jahr, `kostenartId = sonstige`, im Vertrag benannt.

```jsx
// A — keine Mehrbelastungsklausel im Mietvertrag
umlagefaehigCent      = 0                                (§ 560 Abs. 1 BGB)
nichtUmlagefaehigCent = 9600                             (96,00 €)

// B — Mehrbelastungsklausel vorhanden, leistungVon = 01.07.2025
tageLeistung = 01.07. … 31.12.2025 = 31+31+30+31+30+31 = 184
umlagefaehigCent = 9600 × 184 / 365 = 4.839,45 → 4839    (48,39 €)   // 09-K06
nichtUmlagefaehigCent = 9600 − 4839 = 4761               (47,61 €)
schluessel = Wohnfläche · Nenner bleibt der volle nM2Tage = 70810
Muster    = 4839 × 22630 / 70810 = 1.546,48 → 1546       (15,46 €)
Schneider = 4839 × 15688 / 70810 = 1.072,08 → 1072       (10,72 €)
Weber     = 4839 ×  9028 / 70810 =   616,95 →  617        (6,17 €)
Beispiel  = 4839 × 21170 / 70810 = 1.446,71 → 1447       (14,47 €)
Σ = 4682 · Eigentümer = 4839 − 4682 = 157                 (1,57 €)
```

Summenprobe A: 0 + 9600 = 9600 ✓ · B: 4682 + 157 + 4761 = 9600 ✓

> **Die Kappung ändert den Zähler, nie den Nenner.** Würde man den Nenner auf die 184 Tage kürzen, bekäme Schneider (der zum 31.07. auszieht) plötzlich einen Anteil an einer Anlage, die zu seiner Zeit noch keine Kosten verursacht hat. Bewusste Vereinfachung, als 09-K06 markiert.
> 

### 09-F27 — 09-E08, Vollwartungsvertrag ohne Leistungsverzeichnis

*Variante: Referenzobjekt + Aufzug.* Vollwartungsvertrag 108000/Jahr, enthält Reparatur- und Ersatzteilrisiko, kein Leistungsverzeichnis.

```jsx
09-K04: Vorschlag Pauschalabzug 40 %
nichtUmlagefaehigCent = 108000 × 0,40 = 43200            (432,00 €)
umlagefaehigCent      = 108000 − 43200 = 64800           (648,00 €)
schluessel = Wohneinheiten · je Einheit 64800 / 3 = 21600
Muster    = 21600 × 365 / 365 = 21.600,00 → 21600        (216,00 €)
Schneider = 21600 × 212 / 365 = 12.545,75 → 12546        (125,46 €)
Weber     = 21600 × 122 / 365 =  7.220,27 →  7220         (72,20 €)
Beispiel  = 21600 × 365 / 365 = 21.600,00 → 21600        (216,00 €)
Σ Mieter  = 62966 · Eigentümer = 64800 − 62966 = 1834     (18,34 €)
Warntext: „Der Abzug von 40 % ist eine Schätzung. Widerspricht der Mieter, genügt
           einfaches Bestreiten — dann müssen Sie den Vertrag aufschlüsseln
           (BGH VIII ZR 27/07)."
```

Summenprobe: 62966 + 1834 + 43200 = 108000 ✓ — Der Abzug ist **Konvention, nicht Recht** (09-K04) und wird auf der Abrechnung als Schätzung gekennzeichnet.

### 09-F28 — 09-E09, Turnuskosten (Trinkwasseruntersuchung)

Legionellenprüfung nach TrinkwV, Turnus 3 Jahre, Rechnung 18000, fällig und bezahlt 2025.

```jsx
09-K05: voll im Zahlungsjahr, keine Verteilung auf 3 Jahre
umlagefaehigCent = 18000
betrkvNummer     = 2 Nr. 2                               // [UNSICHER], siehe 3.2
schluessel       = Wohnfläche                            // nicht verbrauchsabhängig
Muster    = 18000 × 22630 / 70810 = 5.752,58 → 5753       (57,53 €)
Schneider = 18000 × 15688 / 70810 = 3.987,91 → 3988       (39,88 €)
Weber     = 18000 ×  9028 / 70810 = 2.294,93 → 2295       (22,95 €)
Beispiel  = 18000 × 21170 / 70810 = 5.381,44 → 5381       (53,81 €)
Σ Mieter  = 17417 · Eigentümer = 583                       (5,83 €)
Hinweis:  „Diese Kosten fallen alle 3 Jahre an und werden im Jahr der Zahlung
           vollständig umgelegt."
```

Summenprobe: 17417 + 583 = 18000 ✓ — Die Kostenart ist **§ 2 Nr. 2 zugeordnet, aber nach Wohnfläche verteilt.** Das zeigt: `betrkvNummer` und `defaultSchluessel` sind zwei unabhängige Felder. Die Nummer bestimmt die Umlagefähigkeit, nicht den Maßstab.

### 09-F29 — 09-E10, Abflussprinzip (BGH VIII ZR 27/07)

Im Abrechnungsjahr 2025 gehen zwei Grundsteuerbescheide ein und werden bezahlt: der Jahresbescheid 2024 über 98000 und eine Nachveranlagung 2023 über 12000.

```jsx
periodenprinzip[grundsteuer] = abfluss                   // 09-K07
→ beide Zahlungen gehören in die Periode 2025
umlagefaehigCent = 98000 + 12000 = 110000               (1.100,00 €)
Muster    = 110000 × 22630 / 70810 = 35.154,64 → 35155   (351,55 €)
Schneider = 110000 × 15688 / 70810 = 24.370,57 → 24371   (243,71 €)
Weber     = 110000 ×  9028 / 70810 = 14.024,57 → 14025   (140,25 €)
Beispiel  = 110000 × 21170 / 70810 = 32.886,60 → 32887   (328,87 €)
Σ Mieter  = 106438 · Eigentümer = 110000 − 106438 = 3562  (35,62 €)
```

Summenprobe: 106438 + 3562 = 110000 ✓

**Gegenprobe für den zwingenden Ausnahmefall:** Wären es Heizkosten statt Grundsteuer, gilt `periodenprinzip = leistung` (§§ 6 ff. HeizkostenV) und die Position müsste periodengerecht abgegrenzt werden — das Abflussprinzip ist dort **nicht wählbar**. Der Katalog erzwingt das über das Feld, nicht über eine Nutzerentscheidung.

### 09-F30 — 09-E11, unwirksame Umlageklausel (§ 307 BGB)

Formularmietvertrag WE-01: „Der Mieter trägt zusätzlich die Verwaltungskosten in Höhe von 25,00 € monatlich." = 30000/Jahr.

```jsx
katalogzeile[verwaltungskosten].umlagefaehig = false     // § 1 Abs. 2 Nr. 1 BetrKV
vertrag.nutzungsart = wohnraum · Klausel formularmäßig
→ § 307 Abs. 2 Nr. 1 BGB i. V. m. § 556 Abs. 1 S. 2 BGB: unwirksam
umlagefaehigCent      = 0
nichtUmlagefaehigCent = 30000                            (300,00 €)
Warntext: „Verwaltungskosten sind bei Wohnraum keine Betriebskosten (§ 1 Abs. 2 Nr. 1
           BetrKV). Eine formularvertragliche Umlage ist unwirksam. Der Betrag wird
           als Werbungskosten erfasst, nicht umgelegt."
```

Summenprobe: 0 + 30000 = 30000 ✓

> ⚠️ **[UNSICHER: Individualvereinbarung.** Ob eine ausgehandelte Einzelvereinbarung über Verwaltungskosten bei Wohnraum wirksam ist, ist umstritten. Wir behandeln sie **wie den Formularfall** (nicht umlagefähig) und weisen darauf hin — die konservative Seite. Fachanwalt-Frage, `docs/07`.] Bei Gewerberaum ist die Umlage zulässig; Gewerbe ist Non-Goal V1.
> 

### 09-F31 — 09-E12, Direktzuordnung überschreibt den Katalog

Sonderreinigung des Treppenhauses in WE-02 nach einem Wasserschaden, 6000, `wohnungId = WE-02`, `kostenartId = gebaeudereinigung`.

```jsx
R4 Schritt 1: wohnungId != null → schluessel = Direktzuordnung
              (Katalog-Default Wohnfläche wird nicht ausgewertet)
Der Katalog liefert nur noch: umlagefaehig = true · betrkvNummer = 2 Nr. 9 · Lohn 83 %
lohnanteilCent = 6000 × 83 / 100 = 4980                   (49,80 €)
Muster    = andere Wohnung → 0
Schneider = 6000 × 212 / 365 = 3.484,93 → 3485            (34,85 €)
Weber     = 6000 × 122 / 365 = 2.005,48 → 2005            (20,05 €)
Beispiel  = andere Wohnung → 0
Σ Mieter  = 5490 · Eigentümer = 6000 − 5490 = 510          (5,10 €)
```

Summenprobe: 5490 + 510 = 6000 ✓ — Die 510 sind der August-Leerstand derselben Wohnung. Die Direktzuordnung ändert den Schlüssel, **nicht** die Zeitgewichtung und **nicht** die Residuumsregel.

### 09-F32 — 09-E13, Doppelansatzverbot § 2 Nr. 14 Hs. 2

Das Hauswart-Leistungsverzeichnis (09-F05) enthält 9000 für die Treppenhausreinigung. Gleichzeitig liegt die Rechnung der Reinigungsfirma über 54000 für denselben Zeitraum und denselben Leistungsinhalt vor.

```jsx
Wächter: Nr.-14-Teilbetrag mit Zielnummer 9 gefunden (9000)
       ∧ separate Position mit betrkvNummer 2 Nr. 9 vorhanden (54000)
       ∧ Leistungszeiträume überschneiden sich
→ WARNUNG. Default-Vorschlag nach 09-K11: die speziellere Nummer gewinnt,
  die Hauswart-Position wird gekürzt.
hauswart.umlagefaehigCent = 90000 − 9000 = 81000         (810,00 €)
gebaeudereinigung bleibt bei 54000
Muster    = 81000 × 22630 / 70810 = 25.886,60 → 25887    (258,87 €)
Schneider = 81000 × 15688 / 70810 = 17.945,60 → 17946    (179,46 €)
Weber     = 81000 ×  9028 / 70810 = 10.327,19 → 10327    (103,27 €)
Beispiel  = 81000 × 21170 / 70810 = 24.216,49 → 24216    (242,16 €)
Σ Mieter  = 78376 · Eigentümer = 81000 − 78376 = 2624     (26,24 €)

// Delta gegen 09-F05
Muster −2876 · Schneider −1994 · Weber −1148 · Beispiel −2691 · Eigentümer −291
```

Summenprobe: 78376 + 2624 = 81000 ✓ · Δ-Probe: −2876 − 1994 − 1148 − 2691 − 291 = **−9000** ✓

Die 9000 wandern nicht nach Block (b) — sie sind umlagefähig, nur unter der falschen Nummer erfasst. Sie werden **gestrichen**, nicht umgebucht, weil die Reinigungsfirma dieselbe Leistung bereits abgerechnet hat. Der Wächter blockiert nicht; er zwingt zu einer sichtbaren Entscheidung.

## 7. Out of Scope

### Owned here — logic that originates on this page and exists nowhere else

Die Katalogzeile selbst (3.2, 3.3) · das Umlagefähigkeits-Gate `R2` samt Reihenfolge · die Kappungen für Kabelstichtag, Neuanlage 2021 und Glasfaser-Cap · die Bereinigung gemischter Rechnungen `R3` · die Schlüssel-Kaskade `R4` · die Sonderregeln `R5` · die objektbezogene Ermittlung von `lohnanteilCent` · der Wirtschaftlichkeits-Wächter `R7` · `nichtUmlagefaehigGesamtCent` als Zulieferung für Seite 01 D12 Block (b) · die Versionierung des Katalogs über `gueltigVon`/`gueltigBis`.

### Deferred to `docs/08` (Seite 01) — do not duplicate, that file is the source

Die sechs Umlageschlüssel und ihre Formeln · Nennerbildung, Tagesgewichtung, Division-durch-Null-Guards · die Fiktivbelegung bei Leerstand (D0) · zeilenweise Rundung `round_half_up` · die Residuumsregel für den Eigentümeranteil und die Aufteilung in (a)/(b)/(c) · die Verteilung des Lohnanteils auf die einzelnen Mieter (`anteil35aCent`) · Abschnittsreihenfolge und Wortlaut der gedruckten Abrechnung · Vorauszahlung → Saldo · § 556-Fristenarithmetik.

Die Beispielrechnungen dieser Seite verteilen zwar bis auf den Cent — das ist **Verifikation gegen `08-F01`, keine zweite Implementierung.** Im Code verteilt ausschließlich die Engine aus `docs/08`.

### Not covered by this page at all

- **Heiz- und Warmwasserkosten inhaltlich** — 50/50-Split, Gradtagszahlen, § 9 HeizkostenV, CO₂-Stufenmodell, Öltank-Logik → Seite 01b (`01b-F01 … 01b-F31`). Diese Seite liefert für Nr. 4, 5 und 6 nur `umlagefaehig`, `betrkvNummer` und `periodenprinzip = leistung`.
- **Anlage-V-Zeilen und SKR03/SKR04-Konten** je Kostenart → Seite 04 / `docs/11`. Das Feld `anlageVKategorie` ist hier nur ein Platzhalter, den Seite 04 füllt.
- **Wächter, Fristen, Eskalation** (Eichfrist, § 556-Frist, § 543) → Seite 05. Der Wirtschaftlichkeits-Wächter `R7` bleibt hier, weil er an der Kostenart hängt und nicht an einem Datum.
- **Vertragsklauseln zur Umlagevereinbarung** — Formulierungsbausteine, BGH-Sensibilität, unwirksame Kombinationen → Seite 06. Diese Seite **liest** `vertrag.umlageVereinbarung` und `vertrag.benannteSonstige`, sie erzeugt sie nicht.
- **OCR und Rechnungserfassung** — Modell, Prompts, Feldextraktion, Konfidenz. Diese Seite definiert nur das Zielschema aus 3.4.
- **Vorjahresvergleich und Plausibilitätsanalyse über mehrere Perioden.** `R7` prüft eine Periode gegen eine statische Bandbreite, nicht gegen die Historie des Objekts.
- **Landesrecht und kommunale Gebührensatzungen** (Grundsteuer-Hebesätze, Müll- und Straßenreinigungsgebühren). Steht nicht im Rechtsstand-Register und wird von der Tageskontrolle nicht geprüft.

### Non-Goals V1 — Ergänzung aus dieser Seite

| Nicht-Ziel | Begründung | Betroffene Seite | Wiedervorlage |
| --- | --- | --- | --- |
| **Vorwegabzug bei gemischt genutzten Objekten** (Wohnen + Gewerbe) | Erfordert eine zweite Nennerebene je Kostenart und die Bewertung, ob die Gewerbeeinheit „erhebliche Mehrkosten" verursacht — eine Tatfrage, keine Formel. R2 Schritt 3 blockiert Gewerbeeinheiten hart. | 02, 01 | V2 |
| **Umsatzsteuer-Option und Vorsteueraufteilung** | Zieht sich durch jede Kostenart und jede Anlage-V-Zeile. Bestätigt den bestehenden Non-Goal aus Seite 01. | 02, 01, 04 | V2 |
| **Automatische Kostenart-Erkennung aus dem Rechnungstext ohne Bestätigung** | Der Katalog schlägt vor, der Nutzer bestätigt. Eine falsch erkannte Kostenart erzeugt eine formal fehlerhafte Abrechnung, die der Mieter angreifen kann. | 02 | nicht geplant |
| **Prüfung, ob eine Rechnung sachlich berechtigt ist** | Lokara prüft die Umlagefähigkeit, nicht die Leistungserbringung. Haftungsabgrenzung. | 02 | nicht geplant |
| **Eigenleistung des Vermieters nach § 1 Abs. 1 S. 2 BetrKV** (fiktiver Fremdvergleichswert ohne USt) | Erfordert eine belastbare Marktpreisableitung und ist prüfungsanfällig. V1 nimmt nur belegte Fremdrechnungen. | 02 | V1.x |
| **Umlage nach dem Verursacherprinzip jenseits der erfassten Verbräuche** (§ 556a Abs. 1 S. 2 Alt. 2) | Setzt eine Verursachungserfassung voraus, die kein Vermieter hat. | 02 | nicht geplant |
| **Mieterhöhung wegen gestiegener Betriebskosten** (§ 560 Abs. 1) als Dokument | Diese Seite prüft nur, **ob** eine neue Kostenart umlagefähig ist. Das Erhöhungsschreiben ist ein eigenes Dokument. | 02, 06 | V1.x |

## Offene Punkte

| # | Punkt | Adressat |
| --- | --- | --- |
| 1 | **Seite 01 `08-F21` nachziehen:** Block (b) ist nicht mehr `0,00 €`, sondern **1.008,00 €** (09-F19). | Emir |
| 2 | **`docs/03` § 11** widerspricht weiterhin `08-F01` (P-Spalten-Rundung, fehlende Fiktivbelegung). Diese Seite folgt der Notion-Version, nicht der Datei. | Emir |
| 3 | **Zuordnung `trinkwasseruntersuchung`** (Nr. 2 vs. Nr. 17 mit Benennungspflicht) — Fachanwalt. | Berkay |
| 4 | **Umlagefähigkeit `elektropruefung`** (DGUV V3) — Fachanwalt. | Berkay |
| 5 | **Verwaltungskosten per Individualvereinbarung** bei Wohnraum — Fachanwalt. | Berkay |
| 6 | **Bandbreiten 09-K08** je Kostenart sind bisher nur für `versicherung` gesetzt. Die übrigen 31 Zeilen brauchen Werte, sonst läuft `R7` leer. | Berkay |
| 7 | **Rechtsstand-Register:** 09-K01 bis 09-K11 sind noch nicht eingetragen; alle elf brauchen `verify-before-production`. Register 51 → **62**. | Berkay |