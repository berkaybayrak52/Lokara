---
spec_id: 01-dashboard
titel: Default-Dashboard — Portfolio-KPIs, Cashflow, Aufgaben/Tickets (Option B)
status: freigegeben
prioritaet: hoch
betrifft: apps/web, apps/api
abhaengig_von: [00-layout-global]
repo_stand: Lokara-main @ 2026-08-24
---

## Zweck

Das aktuelle Dashboard (`apps/web/src/features/portal/dashboard.tsx`) ist ein Einzelobjekt-Platzhalter:
es zieht seine Daten aus `useAccountSummary` (Endpoint `/summary`, der bewusst genau EIN Gebäude über
`default_building_id` liefert) und zeigt drei Zähl-Kacheln (Objekt / Einheiten / Mietverhältnisse) plus
eine Abrechnungs-Karte und (für Owner) eine Demo-Reset-Karte. Dieser Spec ersetzt das durch ein
**Portfolio-Default-Dashboard** (Guard A4 aus `00_Layout-Global.md`): alle Kennzahlen aggregieren über
das gesamte Portfolio, ein Einzelobjekt sieht man nur durch Reindrillen über „Objekte".

Ziel ist ein demofähiges Dashboard, das ECHT in der laufenden App funktioniert. Zwei Kennzahlen sind
echt aus der Datenbank (Vermietungsstand, Mietsoll) und ändern sich live, wenn man ein Objekt oder ein
Mietverhältnis anlegt. Die Zahlungs-, Cashflow- und Ticket-Zahlen sind bewusst **Mock** (das Backend
dafür fehlt), werden aber aus dem echten Mietsoll abgeleitet, damit alle Zahlen zueinander passen.

**Dieser Spec enthält keinen Code. Alles ist bis ins Detail in Worten beschrieben.** Wo früher ein
Code-Beispiel stand, steht jetzt eine wörtliche Beschreibung des gewünschten Ergebnisses.

> **Ehrlicher Scope-Hinweis (bitte lesen):** Dies ist **kein reiner Layout-Spec**. Genau eine
> Kennzahl-Gruppe (Vermietungsstand + Mietsoll) braucht eine portfolioweite Aggregation, die es heute
> nicht gibt. Sie wird als **ein neuer, read-only Backend-Endpoint** angelegt (Befehl [D1]) — nicht im
> Frontend über viele Einzelabfragen nachgerechnet. Serverseitig ist die Mietsoll-Summe eine einzige
> Abfrage; im Frontend wären es viele verschachtelte Abfragen (langsam, fehleranfällig). Das ist die
> einzige Backend-Arbeit hier.

> **Was Mock ist und warum:** Zahlungseingänge, Offene Posten, Cashflow-Verlauf und die Aufgaben/
> Ticket-Zahlen haben im heutigen Build keine Datenquelle (Bankanbindung/finAPI verschoben, Mahnwesen
> und Ticket-Modul existieren noch nicht). Sie werden als klar gekennzeichnete Demo-Werte aus dem echten
> Mietsoll abgeleitet, damit die Demo stimmig wirkt, ohne etwas Erfundenes als echt auszugeben.

## Invarianten (zusätzlich zu den Standard-Invarianten)

- Pre-Pitch gilt Desktop/Laptop bei 1280, 1440 und 1920 Pixel sowie 200-Prozent-Zoom. Smartphone-,
  Tablet- und native Varianten sind Post-Pitch; Tastatur, Screenreader und sichtbarer Fokus bleiben
  verpflichtend.

- Nur vorhandene Design-Tokens (`ink`, `green`, `forest`, `mint`, `slate`, `paper`, `danger`/`warning`/
  `success`) und Hausschriften (`font-display` / `font-sans`). Keine rohen Farbwerte.
- **Keine neue npm-Dependency.** Ringe und Diagramme werden als handgezeichnetes SVG umgesetzt (kein
  Recharts/Chart.js/D3). Wie das SVG aussehen soll, ist je Widget in Worten beschrieben.
- **Kein Widget rendert je eine nackte „0" oder eine leere weiße Fläche.** Hat ein Widget nichts
  anzuzeigen, zeigt es einen positiven, aufgelösten Zustand („Voll vermietet", „Keine offenen Posten")
  oder einen Onboarding-Hinweis mit Weg zur nächsten Aktion.
- **Keine bestehende Rechen-, Rechts- oder Geldlogik verändern.** Befehl [D1] fügt einen **neuen
  read-only** Aggregations-Endpoint hinzu (erlaubt, „außer explizit anders"); keine Statement-/Engine-/
  Abrechnungslogik anfassen.
- Portfolio-Standard-Modell (aus `00` A4): Alle Widgets zeigen das gesamte Portfolio; ein Einzelobjekt
  sieht man über die Objektakte, nie über einen globalen Filter/Umschalter.
- Signal nie nur über Farbe (BFSG): jede Ampel/Statusfarbe zusätzlich mit Text oder Icon.
- Bei Unklarheit: naheliegendste Variante umsetzen, **nicht anhalten**, Annahme in `## Build-Notes`.
- `⚠️ MUSS-INPUT`-Werte nie erfinden — Teilpunkt überspringen + loggen, Rest umsetzen.

**Verhältnis zu `00_Layout-Global.md`:** Die Befehle A5 (Marken-Akzent) und A6 (Kartenhöhen) betreffen
genau die drei alten KPI-Kacheln, die dieser Spec ersetzt. Die neuen KPI-Karten müssen diese Stilregeln
**erben** (linke grüne Akzentkante, Label in `text-forest`, Zahl in `text-ink`, natürliche Kartenhöhe),
nicht dagegen bauen. A2 (Dev-Copy raus) und die Kopfzeile „Ihr Bestand auf einen Blick." bleiben. A4
(kein globaler Objekt-Filter) wird eingehalten.

---

## Gesamtlayout des Dashboards

- **Kopfbereich:** Überschrift „Übersicht" und die eine kurze Zeile „Ihr Bestand auf einen Blick."
  (aus `00` A2). Darunter der Widget-Bereich.
- **Obere Reihe — Kennzahlen:** drei gleich hohe Kennzahl-Karten nebeneinander (Mieteinnahmen,
  Vermietungsstand, Offene Posten) — siehe [D4].
- **Darunter — Cashflow:** ein breites Cashflow-Widget über die volle Breite — siehe [D5].
- **Darunter — Aufgaben & Tickets:** eine kompakte Zählerleiste — siehe [D6].
- **Untere Reihe:** die bestehende „Abrechnung erstellen"-Karte und (nur Owner) die Demo-Reset-Karte —
  siehe [D7].
- **Verhalten Desktop/Laptop:** Auf breiten Screens stehen die Kennzahlen dreispaltig nebeneinander,
  Cashflow und Aufgaben über die volle Breite. Bis zur freigegebenen Mindestbreite von 1280 Pixel darf
  das Raster kontrolliert umbrechen, ohne die Reihenfolge zu ändern. Die Seite selbst scrollt nicht
  horizontal. Eine eigenständige Smartphone-/Tablet-Anordnung ist Post-Pitch.
- **Jede Kennzahl-Karte reagiert auf Klick**, sofern ihr Ziel existiert (siehe je Widget).
- **Ladezustand:** solange Daten geladen werden, je Widget eine ruhige Platzhalter-Fläche im Mint-Ton
  (Skeleton), nie eine leere weiße Karte.

---

## Befehle

### [D1] Neuer read-only Endpoint: portfolioweite Übersicht
- **Datei:** `apps/api/src/lokara_api/routers/portal.py` (neuer Endpoint) und
  `apps/api/src/lokara_api/schemas.py` (neues Antwort-Schema).
- **Anker:** In `portal.py` direkt neben der bestehenden Funktion `summary` (Route `/summary`). Das neue
  Antwort-Schema neben die übrigen `…Response`-Klassen in `schemas.py`, in derselben Basisklassen-/
  Alias-Konvention wie `DemoSummaryResponse` (Feldnamen erscheinen auf dem Draht in camelCase).
- **Ist:** Es existiert nur `/summary`, das genau EIN Gebäude (`default_building_id`) liefert. Es gibt
  keinen portfolioweiten Aggregat-Endpoint.
- **Soll:** Einen neuen GET-Endpoint unter dem Pfad `/a/{account_id}/portfolio/overview` anlegen, der
  über **alle sichtbaren, nicht archivierten** Gebäude des Kontos aggregiert und Portfolio-Summen als
  JSON zurückgibt. Scoping/RLS wie bei den anderen Portal-Routen über die Account-Session-Dependency;
  die Employee-Sicht ist zu respektieren (die vorhandene Funktion, die die für den Nutzer sichtbaren
  Gebäude-IDs liefert, verwenden — ist sie gesetzt, nur diese Gebäude zählen). Ob eine Einheit heute
  vermietet ist und ob ein Mietverhältnis heute aktiv ist, wird mit derselben „aktiv heute"-Logik
  bestimmt wie in `buildings.py` (`gültig-ab` liegt heute oder früher, und `gültig-bis` ist entweder
  leer oder liegt nach heute).
- **Default (Feldsemantik — genau diese fünf Felder):**
  - `buildingCount` (Ganzzahl): Anzahl der einbezogenen Gebäude.
  - `unitCount` (Ganzzahl): Anzahl aller Einheiten in diesen Gebäuden.
  - `occupiedUnitCount` (Ganzzahl): Anzahl Einheiten mit mindestens einem heute aktiven
    Mietverhältnis.
  - `vacantUnitCount` (Ganzzahl): `unitCount` minus `occupiedUnitCount`.
  - `mietSollCentsMonthly` (Ganzzahl, Cent): Summe der monatlichen Kaltmiete (`base_rent_cents`) aller
    heute aktiven Mietverhältnisse. Vorauszahlungen/Warm-Miete werden **nicht** eingerechnet (mögliche
    spätere Erweiterung → Build-Note).
  - Hat das Konto keine Gebäude, werden alle fünf Zähler als `0` zurückgegeben (kein 404). Fehlt die
    Mitgliedschaft im Konto, bleibt das der Dependency überlassen (403), nicht hier behandeln.
- **Beschreibung der Aggregationslogik (statt Code):** Der Endpoint holt alle nicht-archivierten
  Gebäude des Kontos, filtert sie (falls Employee) auf die sichtbaren, und geht dann Gebäude für
  Gebäude, Einheit für Einheit durch: jede Einheit erhöht `unitCount`; hat die Einheit heute mindestens
  ein aktives Mietverhältnis, erhöht sie zusätzlich `occupiedUnitCount`, und die Kaltmieten ihrer heute
  aktiven Mietverhältnisse werden auf `mietSollCentsMonthly` addiert. Am Ende wird `vacantUnitCount` als
  Differenz gesetzt. Es wird nichts geschrieben und keine bestehende Berechnung aufgerufen.
- **Akzeptanz:** Ein GET auf `/a/{demo-konto}/portfolio/overview` liefert JSON mit genau diesen fünf
  Feldern; im Demo-Szenario ist `buildingCount` mindestens 1, `unitCount` gleich 3 und
  `mietSollCentsMonthly` größer 0. Ein neuer API-Test in `apps/api/tests/` prüft die Belegungs- und die
  Mietsoll-Summe und bleibt grün.
- **Nicht tun:** `/summary` ändern oder entfernen; die Statement-/Abrechnungs-Engines aufrufen oder
  anfassen; Warm-Miete/Vorauszahlung einrechnen; irgendetwas schreiben.

### [D2] Frontend-Anbindung: Validierungsschema und Abfrage-Hook
- **Datei:** `apps/web/src/lib/contracts.ts` (Schema) und
  `apps/web/src/features/portal/queries.ts` (Hook).
- **Anker:** In `contracts.ts` neben `DemoSummaryResponseSchema`; in `queries.ts` neben
  `useAccountSummary`.
- **Ist:** Es gibt nur das Schema und den Hook für die Einzelgebäude-Zusammenfassung.
- **Soll:** Ein neues Validierungsschema anlegen, das die Antwort von [D1] prüft — mit genau den fünf
  Feldern `buildingCount`, `unitCount`, `occupiedUnitCount`, `vacantUnitCount`, `mietSollCentsMonthly`,
  alle als ganze Zahlen. Dazu einen neuen Abfrage-Hook, der den Endpoint `/a/{accountId}/portfolio/
  overview` aufruft, die Antwort gegen dieses Schema validiert und unter einem eigenen Abfrage-Schlüssel
  (bezogen auf das Konto, z.B. „Konto → Portfolio-Übersicht") zwischenspeichert. Fehlversuche werden
  nicht automatisch wiederholt (wie beim bestehenden Summary-Hook).
- **Default:** Namensgebung analog zum Bestehenden (Schema mit Endung `…ResponseSchema`, Hook mit
  Präfix `use…`). Der bestehende Summary-Hook bleibt erhalten (andere Screens nutzen ihn evtl.), wird
  vom Dashboard aber nicht mehr aufgerufen.
- **Beschreibung (statt Code):** Das Schema ist das Frontend-Gegenstück zum Backend-Schema aus [D1]; es
  fängt eine abweichende Antwort an der Grenze ab, statt fehlerhafte Werte zu rendern. Der Hook kapselt
  den Abruf so, dass das Dashboard nur „Daten / lädt / Fehler" unterscheiden muss.
- **Akzeptanz:** Die Typprüfung (`bun run typecheck`) bleibt grün; der neue Hook wird in `dashboard.tsx`
  importiert und verwendet.
- **Nicht tun:** Den bestehenden Summary-Hook löschen.

### [D3] Demo-/Mock-Finanzdaten (aus echtem Mietsoll abgeleitet)
- **Datei:** neu `apps/web/src/features/portal/dashboard-demo.ts`.
- **Anker:** neue Datei.
- **Ist:** Es gibt keine Zahlungs-, Cashflow- oder Ticketdaten.
- **Soll:** Eine klar benannte Demo-Helferdatei, die aus dem echten `mietSollCentsMonthly` (aus [D1])
  stimmige Mock-Werte ableitet. Alles ist deterministisch (keine Zufallswerte zur Laufzeit — dieselben
  Eingaben ergeben immer dieselbe Ausgabe), klar als Demo erkennbar benannt, wird nirgends gespeichert
  und fließt in keine Abrechnung ein.
- **Default (Ableitungen, in Worten):**
  - **Eingegangene Miete:** 82 % des echten Mietsolls (Faktor 0,82). So ist der spätere Vollständigkeits-
    Ring immer plausibel gefüllt und bewegt sich mit dem echten Mietsoll.
  - **Offene Posten:** Mietsoll minus eingegangene Miete (also die restlichen 18 %). **Offene Mieter:**
    fester Demo-Wert 2.
  - **Cashflow, 12 Monate:** für jeden der letzten 12 Monate (von heute rückwärts, Monatskürzel wie
    „Sep", „Okt" … „Aug") wird ein Einnahmenwert aus dem echten Mietsoll multipliziert mit einer festen
    Faktor-Reihe gebildet — die Reihe schwankt leicht um 1,0 und ist im letzten (laufenden) Monat
    bewusst niedriger (etwa 0,82), damit „noch nicht alles eingegangen" sichtbar wird. Die Ausgaben
    eines Monats sind 38 % seiner Einnahmen. Der Überschuss eines Monats ist Einnahmen minus Ausgaben.
    Alle Beträge in Cent, ganzzahlig gerundet.
  - **Aufgaben/Ticket-Zähler (fest, Mock):** 5 überfällig, 10 heute fällig, 20 diese Woche fällig.
- **Beschreibung (statt Code):** Die Datei stellt eine Hilfsfunktion bereit, die als Eingabe den echten
  Mietsoll-Cent-Betrag bekommt und als Ergebnis ein Objekt mit eingegangener Miete, offenen Posten,
  Anzahl offener Mieter und der 12-Monats-Cashflow-Reihe liefert; die Task-Zähler sind eine feste
  Konstante. Weil alles aus dem echten Mietsoll skaliert, passen die Demo-Zahlen größenmäßig immer zu
  den echten Kennzahlen.
- **Akzeptanz:** Eine Suche nach dem Namen der Hilfsfunktion und der Task-Zähler-Konstante findet sie
  nur in dieser Demo-Datei (Definition) und in den Dashboard-Dateien (Nutzung) — nicht in Statement-,
  Kosten- oder Beleg-Dateien.
- **Nicht tun:** Mock-Werte irgendwo speichern oder in Abrechnungs-/Kosten-Abläufe einspeisen.

### [D4] Obere Reihe — drei Kennzahl-Karten (Ring nur mit echtem Nenner)
- **Datei:** `apps/web/src/features/portal/dashboard.tsx`; die Präsentations-Bausteine (Ring-Karte
  usw.) in einer neuen Datei `apps/web/src/features/portal/dashboard-widgets.tsx`.
- **Anker:** In `dashboard.tsx` der Block mit den drei alten Karten (das Raster, das die Karten „Objekt",
  „Einheiten", „Mietverhältnisse" enthält).
- **Ist:** Drei Karten für EIN Gebäude (Gebäudename, Einheitenzahl, Zahl der Mietverhältnisse).
- **Soll:** Diese drei Karten durch drei Portfolio-Kennzahl-Karten ersetzen. Ein Ring erscheint nur
  dort, wo es ein echtes Verhältnis (einen Nenner) gibt:
  1. **Mieteinnahmen (laufender Monat):** große Zahl ist die eingegangene Miete in Euro (Mock aus [D3]),
     dazu ein Ring, dessen Füllung dem Verhältnis eingegangene Miete zu Mietsoll entspricht (der Nenner
     Mietsoll ist echt). Kleines Label „Mieteinnahmen · lfd. Monat".
  2. **Vermietungsstand:** große Zahl im Format „vermietet / gesamt" (echt aus [D1]), dazu ein Ring,
     dessen Füllung dem Verhältnis vermietete zu allen Einheiten entspricht. Label „Einheiten
     vermietet". Sind alle vermietet, zusätzlich der ruhige positive Hinweis „Voll vermietet".
  3. **Offene Posten:** große Zahl ist der offene Betrag in Euro (Mock aus [D3]), Label „N Mieter offen"
     (N aus [D3]). **Kein Ring** — ein absoluter Euro-Betrag ohne sinnvollen Nenner bekommt keinen
     dekorativen Ring.
- **Default (Styling, Ring und Verhalten):**
  - Jede Karte trägt den Marken-Akzent aus `00` A5: linke grüne Akzentkante, das Label in `text-forest`,
    die große Zahl in `text-ink`. Das Kennzahl-Raster nutzt natürliche Kartenhöhe (aus `00` A6, keine
    erzwungene feste Höhe).
  - **Beschreibung des Rings (statt Code):** ein kreisförmiger Fortschrittsring als SVG. Die Spur (der
    volle Kreis im Hintergrund) ist in `mint` gehalten, der gefüllte Bogen in `green`. Der Füllanteil
    entspricht Wert geteilt durch Nenner, gedeckelt bei 100 %. Ist der Nenner 0, bleibt der Ring leer
    (kein Rechenfehler, keine „NaN"-Anzeige). Der Ring sitzt links, die Zahl mit Label rechts daneben.
  - Euro-Beträge werden über das bestehende Format-Hilfsmittel (`apps/web/src/lib/format.ts`) im
    deutschen Format dargestellt (Punkt als Tausender-, Komma als Dezimaltrenner, „ €").
  - **Klickziele:** Die Vermietungsstand-Karte ist ein Link auf die Objektliste (`/a/{accountId}/
    objekte`, existiert). Die Karten „Mieteinnahmen" und „Offene Posten" tragen ihre Beschriftung
    („Zur Finanzübersicht", „Offene Mieten anzeigen") als **nicht-navigierende** Affordanz (kein Link,
    Standard-Cursor), weil die Zielseiten noch nicht existieren — als Build-Note vermerken.
  - **Erwartetes Ergebnis:** Oben drei gleich hohe Karten mit grünem Akzent; die ersten beiden mit
    Ring, die dritte ohne. Im Demo-Szenario zeigt „Vermietungsstand" z.B. „2 / 3", die beiden
    Geld-Karten zeigen aus dem Mietsoll abgeleitete, stimmige Beträge.
- **Akzeptanz:** Das Dashboard zeigt drei Portfolio-Kennzahl-Karten; die ersten beiden haben einen
  SVG-Ring, die dritte nicht. Eine Suche nach dem Feld „Gebäudename" im Dashboard findet keinen Treffer
  mehr im Kennzahl-Block. Im Demo-Konto sind Vermietungsstand und die abgeleiteten Beträge größer 0.
- **Nicht tun:** Einen globalen Objekt-Filter/-Umschalter einführen (A4). Ein zweites Grün oder neue
  Farben einführen (A5). Einen einzelnen Gebäudenamen als Karten-Titel zeigen (kein Einzelobjekt im
  Portfolio-Dashboard). Leerstand als Fehler/rot darstellen — Leerstand ist normal, keine Warnung.

### [D5] Cashflow-Widget — Senkrechtbalken, Überschuss-Linie, Zeit-Umschalter
- **Datei:** Baustein in `apps/web/src/features/portal/dashboard-widgets.tsx`, eingebunden in
  `dashboard.tsx` unterhalb der Kennzahl-Reihe.
- **Anker:** neuer Baustein „Cashflow-Diagramm".
- **Ist:** Kein Cashflow-Widget vorhanden.
- **Soll:** Ein handgezeichnetes SVG-Diagramm mit der 12-Monats-Reihe aus [D3]: je Periode zwei
  gruppierte **senkrechte Balken** (Einnahmen und Ausgaben) und darüber eine **Überschuss-Linie** (ein
  durchgehender Linienzug über die Überschuss-Werte). Oben rechts ein **Zeit-Umschalter** mit den
  Stufen Jahr / Quartal / Monat, Standard ist Jahr.
- **Default (Inhalt, Umschalter, Design):**
  - **Jahr** zeigt 12 Monatsgruppen. **Quartal** fasst die 12 Monate zu 4 Quartalen zusammen (Summen je
    Quartal, Quartals-Beschriftung). **Monat** zeigt nur den laufenden (letzten) Monat als eine
    Balkengruppe, mit den drei Euro-Werten daneben. (Eine Wochen-Aufschlüsselung im Monat ist eine
    spätere Option → Build-Note.)
  - **Überschrifts-Kennzahl:** über dem Diagramm der Überschuss des laufenden Monats als große Zahl
    (`font-display`, `text-ink`) mit Label „Überschuss · lfd. Monat".
  - **Tooltip:** Beim Überfahren einer Balkengruppe erscheint ein kleiner Kasten mit der Periode und den
    drei Beträgen (Einnahmen, Ausgaben, Überschuss) in Euro.
  - **Design gegen den „Minitab-Look":** Einnahmen-Balken in `green`, Ausgaben-Balken in `slate`, die
    Überschuss-Linie in `forest`. Gitterlinien entweder weglassen oder sehr dezent in `mint`.
    Achsenbeschriftung klein in `slate`. Balkenenden leicht abgerundet. Großzügige Abstände, kein
    Rahmen, kein Schlagschatten, kein 3D. Eine dezente Legende oben (Einnahmen / Ausgaben / Überschuss)
    kennzeichnet jede Reihe mit Farbe **und** Text. Der Umschalter als schlichte Segment-Schalter oder
    Auswahlfeld in den Tokens.
  - **Desktop/Laptop:** Das SVG skaliert zwischen 1280 und 1920 Pixel mit seiner Fläche; die Seite
    selbst scrollt nicht horizontal. Eine mobile Diagrammvariante ist Post-Pitch.
  - **Erwartetes Ergebnis:** Ein aufgeräumtes, markiges Diagramm über die volle Breite: 12
    Monatsgruppen (Standard Jahr), darüber die Überschuss-Linie und die Überschrifts-Kennzahl;
    Umschalten auf Quartal ergibt 4 Gruppen, auf Monat eine Gruppe.
- **Akzeptanz:** Das Widget rendert im Standard 12 Balkengruppen, eine Überschuss-Linie und die
  Überschrifts-Kennzahl. Umschalten auf Quartal ergibt 4 Gruppen, auf Monat eine. Im `package.json`-Diff
  taucht keine neue Diagramm-Bibliothek auf. Der Tooltip erscheint beim Überfahren.
- **Nicht tun:** Eine neue Diagramm-Dependency hinzufügen. Liegende (waagerechte) Balken. „Soll" als
  eigene Reihe in den Cashflow mischen (Soll ist eine Zielgröße, kein Zahlungsstrom).

### [D6] Aufgaben & Tickets — Zählerleiste (kein Board)
- **Datei:** Baustein in `apps/web/src/features/portal/dashboard-widgets.tsx`, eingebunden in
  `dashboard.tsx` unterhalb des Cashflow-Widgets.
- **Anker:** neuer Baustein „Aufgaben-Zählerleiste".
- **Ist:** Nicht vorhanden.
- **Soll:** Eine kompakte Leiste mit drei Zählern (Mock aus [D3]), in dieser Reihenfolge und Gewichtung:
  **überfällig zuerst und optisch am lautesten**, dann heute fällig, dann diese Woche fällig. Ein volles
  Kanban-Board gehört NICHT aufs Dashboard (das lebt später auf der eigenen Vorgänge-Seite).
- **Default (Inhalt, Stil, Verweis):**
  - Reihenfolge und Farbe: „5 überfällig" in `text-danger` und betont → „10 heute fällig" in `text-ink`
    → „20 diese Woche fällig" in `text-slate`. Jeder Zähler zeigt Zahl **und** Wortlabel (BFSG).
  - Eine Karte mit dem Titel „Aufgaben & Tickets" umschließt die Leiste; kleiner Hinweistext darunter:
    „Aus Mieter-Tickets & eigenen Aufgaben."
  - Jeder Zähler ist eine **nicht-navigierende** Affordanz (kein Link), weil die Vorgänge-/Ticket-Seite
    noch fehlt — als Build-Note vermerken.
  - **Verweis auf das kommende Ticket-System:** an der Komponente einen Code-Kommentar hinterlegen, der
    festhält, dass Zähler und Klickziel später an das eigene Ticket-System-Spec angebunden werden und den
    Mock ersetzen (Marker „TODO(ticket-spec)").
  - **Erwartetes Ergebnis:** eine ruhige Leiste, in der „überfällig" sofort ins Auge fällt und die
    beiden anderen Zähler daneben stehen.
- **Akzeptanz:** Das Dashboard zeigt die drei Zähler in der Reihenfolge überfällig → heute → diese
  Woche; „überfällig" in der Danger-Farbe. Eine Suche nach dem Marker „TODO(ticket-spec)" findet genau
  einen Treffer.
- **Nicht tun:** Ein volles Kanban-Board aufs Dashboard bauen. Echte Ticket-Daten erfinden oder
  speichern.

### [D7] Dashboard zusammensetzen — Layout, Zustände, Demo-Flow erhalten
- **Datei:** `apps/web/src/features/portal/dashboard.tsx`.
- **Anker:** die Funktion `Dashboard` (gesamter Render), die Hilfsfunktion `PageFrame`, und die
  bestehende Demo-Reset-Karte.
- **Ist:** `Dashboard` lädt die Einzelgebäude-Zusammenfassung, zeigt ein Lade-Skeleton, einen
  404-Leerzustand mit „Demo-Szenario laden", die drei Einzelgebäude-Karten, eine Abrechnungs-Karte mit
  Gebäudename und (für Owner) die Demo-Reset-Karte.
- **Soll:** Die Datenquelle auf den neuen Portfolio-Übersicht-Hook (aus [D2]) umstellen und in dieser
  Reihenfolge rendern: 1) den Kopf aus `PageFrame` mit „Übersicht" und „Ihr Bestand auf einen Blick.";
  2) die Kennzahl-Reihe [D4]; 3) das Cashflow-Widget [D5]; 4) die Aufgaben/Tickets-Leiste [D6]; 5) eine
  untere Reihe mit der „Abrechnung erstellen"-Karte und (nur Owner) der Demo-Reset-Karte.
- **Default (Zustände, in Worten):**
  - **Lade-Skeleton:** das bestehende Muster beibehalten (ruhige Mint-Flächen, kein hartes Aufblitzen),
    an die neue Kennzahl-Reihe angepasst.
  - **Leerzustand:** wenn die Portfolio-Übersicht `buildingCount` gleich 0 liefert **oder** der Abruf
    einen 404 ergibt, die bestehende „Noch keine Daten / Demo-Szenario laden"-Karte samt Owner-Gating
    **erhalten** (das Demo-Runbook hängt daran). Ob der Nutzer Owner ist, wird weiter über den
    bestehenden „me"-Hook bestimmt.
  - **Fehlerzustand:** ist die API nicht erreichbar, die bestehende „Fehler beim Laden"-Karte
    beibehalten.
  - **Abrechnungs-Karte:** Titel „Abrechnung erstellen", Text „Betriebs- und Heizkostenabrechnung —
    centgenau, mit CO₂-Aufteilung und Rechtsstand." (ohne Gebäudename), Link auf `/a/{accountId}/
    abrechnung` (existiert, demo-relevant).
  - **Demo-Reset-Karte:** unverändert in Funktion und Owner-Gating.
- **Akzeptanz:** Das Dashboard lädt ohne den alten Summary-Hook. Reihenfolge: Kopf → Kennzahlen →
  Cashflow → Aufgaben → (Abrechnung + Demo-Reset). Ein leeres Konto zeigt weiterhin „Demo-Szenario
  laden" (Owner), die Reset-Karte funktioniert unverändert. Bestehende Tests bleiben grün; prüft ein
  Test hart auf die alten drei Karten, wird er an die neue Struktur angepasst und das in Build-Notes
  vermerkt.
- **Nicht tun:** Die Demo-Reset-Karte, den Demo-Lade-Fluss oder deren Owner-Gating entfernen. Den
  Abrechnungs-Link kappen. Einen globalen Objekt-Filter einführen.

---

## Leerer Zustand (neuer Account, noch keine Daten)

Statt leerer Widgets zeigt das Dashboard den nächsten sinnvollen Schritt: den bestehenden Leerzustand
mit „Demo-Szenario laden" (Owner) bzw. „Erstes Objekt anlegen". Kennzahl-Karten mit Nenner 0 zeigen
einen ruhigen leeren Ring statt „0/0"; Geld-Karten ohne Daten zeigen einen neutralen Hinweis statt einer
nackten 0. So wird der leere Zustand zum Onboarding, nicht zur Sackgasse.

## Out of Scope (bewusst NICHT hier — nichts davon gelöscht, nur verortet)

- **Kostenstruktur-Donut** und **Objektstatus-Liste** (aus der früheren Dashboard-Fassung): **nicht
  gelöscht, sondern verschoben.** Die Objektstatus-Liste wird ein optionales Add-Widget im
  Personalisierungs-Spec (`02`); der Kostenstruktur-Donut ist Backlog-Stufe 2. Sie gehören nicht in den
  cleanen Default.
- **§ 556-Frist / Reminder:** nicht als Dashboard-Widget, sondern in der rechten Reminder-Sidebar
  (eigenes Reminder-System). Bewusst vom Dashboard genommen.
- **Personalisierung / Widget-Katalog** („Dashboard bearbeiten", Add/Remove/Reorder, Persistenz) →
  eigenes Spec `02`, späterer Chat.
- **Ticket-System** (echte Mieter-Tickets, Vorgänge-Seite, Klickziele) → eigenes kommendes Ticket-Spec;
  hier nur der Verweis-Marker in [D6].
- **Echte Finanzdaten** (Zahlungseingänge, Offene Posten, Cashflow-Historie, Soll/Ist) → hängen an
  finAPI/Bankanbindung (verschoben) + Mahnwesen. Hier bewusst Mock, aus echtem Mietsoll abgeleitet.
- **Aggregat-Endpoint-Ausbau** (Warm-Miete/Vorauszahlung, Abrechnungsstatus je Objekt) → später.
- **Top-Bar / PageHeader / Sidebar-Refactor** → `09_App-Shell-Desktop.md`.
- **Smartphone-/Tablet-Dashboard und Touch-spezifische Navigation** → Post-Pitch. Pre-Pitch werden
  1280, 1440 und 1920 Pixel abgenommen.
- Jede bestehende Rechen-/Geld-/Rechtslogik.

## Verifikation (Gesamtergebnis)

- Typprüfung (`bun run typecheck`) grün, bestehende Tests (`bun test`) grün, der neue API-Test aus [D1]
  grün.
- Das Dashboard nutzt nicht mehr den alten Summary-Hook (Suche danach in `dashboard.tsx` ohne Treffer).
- Kein Feld „Gebäudename" mehr im Kennzahl-Block des Dashboards.
- Keine neue Diagramm-Bibliothek im `package.json`.
- Kein Widget zeigt eine nackte 0 oder eine leere weiße Fläche; leere Fälle zeigen einen positiven
  Hinweis.
- Auf der kleinsten Pre-Pitch-Laptopbreite von 1280 Pixel bleiben alle Widgets lesbar und dürfen in der
  Reihenfolge Kennzahlen → Cashflow → Aufgaben → untere Reihe kontrolliert umbrechen.
- Screenshot (Desktop, breit): drei Kennzahl-Karten (die ersten beiden mit Ring, grüner Akzent links),
  Cashflow mit 12 Senkrechtbalken, Überschuss-Linie, Überschrifts-Kennzahl und Jahr/Quartal/Monat-
  Umschalter, Aufgaben-Leiste (überfällig zuerst, in Danger-Farbe), untere Reihe mit Abrechnungs- und
  (Owner) Demo-Reset-Karte.
- Live-Check: im Demo-Szenario ein Mietverhältnis anlegen → Vermietungsstand und die aus dem Mietsoll
  abgeleiteten Beträge ändern sich (die zwischengespeicherte Übersicht wird nachgeladen).

## Reihenfolge

1. D1, D2 — Datenfundament (Endpoint + Schema/Hook).
2. D3 — Demo-Finanzhelfer.
3. D4, D5, D6 — die Widgets.
4. D7 — Zusammenbau und Zustände/Demo-Flow.

---

## Build-Notes (füllt die KI beim Umsetzen aus)

<!-- Jede Annahme, jeder übersprungene MUSS-INPUT-Teil, jede Abweichung hier eintragen. Beispiele:
- [D1] Basisklasse/Alias-Konvention für Schemas hieß im Repo anders — an das Bestehende angepasst.
- [D4] Zielseiten Finanzübersicht/Offene Mieten fehlen — Karten 1+3 als nicht-navigierende Affordanz gebaut.
- [D6] Vorgänge-/Ticket-Seite fehlt — Zähler nicht verlinkt, Marker TODO(ticket-spec) gesetzt.
- [D7] Ein Portal-Test prüfte die alten drei Karten — an die neue Kennzahl-Struktur angepasst.
-->
