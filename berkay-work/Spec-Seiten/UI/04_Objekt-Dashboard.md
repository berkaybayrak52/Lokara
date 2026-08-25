---
spec_id: 07-objekt-dashboard
titel: Objekt-Dashboard — Objektakte, KPIs, Aufmerksamkeit, Einheiten und PDF-Übersicht
status: freigegeben
prioritaet: hoch
betrifft: apps/web, apps/api, packages/db, packages/pdf
abhaengig_von: [00-layout-global, 01-dashboard, 02-objekte, 03-kosten, 04-zaehler, 05-abrechnung-erstellen, 06-zahlungen]
repo_stand: Lokara-main @ 2026-08-25
---

## Zweck

Die heutige Objekt-Detailseite wird von einer einfachen Einheitenliste mit dauerhaft sichtbarem
Anlageformular zu einer übersichtlichen Objektakte ausgebaut. Private Vermieter erkennen sofort das
Objekt, seine aktuelle Vermietungs- und Ertragssituation, relevante Hinweise und den Zustand jeder
Einheit. Sämtliche fachlichen Kennzahlen stammen aus autoritativen Backend-Projektionen; das
Frontend erzeugt keine zweite Wahrheit.

## Invarianten (gelten für ALLE Befehle hier)

- Pre-Pitch gilt Desktop/Laptop bei 1280, 1440 und 1920 Pixel sowie 200-Prozent-Zoom. Smartphone-,
  Tablet- und native Varianten sind Post-Pitch; Tastatur, Screenreader und sichtbarer Fokus bleiben
  verpflichtend.

- Nur die vorhandenen Design-Tokens und Hausschriften aus dem UI-Package sowie die Regeln aus
  `00_Layout-Global.md` verwenden. Keine rohe Farbangabe und keine neue isolierte Designsprache
  einführen.
- Die Objektakte ist der Drill-down eines einzelnen Objekts. Portfolioseiten bleiben
  portfolioübergreifend; keinen globalen Objektfilter oder Objektumschalter in App-Shell oder
  Seitenkopf ergänzen.
- Alle Geldbeträge werden serverseitig in Integer-Cents beziehungsweise mit den vorhandenen
  Geldtypen ermittelt und als formatierbare Werte ausgeliefert. Keine Geldberechnung mit
  JavaScript-Floats und keine Prozent-/Demoableitung im Frontend.
- Belegungsstand, Mietpartei, Mietsoll, Saldo, Zahlungsstatus, Readiness, Zählerhinweise und
  Dringlichkeit niemals aus sichtbaren Rohdaten im Browser raten. Die zuständige Backend-Projektion,
  Engine oder der gemeinsame Wächter ist autoritativ.
- Vermietet, echter Leerstand, Eigennutzung und unentgeltliche Überlassung sind verschiedene
  zeitliche Zustände. Ein fehlendes aktives Mietverhältnis ist nicht automatisch Leerstand.
- Ungeklärte Bankumsätze, offene Forderungen, Guthaben und Nachzahlungen bleiben fachlich getrennt.
  Ein positiver Kontoeingang ist nicht automatisch Miete; ein beendetes Mietverhältnis erzeugt nicht
  automatisch eine offene Forderung.
- Hinweise beschreiben Fakten und erlaubte nächste Aktionen. Mahnstufe, Verzug, Zinsen, Gebühren,
  Rechtsfolgen oder künstliche Dringlichkeit werden hier nicht erfunden.
- Das Dashboard bleibt eine kompakte Übersicht mit Drill-downs. Keine vollständigen Kosten-, Bank-,
  Abrechnungs-, Zähler-, Dokument- oder Aktivitätshistorien auf dieser Seite duplizieren.
- Objekt- und Einheitenzugriff bleiben account- und gebäudegescopet. Versteckte UI-Elemente ersetzen
  keine serverseitige Rollen- und Ressourcenprüfung.
- Foto-Upload, Dokument-Storage, Vorgänge/Tickets und Reminder nur aktiv darstellen, wenn die
  zugrunde liegende persistente Funktion tatsächlich vorhanden ist. Bis dahin weglassen oder klar
  als inaktiv beziehungsweise „kommt bald“ kennzeichnen; keine Fake-Zähler und keine klickbare
  Scheinfunktion.
- Der Objektübersichts-PDF ist eine eigene Dokumentart und keine Betriebskostenabrechnung, kein
  Kontoauszug und kein rechtliches Schreiben. Er übernimmt serverseitig bestätigte Snapshotwerte und
  berechnet keine Fachwerte neu.
- Nur die im jeweiligen Befehl benannten Stellen ändern. Bestehende Tests bleiben grün, Typprüfung
  und Lint bleiben sauber.
- Keine bestehende Rechen-, Rechts-, Zahlungs-, Forderungs-, Abrechnungs- oder Zählerlogik verändern,
  sofern ein Befehl dies nicht ausdrücklich und mit autoritativer Quelle verlangt.
- Bei normaler Produktunklarheit den genannten Default umsetzen, nicht anhalten, und die Annahme in
  `## Build-Notes` festhalten.
- `⚠️ MUSS-INPUT` niemals raten. Nur den betroffenen Teil überspringen und in Build-Notes
  dokumentieren; alle übrigen Teile des Befehls trotzdem umsetzen.

## Befehle

### [OD1] Serverseitiges Objekt-Dashboard-Read-Model schaffen

- **Datei/Ort:** Backend unter `apps/api`, vorhandene Gebäude-Router/-Schemas und neue klar
  objektbezogene Projektions-/Service-Stellen; Frontend-Vertrag in `apps/web/src/lib/contracts.ts`
  und Abfrage-Hook im Objekt-Feature.
- **Fundstelle:** Der heutige `GET /a/{accountId}/buildings/{buildingId}`-Vertrag, der nur
  Gebäudestammdaten und je Einheit `id`, `label`, `areaSqm`, `tenancyCount` und `occupiedToday`
  liefert; `useBuildingDetail` in `apps/web/src/features/objekte/queries.ts`.
- **Ist:** Der bestehende Vertrag reicht für die Einheitenliste, kann aber weder die drei
  Belegungszustände noch Mietsoll, Salden, Hinweise, Zähler- oder Abrechnungszustände korrekt
  ausdrücken. Eine clientseitige Zusammensetzung aus mehreren vollständigen Rohlisten wäre langsam,
  fehleranfällig und eine zweite fachliche Wahrheit.
- **Soll:** Einen read-only Objekt-Dashboard-Vertrag bereitstellen, der die für diese Seite
  benötigten Stammdaten, KPI-Werte, priorisierten Fakten, kompakten Modulzusammenfassungen und
  Einheitenzeilen serverseitig zusammensetzt. Der Vertrag besitzt einen expliziten Datenstand
  `asOf`, stabile IDs, fachliche Statusschlüssel, bereits ermittelte Cents-/Flächenwerte und erlaubte
  Aktionen beziehungsweise Drill-down-Ziele. Bestehende Detailverträge dürfen kompatibel erweitert
  oder durch einen eindeutig benannten Dashboard-Endpunkt ergänzt werden; die Entscheidung gegen den
  aktuellen Repo-Stand in Build-Notes festhalten.
- **Default:** Ein dedizierter Objekt-Dashboard-Endpunkt, damit schlanke bestehende Konsumenten des
  Gebäude-Detailvertrags nicht ungefragt alle Finanz- und Modulprojektionen laden. `asOf` entspricht
  dem serverseitigen aktuellen Zeitpunkt beziehungsweise im Demo-Modus dem expliziten `demo_now`.
  Oberhalb von 100 Einheiten liefert der Endpoint weiterhin nur kompakte Einheitenzeilen; Historien
  bleiben paginiert in ihren Fachmodulen.
- **Erwartetes Ergebnis:** Ein einziger initialer Abruf liefert den stabilen, sofort sichtbaren
  Objektkopf, die vier KPIs, höchstens drei priorisierte Hinweise, die kompakte Einheitenübersicht und
  verfügbare Modulzusammenfassungen. Jede Zahl lässt sich auf ein autoritatives Modell oder eine
  Projektion zurückführen. Optionale Module besitzen explizite Verfügbarkeitszustände statt
  synthetischer Nullwerte.
- **Akzeptanz:** API- und Vertragstests beweisen Account-/Gebäudeisolation, Rollenbegrenzung,
  Stichtagskonsistenz, leere Objekte, gemischte Nutzung, Eigennutzung, Mieterwechsel und mindestens
  100 Einheiten ohne N+1-Abfragen. Eine Suche im Objekt-Dashboard-Frontend findet keine eigene
  Aggregation von Miet-, Zahlungs-, Kosten-, Abrechnungs- oder Zählerrohdaten.
- **Nicht tun:** Bestehende Engine-Ergebnisse nachrechnen; vollständige Ledger-, Kosten-, Zähler- oder
  Abrechnungshistorien in den Dashboard-Vertrag kopieren; fremde Gebäude anhand einer vom Client
  gelieferten ID ohne erneute Autorisierung lesen; den alten `occupiedToday`-Boolean als alleinige
  fachliche Wahrheit fortführen.

### [OD2] Objektkopf als Bild-Banner und klare Objektidentität gestalten

- **Datei/Ort:** `apps/web/src/features/objekte/building-detail-page.tsx` beziehungsweise beim Umbau
  daraus extrahierte objektbezogene Präsentationskomponenten; Gebäudestammdaten und Bild-Slot aus
  `02_Objekte.md` [O4], [O5] und [O12].
- **Fundstelle:** Der heutige Seitenkopf mit Breadcrumb, Objektname und einer einfachen Adresszeile.
- **Ist:** Das Objekt ist identifizierbar, besitzt aber keine visuelle Objektakte, keine Gebäudeart,
  kein Nutzungsprofil und keinen klaren Aktionsbereich.
- **Soll:** Den Seitenanfang als breite, ruhige Banner-Karte gestalten. Ein vorhandenes Objektfoto
  bildet den Hintergrund beziehungsweise eine klar abgegrenzte Bildfläche. Darüber oder auf einer
  kontrastgesicherten Inhaltsfläche stehen Breadcrumb, Objektname, vollständige Adresse,
  Gebäudeart/Nutzungsprofil und Anzahl der Einheiten. Text bleibt unabhängig vom Foto WCAG-konform
  lesbar und darf nicht direkt auf einem unkontrolliert hellen oder unruhigen Bild liegen.
- **Default:** Banner über die verfügbare Inhaltsbreite, Bildbereich etwa 220 Pixel hoch auf Desktop
  und Laptop. Text auf einer ruhigen Paper-/Ink-Fläche innerhalb beziehungsweise
  unterhalb des Bildes; kein starker Verlauf als Ersatz für Kontrast. Ohne Asset erscheint eine
  hochwertige Mint-/Paper-Platzhalterfläche mit dezenter vorhandener Gebäudeikonografie und dem Text
  „Objektfoto hinzufügen“. Solange Storage fehlt, steht zusätzlich klein „Foto-Upload kommt bald“;
  die Fläche ist nicht klickbar.
- **Erwartetes Ergebnis:** Nutzer erkennen auf den ersten Blick Name und Adresse des geöffneten
  Objekts. Musterstraße, Lindenweg und Hafenallee sind auch visuell klar unterscheidbar, ohne dass ein
  Foto zwingend vorhanden sein muss. Lange Namen und Adressen umbrechen kontrolliert; das Banner
  verdeckt keine Information und besitzt keinen dekorativen Text im Bild.
- **Akzeptanz:** Objekt mit Foto, ohne Foto und mit langem Namen ist bei 1280, 1440 und 1920 Pixel
  vollständig lesbar. Ohne Storage gibt es weder Datei-Input noch Dropzone noch erfolgreichen Uploadhinweis. Der
  aktuelle Objektpfad und Breadcrumb bleiben korrekt.
- **Nicht tun:** Externe Stockfotos nachladen; ein fremdes Objektfoto zeigen; Foto-Upload simulieren;
  Google Maps als dauerhaft großen Bestandteil des Banners einbauen; die in `02_Objekte.md`
  festgelegten Stammdatenfelder neu definieren.

### [OD3] Bearbeiten und PDF-Export als eindeutige Objektaktionen anbieten

- **Datei/Ort:** Aktionsbereich des neuen Objektkopfs, vorhandener Objektbearbeitungs-/Wizardpfad aus
  `02_Objekte.md`, neuer PDF-Exportvertrag aus [OD13].
- **Fundstelle:** Die heutige Objekt-Detailseite besitzt keine kompakten Objektaktionen; das
  Einheitenformular steht dauerhaft in der rechten Spalte.
- **Ist:** Stammdaten lassen sich nicht aus einer klaren Objektaktion heraus bearbeiten, und es gibt
  keine exportierbare Objektübersicht.
- **Soll:** Im Banner zwei klar erkennbare Aktionen anbieten: „Objekt bearbeiten“ und
  „Objektübersicht als PDF“. Bearbeiten öffnet den vorhandenen beziehungsweise durch `02_Objekte`
  vorgesehenen Stammdatenpfad. Der PDF-Export fordert einen serverseitig erzeugten Snapshot an und
  lädt erst nach erfolgreicher Erzeugung das Dokument. Rollen und Verfügbarkeit kommen aus dem
  Backend; nicht berechtigte Nutzer erhalten keine funktionsfähige Aktion.
- **Default:** „Objekt bearbeiten“ ist eine sekundäre Aktion. „Objektübersicht als PDF“ ist ebenfalls
  sekundär und erhält ein vorhandenes Dokument-/Download-Icon; die Seite besitzt dadurch nicht zwei
  konkurrierende Primärbuttons. Auf kleinen Breiten wandern beide in ein zugängliches Aktionsmenü mit
  sichtbarer Beschriftung. Während der PDF-Erzeugung lautet der Status „PDF wird erstellt…“ und die
  Aktion verhindert Doppelstarts.
- **Erwartetes Ergebnis:** Beide Aktionen sind im Objektkontext leicht auffindbar, ohne die
  Informationshierarchie zu dominieren. Fehler bei der PDF-Erzeugung bleiben auf die Aktion begrenzt
  und zeigen „PDF konnte nicht erstellt werden. Bitte erneut versuchen.“; die Objektakte bleibt
  nutzbar.
- **Akzeptanz:** Berechtigungs-, Lade-, Erfolgs- und Fehlerzustände sind per Tastatur nutzbar und
  getestet. Ein Employee ohne Bearbeitungsrecht sieht keine ausführbare Bearbeitungsaktion; ein
  direkter API-Aufruf wird zusätzlich serverseitig abgelehnt. Mehrfachklick erzeugt nicht unkontrolliert
  mehrere identische Exporte.
- **Nicht tun:** Browser-`print` als PDF-Export ausgeben; eine Abrechnung als Objektübersicht
  umbenennen; Löschen in den prominenten Aktionsbereich aufnehmen; Berechtigung ausschließlich über
  ausgeblendete Buttons regeln.

### [OD4] Vier autoritative Objekt-KPIs ausgeben

- **Datei/Ort:** Neuer KPI-Bereich der Objektakte und Objekt-Dashboard-Projektion aus [OD1].
- **Fundstelle:** Unterhalb des heutigen Objektkopfs existiert keine KPI-Zeile. Der aktuelle
  Detailvertrag liefert nur Einheiten und `occupiedToday`.
- **Ist:** Vermieter müssen Einheiten einzeln öffnen und Beträge selbst zusammenrechnen. Die
  finanzielle und operative Lage des Objekts ist nicht sofort erkennbar.
- **Soll:** Genau vier primäre KPIs darstellen: „Kaltmiete / Monat“, „Gesamtfläche“,
  „Ø Kaltmiete / m²“ und „Vermietungsstand“. Alle Werte kommen aus [OD1] und tragen denselben
  Stichtag. Zu jedem Wert gibt es eine kurze, verständliche Einordnung ohne technische Feldnamen.
- **Default:**
  - „Kaltmiete / Monat“ ist die Summe der am Stichtag gültigen Kaltmietperioden aktiver
    Mietverhältnisse; Vorauszahlungen, Garage und offene Forderungen werden nicht hineingemischt.
  - „Gesamtfläche“ ist die Summe der erfassten Flächen aller aktiven Einheiten des Objekts.
  - „Ø Kaltmiete / m²“ ist eine gewichtete Objektkennzahl: gesamte aktuelle Kaltmiete geteilt durch
    die Fläche der aktuell entgeltlich vermieteten Einheiten. Nicht der einfache Mittelwert der
    Einheitspreise. Ohne vermietete Fläche erscheint „–“ mit „Noch keine vermietete Fläche“.
  - „Vermietungsstand“ zeigt „N von M vermietet“ und darunter getrennt Leerstand und Eigennutzung,
    sofern vorhanden. Leerstand ist kein roter Fehlerzustand.
- **Erwartetes Ergebnis:** Die Karten besitzen identische ruhige Oberflächen, klare Labels,
  tabellarische Ziffern und dezente Lokara-Akzente. Große Beträge und Flächen umbrechen nicht
  unkontrolliert. Tooltips oder Hilfetexte erklären „Kaltmiete ohne Vorauszahlungen“ und die
  gewichtete Quadratmeterkennzahl.
- **Akzeptanz:** Backendtests decken Vollvermietung, Leerstand, Eigennutzung, fehlende Fläche,
  zukünftigen Mietbeginn, beendetes Mietverhältnis und untermonatigen Wechsel ab. Die Summe wird
  centgenau ermittelt. Im Frontend gibt es keine Division oder Summierung dieser KPI-Werte.
- **Nicht tun:** Den alten 82-%-/18-%-Demohelfer aus `01_Dashboard.md` verwenden; Vorauszahlungen als
  Kaltmiete zählen; Leerstand mit Nullmiete in den Quadratmeterdurchschnitt aufnehmen; fehlende Werte
  als `0,00 €` vortäuschen.

### [OD5] Gemischte Nutzung bei der Quadratmeterkennzahl ehrlich trennen

- **Datei/Ort:** KPI-Projektion und Darstellung „Ø Kaltmiete / m²“; Gebäudetyp/Nutzungsdaten aus
  `02_Objekte.md` und Einheiten-Nutzungsart, sofern im umgesetzten Datenmodell vorhanden.
- **Fundstelle:** Die Hafenallee im Portfolio-Runbook enthält Wohnungen und eine Gewerbeeinheit; ein
  einziger Durchschnitt kann diese unterschiedlichen Märkte irreführend vermischen.
- **Ist:** Der aktuelle Einheitsvertrag kennt noch keine belastbare Nutzungsart je Einheit. Ein
  gemischter Wert wäre zwar berechenbar, aber wirtschaftlich schlecht interpretierbar.
- **Soll:** Sobald autoritative Einheiten-Nutzungsarten vorhanden sind, Wohnen und Gewerbe
  serverseitig getrennt aggregieren. Bei nur einer vorhandenen vermieteten Nutzungsart bleibt die
  einfache KPI-Karte. Bei gemischter entgeltlicher Nutzung zeigt dieselbe Karte zwei sauber benannte
  Werte „Wohnen“ und „Gewerbe“ statt eines vermischten Gesamtwerts.
- **Default:** Keine Nutzungsart aus Einheitennamen wie „Büro“ oder „Laden“ ableiten. Fehlt die
  autoritative Einheiten-Nutzungsart beim Umsetzen, [OD5] als nicht verfügbar überspringen, einen
  einzelnen Wert nur dann zeigen, wenn der Backendvertrag ihn ausdrücklich als fachlich zulässig
  liefert, und die Lücke in Build-Notes festhalten.
- **Erwartetes Ergebnis:** Hafenallee kann zwei vergleichbare Quadratmeterwerte zeigen; reine
  Wohnobjekte zeigen weiterhin eine kompakte Karte ohne unnötige Unterteilung.
- **Akzeptanz:** Tests beweisen, dass Gewerbefläche nicht im Wohnwert und Wohnfläche nicht im
  Gewerbewert landet. Der Browser klassifiziert keine Einheit anhand von Freitext.
- **Nicht tun:** Marktüblichkeit, Mietspiegel, Rendite oder Angemessenheit behaupten; einen fehlenden
  Nutzungsdatensatz raten; die Gebäudenutzung mit der Nutzung jeder einzelnen Einheit gleichsetzen.

### [OD6] KPI-Raster und Aufmerksamkeit als gemeinsamen oberen Arbeitsbereich setzen

- **Datei/Ort:** Objekt-Dashboard-Layout direkt unter dem Banner.
- **Fundstelle:** Die freigegebene Brainstorming-Anordnung: vier KPIs links als 2×2-Raster und eine
  höhere Box „Aufmerksamkeit“ rechts; darunter die Einheitenbox.
- **Ist:** Die Seite besitzt ein `2fr_1fr`-Raster aus Einheitenliste und Anlageformular, aber keine
  strukturierte Objektübersicht.
- **Soll:** Auf großen Bildschirmen links die vier KPI-Karten als 2×2-Raster und rechts die
  Aufmerksamkeit-Box über die Höhe beider KPI-Reihen anordnen. Beide Bereiche bilden einen
  zusammengehörigen, oben ausgerichteten Arbeitsblock. Auf der kleinsten Pre-Pitch-Laptopbreite darf
  die Aufmerksamkeit nach den vier KPIs über die volle Breite umbrechen.
- **Default:** Desktop ab dem im Designsystem vorhandenen großen Breakpoint: KPI-Bereich etwa zwei
  Drittel, Aufmerksamkeit etwa ein Drittel; Abstand im 8-Pixel-System. Bei 1280 Pixel sind zwei
  KPI-Spalten und Aufmerksamkeit darunter zulässig. Keine feste Höhe; die rechte Box erhält nur durch
  das Grid die gemeinsame Zeilenspanne. Smartphone-/Tablet-Varianten sind Post-Pitch.
- **Erwartetes Ergebnis:** Der obere Bereich wirkt kompakt und ruhig. Die Aufmerksamkeit ist deutlich
  sichtbar, aber keine optisch identische fünfte KPI und kein rotes Alarmfeld. Unterschiedlich lange
  Inhalte erzeugen keine großen leeren Flächen oder abgeschnittene Texte.
- **Akzeptanz:** Screenshots bei 1280, 1440 und 1920 Pixel zeigen die festgelegte Reihenfolge,
  keine Überlagerung, keinen horizontalen Seiten-Scroll und keine erzwungene leere Kartenhöhe.
- **Nicht tun:** Eine zusätzliche Einheitensidebar bauen; die Aufmerksamkeit vor den Objektkopf
  setzen; globale Containerbreite zurückdrehen; fünf identische KPI-Karten nebeneinander quetschen.

### [OD7] Aufmerksamkeit mit autoritativen Fakten und nächster Aktion füllen

- **Datei/Ort:** Rechte Aufmerksamkeit-Box und serverseitige Dashboard-Projektion; späterer
  gemeinsamer Guard-/Reminder-Vertrag.
- **Fundstelle:** Heute gibt es auf der Objektseite keine gebündelte Sicht auf bevorstehende Wechsel,
  offene Salden, Abrechnungsblocker, fehlende Ablesungen oder autoritative Fristenhinweise.
- **Ist:** Nutzer müssen mehrere Module besuchen und selbst entscheiden, was relevant ist. Ein
  Ticket-/Reminder-Modul ist noch nicht vollständig vorhanden.
- **Soll:** Höchstens drei objektbezogene Fakten anzeigen, die bereits von ihren Fachmodulen oder dem
  gemeinsamen Wächter als relevant geliefert werden. Jede Zeile enthält verständlichen Sachverhalt,
  betroffene Einheit/Mietpartei soweit zulässig und genau eine erlaubte nächste Aktion oder einen
  Drill-down. Zusätzliche Fakten sind über „Alle Hinweise“ erreichbar, sobald eine echte Zielansicht
  existiert.
- **Default:** Darstellungsreihenfolge nach serverseitig gelieferter Priorität, danach Fälligkeits-/
  Ereignisdatum und stabile ID. Zulässige Kategorien zunächst: bevorstehender Ein-/Auszug, offener
  Forderungssaldo, zu prüfende Zahlung, Abrechnungs-Readiness, fehlende Ablesung und vom gemeinsamen
  Wächter gelieferter Zählerhinweis. Ein Auszugsvorschaufenster beträgt 90 Tage. Der Server liefert
  neutrale Schweregrade und Aktionsziele; das Frontend erfindet keine Priorität.
- **Erwartetes Ergebnis:** Beispiele lauten sachlich „500,00 € offen · Wohnung 1“, „Auszug in 24
  Tagen · Dachgeschoss“ oder „Endablesung fehlt · Wohnung 3“. Bei null Fakten zeigt die Box positiv
  „Alles im Blick“ und „Für dieses Objekt besteht aktuell kein Handlungsbedarf.“ ohne Konfetti oder
  Erfolgsanimation.
- **Akzeptanz:** Jede sichtbare Hinweiszeile lässt sich auf einen Backendstatus und ein autorisiertes
  Ziel zurückführen. Ein beendetes Mietverhältnis ohne Forderung erscheint nicht als zahlungssäumig.
  Eine ignorierte Bankausgabe verändert die Box nicht. Tastaturfokus folgt der sichtbaren Reihenfolge.
- **Nicht tun:** Mahnstatus, Verzug, Gebühren oder rechtliche Fristen berechnen; alle ungeklärten
  Bankbewegungen automatisch als offene Miete melden; feste Demo-Hinweise einbauen; das Wort
  „dringend“ allein im Frontend vergeben.

### [OD8] Einheiten als zentrale Arbeitsbox statt Sidebar darstellen

- **Datei/Ort:** Hauptbereich der Objektakte unter KPI/Aufmerksamkeit; heutige Einheitentabelle in
  `building-detail-page.tsx`; Drill-down zur Einheitendetailseite.
- **Fundstelle:** Die heutige Tabelle mit „Einheit“, „Wohnfläche“ und „Status heute“ sowie der
  Immocloud-Referenz mit zusätzlicher linker Einheitensidebar.
- **Ist:** Die Tabelle zeigt nur Fläche und einen zu groben Belegungsstatus. Das dauerhafte
  Anlageformular nimmt rechts Platz ein. Eine zweite Einheitensidebar würde die globale Navigation
  duplizieren.
- **Soll:** Eine breite Box „Einheiten“ direkt unter dem oberen Arbeitsbereich aufbauen. Desktopspalten
  in dieser Reihenfolge: „Einheit“, „Zustand“, „Mietpartei“, „Fläche“, „Kaltmiete“, „Saldo“ und – erst
  bei echtem Modul – „Vorgänge“. Die gesamte Zeile beziehungsweise ein expliziter Link öffnet die
  Einheitendetailseite. Oberhalb stehen Ergebniszahl, Statusfilter und die Aktion „Einheit anlegen“
  für berechtigte Owner.
- **Default:** Filter „Alle“, „Vermietet“, „Leerstand“, „Eigennutzung“ und – bei verfügbaren
  Zahlungsdaten – „Mit offenem Saldo“. „Mit Handlungsbedarf“ erst aktivieren, wenn [OD7] eine
  autoritative Einheitenzuordnung liefert. Standardsortierung ist die bestehende natürliche
  Einheitenreihenfolge; Filterzustand darf als URL-Parameter gespeichert werden. „Kontakte“ ist keine
  Standardspalte.
- **Erwartetes Ergebnis:** Vermieter vergleichen alle Einheiten ohne zweite Sidebar. Zeilen zeigen
  aktuelle Vertrags- und Zahlungsfakten kompakt; historische Details bleiben auf der Einheitenseite.
  Leere und eigengenutzte Einheiten enthalten verständliche Gedankenstriche statt erfundener
  Mietpartei oder Nullmiete.
- **Akzeptanz:** Filter sind per Tastatur bedienbar und ändern nur die sichtbaren servergelieferten
  Zeilen. Jede Einheit führt zum richtigen accountgescopten Pfad. Das bisherige rechte
  `CreateUnitForm` ist nicht mehr dauerhaft sichtbar; die Anlage erfolgt über den Wizard aus
  `02_Objekte.md` [O10].
- **Nicht tun:** Eine Objekt-/Einheitensidebar ergänzen; Kontakte als leere Pflichtspalte anzeigen;
  die komplette Mietverhältnis-Historie in jede Zeile laden; Inline-Bearbeitung für Geld- oder
  Vertragsdaten bauen.

### [OD9] Einheitenzustand und aktuelle Mietpartei zeitlich korrekt projizieren

- **Datei/Ort:** Einheitenteil des Objekt-Dashboard-Read-Models, Mietverhältnis-/Eigennutzungsmodelle
  und Einheitenzeilen.
- **Fundstelle:** Der heutige Backendwert `occupiedToday` und die Frontenddarstellung
  `occupiedToday ? 'Vermietet' : 'Leerstand'`.
- **Ist:** Jede Einheit ohne aktives Mietverhältnis wird als Leerstand dargestellt, auch wenn eine
  aktive Eigennutzung oder unentgeltliche Überlassung vorliegt. Bevorstehende Wechsel sind unsichtbar.
- **Soll:** Pro Einheit genau einen autoritativen Zustand zum `asOf`-Zeitpunkt ausgeben: vermietet,
  Leerstand, Eigennutzung oder unentgeltlich überlassen. Zusätzlich darf ein getrenntes nächstes
  Mietereignis geliefert werden, beispielsweise Einzug oder Auszug innerhalb der nächsten 90 Tage.
  Die aktuelle Mietpartei stammt ausschließlich aus dem am Stichtag gültigen Mietverhältnis und kann
  mehrere Namen oder eine Organisation enthalten.
- **Default:** Nutzertext „Mietpartei“ statt „Mieter“. Mehrere Parteien komma-getrennt mit
  zugänglicher vollständiger Anzeige; bei begrenztem Platz visuell kürzen, aber den vollständigen
  Text für Hilfstechnologien erhalten. Überschneidungen gelten als Backend-Datenfehler und werden
  nicht durch willkürliche Auswahl einer Partei verborgen.
- **Erwartetes Ergebnis:** Lindenwegs Einliegerwohnung kann ehrlich als Leerstand oder Eigennutzung
  erscheinen, ohne offene Mietforderung. Musterstraßes Wohnung B zeigt die aktuelle Partei und einen
  bevorstehenden Wechsel, sofern er im Vorschaufenster liegt.
- **Akzeptanz:** Tests decken halboffene Zeiträume, Auszug/Einzug am selben Grenzdatum,
  Leerstandslücke, Eigennutzung, mehrere Mietparteien und unerlaubte Überschneidung ab. Der String
  „Leerstand“ wird im Frontend nicht mehr allein aus `occupiedToday === false` erzeugt.
- **Nicht tun:** Eigennutzung als Renter anlegen; Namen aus Banktransaktionen ableiten; zukünftige
  Mietparteien vor ihrem Vertragsbeginn als aktuell anzeigen; Datenfehler still auflösen.

### [OD10] Kaltmiete und Saldo je Einheit fachlich getrennt anzeigen

- **Datei/Ort:** Einheitenprojektion, Zahlungs-/Forderungsprojektionen aus `06_Zahlungen.md` [P13],
  [P14], [P16] und Einheitenbox.
- **Fundstelle:** Die heutige Objektseite zeigt weder aktuelle Kaltmiete noch Forderungs- oder
  Zahlungsstatus pro Einheit.
- **Ist:** Ein Frontend könnte versucht sein, Saldo aus Kaltmiete und sichtbaren Bankeingängen zu
  schätzen. Das würde Teilzahlungen, Nachzahlungen, Guthaben, Reviews und beendete Verträge falsch
  behandeln.
- **Soll:** „Kaltmiete“ aus der am Stichtag gültigen Vertragsperiode und „Saldo“ aus der
  autoritativen Forderungs-/Ledger-Projektion getrennt ausgeben. Der Saldo bezieht sich standardmäßig
  auf den laufenden Monat und zeigt Status plus offenen Betrag. Andere Forderungsarten wie eine
  Betriebskosten-Nachzahlung werden eindeutig benannt und nicht mit der Monatskaltmiete verrechnet.
- **Default:** Mögliche Texte: „Ausgeglichen“, „500,00 € offen“, „Teilweise bezahlt“,
  „100,00 € zu prüfen“, „125,00 € Nachzahlung offen“ und „Keine Forderung“. Ein ungeklärter
  Überzahlungsrest ist „zu prüfen“, nicht automatisch Guthaben. Bei mehreren offenen Kategorien zeigt
  die Zeile den gesamten autoritativ offenen Betrag plus „Details“, der Drill-down trennt die
  Bestandteile.
- **⚠️ MUSS-INPUT:** Verbindliche Erzeugungs- und Fälligkeitsregeln für regelmäßige Mietforderungen
  aus `06_Zahlungen.md` [P13]. Fehlen sie beim Bau, keine neue Forderung erzeugen und nur bereits
  autoritativ vorhandene Salden anzeigen; Teilpunkt in Build-Notes festhalten.
- **Erwartetes Ergebnis:** Jonas zeigt nach seiner Teilzahlung 500,00 Euro offen; Maria zeigt den
  ungeklärten Überzahlungsrest getrennt als Prüfung; Sophie zeigt 1.320,00 Euro offen ohne erfundenen
  Bankumsatz; die beendete Einliegerwohnung zeigt keine offene Monatsforderung.
- **Akzeptanz:** Zahlungs-, Dashboard-, Objekt- und Einheitensicht verwenden denselben offenen Saldo.
  Tests beweisen Teilzahlung, Überzahlung, Guthaben, Rücklastschrift, Nachzahlung, fehlenden Eingang
  und Vertragsende centgenau.
- **Nicht tun:** Zahlungseingänge aus Banklisten summieren; Guthaben automatisch verrechnen;
  Kaltmiete und Gesamtmietsoll verwechseln; Mahnstatus aus dem offenen Betrag ableiten.

### [OD11] Kompakte Fachmodul-Zusammenfassungen unter den Einheiten ergänzen

- **Datei/Ort:** Objektakte unterhalb der Einheitenbox; bestehende Features und Drill-down-Routen für
  Zahlungen, Kosten, Abrechnung und Zähler.
- **Fundstelle:** Die Immocloud-Referenz reiht vollständige Mieten-, Betriebskosten-, Finanz-,
  Dokument- und Einheitentabellen untereinander. Lokara besitzt dafür eigene Fachseiten.
- **Ist:** Auf der heutigen Objektseite fehlen alle fachlichen Querinformationen. Das Kopieren der
  vollständigen Tabellen würde die Seite jedoch überladen und Datenverträge duplizieren.
- **Soll:** Vier kompakte Zusammenfassungen in dieser Reihenfolge anbieten: „Zahlungen“, „Kosten &
  Abrechnung“, „Zähler“ und später „Vorgänge“. Jede Karte zeigt höchstens drei autoritative Kennzahlen
  oder Hinweise und einen eindeutigen Drill-down zum bereits objektgefilterten Fachmodul. Nicht
  verfügbare Module werden ehrlich behandelt.
- **Default:**
  - Zahlungen: Mietsoll laufender Monat, fachlich verbucht, offen, zu prüfen.
  - Kosten & Abrechnung: ausgewähltes beziehungsweise laufendes Abrechnungsjahr, Kostenstatus,
    Abrechnungsstatus und nächste serverseitig erlaubte Aktion.
  - Zähler: aktive Zähler, fehlende Ablesungen und Wächterhinweise.
  - Vorgänge: erst bei echter Persistenz offene Vorgänge und betroffene Einheiten; vorher vollständig
    weglassen statt eine große „0 Tickets“-Karte zu zeigen.
- **Erwartetes Ergebnis:** Die Objektakte beantwortet die wichtigsten Fragen, bleibt aber deutlich
  kürzer und ruhiger als die Immocloud-Referenz. Nutzer gelangen mit einem Klick in die vollständige
  gefilterte Arbeitsansicht.
- **Akzeptanz:** Keine Karte lädt eine vollständige Historie. Drill-downs enthalten die autorisierte
  Objekt-ID beziehungsweise nutzen eine objektbezogene Route und behalten sinnvolle Zeitraumfilter.
  Teilfehler einer Karte blockieren Banner, KPIs und Einheiten nicht.
- **Nicht tun:** Vollständige Bankbewegungen, Kostenzeilen, Abrechnungsdokumente oder
  Ablesehistorien auf der Objektakte wiederholen; neue Fachlogik in React-Komponenten anlegen;
  Vorgänge als Mock zeigen.

### [OD12] Kontakte, Dokumente, Fotos und Objektaktivität nachrangig und ehrlich vorbereiten

- **Datei/Ort:** Unterer Bereich der Objektakte; vorhandene beziehungsweise zukünftige
  Storage-/Kontakt-/Audit-Verträge.
- **Fundstelle:** Die Immocloud-Referenz zeigt Kontakte als große Standardfläche sowie Dokumente und
  Notizen. Für Lokara sind Kontakte laut Produktentscheidung optional und Storage ist noch nicht
  produktiv vorhanden.
- **Ist:** Es existiert kein vollständiger allgemeiner Objekt-Dokument-/Foto-Storage und kein
  freigegebenes Kontakt- oder Notizmodul für diese Objektakte. Eine visuell vollständige Nachbildung
  wäre Scheinfunktion.
- **Soll:** Kontakte nicht als Standardfeld der Einheitenbox und nicht als große leere Fläche nahe
  den KPIs zeigen. Sobald echte Kontakte vorhanden sind, einen kompakten optionalen Bereich im
  unteren Seitenteil anbieten; ohne Kontakte reicht eine berechtigte sekundäre Aktion
  „Kontakt hinzufügen“. Dokumente/Fotos erst mit realer Speicherung, Berechtigung, Download und
  Fehlerbehandlung aktivieren. Objektaktivität später als serverseitig paginierte, nachvollziehbare
  Historie aus echten Domänenereignissen aufbauen.
- **Default:** Vor Umsetzung der Module nur der in `02_Objekte.md` [O12] freigegebene inaktive
  Bild-Slot im Banner; keine zusätzlichen leeren Dokument-/Kontakt-/Notizkarten. Aktivität zeigt
  später neueste zehn Ereignisse und „Alle Aktivitäten“, niemals aus Client-Logs erzeugte
  Erfolgsmeldungen.
- **Erwartetes Ergebnis:** Die Seite bleibt im aktuellen Produktstand ehrlich und kompakt. Mit später
  verfügbaren Daten wachsen optionale Bereiche unterhalb der Kernarbeit, ohne KPIs und Einheiten zu
  verdrängen.
- **Akzeptanz:** Ohne Storage oder Kontaktmodul gibt es keine funktionsfähigen Upload-, Lösch-,
  Vorschau-, Download-, Notiz- oder Kontaktaktionen. Spätere Tests beweisen Objekt-/Accountgrenzen,
  Pagination und Berechtigungen.
- **Nicht tun:** Kontakte als Pflichtdaten erfinden; Dokumentnamen hartcodieren; lokale Browserdaten
  als Objektarchiv verwenden; Auditaktivität aus UI-Klicks vortäuschen; fremde Storage-URLs direkt
  einbetten.

### [OD13] Saubere Objektübersicht als serverseitigen PDF-Snapshot erzeugen

- **Datei/Ort:** Neue Objektübersichts-Projektion unter `apps/api`, HTML-zu-PDF-Pfad unter
  `packages/pdf`, Downloadvertrag und PDF-Aktion aus [OD3].
- **Fundstelle:** Lokara verwendet bereits Playwright/Chromium für PDF-Dokumente, besitzt aber keine
  eigenständige Objektübersicht. Die Objekt-Dashboard-Seite selbst ist kein druckfreigegebenes
  Dokument.
- **Ist:** Nutzer können keine kompakte, konsistente Objektakte weitergeben oder archivieren. Ein
  Browserdruck würde responsive UI, Navigation, Ladezustände und möglicherweise nicht zusammenpassende
  Datenstände erfassen.
- **Soll:** Eine eigene Dokumentart „Objektübersicht“ serverseitig erzeugen. Vor Rendering einen
  autorisierten, zeitlich konsistenten Snapshot erstellen und dessen `asOf`, Objekt-ID, Account-ID,
  Erstellzeitpunkt und Dokumentversion archivieren. Der Renderer übernimmt Werte; er berechnet keine
  Miete, Fläche, Salden oder Status neu.
- **Default:** Schlichtes A4-Hochformat im bestehenden Lokara-PDF-Stil. Inhalt in dieser Reihenfolge:
  Lokara-/Dokumentkopf, Objektname und Adresse, Datenstand, Gebäudestammdaten, vier KPIs,
  Einheitenübersicht mit Zustand/Mietpartei/Fläche/Kaltmiete/Saldo, kompakte relevante Hinweise und
  eine Fußzeile mit Seitenzahl und Erstellzeitpunkt. Optionale Bereiche ohne Daten entfallen.
  Objektfoto standardmäßig nicht einbetten, damit Dateigröße, Bildrechte und Druckqualität den
  Kernexport nicht blockieren. PDF-Dateiname:
  `Objektübersicht_<bereinigter-Objektname>_<YYYY-MM-DD>.pdf`.
- **Erwartetes Ergebnis:** Das PDF ist auch ohne Farbdruck verständlich, tabellarische Beträge sind
  rechtsbündig, Tabellenköpfe wiederholen sich auf Folgeseiten und Einheitenzeilen werden nicht
  unlesbar getrennt. Auf jeder Seite ist erkennbar, welches Objekt und welcher Datenstand dargestellt
  wird. Das Dokument behauptet weder Vollständigkeit eines Datenraums noch Rechtswirkung.
- **Akzeptanz:** PDF-Tests prüfen Dokumenttyp, Snapshotidentität, Account-/Objektisolation,
  Seitentrennung bei mindestens 100 Einheiten, fehlende optionale Daten, Umlaute, lange Namen,
  centgenaue Werte und reproduzierbares Rendering. Visuelle Renderprüfung bestätigt A4-Ränder,
  lesbare Tabellen und keine abgeschnittenen Inhalte.
- **Nicht tun:** Browserseite drucken; Betriebskostenabrechnung, Mietvertrag, Kontoauszug oder
  Mahnschreiben imitieren; Werte im PDF-Renderer nachrechnen; ungeklärte Reviews als bezahlte Beträge
  ausgeben; Objektfoto ohne geklärte Speicherung und Bildquelle einbetten.

### [OD14] Rollen, erlaubte Aktionen und sensible Daten absichern

- **Datei/Ort:** Objekt-Dashboard-Endpunkt, PDF-Endpunkt, Objektbearbeitung, Einheiten-Wizard und alle
  Drill-downs; bestehende Membership-/Building-Authorization.
- **Fundstelle:** Die Objektliste blendet Owner-Steuerungen bereits rollenabhängig aus; die heutige
  Objekt-Detailseite zeigt das Einheiten-Anlageformular dagegen unabhängig von der Rolle.
- **Ist:** UI-Gating ist inkonsistent. Außerdem werden mit Mietparteien und Salden personenbezogene
  beziehungsweise finanzielle Daten in die Objektakte aufgenommen.
- **Soll:** Der Server liefert beziehungsweise prüft jede erlaubte Aktion nach Membership-Rolle und
  Gebäudezuweisung. Owner dürfen im freigegebenen Umfang bearbeiten, Einheiten anlegen und PDFs
  erzeugen. Employees sehen nur zugewiesene Objekte und nur die für ihre Rolle freigegebenen
  Aktionen. Nicht erlaubte Daten oder Aktionen werden nicht lediglich optisch versteckt, sondern
  serverseitig verweigert.
- **Default:** Für vorhandene Rollen keine neuen Rechte erfinden; die bestehenden M5-Regeln bleiben
  maßgeblich. Wo eine Aktion noch keine klar freigegebene Employee-Regel besitzt, Owner-only und als
  Annahme in Build-Notes festhalten. Mieterportal-/Renter-Zugriff ist nicht Teil dieser Objektakte.
- **Erwartetes Ergebnis:** Zwei Nutzer mit unterschiedlichen Gebäudezuweisungen erhalten weder über
  Dashboard noch PDF Daten des jeweils fremden Objekts. Die Oberfläche zeigt nur ausführbare
  Aktionen und erklärt einen echten 403/404 nutzerverständlich.
- **Akzeptanz:** API-Tests versuchen direkte fremde Gebäude- und PDF-Aufrufe, Manipulation der URL und
  nicht erlaubte Writes. RLS-/FK- und Rollen-Gates bleiben grün. Frontendtests prüfen sichtbare
  Aktionsunterschiede, ohne sie als einzigen Schutz zu behandeln.
- **Nicht tun:** Neue Rollen einführen; bestehende M5-Autorisierung lockern; vollständige
  Mietparteinamen in Logs, Dateinamen oder Fehlertexte schreiben; Mieterportal vorwegnehmen.

### [OD15] Lade-, Leer-, Teilfehler-, Erfolgs- und Nicht-gefunden-Zustände ausarbeiten

- **Datei/Ort:** Gesamte Objektakte und einzelne optionale Fachmodulkarten.
- **Fundstelle:** Heute zeigt die Seite ein einzelnes großes Mint-Skeleton und bei Fehlern den Text
  „Bitte API und Datenbank prüfen, dann neu laden.“
- **Ist:** Der technische Fehlertext ist nicht nutzergerecht. Ein späterer Fehler eines optionalen
  Moduls könnte die gesamte Objektakte blockieren.
- **Soll:** Den stabilen Objektkopf und Kernabruf mit strukturgleichen Skeletons laden. 404 zeigt
  „Objekt nicht gefunden“ mit „Zurück zu Objekte“. Ein allgemeiner Kernfehler zeigt eine ruhige
  Wiederholen-Aktion ohne API-/Datenbank-Sprache. Optionale Fachmodule besitzen isolierte
  Lade-/Fehlerzustände; Banner, KPIs und Einheiten bleiben nutzbar, wenn beispielsweise die
  Zählerzusammenfassung ausfällt.
- **Default:** Leeres Objekt: Banner und Stammdaten sichtbar, KPI-Werte fachlich leer beziehungsweise
  Gesamtfläche nach vorhandenen Daten, Aufmerksamkeit mit positivem neutralem Zustand und eine große
  Einheiten-Leerkarte „Noch keine Einheiten“ mit Owner-Aktion „Einheit anlegen“. PDF-Export bleibt
  möglich, sofern der Snapshot ehrlich mit dem leeren Zustand umgehen kann. Nach erfolgreicher
  Bearbeitung oder Anlage werden betroffene Queries gezielt invalidiert.
- **Erwartetes Ergebnis:** Kein endloser einzelner Ladebalken ohne Erklärung. Fehler nennen die
  betroffene Information, nicht interne Systeme. Erfolgszustände aktualisieren dieselben
  serverseitigen Werte ohne veraltete parallele UI-Salden.
- **Akzeptanz:** Tests decken Kern-404, Kern-500, Teilfehler, leeres Objekt, fehlende optionale Module,
  PDF-Fehler und erfolgreiche Query-Aktualisierung ab. Kein sichtbarer Text fordert Nutzer auf, „API
  und Datenbank“ zu prüfen.
- **Nicht tun:** Bei Teilfehlern alle bereits geladenen Daten entfernen; fehlende Daten als Nullwerte
  ausgeben; Fehlerdetails oder Stacktraces zeigen; automatische Endlosschleifen beim Retry bauen.

### [OD16] Desktop-/Laptop-Tabellen, Fokus und Barrierefreiheit absichern

- **Datei/Ort:** Banner, Aktionen, KPI-Raster, Aufmerksamkeit, Einheitenbox, Fachmodulkarten und
  PDF-Aktionszustände.
- **Fundstelle:** Die heutige Einheitentabelle und das neue Dashboard enthalten mehrere interaktive
  und datenreiche Bereiche ohne verbindliche Laptopbreiten-Abnahme.
- **Ist:** Auf 1280 Pixel drohen zusammengedrückte Spalten, horizontales Scrollen und unklare
  Zeilenklickziele.
- **Soll:** Tabelle und Arbeitsbereiche für 1280, 1440 und 1920 Pixel optimieren. Filter, Aktionsmenü
  und Drill-downs vollständig per
  Tastatur und Screenreader bedienbar machen. Status nie allein über Farbe vermitteln. Bei Navigation
  und Dialog-/Menüschluss Fokus sinnvoll setzen beziehungsweise zurückgeben.
- **Default:** Bei 1280 Pixel dürfen nachrangige Inhalte in eine zweite Zeile umbrechen; Name/Zustand,
  Mietpartei, Fläche/Kaltmiete, Saldo und Aktion „Einheit öffnen“ bleiben sichtbar. Sichtbarer Fokus
  mit vorhandenem Ring-Token, Überschriftenhierarchie `h1` Objekt und `h2` je Hauptbereich. Animationen
  nur 150–250 Millisekunden über Transform/Opacity und mit Reduced-Motion-Beachtung.
- **Erwartetes Ergebnis:** Die vollständige Kernaufgabe – Objekt erkennen, KPI lesen, Hinweis öffnen,
  Einheit filtern und Einheit öffnen – funktioniert bei 200 Prozent Zoom und ohne Maus.
- **Akzeptanz:** Tastatur-, Screenreader- und Desktopbreiten-Tests prüfen Fokusreihenfolge, zugängliche
  Namen, Statuszusätze, 1280/1440/1920 Pixel, 200-Prozent-Zoom und Reduced Motion. Im Standardzoom gibt
  es keinen horizontalen Seiten-Scroll.
- **Nicht tun:** Ganze Tabellenzeilen ohne zugänglichen Link/Button als versteckte Klickfläche bauen;
  Status ausschließlich grün/rot codieren; Fokusoutline entfernen; Smartphone-/Tablet-Karten oder
  Touchnavigation Pre-Pitch bauen.

### [OD17] Performance, Cache-Aktualisierung und Tests als Abnahmeschutz ergänzen

- **Datei/Ort:** Objekt-Dashboard-Service/-Endpoint, Datenbankabfragen und Indizes soweit nach
  gemessener Abfrage erforderlich, TanStack-Query-Anbindung, API-/Web-/PDF-Tests und Demo-Gate.
- **Fundstelle:** Das heutige Gebäude-Detail greift über ORM-Beziehungen auf Einheiten und
  Mietverhältnisse zu. Das neue Dashboard verbindet mehrere zeitliche und finanzielle Projektionen
  und muss auch bei langen Historien schnell bleiben.
- **Ist:** Ohne bewusstes Read Model drohen N+1-Abfragen, das Laden vollständiger Historien und
  inkonsistente Caches nach Zahlungs-, Miet-, Kosten-, Abrechnungs- oder Zähleraktionen.
- **Soll:** Aggregationen set-basiert und serverseitig ausführen, nur sichtbare kompakte Zeilen
  übertragen und teure Historien in ihren Fachendpoints belassen. Query-Keys objekt- und
  accountgescopet führen. Nach relevanten Mutationen Objekt-Dashboard, Portfolio-Dashboard und
  betroffene Fachprojektionen gezielt invalidieren. Vertrag, Berechnungshandoff, Isolation,
  Darstellung und PDF vollständig testen.
- **Default:** Kein vorzeitiger Redis-Zwang; zuerst geeignete Abfragen und Indizes gegen reale
  Query-Pläne. Falls gecacht wird, enthält der Cache mindestens Account, Objekt und fachlichen
  Datenstand und wird nicht als dauerhafte Wahrheit verwendet. Ziel für den lokalen Demoabruf nach
  Warm-up: unter 500 Millisekunden bei 100 Einheiten und mehrjähriger Historie; Abweichung messen und
  in Build-Notes begründen.
- **Erwartetes Ergebnis:** Die Objektakte bleibt bei Portfolio-Demo und größeren Gebäuden reaktionsfähig.
  Eine bestätigte Zahlung, ein neues Mietverhältnis oder eine Ablesung aktualisiert die betroffenen
  Objektwerte konsistent, ohne vollständigen Browser-Reload und ohne parallel stehen bleibende
  Altwerte.
- **Akzeptanz:** Tests und Messung beweisen keine N+1-Abfrage pro Einheit, stabile Payloadgröße,
  korrekte Invalidierung, Demo-Kontrollsummen, Rollen-/RLS-Grenzen und PDF-Reproduzierbarkeit.
  `scripts/gate.sh full` bleibt grün; bei Portfolio-Seed und PDF zusätzlich der nicht-destruktive
  Demo-Gate und die vorhandene visuelle PDF-Prüfung.
- **Nicht tun:** Vollständige Ledger-/Miet-/Zählerhistorien vorladen; accountübergreifende Cache-Keys
  verwenden; Performance durch Client-Mocks kaschieren; einen destruktiven Demo-Reset ohne
  ausdrückliche Freigabe ausführen.

### [OD18] Die drei Portfolio-Demoobjekte als unterschiedliche Objektzustände abnehmen

- **Datei/Ort:** Portfolio-Seed/-Reset gemäß `DEMO-RUNBOOK-PORTFOLIO.md`, Objekt-Dashboard-Projektion,
  Web- und Demo-Tests; keine parallelen Frontend-Fixtures.
- **Fundstelle:** Der aktuelle Seed enthält nur `bld_demo_muster12`; das Portfolio-Runbook beschreibt
  zusätzlich Lindenweg 8 und Hafenallee 27 sowie die erwarteten Kosten-, Zahlungs-, Zähler- und
  Abrechnungszustände.
- **Ist:** Im heutigen Repo kann nur Musterstraße unter
  `/a/acc_demo_lokara/objekte/bld_demo_muster12` geöffnet werden. Die drei Zielzustände sind noch
  nicht vollständig persistiert.
- **Soll:** Nach Umsetzung des Portfolio-Runbooks liest jedes Objekt-Dashboard denselben
  reproduzierbaren Seed wie Portfolio, Zahlungen, Kosten, Zähler und Abrechnung. Keine
  objektseitigen Sonderwerte oder per Objekt-ID hartcodierten UI-Zweige ergänzen.
- **Default:**
  - Musterstraße 12 demonstriert sieben vermietete Einheiten, den historischen Mieterwechsel,
    finalisierte/vorschaufähige Abrechnung, Golden-Kosten/-Zähler und 125,00 Euro offene Nachzahlung.
  - Lindenweg 8 demonstriert zwei vermietete Einheiten sowie eine ehrlich getrennte Leerstands-/
    Eigennutzungseinheit, 500,00 Euro offenen Teilzahlungsrest, ungeklärte Überzahlung und
    Abrechnungs-Readiness.
  - Hafenallee 27 demonstriert gemischte Nutzung, 5.400,00 Euro aktuelles Mietsoll, 1.320,00 Euro
    offene Forderung, separates Mietkonto, Zählerhinweis und positive Aktion „Abrechnung erstellen“.
- **Erwartetes Ergebnis:** Die drei Objektakten sehen strukturell gleich aus, zeigen aber sichtbar
  unterschiedliche reale Lebenszykluszustände. Änderungen aus dem Zahlungs-Demoablauf aktualisieren
  Objekt- und Portfolio-Dashboard aus derselben Projektion.
- **Akzeptanz:** Demo-Reset erzeugt 3 Objekte, 13 Einheiten, 12 aktuell vermietete und eine
  nicht vermietete/eigengenutzte Einheit sowie 15.360,00 Euro Portfolio-Mietsoll. Jonas, Maria,
  Sophie und Anna erscheinen mit den im Runbook festgelegten getrennten Zuständen. Keine Suche im
  Frontend findet diese Beträge als Objekt-Dashboard-Konstanten.
- **Nicht tun:** Das aktuelle Einobjekt-Seed still als vollständige Portfolio-Demo bezeichnen;
  Golden-Abrechnungswerte verändern; zufällige Daten bei jedem Lauf erzeugen; Demo-IDs als
  Produktionslogik verwenden.

## Out of Scope (bewusst NICHT hier)

- Portfolio-Dashboard und globale App-Shell neu gestalten; dafür gelten `01_Dashboard.md` und der
  `09_App-Shell-Desktop.md`.
- Objektliste, Kartenansicht, Geocoding und Anlage-Wizards neu definieren; sie gehören
  `02_Objekte.md`.
- Neue Kostenklassifikation, Umlageschlüssel oder BetrKV-Logik; sie gehören `03_Kosten.md` und den
  autoritativen Regeln.
- Eichfristen, Verbrauch, Plausibilität oder Heizkosten neu berechnen; sie gehören
  `04_Zaehler.md` und dem gemeinsamen Wächter.
- Abrechnungs-Readiness, Salden oder neue Vorauszahlungen berechnen; sie gehören
  `05_Abrechnung-erstellen.md`.
- Forderungs-, Matching-, Guthaben-, Mahn- oder Fälligkeitslogik neu definieren; sie gehört
  `06_Zahlungen.md` beziehungsweise einem später freigegebenen Mahn-/Reminder-Spec.
- Vollständiges Ticket-/Vorgangs-/Reminder-System. Dieser Spec reserviert nur dessen späteren
  objektbezogenen Konsumenten.
- Produktiver Foto-/Dokumentupload, Storage, Virenprüfung, OCR, E-Mail-Eingang oder Versand.
- Allgemeines CRM, Kontaktverwaltung, Notizen oder Mieterportal.
- Rendite, Marktwert, Mietspiegelvergleich, Angemessenheitsbewertung oder Investitionsberatung.
- Browserdruck als Ersatz für die definierte Objektübersichts-PDF.

## Verifikation (Gesamtergebnis)

1. Musterstraße über die Objektliste öffnen: Banner, Identität, zwei Aktionen, vier KPIs,
   Aufmerksamkeit und Einheitenbox erscheinen in dieser Reihenfolge.
2. Desktop/Laptop bei 1280, 1440 und 1920 Pixel prüfen: links 2×2 KPIs, rechts Aufmerksamkeit über
   beide Reihen beziehungsweise bei 1280 kontrolliert darunter; keine zusätzliche Einheitensidebar.
3. Ohne Objektfoto erscheint der ehrliche inaktive Lokara-Platzhalter; keine Netzwerkabfrage für ein
   Stockfoto und kein simulierter Upload.
4. KPI-Werte gegen Backendantwort und Seed kontrollieren. Kaltmiete enthält keine Vorauszahlungen;
   Quadratmeterwert ist gewichtet; Vermietungsstand trennt Leerstand und Eigennutzung.
5. Einheitenbox prüft Zustand, aktuelle Mietpartei, Fläche, Kaltmiete und Saldo. Ganze Kernaufgabe ist
   per Tastatur und bei 200 Prozent Zoom nutzbar.
6. Lindenweg beweist, dass Leerstand/Eigennutzung keine offene Mietforderung erzeugt. Jonas und Maria
   zeigen Teilzahlung beziehungsweise ungeklärte Überzahlung getrennt.
7. Hafenallee beweist gemischte Nutzung und getrennte Quadratmeterwerte, sofern die autoritative
   Einheiten-Nutzungsart umgesetzt ist.
8. Aufmerksamkeit zeigt höchstens drei echte Fakten, einen ruhigen „Alles im Blick“-Zustand und keine
   Frontend-erfundene Dringlichkeit.
9. Kosten-, Abrechnungs-, Zähler- und Zahlungszusammenfassungen führen zu den richtigen
   objektgefilterten Fachseiten und laden keine vollständigen Historien.
10. Objektübersicht als PDF erzeugen: korrekter Objekt-/Datenstand, A4-Layout, Seitenumbruch bei 100
    Einheiten, keine Neuberechnung und kein Zugriff auf fremde Objekte.
11. Owner-/Employee- und Gebäudezuweisungen mit direkten API-Aufrufen prüfen. Versteckte Aktionen
    ersetzen keine 403/404-/RLS-Grenze.
12. Lade-, Leer-, 404-, Kernfehler-, Teilfehler-, PDF-Fehler- und Erfolgszustände prüfen. Kein
    Nutzertext erwähnt API oder Datenbank.
13. Frontend-Suche findet keine fest codierten Demo-Beträge, keine 82-/18-Prozentableitung und keine
    Klassifikation von Einheiten anhand ihres Namens.
14. Typprüfung, Lint, Full-Gate, relevante RLS-/FK-Prüfungen, nicht-destruktiver Portfolio-Demo-Gate
    sowie PDF-Renderprüfung sind grün.

## Reihenfolge

1. [OD1], [OD9], [OD10] — autoritative Objekt-, Belegungs- und Zahlungsprojektionen.
2. [OD17] — Verträge, Isolation, Performancegrundlage und Tests parallel zur Projektion absichern.
3. [OD2], [OD3], [OD4], [OD5] — Objektkopf, Aktionen und vier KPIs.
4. [OD6], [OD7] — freigegebenes KPI-/Aufmerksamkeitslayout und echte Hinweise.
5. [OD8] — zentrale Einheitenbox für Desktop und Laptop.
6. [OD11], [OD12] — kompakte Fachmodule und ehrliche Zukunftsgrenzen.
7. [OD13] — Objektübersichts-PDF nach stabiler Dashboard-Projektion.
8. [OD14], [OD15], [OD16] — Rollen, Zustände und vollständige Barrierefreiheit.
9. [OD18] — drei Demoobjekte und gesamter Demo-/PDF-Abgleich.

## Build-Notes (füllt die KI beim Umsetzen aus)

<!-- Erwartete Einträge:
- [OD1] dedizierter Endpoint oder kompatible Vertragserweiterung und Begründung.
- [OD5] autoritative Nutzungsart je Einheit vorhanden; andernfalls Teilpunkt übersprungen.
- [OD7] verfügbare Guard-/Reminder-Kategorien; keine erfundene Priorisierung.
- [OD10] MUSS-INPUT für Mietforderungs-/Fälligkeitsregeln vorhanden oder nur bestehende Salden gezeigt.
- [OD12] tatsächlicher Stand von Kontakt-, Dokument-, Foto-, Notiz- und Aktivitätsmodulen.
- [OD13] Snapshot-/Archivierungsentscheidung und PDF-Fingerprint/Renderprüfung.
- [OD14] ungeklärte Employee-Rechte als Owner-only behandelt.
- [OD17] gemessene Abrufzeit und gegebenenfalls begründete Abweichung vom 500-ms-Ziel.
- [OD18] Portfolio-Seed vollständig vorhanden oder welche objektbezogenen Zustände noch fehlen.
-->
