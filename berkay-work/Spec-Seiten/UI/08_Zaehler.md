---
spec_id: 04-zaehler
titel: Zähler — Bestandsbaum, einstufiger Wizard, Ablesungen und externe Heizkostenabrechnung
status: freigegeben
prioritaet: hoch
betrifft: apps/web, apps/api, packages/db, gemeinsamer Wächter/Guard
abhaengig_von: [00-layout-global, 02-objekte, 03-kosten]
repo_stand: Lokara-main @ 2026-08-25
---

## Zweck

Die heutige Zählerseite wird von einer langen technischen Kartenfolge mit rechtem Inline-Formular zu
einer skalierbaren Bestandsansicht umgebaut: Objekt → Gebäudezähler/Einheiten → Zähler → Details und
Ablesungen. Zähler werden über einen einstufigen Wizard auf eigener Route angelegt; Eichdaten,
Fernablesbarkeit, Gerätewechsel und externe Heizkostenabrechnungen werden fachlich eindeutig und ohne
vorgetäuschte Integrationen geführt.

Dieser Spec enthält ausschließlich Beschreibungen, keinen Beispiel-Code. Die ausführende KI schreibt
die Implementierung gegen den dann aktuellen Repo-Stand.

## Invarianten

- Pre-Pitch gilt Desktop/Laptop bei 1280, 1440 und 1920 Pixel sowie 200-Prozent-Zoom. Smartphone-,
  Tablet- und native Varianten sind Post-Pitch; Tastatur, Screenreader und sichtbarer Fokus bleiben
  verpflichtend.

- Nur die vorhandenen Design-Tokens Petrol-Ink, Lokara-Grün, Forest, Mint, Slate und Paper sowie die
  vorhandenen Status-Tokens verwenden. Montserrat (`font-display`) gilt für Überschriften, Kennzahlen
  und Zählerstände; Manrope (`font-sans`) für Fließtext, Labels und Tabellen. Keine rohen Farbwerte und
  keine alten Navy-/Teal-/Cream-/Poppins-Vorgaben verwenden.
- Keine neue Frontend-Dependency einführen. Die aufklappbare Hierarchie mit vorhandenen React-, HTML-
  und UI-Package-Mitteln umsetzen; kein neues Accordion-, Dialog- oder Icon-Paket installieren.
- Portfolio-Standard aus `00_Layout-Global`: kein globaler Objektfilter. Der Objektbaum auf dieser
  Fachseite ist der Zählerbestand selbst und keine globale Auswahl, die andere Seiten beeinflusst.
- Zählerstände bleiben append-only. Eine Korrektur ist ein neuer Eintrag; ein bereits verwendeter
  Zähler oder eine Ablesung wird nie überschrieben oder endgültig gelöscht.
- Zählerwechsel, Einbau und Ausbau sind zeitliche Ereignisse. Keine wechselnden Tatsachen als einzigen
  überschreibbaren „aktuellen Wert“ modellieren.
- Keine Eichfrist, Rechtsfolge, Schätzung, Verbrauchsinterpolation oder Abrechnungslogik im Frontend
  erfinden. Das Frontend zeigt ausschließlich strukturierte Ergebnisse aus Backend, Wächter und Engines.
- Wärmemengenzähler und Heizkostenverteiler sind unterschiedliche Gerätetypen. Ein
  Heizkostenverteiler sitzt typischerweise am Heizkörper und zählt Verbrauchseinheiten; ein
  Wärmemengenzähler zählt reale Wärmemenge in kWh. Fernablesbarkeit ändert den Gerätetyp nicht.
- Fernablesbarkeit darf als Geräteeigenschaft gespeichert werden. Eine Verbindung, Synchronisierung
  oder automatische Funkablesung mit Lokara darf nicht angezeigt oder simuliert werden, solange keine
  echte Integration existiert.
- Externe Heizkostenabrechnung ist ein Abrechnungsmodus je Objekt und Zeitraum, kein Zählertyp. Für
  denselben Zeitraum darf nie gleichzeitig ein externes Ergebnis und eine Lokara-Eigenberechnung als
  maßgebliches Heizkostenergebnis verwendet werden.
- OCR ist nur ein sichtbarer, eindeutig inaktiver Zukunftsausblick. Kein Datei-Input, keine Dropzone,
  kein Upload-Request und keine Scheinerkennung bauen.
- Signal nie allein über Farbe transportieren. Status braucht immer lesbaren Text und, wo passend,
  Form oder Symbol.
- Bestehende Account-/Gebäude-/Einheiten-Autorisierung und RLS nicht abschwächen. Jede neue Zeile und
  jeder neue Endpoint bleibt `account_id`-gescopet.
- Bestehende Tests bleiben grün, Typprüfung und Lint bleiben sauber. Neue fachliche Verträge erhalten
  Backend- und Frontend-Tests.
- Bei normaler Unklarheit den genannten Default verwenden und die Annahme in `## Build-Notes`
  festhalten. `⚠️ MUSS-INPUT` nie raten; nur den betroffenen Teil überspringen und den Rest umsetzen.

## Befehle

### [Z1] Seitenkopf und Informationsarchitektur neu ordnen

- **Datei/Ort:** `apps/web/src/features/zaehler/meters-page.tsx`, gesamter sichtbarer Aufbau von
  `MetersPage` und `MetersForBuilding`; Einbindung weiterhin über
  `apps/web/src/app/a/[accountId]/zaehler/page.tsx`.
- **Fundstelle:** Der heutige Kopf „Zähler“ mit dem langen Absatz über Eichfrist und append-only
  Korrekturen; darunter der Objekt-Umschalter, anschließend zuerst „Heizkosten des Gebäudes“, die
  Eichwarnungen und das zweispaltige Raster aus Zählerkarten und „Zähler anlegen“.
- **Ist:** Der primäre Gerätebestand beginnt erst nach dem Heizkostenformular. Bei mehreren Objekten
  wird genau ein Objekt ausgewählt; alle Zähler werden als lange Kartenfolge gerendert. Das Anlegen
  belegt dauerhaft die rechte Spalte.
- **Soll:** Den Kopf auf eine kurze Nutzerbotschaft reduzieren und direkt darunter eine Kopfaktionszeile
  anlegen. Danach den vollständigen aufklappbaren Bestandsbaum aus [Z2] rendern. Heizkosten-
  Abrechnungsgrundlagen folgen erst nach dem Zählerbestand als eigener Abschnitt aus [Z11]/[Z12]. Das
  rechte Inline-Formular vollständig entfernen; Zähler werden ausschließlich über den Wizard [Z5]
  angelegt.
- **Default:** Titel „Zähler“. Untertitel „Zähler, Ablesungen und Gerätestatus je Objekt und Einheit.“
  In der Kopfaktionszeile rechts zuerst die bedingte Warnaktion aus [Z3], danach der primäre Button
  „Zähler anlegen“. Der Button führt auf `/a/{accountId}/zaehler/neu`; wird er innerhalb eines
  geöffneten Objekts ausgelöst, dessen Objekt-ID als Query-Parameter `objektId` mitgeben.
- **Erwartetes Ergebnis:** Beim Öffnen der Seite versteht ein privater Vermieter sofort: Hier verwaltet
  er seinen Zählerbestand und die Ablesungen. Die erste große Inhaltsfläche ist der Bestand, nicht eine
  Brennstoffrechnung. Es gibt genau eine primäre Aktion oben rechts. Die Seite nutzt die volle
  verfügbare Standardbreite aus `00_Layout-Global` und kein altes 3:2-Formularraster.
- **Akzeptanz:** Im sichtbaren Seitenkopf steht der kurze Untertitel. `CreateMeterForm` wird nicht mehr
  in `meters-page.tsx` gerendert. „Zähler anlegen“ führt auf eine eigene URL. Der Zählerbestand steht
  vor dem Heizkostenbereich.
- **Nicht tun:** Navigation oder App-Shell umbauen; globalen Objektfilter ergänzen; Heizkosten- oder
  Abrechnungsdaten löschen.

### [Z2] Aufklappbaren Bestandsbaum Objekt → Einheit → Zähler bauen

- **Datei/Ort:** `apps/web/src/features/zaehler/meters-page.tsx`; Präsentationskomponenten in neuen,
  fachlich benannten Dateien unter `apps/web/src/features/zaehler/`, beispielsweise für Objekt-,
  Einheiten- und Zählerzeilen. Bestehende `meter-list.tsx`, `reading-history.tsx` und
  `create-reading-form.tsx` entweder gezielt weiterverwenden oder entlang dieser Struktur aufteilen.
- **Fundstelle:** Der heutige Objekt-Button-Umschalter und `MeterList`, die alle Zähler des ausgewählten
  Gebäudes als flache Kartenfolge ausgibt.
- **Ist:** Nur ein Objekt ist gleichzeitig sichtbar. Gebäudezähler und Einheitenzähler liegen in einer
  flachen Liste; die Zuordnung erkennt man nur an Texten wie „Gebäude (Hauptzähler)“ oder
  „Wohnung A“. Bei größerem Bestand wird die Seite extrem lang.
- **Soll:** Alle für den Nutzer sichtbaren Objekte als erste Accordion-Ebene darstellen. Beim Öffnen
  eines Objekts erscheinen in dieser Reihenfolge: „Gebäudezähler“, danach alle Einheiten des Objekts.
  Jede Einheit ist eine zweite aufklappbare Ebene. Nach Öffnen erscheinen die aktiven Zähler dieser
  Einheit als kompakte Zählerzeilen; ausgebaute/stornierte Geräte stehen getrennt unter „Historische
  Zähler“. Jede Zählerzeile lässt sich als dritte Ebene öffnen und zeigt Stammdaten, Verbrauch,
  Ableseaktion und Historie.
- **Default:** Beim ersten Laden alle Objekte geschlossen, außer es gibt genau ein Objekt; dann dieses
  Objekt öffnen, seine Einheiten aber geschlossen lassen. Ein aus URL-Fragment/Query adressierter
  Warnzähler überschreibt diesen Default und öffnet automatisch seinen vollständigen Pfad. Pro
  Accordion-Schalter ein echtes `button`-Element mit `aria-expanded` und `aria-controls`; Enter und
  Leertaste funktionieren nativ. Geöffnete Zustände leben nur im Seiten-State, nicht in localStorage.
- **Erwartetes Ergebnis:** Geschlossen zeigt ein Objekt Name, Adresse, Anzahl aktiver Zähler und
  zusammengefasste offene Status („2 Eichdaten fehlen“, „1 Eichfrist abgelaufen“). „Gebäudezähler“
  umfasst Geräte ohne Einheit. Eine geschlossene Einheit zeigt Name, Zähleranzahl und Warnanzahl.
  Eine geschlossene Zählerzeile zeigt Gerätetyp, Bezeichnung/Einbauort, Zählernummer, letzte wirksame
  Ablesung, Eichstatus und Fernablesbarkeit. Erst geöffnet erscheinen Details und Historie. Lange
  Bestände bleiben dadurch schnell scannbar.
- **Akzeptanz:** Ein Konto mit mehreren Objekten zeigt alle Objekte in derselben Seite. Ein Zähler der
  Wohnung A ist über Objekt → Wohnung A → Zähler erreichbar; ein Hauptzähler über Objekt →
  Gebäudezähler → Zähler. Die Seite rendert keine flache Folge aller Karten mehr. Tastatur und
  Screenreader können jede Ebene öffnen und schließen.
- **Nicht tun:** Einheiten ohne Zähler ausblenden; Gebäudezähler künstlich einer Einheit zuordnen;
  Objekte anhand eines globalen Filters entfernen; historische und aktive Geräte vermischen.

### [Z3] Abgelaufene Eichfristen als Kopfaktion mit Direktsprung anzeigen

- **Datei/Ort:** Kopfaktionszeile aus [Z1], Bestandsbaum aus [Z2] und die von [Z9] gelieferte
  Guard-/Statusantwort.
- **Fundstelle:** Die heutigen separaten roten/gelben `StatusNote`-Blöcke oberhalb der flachen
  Zählerliste, die Seriennummern als Text aufzählen.
- **Ist:** Die Warnung nennt betroffene Nummern, führt aber nicht zum Gerät. Sie basiert auf einer
  lokalen Router-Klassifikation und steht weit entfernt von der Anlegeaktion.
- **Soll:** Wenn mindestens ein sichtbarer Zähler den vom Backend gelieferten Status `EXPIRED` trägt,
  neben „Zähler anlegen“ eine Warnschaltfläche anzeigen. Klick öffnet den vollständigen Accordion-Pfad
  des ersten beziehungsweise nächsten betroffenen Zählers, scrollt ihn mit reduziertem Motion-Verhalten
  in den sichtbaren Bereich und setzt den Tastaturfokus auf dessen Statuskopf.
- **Default:** Text exakt „Eichfrist von 1 Zähler abgelaufen“ beziehungsweise „Eichfrist von X Zählern
  abgelaufen“. Warnstil aus den vorhandenen Tokens, nicht destruktiv rot. Nach dem Sprung zeigt die
  geöffnete Zähleransicht „1 von X“ sowie kleine Aktionen „Vorheriger“ und „Nächster“, wenn mehrere
  Treffer existieren. Die Reihenfolge folgt Objektname, Einheit/Gebäudezähler, Gerätetyp,
  Zählernummer. Bei `prefers-reduced-motion` ohne animiertes Scrollen springen.
- **Erwartetes Ergebnis:** Die Warnung ist früh sichtbar und führt mit einem Klick zum Handlungsort.
  Objekt, Einheit und Zähler öffnen sich automatisch; der Nutzer muss keine Seriennummer in der Liste
  suchen. Status `MISSING_DATA` oder `REVIEW_REQUIRED` zählt nicht in die Zahl abgelaufener Fristen.
- **Akzeptanz:** Bei X abgelaufenen Geräten enthält die Schaltfläche X. Klick fokussiert einen tatsächlich
  abgelaufenen Zähler. „Nächster“ erreicht alle X Treffer genau einmal. Ohne abgelaufenen Zähler fehlt
  die Kopfaktion vollständig.
- **Nicht tun:** Ablaufstatus im Frontend berechnen; „Eichdaten fehlen“ als abgelaufen zählen;
  Warnzustand nur über Farbe zeigen.

### [Z4] Gerätetypen und Stammdaten im Datenmodell eindeutig machen

- **Datei/Ort:** `packages/domain/src/lokara_domain/meter.py`, Zählermodelle und neue Migration unter
  `packages/db`, `apps/api/src/lokara_api/schemas.py`, `apps/api/src/lokara_api/routers/meters.py`,
  `apps/web/src/lib/contracts.ts` und `apps/web/src/features/zaehler/queries.ts`.
- **Fundstelle:** Aktuell unterscheiden `MeterKind` und `measurement_unit` nur `HEAT`, `WARM_WATER`,
  `COLD_WATER` sowie kWh/m³/HKV-Einheiten. Wärmemengenzähler und Heizkostenverteiler heißen im UI beide
  „Wärme“ und werden indirekt über die Maßeinheit unterschieden. `label` und Bewertungsfaktor existieren
  im Vertrag, werden im Anlegeformular aber nicht vollständig geführt.
- **Ist:** Geräteidentität, Medium und Maßeinheit sind vermischt. Lifecycle- und Fernablesedaten fehlen.
  `calibration_valid_until = null` bedeutet pauschal „nicht eichpflichtig“ und kann fehlende Daten nicht
  abbilden.
- **Soll:** Einen expliziten Gerätetyp als Backend-Stammdatum einführen: Wärmemengenzähler,
  Heizkostenverteiler, Warmwasserzähler, Kaltwasserzähler oder Gaszähler. Medium und erlaubte Maßeinheit werden
  serverseitig aus diesem Typ validiert. Ergänzen: genauer Einbauort/Bezeichnung, Einbaudatum,
  Fernablesestatus `REMOTE_READABLE | NOT_REMOTE_READABLE | UNKNOWN`, Eichdatenzustand aus [Z9] und
  Lifecycle-Felder aus [Z6]. Bestehende Zähler migrationssicher anhand ihrer bisherigen Art und
  Maßeinheit zuordnen; mehrdeutige Bestandsdaten als prüfbedürftig kennzeichnen, nicht raten.
- **Default:** Anzeigenamen „Wärmemengenzähler“, „Heizkostenverteiler“, „Warmwasserzähler“,
  „Kaltwasserzähler“ und „Gaszähler“. Zuordnung: Wärmemengenzähler → kWh; Heizkostenverteiler →
  Verbrauchseinheiten; Warm-/Kaltwasserzähler → m³; Gaszähler → Wärme in m³. Gaszähler sind
  ausschließlich für Erdgas vorgesehen. Ihre Umrechnung in kWh verwendet den versionierten Brennwert
  × die versionierte Zustandszahl aus der Versorgerabrechnung; beide Werte, Gültigkeitszeitraum und
  Quelle bleiben in der UVI-Provenienz sichtbar. Bewertungsfaktor nur für Heizkostenverteiler beziehungsweise fachlich
  dafür freigegebene Wärmegeräte zulassen. API-Feldnamen folgen der vorhandenen snake_case/camelCase-
  Konvention.
- **Erwartetes Ergebnis:** Das UI bezeichnet einen Heizkostenverteiler nie mehr nur als „Wärme“.
  Engines erhalten weiterhin die bisherigen normalisierten Medium-/Einheitswerte, während Verwaltung
  und Nutzerführung den konkreten Gerätetyp kennen. Fehlende Eichdaten sind technisch von „nicht
  eichpflichtig“ unterscheidbar.
- **Akzeptanz:** Jeder neue Zähler besitzt einen expliziten Gerätetyp. Unzulässige Typ-/Einheiten-
  Kombinationen werden am API-Rand abgelehnt. Bestehende Demo-HKV erscheinen als
  „Heizkostenverteiler“, der zentrale kWh-Zähler als „Wärmemengenzähler“. Zusätzlich ist genau
  `GAS_METER + HEAT + CUBIC_METRE` zulässig; Gaszähler mit Warm-/Kaltwasser oder kWh bleiben
  unzulässig. Migration und Downgrade sind getestet.
- **Nicht tun:** Bestehende Engine-Enums ungeprüft ersetzen; aus „fernablesbar“ einen Gerätetyp machen;
  unklare Bestandszeilen still als „nicht eichpflichtig“ einstufen.

### [Z5] Einstufigen Zähler-Wizard auf eigener Route bauen

- **Datei/Ort:** Neue Route `apps/web/src/app/a/[accountId]/zaehler/neu/page.tsx`, neue Wizard-Komponente
  unter `apps/web/src/features/zaehler/`; `create-meter-form.tsx` wird durch den Wizard ersetzt oder nur
  noch als intern wiederverwendbarer Teil ohne alte Kartenhülle genutzt.
- **Fundstelle:** Das heutige rechte Inline-Formular „Zähler anlegen“ mit Zählerart, Zähleinheit,
  Zählernummer, Einbauort und optionaler Eichfrist.
- **Ist:** Das Formular ist dauerhaft sichtbar, vermischt Gerätetyp und Maßeinheit, hat kein sichtbares
  Bezeichnungsfeld trotz internem `label`, keine Lifecycle-Auswahl, keine Fernablesbarkeit und keine
  saubere Trennung der Eichfälle.
- **Soll:** Eine eigene, einstufige Wizard-Seite bauen. „Einstufig“ bedeutet eine URL und ein Formular,
  nicht mehrere nacheinander navigierte Schritte. Das Formular ist in klar beschriftete Bereiche
  gegliedert; abhängige Felder erscheinen direkt nach der jeweiligen Auswahl. Reihenfolge: Zuordnung,
  Gerätetyp, Gerätedaten, Fernablesbarkeit, Eichangaben, Anlegeart, Zusammenfassung/Absenden.
- **Default:**
  - **Zuordnung:** Objekt als Pflichtauswahl; `objektId` vorbelegen. Auswahl „Gebäude/Heizungsanlage“
    oder „Einheit“. Bei Einheit anschließend Pflichtauswahl der Einheit. Feld „Einbauort/Raum
    (optional)“, Beispiel „Wohnzimmer“ oder „Heizzentrale“.
  - **Gerätetyp:** fünf Auswahlkacheln aus [Z4], genau eine. Nach Wahl die feste Maßeinheit lesbar
    anzeigen, aber nicht als frei kombinierbares Feld anbieten.
  - **Gerätedaten:** Zählernummer Pflicht; „Eigene Bezeichnung (optional)“; Hersteller und Modell
    optional; Einbaudatum Pflicht. Bewertungsfaktor nur zeigen, wenn der Gerätetyp ihn fachlich nutzt;
    Hilfetext „Bitte vom Gerät oder Messdienstleister übernehmen."
  - **Gasumrechnung:** Bei „Gaszähler“ Brennwert (kWh/m³), Zustandszahl, Gültigkeitsbeginn,
    optionales Gültigkeitsende und die Beleg-/Rechnungsreferenz als Pflichtangaben zeigen. Kein Wert
    wird hartkodiert oder geschätzt. Die Werte werden als append-only Gebäudekonfiguration versioniert.
  - **Fernablesbarkeit:** Pflichtauswahl „Fernablesbar“, „Nicht fernablesbar“, „Unbekannt“. Bei
    „Fernablesbar“ ausschließlich den ehrlichen Hinweis aus [Z10], keine Verbindungsfelder.
  - **Eichangaben:** Pflichtauswahl „Eichpflichtig – Eichdaten vorhanden“, „Eichpflichtig – Eichdaten
    fehlen“, „Nicht eichpflichtig“ oder „Unklar – später prüfen“. Abhängige Felder/Status aus [Z9].
  - **Anlegeart:** „Neuen Zähler einbauen“, „Bestehenden Zähler nachtragen“ oder „Vorhandenen Zähler
    ersetzen“. Ersatz öffnet die Felder aus [Z6].
  - Primärbutton „Zähler anlegen“, Ladecopy „Wird angelegt…“. Sekundär „Abbrechen“ zurück zur Liste.
  - Entwurfsschlüssel `{accountId}.{buildingId-or-new}.meter-create`; vorhandenes `useFormDraft`-Muster
    nutzen.
- **Erwartetes Ergebnis:** Der Nutzer entscheidet über verständliche Gerätetypen und Sachverhalte,
  nicht über technische Enum-Kombinationen. Abhängige Felder halten die Seite trotz Einstufigkeit
  übersichtlich. Nach Erfolg erscheint auf derselben Route eine Bestätigung „Zähler angelegt“ mit
  Gerätetyp, Objekt, Einheit/Anlage und Zählernummer sowie den Aktionen „Erste Ablesung erfassen“,
  „Noch einen Zähler anlegen“ und „Fertig – zur Zählerliste“.
- **Akzeptanz:** Wizard ist über den Kopfbutton erreichbar und enthält alle genannten Bereiche. Ein
  Kaltwasserzähler kann nicht in kWh angelegt werden. „Noch einen Zähler anlegen“ leert den Entwurf;
  „Fertig“ öffnet und fokussiert den neuen Zähler im Bestandsbaum. Typprüfung und Formulartests grün.
- **Nicht tun:** Kein Modal; keinen mehrseitigen Schritt-Wizard; keine Eichfrist selbst berechnen; keine
  Funkverbindung oder OCR in diesen Geräte-Wizard einbauen.

### [Z6] Einbau, Ausbau und Austausch als zusammenhängenden Lifecycle umsetzen

- **Datei/Ort:** Zählermodelle/Migration, Meter-Schemas und Router im Backend; Wizard [Z5] und geöffnete
  Zählerdetails im Frontend.
- **Fundstelle:** Heutiger DELETE-Endpoint `/meters/{meter_id}`, der einen Zähler samt allen Ablesungen
  löscht; vorhandener Ablesegrund `DEVICE_CHANGE` ohne Beziehung zwischen altem und neuem Gerät.
- **Ist:** Zähler besitzen keinen aktiven Zeitraum und keine Vorgänger-/Nachfolgerverknüpfung. Ein
  Austausch kann nur als isolierte Ablesung notiert werden. Hard-Delete zerstört die gesamte Historie;
  die Sperre nach finalisierter Abrechnung ist nur ein TODO.
- **Soll:** Zähler mit `valid_from`/`valid_to` beziehungsweise gleichwertigem Einbau-/Ausbauzeitraum und
  Lifecycle-Status führen. Austausch als atomaren Backend-Workflow umsetzen: altes Gerät auswählen,
  Austauschdatum, Schlussstand alt, Anfangsstand neu, Grund optional; altes Gerät beenden, neues anlegen,
  beide verknüpfen und die beiden Wechselablesungen append-only erzeugen. Einen aktiven Zähler über
  „Zähler ausbauen“ mit Pflichtdatum und Pflichtgrund beenden. Hard-Delete aus dem Nutzer-UI entfernen.
- **Default:** Status `ACTIVE`, `REMOVED`, `REPLACED`, `VOID`. „Falsch angelegt“ darf nur als
  kontrolliertes `VOID` mit Pflichtbegründung erfolgen, solange der Zähler weder Ablesungen noch eine
  Referenz in einer finalisierten Abrechnung besitzt; andernfalls ausschließlich Ausbau/Austausch.
  Historische Geräte bleiben im Objekt/der Einheit sichtbar, standardmäßig eingeklappt.
- **Erwartetes Ergebnis:** Ein Gerätewechsel bildet zwei Geräte und einen nachvollziehbaren Übergang ab.
  Verbrauch wird nie über die zurückgesetzten Register verschiedener Zähler hinweg subtrahiert. Alte
  Ablesungen bleiben dauerhaft auffindbar. Finalisierte Abrechnungen behalten ihre Quellen.
- **Akzeptanz:** Nach Austausch ist der Vorgänger beendet, der Nachfolger aktiv und beider Verknüpfung
  abrufbar. Schluss- und Anfangsablesung stehen in den jeweiligen Historien. Der bisherige Button
  „Zähler löschen“ fehlt. Backend-Tests beweisen, dass verwendete Zähler nicht vernichtet werden.
- **Nicht tun:** Ablesungen verschieben, überschreiben oder löschen; Austausch nur als Textnotiz führen;
  Verbrauch über zwei Geräte-IDs durch einfache Differenz berechnen.

### [Z7] Ablesungserfassung auf aktuellen Kontext und Backend-Plausibilität umstellen

- **Datei/Ort:** `apps/web/src/features/zaehler/create-reading-form.tsx`, `queries.ts`, Contracts und
  Meter-Reading-Endpoint/Schemas.
- **Fundstelle:** Das aufgeklappte Formular „Ablesung erfassen“ mit festem Defaultdatum `31.12.2025`,
  Wert, Grund und Notiz; generischer 422-Text „Bitte Datum und Zählerstand prüfen.“
- **Ist:** Datum und globaler Abrechnungszeitraum sind auf 2025 festgelegt. Letzter wirksamer Stand,
  Austauschkontext und strukturierte Plausibilitätsbefunde fehlen. Quelle `MANUAL` wird technisch
  gesetzt, aber im Formular nicht erklärt.
- **Soll:** Im geöffneten Zähler einen kompakten Erfassungsbereich anbieten. Zähler, Gerätetyp,
  Maßeinheit, letzte wirksame Ablesung und deren Datum oberhalb der Felder sichtbar machen. Datum,
  Zählerstand, Ablesegrund und optionale Notiz erfassen. Das Backend validiert und liefert
  strukturierte Befunde für Rückwärtslauf, doppeltes Datum, auffällige Differenz, außerhalb des aktiven
  Gerätezeitraums und Wechselkonflikte. Feld- oder Hinweistext dem konkreten Befund zuordnen.
- **Default:** Ablesedatum = heutiges lokales Datum, nicht Abrechnungsjahresende. Quelle sichtbar als
  ruhige Information „Manuell erfasst“, nicht als änderbare Auswahl. Bei `CORRECTION` Pflichtauswahl der
  zu korrigierenden Ablesung und Pflichtbegründung. Bei `TENANT_CHANGE` die zu diesem Datum passende
  Mietpartei serverseitig vorschlagen und bestätigbar anzeigen; nicht im Browser aus Zeiträumen raten.
  Bei `DEVICE_CHANGE` auf den Austauschworkflow [Z6] verweisen statt eine unverbundene Einzelablesung zu
  erzeugen.
- **Erwartetes Ergebnis:** Der Nutzer sieht vor Eingabe, welchen Stand er fortschreibt. Normale Werte
  werden direkt gespeichert. Warnwürdige, aber fachlich zulässige Werte verlangen eine bewusste
  Bestätigung mit verständlicher Erklärung; unzulässige Werte werden feldnah abgelehnt. Ein Fehler
  nennt nicht nur „422“ oder „prüfen“.
- **Akzeptanz:** Kein festes 2025-Datum im Formular. Rückwärtsstand erhält einen strukturierten Befund und
  wird nicht still als Verbrauch genutzt. Korrektur lässt sich ohne Ziel und Begründung nicht senden.
  Gespeicherte manuelle Ablesung zeigt Quelle „Manuell erfasst“.
- **Nicht tun:** Schwellwerte für Auffälligkeit im Frontend erfinden; rückwärts laufenden Zähler als
  negativen Verbrauch abrechnen; Nutzerdaten anhand des Browsers allein zuordnen.

### [Z8] Ablesehistorie und Verbrauchsentwicklung verständlich darstellen

- **Datei/Ort:** `reading-history.tsx`, geöffnete Zählerdetails und neue read-only Backend-Projektion für
  Zeitraum/Verbrauch; bestehende Adapter-/Engine-Faltung wiederverwenden.
- **Fundstelle:** Aktuelle Tabelle mit Datum, Zählerstand, Grund, Quelle und Status sowie das einzelne
  Feld „Verbrauch 01.01.2025–31.12.2025“ aus `MeterOut`.
- **Ist:** Die Historie ist nachvollziehbar, aber der Verbrauch ist an globale 2025-Konstanten gebunden.
  Anfangs-/Endstand und der genaue Grund eines fehlenden Verbrauchs sind nicht sichtbar. Eine
  Entwicklung über Zeiträume fehlt.
- **Soll:** Über den Zählerdetails eine Zeitraumwahl für vorhandene, backendseitig angebotene
  Abrechnungsperioden setzen. Dazu eine Verbrauchszusammenfassung mit wirksamer Anfangsablesung,
  Endablesung, Differenz, Maßeinheit und Status `MEASURED | INCOMPLETE | ESTIMATED | NOT_APPLICABLE`.
  Eine einfache Verbrauchsentwicklung nur rendern, wenn das Backend echte periodisierte Werte liefert.
  Historientabelle beibehalten. Eine eigenständige mobile Kartenvariante ist Post-Pitch.
- **Default:** Vorauswahl = laufender beziehungsweise jüngster vom Backend angebotener Zeitraum; keine
  im Frontend erzeugte Jahresliste. Fehlzustände konkret: „Anfangsablesung fehlt“, „Endablesung fehlt“,
  „Gerätewechsel im Zeitraum“ oder der gelieferte Backend-Befund. Geschätzte Werte zeigen Methode,
  Grundlage und Provenienz, sofern geliefert. Abgelöste Korrekturen bleiben durchgestrichen plus Wort
  „Abgelöst“.
- **Erwartetes Ergebnis:** Ein Vermieter kann nachvollziehen, aus welchen zwei wirksamen Ständen ein
  Verbrauch entstanden ist. Die Seite erfindet bei fehlenden Daten weder `0` noch eine Kurve. Spätere
  UVI-/Monatswerte können dieselbe Projektion nutzen, ohne die jährliche Abrechnungsfaltung zu verändern.
- **Akzeptanz:** Keine sichtbare fest verdrahtete Periode 2025. Bei vollständigem Paar stimmen Differenz
  und Abrechnungseingang überein. Bei unvollständigem Paar wird der konkrete fehlende Bestandteil
  genannt. Abgelöste Zeilen bleiben sichtbar.
- **Nicht tun:** Lineare Monatsinterpolation im Frontend; geschätzten und gemessenen Verbrauch gleich
  darstellen; historische Korrekturen ausblenden.

### [Z9] Eichdatenzustände trennen und an den gemeinsamen Wächter anbinden

- **Datei/Ort:** Zählermodell/Schemas, gemeinsamer Guard/Wächter gemäß `PLAN.md` und
  `docs/12-guards-deadlines.md`, Meter-Router, `calibration-badge.tsx`, Wizard [Z5] und Kopfaktion [Z3].
- **Fundstelle:** Aktuell `calibration_valid_until` sowie die lokale Router-Funktion
  `_calibration_status` mit 90-Tage-Warnfenster. `null` wird immer als `NOT_APPLICABLE` ausgegeben;
  der Seitenhinweis enthält eigenen Rechtstext.
- **Ist:** „Nicht eichpflichtig“ und „Eichdaten fehlen“ sind nicht unterscheidbar. Friststatus und
  Warnschwelle sind Meter-Router-Sonderlogik statt gemeinsamer Wächter. Der Nutzer trägt direkt ein
  Gültig-bis-Datum ein.
- **Soll:** Den Sachverhalt explizit speichern: `DATA_AVAILABLE`, `MISSING_DATA`, `NOT_APPLICABLE` oder
  `REVIEW_REQUIRED`. Bei vorhandenen Daten die vom freigegebenen Regelmodell benötigte Ausgangsangabe
  speichern; Gültig-bis, Stufe, Text und Rechtsstand ausschließlich vom versionierten Backend-Wächter
  liefern. Badge und Kopfaktion rendern nur diese Projektion.
- **Default:** Wizardtexte:
  - „Eichpflichtig – Eichdaten vorhanden“ → erforderliche Ausgangsdatenfelder zeigen.
  - „Eichpflichtig – Eichdaten fehlen“ → nach Anlage Status „Eichdaten fehlen“ und Aktion „Eichdaten
    ergänzen“.
  - „Nicht eichpflichtig“ → neutraler Status; beim Heizkostenverteiler als erwarteter Vorschlag, aber
    serverseitig validieren.
  - „Unklar – später prüfen“ → Status „Eichpflicht prüfen“, nie als nicht eichpflichtig behandeln.
  Statusnamen: `VALID`, `EXPIRING_SOON`, `EXPIRED`, `MISSING_DATA`, `NOT_APPLICABLE`,
  `REVIEW_REQUIRED`.
- **⚠️ MUSS-INPUT:** Verbindlicher versionierter Eichfrist-Regelstand einschließlich der Behandlung von
  Übergangsfällen. `PLAN.md` nennt noch einen 5-/6-Jahres-Konflikt; Dokumentstellen enthalten einen
  späteren Sechs-Jahres-Stand mit weiterhin unsicherem Übergang. Bis die maßgebliche Backend-Regel
  freigegeben ist, keine neue Laufzeit oder Übergangsregel raten. Datenzustände, Wizard und neutrale
  fehlende/unklare Zustände trotzdem umsetzen; die bestehende Berechnung nicht heimlich erweitern.
- **Erwartetes Ergebnis:** „Nicht eichpflichtig“, „Eichdaten fehlen“ und „Eichpflicht prüfen“ sind drei
  verschiedene, verständliche Zustände. Nach Freigabe liefert ein gemeinsamer Wächter Ablaufstatus,
  Warnstufe und Text; die Zählerseite enthält keine eigene Tages-/Jahresarithmetik.
- **Akzeptanz:** Ein Zähler mit fehlenden Daten zeigt niemals „Nicht eichpflichtig“. Eine Suche im
  Frontend findet keine Eichfristberechnung. Die alte lokale 90-Tage-Logik wird erst entfernt, wenn die
  Wächterantwort sie vollständig ersetzt; der Übergang bleibt getestet und ohne Statusverlust.
- **Nicht tun:** Fristwerte, Rechtsfolgen oder Übergangsregeln im Frontend hinterlegen; fehlende Daten
  als Ablauf behandeln; Abrechnung allein wegen einer Warnung automatisch blockieren.

### [Z10] Fernablesbarkeit ehrlich als Stammdatum und Vision führen

- **Datei/Ort:** Wizard [Z5], Zählerzeile/-details [Z2], Contracts/Backend-Stammdaten aus [Z4].
- **Fundstelle:** Aktuell existieren Ablesequellen `MANUAL`, `MDL` und `RADIO`, aber keine sichtbare
  Fernablesbarkeit und keine reale Verbindungsmöglichkeit von Funkgeräten mit Lokara.
- **Ist:** Manuell erfasste, Messdienstleister- und Funkquellen sind im Datenmodell vorbereitet; die
  Nutzeroberfläche kann Geräte weder als fernablesbar kennzeichnen noch ehrlich erklären, dass keine
  Integration besteht.
- **Soll:** Fernablesbarkeit als Pflichtauswahl im Wizard speichern und im Bestand anzeigen. Bei
  „Fernablesbar“ ausschließlich einen Zukunftshinweis ausgeben. Keine Anbieter-, Zugangsdaten-,
  Verbindungs-, Synchronisations- oder Testfelder rendern. Automatisch erzeugte Quelle `RADIO` oder
  `MDL` nur bei einem echten späteren Importweg setzen; manuelle Eingaben bleiben `MANUAL`.
- **Default:** Hinweistext: „Fernablesbares Gerät. Die automatische Übertragung von Funkablesungen an
  Lokara ist für eine spätere Version vorgesehen. Ablesungen werden derzeit manuell erfasst.“ In der
  geschlossenen Zählerzeile Badge „Fernablesbar“ beziehungsweise „Nicht fernablesbar“ oder
  „Fernablesbarkeit unbekannt“. Kein „Verbunden“-Badge.
- **Erwartetes Ergebnis:** Lokara kennt die für spätere Prozesse wichtige Geräteeigenschaft, verspricht
  aber keine heutige Verbindung. Nutzer wissen sofort, dass sie den Stand weiterhin manuell erfassen
  müssen. Die Datenstruktur bleibt für spätere Adapter erweiterbar.
- **Akzeptanz:** Ein fernablesbares Gerät lässt sich anlegen und zeigt den Hinweis. Im UI existiert kein
  Wort „verbunden“, kein Verbindungstest und kein Credential-Feld. Eine manuelle Ablesung erhält nie
  Quelle `RADIO`.
- **Nicht tun:** Funkpflicht im Frontend berechnen; Funkfähigkeit aus Hersteller/Modell erraten;
  simulierte Imports oder Anbieterlisten bauen.

### [Z11] Externe Heizkostenabrechnung als Objekt-/Zeitraummodus ergänzen

- **Datei/Ort:** Neuer fachlicher Vertrag und versionierte/persistierte Zeilen in Backend/DB; sichtbarer
  Abschnitt nach dem Zählerbestand in `meters-page.tsx`; vorhandene `heating-cost-section.tsx` und
  Statement-Anbindung kontrolliert erweitern. Abstimmung mit `03_Kosten`, damit kein doppelter
  Erfassungsweg entsteht.
- **Fundstelle:** Der heutige Abschnitt „Heizkosten des Gebäudes“ mit freier Sammelposition,
  Gesamtbetrag, Zeitraum, CO₂-Menge und CO₂-Kosten. Es existiert kein Weg für eine durch einen
  Messdienstleister erstellte Heizkostenabrechnung.
- **Ist:** Lokara behandelt die eingetragenen Heizkosten und Zählerdaten als Grundlage der eigenen
  Berechnung. Ein externer Anbieter kann weder als Modus noch mit Bearbeitungsstatus und bestätigtem
  Ergebnis geführt werden.
- **Soll:** Pro Objekt und Abrechnungszeitraum genau einen Modus führen: „Mit Lokara abrechnen“ oder
  „Durch Messdienstleister abrechnen“. Der Modus ist versioniert und kann nach Finalisierung nicht
  überschrieben werden. Im externen Modus Messdienstleister, Zeitraum, optionale Vertrags-/Vorgangsnummer
  und Workflowstatus erfassen. Externe Ergebnisse erst nach ausdrücklicher Bestätigung als maßgeblich
  an den Statement-Prozess übergeben; Lokaras eigene Heizkostenberechnung für denselben Zeitraum nicht
  parallel als zweites Ergebnis verwenden.
- **Default:** Statusfolge `BEAUFTRAGT`, `DATEN_UEBERMITTELT`, `ABRECHNUNG_ERHALTEN`, `GEPRUEFT`,
  `UEBERNOMMEN`. Anzeigenamen entsprechend „Beauftragt“, „Daten übermittelt“, „Abrechnung erhalten“,
  „Geprüft“, „Übernommen“. Pflichtfelder zunächst Messdienstleister und Zeitraum. Vertragsnummer/Notiz
  optional. Eine manuelle Ergebnisübernahme verlangt mindestens Gesamtergebnis, eindeutige
  Einheiten-/Mietverhältniszuordnung, Quelle/Referenz und Bestätigung. Backend lehnt gleichzeitige
  maßgebliche Eigen- und Fremdberechnung ab.
- **Erwartetes Ergebnis:** Vermieter können ehrlich dokumentieren, dass ista, Techem oder ein anderer
  Messdienstleister abrechnet, ohne diesen Anbieter im Frontend hartzukodieren. Der Zählerbestand bleibt
  in Lokara sichtbar; die Herkunft des Heizkostenergebnisses ist in der späteren Abrechnung eindeutig.
  Noch nicht bestätigte externe Werte fließen nicht in Geldberechnungen ein.
- **Akzeptanz:** Ein Objekt/Zeitraum kann genau einen Modus besitzen. Externes Ergebnis trägt Quelle und
  Prüfstatus. Vor `GEPRUEFT/UEBERNOMMEN` verwendet der Statement-Weg es nicht. Ein Test verhindert zwei
  maßgebliche Heizkostenergebnisse für denselben Objektzeitraum.
- **Nicht tun:** Messdienstleister als Zählertyp modellieren; PDF-Werte ungeprüft in Engines einspeisen;
  externe und interne Heizkosten addieren; Anbieterbehauptungen oder Integrationen erfinden.

### [Z12] OCR-Ausblick nutzerfreundlich, sichtbar und inaktiv darstellen

- **Datei/Ort:** Externer Heizkostenbereich aus [Z11], oberhalb der manuellen Erfassung externer
  Ergebnisse.
- **Fundstelle:** Neuer Modus-Umschalter innerhalb „Durch Messdienstleister abrechnen“.
- **Ist:** Es gibt auf der Zählerseite keine Möglichkeit, eine externe Abrechnung zu übernehmen. Eine
  OCR-/Dokumentenspeicherung ist technisch noch nicht vorhanden.
- **Soll:** Einen Zwei-Segment-Umschalter zeigen: „Manuell erfassen“ aktiv und vorausgewählt;
  „Abrechnung automatisch übernehmen“ sichtbar, aber deaktiviert. Neben dem zweiten Segment ein
  Kennzeichen „Bald verfügbar“. Darunter den konkreten zukünftigen Nutzen erklären, ohne eine heutige
  Uploadmöglichkeit anzudeuten.
- **Default:** Text exakt: „Laden Sie künftig die Abrechnung Ihres Messdienstleisters hoch. Lokara
  erkennt Beträge, Zeiträume und Verbrauchsdaten und bereitet alles zur Prüfung für Sie vor.“ Das
  Segment ist semantisch deaktiviert, nicht fokussierbar und verwendet die gedämpften vorhandenen
  Tokens. Das aktive manuelle Formular bleibt vollständig nutzbar.
- **Erwartetes Ergebnis:** Nutzer erkennen die Produktvision und ihren Nutzen, verstehen aber eindeutig,
  dass sie heute manuell erfassen müssen. Die Oberfläche wirkt nicht wie eine tote technische
  Fehlermeldung und nicht wie ein Fake-Uploader.
- **Akzeptanz:** Text und „Bald verfügbar“ sind sichtbar. Klick, Tap und Tastatur lösen keine Aktion aus.
  Im DOM existieren in diesem Bereich kein Datei-Input und keine Dropzone; im Netzwerk kein Upload-
  oder OCR-Aufruf.
- **Nicht tun:** Nicht trocken nur „OCR kommt später“ schreiben; keinen deaktiviert aussehenden, aber
  anklickbaren Upload bauen; keine Beispieldatei automatisch auswerten.

### [Z13] Heizkosten-Eingaben prüfbar strukturieren und korrekt zur Abrechnung abgrenzen

- **Datei/Ort:** `heating-cost-section.tsx`, Heating-Cost-Schemas/Router/Modelle und Statement-Handoff;
  fachliche Platzierung mit `03_Kosten` abstimmen.
- **Fundstelle:** Die heutige freie Position „Heizung & Warmwasser (Brennstoff, Wartung,
  Betriebsstrom)“ mit einem Gesamtbetrag und optionaler CO₂-Menge/-Kosten.
- **Ist:** Die Demo-Zahlen 10.300,00 €, 4.000 kg und 261,80 € sind intern plausibel; die freie
  Sammelposition reicht aber nicht aus, um eine reale Lieferantenrechnung, einzelne Kostenbestandteile
  und CO₂-Herkunft prüfbar abzubilden. Lieferzeitpunkt, Energieträger, Energiegehalt und Emissionsfaktor
  fehlen in dieser Eingabe.
- **Soll:** Heizkosten-Abrechnungsgrundlagen als nachvollziehbare Positionen und Beleg-/Quellenangaben
  führen. CO₂-Menge und CO₂-Kosten eindeutig der Brennstoff- beziehungsweise Wärmelieferung zuordnen.
  Zusätzlich die für die vorhandenen Backend-Engines bereits vorgesehenen Felder anzeigen, sofern der
  Backend-Vertrag sie liefert; fehlende Rechts-/Berechnungsfelder nicht im Frontend ableiten. Die
  Seite zeigt einen Vollständigkeitsstatus für die spätere Heizkostenabrechnung.
- **Default:** Nutzerseitige Kategorien mindestens „Brennstoff/Wärmelieferung“, „Betriebsstrom“,
  „Wartung“, „Mess-/Abrechnungsdienst“ und „Sonstige zugelassene Heizkostenposition“; der verbindliche
  Katalog und seine Umlagefähigkeit kommen aus dem Backend, nicht aus einer Frontend-Liste. Pro
  Brennstoff-/Wärmelieferung Quelle/Belegreferenz, Liefer-/Leistungszeitraum, Betrag und gelieferte CO₂-
  Angaben erfassen. Status „Vollständig“, „Angaben fehlen“ oder „Prüfung erforderlich“ ausschließlich
  aus Backend-Readiness-Befunden.
- **Erwartetes Ergebnis:** Ein Prüfer kann erkennen, woraus der Gesamtbetrag besteht und welche
  Lieferantenangabe die CO₂-Werte belegt. Lokara behauptet nicht aufgrund eines mathematisch passenden
  Betrags, die Rechnung sei rechtlich legitim. Fehlende Inputs führen zu verständlichen Befunden und
  nicht zu erfundenen Werten.
- **Akzeptanz:** CO₂-Werte besitzen eine eindeutige Quellen-/Positionszuordnung. Eine freie Sammelzeile
  allein kann nicht still als vollständig gelten. Bestehende Demo-Goldens und centgenaue Engines
  bleiben unverändert, solange die Eingabewerte identisch sind.
- **Nicht tun:** CO₂-Preis, Emissionsfaktor, Energieträger oder Rechtsstatus im Frontend raten;
  bestehende Heizkosten-Engine neu implementieren; normale Betriebskosten mit einem freien
  Heizkosten-Umlageschlüssel versehen.

### [Z14] Lade-, Leer-, Fehler-, Erfolg-, Entwurfs- und Berechtigungszustände vereinheitlichen

- **Datei/Ort:** Alle sichtbaren Zählerkomponenten und neue Wizard-/Externe-Abrechnungskomponenten.
- **Fundstelle:** Bestehende Mint-Skeletons, `StatusNote`-Fehler, „Noch kein Objekt“, „Noch keine Zähler
  erfasst“, Entwurfs- und Erfolgshinweise.
- **Ist:** Grundzustände existieren, sind aber auf den ausgewählten Einzelobjekt-/Zweispaltenaufbau
  zugeschnitten. Teils verweisen Texte auf Heizkostenpflicht oder technische API-Prüfung statt auf die
  nächste Nutzeraktion.
- **Soll:** Für jede Accordion-Ebene und jeden Schreibablauf vollständige Zustände definieren. Skeletons
  halten die spätere Höhe stabil. Fehler nennen betroffenen Bereich und bieten „Erneut versuchen“.
  Leerzustände führen zur nächsten erlaubten Aktion. Erfolg bestätigt den konkreten gespeicherten
  Datensatz. Entwurf ist ruhig, aber sichtbar. Nicht berechtigte Nutzer sehen Bestand und Status gemäß
  ihrer bestehenden Sicht, aber keine Schreibaktionen.
- **Default:**
  - Kein Objekt: „Noch kein Objekt“ plus Owner-Link „Objekt anlegen“.
  - Objekt ohne Einheiten/Zähler: Gebäudezählerbereich und vorhandene Einheiten trotzdem zeigen; CTA
    „Zähler anlegen“ nur bei Schreibrecht.
  - Einheit ohne Zähler: „Dieser Einheit ist noch kein Zähler zugeordnet.“ plus CTA.
  - Fehler: verständliche Bereichsbezeichnung, Retry-Button; keine Aufforderung „API und Datenbank
    prüfen“ im Nutzer-UI.
  - Erfolg/Entwurf über vorhandene `StatusNote`-Muster; Screenreader-Live-Region `polite` für Erfolg,
    `assertive` nur für blockierende Fehler.
- **Erwartetes Ergebnis:** Keine leere weiße Fläche und keine Entwicklercopy. Jeder Zustand erklärt,
  was passiert ist und was der Nutzer als Nächstes tun kann. Employee-/Read-only-Sicht enthält keine
  Schaltfläche, die erst serverseitig scheitert.
- **Akzeptanz:** Manuelle Prüfung der Zustände ohne Objekt, ohne Einheit, ohne Zähler, Ladefehler,
  Schreibfehler, Erfolg und wiederhergestellter Entwurf. Nirgends steht „Bitte API und Datenbank
  prüfen“.
- **Nicht tun:** Berechtigungen nur durch versteckte Buttons absichern; Fehlzustand als leere Liste
  tarnen; Demo-Ladefluss anderer Seiten verändern.

### [Z15] Desktop-/Laptop-Bedienung, Fokus und visuelle Konsistenz absichern

- **Datei/Ort:** Bestandsbaum, Zählerdetails, Historie, Wizard und externer Heizkostenbereich.
- **Fundstelle:** Aktuelle lange Kartenfolge, breite Ablese- und Heizkostentabellen, enge Inline-
  Löschbestätigungen und aufklappbare Ableseformulare.
- **Ist:** Basiselemente besitzen Labels und teilweise ARIA-Attribute; eine verbindliche
  Desktop-/Laptop-Fokusführung und ein Direktsprungverhalten fehlen.
- **Soll:** Desktop und Laptop als kompakte, gerahmte Accordion-Liste darstellen. Kein horizontaler
  Seitenscroll im Standardzoom. Öffnen einer Ebene lässt den Fokus am Schalter; Direktsprung [Z3]
  fokussiert den Zielstatus. Nach Formularfehler Fokus auf Fehlerzusammenfassung und danach erstes
  fehlerhaftes Feld ermöglichen. Fokusrahmen aus den UI-Tokens sichtbar lassen.
- **Default:** Pre-Pitch-Breiten 1280, 1440 und 1920 Pixel; keine Smartphone-/Tablet-Sonderlogik.
  Montserrat für Zählerstände/Kennzahlen, Manrope für Tabellenlabels. Ruhige Paper-Flächen, Mint-Rahmen,
  Lokara-Grün nur für primäre Aktion/positiven Akzent, Forest für Labels, Slate für Sekundärtext.
  Übergänge 150–250 ms nur über Höhe nicht erzwingen; bevorzugt Opacity/Transform, bei
  `prefers-reduced-motion` ohne Bewegung.
- **Erwartetes Ergebnis:** Auf Laptop und breitem Desktop bleiben alle Werte mit Label verständlich.
  Tastaturnutzer können den vollständigen Ablauf ohne Maus ausführen. Optik entspricht Dashboard,
  Objekte und Kosten statt der heutigen technischen Formularseite.
- **Akzeptanz:** Prüfung bei 1280, 1440 und 1920 Pixel sowie 200-Prozent-Zoom. Tab-Reihenfolge folgt
  der visuellen Reihenfolge. Jede sichtbare Aktion hat einen Fokuszustand; Status ist ohne Farbe
  verständlich.
- **Nicht tun:** Smartphone-/Tablet-Karten, Touchnavigation oder native Muster Pre-Pitch bauen; Hover
  als einzige Informationsquelle verwenden; rohe Farben oder fremde Schriften ergänzen.

### [Z16] Verträge, Migrationen und Tests als Abnahmeschutz ergänzen

- **Datei/Ort:** API-Tests insbesondere `apps/api/tests/test_meters_api.py` und neue fokussierte Tests;
  Webtests unter `apps/web/src/features/zaehler/`; DB-Migrations-/RLS-Tests; bestehende Adapter- und
  Engine-Tests.
- **Fundstelle:** Backendtests decken aktuell Isolation, Typ-/Einheitenvalidierung, Seriennummer,
  append-only Korrektur, Verbrauch, Eichstatus und Abrechnungswirkung ab. Für die Zähler-UI existieren
  keine eigenen Komponenten-/Interaktionstests.
- **Ist:** Die wichtigsten Recheninvarianten sind geschützt; neue Hierarchie, Wizard, Lifecycle,
  Eichdatenunterscheidung, externe Abrechnung, OCR-Grenze und Desktopinteraktion wären ohne Tests offen.
- **Soll:** Tests für jeden neuen Vertrag und Nutzerfluss ergänzen. Vorhandene Goldens nicht auf neue
  Beispielwerte umbasieren. Migrationen müssen bestehende Demo-Daten deterministisch übernehmen und
  Account-Isolation bewahren.
- **Default:** Mindestens prüfen:
  - expliziter Gerätetyp und unzulässige Kombinationen;
  - Bestandsbaum-Gruppierung Gebäude/Einheiten/historische Geräte;
  - Kopfanzahl und Direktsprung für abgelaufene Eichfristen;
  - getrennte Zustände `MISSING_DATA`, `NOT_APPLICABLE`, `REVIEW_REQUIRED`;
  - Wizard-Pflichtfelder, Entwurf und Bestätigung;
  - atomarer Austausch mit zwei Ablesungen und ohne Querverbrauch;
  - Hard-Delete-Sperre bei Ablesungen/finalisierter Referenz;
  - Korrektur bleibt append-only;
  - manueller Stand erhält `MANUAL`, keine vorgetäuschte Funkquelle;
  - externer Modus verhindert paralleles maßgebliches Lokara-Ergebnis;
  - OCR-Segment ist deaktiviert und erzeugt keinen Upload;
  - Tastatur-/ARIA-Zustände der drei Accordion-Ebenen.
- **Erwartetes Ergebnis:** Die neue Seite ist nicht nur visuell demofähig, sondern schützt Historie,
  Abrechnungsquelle und Gerätezuordnung deterministisch. Spätere Funk-/OCR-Integrationen können neue
  Adapter ergänzen, ohne die manuellen Invarianten zu brechen.
- **Akzeptanz:** Web-Typecheck, Webtests, Python-Tests, Migrations-/RLS-Gates und vorhandene
  Heizkosten-Goldens sind grün. Es gibt mindestens einen Frontendtest für Wizard, Bestandsbaum und
  Warnsprung sowie Backendtests für Lifecycle und externen Modus.
- **Nicht tun:** Bestehende Assertions löschen, um neue Verträge grün zu bekommen; Tests mit echtem
  Funkanbieter, OCR-Netzwerk oder Messdienstleister-Netzwerk ausführen; Goldenbeträge verändern.

## Out of Scope

- Echte Funkgeräte-Verbindung, automatische Funkablesung, Anbieter-Credentials, Gerätesynchronisation
  und produktive MDL-/HeiWaKo-Integration. Sie bleiben Produktvision hinter den vorhandenen Adapter-
  Grenzen.
- Funktionsfähige OCR, Dokumentupload, Dateispeicher, Virenprüfung und automatische strukturierte
  Extraktion externer Heizkostenabrechnungen. Hier nur der inaktive Zukunftsausblick [Z12].
- Produktive Anbieterlisten oder Vertragsabschlüsse mit Messdienstleistern.
- Erfindung oder Änderung rechtlicher Eichfristen, Übergangsregeln, Warnschwellen oder Rechtsfolgen.
- UVI-Berechnung, Monatsinterpolation und automatische Mieterzustellung; diese gehören zu den
  vorgesehenen Guard-/UVI-/Delivery-Slices.
- Neuimplementierung der Heizkosten-, CO₂- oder Statement-Engines und Änderung bestehender Goldenwerte.
- Allgemeiner Objekt-Dashboard-Umbau, globale Reminder-Sidebar und der Desktop-App-Shell-Refactor aus
  `09_App-Shell-Desktop.md`.
- Stromzähler. Gaszähler sind durch die Entscheidung vom 28.08.2026 als fünfter Typ aufgenommen;
  Öl und Pellets bleiben Brennstofflieferungen und sind keine Gaszähler-Medien.

## Verifikation

1. Seite öffnen: Kopf zeigt kurzen Untertitel, bedingte Eichwarnung und „Zähler anlegen“; danach den
   Bestandsbaum, erst später Heizkosten-Abrechnungsgrundlagen.
2. Mehrere Objekte prüfen: alle erscheinen als erste Ebene. Objekt öffnen → Gebäudezähler plus
   Einheiten; Einheit öffnen → ihre Zähler; Zähler öffnen → Details, Ablesung und Historie.
3. Eichwarnung anklicken: korrekter Pfad öffnet sich, Ziel wird fokussiert; mehrere Treffer lassen sich
   vollständig durchlaufen.
4. Wizard: jeden der vier Gerätetypen prüfen; Maßeinheit ist korrekt festgelegt. Eichdaten fehlen,
   nicht eichpflichtig und unklar erzeugen drei verschiedene Status. Fernablesbar zeigt nur den
   Zukunftshinweis, keine Verbindung.
5. Zähler austauschen: Vorgänger bleibt historisch, Nachfolger ist aktiv, Schluss-/Anfangsablesungen
   bleiben getrennt und es entsteht kein Verbrauch über den Reset.
6. Ablesung erfassen und korrigieren: heutiges Datum als Default, strukturierte Plausibilitätsmeldung,
   Korrektur mit Ziel/Begründung; beide Versionen bleiben sichtbar.
7. Externe Heizkostenabrechnung wählen: manueller Workflow funktioniert, unbestätigte Werte fließen
   nicht in die Abrechnung; paralleles maßgebliches Lokara-Ergebnis wird verhindert.
8. OCR-Ausblick: nutzerfreundlicher Text und „Bald verfügbar“ sichtbar, aber kein Datei-Input, Upload
   oder Klickverhalten.
9. Desktop/Laptop, Tastatur und Screenreader bei 1280, 1440 und 1920 Pixel prüfen: kein horizontaler
   Seitenscroll im Standardzoom, korrekte Fokusreihenfolge, Status ohne Farbwahrnehmung verständlich.
10. Typprüfung, Lint, Web-/API-/DB-/Engine-Tests und RLS-Gates bleiben grün; bestehende Heizkosten-
    Goldenwerte unverändert.

## Reihenfolge

1. [Z4], [Z6], [Z9] — Datenverträge, Lifecycle und neutrale Eichdatenzustände.
2. [Z1], [Z2], [Z3] — Seitenarchitektur, Bestandsbaum und Warnsprung.
3. [Z5], [Z7], [Z8] — Wizard, Ablesung und Verbrauchsprojektion.
4. [Z10] — Fernablesbarkeit als ehrliches Stammdatum/Vision.
5. [Z11], [Z12], [Z13] — externe Abrechnung, OCR-Ausblick und prüfbare Heizkosteninputs.
6. [Z14], [Z15], [Z16] — Zustände, Desktop-Accessibility und vollständige Verifikation.

## Build-Notes (füllt die KI beim Umsetzen aus)

<!-- Annahmen, Abweichungen und übersprungene MUSS-INPUT-Teile hier eintragen. Erwartet insbesondere:
- [Z4] Ergebnis der migrationssicheren Zuordnung bestehender HEAT-Geräte.
- [Z9] Freigegebener Eichfrist-Regelstand oder übersprungene Wächterberechnung.
- [Z11] Exakte Ablage und Versionierung des externen Abrechnungsmodus.
- [Z12] Bestätigung, dass weder Datei-Input noch Upload/OCR-Aufruf gebaut wurde.
- [Z10] Bestätigung, dass keine Funk-Verbindungsoberfläche vorgetäuscht wurde.
-->
