---
spec_id: 02-objekte
titel: Objekte — Redesign, zwei Wizards, Karten-Ansicht, Einheiten-Fix, Mietverhältnis-Einstieg
status: freigegeben
prioritaet: hoch
betrifft: apps/web, apps/api, packages/db
abhaengig_von: [00-layout-global]
repo_stand: Lokara-main @ 2026-08-24
---

## Zweck

Die Objekte-Seite (`apps/web/src/features/objekte/`) wird überarbeitet. Vier Dinge:

1. **Ein kaputter Screen wird repariert.** Die Einheiten-Detailseite (`/a/{accountId}/einheiten/{unitId}`)
   zeigt heute „Fehler beim Laden", weil der Zod-Vertrag im Frontend von der API abgedriftet ist. Das
   Anlegen eines Mietverhältnisses würde zusätzlich mit HTTP 422 scheitern, weil der Sende-Payload
   veraltet ist. Beides wird korrigiert.
2. **Das Anlegen läuft künftig über zwei Wizards** statt über die beiden rechten Inline-Formulare:
   Wizard-A legt ein **Objekt** an (zweistufig: Gebäudeart → Eckdaten), Wizard-B legt eine **Einheit**
   an (einstufig, mit Bestätigung und „noch eine Einheit anlegen").
3. **Die Objektliste bekommt oben einen Ansichts-Umschalter Liste ⇄ Karte.** In der Kartenansicht
   erscheinen die Objekte als Stecknadeln auf einer Karte.
4. **Auf der Einheitenseite entsteht ein Einstieg „Jetzt Mietverhältnis erstellen"** mit der Wahl
   zwischen Vertragsgenerator (entsteht parallel, externe Route) und manuellem Einpflegen.

**Dieser Spec enthält keinen Code. Alles ist in Worten beschrieben.** Die ausführende KI schreibt den
Code selbst gegen den echten aktuellen Dateistand.

> **Ehrlicher Scope-Hinweis (bitte lesen):** Dies ist **kein reiner Frontend-Spec**. Die Karten-Ansicht
> und die neuen Stammdaten (Gebäudeart, Wohn-/Nichtwohn-Kennzeichen, Land, Geo-Koordinaten) brauchen
> **neue Datenbank-Spalten + eine Migration + serverseitiges Geocoding** ([O4], [O5]). Das ist echte
> Backend-Arbeit, kein Styling. Sie ist bewusst klein gehalten (fünf Spalten, ein neuer Endpoint-Zusatz),
> aber sie ist da.

> **Was echt ist und was noch nicht:** Objekte, Einheiten und Mietverhältnisse anlegen ist **echt** und
> funktioniert live. Der **Bild-Upload ist es noch nicht** — die App hat heute keinen Objekt-/Datei-Speicher
> (nur fertige Abrechnungs-PDFs liegen als Bytes in der Datenbank). Deshalb werden die Bild-Bereiche in
> dieser Runde nur **sichtbar** angelegt (mit Platzhalter/Beispielbild), aber **kein funktionierender
> Uploader** — echtes Speichern kommt in einer späteren Storage-Runde ([Out of Scope]). Kein Fake-Uploader,
> der so tut, als würde er speichern.

> **Der Vertragsgenerator** (Auswahl in [O11]) **entsteht parallel** und existiert im heutigen Repo-Stand
> noch nicht. Der Button verlinkt auf eine benannte Route; ob diese Route schon existiert, ist der KI beim
> Bauen egal (Next.js rendert notfalls die 404 aus `00` A9). Der genaue Pfad wird mit Emir abgestimmt —
> siehe [O11], Feld „Default".

## Invarianten (zusätzlich zu den Standard-Invarianten)

- Pre-Pitch gilt Desktop/Laptop bei 1280, 1440 und 1920 Pixel sowie 200-Prozent-Zoom. Keine eigene
  Smartphone-/Tablet-Karten-, Drawer- oder Touchnavigation bauen; Tastatur, Screenreader und
  sichtbarer Fokus bleiben verpflichtend.

- Nur vorhandene Design-Tokens (`ink`, `green`, `forest`, `mint`, `slate`, `paper`, `danger`/`warning`/
  `success`) und Hausschriften (`font-display` / `font-sans`). Keine rohen Farbwerte.
- **Genau eine neue Laufzeit-Dependency ist erlaubt:** die Kartenbibliothek **Leaflet** (+ `@types/leaflet`
  als Dev-Dependency; `react-leaflet` nur wenn zwingend nötig und dann **ausschließlich v5+** wegen React
  19 — Details in [O9]) — ausschließlich für Befehl [O9].
  Sonst **keine** neue Dependency. Insbesondere **kein** neues Dialog-/Modal-/Dropdown-Paket: Beide Wizards
  sind **eigene Seiten (Routen)**, keine Modals. Das umgeht, dass `@lokara/ui` heute keine Dialog-Komponente
  hat.
- **Kollision mit dem späteren Objekt-Dashboard-Spec:** Die Datei `building-detail-page.tsx` wird später
  von einem eigenen Spec zu einer KPI-/Widget-Sicht umgebaut. Dieser Spec fasst dort **nur den
  Einheiten-Block und den Anlege-Einstieg** an — **nicht** das Seitengerüst, nicht den Kopfbereich in eine
  Widget-Struktur umbauen. Minimal-invasiv bleiben.
- **Kein Widget/keine Liste rendert je eine nackte leere weiße Fläche.** Leerzustände bekommen einen
  positiven, aufgelösten Text oder einen Onboarding-Hinweis mit Weg zur nächsten Aktion (bestehendes
  Muster, z. B. „Noch keine Einheiten").
- **Keine bestehende Rechen-, Rechts- oder Geldlogik verändern.** Der Contract-Fix ([O1]–[O3]) korrigiert
  nur die Übertragung/Anzeige, nicht die Beträge selbst. Die NK-/Heizkosten-/CO₂-Engines bleiben unberührt.
- Portfolio-Standard-Modell (aus `00` A4): **kein globaler Objekt-Filter/-Umschalter**. Der Ansichts-Toggle
  in [O8] schaltet nur die Darstellung derselben vollständigen Objektliste um (Liste vs. Karte) — er filtert
  nichts und wählt kein Einzelobjekt aus.
- Signal nie nur über Farbe (BFSG): jede Status-/Typ-Kennzeichnung zusätzlich mit Text.
- Marken-Akzent und Kartenhöhen aus `00` A5/A6 erben, wo neue Karten entstehen.
- **Neue App-Router-Seiten ([O6], [O10]) liegen im selben account-gescopeten Segment wie die bestehenden
  Objekt-Seiten** (dieselbe Route-Group unter `a/[accountId]/…`), damit die App-Shell (Sidebar, Kopf,
  Session/Autorisierung aus `00`) sie umschließt. Keine Seite außerhalb dieses Segments anlegen (sonst
  fehlt der Rahmen und/oder die RLS-Absicherung).
- **Nach dem Entfernen der beiden rechten Inline-Formulare ([O7], [O10]) alle dadurch ungenutzten Importe
  entfernen** (z. B. `useForm`, `zodResolver`, `useFormDraft`, `FormField`, das jeweilige lokale
  Zod-Schema), damit Lint/Typecheck sauber bleiben. Kein toter Code.
- Bei Unklarheit: naheliegendste Variante umsetzen, **nicht anhalten**, Annahme in `## Build-Notes`.
- `⚠️ MUSS-INPUT`-Werte nie erfinden — Teilpunkt überspringen + loggen, Rest umsetzen.

**Verhältnis zu `00_Layout-Global.md`:** A2 (Dev-Copy raus), A3 (Container-Breite/Padding), A4 (kein
globaler Objekt-Filter) und der Marken-Akzent A5/A6 gelten weiter. Der bestehende Untertitel der
Objektseite („Gebäude mit ihren Einheiten und Mietverhältnissen. Ein Klick auf ein Objekt öffnet die
Einheiten.") wird durch [O7] leicht angepasst, weil das Anlegen jetzt über einen Button statt über ein
rechtes Formular läuft.

---

## Reihenfolge / Bau-Empfehlung

Zuerst der Fix-Cluster ([O1], [O2], [O3], [O3b]) — er ist unabhängig, macht einen aktuell kaputten
Screen wieder heil und hält Typecheck/Tests grün. Dann das Datenmodell ([O4], [O5]) als Fundament für
Wizard-A und Karte. Dann die Wizards ([O6], [O7], [O10]), der Toggle + Karte ([O8], [O9]), der
Mietverhältnis-Einstieg ([O11]) und zuletzt die Bild-Slots ([O12]).

---

## Befehle

### [O1] Einheiten-Detailseite reparieren — Zod-Vertrag auf das echte API-Format ziehen

- **Datei/Ort:** `apps/web/src/lib/contracts.ts`, das Schema-Objekt `TenancyOutSchema`.
- **Fundstelle:** Das Objekt, das aktuell mit `export const TenancyOutSchema = z.object({` beginnt und die
  Felder `renterNames`, `validFrom`, `validTo`, `baseRentCents`, `baseRentEur`, `advancePaymentCents`,
  `advancePaymentEur`, `activeToday` enthält.
- **Ist:** Das Schema verlangt zwei Felder `advancePaymentCents` (Ganzzahl) und `advancePaymentEur`
  (String). Die API liefert diese Felder aber **nicht mehr**: seit Migration `0015_m6_temporal_advances`
  gibt die API stattdessen eine **Liste** unter dem Feld `advancePaymentSchedule` zurück (siehe
  `apps/api/src/lokara_api/schemas.py`, Klasse `TenancyOut`, Feld `advance_payment_schedule`, auf dem Draht
  camelCase `advancePaymentSchedule`). Weil das Zod-Schema das alte Format erzwingt, schlägt das Parsen der
  echten Antwort fehl, und wegen `retry: false` landet die Seite sofort im roten „Fehler beim Laden"-Zustand.
- **Soll:** Im `TenancyOutSchema` die beiden Felder `advancePaymentCents` und `advancePaymentEur`
  **entfernen** und durch **ein** Feld `advancePaymentSchedule` ersetzen: eine Liste (Array) von Objekten.
  Jedes Objekt der Liste hat die Felder `id` (String), `amountCents` (Ganzzahl), `amountEur` (String),
  `validFrom` (String), `validTo` (String **oder** null), `predecessorId` (String **oder** null),
  `declarationRef` (String). Diese Feldnamen und Typen entsprechen exakt der API-Klasse
  `AdvancePaymentPeriodOut` in `schemas.py` (camelCase auf dem Draht). Das Listen-Element als **eigenes,
  exportiertes Unter-Schema** definieren (z. B. `AdvancePaymentPeriodOutSchema`) und im
  `TenancyOutSchema` als `z.array(...)` verwenden — nicht anonym inline, damit es wiederverwendbar und
  testbar ist. Der zugehörige exportierte Typ (`TenancyOut`) bleibt aus dem Schema abgeleitet.
- **Abhängige Stellen (mitprüfen, sonst bricht der Typecheck):** `TenancyOutSchema` wird in
  `contracts.ts` von `UnitDetailResponseSchema` (Feld `tenancies: z.array(TenancyOutSchema)`) benutzt —
  das bleibt gültig, keine Änderung nötig. **Aber** der abgeleitete Typ `TenancyOut` wird zusätzlich von
  `tenancy-timeline.tsx` (nur Zeitfelder) und von `tenancy-timeline.test.ts` (baut ein Fixture im **alten**
  Feldformat) importiert. Das Test-Fixture wird durch [O3b] nachgezogen; `tenancy-timeline.tsx` selbst
  liest keine Vorauszahlungsfelder und braucht keine Änderung.
- **Erwartetes Ergebnis:** Die Antwort des Endpoints `GET /a/{accountId}/units/{unitId}` wird vom
  Zod-Schema **ohne Fehler** geparst. Die Einheiten-Detailseite lädt und zeigt ihren Inhalt (Zeitstrahl +
  Mietverhältnis-Tabelle), statt den roten Fehlerkasten. Für ein Mietverhältnis mit genau einer
  Vorauszahlungs-Periode enthält `advancePaymentSchedule` genau ein Element; bei einer späteren Anpassung
  der Vorauszahlung mehrere.
- **Akzeptanz:** In `contracts.ts` kommen die Zeichenketten `advancePaymentCents` und `advancePaymentEur`
  im `TenancyOutSchema` nicht mehr vor; `advancePaymentSchedule` mit den sieben genannten Unterfeldern ist
  vorhanden. Im laufenden Demo-Build öffnet die Einheitenseite von „Wohnung A (EG links)" ohne „Fehler beim
  Laden". Die Typprüfung (`bun run typecheck` bzw. das Projekt-Äquivalent) bleibt sauber.
- **Nicht tun:** Keine anderen Schemas in `contracts.ts` anfassen. Keine Beträge/Formatierung ändern.

### [O2] NK-Vorauszahlung in der Mietverhältnis-Tabelle aus der Schedule-Liste anzeigen

- **Datei/Ort:** `apps/web/src/features/objekte/unit-detail-page.tsx`, die Mietverhältnis-Tabelle in
  `UnitDetailPage`.
- **Fundstelle:** Die Tabellenzelle, die aktuell den Wert `tenancy.advancePaymentEur` in der Spalte
  „NK-Vorauszahlung" ausgibt (die letzte Zelle jeder Zeile, rechtsbündig, `tabular-nums`), sowie die
  Kopfzeile „NK-Vorauszahlung".
- **Ist:** Die Zelle liest `tenancy.advancePaymentEur` — ein Feld, das es nach [O1] nicht mehr gibt. Ohne
  Änderung würde die Datei nicht mehr typprüfen.
- **Soll:** Die Zelle stattdessen aus `tenancy.advancePaymentSchedule` den **heute gültigen** Betrag
  anzeigen: das Perioden-Element, dessen `validFrom` am oder vor dem heutigen Tag liegt und dessen
  `validTo` leer (null) ist oder nach heute liegt. Gibt es kein heute gültiges Element (z. B. bei einem
  rein zukünftigen oder rein vergangenen Mietverhältnis), das **zeitlich letzte** Element (größtes
  `validFrom`) verwenden. Angezeigt wird dessen `amountEur`. Ist die Liste leer, „—" anzeigen (der
  Leerzustand-Strich, gedämpft).
- **Default:** Auswahlregel „heute gültige Periode, sonst die zeitlich letzte". Anzeige des `amountEur`
  unverändert als bereits formatierter Euro-String (keine erneute Formatierung).
- **Erwartetes Ergebnis:** Die Spalte „NK-Vorauszahlung" zeigt für jedes Mietverhältnis denselben Wert
  wie zuvor (bei genau einer Periode identisch), rechtsbündig in `tabular-nums`. Die Seite typprüft und
  rendert. Kein Verweis mehr auf ein nicht existentes Einzelfeld.
- **Akzeptanz:** In `unit-detail-page.tsx` kommt `advancePaymentEur` nicht mehr vor. Die Tabelle zeigt für
  „Wohnung A (EG links)" einen plausiblen NK-Vorauszahlungsbetrag. Typprüfung sauber.
- **Nicht tun:** Den Zeitstrahl (`TenancyTimeline`) oder die Kaltmiete-Spalte nicht anfassen. Keine
  Beträge umrechnen.

### [O3] Mietverhältnis-Anlegen: Sende-Payload auf das echte API-Format bringen

- **Datei/Ort:** `apps/web/src/features/objekte/queries.ts` (Hook `useCreateTenancy` + zugehöriges
  Eingabe-Interface `TenancyCreateInput`) **und** `apps/web/src/features/objekte/unit-detail-page.tsx`
  (das `onSubmit` in `CreateTenancyForm` sowie das Formular selbst).
- **Fundstelle:** In `queries.ts` das Interface, das aktuell mit `interface TenancyCreateInput {` beginnt
  und die Felder `renterName`, `validFrom`, `validTo`, `baseRentCents`, `advancePaymentCents` hat. In
  `unit-detail-page.tsx` der `create.mutate(...)`-Aufruf, der aktuell ein Objekt mit `baseRentCents` und
  `advancePaymentCents` übergibt.
- **Ist:** Das Frontend sendet `advancePaymentCents`. Die API-Klasse `TenancyCreate` (in `schemas.py`)
  erwartet aber `initialAdvancePaymentCents` (Ganzzahl ≥ 0) **und** `advanceDeclarationRef` (nicht-leerer
  String, max. 500 Zeichen). Ein POST im alten Format schlägt mit HTTP 422 fehl → das Anlegen ist kaputt.
- **Soll:** Das Sende-Format umstellen. Das Feld `advancePaymentCents` im Payload umbenennen in
  `initialAdvancePaymentCents` und zusätzlich ein Feld `advanceDeclarationRef` mitsenden. Der Wert für
  `advanceDeclarationRef` kommt aus einem **neuen optionalen Formularfeld** „Grundlage der
  NK-Vorauszahlung" (siehe Default). Interface und Typen in `queries.ts` entsprechend anpassen; der
  Response-Typ des Hooks bleibt `TenancyOutSchema` (nach [O1] korrekt).
- **Default:** Neues Formularfeld „Grundlage der NK-Vorauszahlung" (einzeiliger Text) mit vorbelegtem
  Default **„Mietvertrag"**. Der Nutzer kann ihn überschreiben; leer lassen ist nicht erlaubt (dann gilt
  der Default). Dieses Feld ist eine freie Herkunftsangabe, **kein** rechenrelevanter Betrag — daher kein
  `⚠️ MUSS-INPUT`, der Default ist zulässig.
- **Erwartetes Ergebnis:** Ein neu angelegtes Mietverhältnis wird von der API mit HTTP 201 angenommen. Der
  „Fehler beim Anlegen"-Zustand tritt nur noch bei echten Konflikten auf (überlappender Zeitraum → 422 mit
  der bestehenden Überschneidungs-Meldung). Nach dem Anlegen erscheint die neue Zeile in der Tabelle und
  im Zeitstrahl. Das Formular zeigt zusätzlich das Feld „Grundlage der NK-Vorauszahlung" (vorbelegt mit
  „Mietvertrag") zwischen der NK-Vorauszahlung und dem Absende-Button.
- **Akzeptanz:** In `queries.ts` und `unit-detail-page.tsx` kommt `advancePaymentCents` als Sende-Feld
  nicht mehr vor; `initialAdvancePaymentCents` und `advanceDeclarationRef` werden gesendet. Im Demo-Build
  lässt sich für eine leerstehende Einheit ein Mietverhältnis anlegen, ohne dass 422 wegen Feldnamen
  auftritt. Typprüfung sauber.
- **Nicht tun:** Die Überlappungsprüfung, die Kaltmiete-Umrechnung (`parseEurToCents`) oder die
  Unveränderlichkeits-Semantik nicht ändern.

### [O3b] Test-Fixture von `tenancy-timeline` an das neue Vertragsformat anpassen

- **Datei/Ort:** `apps/web/src/features/objekte/tenancy-timeline.test.ts`.
- **Fundstelle:** Die Hilfsfunktion, die aktuell mit `function tenancy(validFrom: string, validTo: string
  | null, name: string): TenancyOut {` beginnt und ein Objekt mit den Feldern `baseRentCents`,
  `baseRentEur`, `advancePaymentCents`, `advancePaymentEur`, `activeToday` zurückgibt.
- **Ist:** Das Fixture konstruiert einen `TenancyOut` mit den **alten** Feldern `advancePaymentCents: 0`
  und `advancePaymentEur: ''`. Nach [O1] gibt es diese Felder im Typ `TenancyOut` nicht mehr, dafür fehlt
  das neue Pflichtfeld `advancePaymentSchedule` — der Typecheck (`tsc`) und `vitest` würden hier brechen.
- **Soll:** Im Fixture die beiden Felder `advancePaymentCents` und `advancePaymentEur` entfernen und
  stattdessen `advancePaymentSchedule` als **leere Liste** (`[]`) setzen. Alle übrigen Felder unverändert
  lassen. Die Testfälle selbst (Segment-Logik über `buildSegments`) bleiben inhaltlich unangetastet — sie
  nutzen nur die Zeitfelder.
- **Erwartetes Ergebnis:** `tenancy-timeline.test.ts` typprüft wieder und läuft grün; das Fixture spiegelt
  das echte `TenancyOut`-Format nach [O1].
- **Akzeptanz:** In `tenancy-timeline.test.ts` kommen `advancePaymentCents`/`advancePaymentEur` nicht mehr
  vor; `advancePaymentSchedule: []` ist gesetzt. `bun run test` (Web) und `bun run typecheck` sind grün.
- **Nicht tun:** Keine Testfälle löschen oder ihre Erwartungen ändern. Kein Vorauszahlungsbetrag ins
  Fixture erfinden (leere Liste genügt für die Zeitstrahl-Tests).

### [O4] Datenmodell: fünf neue Spalten am Gebäude + Migration

- **Datei/Ort:** `packages/db/src/lokara_db/models.py` (Klasse `Building`) und eine **neue
  Alembic-Migration** unter `packages/db` (Verzeichnis der bestehenden Migrationen, z. B. neben
  `0015_m6_temporal_advances`).
- **Fundstelle:** Die Modellklasse für Gebäude (`class Building`) mit ihren heutigen Feldern `name`,
  `street`, `postal_code`, `city` und der Beziehung zu `units`.
- **Ist:** Ein Gebäude kennt nur Name und Adresse. Es gibt keine Gebäudeart, keine Wohn-/Nichtwohn-Angabe,
  kein Land und keine Geo-Koordinaten.
- **Soll:** Am Gebäude fünf Spalten ergänzen und per Migration nachziehen. **Jede der drei
  Nicht-Geo-Spalten ist NOT NULL mit einem DB-seitigen `server_default`** — das ist entscheidend, damit
  bestehende Insert-Pfade, die die neuen Spalten nicht kennen (v. a. der Demo-Seed `lokara-seed-demo`,
  der Gebäude direkt über das ORM anlegt), **nicht brechen**:
  1. `building_type` — **kein Postgres-ENUM-Typ**, sondern `VARCHAR` mit einer **CHECK-Bedingung** auf
     genau die vier erlaubten Werte `WOHN_UND_GESCHAEFTSHAUS`, `WOHNHAUS`, `GEWERBEIMMOBILIE`,
     `EINFAMILIENHAUS`. NOT NULL, `server_default = 'WOHNHAUS'`. (VARCHAR+CHECK statt nativem Enum, weil
     das spätere Erweitern eines PG-Enum-Typs per Alembic fehleranfällig ist.)
  2. `is_residential` — Wahrheitswert (Wohngebäude ja/nein), rechtlich relevant für die Engines. NOT NULL,
     `server_default = true`.
  3. `country` — `VARCHAR`, Ländername. NOT NULL, `server_default = 'Deutschland'`.
  4. `latitude` — Fließkomma, **nullbar** (kein Default).
  5. `longitude` — Fließkomma, **nullbar** (kein Default).
- **Default:** Die drei `server_default`-Werte oben (`WOHNHAUS`, `true`, `Deutschland`) gelten sowohl für
  Bestandszeilen (Backfill durch die Migration) **als auch** für künftige Inserts ohne die Felder. Die
  vier Enum-Werte sind verbindlich (kein `⚠️ MUSS-INPUT` — Struktur-Schlüssel, keine Rechtswerte). Falls
  `models.py` die Spalten zusätzlich auf ORM-Ebene absichern soll, dort denselben `server_default`
  setzen, damit ORM-Inserts und DB übereinstimmen.
- **Erwartetes Ergebnis:** `alembic upgrade head` läuft sauber durch; bestehende Gebäude erhalten die
  Default-Werte. **Ein Insert ohne die neuen Spalten (z. B. der Seed) gelingt weiterhin**, weil die DB
  die `server_default`-Werte einsetzt. Ein Downgrade entfernt die fünf Spalten und die CHECK-Bedingung
  restlos.
- **Akzeptanz:** Migration idempotent und reversibel (up/down sauber). Nach `lokara-seed-demo` **ohne
  Fehler** hat „Musterstraße 12" `building_type = WOHNHAUS`, `is_residential = true`, `country =
  Deutschland`. Ein Insert eines Gebäudes mit einem Wert außerhalb der vier Enum-Werte wird von der
  CHECK-Bedingung abgelehnt. Die Python-Testsuite bleibt grün.
- **Nicht tun:** Keinen nativen Postgres-ENUM-Typ anlegen. Keine bestehende Spalte umbenennen/entfernen.
  Keine Änderung an `Unit`/`Tenancy`. `latitude`/`longitude` **nicht** NOT NULL machen.

### [O5] API: Stammdaten annehmen, serverseitig geocoden, Koordinaten ausliefern

- **Datei/Ort:** `apps/api/src/lokara_api/schemas.py` (Klassen `BuildingCreate`, `BuildingSummary`),
  `apps/api/src/lokara_api/routers/buildings.py` (Funktionen `create_building`, `_building_summary`) und
  `apps/web/src/lib/contracts.ts` (`BuildingSummarySchema`). Für das Geocoding ein kleiner neuer
  Helfer (z. B. eine Funktion im `buildings`-Router oder ein kleines Modul daneben).
- **Fundstelle:** In `schemas.py` die Klassen, die mit `class BuildingCreate(ApiModel):` bzw.
  `class BuildingSummary(ApiModel):` beginnen. In `buildings.py` die Funktion `create_building` (baut ein
  `Building` aus `body.name/street/postal_code/city`) und der Helfer `_building_summary`. In `contracts.ts`
  das `BuildingSummarySchema` mit `id/name/street/postalCode/city/unitCount`.
- **Ist:** `BuildingCreate` kennt nur Name+Adresse; `create_building` setzt keine Gebäudeart, kein Land,
  keine Koordinaten; `BuildingSummary` (und das Frontend-Schema) liefern keine Typ-/Geo-Infos.
- **Soll:** Drei Erweiterungen:
  1. **`BuildingCreate`** um Felder erweitern: `building_type` (einer der vier Enum-Werte aus [O4]),
     `is_residential` (Wahrheitswert), `house_number` (Text, 1–20 Zeichen), `country` (Text, Default
     „Deutschland", max. 100 Zeichen). **Das bestehende Feld `postal_code` behält seine `^\d{5}$`-Regel
     (fünf Ziffern, deutschland-spezifisch) — NICHT aufweichen.** Die App bleibt bewusst DE-fokussiert;
     `country` ist Anzeige-/Geocoding-Kontext, kein Signal für internationale PLZ-Formate. Hinweis
     Hausnummer: Die App speichert Straße heute als **ein** Feld `street`. Wizard-A ([O6]) erhebt Straße
     und Hausnummer **getrennt**; die API fügt sie beim Anlegen zu `street` zusammen („{Straße}
     {Hausnummer}"), auf die Feldlänge von `street` (max. 200) begrenzt. Ein eigenes `house_number`-Feld
     in der DB ist **nicht** Teil dieses Specs (nur zusammenfügen).
  2. **`create_building`** setzt die neuen Spalten aus [O4] und ruft **nach** dem Zusammenbauen der
     Adresse den Geocoding-Helfer auf (best effort): Adresse → `latitude`/`longitude`. Schlägt Geocoding
     fehl oder ist es nicht erreichbar, bleiben die Koordinaten null und das Anlegen gelingt trotzdem.
  3. **`BuildingSummary`** (API) und **`BuildingSummarySchema`** (Frontend) um `building_type` (String),
     `latitude` (Zahl oder null) und `longitude` (Zahl oder null) erweitern, damit Liste und Karte den
     Typ und die Pins anzeigen können. `_building_summary` füllt diese Felder.
- **Geocoding-Helfer:** Nutzt den öffentlichen Nominatim-Dienst von OpenStreetMap
  (`https://nominatim.openstreetmap.org/search`, Query aus Straße+Hausnummer+PLZ+Ort+Land, JSON, erstes
  Ergebnis → lat/lon). **Serverseitig** (nicht aus dem Browser), mit gesetztem `User-Agent`
  „Lokara/1.0 (Kontakt-E-Mail)". Ein **harter Timeout von ca. 3 Sekunden**; bei Fehler, Timeout,
  leerem Ergebnis oder blockiertem Netz (Sandbox ohne Egress) **still null zurückgeben und den Fehler
  fangen** — Geocoding darf das Anlegen **niemals** zum Scheitern bringen und die Request-Latenz nicht
  über den Timeout hinaus erhöhen. **`⚠️ MUSS-INPUT`:** die Kontakt-E-Mail im User-Agent
  (Nominatim-Nutzungsrichtlinie). Ist sie nicht geliefert, den User-Agent mit Platzhalter
  „kontakt@lokara.de" setzen und in Build-Notes vermerken.
- **Default:** `country` = „Deutschland"; Geocoding best effort mit stiller Null-Rückgabe bei Fehler;
  Adresse für die Abfrage = „{Straße} {Hausnummer}, {PLZ} {Ort}, {Land}".
- **Erwartetes Ergebnis:** Ein über Wizard-A angelegtes Objekt wird mit HTTP 201 gespeichert und trägt
  Gebäudeart, Wohn-/Nichtwohn-Kennzeichen, Land und (falls Geocoding klappte) Koordinaten. Die
  Objektliste-Antwort enthält je Objekt `buildingType`, `latitude`, `longitude`. Fällt Geocoding aus,
  funktioniert alles außer der Kartennadel dieses Objekts.
- **Akzeptanz:** `POST /a/{accountId}/buildings` mit den neuen Feldern liefert 201. `GET
  /a/{accountId}/buildings` liefert je Objekt `buildingType/latitude/longitude`. Frontend-Typprüfung und
  Python-Tests bleiben grün. **Pflicht: alle bestehenden Tests und Fixtures, die `BuildingCreate`-Payloads
  oder `create_building` aufrufen, um die neuen Pflichtfelder (`buildingType`, `isResidential`,
  `houseNumber`) ergänzen** — sonst brechen sie mit Validierungsfehlern. Der Geocoding-Helfer muss in Tests
  **ohne echten Netzzugriff** funktionieren (Netzfehler → null, kein Testfehler); wenn nötig den
  HTTP-Aufruf im Test kapseln/mocken. `BuildingSummary` wird nur in `_building_summary` (buildings.py)
  konstruiert — keine weitere Konstruktionsstelle, die die neuen Pflichtfelder bräuchte.
- **Nicht tun:** Kein Geocoding aus dem Browser. Keine Blockade des Anlegens bei Geocoding-Fehler. Keine
  Bezahl-Geocoder, keine API-Keys. Die `postal_code`-Regex nicht aufweichen.

### [O6] Wizard-A — Objekt anlegen (zweistufige eigene Seite)

- **Datei/Ort:** Neue Next.js-App-Router-Seite unter der Route `/a/{accountId}/objekte/neu` (die KI legt
  die `page.tsx` an der zur bestehenden Objektliste/-Detailseite passenden Stelle im `app/`-Baum an) plus
  eine neue Wizard-Komponente in `apps/web/src/features/objekte/` (z. B. `building-wizard.tsx`). Nutzt den
  bestehenden `useCreateBuilding`-Hook (`queries.ts`, um die neuen Felder aus [O5] erweitert) und
  `useFormDraft` für die Entwurfs-Sicherung.
- **Fundstelle:** Das heutige rechte Inline-Formular `CreateBuildingForm` in `buildings-page.tsx` (Felder
  Bezeichnung, „Straße und Hausnummer", PLZ, Ort) ist die inhaltliche Vorlage — es wird durch diesen
  Wizard ersetzt (Entfernen des Inline-Formulars: siehe [O7]).
- **Ist:** Objekte legt man über ein einstufiges rechtes Formular an, ohne Gebäudeart, ohne getrennte
  Hausnummer, ohne Land.
- **Soll:** Zweistufiger Wizard auf eigener Seite mit Kopf „Objekt anlegen" und einer schlanken
  Fortschrittsanzeige „Schritt 1 von 2 / Schritt 2 von 2":
  - **Schritt 1 — Gebäudeart:** Vier auswählbare Kacheln (Radio-Charakter, genau eine wählbar):
    **„Wohn- und Geschäftshaus", „Wohnhaus", „Gewerbeimmobilie", „Einfamilienhaus"**. Jede Kachel mit
    Titel und einer kurzen erklärenden Zeile in `text-slate`. Ausgewählte Kachel trägt den Marken-Akzent
    (linke grüne Kante / grüner Rahmen, Label `text-forest`) — Auswahl zusätzlich über ein Häkchen/Wort
    kenntlich, nicht nur über Farbe. Wird **„Wohn- und Geschäftshaus"** gewählt, erscheint darunter eine
    **Folgefrage** „Überwiegende Nutzung" mit zwei Optionen „Wohnen" / „Gewerbe". Weiter-Button ist
    deaktiviert, solange keine Kachel (bzw. bei gemischt keine Nutzung) gewählt ist.
  - **Schritt 2 — Eckdaten:** Einzelne Felder in dieser Reihenfolge: **Bezeichnung** (Hinweis „z. B.
    Musterstraße 12"), **Straße**, **Hausnummer**, **PLZ** (numerisch, genau 5 Ziffern), **Ort**,
    **Land** (vorbelegt „Deutschland"). Darunter der Bild-Bereich aus [O12] (sichtbar, inaktiv). Zwei
    Schaltflächen: „Zurück" (zu Schritt 1) und „Objekt anlegen".
  - **Ableitung des Wohn-/Nichtwohn-Kennzeichens** (`is_residential`) aus Schritt 1, ohne den Nutzer extra
    zu fragen (außer im gemischten Fall): „Wohnhaus"/„Einfamilienhaus" → Wohngebäude (wahr);
    „Gewerbeimmobilie" → Nichtwohngebäude (falsch); „Wohn- und Geschäftshaus" → aus der Folgefrage
    (Wohnen → wahr, Gewerbe → falsch). `building_type` = der gewählte Enum-Wert.
  - **Absenden:** Ruft `useCreateBuilding` mit Bezeichnung, Straße, Hausnummer, PLZ, Ort, Land,
    `building_type`, `is_residential` auf. Bei Erfolg **Weiterleitung** auf die Objekt-Detailseite des
    neu angelegten Objekts (`/a/{accountId}/objekte/{neueId}`) und Entwurf löschen.
- **Default:** Schrittanzeige als schlichte Textzeile („Schritt 1 von 2"); Kachel-Erklärzeilen kurz und
  neutral (z. B. Wohnhaus: „Reines Wohngebäude", Gewerbeimmobilie: „Überwiegend gewerbliche Nutzung",
  Wohn- und Geschäftshaus: „Gemischte Nutzung — Wohnen und Gewerbe", Einfamilienhaus: „Ein Haus, eine
  Wohneinheit"). Validierung wie im Alt-Formular: Bezeichnung/Straße/Ort Pflicht, PLZ genau 5 Ziffern.
  Hausnummer Pflicht (kurzer Text). Land Pflicht mit Default. Entwurfs-Schlüssel analog dem bestehenden
  (`{accountId}.building-create`), erweitert um die neuen Felder.
- **Erwartetes Ergebnis:** Über „Objekt anlegen" auf der Objektseite ([O7]) gelangt man auf
  `/objekte/neu`, wählt eine Gebäudeart, füllt die Eckdaten und landet nach dem Anlegen direkt in der
  Detailseite des neuen Objekts. Eingaben überstehen einen versehentlichen Reload (Entwurf). Der gemischte
  Fall fragt zusätzlich die überwiegende Nutzung ab.
- **Akzeptanz:** Die Route `/a/{accountId}/objekte/neu` existiert und rendert den zweistufigen Wizard. Ein
  im Demo-Build angelegtes „Wohn- und Geschäftshaus" mit überwiegender Nutzung „Gewerbe" erzeugt ein
  Objekt mit `is_residential = false`. Nach dem Anlegen ist die URL die Detailseite des neuen Objekts.
  Typprüfung sauber.
- **Nicht tun:** Kein Modal/Dialog-Paket verwenden. Keine Einheiten oder Mietverhältnisse in diesem Wizard
  (die kommen erst auf der Detailseite). Bild-Upload nicht funktional machen (nur Slot, [O12]).

### [O7] Objektliste-Seite — Inline-Formular durch „Objekt anlegen"-Button ersetzen, einspaltig

- **Datei/Ort:** `apps/web/src/features/objekte/buildings-page.tsx`, Funktion `BuildingsPage` und die
  Komponente `CreateBuildingForm`.
- **Fundstelle:** Das zweispaltige Grid `grid max-w-5xl gap-8 lg:grid-cols-[2fr_1fr]`, das links die
  „Objektliste"-Section und rechts `{ownerControls ? <CreateBuildingForm … /> : null}` rendert; der
  Untertitel-Absatz, der mit „Gebäude mit ihren Einheiten und Mietverhältnissen." beginnt; die gesamte
  Komponente `CreateBuildingForm`.
- **Ist:** Rechts steht ein dauerhaft sichtbares Anlege-Formular; die Liste teilt sich die Breite mit ihm.
- **Soll:** Das rechte Inline-Formular entfernen (Komponente `CreateBuildingForm` samt ihrem Zod-Schema
  und dem `useFormDraft`-Aufruf aus dieser Datei nehmen — die Anlege-Logik lebt ab jetzt im Wizard [O6]).
  Statt des Grids die Objektliste **über die volle Breite** (bzw. `max-w-5xl` einspaltig) anzeigen. Im
  Seitenkopf, rechts neben der Überschrift „Objekte" (oder direkt unter dem Untertitel), einen primären
  **Button/Link „Objekt anlegen"**, der auf `/a/{accountId}/objekte/neu` führt — **nur** wenn
  `ownerControls` wahr ist. Den Untertitel anpassen auf: „Alle Objekte dieses Kontos. Ein Klick auf ein
  Objekt öffnet seine Einheiten." (der alte Nebensatz zum rechten Formular entfällt). Der Leerzustand
  „Noch keine Objekte" bekommt statt „Legen Sie rechts Ihr erstes Gebäude an …" den Text „Legen Sie Ihr
  erstes Objekt über ‚Objekt anlegen' an — Einheiten und Mietverhältnisse folgen auf der Detailseite." Der
  Ansichts-Toggle aus [O8] sitzt oberhalb der Liste.
- **Default:** Button-Beschriftung „Objekt anlegen", primärer Button-Stil (wie der bestehende
  `Button type="submit"`), oben rechts im Kopf. Für Nicht-Owner erscheint kein Button.
- **Erwartetes Ergebnis:** Die Objektseite zeigt oben Überschrift + angepassten Untertitel + (für Owner)
  „Objekt anlegen"-Button + Ansichts-Toggle, darunter die Objektliste in voller Breite. Kein rechtes
  Formular mehr. Klick auf „Objekt anlegen" öffnet den Wizard.
- **Akzeptanz:** In `buildings-page.tsx` existiert `CreateBuildingForm` nicht mehr; es gibt einen Link auf
  `/objekte/neu`. Die Liste nutzt nicht mehr das `2fr_1fr`-Grid. Im Demo-Build ist das rechte
  Anlege-Formular verschwunden, der Button ist da. Typprüfung sauber.
- **Nicht tun:** Die Tabellenspalten/Verlinkung der Objekte nicht verändern (außer der Typ-Kennzeichnung,
  die optional in [O8]/Liste ergänzt werden darf). Keine Owner-Sichtbarkeitslogik ändern.

### [O8] Ansichts-Umschalter Liste ⇄ Karte

- **Datei/Ort:** `apps/web/src/features/objekte/buildings-page.tsx` (State + Umschalter + bedingtes
  Rendern); die Kartenkomponente selbst in einer neuen Datei (`building-map.tsx`, siehe [O9]).
- **Fundstelle:** Der Bereich oberhalb der Objektliste-Section in `BuildingsPage`.
- **Ist:** Es gibt nur die Tabellenansicht.
- **Soll:** Über der Liste ein **Zwei-Segment-Umschalter** („Liste" | „Karte") als
  Segmented-Control-artige Schaltfläche (zwei Buttons in einer gerahmten Gruppe; aktives Segment mit
  Marken-Akzent hinterlegt, `aria-pressed`/`role`-korrekt, per Tastatur bedienbar). Bei „Liste" wird die
  bestehende Tabelle gerendert, bei „Karte" die Kartenkomponente aus [O9]. Der gewählte Zustand lebt in
  einem lokalen `useState` (Default „Liste"). **Kein** localStorage (In-Memory reicht; entspricht der
  In-Conversation-Regel und ist demofähig). Der Umschalter ändert **nicht** die zugrundeliegende
  Objektmenge (kein Filter, A4). **Die Ladezustände von `useBuildings` gelten in beiden Ansichten
  gleichermaßen:** `isPending` → derselbe Skeleton wie bei der Liste (auch in der Karten-Ansicht);
  `isError` → dieselbe Fehler-`StatusNote`. Die Kartenkomponente wird **erst mit geladenen Daten**
  gerendert, nie mit `undefined`.
- **Default:** Startansicht „Liste". Segment-Beschriftungen „Liste" und „Karte". Der Umschalter ist auch
  sichtbar, wenn es (noch) keine Objekte gibt; „Karte" zeigt dann den Karten-Leerzustand aus [O9].
- **Erwartetes Ergebnis:** Ein Klick auf „Karte" ersetzt die Tabelle durch die Karte, „Liste" schaltet
  zurück. Der aktive Zustand ist klar erkennbar (Farbe **und** Form/Text). Tastaturfokus und
  Screenreader-Ansage funktionieren.
- **Akzeptanz:** Auf der Objektseite existiert ein Zwei-Segment-Umschalter; Umschalten wechselt sichtbar
  zwischen Tabelle und Karte, ohne Neuladen. Die Objektanzahl bleibt in beiden Ansichten gleich.
- **Nicht tun:** Keinen dritten Zustand, keinen globalen Filter, keine Persistenz über localStorage.

### [O9] Karten-Ansicht mit Stecknadeln (Leaflet + OpenStreetMap)

- **Datei/Ort:** Neue Komponente `apps/web/src/features/objekte/building-map.tsx`; Einbindung der
  Leaflet-CSS an der dafür passenden Stelle (die KI wählt den projektkonformen Weg — globale CSS-Einbindung
  oder Komponenten-Import). `package.json` von `apps/web` (neue Dependency **Leaflet** + `@types/leaflet`).
- **⚠️ Versions-/SSR-Fallstricke (verbindlich, sonst bricht Build/Runtime):**
  - Das Projekt läuft auf **React 19 / Next 15**. **`react-leaflet` v4 ist inkompatibel** (Peer = React 18)
    und darf **nicht** installiert werden. Empfohlener Weg: **Leaflet direkt/imperativ** einbinden (Karte in
    einem `useEffect` mit `useRef` aufbauen), das umgeht jeden React-Peer-Konflikt. Falls die KI dennoch
    `react-leaflet` will, **nur v5 oder höher** (React-19-kompatibel).
  - Leaflet braucht `window` → die Komponente ist **strikt client-seitig**: `'use client'` **und** der
    Karten-Aufbau erst nach dem Mount (im Effekt); wo nötig `next/dynamic` mit `ssr: false`. Kein
    Leaflet-Import auf Modul-Ebene, der beim SSR ausgeführt würde.
  - **Marker-Icon-Fix:** Unter Bundlern zeigen Leaflets Standard-Icons oft 404. Den bekannten Fix anwenden
    (Icon-URLs explizit auf die aus dem Paket importierten Bild-Dateien setzen bzw. `L.icon` mit gesetzten
    Pfaden), damit die Nadeln sichtbar sind.
  - **Tiles/Egress:** Das Projekt hat aktuell **kein** CSP/`headers()`-Setup (siehe `next.config.ts`), OSM-
    Kacheln laden also. Sollte später ein CSP dazukommen, `img-src`/`connect-src` für
    `https://*.tile.openstreetmap.org` freigeben. Bei blockiertem Netz zeigt die Karte einfach keine
    Kacheln — kein Absturz.
- **Fundstelle:** Neuer Code; die Datenquelle ist der bestehende `useBuildings`-Hook (liefert nach [O5]
  je Objekt `latitude/longitude/name/street/postalCode/city/buildingType/id`).
- **Ist:** Keine Karte vorhanden.
- **Soll:** Eine Kartenkomponente, die alle Objekte mit vorhandenen Koordinaten als **Stecknadeln**
  (Marker) zeigt. Beim Laden auf die Gesamtheit der Pins zoomen/zentrieren (Bounding-Box aller Marker);
  gibt es genau einen Pin, sinnvoll heranzoomen; gibt es keinen Pin, auf eine Deutschland-Übersicht
  zentrieren. Klick/Tap auf einen Pin öffnet ein kleines Popup mit **Objektname** (als Link auf die
  Detailseite `/a/{accountId}/objekte/{id}`), **Adresse** und **Gebäudeart** (lesbarer Klartext, nicht der
  Enum-Rohwert). Kartenkacheln von OpenStreetMap (`https://tile.openstreetmap.org/{z}/{x}/{y}.png`) mit der
  vorgeschriebenen Attributions-Zeile „© OpenStreetMap-Mitwirkende". Die Karte hat eine feste, angemessene
  Höhe (z. B. rund 480–560 px, responsiv volle Breite der Liste) und abgerundete Ecken/Rahmen im Kartenstil
  der App.
- **Leerzustand / fehlende Koordinaten:** Objekte **ohne** Koordinaten erscheinen nicht als Pin; sitzt kein
  einziges Objekt auf der Karte, zeigt die Kartenfläche einen ruhigen Hinweis „Für diese Objekte liegen
  noch keine Koordinaten vor." (überlagert oder unter der Karte). Kein leerer weißer Block.
- **Default:** Standard-Marker von Leaflet (kein eigenes Icon nötig; falls die Standard-Icon-Pfade unter
  Next.js Probleme machen, den bekannten Icon-Fix anwenden). Popup-Inhalt: Name (Link) fett, darunter
  Adresse in `text-slate`, darunter Gebäudeart-Klartext. Deutschland-Zentrum als Fallback: ungefähr 51,2° N,
  10,4° O, niedriger Zoom.
- **Erwartetes Ergebnis:** In der Kartenansicht sieht man die Objekte als Nadeln; im Demo-Build (ein
  Objekt „Musterstraße 12", Frankfurt) sitzt — sofern Geocoding beim Seed/Anlegen griff — eine Nadel über
  Frankfurt, deren Popup den verlinkten Namen, die Adresse und „Wohnhaus" zeigt. Klick auf den Namen führt
  zur Detailseite. Griff das Geocoding nicht, erscheint der ruhige „keine Koordinaten"-Hinweis statt eines
  Fehlers.
- **Akzeptanz:** Leaflet ist als einzige neue Laufzeit-Dependency in `apps/web/package.json` hinzugekommen;
  die Karte rendert mit OSM-Kacheln und Attribution; Pins mit Popups sind vorhanden; die Ansicht baut ohne
  Konsolenfehler. Typprüfung sauber.
- **Nicht tun:** Keine weiteren Karten-/Icon-Bibliotheken. Kein bezahlter Tile-Anbieter, kein API-Key.
  Kein Geocoding im Browser (Koordinaten kommen aus der API, [O5]).

### [O10] Wizard-B — Einheit anlegen (einstufig, mit Bestätigung und „noch eine Einheit")

- **Datei/Ort:** Neue Route `/a/{accountId}/objekte/{buildingId}/einheit/neu` (neue `page.tsx`) plus eine
  Wizard-Komponente in `apps/web/src/features/objekte/` (z. B. `unit-wizard.tsx`). Nutzt den bestehenden
  `useCreateUnit`-Hook und `useFormDraft`. In `building-detail-page.tsx` wird das rechte Inline-Formular
  `CreateUnitForm` durch einen Button ersetzt.
- **Fundstelle:** Die Komponente `CreateUnitForm` in `building-detail-page.tsx` (Felder „Bezeichnung",
  „Wohnfläche in m²") ist die inhaltliche Vorlage; das `2fr_1fr`-Grid in `BuildingDetailPage`, das rechts
  `<CreateUnitForm … />` rendert.
- **Ist:** Einheiten legt man über ein dauerhaft sichtbares rechtes Formular an.
- **Soll:** Zwei Änderungen:
  1. **Detailseite:** `CreateUnitForm` samt ihrem Zod-Schema/Entwurf aus `building-detail-page.tsx`
     entfernen (nur den Einheiten-Block anfassen, Kopf/Gerüst unberührt lassen — Invariante). Die
     Einheitenliste über die volle Breite (`max-w-5xl` einspaltig) zeigen. Oben im Kopf der Detailseite
     einen **Button „Einheit anlegen"**, der auf `/objekte/{buildingId}/einheit/neu` führt (nur für Owner,
     analog zur bisherigen Sichtbarkeit — falls die Detailseite heute keine Owner-Prüfung hat, den Button
     unbedingt zeigen; die Owner-Absicherung liegt ohnehin serverseitig).
  2. **Wizard-B (eigene Seite):** Kopf „Einheit anlegen — {Objektname}". Ein einstufiges Formular mit den
     Feldern **Bezeichnung** (Hinweis „z. B. Wohnung 1 (EG links)") und **Wohnfläche in m²** (Hinweis
     „z. B. 64,50"), plus dem Bild-Slot aus [O12] (sichtbar, inaktiv). Absende-Button „Einheit anlegen".
     **Nach erfolgreichem Anlegen** wechselt die Seite in einen **Bestätigungszustand**: eine Erfolgs-Karte
     „Einheit angelegt" mit dem Namen der neuen Einheit und **drei** Aktionen: „Noch eine Einheit anlegen"
     (setzt das Formular zurück und startet den Wizard erneut — Entwurf geleert), „Zur Einheit"
     (Detailseite der neuen Einheit `/a/{accountId}/einheiten/{neueUnitId}`) und „Fertig — zum Objekt"
     (zurück zur Objekt-Detailseite).
- **Default:** Validierung wie im Alt-Formular (Bezeichnung Pflicht; Fläche als deutsche Dezimalzahl > 0,
  Umrechnung via `parseSqmToX100`). Entwurfs-Schlüssel analog `{accountId}.{buildingId}.unit-create`. Der
  Bestätigungszustand bleibt auf derselben Route (kein neues Routing), gesteuert über lokalen State.
- **Erwartetes Ergebnis:** Von der Objekt-Detailseite öffnet „Einheit anlegen" den Wizard; nach dem
  Anlegen kann man ohne Umweg „noch eine Einheit" erfassen (mehrere hintereinander), zur neuen Einheit
  springen oder fertig werden. Das rechte Inline-Formular der Detailseite ist verschwunden, die
  Einheitenliste steht in voller Breite.
- **Akzeptanz:** Die Route `/a/{accountId}/objekte/{buildingId}/einheit/neu` existiert; nach dem Anlegen
  erscheint der Bestätigungszustand mit „Noch eine Einheit anlegen", das das Formular zurücksetzt. In
  `building-detail-page.tsx` gibt es `CreateUnitForm` nicht mehr, dafür einen Link auf die Wizard-Route.
  Typprüfung sauber.
- **Nicht tun:** Kein Modal/Dialog-Paket. Kein Batch-Anlegen mehrerer Einheiten in **einem** POST (jede
  Einheit ist ein eigener POST; „noch eine" ist ein Neustart des Formulars). Das Seitengerüst der
  Detailseite nicht in eine Widget-Struktur umbauen (gehört dem Objekt-Dashboard-Spec).

### [O11] Einheitenseite — Einstieg „Jetzt Mietverhältnis erstellen" mit Auswahl

- **Datei/Ort:** `apps/web/src/features/objekte/unit-detail-page.tsx`, Bereich „Mietverhältnisse" /
  `CreateTenancyForm`.
- **Fundstelle:** Die rechte Spalte mit `<CreateTenancyForm … />` und der Leerzustand „Noch kein
  Mietverhältnis" in `UnitDetailPage`.
- **Ist:** Rechts steht direkt das manuelle Mietverhältnis-Formular; es gibt keinen Einstieg mit
  Wahlmöglichkeit.
- **Soll:** Vor das manuelle Formular einen **Einstiegs-Schritt** setzen: ein Bereich (bzw. der
  Leerzustand) mit einem primären Button **„Jetzt Mietverhältnis erstellen"**. Ein Klick zeigt **zwei
  nebeneinanderliegende Auswahlkacheln**:
  - **„Mit Vertragsgenerator"** — führt auf die (extern entstehende) Vertragsgenerator-Route (siehe
    Default). Kurze Erklärzeile „Vertrag erzeugen und Daten automatisch übernehmen".
  - **„Vertragsdaten selbst einpflegen"** — blendet das bestehende, in [O3] korrigierte Formular
    `CreateTenancyForm` ein (inkl. des neuen Felds „Grundlage der NK-Vorauszahlung"). Kurze Erklärzeile
    „Bestehende Angaben manuell erfassen".
  Ist bereits mindestens ein Mietverhältnis vorhanden, bleibt die bestehende Tabellen-/Zeitstrahl-Anzeige;
  der „Jetzt Mietverhältnis erstellen"-Einstieg sitzt dann darüber oder darunter als Aktion, führt aber
  zur selben Zwei-Wege-Auswahl.
- **Default:** Vertragsgenerator-Route = **`/a/{accountId}/vertraege/neu?unitId={unitId}`**. ⚠️ Dieser
  Pfad ist mit Emir abzustimmen (der Vertragsgenerator entsteht parallel). Existiert die Route beim Bauen
  noch nicht, ist das unkritisch — der Link zeigt vorerst die gebrandete 404 aus `00` A9. Kein
  `⚠️ MUSS-INPUT`-Blocker; Annahme in Build-Notes vermerken. Startzustand des Einstiegs: Auswahl noch nicht
  getroffen (beide Kacheln sichtbar); „selbst einpflegen" klappt das Formular auf derselben Seite auf.
- **Erwartetes Ergebnis:** Auf einer leeren Einheit sieht man zuerst „Jetzt Mietverhältnis erstellen";
  nach Klick die zwei Wege. „Selbst einpflegen" zeigt das funktionierende Formular (legt nach [O3] echt an);
  „Mit Vertragsgenerator" navigiert auf die Vertragsgenerator-Route.
- **Akzeptanz:** Die Einheitenseite zeigt den Auswahlschritt mit zwei Kacheln; „selbst einpflegen" öffnet
  das Formular und ein Anlegen gelingt (HTTP 201); „Mit Vertragsgenerator" ist ein Link auf die benannte
  Route. Typprüfung sauber.
- **Nicht tun:** Den Vertragsgenerator **nicht** bauen (nur verlinken). Die Unveränderlichkeits-/
  Überlappungs-Semantik des Anlegens nicht ändern.

### [O12] Bild-Slots (sichtbar, inaktiv, mit Beispiel-/Platzhalterbild)

- **Datei/Ort:** Wizard-A ([O6], Schritt 2), Wizard-B ([O10], Formular). Optional zusätzlich ein
  ruhiger Anzeige-Slot oben auf der Objekt-Detailseite und der Einheiten-Detailseite (nur Anzeige, siehe
  Default).
- **Fundstelle:** Neuer Bereich innerhalb der beiden Wizards, unter den Eingabefeldern.
- **Ist:** Es gibt keine Bilddarstellung.
- **Soll:** Einen klar beschrifteten **Bild-Bereich** „Fotos (optional)" anzeigen, der **nicht speichert**:
  eine gestrichelt umrandete Ablagefläche mit dem Text „Foto-Upload kommt bald" und — als Vorschau — dem
  Beispiel-/Platzhalterbild (siehe Default). Der Bereich ist sichtbar deaktiviert (gedämpft, nicht
  anklickbar zum echten Hochladen) und trägt einen kleinen Hinweis „Wird in einer späteren Version
  aktiviert." Keine Datei wird ausgewählt, gesendet oder gespeichert.
- **Default:** ⚠️ **MUSS-INPUT (weich):** Beispiel-Asset. Liefert Berkay eine Bilddatei, wird sie als
  Vorschaubild in die Slots gelegt (unter `apps/web/public/…`, referenziert per statischem Pfad). Ist
  **kein** Asset geliefert, **kein** externes Bild laden — stattdessen eine schlichte Platzhalterfläche in
  `bg-mint`/`text-slate` mit zentriertem Text „Foto folgt" rendern (rein aus Tokens, keine neue Datei,
  kein Icon-Paket). Annahme in Build-Notes vermerken. Der optionale Anzeige-Slot auf den Detailseiten ist
  **nur** zu bauen, wenn er ohne Umbau des Seitengerüsts passt (Invariante Detailseite); sonst weglassen
  und in Build-Notes vermerken.
- **Erwartetes Ergebnis:** In beiden Wizards sieht man einen aufgeräumten „Fotos (optional)"-Bereich mit
  Platzhalter/Beispielbild und dem Hinweis „kommt bald" — aber es lässt sich nichts hochladen, und es
  entsteht kein Eindruck einer funktionierenden Speicherung.
- **Akzeptanz:** Die Wizards zeigen den Bild-Bereich; ein Klick löst **kein** Datei-Dialog-/Upload-Verhalten
  aus; im Code gibt es keinen Upload-Request. Kein externes Bild wird geladen, wenn kein Asset vorliegt.
- **Nicht tun:** Keinen `<input type=file>`-Uploader verdrahten, keinen Storage-/Upload-Endpoint aufrufen,
  keine externe Bild-URL einbetten.

---

## Out of Scope (bewusst NICHT hier)

- **Echter Bild-Upload / Objekt- und Einheiten-Fotos speichern.** Braucht Objekt-Storage (S3/Supabase) +
  Attachment-Tabelle + Upload-Endpoint + Thumbnails; eigene spätere Storage-Runde. Hier nur sichtbarer
  inaktiver Slot ([O12]).
- **Objekt-Dashboard (KPI-/Widget-Umbau der Objekt-Detailseite).** Eigener späterer Spec. Dieser Spec
  fasst `building-detail-page.tsx` nur minimal an (Einheiten-Block + „Einheit anlegen"-Button).
- **Vertragsgenerator-Modul selbst.** Entsteht parallel; hier nur der verlinkende Einstieg ([O11]).
- **Produktives Geocoding.** Nominatim ist nur für Demo/geringe Last geeignet (Nutzungsrichtlinie:
  1 Anfrage/Sekunde, korrekter User-Agent). Ein eigener/kostenpflichtiger Geocoder für den Produktivbetrieb
  ist später zu klären.
- **Mehrfach-Einheiten in einem Batch-POST** und ein transaktionaler Wizard-Batch-Endpoint. Durch die
  abgestufte Wizard-Führung nicht nötig (jeder Schritt = ein Einzel-POST); ein zuvor angedachter
  Batch-Endpoint kann entfallen.
- **Getrennte Hausnummer-Spalte in der DB.** Wizard-A erhebt Hausnummer separat, die API fügt sie an
  `street` an ([O5]); ein eigenes DB-Feld ist späteres Thema.

## Verifikation

1. **Fix (Screen 3):** Im Demo-Build die Einheitenseite von „Wohnung A (EG links)" öffnen → sie lädt
   (kein „Fehler beim Laden"), Zeitstrahl + Tabelle sichtbar, NK-Vorauszahlung zeigt einen Betrag.
2. **Mietverhältnis anlegen:** Für die leerstehende „Wohnung B (EG rechts)" über „Jetzt Mietverhältnis
   erstellen" → „selbst einpflegen" einen Zeitraum anlegen → HTTP 201, neue Zeile erscheint. Ein
   überlappender Zeitraum liefert weiterhin die Überschneidungs-Meldung (422), aber kein Feldnamen-422.
3. **Wizard-A:** „Objekt anlegen" → Gebäudeart wählen (inkl. gemischtem Fall mit Nutzungsfrage) →
   Eckdaten mit getrennter Hausnummer und Land → nach dem Anlegen Landung auf der neuen Detailseite; das
   Objekt trägt Gebäudeart und Wohn-/Nichtwohn-Kennzeichen.
4. **Wizard-B:** Auf der Detailseite „Einheit anlegen" → Einheit erfassen → Bestätigung → „Noch eine
   Einheit anlegen" setzt das Formular zurück; mehrere Einheiten hintereinander möglich.
5. **Toggle + Karte:** „Karte" zeigt die Objekte als Pins (bzw. den „keine Koordinaten"-Hinweis, falls
   Geocoding ausfiel); Pin-Popup verlinkt auf die Detailseite; „Liste" schaltet zurück. Objektanzahl in
   beiden Ansichten gleich.
6. **Bild-Slots:** In beiden Wizards sichtbar, deutlich als „kommt bald" markiert, nicht hochladbar,
   kein Upload-Request.
7. **Seed & Migration:** `alembic upgrade head` und danach `lokara-seed-demo` laufen **ohne Fehler**
   durch (server_default deckt die neuen Pflichtspalten für ORM-Inserts ab); Downgrade entfernt die
   Spalten sauber.
8. **Nichtregression:** `bun run typecheck` **und** `bun run test` (Web, inkl. des angepassten
   `tenancy-timeline.test.ts` aus [O3b]) grün; Python-Tests grün (inkl. angepasster `BuildingCreate`-
   Tests und netzfreiem Geocoding); `bun run lint` ohne ungenutzte Importe; bestehende Seiten (Dashboard,
   Kosten, Zähler, Abrechnung) unverändert.

## Build-Notes (füllt die KI aus)

<!-- Annahmen, Defaults, Abweichungen, übersprungene MUSS-INPUTs hier eintragen. Erwartet u. a.:
     - Kontakt-E-Mail im Nominatim-User-Agent (O5) — Platzhalter genutzt? 
     - Vertragsgenerator-Route (O11) — verwendeter Pfad + ob mit Emir bestätigt.
     - Beispiel-Asset für Bild-Slots (O12) — geliefert oder Platzhalter „Foto folgt"?
     - Optionaler Anzeige-Slot auf Detailseiten (O12) — gebaut oder weggelassen (Gerüst-Invariante)?
     - Exakte Ablage der neuen App-Router-Seiten (O6/O10). -->
