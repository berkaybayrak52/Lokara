---
spec_id: 00-layout-global
titel: Layout Global — App-Shell, Marke, Container
status: freigegeben
prioritaet: hoch
betrifft: apps/web
abhaengig_von: []
repo_stand: Lokara-main @ 2026-08-23
---

## Zweck

Globaler Rahmen der eingeloggten App: Marke sichtbar machen, Entwickler-Text und „NK-only"-Rahmung
entfernen, Container-Breite/Totraum beheben, Favicon und gebrandete Fehlerseiten ergänzen. Betrifft
jede eingeloggte Seite. Reines Layout/UI/Text — keine Fachlogik. **Dieser Spec enthält bewusst
keinen Code; jede Änderung ist in Worten beschrieben, die umsetzende KI schreibt den Code selbst
gegen den echten Dateistand.**

## Invarianten (gelten für ALLE Befehle hier)

- Pre-Pitch wird ausschließlich die Web-App für Desktop und Laptop abgenommen: 1280, 1440 und
  1920 Pixel sowie 200-Prozent-Zoom. Eigenständige Smartphone-/Tablet-Informationsarchitektur,
  Touch-Navigation und native App sind Post-Pitch; Semantik, Tastatur und sichtbarer Fokus bleiben
  Pre-Pitch verpflichtend.

- Nur die vorhandenen Design-Tokens verwenden (die definierten Farb-Tokens Petrol-Ink, Lokara-Grün,
  Forest, Mint, Slate, Paper sowie die Hausschriften Montserrat für Anzeige/Zahlen und Manrope für
  Text). **Keine rohe Farbangabe neu erfinden.** Die alte Angabe „Poppins/Navy/Teal/Cream" ist
  überholt.
- Nur die im jeweiligen Befehl benannten Stellen ändern. Keine unbeteiligte Datei anfassen.
- Bestehende Tests bleiben grün, die Typprüfung bleibt sauber.
- Keine Rechen-, Geld- oder Rechtslogik verändern.
- Bei Unklarheit: naheliegendste Variante umsetzen, **nicht anhalten**. Annahme ans Dateiende in
  `## Build-Notes`.
- `⚠️ MUSS-INPUT`-Werte nie erfinden: Teilpunkt überspringen + loggen, Rest des Befehls umsetzen.

---

## Befehle

### [A1] Logo austauschen (Platzhalter → CD-Logo)
- **Datei/Ort:** App-Shell, ganz oben im Kopf der linken Seitenleiste.
- **Fundstelle:** Der anklickbare Logo-Bereich oben in der Seitenleiste — aktuell ein kleines
  quadratisches Symbol aus vier farbigen Kacheln (2×2-Raster, dunkles Quadrat mit grün/hellen
  Vierteln) direkt neben dem Schriftzug „Lokara".
- **Ist:** Dieses Symbol ist rein per CSS gezeichnet, kein echtes Logo, und passt nicht zum
  Corporate Design.
- **Soll:** Das gezeichnete Kachel-Quadrat entfernen und stattdessen das echte Lokara-Logo als
  Bildgrafik einsetzen.
- **Default:** Bilddatei `lokara-logo.png`, Höhe 28 Pixel, links neben dem Schriftzug „Lokara".
  Enthält das Bild nur ein Signet → den Schriftzug „Lokara" behalten. Enthält es Signet **und**
  Wortmarke → den separaten Schriftzug entfernen. Liegt das Bild noch nicht im Projekt vor → die
  Einbindung trotzdem anlegen und das fehlende Asset in Build-Notes melden.
- **Erwartetes Ergebnis:** Oben in der Seitenleiste erscheint das echte Lokara-Logo als Grafik, rund
  28 Pixel hoch, vertikal mittig, mit dem gewohnten großzügigen Abstand (etwa 32 Pixel) zum darunter
  beginnenden Menü. Das Logo bleibt anklickbar und führt zur Startseite. Kein gezeichnetes
  Vier-Kachel-Quadrat mehr.
- **Akzeptanz:** Im Kopf der Seitenleiste ist kein CSS-gezeichnetes Kästchen mehr, sondern eine
  Bildgrafik; ein Screenshot bestätigt das Logo.
- **Nicht tun:** Das Klickziel oder das Grundgerüst der Seitenleiste ändern.

### [A2] Entwickler-Text aus dem Nutzer-UI entfernen
- **Datei/Ort:** Dashboard-/Übersichtsseite (gemeinsamer Seitenkopf) und die App-Shell.
- **Fundstelle:** (1) Der Beschreibungsabsatz unter der Überschrift „Übersicht", der mit „Ihr Bestand
  auf einen Blick." beginnt und mit einem zweiten Satz über URL-Kontext und serverseitige
  Autorisierung weitergeht. (2) In der App-Shell der Hinweistext auf der „Kein Zugriff"-Ansicht, der
  mit „— jeder Zugriff wird serverseitig unabhängig geprüft." endet.
- **Ist:** Beide enthalten technische Selbstbeschreibung, die ein Vermieter nicht sehen soll.
- **Soll:** Im Übersichts-Absatz nur „Ihr Bestand auf einen Blick." behalten, den zweiten Satz
  streichen. In der App-Shell den genannten Halbsatz streichen.
- **Erwartetes Ergebnis:** Unter „Übersicht" steht genau eine kurze Zeile in der gedämpften
  Sekundär-Textfarbe (Slate): „Ihr Bestand auf einen Blick." Kein technischer Zusatz. Auf der
  „Kein Zugriff"-Ansicht endet der Text sauber, ohne Erwähnung serverseitiger Prüfung.
- **Akzeptanz:** Im sichtbaren UI ist nirgends mehr von „serverseitig" oder „Kontext kommt aus der
  URL" zu lesen; eine Volltextsuche im Frontend-Quellordner nach diesen Wörtern findet keinen im UI
  angezeigten Treffer.
- **Nicht tun:** Andere Texte anfassen.

### [A3] Container-Breite / Totraum
- **Datei/Ort:** App-Shell, der zentrierende Wrapper um den gesamten Seiteninhalt rechts neben der
  Seitenleiste.
- **Fundstelle:** Der mittig gesetzte Inhalts-Container, aktuell auf 1100 Pixel Maximalbreite
  begrenzt.
- **Ist:** Der Inhalt ist auf 1100 Pixel zentriert; auf breiten Monitoren entstehen dadurch große
  leere Ränder links und rechts.
- **Soll:** Die Maximalbreite anheben und den seitlichen Innenabstand auf großen Bildschirmen
  vergrößern.
- **Default:** Maximalbreite 1440 Pixel; seitlicher Innenabstand normal großzügig, ab etwa 1280
  Pixel Fensterbreite noch etwas mehr Luft.
- **Erwartetes Ergebnis:** Auf einem 1920-Pixel-Monitor füllt der Inhalt spürbar mehr Breite, die
  leeren Seitenränder schrumpfen deutlich; auf Laptop-Breiten ändert sich kaum etwas. Inhalt bleibt
  mittig, wirkt aber nicht mehr „abgebrochen".
- **Akzeptanz:** Auf 1920 Pixel kein leerer Rand größer als etwa 15 % der Inhaltsbreite je Seite.
- **Nicht tun:** Die Breite der Seitenleiste ändern. Falls Tabellen dadurch zu breit laufen, eine
  eigene Lesebreite auf die Tabelle setzen (nicht global zurückdrehen) und als Build-Note melden.

### [A4] Objekt-Navigationsmodell (Guard) — KEIN globaler Objekt-Filter
- **Datei/Ort:** — (Design-Guard, keine Datei in dieser Runde).
- **Ist:** Die alte Dashboard-Spec nannte einen globalen Objekt-Filter im Kopf, auf den „alle
  Widgets reagieren". Diese Vorgabe ist überholt.
- **Soll:** Es gilt das Portfolio-Standard-Modell: Übersichten zeigen immer das gesamte Portfolio;
  ein einzelnes Objekt sieht man nur, indem man über „Objekte" in die Objektakte hineingeht. Deshalb
  **keinen globalen Objekt-Umschalter/Filter** in Kopfzeile oder Seitenkopf bauen.
- **Default:** Kopfzeile und einheitlicher Seitenkopf werden in dieser Runde nicht gebaut — sie
  kommen gebündelt in `09_App-Shell-Desktop.md`. A4 ist hier nur der Guard.
- **Erwartetes Ergebnis:** Nirgends erscheint ein globaler „Alle Objekte / Einzelobjekt"-Umschalter.
- **Akzeptanz:** Keine neue Filter-/Umschalter-Komponente im Ergebnis.
- **Nicht tun:** Einen globalen Objekt-Filter einführen.

### [A5] Marken-Akzent setzen (nicht alles grau)
- **Datei/Ort:** Dashboard-/Übersichtsseite, die drei oberen Kennzahl-Karten.
- **Ist:** Außer dem einen grünen Button ist alles grau/weiß; die Marke ist praktisch unsichtbar.
- **Soll:** Jeder Kennzahl-Karte einen dezenten Marken-Akzent geben — nur mit vorhandenen Tokens,
  ohne neue Abhängigkeit.
- **Default:** An jeder Kennzahl-Karte eine schmale senkrechte Akzentleiste am linken Rand in
  Lokara-Grün (etwa 4 Pixel breit). Das kleine Kopf-Label über der Zahl in der dunkelgrünen Nuance
  (Forest). Die große Zahl bleibt in der Haupttextfarbe (Ink). Am Ende justierbar.
- **Erwartetes Ergebnis:** Die Karten wirken nicht mehr rein grau — jede trägt links eine feine
  grüne Kante, das Kopf-Label ist grünlich abgesetzt, die Zahl bleibt kräftig dunkel. Die Marke ist
  auf einen Blick erkennbar, ohne dass eine zweite Farbe hinzukommt.
- **Akzeptanz:** Die Marke ist auf dem Dashboard auch ohne den Button erkennbar (Akzent je Karte).
- **Nicht tun:** Ein zweites Grün oder neue Farben einführen; ein Signal nie allein über Farbe
  transportieren.

### [A6] Karten-Leerlauf / erzwungene Höhen
- **Datei/Ort:** Dashboard-/Übersichtsseite, die Karten-Raster (obere Dreier-Reihe und die untere
  Zweier-Reihe).
- **Ist:** Karten wirken „halb leer" — Text oben und unten, dazwischen ein sichtbares Loch, weil die
  Rasterzellen bei ungleichem Inhalt gleich hoch gestreckt werden.
- **Soll:** Die Karten ihre natürliche Höhe nehmen lassen (am Raster oben ausrichten), keine
  erzwungene feste Höhe.
- **Erwartetes Ergebnis:** Jede Karte ist nur so hoch wie ihr Inhalt; kein leerer Block mehr
  zwischen Kopf und Fuß. Die Karten einer Reihe müssen nicht mehr zwingend gleich hoch sein.
- **Akzeptanz:** Keine Karte mit sichtbarem vertikalem Leerraum zwischen Kopf und Fuß.
- **Nicht tun:** Karteninhalte entfernen.

### [A7] Favicon ergänzen (fehlt komplett)
- **Datei/Ort:** Frontend-App — ein bisher nicht vorhandenes öffentliches Asset-/Icon-Verzeichnis.
- **Ist:** Die Frontend-App hat kein öffentliches Asset-Verzeichnis und keine Favicon; der
  Browser-Tab zeigt das nackte Standard-Icon des Frameworks.
- **Soll:** Eine Favicon einbinden, sodass der Browser-Tab das Lokara-Signet zeigt.
- **Default:** Die vorhandene Signet-Grafik `lokara-favicon.png` als App-Icon nach der Konvention des
  Frameworks hinterlegen, sodass das Tab-Icon automatisch erzeugt wird. Liegt das Asset noch nicht im
  Projekt vor → die Einbindung anlegen und das fehlende Asset in Build-Notes melden (Berkay/Emir
  legen die Datei nach).
- **Erwartetes Ergebnis:** Sobald das Asset vorliegt, zeigt der Browser-Tab das Lokara-Signet statt
  des Framework-Standardicons. (Dasselbe Signet dient später als eingeklapptes Sidebar-Logo — das ist
  Teil von `09_App-Shell-Desktop.md`, nicht hier.)
- **Akzeptanz:** Der Browser-Tab zeigt das Lokara-Signet.
- **Nicht tun:** Ein vollständiges PWA-/Installations-Icon-Set bauen — bewusst nicht in dieser Runde.

### [A8] „NK-only"-Formulierungen entfernen
- **Datei/Ort:** Die App-Metadaten (Seitentitel/Beschreibung), ein Text-Sweep über den gesamten
  Frontend-Quellordner, und der Fuß-Disclaimer auf der öffentlichen Startseite.
- **Fundstelle:** (1) In den App-Metadaten das Beschreibungsfeld, das aktuell „Rechtskonforme
  Nebenkosten- und Betriebskostenabrechnung." lautet. (2) Überall im UI sichtbare Texte, die Lokara
  als reines Nebenkosten-/Abrechnungswerkzeug rahmen. (3) Im Fußbereich der Startseite der
  Disclaimer, der mit „…Betriebs- und Heizkostenabrechnung, keine Rechts- oder Steuerberatung." endet.
- **Ist:** Diese Stellen rahmen Lokara als NK-Tool. Lokara ist aber Full-Lifecycle-Verwaltung.
- **Soll (drei Teile):**
  1. Die Metadaten-Beschreibung auf eine lebenszyklus-weite Formulierung setzen.
     **Default:** „Vermieten leicht gemacht — Verwaltung über den ganzen Lebenszyklus."
  2. Im Text-Sweep alle im UI sichtbaren **Positionierungs**-Texte, die von Nebenkosten- bzw.
     Betriebs-/Heizkostenabrechnung als Produktkern sprechen, auf „Verwaltung allgemein" umschreiben.
     Reine Funktions-Bezeichnungen (z.B. die Karte „Abrechnung 2025") bleiben unverändert — sie
     beschreiben eine Funktion, nicht das Produkt.
  3. Der Fuß-Disclaimer: Die Schutzaussage „keine Rechts- oder Steuerberatung" bleibt inhaltlich
     erhalten; nur die NK-Rahmung davor wird angepasst. **Lokara unterstützt Vermieter bei der Verwaltung ihrer Objekte und ersetzt keine Rechts- oder Steuerberatung.** 
Bis dahin den Disclaimer **nicht anfassen**, in Build-Notes vermerken; Teil 1
     und 2 trotzdem umsetzen.
- **Erwartetes Ergebnis:** Browser-Tab-Titel und Vorschautext beschreiben Lokara als
  Lebenszyklus-Verwaltung. Im UI rahmt kein sichtbarer Text das Produkt mehr als NK-/Abrechnungs-Tool
  — mit Ausnahme reiner Funktions-Labels und des (bis zur Textlieferung unveränderten) Disclaimers.
- **Akzeptanz:** Eine Suche im Frontend-Quellordner nach der Wendung „Nebenkosten- und
  Betriebskostenabrechnung" liefert keinen Treffer mehr in Metadaten oder Fließtext; Funktions-Labels
  und der Disclaimer sind unverändert bzw. später separat angepasst.
- **Nicht tun:** Funktions-Labels ändern; den Disclaimer-Text raten.

### [A9] Gebrandete Fehler- und Nicht-gefunden-Seite
- **Datei/Ort:** Frontend-App, globale Fehler- und 404-Behandlung (aktuell nicht vorhanden), optional
  eine globale Ladeansicht.
- **Ist:** Es gibt keine globale Fehler-, Nicht-gefunden- oder Ladeseite; bei einem Absturz oder
  einer unbekannten Adresse erscheint die weiße Standardseite des Frameworks. Beim Pitch ein
  Totalausfall-Bild.
- **Soll:** Eine gebrandete Fehlerseite und eine gebrandete 404-Seite ergänzen, jeweils mit
  vorhandenen Tokens und Bausteinen.
- **Default (Fehlerseite):** Zentrierter Inhalt mit Lokara-Logo, einer Anzeige-Überschrift „Etwas ist
  schiefgelaufen", einem Hinweisblock im Fehler-Stil (rötlicher Warnton aus den Status-Tokens) und
  einem Button „Erneut versuchen", der die Ansicht neu lädt. **Default (404):** gleiche Aufmachung mit
  Überschrift „Seite nicht gefunden" und Button „Zur Übersicht".
- **Erwartetes Ergebnis:** Bei einem Fehler oder einer unbekannten Adresse sieht der Nutzer eine
  ruhige, im Lokara-Look gestaltete Seite (Logo, Hausschrift, Marken-/Status-Farben) mit einer klaren
  Handlungsmöglichkeit — nie die weiße Framework-Standardseite.
- **Akzeptanz:** Eine unbekannte Adresse und ein absichtlich ausgelöster Fehler zeigen jeweils eine
  Lokara-gebrandete Seite.
- **Nicht tun:** Rohe Farbwerte statt der Tokens verwenden.

---

## Out of Scope (bewusst NICHT hier)

- Kopfzeile, einheitlicher Seitenkopf, einklappbare Seitenleiste/Rail, Icons und Account-Menü → kommen
  gebündelt in `09_App-Shell-Desktop.md`. Eine eigenständige Smartphone-/Tablet-Navigation und
  die native App sind Post-Pitch.
- Vollständiges PWA-Manifest und Installations-Icons.
- Dashboard-Inhalt/Widgets → `01_Dashboard.md`.
- Jede Rechen-, Geld- oder Rechtslogik.

## Verifikation (Gesamtergebnis)

- Typprüfung und bestehende Tests bleiben grün.
- Kein im UI sichtbarer Text erwähnt mehr „serverseitig" oder „Kontext kommt aus der URL".
- Die Wendung „Nebenkosten- und Betriebskostenabrechnung" taucht nicht mehr in Metadaten oder
  Fließtext auf.
- Screenshots auf einem breiten Monitor: Bild-Logo statt Kästchen, grüner Akzent auf den
  KPI-Karten, kein übergroßer Seitenrand. Unbekannte Adresse und ausgelöster Fehler zeigen
  gebrandete Seiten.

## Reihenfolge

1. A1, A2, A7, A8, A9 — sofort, kein Datenbedarf.
2. A3, A5, A6 — Styling-Politur.
3. A4 — nur Guard (nichts bauen).

---

## Build-Notes (füllt die KI beim Umsetzen aus)

<!-- Jede Annahme, jeder übersprungene MUSS-INPUT-Teil, jede Abweichung hier eintragen. Beispiel:
- [A1] lokara-logo.png war nicht im Projekt — Einbindung angelegt, Asset fehlt noch.
- [A8] Disclaimer-Wortlaut (MUSS-INPUT) fehlt — Fuß-Disclaimer unverändert gelassen, Teil 1+2 umgesetzt.
-->
