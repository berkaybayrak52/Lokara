---
spec_id: 08-einheiten-dashboard
titel: Einheiten-Dashboard — kompakte Einheitenakte, Mietverhältnis, Zahlungen und Kommunikation
status: freigegeben
prioritaet: hoch
betrifft: apps/web, apps/api, packages/db
abhaengig_von: [00-layout-global, 02-objekte, 05-abrechnung-erstellen, 06-zahlungen, 07-objekt-dashboard]
repo_stand: Lokara-main @ 2026-08-25
---

## Zweck

Die heutige technische Mietverhältnis-Seite wird zu einer kompakten Einheitenakte. Sie zeigt
Stammdaten, das aktuelle Mietverhältnis, dokumentierte Vertragsfakten, den autoritativen Zahlungsstand
und – nur bei tatsächlich vorhandenen Produktpfaden – Mieterportal, Nachrichten und Dokumente. Die
Einheitenakte bleibt bewusst schmaler als das Objekt-Dashboard und erzeugt keine zweite fachliche
Wahrheit.

## Invarianten

- Pre-Pitch gilt Desktop/Laptop bei 1280, 1440 und 1920 Pixel sowie 200-Prozent-Zoom. Smartphone-,
  Tablet- und native Varianten sind Post-Pitch; Tastatur, Screenreader und sichtbarer Fokus bleiben
  verpflichtend.

- Nur das aktuelle Lokara-Designsystem aus `00_Layout-Global.md` verwenden: vorhandene Farb-, Status-,
  Typografie-, Abstands-, Fokus- und Komponenten-Tokens; keine rohen Farbwerte, keine alte
  Navy-/Teal-/Cream-/Poppins-Sprache und keine Immocloud-Gestaltung kopieren.
- Die Einheitenakte ist der Drill-down genau einer Einheit. Objekt-KPIs, vollständige Fachhistorien
  und Objektmodule aus `07_Objekt-Dashboard.md` nicht duplizieren.
- Alle Geldbeträge bleiben ganzzahlig in Cent beziehungsweise `Decimal`. Das Frontend summiert,
  dividiert, klassifiziert und priorisiert keine Miet-, Zahlungs-, Saldo- oder Abrechnungswerte.
- Kaltmiete je Quadratmeter kommt als fertige Backend-Projektion aus der zum Stichtag gültigen
  Kaltmiete und der erfassten Fläche. Sie wird nicht als zweite Wahrheit gespeichert und nicht im
  Browser berechnet.
- Aktuelle Nutzung, Vertragsstand, Mietparteien, Vorauszahlungsperiode, Zahlungsstatus und Saldo werden
  zu einem gemeinsamen serverseitigen `asOf` bestimmt; im Demo-Modus gilt der explizite
  `demo_now`/`demo_today`, nicht die Browseruhr.
- Vermietet, Leerstand, Eigennutzung und unentgeltliche Überlassung sind unterschiedliche zeitliche
  Zustände. Ein fehlendes aktuelles Mietverhältnis bedeutet nicht automatisch Leerstand.
- Mehrere Mietparteien innerhalb eines Mietverhältnisses bleiben getrennte Personen und
  Portalberechtigungen. Nie still nur die erste Partei verwenden.
- Lokara zeigt bei Mieterhöhungen ausschließlich dokumentierte Vertragsfakten. Lokara bewertet
  **niemals** die rechtliche Zulässigkeit, berechnet keinen frühesten zulässigen Termin und gibt keine
  Empfehlung zur Mieterhöhung ab.
- Zahlungsstand, Teilzahlung, Guthaben, ungeklärte Überzahlung, Nachzahlung und offene Forderung kommen
  aus den autoritativen Forderungs-/Ledger-/Allokationsprojektionen aus `06_Zahlungen.md`. Ein
  Bankumsatz ist ohne fachliche Verbuchung keine Zahlung auf eine Mietforderung.
- Abrechnungssalden und Dokumente finalisierter Abrechnungen werden aus den bestehenden unveränderlichen
  Archiven konsumiert und nicht kopiert oder neu berechnet.
- Mieterportal, Nachrichten, allgemeine Dokumente, Upload und Versand nur als funktionsfähig zeigen,
  wenn Datenmodell, Persistenz, Berechtigungen, Adapter und Tests tatsächlich vorhanden sind.
  Andernfalls kompakt und eindeutig inaktiv kennzeichnen oder vollständig auslassen.
- Das bisher dauerhaft sichtbare Mietverhältnis-Anlageformular wird durch eine kontextabhängige Aktion
  ersetzt. Stammdaten- und Vertragsbearbeitung nicht in viele Inline-Formulare über die Akte verteilen.
- Bestehende Account-, Gebäude- und Einheitenautorisierung, Rollenregeln, RLS, FK-, Append-only- und
  Unveränderlichkeitsregeln nicht abschwächen. UI-Gating ersetzt keine Serverprüfung.
- Signal nie allein durch Farbe vermitteln. Die vollständige Kernaufgabe muss per Tastatur, bei
  200 Prozent Zoom und auf den Pre-Pitch-Breiten 1280, 1440 und 1920 Pixel bedienbar bleiben.
  Smartphone-/Tablet-Varianten sind Post-Pitch.
- Keine neue Rechen-, Rechts-, Forderungs-, Zahlungs-, Mahn-, Abrechnungs- oder Zählerlogik einführen,
  sofern ein Befehl sie nicht ausdrücklich als reine Projektion vorhandener Wahrheiten benennt.
- Nur die im jeweiligen Befehl genannten Dateien und Stellen ändern. Bestehende Tests, Typprüfung,
  Lint, RLS-/FK-Gates und fachliche Golden-Fixtures bleiben grün.
- Bei normaler Unklarheit den genannten Default verwenden und in `## Build-Notes` dokumentieren.
  `⚠️ MUSS-INPUT` nie raten; nur den betroffenen Teil überspringen, den Rest weiter umsetzen.

## Befehle

### [ED1] Gebrochenen Einheitenvertrag zuerst konsistent reparieren

- **Datei/Ort:** `apps/web/src/lib/contracts.ts`,
  `apps/web/src/features/objekte/unit-detail-page.tsx`,
  `apps/web/src/features/objekte/queries.ts`, vorhandene Vertrags-/Render-Tests sowie nur bei einer
  tatsächlich notwendigen kompatiblen Ergänzung `apps/api/src/lokara_api/schemas.py` und
  `apps/api/src/lokara_api/routers/buildings.py`.
- **Fundstelle:** `TenancyOutSchema` erwartet heute `advancePaymentCents` und
  `advancePaymentEur`; `_tenancy_out` liefert inzwischen `advancePaymentSchedule`. Das Formular sendet
  noch `advancePaymentCents`, während `TenancyCreate` `initialAdvancePaymentCents` und
  `advanceDeclarationRef` verlangt.
- **Ist:** Frontend und Backend sind jeweils typintern konsistent, aber auf dem Draht inkompatibel. Der
  lokale TypeScript-Check bleibt deshalb grün, während die Seite beim Laden an der Zod-Grenze mit
  „Fehler beim Laden“ scheitern kann. Die aktuelle Demo-Aufnahme zeigt genau diesen Zustand.
- **Soll:** Den Frontend-Vertrag und alle Konsumenten auf den aktuellen versionierten
  Vorauszahlungsplan umstellen. Die Anlage sendet die aktuelle API-Payload einschließlich
  Nachweis-/Erklärungsreferenz. Eine einzelne angezeigte „aktuelle Vorauszahlung“ wird anhand des
  gemeinsamen `asOf` serverseitig projiziert; historische Schedule-Zeilen bleiben für die
  Vertragsdetails erhalten.
- **Default:** Der bestehende Backendvertrag mit `advancePaymentSchedule` bleibt maßgeblich.
  Deklarationsreferenz ist im Anlagefluss ein Pflichtfeld mit Label „Grundlage der Vorauszahlung“ und
  Beispielhinweis „Mietvertrag vom TT.MM.JJJJ“; kein erfundener Standardtext wird gespeichert.
- **Erwartetes Ergebnis:** Der Demo-Pfad einer gesäten Einheit lädt ohne generischen Fehler. Aktuelle
  und historische Vorauszahlungsperioden sind unterscheidbar. Das Erstellen eines Mietverhältnisses
  erzeugt genau die erwartete initiale Schedule-Zeile und invalidiert Einheit, Objektakte und
  Portfolioübersicht gezielt.
- **Akzeptanz:** Ein Contract-Test validiert die reale API-Antwort gegen das Frontendschema. Ein
  Integrationstest liest eine Einheit mit mindestens zwei Vorauszahlungsperioden. Laden und Anlage
  funktionieren; Typprüfung und API-Tests sind grün.
- **Nicht tun:** Backend auf den alten Einzelbetrag zurückbauen; Schedule-Zeilen im Frontend
  zusammenfassen oder überschreiben; einen Betrag anhand des neuesten Array-Elements ohne
  Stichtagsprüfung wählen; Golden-Beträge ändern.

### [ED2] Ein serverseitiges Read Model für die kompakte Einheitenakte schaffen

- **Datei/Ort:** Neuer klar benannter Read-Service und GET-Endpoint unter `apps/api`, Antwortschema in
  `apps/api/src/lokara_api/schemas.py`, Frontendvertrag in `apps/web/src/lib/contracts.ts` und Hook in
  `apps/web/src/features/objekte/queries.ts`.
- **Fundstelle:** Der heutige GET `/a/{account_id}/units/{unit_id}` liefert nur Einheit, Objekt,
  Mietverhältnisse und Eigennutzungsperioden. Geld-, Portal-, Nachrichten-, Dokument- und
  Ausstattungsdaten besitzen keinen gemeinsamen Einheitenvertrag.
- **Ist:** Zusätzliche Module müssten mehrere objekt- und kontogescopte Endpoints laden und Werte im
  Browser zusammensetzen. Dadurch drohen unterschiedliche Stichtage, N+1-Abfragen und eine zweite
  Saldenwahrheit.
- **Soll:** Einen kompakten, autorisierten Einheitenakten-Vertrag bereitstellen. Er enthält
  `asOf`, Stammdaten, aktuellen Nutzungszustand, aktuelle Parteien, aktuelles Mietverhältnis,
  dokumentierte Vertragsfakten, fertig projizierte Geldfakten, erlaubte Aktionen und kompakte
  Modulzusammenfassungen. Nicht vorhandene Fachmodule werden über explizite Verfügbarkeit und nicht
  über erfundene Nullwerte dargestellt.
- **Default:** Einen dedizierten Pfad wie `/a/{account_id}/units/{unit_id}/dashboard` verwenden und
  den bestehenden CRUD-Detailendpoint kompatibel erhalten. Kern und optionale Module im Vertrag
  trennen, damit ein Teilfehler von Nachrichten oder Dokumenten nicht die Einheit, den Vertrag und
  den Zahlungsstand entfernt. Historien bleiben in paginierten Fachendpoints.
- **Erwartetes Ergebnis:** Ein Request liefert alle oberhalb des ersten Seitenumbruchs benötigten
  Fakten mit einem konsistenten Datenstand. Jede Geldzahl und jeder Status besitzt eine autoritative
  Quelle. Ein optional nicht verfügbares Modul ist im Vertrag als nicht verfügbar erkennbar.
- **Akzeptanz:** API-Tests decken 404 statt Datenleck, Rollen, mehrere Parteien, Leerstand,
  Eigennutzung, Zukunftsvertrag, fehlende Fläche, Teilfehler und gemeinsamen `asOf` ab. Das Frontend
  aggregiert keine Fachrohdaten.
- **Nicht tun:** Vollständige Ledger-, Nachrichten-, Dokument-, Abrechnungs- oder Mietverlaufshistorien
  in den Startpayload laden; fremde Ressourcen aus einer Client-ID verknüpfen; einen Cache als
  dauerhafte Wahrheit behandeln.

### [ED3] Fehlende Einheiten- und Vertragsstammdaten versionierbar ergänzen

- **Datei/Ort:** `packages/db/src/lokara_db/models.py`, neue Alembic-Migration, API-Schemas/-Router,
  Einheitenbearbeitung aus `02_Objekte.md`, Seed und Tests.
- **Fundstelle:** `Unit` besitzt aktuell nur Bezeichnung und Fläche. `Tenancy` besitzt Zeitraum und
  Kaltmiete; Zimmer, Nutzungsart, Ausstattung, Garage/Stellplatz, Vertragsart und dokumentierte
  Mietänderungen fehlen.
- **Ist:** Die gewünschten Eckdaten könnten nur aus Namen geraten, im Frontend hartcodiert oder als
  unstrukturierter Text gespeichert werden. Historische Mietänderungen wären nicht nachvollziehbar.
- **Soll:** Die für die Einheitenakte benötigten strukturierten Fakten ergänzen. Einheit und Vertrag
  fachlich trennen: Zimmer, Nutzungsart und Ausstattung gehören zur Einheit; Vertragsart,
  einbezogene beziehungsweise separat ausgewiesene Garage/Stellplätze und dokumentierte
  Mietänderungen gehören zum Mietverhältnis beziehungsweise zu versionierten Vertragsperioden.
- **Default:** Nutzungsart `RESIDENTIAL | COMMERCIAL | OTHER`; Zimmer als nichtnegative Dezimalzahl in
  fester Darstellung und bei Gewerbe optional; Ausstattung als begrenzte, servervalidierte
  Merkmalsauswahl plus optionaler sachlicher Freitext; Stellplatz/Garage als eigene verknüpfte
  Vertragsposition mit Typ und Einbindungsart `INCLUDED | SEPARATE`, nicht als Boolean. Vertragsart
  mindestens `RESIDENTIAL_OPEN_ENDED | RESIDENTIAL_FIXED_TERM | COMMERCIAL_OPEN_ENDED |
  COMMERCIAL_FIXED_TERM | OTHER`; unbekannte Bestandsdaten bleiben `null`/„Nicht erfasst“.
  Mietänderungen werden append-only mit Wirksamkeitsdatum, neuem Kaltmietbetrag und Dokument-/
  Nachweisreferenz gespeichert. Das Feld heißt nutzerseitig „Letzte dokumentierte Mietänderung“.
- **Erwartetes Ergebnis:** Die Einheitenakte kann alle gewünschten Eckdaten aus persistierten,
  accountgescopten Fakten anzeigen. Frühere Mietbeträge und Änderungen bleiben nachvollziehbar.
  Bestandsdatensätze werden nicht mit geratenen Defaults rückwirkend klassifiziert.
- **Akzeptanz:** Migration und API-Tests decken Null-Bestand, Wohnen, Gewerbe, halbe Zimmer,
  mehrere Ausstattungen, separate und eingebundene Stellplätze sowie mindestens zwei
  Mietänderungsperioden ab. Frontendsuche findet keine Klassifikation anhand von Einheitennamen.
- **Nicht tun:** Garage in die Kaltmiete einrechnen; Ausstattungsbegriffe frei aus Dokumenten oder
  Einheitennamen ableiten; Mietänderungen per UPDATE überschreiben; aus Vertragsart eine rechtliche
  Aussage ableiten.

### [ED4] Einheitenkopf und Eckdaten kompakt gestalten

- **Datei/Ort:** `apps/web/src/features/objekte/unit-detail-page.tsx` und bei sinnvoller Aufteilung
  neue präsentationsbezogene Dateien im selben Featureordner.
- **Fundstelle:** Heutiger Kopf mit Breadcrumb, Einheitenlabel, Fläche und Objektname; darunter das
  `2fr_1fr`-Raster aus Historie und dauerhaftem Anlageformular.
- **Ist:** Die Seite beantwortet nicht klar, welcher Zustand heute gilt. Zimmer, Nutzung,
  Kaltmiete/m², Ausstattung und Stellplatz fehlen. Technische CRUD-Erklärungen dominieren.
- **Soll:** Den bestehenden Breadcrumb erhalten und direkt zum Objekt-Dashboard zurückführen. Darunter
  einen ruhigen Einheitenkopf mit Bezeichnung, vollständiger Objektadresse, aktuellem Zustand und
  Datenstand anzeigen. Es folgt genau eine breite Eckdatenkarte mit den Bereichen „Eckdaten“ und –
  nur bei vorhandenen Daten – „Ausstattung“.
- **Default:** Eckdaten in dieser Reihenfolge: Fläche, Zimmer, Nutzungsart, aktuelle Kaltmiete,
  Kaltmiete/m² und Garage/Stellplatz. Werte fehlen ehrlich als „Nicht erfasst“ beziehungsweise „–“;
  ein berechtigter Owner erhält die sekundäre Aktion „Eckdaten ergänzen“. Ausstattung zeigt
  vorhandene Merkmale als ruhige Text-/Iconliste. Ohne Merkmale keine große leere Hälfte, sondern
  eine kompakte Zeile mit „Ausstattung noch nicht erfasst“ und Owner-Aktion.
- **Erwartetes Ergebnis:** Die Einheit ist ohne Scrollen identifizierbar. Eckdaten wirken wie eine
  kompakte Akte, nicht wie sechs dekorative KPI-Karten. Gewerbeeinheiten zeigen bei Zimmern „–“ und
  werden nicht wie Wohnungen beschriftet.
- **Akzeptanz:** 1280, 1440 und 1920 Pixel sowie 200 Prozent Zoom zeigen dieselben Fakten ohne
  horizontalen Seitenscroll im Standardzoom. Alle Werte entsprechen exakt der Backendantwort.
- **Nicht tun:** Immocloud-Seitennavigation, Farben oder Pixelaufteilung kopieren; Objekt-KPIs
  wiederholen; eine zusätzliche Einheitensidebar bauen; fehlende Werte aus Freitext raten.

### [ED5] Aktionen nach Zustand und Berechtigung anbieten

- **Datei/Ort:** Einheitenkopf, bestehender Mietverhältnis-Anlagefluss, neue/erweiterte Aktionsflags im
  Read Model und serverseitige Owner-/Employee-Prüfung.
- **Fundstelle:** Das heutige Anlageformular steht ständig rechts und ist nicht zuverlässig nach
  Rolle und aktuellem Vertragszustand begrenzt.
- **Ist:** Der Formularblock verdrängt die eigentliche Akte. Nutzer sehen auch dann „Mietverhältnis
  anlegen“, wenn zuerst ein Wechsel, ein Ende oder eine Stammdatenkorrektur nötig wäre.
- **Soll:** Das Dauerformular entfernen und Aktionen in den Kopf beziehungsweise das aktuelle
  Mietverhältnis verlagern. Der Server liefert die tatsächlich erlaubten Aktionen; das Frontend zeigt
  nur diese und prüft Schreibrechte nicht selbst nach.
- **Default:** Primäre Aktion nach Zustand: ohne aktuelles oder zukünftiges Mietverhältnis
  „Mietverhältnis anlegen“; bei aktivem Mietverhältnis „Mietverhältnis öffnen“; bei dokumentiertem
  bevorstehendem Ende „Wechsel vorbereiten“. Sekundär „Einheit bearbeiten“. Mieterportalaktion folgt
  [ED9]. Das Anlageformular öffnet als fokussierter Wizard/Dialog oder eigene Route und verwendet den
  bestehenden Entwurfsmechanismus.
- **Erwartetes Ergebnis:** Die Seite bleibt schmal und lesbar. Keine Aktion wird nur per CSS verborgen;
  ein direkter nicht erlaubter Request wird serverseitig abgewiesen.
- **Akzeptanz:** Rollen- und Zustandsmatrix ist in API- und Frontendtests abgedeckt. Dialogschluss oder
  Rücknavigation setzt den Fokus zur auslösenden Aktion zurück; erfolgreicher Abschluss aktualisiert
  die Akte.
- **Nicht tun:** Bestehende M5-Rechte erweitern; Employee-Rechte raten; destruktives Löschen eines
  Mietverhältnisses anbieten; mehrere vollständige Formulare gleichzeitig rendern.

### [ED6] Aktuelles Mietverhältnis vor der Historie zeigen

- **Datei/Ort:** Hauptbereich der Einheitenakte und Projektion des aktuellen Mietverhältnisses.
- **Fundstelle:** Die heutige Seite beginnt mit Zeitstrahl und Tabelle aller Mietverhältnisse; der
  aktuell gültige Vertrag besitzt keine hervorgehobene Zusammenfassung.
- **Ist:** Nutzer müssen aus historischen Zeilen selbst erkennen, wer heute Vertragspartner ist und
  welche Werte gelten.
- **Soll:** Eine Karte „Aktuelles Mietverhältnis“ vor der Historie anzeigen. Sie enthält alle aktuellen
  Mietparteien, Vertragsbeginn, bei Befristung das dokumentierte Vertragsende, Vertragsart,
  Kaltmiete, aktuelle Vorauszahlungen, monatliches Gesamtmietsoll und vertraglich zugeordnete
  Garage/Stellplätze. Darunter ausschließlich dokumentierte Mietänderungsfakten.
- **Default:** Parteien untereinander mit vollständigem Namen. Zeitraum in nutzerverständlichen
  inklusiven Daten; die technische exklusive `validTo`-Grenze nicht als Auszugstag ausgeben. Bei
  offenem Ende „unbefristet“. Mietänderung: „Letzte dokumentierte Mietänderung: TT.MM.JJJJ“ plus
  neuer Betrag; fehlt sie, „Keine Mietänderung erfasst“. Keine nächste Erhöhungsmöglichkeit anzeigen.
- **Erwartetes Ergebnis:** Der aktuelle Vertragsstand ist ohne Interpretation verständlich. Bei
  Leerstand/Eigennutzung ersetzt ein passender neutraler Zustand die Vertragskarte und bietet nur
  erlaubte Aktionen.
- **Akzeptanz:** Tests decken mehrere Parteien, befristet/unbefristet, Zukunftsvertrag, Leerstand,
  Eigennutzung, Stellplatz, mehrere Vorauszahlungs- und Mietänderungsperioden ab.
- **Nicht tun:** Vertragsende direkt aus dem exklusiven Enddatum als letzten Nutzungstag ausgeben;
  mehrere Parteien zusammenfassen; Gesamtmietsoll im Browser addieren; aus Vertragsart oder
  Änderungshistorie eine rechtliche Bewertung erzeugen.

### [ED7] Miet- und Nutzungshistorie verständlich einklappen

- **Datei/Ort:** `apps/web/src/features/objekte/tenancy-timeline.tsx`,
  `tenancy-timeline.test.ts` und Historienbereich der Einheitenseite.
- **Fundstelle:** Der vorhandene Zeitstrahl berechnet sein Fenster mit `Date.now()`, zeichnet
  Leerstandslücken im Browser und erklärt technische halboffene Zeiträume im Nutzertext.
- **Ist:** Der Zeitstrahl ist fachlich wertvoll, verwendet aber einen anderen Stichtag als eine
  dynamische Demo und zeigt technische Sprache. Lange Historien wachsen vollständig in die Seite.
- **Soll:** Den Zeitstrahl als eingeklappten Bereich „Miet- und Nutzungshistorie“ erhalten. Segmente und
  zugängliche Textdarstellung kommen aus einer serverseitigen Zeitabschnittsprojektion mit gemeinsamem
  `asOf`. Vergangene, aktuelle und zukünftige Mietverhältnisse, Leerstand, Eigennutzung und
  unentgeltliche Überlassung bleiben getrennte Segmente.
- **Default:** Aktuelles Mietverhältnis bleibt außerhalb immer sichtbar. Historie initial eingeklappt,
  zeigt im geschlossenen Zustand Anzahl und ältesten erfassten Beginn. Beim Öffnen neueste Abschnitte
  zuerst als Text, ergänzend ein visueller Zeitstrahl. Technische Wörter `validFrom`, `validTo`,
  „halboffen“ und „exkl.“ erscheinen nicht im Nutzertext. Mehr als zehn Abschnitte serverseitig
  paginieren oder über „Weitere laden“ nachladen.
- **Erwartetes Ergebnis:** Mieterwechsel und Leerstandslücken bleiben nachvollziehbar, ohne die
  kompakte Einheitenakte zu dominieren. Screenreader erhalten dieselben Zeitabschnitte wie die Grafik.
- **Akzeptanz:** Tests decken den Runbook-Wechsel in Wohnung B, einen Leerstandsmonat, Eigennutzung,
  zukünftigen Vertrag, lange Historie und Demo-Stichtag ab.
- **Nicht tun:** Leerstand allein im Browser aus fehlenden Zeilen als aktuellen Status klassifizieren;
  historische Zahlungen einer neuen Partei zuordnen; eine unendliche Zeitleiste vollständig laden.

### [ED8] Zahlungsstrom und Saldo als kompakten Ausschnitt anbinden

- **Datei/Ort:** Einheitenakten-Projektion, autoritative Read Models aus `06_Zahlungen.md` [P13],
  [P14], [P16], kompakte Webkomponente und gefilterter Drill-down zur Zahlungsseite.
- **Fundstelle:** Auf der heutigen Einheitenseite existieren keine Forderungen, Zahlungen oder Salden.
  Die Zahlungsseite besitzt eigene Bank-, Matching- und Ledgerpfade.
- **Ist:** Ein Vermieter kann nicht sehen, ob die aktuelle Miete bezahlt, teilweise bezahlt, offen oder
  ungeklärt ist. Eine lokale Zusammenrechnung würde Forderung, Bankumsatz und Guthaben vermischen.
- **Soll:** Unterhalb der Vertragshistorie einen Bereich „Zahlungen“ anzeigen. Kopfwerte: aktueller
  autoritativer Gesamtsaldo, Mietsoll des laufenden Monats, fachlich verbucht, verbleibend offen und
  getrennt vorhandenes Guthaben beziehungsweise ungeklärte Abweichung. Darunter höchstens die letzten
  sechs Forderungsperioden und relevante Betriebskosten-Nachzahlungen.
- **Default:** Statuswerte `Bezahlt`, `Teilweise bezahlt`, `Offen` und `Prüfen`, jeweils Text plus
  Statustoken. Teilzahlung zeigt „X,XX € von Y,YY € bezahlt · Z,ZZ € offen“. Ungeklärte Überzahlung
  erscheint getrennt als „X,XX € bitte prüfen“, nicht als Guthaben oder Einnahme. Positive
  Abrechnungsguthaben erscheinen als Verpflichtungs-/Saldo-Hinweis, nicht als negative Forderung.
  Aktion „Alle Zahlungen anzeigen“ öffnet die Zahlungsseite mit autorisiertem Einheiten-/
  Mietverhältnisfilter.
- **Erwartetes Ergebnis:** Jonas zeigt 600,00 Euro verbucht und 500,00 Euro offen; Maria zeigt die
  ungeklärte Abweichung getrennt; Sophie zeigt eine offene Forderung ohne erfundenen Bankumsatz; Anna
  zeigt 125,00 Euro offene Betriebskosten-Nachzahlung. Änderungen auf der Zahlungsseite aktualisieren
  dieselbe Einheitenprojektion.
- **Akzeptanz:** Contract-Tests beweisen identische Forderungs-ID und identischen offenen Centbetrag in
  Zahlung, Objektakte, Einheit und Dashboard. Serverseitige Pagination verhindert das Laden der
  vollständigen Historie.
- **Nicht tun:** Bankumsätze im Browser summieren; „Alle Mieten als bezahlt markieren“ anbieten;
  ungeklärte Überzahlung automatisch als Guthaben buchen; Guthaben automatisch verrechnen; Mahnstufe,
  Verzug, Zinsen oder Gebühren anzeigen.
- **⚠️ MUSS-INPUT:** Verbindliche Erzeugungs- und Fälligkeitsregeln für regelmäßige Mietforderungen
  sowie Behandlung gemeinsamer Mietverhältnisse aus `06_Zahlungen.md`. Fehlen sie beim Bau, keine
  Forderungen neu erzeugen; ausschließlich bereits autoritativ vorhandene Forderungs-/Ledgerwerte
  anzeigen und die Einschränkung in Build-Notes festhalten.

### [ED9] Mieterportalzugriff pro Mietpartei vorbereiten und ehrlich begrenzen

- **Datei/Ort:** Einheitenkopf/aktuelle Mietparteien, neues Portalberechtigungsmodell und Owner-API nur
  bei freigegebener Implementierung, Benachrichtigungsadapter, Audit-/Sicherheits- und UI-Tests.
- **Fundstelle:** Gewünschte Aktion „Mieterportal einrichten“; im aktuellen Repo existiert kein
  vollständiges Mieterportal und kein belastbarer Einladungs-/Zugriffsvertrag.
- **Ist:** Ein sofort aktiver Button würde eine Zustellung oder Berechtigung vortäuschen. Bei mehreren
  Mietparteien wäre „dieser Person“ mehrdeutig.
- **Soll:** Portalzugriff immer einer konkreten Mietpartei innerhalb eines konkreten Mietverhältnisses
  zuordnen. Zustände und Aktionen pro Partei anzeigen. Eine Einladung erstellt eine idempotente,
  widerrufbare Berechtigung; Versand und Zustellung bleiben getrennte Zustände.
- **Default:** Zustände `NOT_INVITED | INVITATION_PENDING | ACTIVE | REVOKED | DELIVERY_FAILED`.
  Aktionen: „Mieterportal einrichten“, „Einladung erneut senden“ oder „Portalzugriff verwalten“.
  Bei mehreren Parteien öffnet die Aktion eine Auswahl mit Name und Zieladresse; nichts ist
  vorausgewählt. Erneutes Senden erzeugt keine zweite aktive Berechtigung. Ohne echten Adapter bleibt
  die Aktion inaktiv mit „Mieterportal kommt später“; im Demo-Modus darf eine persistierte
  Demo-Einladung als solche gekennzeichnet werden, aber keine E-Mail-Zustellung behaupten.
- **Erwartetes Ergebnis:** Nutzer erkennen für jede Mietpartei, ob Zugang besteht. Zugriff endet nicht
  still allein durch eine UI-Änderung; Entzug und Vertragsende werden serverseitig und auditierbar
  verarbeitet.
- **Akzeptanz:** Tests decken mehrere Parteien, doppelten Submit, erneutes Senden, Widerruf,
  Vertragsende, fremde Einheit, Employee-Verbot und Adapterfehler ab. Keine vollständige E-Mail-Adresse
  erscheint in Logs oder allgemeinen Listen.
- **Nicht tun:** Portalzugang allein an Unit oder Renter ohne Mietverhältnisbezug hängen; erste Partei
  automatisch wählen; Einladung als zugestellt markieren; Mieterportal-UI in diesem Spec bauen.
- **⚠️ MUSS-INPUT:** Freigegebener Identitäts-, Einladungs-, Zustell-, Widerrufs- und
  Datenschutzprozess sowie konkrete Portalrechte der Mietpartei. Fehlt dieser Input, nur den ehrlichen
  inaktiven Zustand umsetzen.

### [ED10] Nachrichtenmodul nur an einen echten Nachrichtenpfad anbinden

- **Datei/Ort:** Unterer Bereich der Einheitenakte; Nachrichtenmodelle, API, Berechtigungen und
  Versand-/Portalpfad erst bei tatsächlicher Implementierung.
- **Fundstelle:** Gewünschtes Widget mit vorhandenen Nachrichten oder der Aktion „Nachricht schreiben“;
  derzeit existiert kein Nachrichtenportal im Repo.
- **Ist:** Eine leere Karte oder ein aktiver Button würde Funktionalität vortäuschen und die schmale
  Seite unnötig verlängern.
- **Soll:** Bei vorhandenem Modul höchstens die drei neuesten einheiten-/mietverhältnisbezogenen
  Konversationen zeigen: Partei, Betreff/Vorschau, Zeitpunkt und ungelesener Status. Danach „Alle
  Nachrichten“. Ohne Konversation „Noch keine Nachrichten“ und „Nachricht schreiben“.
- **Default:** Das Widget erscheint nur bei echter Persistenz und Berechtigung. „Nachricht schreiben“
  ist nur aktiv, wenn mindestens eine erlaubte Empfängerpartei und ein echter Speicher-/Versandpfad
  vorhanden sind. Ohne Modul eine kompakte inaktive Zeile „Nachrichtenportal kommt später“ oder den
  Bereich vollständig auslassen; keine große Leerkarte.
- **Erwartetes Ergebnis:** Nachrichten sind dem konkreten Mietverhältnis zugeordnet und enthalten keine
  fremden Parteien. Teilfehler im Nachrichtenmodul blockieren Eckdaten, Vertrag und Zahlungen nicht.
- **Akzeptanz:** Tests decken keine Nachrichten, ungelesene Nachricht, mehrere Parteien, Pagination,
  fremdes Mietverhältnis, Versandfehler und inaktiven Zukunftszustand ab.
- **Nicht tun:** Nachrichten aus Browserzustand, Notizen oder Auditlogs erzeugen; E-Mail als Nachricht
  ausgeben, solange kein Import existiert; einen Klick ohne Persistenz als gesendet anzeigen.
- **⚠️ MUSS-INPUT:** Kanal, Empfänger-/Absenderidentität, Zustellstatus, Aufbewahrung, Löschung,
  Moderation und Benachrichtigungsregeln. Ohne diese Inputs kein produktives Nachrichtenmodul bauen.

### [ED11] Dokumente kompakt und ohne zweiten Archivbestand zeigen

- **Datei/Ort:** Unterer Bereich der Einheitenakte, bestehende finalisierte Dokumentendpoints sowie
  ein allgemeines Storage-/Metadatenmodell nur bei freigegebener Implementierung.
- **Fundstelle:** Gewünschter Dokumentbereich; vorhanden sind finalisierte Abrechnungsdokumente, aber
  kein allgemeiner Einheiten-Dokumentenraum.
- **Ist:** Mietvertrag, Nachtrag und Übergabeprotokoll können nicht belastbar gespeichert werden.
  Ein neuer lokaler Mockbestand würde mit dem Abrechnungsarchiv kollidieren.
- **Soll:** Einen kompakten Dokumentausschnitt mit höchstens fünf neuesten Dokumenten anzeigen. Jedes
  Dokument besitzt Dokumentart, Dateiname, Mietverhältnisbezug, Erstellzeitpunkt, Größe und
  Portal-Sichtbarkeit. Finalisierte Abrechnungsdokumente werden über ihr bestehendes Archiv referenziert
  und nicht kopiert. „Alle Dokumente“ führt später in einen paginierten Dokumentenraum.
- **Default:** Dokumentarten mindestens Mietvertrag, Nachtrag, dokumentierte Mietänderung,
  Übergabeprotokoll, Abrechnung und Sonstiges. Ohne allgemeinen Storage nur vorhandene echte
  Abrechnungsdokumente zeigen; „Dokument hinzufügen“ inaktiv mit „Dokumentenablage kommt später“ oder
  auslassen. Öffnen/Download nur mit echtem autorisiertem Bytepfad.
- **Erwartetes Ergebnis:** Die Einheitenakte zeigt vorhandene Nachweise ohne Duplikate oder tote
  Aktionen. Dokumentfehler beeinflussen den Zahlungs- oder Vertragsstatus nicht.
- **Akzeptanz:** Tests beweisen Account-/Einheiten-/Mietverhältnisgrenzen, Portal-Sichtbarkeit,
  Pagination, fehlenden Storage, unveränderte Archivbytes und keine doppelten Abrechnungsdokumente.
- **Nicht tun:** Dateien in localStorage/base64 im Fachdatensatz ablegen; Dokumentnamen hartcodieren;
  Upload, Download, Löschen oder Virenprüfung vortäuschen; finale Archive editieren.
- **⚠️ MUSS-INPUT:** Storage-Anbieter, Dateirechte, Formate, Größenlimit, Virenprüfung, Aufbewahrung,
  Löschung, Versionierung und Sichtbarkeit im Mieterportal. Ohne diese Inputs keinen allgemeinen
  Uploadpfad aktivieren.

### [ED12] Lade-, Leer-, Fehler-, Erfolg- und Teilfehlerzustände ausarbeiten

- **Datei/Ort:** Gesamte Einheitenakte und ihre optionalen Module.
- **Fundstelle:** Heute ein einzelner großer Mint-Skeleton und generische Fehleranzeige
  „Fehler beim Laden“ mit Rücksprung zur Objektliste.
- **Ist:** Der aktuelle Vertragsfehler ist nicht diagnostizierbar; Nutzer verlieren zudem den direkten
  Rückweg zum zugehörigen Objekt. Ein späterer Modulfehler könnte die ganze Akte entfernen.
- **Soll:** Strukturgetreuen Ladezustand für Kopf, Eckdaten und Vertrag verwenden. 404 zeigt „Einheit
  nicht gefunden“ mit Rückkehr zu „Objekte“. Allgemeiner Kernfehler zeigt „Einheit konnte nicht geladen
  werden“, „Erneut versuchen“ und den sicheren Objektrückweg, sofern bekannt. Optionale Module besitzen
  isolierte Fehler- und Retry-Zustände.
- **Default:** Einheit ohne Mietverhältnis zeigt neutral den tatsächlichen Zustand und genau eine
  erlaubte Aktion. Fehlende Eckdaten sind „Nicht erfasst“, nicht `0`. Erfolgreiche Änderungen melden
  sich kurz in einer zugänglichen Statusregion und aktualisieren die Backendantwort. Keine Hinweise auf
  API, Datenbank, Zod, HTTP-Code oder interne IDs.
- **Erwartetes Ergebnis:** Ein Nachrichten- oder Dokumentfehler lässt Einheitenkopf, Vertrag und
  Zahlungen stehen. Der heute sichtbare generische Fehler durch den Vertragsbruch ist nach [ED1]
  regressionsgeschützt.
- **Akzeptanz:** Tests decken Kern-Laden, 404, 500, Vertragsvalidierungsfehler, leere Einheit,
  Teilfehler, Retry und erfolgreiche Mutation ab. Fokus landet auf Statuskopf beziehungsweise erstem
  Fehler.
- **Nicht tun:** Bereits geladene Kerndaten bei Teilfehler entfernen; Stacktraces oder rohe
  Backendtexte zeigen; Endlos-Retry bauen; fehlende Daten als Nullbetrag darstellen.

### [ED13] Desktop-/Laptop-Nutzung, Tastatur und Fokus absichern

- **Datei/Ort:** Einheitenkopf, Eckdaten, aktuelles Mietverhältnis, Historie, Zahlungsabschnitt,
  Portalaktionen, Nachrichten und Dokumente sowie zugehörige Webtests.
- **Fundstelle:** Die heutige breite Mietverhältnis-Tabelle und das `2fr_1fr`-Raster besitzen keine
  verbindliche Laptopbreiten- und Fokusabnahme.
- **Ist:** Lange Namen, mehrere Parteien, Beträge und Aktionen können bei 1280 Pixel zusammengedrückt
  werden. Inline- und Dialogaktionen benötigen eine konsistente Fokusführung.
- **Soll:** Desktop und Laptop verwenden ruhige Karten und kompakte Tabellen. Jede Aktion ist per
  Tastatur erreichbar und besitzt sichtbaren Fokus. Dialoge/Drawer halten Fokus und geben ihn danach
  zum Auslöser zurück.
- **Default:** Seitenreihenfolge bleibt bei allen Pre-Pitch-Breiten stabil. Geld rechtsbündig und
  `tabular-nums`; lange Namen umbrechen. Einzelne Tabellen dürfen bei 200-Prozent-Zoom innerhalb ihrer
  Fläche kontrolliert scrollen. Bewegung 150–250 Millisekunden nur über Transform/Opacity und mit
  `prefers-reduced-motion`.
- **Erwartetes Ergebnis:** Einheit erkennen, Vertrag lesen, Zahlung prüfen, Portalstatus verstehen,
  Nachricht beziehungsweise Dokument öffnen funktioniert bei 1280, 1440 und 1920 Pixel,
  200 Prozent Zoom und ohne Maus.
- **Akzeptanz:** Desktopbreiten-, Tastatur- und Screenreadertests prüfen Überschriftenhierarchie,
  Fokusreihenfolge, Statuszusätze, Dialogrückkehr, reduzierte Bewegung und fehlenden horizontalen
  Seitenscroll.
- **Nicht tun:** Smartphone-/Tablet-Karten oder Touchnavigation Pre-Pitch bauen; Aktionen nur auf Hover
  zeigen; Fokusoutline entfernen; Status nur farblich codieren; neues Komponenten-/Iconpaket allein
  hierfür installieren.

### [ED14] Performance, Demo und vollständige Abnahme absichern

- **Datei/Ort:** Einheitenakten-Service/-Endpoint, Query-Keys und Invalidierung, API-/Web-/DB-Tests,
  Portfolio-Seed/-Reset und `DEMO-RUNBOOK-PORTFOLIO.md`.
- **Fundstelle:** Die heutige Detailantwort lädt ORM-Beziehungen direkt. Das Portfolio-Runbook enthält
  nun zusätzliche Zimmer-, Ausstattungs-, Stellplatz-, Vertrags-, Portal-, Nachrichten- und
  Dokumentzustände, die im aktuellen Einobjekt-Seed noch nicht persistiert sind.
- **Ist:** Lange Miet-, Zahlungs-, Nachrichten- und Dokumenthistorien könnten den Startpayload
  aufblähen. Die Demo-Zielwerte existieren im Runbook, aber nicht vollständig im Seed.
- **Soll:** Kerndaten set-basiert und ohne N+1 laden; Historien serverseitig paginieren. Query-Keys
  mindestens account- und unitgescopet führen. Nach Vertrags-, Stammdaten-, Zahlungs-, Portal-,
  Nachrichten- oder Dokumentaktion nur betroffene Projektionen invalidieren. Die Runbook-Zustände
  reproduzierbar und ohne Frontend-Sonderwerte seeden.
- **Default:** Kein Redis-Zwang; zuerst Abfragen und Indizes messen. Ziel nach lokalem Warm-up unter
  400 Millisekunden für die Kerneinheitenakte bei mehrjähriger Historie; Abweichungen messen und in
  Build-Notes begründen. Startpayload enthält höchstens sechs Zahlungsperioden, drei Nachrichten und
  fünf Dokumente; weitere Daten per Pagination. Feste Demo-IDs und `demo_today`/`demo_now` verwenden.
- **Erwartetes Ergebnis:** Anna demonstriert vollständige Eckdaten, aktive Portalnutzung, Nachricht,
  Dokumente und 125,00 Euro offene Nachzahlung. Fatma demonstriert Mieterwechsel und noch nicht
  eingerichtetes Portal. Jonas, Maria und Sophie demonstrieren Teilzahlung, ungeklärte Überzahlung und
  offene Forderung ohne erfundenen Umsatz. Gewerbeeinheiten zeigen keine geratenen Zimmerwerte.
- **Akzeptanz:** Demo-Reset erfüllt die Green-light-Checkliste des Runbooks. Tests messen keine
  N+1-Abfrage pro Einheit oder Historienzeile, stabile Payloadgröße, konsistente Invalidierung,
  Rollen-/RLS-Grenzen und centgleiche Salden. Typprüfung, Lint, Full-Gate und nicht-destruktiver
  Demo-Gate sind grün.
- **Nicht tun:** Demo-IDs als Produktionslogik verwenden; Frontend nach Unit-ID verzweigen;
  vollständige Historien vorladen; zufällige Laufzeitwerte erzeugen; Golden-Abrechnungswerte ändern;
  destruktiven Demo-Reset ohne ausdrückliche Freigabe ausführen.

## Out of Scope

- Das Objekt-Dashboard, die Objektliste, Kartenansicht oder globale App-Shell neu gestalten; dafür
  gelten `00_Layout-Global.md`, `02_Objekte.md` und `07_Objekt-Dashboard.md`.
- Objekt-KPIs, allgemeine Aufmerksamkeit, vollständige Kosten-, Zähler-, Abrechnungs-, Bank- oder
  Aktivitätshistorien in die Einheitenseite kopieren.
- Rechtliche Bewertung, Empfehlung oder Terminberechnung für eine Mieterhöhung; ebenso keine
  Mietspiegel-, Kappungsgrenzen-, Modernisierungs- oder Vertragsauslegung.
- Vollständiges Mieterportal, dessen Mieter-UI, Identitätsprüfung oder Vertragsgenerator. Dieser Spec
  definiert nur die vermieterseitige Zugriffsverwaltung und ihren ehrlichen inaktiven Zustand.
- Produktives Nachrichtenportal ohne die MUSS-INPUTs aus [ED10].
- Allgemeiner Dokumentupload/-Storage ohne die MUSS-INPUTs aus [ED11].
- Neue Forderungs-, Fälligkeits-, Guthaben-, Mahn-, Verzugs-, Zins-, Gebühren- oder
  Gesamtschuldnerlogik.
- Automatische Guthabenverrechnung, Auszahlung oder „alle Mieten als bezahlt markieren“.
- Neue Abrechnungs-, Kosten-, Zähler-, Verbrauchs-, Readiness- oder Rechtsberechnungen.
- Allgemeines CRM, Notizen, Tickets, Vorgänge, Reminder oder Aktivitätsfeed. Die Einheitenakte bleibt
  bewusst schmaler als die Objektakte.
- Immocloud-Navigation, Farben, Layoutpixel oder Komponenten kopieren; Screenshots dienen nur als
  Kontext für Informationsarchitektur.

## Verifikation

1. Der bestehende Demo-Einheitenpfad lädt wieder; Frontend- und Backendvertrag für versionierte
   Vorauszahlungen stimmen in einem echten Contract-Test überein.
2. Breadcrumb führt über das konkrete Objekt zurück. Kopf zeigt Einheit, Adresse, Zustand und
   gemeinsamen Datenstand.
3. Eckdaten zeigen Fläche, Zimmer, Nutzung, Kaltmiete, backendprojizierte Kaltmiete/m² und
   Garage/Stellplatz. Ausstattung erscheint nur aus persistierten Fakten.
4. Die Seite enthält keine Objekt-KPI-Reihe und bleibt sichtbar kompakter als das Objekt-Dashboard.
5. Aktuelles Mietverhältnis zeigt alle Parteien, Vertragszeitraum, Vertragsart, Vorauszahlungen,
   Gesamtmietsoll, Stellplatzbezug und ausschließlich dokumentierte Mietänderungen.
6. Eine Volltextsuche im Einheiten-Frontend findet keine Aussage „Mieterhöhung möglich“, keinen
   frühesten Erhöhungstermin und keine rechtliche Bewertung.
7. Historie zeigt Mieterwechsel, Leerstand, Eigennutzung und Zukunftsvertrag mit demselben `asOf`; im
   sichtbaren Nutzertext stehen nicht `validFrom`, `validTo`, „halboffen“ oder „exkl.“.
8. Zahlungsabschnitt verwendet dieselben Forderungs-IDs und Centbeträge wie Zahlungs-, Objekt- und
   Dashboardprojektionen. Jonas, Maria, Sophie und Anna zeigen die Runbook-Zustände korrekt.
9. Portalzugriff ist pro Partei und Mietverhältnis modelliert. Ohne freigegebenen Identitäts-/
   Versandpfad bleibt die Aktion ehrlich inaktiv.
10. Nachrichten und Dokumente zeigen nur persistierte, autorisierte Daten. Ohne Modul/Storage gibt es
    keine funktionsfähigen Scheinaktionen oder große leere Flächen.
11. Owner-/Employee-, fremde Account-, Gebäude-, Einheit-, Mietverhältnis- und Dokumentzugriffe werden
    serverseitig geprüft; direkte fremde Aufrufe liefern 403/404 gemäß bestehendem Vertrag.
12. Kernfehler, Teilfehler, 404, leere Einheit, fehlende Stammdaten und erfolgreiche Mutationen besitzen
    verständliche Zustände ohne API-/Datenbank-/Zod-Sprache.
13. Desktop/Laptop bei 1280, 1440 und 1920 Pixel, 200 Prozent Zoom, Tastatur, Screenreader und Reduced
    Motion funktionieren ohne horizontalen Seitenscroll im Standardzoom oder Fokusverlust.
14. Startpayload bleibt kompakt und paginiert Historien. Messung zeigt keine N+1-Abfragen und
    dokumentiert die lokale Abrufzeit.
15. Portfolio-Demo, Typprüfung, Lint, Full-Gate, RLS-/FK-Prüfungen und nicht-destruktiver Demo-Gate
    bleiben grün; bestehende Golden-Beträge und finale Archivbytes bleiben unverändert.

## Reihenfolge

1. [ED1] — bestehenden Laufzeit-Vertragsbruch reparieren.
2. [ED2], [ED3] — Read Model sowie fehlende strukturierte Stammdaten schaffen.
3. [ED4], [ED5], [ED6], [ED7] — kompakte Akte, Aktionen, aktueller Vertrag und Historie.
4. [ED8] — autoritativen Zahlungs-/Saldoausschnitt anbinden.
5. [ED9], [ED10], [ED11] — Portal, Nachrichten und Dokumente nur im tatsächlich verfügbaren Umfang.
6. [ED12], [ED13] — Zustände, Desktop-/Laptop-Breiten, Tastatur und Fokus.
7. [ED14] — Performance, Portfolio-Demo und vollständige Abnahme.

## Build-Notes (füllt die KI beim Umsetzen aus)

<!-- Erwartete Einträge:
- [ED1] tatsächliche Ursache und gewählter kompatibler Vorauszahlungsvertrag.
- [ED2] Endpoint-/Read-Model-Struktur, autoritative Quellen und Teilfehlergrenzen.
- [ED3] konkrete Migration, Bestandsdaten mit unbekannten Werten und Versionierungsmodell.
- [ED5] ungeklärte Employee-Aktionen als Owner-only behandelt.
- [ED8] MUSS-INPUT Forderungs-/Fälligkeits-/Gesamtschuldnerregeln vorhanden oder nur bestehende
  Forderungen angezeigt.
- [ED9] Portal-Identitäts-/Einladungsprozess vorhanden oder ausschließlich inaktiver Zustand.
- [ED10] Nachrichtenpfad vorhanden oder Modul ausgelassen/inaktiv.
- [ED11] Storage-/Dokumentenprozess vorhanden oder nur echte Abrechnungsarchive gezeigt.
- [ED14] gemessene Abrufzeit, Payloadgrößen, Pagination und tatsächlicher Portfolio-Seed-Stand.
-->
