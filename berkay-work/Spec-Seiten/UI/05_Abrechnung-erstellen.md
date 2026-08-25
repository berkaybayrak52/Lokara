---
spec_id: 05-abrechnung-erstellen
titel: Abrechnung erstellen — Liste, geführter Wizard, Finalisierung und Dokumente
status: freigegeben
prioritaet: hoch
betrifft: apps/web, apps/api, packages/db, packages/pdf
abhaengig_von: [00-layout-global, 02-objekte, 03-kosten, 04-zaehler]
repo_stand: Lokara-main @ 2026-08-25
---

## Zweck

Die heutige einzelne Berechnungsmaske wird durch eine Abrechnungsliste und einen geführten,
wiederaufnehmbaren Erstellungsprozess ersetzt. Vorhandene Objekt-, Miet-, Kosten-, Zähler-, Heizkosten-
und Vorauszahlungsdaten werden kontrolliert übernommen, fachliche Blocker kommen ausschließlich aus
Backend und Engines, und finalisierte Einzelabrechnungen erhalten ein schlichtes, druckfreundliches
A4-Layout nach den freigegebenen PDF-Referenzen. Dieser Spec enthält keinen Code; die Umsetzung erfolgt
gegen den dann aktuellen Repo-Stand.

## Invarianten

- Pre-Pitch gilt Desktop/Laptop bei 1280, 1440 und 1920 Pixel sowie 200-Prozent-Zoom. Smartphone-,
  Tablet- und native Varianten sind Post-Pitch; Tastatur, Screenreader und sichtbarer Fokus bleiben
  verpflichtend.

- Nur die vorhandenen Design-Tokens Petrol-Ink, Lokara-Grün, Forest, Mint, Slate und Paper sowie die
  vorhandenen Status-Tokens verwenden. Montserrat (`font-display`) gilt für Überschriften und
  Kennzahlen, Manrope (`font-sans`) für Fließtext, Labels und Tabellen. Keine rohen Farbwerte und keine
  alten Navy-/Teal-/Cream-/Poppins-Vorgaben verwenden.
- App-Shell, Container und Portfolio-Navigation aus `00_Layout-Global` erben. Kein globaler
  Objektfilter; die Objektauswahl innerhalb des Abrechnungs-Wizards ist fachlich lokal.
- Eine Abrechnung betrifft genau ein Objekt und einen Abrechnungszeitraum. Einheiten, Nutzungsabschnitte
  und Parteien werden daraus abgeleitet, nicht kontoweit vermischt.
- Frontend und PDF berechnen keine Rechts-, Geld-, Frist-, Schätz-, Rundungs-, Verteilungs- oder
  Statuslogik. Fachliche Werte, Readiness, Findings, Fristen und Berechnungsergebnisse kommen aus
  Backend, Guards, Rules Store und Engines.
- Geld bleibt ganzzahlig in Cent beziehungsweise `Decimal`; keine Float-Berechnung. Angezeigte
  Euro-Eingaben werden ausschließlich am API-Rand in Cent umgewandelt.
- Mietverhältnisse, Eigennutzung, mietfreie Nutzung und Leerstand sind unterschiedliche zeitliche
  Sachverhalte. Sie nie in einem einzigen Boolean oder einer pauschalen Auswahl zusammenfassen.
- Eine Abrechnung darf nur mit Backend-Status `READY` finalisiert werden. Warnungen erlauben das
  Fortfahren ausschließlich, wenn das Backend sie ausdrücklich als nicht blockierend klassifiziert.
- Vorschau ist live beziehungsweise entwurfsbezogen; Finalisierung friert Eingaben, Ergebnisse,
  Dokumente, Rechtsstände und Herkunft unveränderlich ein. Korrekturen erzeugen neue Versionen und
  überschreiben keine finalisierte Fassung.
- Tatsächliche bestätigte Vorauszahlungen bestimmen den Saldo. Vertragliches Vorauszahlungssoll darf
  fehlende Ist-Zahlungen nie ersetzen.
- Für denselben Objektzeitraum gilt genau ein maßgeblicher Heizkostenpfad: Lokara-Eigenberechnung oder
  bestätigte externe Messdienstleister-Abrechnung. Beide Ergebnisse nie addieren oder parallel als
  maßgeblich verwenden.
- E-Mail-Belegimport, OCR, Mieterportal, Nachrichtenversand und E-Mail-Versand nur als funktionsfähig
  anzeigen, wenn ihre echten Backend-/Adapterpfade vorhanden und getestet sind. Andernfalls eindeutig
  als inaktiver Zukunftsausblick kennzeichnen; keine Adresse, Zustellung oder Erkennung simulieren.
- Signal nie allein über Farbe vermitteln. Status enthält immer Text und gegebenenfalls Symbol/Form.
- Der Wizard ist per Tastatur bedienbar, führt Fokus nach Navigation und Fehlern gezielt, erfüllt WCAG
  2.1 AA/BFSG und respektiert `prefers-reduced-motion`.
- Bestehende Account-/Gebäude-/Einheiten-Autorisierung und RLS nicht abschwächen. Jeder neue Datensatz
  und Endpoint bleibt `account_id`-gescopet; Finalisierung und Versand bleiben Owner-only.
- Bestehende Tests, Typprüfung, Lint, RLS-/FK-Gates und die heutigen Engine-Goldens bleiben grün. Neue
  fachliche Verträge erhalten Backend-, DB-, Engine-, PDF- und Frontendtests.
- Bei normaler Unklarheit den genannten Default verwenden und die Annahme in `## Build-Notes`
  festhalten. `⚠️ MUSS-INPUT` nie raten; nur den betroffenen Teil überspringen und den Rest umsetzen.

## Befehle

### [R1] Abrechnungsliste als Startseite aufbauen

- **Datei/Ort:** `apps/web/src/app/a/[accountId]/abrechnung/page.tsx`; die heutige
  `StatementPage`-Einbindung und neue fachlich benannte Listenkomponenten unter
  `apps/web/src/features/abrechnung/`. Bestehende Berechnungs-/Finalisierungsbausteine aus
  `features/portal/statement.tsx` kontrolliert aufteilen oder wiederverwenden.
- **Fundstelle:** Die heutige Seite „Abrechnung erstellen“, die sofort die Karte „Abrechnung
  berechnen“ mit Objekt und Zeitraum zeigt.
- **Ist:** Es gibt keine Übersicht aller Entwürfe und finalisierten Abrechnungen. Auswahl, Berechnung,
  Vorauszahlungsprüfung, Finalisierung und Archiv stehen in einem langen Screen.
- **Soll:** `/abrechnung` zu einer Liste aller für das Konto sichtbaren Abrechnungen machen. Oben stehen
  Titel „Abrechnungen“, ein kurzer Untertitel und rechts die primäre Aktion „Abrechnung erstellen“.
  Darunter eine filter- und sortierbare Tabelle mit Titel, Objekt, Einheitenanzahl, Zeitraum, Status,
  Ergebniszusammenfassung, erstellt am, zuletzt geändert und Aktionsmenü. Entwürfe öffnen den Wizard an
  der zuletzt bearbeiteten Stelle; finalisierte Fassungen öffnen die Detail-/Archivansicht aus [R16].
- **Default:** Titel „Abrechnungen“. Untertitel „Betriebs- und Heizkostenabrechnungen vorbereiten,
  prüfen und abschließen.“ Standardsortierung `updated_at` absteigend. Statusfilter „Alle“, „Entwurf“,
  „Prüfung erforderlich“, „Bereit“, „Finalisiert“, „Teilweise versendet“, „Versendet“, „Korrigiert“.
  Ergebnistext beispielsweise „2 Nachzahlungen · 1 Guthaben“; solange kein bestätigter Saldo existiert
  „Noch kein Ergebnis“. Zeilenaktion für Entwurf „Weiterbearbeiten“, für finalisierte Version „Öffnen“.
- **Erwartetes Ergebnis:** Die Fachseite beginnt wie Objekte und Kosten mit einer ruhigen, vollbreiten
  Bestandsliste. Statusbadges nutzen Text plus vorhandene Status-Tokens. Ein leerer Account zeigt keine
  leere Tabelle, sondern „Noch keine Abrechnung“ mit der Aktion „Erste Abrechnung erstellen“. Die
  Tabelle bleibt auf den Pre-Pitch-Breiten 1280, 1440 und 1920 Pixel ohne horizontale Gesamtseitenrolle
  lesbar. Eine Smartphone-/Tablet-Kartenvariante ist Post-Pitch.
- **Akzeptanz:** `/abrechnung` zeigt nicht mehr direkt die heutige Berechnungskarte. Eine gespeicherte
  Abrechnung erscheint als Listeneintrag; ein Entwurf ist wiederaufnehmbar, eine finalisierte Version
  führt zu Dokumenten und Historie. Es gibt genau eine primäre Kopfaktion.
- **Nicht tun:** Dashboard oder App-Shell umbauen; eine kontoweite Objektfilterung einführen; bestehende
  finalisierte Archive löschen oder aus der Liste ausblenden.

### [R2] Persistentes, versionierbares Abrechnungsentwurfsmodell ergänzen

- **Datei/Ort:** Abrechnungs-/Statement-Modelle in `packages/db/src/lokara_db/models.py`, neue
  Alembic-Migration, API-Schemas und ein account-/building-gescopeter Draft-Router beziehungsweise eine
  klare Erweiterung des vorhandenen Statement-Bereichs.
- **Fundstelle:** Das heutige `Statement`-Modell speichert finalisierte Versionen; die Live-Vorschau
  bleibt ausschließlich im Client-/Query-Zustand. Es gibt keinen wiederaufnehmbaren Entwurf.
- **Ist:** Beim Verlassen der Seite gehen Auswahl und Bearbeitungsfortschritt verloren. Ein
  finalisiertes Statement ist zu Recht unveränderlich, kann aber keinen editierbaren Entwurf ersetzen.
- **Soll:** Ein eigenständiges, account- und building-gescopetes Abrechnungsentwurfsmodell einführen.
  Es speichert Objekt, Zeitraum, Titel, aktuellen Wizard-Schritt, ausgewählte Einheiten, ausschließlich
  erlaubte entwurfsbezogene Overrides, Erstell-/Änderungszeitpunkt und einen optimistischen
  Versionszähler. Stammdaten und Kosten nicht vollständig duplizieren; Entwurf referenziert Quellen
  und speichert nur bewusste Abweichungen. Finalisierung liest einen konsistenten Entwurf, friert seine
  aufgelösten Eingaben ein und markiert ihn abgeschlossen.
- **Default:** Status `DRAFT | REVIEW_REQUIRED | READY | FINALIZED | CANCELLED`; separater
  Versandstatus aus [R17]. Genau ein aktiver Entwurf pro Objekt, Zeitraum und Titel ist nicht zwingend;
  Duplikate sind erlaubt, aber die UI warnt. Autospeichern mit etwa 600 ms Entprellung nach einer
  relevanten Änderung und sofort beim Schrittwechsel. Sichtbarer Text „Gespeichert“ beziehungsweise
  „Speichern fehlgeschlagen“. Optimistische Konflikte liefern HTTP 409 und laden nicht still fremde
  Änderungen über die lokale Fassung.
- **Erwartetes Ergebnis:** Ein Nutzer kann die Erstellung verlassen, aus der Liste wieder öffnen und
  an derselben Stelle mit denselben Entscheidungen fortsetzen. Finalisierte Datensätze bleiben
  unveränderlich und werden nie wieder zu Entwürfen.
- **Akzeptanz:** Entwurf anlegen, ändern, neu laden und fortsetzen funktioniert. Zwei konkurrierende
  Updates überschreiben einander nicht unbemerkt. Finalisierung erzeugt weiterhin immutable Snapshot,
  Archive und Hashes; der Entwurf verweist anschließend auf die finalisierte Version.
- **Nicht tun:** Finalisierte `Statement`-Zeilen editierbar machen; vollständige ORM-Objekte als
  unversionierte JSON-Kopie ablegen; Entwürfe nur in localStorage speichern; RLS umgehen.

### [R3] Wizard-Einstieg mit Objekt und Zeitraum erstellen

- **Datei/Ort:** Neue Route `apps/web/src/app/a/[accountId]/abrechnung/neu/page.tsx` und neuer Wizard
  unter `apps/web/src/features/abrechnung/`; Draft-Create-Endpoint aus [R2].
- **Fundstelle:** Die heutige Karte „Abrechnung berechnen“ mit Objekt, `Zeitraum von`, `Zeitraum bis`
  und hart vorbelegtem Jahr 2025.
- **Ist:** Objekt und Zeitraum starten sofort eine Live-Berechnung. Die Standardperiode ist ein
  Demo-Preset, kein Produktdefault; es wird kein Entwurf erzeugt.
- **Soll:** Vor dem vollständigen Wizard einen kompakten Einstieg mit Objektauswahl und
  Abrechnungszeitraum zeigen. „Weiter“ validiert die Auswahl serverseitig, erzeugt einen Entwurf und
  öffnet [R4] auf Schritt „Grundlagen“.
- **Default:** Bei genau einem Objekt automatisch vorauswählen; bei mehreren „Objekt wählen“. Ein von
  Objektakte/Dashboard mitgegebener `objektId`-Queryparameter wird nach Autorisierung vorausgewählt.
  Zeitraumvorschläge kommen aus einer Backend-Projektion über vorhandene Kosten-/Miet-/Ablesedaten und
  bereits finalisierte Perioden. Default ist der jüngste vollständige, noch nicht finalisierte Zeitraum;
  fehlt ein Vorschlag, bleiben Von/Bis leer. Anfang und Ende sind im UI inklusive. Primär „Weiter“,
  sekundär „Abbrechen“ zurück zur Liste.
- **Erwartetes Ergebnis:** Es gibt keinen hart codierten 2025-Default. Ein privater Vermieter wählt nur
  Objekt und Zeitraum, bevor der umfassende Prozess beginnt. Ungültige, über zwölf Monate lange oder
  widersprüchliche Zeiträume werden mit dem konkreten Backend-Fehler erklärt und nicht gespeichert.
- **Akzeptanz:** Bei einem Objekt ist es vorausgewählt; bei mehreren ist eine bewusste Wahl erforderlich.
  „Weiter“ erzeugt einen wiederauffindbaren Entwurf. Zeitraumregeln werden nicht in React berechnet.
- **Nicht tun:** Das erste Objekt still als Fallback verwenden, wenn mehrere existieren; Frist- oder
  Höchstdauerlogik im Frontend hart codieren; bereits finalisierte Perioden ohne Korrekturhinweis als
  normale Erstabrechnung starten.

### [R4] Permanente Fortschrittsleiste und Wizard-Rahmen bauen

- **Datei/Ort:** Gemeinsamer Wizard-Rahmen der neuen Abrechnungsfeature-Dateien; alle Wizard-Routen
  beziehungsweise ein routeninterner Schrittzustand.
- **Fundstelle:** Neuer Bereich; die Immocloud-Screenshots dienen nur als Informationsarchitektur-
  Inspiration, nicht als Farb-/Komponentenquelle.
- **Ist:** Der heutige Screen ist eine lange lineare Seite ohne sichtbaren Fortschritt, gespeicherten
  Schritt oder klare Trennung von Vorbereitung, Prüfung und Abschluss.
- **Soll:** Während der gesamten Erstellung oben eine dauerhaft sichtbare Fortschrittsleiste mit sechs
  Schritten anzeigen: „Grundlagen“, „Absender & Konto“, „Einheiten & Mietverhältnisse“, „Kosten &
  Verteilung“, „Prüfung & Vorauszahlungen“, „Dokumente & Versand“. Darunter steht jeweils genau ein
  fachlicher Schritt. Unten eine feste, aber nicht überdeckende Aktionsleiste mit „Zurück“, „Entwurf
  speichern und schließen“ und „Weiter“ beziehungsweise der fachlich passenden Abschlussaktion.
- **Default:** Desktop/Laptop horizontal; auf 1280 Pixel darf die Beschriftung kompakter werden, alle
  sechs Schritte bleiben jedoch sichtbar und zugänglich. Zustände `COMPLETED`, `CURRENT`, `UPCOMING`, `BLOCKED` aus dem
  Draft-/Readiness-Vertrag. Abgeschlossene Schritte sind anklickbar, zukünftige erst nach Abschluss der
  notwendigen Vorgänger; Blocker öffnen ihren ersten Fehler. Fortschrittszustand wird im Entwurf
  gespeichert. Sticky-Leiste nur innerhalb des Inhaltsbereichs, unterhalb der App-Shell.
- **Erwartetes Ergebnis:** Der Nutzer weiß jederzeit, wo er ist, was erledigt ist und welcher Bereich
  Aufmerksamkeit braucht. Fokus wechselt beim Schrittwechsel auf die neue H1; bei Validierungsfehlern
  auf die Fehlerzusammenfassung beziehungsweise das erste ungültige Feld. Keine Vollseitenanimation.
- **Akzeptanz:** Alle sechs Schritte sind bei 1280, 1440 und 1920 Pixel sichtbar. Tastatur und Screenreader
  erkennen aktuellen, abgeschlossenen und blockierten Zustand. Zurück/Weiter verliert keine Daten.
- **Nicht tun:** Immocloud-Farben oder Layoutpixel kopieren; Fortschritt nur über eine farbige Linie
  darstellen; Browser-History durch rein lokalen unadressierbaren Zustand unbrauchbar machen.

### [R5] Grundlagen, Titel und Einheitenumfang festlegen

- **Datei/Ort:** Schritt „Grundlagen“ im Abrechnungs-Wizard, Draft-Schemas/-Endpoint und Backend-
  Projektion der Einheiten/Nutzungsarten.
- **Fundstelle:** Neuer Schritt nach Objekt-/Zeitraumauswahl; in der heutigen Seite fehlt Titel und eine
  kontrollierte Auswahl der einbezogenen Einheiten.
- **Ist:** Die Live-Berechnung nimmt automatisch alle aus den Daten ableitbaren Einheiten. Eigennutzung,
  mietfreie Nutzung und Leerstand sind nicht als überprüfbarer Umfang sichtbar.
- **Soll:** Titel, unveränderlich sichtbares Objekt, Zeitraum und Abrechnungsumfang anzeigen. Einen
  Hauptschalter „Alle abrechnungsrelevanten Einheiten berücksichtigen“ anbieten und darunter immer eine
  vollständige Tabelle der Einheiten/Nutzungsabschnitte mit Auswahl, Nutzungsart und Backend-Status.
  Bei deaktiviertem Hauptschalter einzelne fachlich zulässige Einheiten auswählbar machen. Eigennutzung,
  mietfreie Nutzung und Leerstand getrennt kennzeichnen und in Eigentümer-/Steuerprojektionen erhalten.
- **Default:** Titel „Betriebs- und Heizkostenabrechnung {Jahr} – {Objektname}“. Hauptschalter aktiv.
  Tabellenspalten „Einheit“, „Nutzung im Zeitraum“, „Parteien“, „Zeitraum“, „Einbezogen“, „Status“.
  Alle backendseitig abrechnungsrelevanten Einheiten aktiv; Einheiten ohne Mieter bleiben für
  Eigentümer-/Leerstandsanteile enthalten. Hilfetext: „Leerstand, Eigennutzung und mietfreie Nutzung
  bleiben als eigene Zeitabschnitte nachvollziehbar.“
- **Erwartetes Ergebnis:** Der Nutzer sieht vor jeder Berechnung den vollständigen Umfang. Ein
  Mieterwechsel erscheint als mehrere Abschnitte, nicht als aktueller Mieter. Ein Ausschluss, den das
  Backend fachlich nicht zulässt, wird verhindert und verständlich begründet.
- **Akzeptanz:** Titel ist editierbar und wird gespeichert. Alle Einheiten des Objekts sind sichtbar.
  Eigennutzung, mietfreie Nutzung und Leerstand sind getrennte Werte. Keine Steuerwirkung wird im
  Frontend berechnet oder behauptet.
- **Nicht tun:** Einen einzigen Switch „Eigennutzung/mietfrei einbeziehen“ als Datenmodell verwenden;
  leerstehende Einheiten ausblenden; Nutzungsart aus Namen oder fehlendem Mieter raten.

### [R6] Absender-, Adress- und Kontodaten kontrolliert versionieren

- **Datei/Ort:** Schritt „Absender & Konto“, vorhandene Delivery-/Payment-Versionierungsmodelle und
  passende account-/building-gescopete APIs; Draft-Overrides.
- **Fundstelle:** Heute stehen „Zustelladresse versionieren“ und „Zahlungs- und Guthabenhinweis
  versionieren“ erst tief im Finalisierungsblock; Kontoinformationen sind nicht als zusammenhängender
  Prüfschritt vorhanden.
- **Ist:** Stammdatenpflege, dokumentbezogene Auswahl und Finalisierung sind vermischt. Änderungen
  können nicht klar auf „nur diese Abrechnung“ versus „künftig als Stammdatum“ begrenzt werden.
- **Soll:** Absendername/Firma, Anschrift, Kontoinhaber, IBAN, BIC soweit fachlich erforderlich,
  Zahlungshinweis und Guthabenhinweis in klaren Karten anzeigen. Bestehende gültige Versionen
  vorausfüllen. Jede Korrektur gilt standardmäßig nur als Entwurfs-Override; eine getrennte bewusste
  Aktion speichert sie zusätzlich als neue Stammdatenversion. Finalisierung friert die ausgewählte
  Fassung wortgetreu ein.
- **Default:** Zwei Karten „Absender“ und „Bankverbindung & Hinweise“. Default-Auswahl „Nur für diese
  Abrechnung ändern“. Sekundäre Checkbox/Aktion „Auch als neue Stammdatenversion speichern“ ist nicht
  vorausgewählt. IBAN maskiert anzeigen, beim Bearbeiten vollständig; BIC nur zeigen, wenn Datenvertrag
  oder Zahlungsweg sie benötigt. Kein fremdes Bankkonto vorauswählen.
- **Erwartetes Ergebnis:** Der Nutzer kann die später gedruckten Angaben vor der Mieterprüfung
  korrigieren, ohne versehentlich globale Stammdaten zu überschreiben. Versionshistorie bleibt
  nachvollziehbar.
- **Akzeptanz:** Änderung nur im Entwurf verändert keine bestehende Stammdatenzeile. Bewusste globale
  Speicherung erzeugt eine neue Version. Vorschau und finalisiertes PDF verwenden exakt die im Entwurf
  ausgewählten Angaben.
- **Nicht tun:** Alte Versionen überschreiben; IBAN in Listen/Logs vollständig ausgeben; Kontodaten im
  Client erfinden; heutige DeliveryAddress als Gebäudeadresse missbrauchen.

### [R7] Einheiten- und Mietdaten in einer großen Prüftabelle zeigen

- **Datei/Ort:** Schritt „Einheiten & Mietverhältnisse“, read-only Backend-Projektion über Gebäude,
  Units, Tenancies, Personenzahlperioden, Vorauszahlungspläne und bestätigte Zahlungen; Frontend-Tabelle.
- **Fundstelle:** Die heutige Abrechnungsseite zeigt diese Daten vor der Berechnung nicht; die
  Vorauszahlungsprüfung wählt Mietverhältnisse einzeln in einem Dropdown.
- **Ist:** Mieterwechsel, Nutzungszeitraum, Personenzahl, Fläche und Vorauszahlungen sind nicht gemeinsam
  kontrollierbar. Der Einzelauswahl-Workflow skaliert schlecht und lädt zu ausgelassenen Parteien ein.
- **Soll:** Eine vollbreite, ruhige Tabelle für alle betroffenen Nutzungsabschnitte rendern. Spalten:
  „Einheit“, „Nutzung“, „Name/Partei“, „Nutzungszeitraum“, „Ø Personenzahl“, „Fläche“, „vertragliches
  Vorauszahlungssoll“, „bestätigte Ist-Vorauszahlungen“, „Status“, „Aktion“. Mieterwechsel erzeugen
  getrennte Zeilen; Leerstand/Eigennutzung/mietfrei sind eigene Zeilen. Korrekturen führen per Link zur
  zuständigen Objekt-/Einheitenfunktion und kehren anschließend in den Entwurf zurück.
- **Default:** Keine Inline-Mini-Formulare. „Prüfen“ öffnet Details beziehungsweise den bestehenden
  Stammdatenort. Ø Personenzahl und Zeitanteile kommen fertig aus der Backend-Projektion und tragen ihre
  Einheit/Periode. Fehlt eine bestätigte Ist-Abstimmung, zeigt die Zeile `BLOCKER` mit „Vorauszahlungen
  noch nicht bestätigt“. Eine eigene mobile Karte pro Abschnitt ist Post-Pitch.
- **Erwartetes Ergebnis:** Private Vermieter können alle abrechnungsrelevanten Parteien in einem Blick
  kontrollieren. Systematische Lücken und Überschneidungen sind sichtbar, bevor Kosten verteilt werden.
- **Akzeptanz:** Jeder Nutzungsabschnitt des Zeitraums ist genau einmal sichtbar. Ein Mieterwechsel und
  anschließender Leerstand erscheinen getrennt. Frontend berechnet weder Durchschnittspersonenzahl noch
  Tagesanteile. Direktsprung und Rückkehr zum Entwurf funktionieren.
- **Nicht tun:** Nur heute aktive Mietverhältnisse zeigen; vertragliches Soll als Ist-Zahlung anzeigen;
  fremde Mieterdaten in eine Einzelabrechnung projizieren; ein zweites Mietdatenmodell im Wizard bauen.

### [R8] Einheitlichen Backend-Readiness-Vertrag für die Abrechnung schaffen

- **Datei/Ort:** Statement-/Draft-Service im API, Schemas, gegebenenfalls ein reiner Orchestrierungs-
  Vertrag zwischen NK-, Heating-, Guard- und Rules-Ergebnissen; Frontend-Contracts.
- **Fundstelle:** Heute existieren strukturierte Heizkosten-Findings, textuelle NK-Findings, ein
  `page02_production_blocked`-Boolean, `heating_missing_reason` und separate Router-Fristlogik.
- **Ist:** Die UI kann nicht einheitlich erklären, welcher Datensatz fehlt, wo er korrigiert wird und
  ob Vorschau, Finalisierung oder nur eine Nachforderung blockiert ist.
- **Soll:** Einen strukturierten Readiness-Vertrag liefern. Jeder Prüfpunkt enthält stabilen Code,
  Bereich, Schweregrad `INFO | WARNING | BLOCKER`, betroffene Entity-ID/-Art, deutschen Nutztext,
  Korrekturroute, erlaubte Aktionen und Rechts-/Regelprovenienz, sofern relevant. Der Gesamtstatus
  `DRAFT | REVIEW_REQUIRED | READY | FINALIZED` wird serverseitig abgeleitet. Mindestens prüfen:
  Objekt/Einheiten, Mietzeiträume, Personenzahlen, Kostenklassifizierung, Umlageschlüssel, Vertragsbasis,
  Zähler/Ablesepaare, Heizkostenpfad, CO₂-Eingaben, Vorauszahlungsabstimmungen, Absender/Adresse/Konto,
  Kontrollsummen, Frist und bestehende finale Version.
- **Default:** Blocker verhindern „Weiter“ nur, wenn der nächste Schritt fachlich darauf angewiesen ist;
  spätestens Prüfung/Finalisierung zeigen alle Blocker. Warnungen bleiben sichtbar und quittierbar,
  werden aber nicht im Client hoch- oder heruntergestuft. Korrekturroute ist relativ zum Account.
- **Erwartetes Ergebnis:** Alle Wizard-Schritte verwenden denselben Statusvertrag. Fehlermeldungen
  führen zum Handlungsort, statt „API und Datenbank prüfen“ zu sagen. Engines bleiben die Quelle der
  Fachentscheidung.
- **Akzeptanz:** Für jeden genannten Bereich existiert ein testbarer Status. Eine fehlende Endablesung,
  unbestätigte externe Abrechnung oder fehlende Vorauszahlungsabstimmung liefert einen konkreten
  Blocker mit Entity und Route. Eine Frontend-Suche findet keine nachgebildete Fachstatusberechnung.
- **Nicht tun:** Gesetzesfristen, Prozentsätze, Schätzschwellen oder Rechenregeln in React duplizieren;
  technische Exceptions ungefiltert anzeigen; alle Hinweise pauschal zum Blocker machen.

### [R9] Kosten und Umlageschlüssel aus Lokara in einer Prüftabelle übernehmen

- **Datei/Ort:** Schritt „Kosten & Verteilung“, Statement-/Draft-Projektion, vorhandene Kosten-
  Contracts und `03_Kosten`-Datenmodelle; neue Abrechnungs-Komponenten.
- **Fundstelle:** Heute zeigt die Ergebnisansicht bereits berechnete Karten pro Kostenart. Eine
  vorbereitende, bearbeitbare Gesamttabelle fehlt.
- **Ist:** Nutzer sehen erst nach der Berechnung, welche Kosten eingeflossen sind. Änderungen am
  Schlüssel oder fehlende Positionen erfordern einen unklaren Seitenwechsel.
- **Soll:** Alle zum Objekt und Zeitraum gehörenden, nicht stornierten Kosten automatisch in eine
  vollbreite Tabelle übernehmen. Spalten: „Kostenart“, „Zeitraum“, „Beleg/Quelle“, „Gesamtkosten“,
  „umlagefähiger Betrag“, „Verteilerschlüssel“, „Hinweis“, „Status“, „Aktionen“. Der Nutzer kann eine
  Position prüfen, ihren Schlüssel als neue versionierte Zuordnung ändern, einen dokumentbezogenen
  Hinweis ergänzen, zur Kostenakte springen oder über [R10] weitere Kosten erfassen.
- **Default:** Nur vorhandene Positionen anzeigen; keine Liste aller Katalogarten mit `0,00 €`.
  Standardsortierung nach BetrKV-Katalogreihenfolge, danach Belegdatum/Erstellung. Summenfuß mit
  Gesamtkosten, nicht umlagefähigem Eigentümeranteil und umlagefähigem Betrag. Schlüssel als Klartext
  plus kurze Bemessung; Direktzuordnung nennt das Ziel. Heizkostenpositionen erhalten ihren getrennten
  Pfad aus [R11] und werden nicht als freie NK-Zeile doppelt geführt.
- **Erwartetes Ergebnis:** Die meisten Daten sind durch `03_Kosten` bereits vorbereitet und müssen nur
  kontrolliert werden. Jede Abweichung bleibt auditierbar; eine Schlüsseländerung rechnet die Vorschau
  neu, ohne Ursprungsdaten zu überschreiben.
- **Akzeptanz:** Alle wirksamen Kosten erscheinen genau einmal. Stornierte Positionen fehlen, bleiben in
  ihrer Kostenhistorie erhalten. Änderung eines Schlüssels erzeugt eine neue Assignment-Version und
  aktualisiert Readiness/Vorschau. Kontrollsumme kommt vom Backend.
- **Nicht tun:** Kostentexte frei als Rechtsklassifizierung behandeln; Schlüssel im Frontend automatisch
  wählen; Kostenzeilen endgültig löschen; Heizkosten doppelt addieren.

### [R10] Weitere Kosten im Wizard erfassen und einmalig auf bessere Eingangswege hinweisen

- **Datei/Ort:** Kosten-Schritt aus [R9], kontrolliert wiederverwendeter Kosten-Wizard aus
  `03_Kosten`, Draft-State und ein rein lokaler/entwurfsbezogener Hinweisstatus.
- **Fundstelle:** Neue Aktion „Kosten hinzufügen“ unter beziehungsweise über der Kostentabelle.
- **Ist:** Zusätzliche Kosten können nur auf der separaten Kostenseite erfasst werden; persönliche
  Lokara-E-Mail-Adressen und produktives E-Mail-Parsing existieren im aktuellen Repo nicht.
- **Soll:** „Kosten hinzufügen“ öffnet innerhalb des Abrechnungsprozesses denselben fachlichen
  Erfassungsvertrag wie `03_Kosten`, ohne eine zweite Kostenlogik zu bauen. Beim ersten Aufruf im
  Entwurf einmalig einen Hinweis zeigen, dass vorbereitete Kosten unter „Kosten“ schneller und sicherer
  sind. Den zukünftigen E-Mail-Eingang ehrlich ankündigen, aber inaktiv lassen. Danach darf der Nutzer
  fortfahren oder zur Kostenseite wechseln.
- **Default:** Hinweistext: „Kosten lassen sich schneller und sicherer vorbereiten, wenn Sie sie vorab
  unter ‚Kosten‘ erfassen. Künftig können Belege außerdem über eine persönliche Lokara-E-Mail-Adresse
  automatisch Ihrem Konto zugeordnet werden.“ Aktionen „Trotzdem hier hinzufügen“ und „Zu Kosten“.
  Hinweis pro Entwurf nur einmal; kein globales dauerhaftes Wegklicken nötig. Ergänzte Kosten werden als
  echte `CostEntry` mit Herkunft „manuell im Abrechnungsprozess“ angelegt und anschließend referenziert.
- **Erwartetes Ergebnis:** Spontane Nachträge blockieren den Prozess nicht, aber Lokara lenkt freundlich
  zum skalierbaren Kostenworkflow. Keine Scheinfunktion suggeriert bereits aktiven E-Mail-Empfang.
- **Akzeptanz:** Erstes Hinzufügen zeigt den Hinweis, zweites nicht erneut. „Trotzdem“ öffnet die echte
  Kostenerfassung; die neue Position erscheint in der Tabelle. Es gibt keine generierte Empfangsadresse,
  keinen Mail-Request und keine automatische Parsing-Behauptung.
- **Nicht tun:** Persönliche E-Mail-Adresse erfinden; E-Mail-Parsing oder Lieferantenintegration in
  diesem Spec bauen; einen parallelen vereinfachten Kosten-Datentyp nur für Abrechnungen einführen.

### [R11] Eigen- und Fremd-Heizkosten eindeutig in den Prozess integrieren

- **Datei/Ort:** Kosten-/Prüfschritt, Statement-Service, Heating-/MDL-Verträge und Abhängigkeiten aus
  `04_Zaehler` [Z11]–[Z13].
- **Fundstelle:** Die heutige Ergebnisansicht entscheidet bereits anhand `heatingPath` zwischen
  `SELF_BILLING`, `MDL_NET` und `MDL_GROSS`; der vorbereitende Wizard macht die Quelle nicht sichtbar.
- **Ist:** Externe bestätigte MDL-Werte können technisch durchgereicht werden, aber ein verständlicher
  Nutzerworkflow und eine klare Modusprüfung fehlen. Eigene Heizkosten hängen an vollständigen
  Heizkosten- und Zählerdaten.
- **Soll:** Im Kosten-Schritt einen eigenen Abschnitt „Heiz- und Warmwasserkosten“ zeigen. Für Objekt
  und Zeitraum exakt den Backend-Modus „Mit Lokara berechnen“ oder „Messdienstleister-Abrechnung
  übernehmen“ anzeigen. Beim Lokara-Pfad Kostenpositionen, Zähler-/Ablesestatus, Grund-/Verbrauchsanteil,
  Warmwasser- und CO₂-Eingaben prüfen. Beim externen Pfad Anbieter, Version, Zeitraum, Status,
  bestätigte Parteienbeträge und Quelle zeigen; nur `CONFIRMED/UEBERNOMMEN` fließt ein. Neben der
  manuellen externen Übernahme den inaktiven OCR-Ausblick aus `04_Zaehler` wiederverwenden.
- **Default:** Blockertext bei unbestätigtem externen Ergebnis: „Die Abrechnung des Messdienstleisters
  ist noch nicht vollständig geprüft und bestätigt.“ OCR-Hinweis: „Laden Sie künftig die Abrechnung
  Ihres Messdienstleisters hoch. Lokara liest die Angaben dann zur Prüfung vor. Bis dahin übernehmen
  Sie die bestätigten Werte manuell.“ Badge „Bald verfügbar“, kein Dateifeld.
- **Erwartetes Ergebnis:** Der Nutzer erkennt Quelle und Reife des Heizkostenergebnisses. Lokara
  rechnet bestätigte MDL-Beträge nicht neu und verwendet nie gleichzeitig Eigen- und Fremdergebnis.
- **Akzeptanz:** Für jeden Zeitraum existiert höchstens ein maßgeblicher Heizkostenpfad. Ein
  unbestätigter MDL-Datensatz blockiert, ein bestätigter wird unverändert projiziert. OCR ist sichtbar,
  deaktiviert und erzeugt keinen Upload-/Netzwerkaufruf.
- **Nicht tun:** Messdienstleister als Zählertyp modellieren; externe Werte ungeprüft übernehmen;
  §§-Spalten für MDL-Beträge erfinden; eigene und externe Heizkosten addieren.

### [R12] Prüfung, Salden und neue Vorauszahlungsvorschläge zusammenführen

- **Datei/Ort:** Schritt „Prüfung & Vorauszahlungen“, Statement-Projektion, Advance-Reconciliation-
  APIs und eine neue reine Backend-Berechnung für Vorauszahlungsvorschläge mit versioniertem Vertrag.
- **Fundstelle:** Heute prüft `TenantSaldoPreview` genau ein Mietverhältnis, erfasst Beträge in Cent und
  zeigt den Saldo erst nach Bestätigung. Die Nutzererwartung ist eine Gesamtprüfung aller Parteien.
- **Ist:** Der Prozess ist technisch, langsam und fehleranfällig. Es gibt keinen strukturierten Vorschlag
  für die nächste monatliche Vorauszahlung und keine Gesamtübersicht über alle Salden.
- **Soll:** Zuerst eine Objektzusammenfassung mit Betriebskosten, Heizkosten, CO₂-Vermieteranteil,
  nicht umlagefähigen Kosten, umlagefähiger Summe, Eigentümer-/Leerstandsanteil und Kontrollsummen
  zeigen. Darunter eine vollbreite Tabelle je Mietverhältnis mit Einheit, Partei, bisherigem monatlichem
  Soll, bestätigten Ist-Vorauszahlungen, Kostenanteil, Saldo, Backend-Vorschlag für die neue monatliche
  Vorauszahlung, editierbarem gewählten Betrag und „Übernehmen“. Vorschlag, Rundung, Referenzperiode,
  Wirksamkeitsvoraussetzungen und Provenienz kommen vollständig aus einer freigegebenen Backend-Regel.
- **Default:** Saldo als „Nachzahlung“, „Guthaben“ oder „Ausgeglichen“ mit Betrag und Text. Eurofelder
  statt Centfelder. Vorschlag wird angezeigt, aber nie automatisch übernommen; Switch „Vorschlag
  übernehmen“ standardmäßig aus. Ein manueller Betrag speichert eine Entwurfsentscheidung, ändert noch
  keinen Mietvertrag und keine `AdvancePaymentPeriod`. Kontrollsummen als eigener Backend-Status.
- **⚠️ MUSS-INPUT:** Die fachlich und rechtlich freigegebene Berechnung des neuen monatlichen
  Vorauszahlungsvorschlags einschließlich verwendeter Kostenbasis, Prognosezeitraum, Rundung,
  Mindeständerung, Umgang mit Heizkosten/CO₂, Wirksamkeitsdatum und erforderlichem Erklärungstext.
  Solange diese Freigabe fehlt, nur vorhandene Salden zeigen; Vorschlagsspalten und Übernahmefunktion
  überspringen und in Build-Notes dokumentieren.
- **Erwartetes Ergebnis:** Der Vermieter prüft das gesamte Objekt in einer Ansicht. Kein Mietverhältnis
  wird versehentlich ausgelassen. Ein Vorschlag ist nachvollziehbares Werkzeug, keine automatische
  Vertragsänderung.
- **Akzeptanz:** Alle betroffenen Mietverhältnisse erscheinen. Kostenanteil minus bestätigte
  Ist-Vorauszahlung stimmt centgenau mit dem Backend-Saldo überein. Ohne bestätigte Abstimmung wird kein
  Saldo geschätzt. Ohne MUSS-INPUT existiert keine erfundene Vorschlagsformel.
- **Nicht tun:** Jahreskosten pauschal durch zwölf teilen; vertragliches Soll als Ist verwenden;
  Vorschlag automatisch aktivieren; neue Vorauszahlung ohne gesonderte Erklärung persistent wirksam
  machen.

### [R13] Fachliche Blocker und Fristen vor der Finalisierung zentral prüfen

- **Datei/Ort:** Readiness-/Guard-Orchestrierung [R8], `packages/guard-engine`, Statement-
  Finalisierungsservice/-Router und Prüfungs-UI.
- **Fundstelle:** Heute berechnet der Finalisierungsrouter verspätete positive Nachforderungen separat
  über `date.today()` und Jahresersetzung; der vorhandene Frist-Guard hat keinen UI-/Finalisierungs-
  Consumer. Das Feld „Ausnahmegrund“ ist immer sichtbar.
- **Ist:** Friststatus kann zwischen Guard, UI und Finalisierung abweichen. Ein Schaltjahr-Randfall und
  ein frei eingegebener Ausnahmegrund werden nicht als gemeinsamer fachlicher Vertrag behandelt.
- **Soll:** Statement-Frist einmal im Guard/Backend auswerten und denselben strukturierten Status in
  Wizard und Finalisierung verwenden. Vor Abschluss alle Blocker aus [R8] erneut serverseitig gegen
  aktuellen Datenstand prüfen. Verspätete positive Nachforderung klar von Archivierung, Guthaben und
  Zustellung trennen. Ein Ausnahmegrund erscheint ausschließlich, wenn der Backend-Status ihn zulässt
  und verlangt; er bestätigt nicht automatisch die rechtliche Berechtigung.
- **Default:** Bei abgelaufener Regelfrist Warn-/Blockertext aus dem Guard. Guthaben und rechnerischer
  Saldo bleiben sichtbar. Ohne freigegebenen Ausnahmegrund wird eine positive Forderung nicht als
  durchsetzbare Zahlungsforderung/Settlement erzeugt, während eine technisch zulässige Archivierung
  eindeutig als solche bezeichnet wird. Kalenderarithmetik nutzt die gemeinsame getestete Funktion,
  einschließlich 29. Februar.
- **⚠️ MUSS-INPUT:** Zulässige strukturierte Ausnahmegründe, erforderliche Nachweise und die fachliche
  Entscheidung, ob Lokara nur dokumentiert oder die Ausnahme serverseitig freigeben darf. Bis dahin
  kein frei erfundener Katalog und keine UI-Aussage „Ausnahme bestätigt“.
- **Erwartetes Ergebnis:** Der Nutzer versteht, ob das Dokument berechnet, finalisiert und/oder eine
  Nachforderung erzeugt werden darf. Dieselbe Entscheidung gilt in UI, Archiv und Ledger.
- **Akzeptanz:** Guard- und Finalisierungsstatus stimmen für normale, verspätete und Schaltjahrfälle
  überein. Das Frontend enthält keine Fristarithmetik. Zwischen Datencheck und POST geänderte Daten
  werden beim Abschluss erneut geprüft und können Finalisierung atomar verhindern.
- **Nicht tun:** Zwölfmonatsfrist oder Ausnahme im Frontend berechnen; Freitext als Rechtsnachweis
  behandeln; Guthaben wegen verspäteter Nachforderung unterdrücken; technische Archivierung als
  erfolgreiche Zustellung darstellen.

### [R14] Dokumentvorschau vor Abschluss bereitstellen

- **Datei/Ort:** Schritt „Dokumente & Versand“, bestehende Statement-Projektionen, neue
  entwurfsbezogene Vorschauendpoints und PDF-/HTML-Renderer unter `packages/pdf`.
- **Fundstelle:** Heute lädt „PDF herunterladen“ direkt die Live-Vermieterübersicht. Eine klare
  Vorschau von Anschreiben und allen Mieter-Einzelabrechnungen vor Finalisierung fehlt.
- **Ist:** Der Nutzer kann Dokumente nicht als zusammengehöriges Paket prüfen. Live-Vermieterübersicht,
  technische Mieterarchive und spätere Zustellung sind begrifflich vermischt.
- **Soll:** Vor Finalisierung eine Dokumentliste anzeigen: Anschreiben und Einzelabrechnung je
  Mietverhältnis, Vermieterübersicht sowie fachlich notwendige Anlagen. Jede Vorschau wird strikt für
  ihre Zielgruppe projiziert und darf keine Daten anderer Mieter enthalten. Vorschau trägt sichtbar
  „Entwurf – nicht versendet“ und wird nicht als Archivbyte behandelt. Nach Änderungen wird sie aus dem
  aktuellen Entwurf neu erzeugt.
- **Default:** Dokumentzeile mit Empfänger/Einheit, Dokumenttyp, Readiness und Aktion „Vorschau“.
  Vorschau in eigener Route/Ansicht mit „Zurück zur Prüfung“, nicht in einem winzigen Modal. Download
  einer Entwurfsvorschau optional mit sichtbarem Entwurfskennzeichen. Primäre Aktion erst „Abrechnung
  finalisieren“; Versand folgt danach in [R17].
- **Erwartetes Ergebnis:** Der Vermieter kann genau die Dokumente prüfen, die später eingefroren werden.
  Eigentümerdaten und andere Parteien erscheinen nie in einer Mieter-Einzelabrechnung.
- **Akzeptanz:** Für N berechtigte Mietverhältnisse existieren N getrennte Einzelvorschauen plus
  Anschreiben; keine Vorschau enthält fremde Mieteridentität oder Salden. Änderungen invalidieren die
  alte Vorschau sichtbar.
- **Nicht tun:** Ein Gesamt-PDF erzeugen und Seiten clientseitig verstecken; Vorschau als finalisiert
  kennzeichnen; Live-PDF pauschal „Mieterabrechnung“ nennen.

### [R15] Anschreiben im freigegebenen schlichten A4-Layout erzeugen

- **Datei/Ort:** Anschreiben-Renderer unter `packages/pdf`, finaler Snapshot-/Dokumentvertrag und
  PDF-Tests. Visuelle Referenz:
  `/Users/berkaybayrak/Documents/Immo/Auf dem Troppenbruch 2, 52146 Würselen/2025 Abrechnung/Einzelabrechnungen/Anschreiben_MB.pdf`.
- **Fundstelle:** Neues beziehungsweise bisher nicht als freigegebene Dokumentfamilie umgesetztes
  Anschreiben vor jeder Mieter-Einzelabrechnung.
- **Ist:** Die technische Finalisierung erzeugt Mieter-PDFs, aber das vom Nutzer freigegebene nüchterne
  Anschreiben-Layout ist noch kein verbindlicher Renderer-Vertrag.
- **Soll:** Ein separates A4-Anschreiben je Mietverhältnis im Layout der Referenz erzeugen: kleine
  Absenderzeile, Empfängeranschrift, rechts Ort/Datum, kräftiger Betreff, Anrede, kurzer Ergebnistext,
  Zahlungs-/Guthabenhinweis, Aufbewahrungs-/Rückfrageabsatz, Grußformel, Absendername, Anlagenvermerk und
  Seitenzahl. Weißer Hintergrund, schwarze/dunkelgraue Schrift, keine Karten, Farbflächen, Verläufe,
  Logos oder dekorative Elemente. Wortlaut wird aus strukturierten Saldo- und Hinweiszweigen gebaut.
- **Default:** Eigenständiges Dokument; A4 Hochformat; großzügige drucktaugliche Ränder; eine ruhige
  Sans-Serif-Schrift aus dem vorhandenen PDF-Fontbestand; fett nur Betreff und notwendige Hervorhebung.
  Ergebniszweige „Nachzahlung“, „Guthaben“ und „ausgeglichen“; Fälligkeit ausschließlich als
  Backend-Feld anzeigen, nie aus Erstellungsdatum ableiten. Anlagenname „Betriebs- und
  Heizkostenabrechnung {Jahr}“ beziehungsweise fachlich passender Titel.
- **⚠️ MUSS-INPUT:** Rechtlich/fachlich freigegebene Textbausteine für Fälligkeit, Nachzahlung,
  Guthabenauszahlung, Aufbewahrung, Beratungsausschluss und gegebenenfalls neue Vorauszahlung. Bis zur
  Lieferung keine Sätze aus der Musterdatei als allgemeingültige Rechtsaussage kopieren; vorhandene
  freigegebene Backend-Hinweise weiterverwenden und fehlende Zweige überspringen.
- **Erwartetes Ergebnis:** Das Anschreiben wirkt wie ein klassischer, seriöser Geschäftsbrief und
  entspricht visuell der Referenz, ohne deren konkrete Namen, Beträge oder potenziell ungeprüfte
  Rechtsformulierungen zu kopieren.
- **Akzeptanz:** Gerenderter Screenshotvergleich bestätigt Struktur, Abstände und Farbreduktion. Name,
  Anschrift, Zeitraum, Saldo, Datum und Anlagenvermerk stammen aus dem finalen Snapshot. Tagged-PDF,
  Sprache, Textsuche und Seitenzahl sind getestet.
- **Nicht tun:** Referenz-PDF einbetten oder pixelgenau als Bild kopieren; konkrete Musterpersonen oder
  -beträge übernehmen; Fälligkeit erfinden; Marketingfarbe, Diagramm oder App-Kartenstil verwenden.

### [R16] Einzelabrechnung und eigene Heizkostenanlage als konsistente Dokumentfamilie rendern

- **Datei/Ort:** Statement-/Heating-Renderer unter `packages/pdf`, finale Snapshot-Verträge und
  PDF-Golden-/Layouttests. Visuelle Referenz:
  `/Users/berkaybayrak/Documents/Immo/Auf dem Troppenbruch 2, 52146 Würselen/2025 Abrechnung/Einzelabrechnungen/Kalkulation_MB.pdf`.
- **Fundstelle:** Bestehende Vermieter-/Mieter-Renderer und die freigegebene Beispiel-
  Einzelabrechnung. Das Diagramm der Referenz ist ausdrücklich keine Pflicht.
- **Ist:** Lokara besitzt fachlich umfangreiche PDF-Projektionen, aber die gewünschte einheitliche,
  farbarme Dokumentgestaltung und der konsistente Eigen-Heizkostenanhang sind noch nicht als dieser
  Zielvertrag beschrieben.
- **Soll:** Die Mieter-Einzelabrechnung als nüchterne A4-Dokumentfamilie gestalten: Titel,
  Abrechnungsjahr/-zeitraum, Einheit, Mieter, umlagefähige Kosten, bestätigte Vorauszahlungen,
  Nachzahlung/Guthaben, anschließend eine große Kostentabelle mit Kostenart, Umlageschlüssel,
  Gesamtkosten und Anteil der Einheit sowie klarer Summenzeile. Weiß, schwarz/dunkelgrau, horizontale
  Trennlinien, großzügige Ränder, keine Karten oder dekorativen Flächen. Bei Lokara-Eigenberechnung
  folgen im exakt gleichen Layout die notwendigen Heizkostenseiten mit Gesamt-/umlagefähigen Kosten,
  Grund- und Verbrauchsblöcken, angewendetem Verhältnis, Gesamtbemessungen, Nutzerwechseln,
  Schätzgrundlagen, Geräte-/Ablesedaten, Warmwasserabtrennung, CO₂-Kosten/Vermieterabzug,
  Kontrollsummen, Provenienz und Rechtsständen. MDL-Dokumente zeigen nur bestätigte übernommene Werte
  und deren Quelle, keine erfundene §§-Aufteilung.
- **Default:** Kein Diagramm. Farbe höchstens äußerst sparsam für den finalen Saldo und nur zusätzlich
  zu Text; vorzugsweise vollständig monochrom. Mehrseitige Tabellen wiederholen Kopfzeilen und trennen
  keine Überschrift von der ersten Zeile. Seitenzahl „Seite X von Y“. Kosten mit `0,00 €` nur zeigen,
  wenn sie fachlich/dokumentarisch erforderlich sind; keine leeren Katalogzeilen. Eigentümerresiduum,
  Leerstandsaufstellung und interne Findings gehören nicht in fremde Mieter-Einzelabrechnungen.
- **Erwartetes Ergebnis:** Betriebskosten- und selbst erstellte Heizkostenabrechnung wirken wie ein
  zusammengehöriges, seriöses Dokument. Rechtlich notwendige Details dürfen zusätzliche Seiten
  erzeugen, ohne in einen anderen visuellen Stil zu wechseln.
- **Akzeptanz:** PDF-Tests prüfen Zielgruppentrennung, Pflichtblöcke, Summen, Rechtsstände, wiederholte
  Tabellenköpfe, Seitenzahlen, Suchtext und Tagged-Struktur. Renderprüfung zeigt keine abgeschnittenen
  Zeilen, Überlagerungen, unnötige Farbe oder Pflichtdiagramme. Bestehende fachliche Goldens bleiben
  centgenau unverändert, sofern kein gesondert freigegebener Rechenspec sie ändert.
- **Nicht tun:** Kreis-/Balkendiagramm als Pflicht bauen; Musterbeträge übernehmen; rechtliche
  Heizkostenangaben im Renderer neu berechnen; MDL-Werte in eine Eigenberechnung umformen; vertrauliche
  Daten anderer Parteien drucken.

### [R17] Finalisierung, Versandkanäle und Archivstatus ehrlich trennen

- **Datei/Ort:** Dokument-/Versandschritt, Finalisierungsrouter/-service, Statement-/Archive-Modelle,
  neue Delivery-Modelle/Adapter erst bei tatsächlicher Implementierung und Listenstatus aus [R1].
- **Fundstelle:** Heute heißt die Aktion „Finalisieren und archivieren“ und versendet nichts. Die
  gewünschte Zielaktion lautet langfristig „Abschließen und versenden“ über Portal, E-Mail oder PDF/Post.
- **Ist:** Immutable Finalisierung und PDF-Archive existieren. Mieterportal-/Nachrichtenversand,
  E-Mail-Zustellung und rechtssicherer Zustellnachweis sind im aktuellen Scope nicht vorhanden.
- **Soll:** Finalisierung und Zustellung als zwei nachvollziehbare Aktionen modellieren. Zuerst
  „Abrechnung finalisieren“: Readiness erneut prüfen, Snapshot und alle PDFs atomar erzeugen, archivieren
  und Version festschreiben. Danach Versandkanäle pro Empfänger anbieten: Mieterportal, E-Mail oder
  „PDF herunterladen / postalisch selbst versenden“. Portal/E-Mail nur aktivieren, wenn echte Adapter,
  Einwilligung/Adresse, Statuspersistenz, Fehlerbehandlung und Tests vorhanden sind. Bei mehreren
  Kanälen zeigt die Liste getrennte Delivery-Zustände.
- **Default:** Ohne produktive Zustellintegration ist nur „PDFs herunterladen“ aktiv; Portal und
  E-Mail tragen „Bald verfügbar“. Kombinierter Button „Abschließen und versenden“ erscheint erst, wenn
  ein funktionsfähiger Versandkanal ausgewählt ist; sonst „Abrechnung finalisieren“. Versandstatus
  `NOT_SENT | QUEUED | SENT | DELIVERED | FAILED | MANUAL_POST`; `MANUAL_POST` bedeutet nur vom
  Vermieter als selbst versendet markiert, nicht technisch nachgewiesen. Fehlversand ändert die
  finalisierte Abrechnung nicht.
- **⚠️ MUSS-INPUT:** Freigegebene Zustellwege, Einwilligungs-/Adressvoraussetzungen, rechtlich
  maßgebliches Zustelldatum, Nachweis-/Aufbewahrungsumfang, Portal- und E-Mail-Text sowie die Frage, ob
  und wann Lokara den Postweg empfehlen darf. Bis dahin keine pauschale Aussage „postalischer Versand
  ist sicherer“ und keine Zustellung behaupten.
- **Erwartetes Ergebnis:** Der Nutzer kann Dokumente sicher finalisieren und heute herunterladen. Später
  kann Lokara echte Zustellungen ergänzen, ohne Finalisierung und Übermittlung begrifflich zu vermischen.
  Nach Abschluss steht die Abrechnung sofort in der Liste mit Version, Dokumenten und ehrlichem Status.
- **Akzeptanz:** Finalisierung erzeugt alle Bytes oder keine. Ein Versandfehler löscht/ändert kein
  Archiv. Liste und Detailansicht unterscheiden `FINALIZED` von `SENT/DELIVERED`. In der aktuellen
  technischen Lage lösen Portal-/E-Mail-Elemente keinen Request aus.
- **Nicht tun:** Finalisierung automatisch als Zustellung markieren; Versandstatus nur im Client
  halten; Portal/E-Mail simulieren; postalische Rechtsbehauptung erfinden; endgültige PDFs nach Versand
  neu berechnen.

### [R18] Korrekturen und Archivdetail nachvollziehbar machen

- **Datei/Ort:** Neue Detailroute für eine Abrechnung, beispielsweise
  `/a/[accountId]/abrechnung/[statementId]`, Statement-History-/Document-APIs und Liste [R1].
- **Fundstelle:** Heute zeigt der untere Block „Archivhistorie“ nur Version, Status und Downloadlinks;
  Korrektur verlangt eine technische Auswahl der jüngsten Version.
- **Ist:** Archiv und Korrektur sind schwer verständlich. Es gibt keine zusammenhängende Detailansicht
  mit Ergebnis, Dokumenten, Versand und Versionskette.
- **Soll:** Für finalisierte Abrechnungen eine Detailansicht mit Titel, Objekt, Zeitraum, Version,
  Erstellzeitpunkt, Ergebniszusammenfassung, Dokumenten je Empfänger, Hash-/Archivstatus in
  nutzerverständlicher Form, Versandstatus und vollständiger Versionshistorie bauen. Aktion „Korrektur
  erstellen“ legt einen neuen Entwurf an, referenziert automatisch die jüngste finalisierte Version und
  erklärt, dass die alte Fassung unverändert bleibt. Finalisierung der Korrektur setzt die jüngste
  Version auf `SUPERSEDED/KORRIGIERT` und erzeugt neue Dokumente.
- **Default:** Keine technische Selectbox zur Wahl des Vorgängers. Nur die jüngste finalisierte Version
  kann korrigiert werden. Alte Dokumente bleiben downloadbar und tragen ihren Status. Korrekturgrund als
  Pflichttext im Entwurf; konkrete Kommunikations-/Zustellwirkung bleibt [R17].
- **Erwartetes Ergebnis:** Jede Änderung ist als neue Version nachvollziehbar. Nutzer erkennen sofort,
  welches Dokument aktuell ist und welche Fassung ersetzt wurde.
- **Akzeptanz:** Version 2 referenziert Version 1; Version 1 bleibt unverändert und sichtbar. Direkte
  Korrektur einer älteren als der jüngsten Fassung wird serverseitig abgelehnt. Dokumente und
  Versandereignisse bleiben ihrer Version zugeordnet.
- **Nicht tun:** Finale Zeile zurück in Bearbeitung setzen; Vorgängerbytes ersetzen; ältere Versionen
  verstecken oder löschen; Korrektur ohne Grund beziehungsweise Versionsbezug erlauben.

### [R19] Lade-, Leer-, Fehler-, Erfolg- und Berechtigungszustände vereinheitlichen

- **Datei/Ort:** Abrechnungsliste, Einstieg, alle Wizard-Schritte, Vorschau, Finalisierung, Detail- und
  Archivansicht.
- **Fundstelle:** Heute bestehen zwei generische Mint-Skeletons und Fehlertexte wie „Bitte API und
  Datenbank prüfen“. Erfolgs- und Wiederaufnahmezustände sind kaum ausgearbeitet.
- **Ist:** Zustände nennen weder betroffenen Bereich noch konkrete Korrektur. Ladeflächen bilden die
  spätere Struktur nicht ab; Fokus bleibt nach Fehlern unbestimmt.
- **Soll:** Für jeden Bereich strukturgetreue Ladezustände, positive Leerzustände, konkrete
  Backend-Fehler, Autospeicherstatus, Konfliktzustand, Abschlussbestätigung und Berechtigungsansicht
  definieren. Fehler zeigen Handlung und Korrekturroute. Nach finaler Aktion eine Erfolgsansicht mit
  Version, Dokumentanzahl, Salden-/Forderungsstatus und Aktionen „Zur Abrechnung“, „PDFs herunterladen“
  und „Zur Liste“.
- **Default:** Liste ohne Daten: „Noch keine Abrechnung“. Objekt ohne abrechenbare Daten: konkrete
  Readiness-Punkte statt Demo-404. Ladecopy je Schritt, beispielsweise „Kosten werden geprüft…“.
  Autospeicherfehler blockiert Schrittwechsel nicht sofort, aber Finalisierung, bis gespeichert.
  HTTP 409 zeigt „Der Entwurf wurde an anderer Stelle geändert“ mit „Aktuelle Fassung laden“; keine
  automatische Überschreibung. Nicht-Owner dürfen vorhandene freigegebene Ansichten nach Rollenvertrag
  sehen, aber keine Entwürfe finalisieren oder versenden.
- **Erwartetes Ergebnis:** Kein nutzerseitiger Text fordert auf, API oder Datenbank zu prüfen. Jeder
  Fehler ist verständlich, fokussierbar und nach Möglichkeit direkt lösbar.
- **Akzeptanz:** Manuelle Prüfung deckt leeres Konto, fehlende Einheiten, Ladefehler, 409, 422-Blocker,
  Autospeicherfehler, erfolgreiche Finalisierung, Versandfehler und fehlendes Schreibrecht ab. Fokus
  landet jeweils auf Statuskopf oder erstem Fehler.
- **Nicht tun:** Stacktraces oder technische Exceptiontexte zeigen; Fehler nur toast-basiert anzeigen;
  gespeicherte Daten bei Retry leeren; Owner-Schutz nur über versteckte Buttons lösen.

### [R20] Desktop-/Laptop-Tabellen, Tastatur und Fokus absichern

- **Datei/Ort:** Fortschrittsleiste, Einheiten-, Kosten-, Saldo- und Dokumenttabellen sowie feste
  Wizard-Aktionsleiste.
- **Fundstelle:** Immocloud-Referenzen zeigen sehr breite Tabellen; die heutige Lokara-Heizkostentabelle
  besitzt ebenfalls viele Spalten.
- **Ist:** Breite Tabellen und reine Symbolaktionen sind auf kleineren Laptops schwer bedienbar; der
  lange Screen besitzt keine systematische Fokusführung.
- **Soll:** Desktop und Laptop verwenden große, saubere Tabellen. Einzelne Datentabellen dürfen auf
  1280 Pixel kontrolliert innerhalb ihrer Fläche scrollen, die Gesamtseite nicht. Aktionen erhalten
  Textlabels oder zugängliche Namen. Sticky-Fußleiste darf keine letzte Zeile verdecken.
  Schrittwechsel, Fehler, Korrekturrückkehr und Abschluss setzen Fokus sinnvoll.
- **Default:** Pre-Pitch-Breiten 1280, 1440 und 1920 Pixel. Geld rechtsbündig und `tabular-nums`;
  Labels in Manrope, Beträge und
  Kennzahlen in Montserrat. Kein animiertes Scrollen bei `prefers-reduced-motion`. Escape führt nicht
  ohne Bestätigung aus einem ungespeicherten Entwurf.
- **Erwartetes Ergebnis:** Der vollständige Prozess ist auf Laptop und Desktop ohne Datenverlust,
  Mauszwang oder abgeschnittene Inhalte nutzbar. Das UI bleibt visuell konsistent mit
  Dashboard, Objekte, Kosten und Zähler.
- **Akzeptanz:** Tastatur erreicht jede Zeile, Aktion und jeden Schritt in logischer Reihenfolge.
  Screenreader erhalten Tabellenlabels, Status und Fehlzuordnung. Bei 1280 Pixel und 200-Prozent-Zoom
  bleibt die Abschlussaktion erreichbar.
- **Nicht tun:** Smartphone-/Tablet-Karten oder Touchnavigation Pre-Pitch bauen; Aktionen nur als
  unbeschriftete Icons bauen; Fokusoutline entfernen; ein neues Komponenten-/Iconpaket nur für diesen
  Wizard installieren.

### [R21] Verträge, Migrationen und Tests als Abnahmeschutz ergänzen

- **Datei/Ort:** Neue/angepasste Tests in Web, API, DB, Engines und PDF-Package; Golden-Fixtures gemäß
  Repo-Prozess; Demo- und PDF-Gates.
- **Fundstelle:** Vorhandene Statement-, Finalization-, NK-, Heating- und PDF-Tests sowie der aktuell
  grüne reine Engine-/PDF-Bestand. Der lokale Demo-Lauf kann derzeit generisch fehlschlagen und braucht
  eine reproduzierbare Abdeckung.
- **Ist:** Einzelne fachliche Bausteine sind gut getestet, aber Liste, Entwurf, Wizard-Readiness,
  Wiederaufnahme, Kostenprüfung, Gesamt-Vorauszahlungsprüfung, Dokumentvorschau und Zustellgrenzen sind
  nicht als zusammenhängender Nutzerpfad abgesichert.
- **Soll:** Tests für Draft-Lifecycle, RLS, Konflikte, jeden Wizard-Schritt, Readiness-Codes,
  Mieterwechsel, Leerstand, Eigennutzung, mietfreie Nutzung, Kostenklassifizierung, Schlüsselversion,
  fehlende Ablesungen, Schätzung, Eigen-/MDL-Pfad, CO₂, Ist-Vorauszahlungen, Salden, Frist, 29. Februar,
  Korrekturversion, Vorschauisolierung, atomare Finalisierung, Dokumentlayout und Versandgrenzen
  ergänzen. Den Demo-Pfad Objekt → Entwurf → Prüfung → Finalisierung → Liste reproduzierbar machen.
- **Default:** Frontendtests beweisen Fortschritt, Autospeichern, große Tabellen, Fokus und inaktive
  Zukunftsfunktionen. API-/DB-Tests beweisen Account-/Gebäudegrenzen, immutable Finalisierung und
  Versionsketten. PDF-Goldens verwenden anonymisierte Fixtures und prüfen Anschreiben,
  Einzelabrechnung, Eigenheizkosten und MDL-Pass-through. Vor und nach PDF-Änderungen Fingerprint
  dokumentieren; erwartete Änderung durch neue Layoutgoldens ausdrücklich freigeben.
- **Erwartetes Ergebnis:** Der vollständige Prozess ist fachlich und visuell regressionsgeschützt.
  Keine neue UI-Regel kann Engine-/Backendwerte überstimmen.
- **Akzeptanz:** Fast-/Full-/Demo-Gates laufen grün; Web-Typprüfung/Lint grün; RLS-/FK-Prüfungen grün;
  PDF-Renderprüfung ohne Überlagerung oder abgeschnittene Inhalte. Tests beweisen, dass Portal, E-Mail,
  OCR und E-Mail-Belegimport ohne echte Integration keinen Request auslösen.
- **Nicht tun:** Bestehende Goldenbeträge an neue UI-Erwartungen anpassen; echte personenbezogene Daten
  der Referenz-PDFs in Fixtures übernehmen; Netzwerke zu E-Mail/OCR/Messdienstleister in Tests nutzen;
  fehlschlagende Gates abschalten.

## Out of Scope

- Umsetzung eines produktiven Mieterportals, Nachrichtenversands oder E-Mail-Zustelladapters; dieser
  Spec definiert nur ehrliche UI-/Statusgrenzen und die spätere Anschlussstelle.
- Persönliche Lokara-E-Mail-Adressen, Postfachbetrieb, Lieferanten-Onboarding und produktives
  E-Mail-Parsing. Im Wizard nur der inaktive Zukunftshinweis aus [R10].
- Funktionsfähige OCR, Dokumentupload, Dateispeicher, Virenprüfung und automatische Extraktion externer
  Heizkostenabrechnungen. Nur der inaktive Ausblick aus `04_Zaehler`/[R11].
- Erfindung oder Änderung von NK-, Heizkosten-, CO₂-, Frist-, Schätz-, Rundungs- oder
  Vorauszahlungslogik. Fachliche Änderungen benötigen eigenen freigegebenen Rechen-/Rechtsspec und
  Golden-Fixtures.
- Rechtsfreigabe der aktuell als `verify-before-production` beziehungsweise produktionsgesperrt
  markierten Werte und Page-02-Positionen.
- Automatische Vertragsänderung einer neuen Vorauszahlung oder Erstellung des dazugehörigen
  rechtlichen Erhöhungsschreibens ohne den MUSS-INPUT aus [R12]/[R15].
- Verbindliche Behauptung, postalischer Versand sei generell erforderlich oder sicherer, solange der
  MUSS-INPUT aus [R17] fehlt.
- Ein Pflichtdiagramm in der PDF. Diagramme sind ausdrücklich optional und standardmäßig nicht
  Bestandteil der Abrechnung.
- Änderungen an Dashboard-, Objekt-, Kosten- oder Zähler-Informationsarchitektur außerhalb der hier
  benannten Verknüpfungs-/Korrekturziele.

## Verifikation

1. `/abrechnung` zeigt eine vollbreite Liste mit Status, Zeitraum, Ergebnis und Kopfaktion; ein leeres
   Konto zeigt den positiven Leerzustand.
2. „Abrechnung erstellen“ führt über Objekt und Zeitraum zu einem persistenten Entwurf ohne festen
   2025-Default. Verlassen und Wiederaufnahme landen am gespeicherten Schritt.
3. Die sechs Schritte sind auf allen Pre-Pitch-Desktop-/Laptopbreiten sichtbar; Fokus, Tastatur und
   Blockerzustände funktionieren.
4. Grundlagen zeigen Titel, vollständigen Einheitenumfang und getrennte Zeitabschnitte für Mieter,
   Leerstand, Eigennutzung und mietfreie Nutzung.
5. Absender-/Kontokorrektur nur im Entwurf verändert keine Stammdaten; bewusstes Speichern erzeugt eine
   neue Version.
6. Einheiten-/Miettabelle zeigt Nutzungszeitraum, Ø Personenzahl, Fläche, Soll- und bestätigte
   Ist-Vorauszahlungen; ein Mieterwechsel erscheint in mehreren Zeilen.
7. Kostentabelle übernimmt alle wirksamen Lokara-Kosten genau einmal. Schlüsseländerung ist versioniert,
   Nachtrag funktioniert und der einmalige E-Mail-Zukunftshinweis erzeugt keine Scheinfunktion.
8. Eigen- und Fremd-Heizkosten sind exklusiv. Fehlende Ablesungen beziehungsweise unbestätigte MDL-Werte
   blockieren über Backend-Findings; OCR bleibt sichtbar und inaktiv.
9. Prüfung zeigt centgenaue Objekt- und Parteiwerte. Ohne bestätigte Ist-Abstimmung kein Saldo; ohne
   MUSS-INPUT kein erfundener Vorauszahlungsvorschlag.
10. Friststatus ist in Guard, UI und Finalisierung identisch und deckt normale, verspätete und
    Schaltjahrfälle ab.
11. Vorschau erzeugt getrennte Anschreiben und Einzelabrechnungen ohne fremde Mieterdaten.
12. PDF-Renderprüfung bestätigt das schlichte A4-Layout der Referenzen: weiß, schwarz/dunkelgrau,
    klare Linien und Tabellen, keine Karten, keine Pflichtdiagramme. Die selbst berechnete
    Heizkostenanlage bleibt gestalterisch konsistent.
13. Finalisierung ist atomar und immutable. Danach erscheint die Version sofort in der Liste; ein
    Versandfehler verändert das Archiv nicht. Ohne echte Integration sind nur PDF-Download und
    manueller Poststatus aktiv.
14. Korrektur erzeugt eine neue Version mit Bezug zur jüngsten finalen Fassung; alte Bytes, Hashes,
    Dokumente und Status bleiben sichtbar.
15. Desktop-/Laptop-Ansicht bei 1280, 1440 und 1920 Pixel, WCAG/BFSG, Typprüfung, Lint,
    Web-/API-/DB-/Engine-/PDF-Tests, RLS-/FK-Gates und
    kompletter Demo-Pfad sind grün.

## Reihenfolge

1. [R2], [R8] — Entwurfs- und Readiness-Fundament.
2. [R1], [R3], [R4] — Liste, Einstieg und Wizard-Rahmen.
3. [R5], [R6], [R7] — Grundlagen, Absender/Konto und Mietdaten.
4. [R9], [R10], [R11] — Kosten, Nachträge und Heizkostenpfade.
5. [R12], [R13] — Gesamtprüfung, Salden, Vorschläge und Fristen.
6. [R14], [R15], [R16] — Vorschau und freigegebene Dokumentfamilie.
7. [R17], [R18] — Finalisierung, ehrliche Versandgrenzen, Archiv und Korrektur.
8. [R19], [R20], [R21] — Zustände, Desktop-Accessibility und vollständige Abnahme.

## Build-Notes (füllt die KI beim Umsetzen aus)

<!-- Erwartete Einträge:
- [R2] Exakte Draft-Tabellen-/Versionsstruktur und Konfliktstrategie.
- [R8] Vollständige Readiness-Code-Liste und Korrekturrouten.
- [R10] Bestätigung, dass keine persönliche E-Mail-Adresse und kein Parsing gebaut wurde.
- [R11] Bestätigung, dass OCR inaktiv ist und Eigen-/MDL-Pfade exklusiv bleiben.
- [R12] MUSS-INPUT Vorauszahlungsvorschlag vorhanden oder Teilpunkt übersprungen.
- [R13] MUSS-INPUT Ausnahmegründe vorhanden oder Teilpunkt übersprungen.
- [R15] Freigegebene Anschreiben-Texte vorhanden oder fehlende Zweige übersprungen.
- [R17] Aktive Versandkanäle und offene MUSS-INPUTs; keine Zustellung simuliert.
- [R21] Vorher-/Nachher-PDF-Fingerprint und Ergebnisse der Renderprüfung.
-->
