---
spec_id: 09-app-shell-desktop
titel: Web-App-Shell Desktop — Seitenleiste, Seitenkopf, Account-Menü und Pitch-Navigation
status: freigegeben
prioritaet: hoch
betrifft: apps/web, packages/ui
abhaengig_von: [00-layout-global]
repo_stand: Lokara-main @ 2026-08-25
---

## Zweck

Die bestehende Web-App erhält für Pitch und Desktopbetrieb eine konsistente, platzsparende Shell aus
einklappbarer Seitenleiste, eindeutiger Navigation, einheitlichem Seitenkopf und Account-Menü. Der Spec
betrifft ausschließlich Desktop und Laptop. Smartphone-/Tablet-Navigation und eine native App sind
Post-Pitch.

## Invarianten

- Pre-Pitch werden ausschließlich 1280, 1440 und 1920 Pixel Fensterbreite sowie 200-Prozent-Zoom
  abgenommen. Primäre Pitch-Auflösung ist 1920 × 1080 beziehungsweise die tatsächlich verwendete
  Präsentationsauflösung.
- Keine eigenständige Smartphone-/Tablet-Informationsarchitektur, keinen Mobile Drawer, keine Bottom
  Navigation, keine Touch-spezifische Shell und keine native Navigation bauen. Diese Varianten sind
  Post-Pitch.
- Semantische Navigation, Tastaturbedienung, Screenreader-Beschriftung, sichtbarer Fokus, sinnvolle
  flexible Laptopbreiten und Reduced Motion bleiben Pre-Pitch verpflichtend.
- URL-getragener Accountkontext, Rollenfilter, Gebäudezuweisungen, serverseitige Autorisierung und RLS
  bleiben unverändert maßgeblich. Versteckte Navigation ist kein Zugriffsschutz.
- Portfolio bleibt das Standardmodell: kein globaler Objektumschalter in Sidebar, Top-Bar oder
  Seitenkopf. Einzelobjekte werden über „Objekte“ geöffnet.
- Nur vorhandene Lokara-Tokens, Montserrat für Anzeige/Kennzahlen und Manrope für Text verwenden.
  Keine rohen Farbwerte, keine alte Navy-/Teal-/Cream-/Poppins-Sprache.
- Die Shell enthält Navigation und globalen Kontext, aber keine Fachberechnungen, Fach-KPIs,
  Forderungssalden, Reminder oder Demo-Mocks.
- Nur existierende und für die Rolle erreichbare Routen als aktive Navigation zeigen. Kommende Module
  nicht als klickbare tote Links ausgeben.
- Seitentitel, Untertitel, Breadcrumbs und Aktionen besitzen je Seite genau eine visuelle Quelle. Die
  Shell erzeugt keine zweite Überschrift über einem bereits vollständigen Fachseitenkopf.
- Änderungen an Fachseiten beschränken sich auf die Einbindung des gemeinsamen Seitenkopfvertrags und
  notwendige Abstandsbereinigung; ihre Informationsarchitektur und Fachlogik bleiben in `01–08`.
- Bestehende Tests, Typprüfung, Lint, Account-/Rollen- und RLS-Gates bleiben grün.
- Bei normaler Unklarheit den Default verwenden und in Build-Notes dokumentieren. `⚠️ MUSS-INPUT` nie
  raten; nur den betroffenen Teil auslassen und den Rest weiter umsetzen.

## Befehle

### [S1] Desktop-Shell als stabiles Zweispaltenlayout aufbauen

- **Datei/Ort:** `apps/web/src/features/portal/app-shell.tsx`,
  `apps/web/src/app/a/[accountId]/layout.tsx` und bei sinnvoller Aufteilung neue präsentationsbezogene
  Dateien unter `apps/web/src/features/portal/`.
- **Fundstelle:** `PortalShellContent` verwendet heute eine 256-Pixel-Seitenleiste ab `md`, einen
  zentrierten 1100-Pixel-Inhaltswrapper und zusätzlich eine horizontale „Mobile Hauptnavigation“.
- **Ist:** Desktopnavigation funktioniert grundsätzlich, wirkt aber wie ein technischer Prototyp. Die
  Sidebar ist nicht einklappbar, Inhaltsbreite und Seitenköpfe sind uneinheitlich, und die mobile
  Parallelnavigation liegt trotz Post-Pitch-Entscheidung im selben Shellvertrag.
- **Soll:** Eine stabile Desktop-/Laptop-Shell mit links fixierter Navigation und rechts flexiblem
  Hauptbereich schaffen. Die Seitenleiste bleibt viewporthoch, scrollt bei Bedarf intern und bewegt
  sich nicht mit langen Fachseiten. Der Hauptbereich besitzt einen Shell-Kopf und darunter den
  Seiteninhalt.
- **Default:** Ausgeklappte Sidebar 248 Pixel, eingeklappte Rail 72 Pixel. Hauptbereich mindestens 0
  breit für korrektes Flexverhalten. Shell-Hintergrund `paper`, Sidebar und Inhaltsflächen aus den
  vorhandenen Paper-/White-/Mint-Tokens. Die horizontale Mobile-Navigation ist nicht Bestandteil des
  Pre-Pitch-Vertrags und wird nicht weiter ausgebaut; eine spätere mobile Shell erhält einen eigenen
  Spec.
- **Erwartetes Ergebnis:** Auf 1280, 1440 und 1920 Pixel bleiben Navigation und Inhalt stabil. Lange
  Zähler-, Zahlungs- oder Abrechnungsseiten schieben Account-Menü und Navigation nicht aus dem
  Viewport.
- **Akzeptanz:** Screenshots aller drei Abnahmebreiten und einer langen Seite zeigen keine
  Überlagerung, keinen horizontalen Seitenscroll im Standardzoom und eine unabhängig intern
  scrollende Sidebar.
- **Nicht tun:** Smartphone-Breakpoints, Drawer oder Bottom Navigation ergänzen; Fachseiten in die
  Sidebar verschieben; Seitenbreite durch einen starren Vollseiten-Mindestwert erzwingen.

### [S2] Echtes Lokara-Logo und klare Markenfläche verwenden

- **Datei/Ort:** Logo-Bereich oben in `app-shell.tsx` und vorhandene Assets gemäß
  `00_Layout-Global.md` [A1]/[A7].
- **Fundstelle:** Aktuell steht ein per CSS gezeichnetes Vier-Kachel-Quadrat neben „Lokara“.
- **Ist:** Der Platzhalter ist kein echtes Markenasset und wirkt im Pitch unfertig.
- **Soll:** Das echte Lokara-Logo einsetzen und sein Verhalten für ausgeklappte Sidebar und Rail
  definieren. Das Logo bleibt ein Link zur Portfolioübersicht des aktuellen Accounts, nicht zur
  öffentlichen Startseite, sofern ein Account aktiv ist.
- **Default:** Ausgeklappt vollständige Wortmarke beziehungsweise Signet plus „Lokara“, Höhe etwa
  28 Pixel. Eingeklappt nur das echte Signet, mittig. Tooltip beziehungsweise zugänglicher Name
  „Zur Übersicht“. Fehlt das freigegebene Asset beim Bau, vorhandenen Platzhalter nicht durch ein
  neu erfundenes Logo ersetzen, sondern fehlendes Asset in Build-Notes melden.
- **Erwartetes Ergebnis:** Die Marke ist ruhig und eindeutig; beim Ein-/Ausklappen springt die
  Navigation nicht vertikal.
- **Akzeptanz:** Kein CSS-gezeichnetes Vier-Kachel-Symbol bleibt. Linkziel enthält den aktiven
  `accountId`; Fokus und zugänglicher Name sind vorhanden.
- **Nicht tun:** Neues Logo zeichnen; externe Bild-URL laden; Logo als globalen Objektfilter verwenden.

### [S3] Seitenleiste einklappbar und pitchsicher machen

- **Datei/Ort:** Desktop-Sidebar und persistierter rein visueller Shellzustand in
  `apps/web/src/features/portal/`; UI-Tests.
- **Fundstelle:** Die heutige Sidebar besitzt immer 256 Pixel Breite und keinen Umschalter.
- **Ist:** Auf 1280-Pixel-Laptops fehlt Fachseiten Breite; auf 1920 Pixel bleibt gleichzeitig viel
  unstrukturierter Totraum.
- **Soll:** Einen eindeutigen Umschalter am oberen beziehungsweise unteren Rand der Navigation
  anbieten. Eingeklappt zeigt die Rail Logo-Signet und Navigationsicons; Textlabels bleiben über
  zugängliche Namen und Tooltip erreichbar.
- **Default:** Startzustand bei 1280 Pixel eingeklappt, ab 1440 Pixel ausgeklappt. Eine bewusste
  Nutzerentscheidung wird lokal als reine Darstellungspräferenz gespeichert und überschreibt den
  Breiten-Default beim nächsten Laden. Übergang 180 Millisekunden über Breite/Opacity, bei Reduced
  Motion ohne Animation. Umschaltertexte „Navigation einklappen“/„Navigation ausklappen“.
- **Erwartetes Ergebnis:** Der Pitch kann mit einem Klick mehr Inhaltsbreite schaffen, ohne Navigation
  oder Accountkontext zu verlieren. Reload behält die Präferenz.
- **Akzeptanz:** Tastatur und Maus schalten beide Zustände. Fokus bleibt am Umschalter; keine
  Layoutüberlagerung oder abgeschnittene Iconfläche. Serverseitiges Rendern und Hydration zeigen
  keinen störenden Dauer-Flash.
- **Nicht tun:** Shellpräferenz im Backend als Fachdaten speichern; Sidebar automatisch bei jeder
  Fachnavigation öffnen; Hover als einzige Möglichkeit zum Ausklappen verwenden.

### [S4] Navigation begrifflich ordnen und mit vorhandenen Icons unterstützen

- **Datei/Ort:** `NAV_ITEMS` und Navigationselemente in `app-shell.tsx`; gegebenenfalls kleine
  shellinterne Iconkomponenten ohne neue Dependency.
- **Fundstelle:** Aktuelle Reihenfolge: Übersicht, Objekte, Kosten erfassen, Beleg-Upload, Zähler,
  Abrechnung erstellen, Zahlungen, Steuern. Alle Einträge sind reine Textlinks.
- **Ist:** Aktionsformulierungen und Modulnamen sind gemischt. „Kosten erfassen“ und „Abrechnung
  erstellen“ bezeichnen inzwischen Bestands-/Arbeitsbereiche, nicht nur eine Einzelaktion.
- **Soll:** Hauptnavigation als stabile Modulnavigation beschriften und jedem Eintrag ein einfaches,
  vorhandenes beziehungsweise lokal konsistentes Icon geben. Aktiver Zustand funktioniert für
  Unterrouten wie Objekt- und Einheitendetail weiter.
- **Default:** Reihenfolge und Labels: „Übersicht“, „Objekte“, „Zahlungen“, „Kosten“, „Belege“,
  „Zähler“, „Abrechnungen“, „Steuern“. Zahlungen bleibt Owner-only; Steuern Owner oder Tax Advisor;
  Tax Advisor sieht gemäß bestehendem Vertrag ausschließlich Steuern. Objekt- und Einheitenpfade
  aktivieren „Objekte“. Icons dienen zusätzlich zum Text, nie als einzige Bedeutung.
- **Erwartetes Ergebnis:** Die Navigation liest sich als Produktstruktur und nicht als Liste von
  Buttons. Ausgeklappt stehen Icon und Text, eingeklappt Icon mit Tooltip/zugänglichem Namen.
- **Akzeptanz:** Jeder vorhandene Pfad markiert genau einen Eintrag mit `aria-current="page"`.
  Rollenmatrix entspricht den bestehenden Tests; keine tote Route erscheint.
- **Nicht tun:** Vorgänge, Reminder, Mieterportal oder Nachrichten vor ihrer Implementierung als aktive
  Navigation ergänzen; neue Iconbibliothek nur für acht Symbole installieren; Autorisierung aus dem
  Frontend ableiten.

### [S5] Einheitlichen Desktop-Seitenkopf als gemeinsamen Vertrag schaffen

- **Datei/Ort:** Neuer wiederverwendbarer Seitenkopf im UI- oder Portalbereich; kontrollierte
  Einbindung in die Seiten aus `01–08`.
- **Fundstelle:** Jede Fachseite baut Überschrift, Untertitel, Breadcrumb und Aktionen derzeit selbst
  mit unterschiedlichen Abständen und Breiten.
- **Ist:** Beim Wechsel zwischen Übersicht, Objekten, Kosten, Zählern, Abrechnung und Zahlungen springen
  Titel und Aktionen sichtbar. Manche Seiten besitzen technische Untertexte oder mehrere primäre
  Aktionen.
- **Soll:** Einen gemeinsamen Desktop-Seitenkopf mit Slots für Breadcrumb, Titel, kurze Beschreibung,
  Status und Aktionen definieren. Fachseiten liefern Inhalt; die Shell beziehungsweise Komponente
  liefert Layout, Typografie und Abstand.
- **Default:** Breadcrumb optional oberhalb. Eine `h1` in Montserrat, Beschreibung in Manrope/Slate,
  Aktionen rechts oben. Genau eine primäre Aktion; weitere als sekundäre Buttons oder Menü. Kopf
  bleibt im normalen Dokumentfluss, nicht global sticky. Lange Titel umbrechen, Aktionen dürfen bei
  1280 Pixel kontrolliert in eine zweite Zeile wechseln.
- **Erwartetes Ergebnis:** Alle Hauptseiten beginnen an derselben horizontalen und vertikalen Position.
  Detailseiten behalten ihre spezifischen Breadcrumbs und Identitätsköpfe aus `07`/`08`, verwenden
  aber dieselben Grundabstände.
- **Akzeptanz:** Screenshotfolge der acht Hauptbereiche zeigt konsistente Titelbaseline, Beschreibung
  und Aktionsposition. Pro Seite existiert genau eine `h1`; keine doppelte Shellüberschrift.
- **Nicht tun:** Fachtexte vereinheitlichen oder neu erfinden; Objekt-/Einheitenbanner durch einen
  generischen Kopf ersetzen; Kopf auf Smartphone-/Tablet-Verhalten optimieren.

### [S6] Account-Menü statt überladener Fußkarte einführen

- **Datei/Ort:** Unterer Sidebarbereich, bestehende Accountdaten aus `useMe`, Kontoauswahl und
  Account-/Rollen-Tests.
- **Fundstelle:** Aktuell zeigt eine Paper-Karte Accountname, Rolle und bei mehreren Accounts eine
  vollständige Linkliste.
- **Ist:** Bei mehreren Accounts wächst die Karte stark und konkurriert mit der Hauptnavigation. Es
  gibt kein klar benanntes Account-Menü.
- **Soll:** Unten einen kompakten Account-Schalter mit Accountname und Rolle anzeigen. Aktivierung
  öffnet ein zugängliches Menü mit anderen verfügbaren Accounts und „Zur Kontoauswahl“.
- **Default:** Ausgeklappt Accountname plus Rollenlabel und Chevron; eingeklappt ein neutrales
  Account-Signet beziehungsweise Initial mit Tooltip. Aktiver Account ist markiert, aber nicht erneut
  anklickbar. Kontowechsel führt zur autorisierten Account-Startseite. Keine Einstellungen- oder
  Abmelden-Aktion erfinden, solange kein echter Pfad existiert.
- **Erwartetes Ergebnis:** Die Sidebar bleibt auch mit mehreren Accounts kompakt. Vollständige lange
  Accountnamen sind im Menü erreichbar und werden im geschlossenen Zustand kontrolliert gekürzt.
- **Akzeptanz:** Tastatur öffnet, navigiert und schließt das Menü; Escape gibt Fokus zurück. Tests
  decken ein Konto, mehrere Konten, Tax Advisor, langen Namen und fehlenden aktiven Account ab.
- **Nicht tun:** Accountwechsel nur clientseitig vortäuschen; fremde Accounts zeigen; Einstellungen,
  Logout oder Profilseiten als tote Links ergänzen.

### [S7] Inhaltsbreite und Pitch-Totraum global korrigieren

- **Datei/Ort:** Inhaltswrapper in `app-shell.tsx` und ausschließlich notwendige Lesebreiten einzelner
  Fachseiten gemäß `00_Layout-Global.md` [A3].
- **Fundstelle:** Der aktuelle globale Wrapper ist auf 1100 Pixel begrenzt und zentriert.
- **Ist:** Auf 1920-Pixel-Screens entstehen große leere Ränder; breite Objekt-, Zahlungs- und
  Abrechnungstabellen werden unnötig zusammengedrückt.
- **Soll:** Globalen Hauptbereich bis zur freigegebenen 1440-Pixel-Inhaltsbreite wachsen lassen und
  seitliche Abstände nach Desktopbreite staffeln. Lesetext darf lokal schmaler bleiben; Tabellen und
  Dashboards nutzen die größere Fläche.
- **Default:** Maximalbreite 1440 Pixel. Seitlicher Innenabstand 24 Pixel bei 1280, 32 Pixel bei 1440
  und 40 Pixel bei 1920. Zentriert innerhalb der Fläche rechts der Sidebar. Seiten definieren keine
  konkurrierenden globalen Maximalbreiten; schmale Formulare dürfen lokale Lesebreiten behalten.
- **Erwartetes Ergebnis:** Pitch-Screens nutzen sichtbar mehr Raum, ohne randlos oder gestreckt zu
  wirken. Tabellen bleiben scanbar; Fließtext wird nicht unnötig breit.
- **Akzeptanz:** Screenshots bei 1280/1440/1920 zeigen konsistente Ränder und keinen leeren Rand größer
  als etwa 15 Prozent der verfügbaren Hauptfläche je Seite bei 1920 Pixel.
- **Nicht tun:** Sidebarbreite zurückvergrößern, um Totraum zu füllen; jede Fachseite auf volle
  1440 Pixel zwingen; horizontalen Gesamtseitenscroll zulassen.

### [S8] Rollen, aktive Zustände und Direktrouten sicher erhalten

- **Datei/Ort:** Navigationsfilter, `taxAdvisorRedirectPath`, Shelltests und vorhandene
  Autorisierungs-/Rollenverträge.
- **Fundstelle:** Aktuelle Navigation filtert Zahlungen und Steuern nach Rolle und leitet Tax Advisor
  zum Steuerbereich. Objekt- und Einheitendetails gehören über `activePrefixes` zu „Objekte“.
- **Ist:** Diese Logik ist sicherheitsrelevant für eine ehrliche Navigation, obwohl der Server der
  eigentliche Schutz bleibt. Ein visueller Umbau darf sie nicht verlieren.
- **Soll:** Rollen- und Aktivzustände unverändert beziehungsweise expliziter testen. Die Shell erhält
  nur die für den Account vorhandene Rolle aus `/me`; sie erfindet keine Rechte. Direkte nicht erlaubte
  Requests bleiben Sache der API.
- **Default:** Owner sieht alle vorhandenen Owner-Module; Employee nur gemäß bestehender M5-Regeln;
  Tax Advisor ausschließlich Steuern. Während Rollenladen Skeleton statt kurzzeitig falscher Links.
  Unbekannte Rolle zeigt keine privilegierten Module und eine verständliche Zugriffssicht.
- **Erwartetes Ergebnis:** Kein Navigationseintrag blinkt beim Laden kurz sichtbar und verschwindet
  danach. Aktive Unterrouten werden zuverlässig markiert.
- **Akzeptanz:** Bestehende Account-Switcher-Tests werden erweitert um Ladezustand, unbekannte Rolle,
  Einheitenroute, Abrechnungsdetail und direkten fremden Accountpfad.
- **Nicht tun:** Rollenrechte in eine neue parallele Clientmatrix kopieren, wenn ein bestehender
  Vertrag wiederverwendet werden kann; Tax-Advisor-Redirect entfernen; versteckte Links als Schutz
  dokumentieren.

### [S9] Shell-Lade-, Fehler- und Kein-Zugriff-Zustände nutzerverständlich gestalten

- **Datei/Ort:** `app-shell.tsx`, `portal-entry.tsx` und globale Fehler-/404-Grenzen aus
  `00_Layout-Global.md` [A9].
- **Fundstelle:** Rollenladen zeigt heute nur Text, die Portal Entry meldet „Keine Verbindung zur API“
  und fragt „Läuft der Server?“, die Kein-Zugriff-Ansicht erwähnt serverseitige Prüfung.
- **Ist:** Technische Sprache ist im Pitch sichtbar. Ladezustände bilden die spätere Shell nicht ab.
- **Soll:** Strukturgetreue Shell-Skeletons, verständliche Wiederholen-Aktionen und gebrandete
  Zugriffszustände verwenden. Bereits bekannter Account-/Navigationskontext bleibt bei einem
  Teilfehler sichtbar, soweit sicher möglich.
- **Default:** Laden: Sidebar-Skeleton plus Kopf-/Inhaltsfläche. Allgemeiner Fehler: „Lokara konnte
  nicht geladen werden“ und „Erneut versuchen“. Kein Zugriff: „Kein Zugriff auf dieses Konto“ und
  „Zur Kontoauswahl“. Keine API-, Server-, Datenbank-, URL-Kontext-, HTTP- oder Stack-Sprache.
- **Erwartetes Ergebnis:** Pitch und produktive UI zeigen auch bei Fehlern eine konsistente Lokara-
  Oberfläche mit klarer Handlung.
- **Akzeptanz:** Tests decken Laden, `/me`-Fehler, unbekannten Account, 404, Retry und Tax-Advisor-
  Weiterleitung ab. Fokus landet auf Statusüberschrift beziehungsweise Retry.
- **Nicht tun:** Technische Startbefehle im Nutzer-UI zeigen; Fehler nur als Toast ausgeben; bekannte
  sichere Navigation bei einem isolierten Inhaltsfehler unnötig löschen.

### [S10] Desktop-Accessibility, Zoom und Pitch-Regressionen absichern

- **Datei/Ort:** Shell-, Account- und Navigations-Tests; visuelle Screenshots der Hauptseiten;
  vorhandene Gate-Skripte.
- **Fundstelle:** Die Shell besitzt bereits Fokusklassen und `aria-current`, aber keinen vollständigen
  Test für Rail, Account-Menü, Seitenkopf und festgelegte Pitchbreiten.
- **Ist:** Ein visueller Shellumbau kann Fokus, Rollenfilter, aktive Zustände oder Fachseitenbreite
  unbemerkt beschädigen.
- **Soll:** Tastatur-, Screenreader-, Zoom-, Rollen- und Screenshotabnahme für die Desktop-Shell
  ergänzen. Navigation besitzt semantisches `nav`, eindeutigen Namen, logisch geordnete Links und
  sichtbaren Fokus. Rail-Tooltips ersetzen nicht zugängliche Namen.
- **Default:** Screenshotmatrix 1280 × 800, 1440 × 900 und 1920 × 1080, jeweils ausgeklappt; zusätzlich
  1280 eingeklappt und 200-Prozent-Zoom auf der primären Pitchauflösung. Testseiten: Übersicht,
  Objektliste, Objektakte, Einheitenakte, Zahlungen, Zähler und Abrechnung. Reduced Motion wird geprüft.
- **Erwartetes Ergebnis:** Die Shell ist im Pitch reproduzierbar und vollständig ohne Maus bedienbar.
  Fachseiten verlieren durch die gemeinsame Breite weder Inhalt noch Fokus.
- **Akzeptanz:** Typprüfung, Lint, Webtests und Full-Gate sind grün. Screenshotvergleich zeigt keine
  Überlagerung, doppelte `h1`, abgeschnittene Navigation oder technischen Fehlertext.
- **Nicht tun:** Smartphone-/Tablet- oder native Screenshotmatrix Pre-Pitch ergänzen; Accessibility
  wegen Desktop-Fokus reduzieren; visuelle Regressionen durch pauschal größere Toleranzen verbergen.

## Out of Scope

- Smartphone-Web-Navigation, Tablet-spezifische Shell, Mobile Drawer, Bottom Navigation,
  Touch-Gesten und kleine Viewports unter 1280 Pixel.
- Native iOS-/Android-App, native Tab-Bar, Deep Links, Push Notifications, Offlinebetrieb,
  App-Store- und Gerätefunktionen.
- Fachinhalte und Informationsarchitektur aus `01–08` neu definieren.
- Globaler Objektfilter oder Objektumschalter.
- Vorgänge, Tickets, Reminder, Mahnwesen, Mieterportal und Nachrichten als neue Navigationsziele,
  solange die jeweiligen Module nicht implementiert und freigegeben sind.
- Neue Rollen, neue Rechte, Authentifizierungs- oder RLS-Logik.
- Profil-, Einstellungs-, Logout-, Hilfe- oder Supportseiten ohne existierende Produktpfade.
- Neue Icon-, Tooltip-, Menü- oder Animationsbibliothek, wenn die kleine Shellfunktion mit vorhandenen
  Mitteln umgesetzt werden kann.

## Verifikation

1. Bei 1280, 1440 und 1920 Pixel steht links eine stabile Desktopnavigation und rechts der flexible
   Hauptbereich ohne horizontalen Seitenscroll im Standardzoom.
2. Sidebar lässt sich auf 72 Pixel einklappen und auf 248 Pixel ausklappen; Präferenz bleibt nach
   Reload erhalten und Fokus bleibt am Umschalter.
3. Echtes Lokara-Logo ersetzt das CSS-Kachelzeichen und führt zur Übersicht des aktiven Accounts.
4. Navigation verwendet die Labels Übersicht, Objekte, Zahlungen, Kosten, Belege, Zähler,
   Abrechnungen und Steuern in der festgelegten Rollenmatrix.
5. Objekt- und Einheitenpfade markieren „Objekte“; Unterrouten markieren genau einen passenden
   Navigationseintrag.
6. Gemeinsamer Seitenkopf erzeugt pro Seite genau eine `h1`, konsistente Abstände und höchstens eine
   primäre Aktion. Objekt-/Einheitenbanner bleiben fachlich erhalten.
7. Account-Menü funktioniert für ein und mehrere Konten, lange Namen und Tax Advisor per Tastatur und
   gibt Fokus nach Escape zurück.
8. Inhaltsbereich nutzt bis zu 1440 Pixel; 1920-Pixel-Pitch-Screens besitzen deutlich weniger Totraum
   als die heutige 1100-Pixel-Shell.
9. Laden, `/me`-Fehler und Kein-Zugriff-Ansicht enthalten keine API-/Server-/Datenbank-/URL-Sprache und
   bieten eine klare nächste Aktion.
10. Tastatur, Screenreader, 200-Prozent-Zoom und Reduced Motion funktionieren; Fokus ist jederzeit
    sichtbar und Rollen-/Accountgrenzen bleiben unverändert.
11. Keine Smartphone-/Tablet-/native Navigation wurde als Teil dieses Specs gebaut oder vorgeführt.
12. Typprüfung, Lint, Webtests, Full-Gate und Pitch-Screenshotmatrix sind grün.

## Reihenfolge

1. [S1], [S7] — Shellgrundriss und Inhaltsbreite.
2. [S2], [S3], [S4] — Marke, Rail und Navigation.
3. [S6], [S8] — Account-Menü, Rollen und aktive Zustände.
4. [S5] — gemeinsamer Seitenkopf kontrolliert über `01–08` ausrollen.
5. [S9], [S10] — Zustände, Accessibility und Pitch-Abnahme.

## Build-Notes (füllt die KI beim Umsetzen aus)

<!-- Erwartete Einträge:
- [S2] tatsächlich vorhandenes Logo-/Signet-Asset oder fehlendes Asset.
- [S3] gewählter Präferenzschlüssel und Strategie gegen Hydration-Flash.
- [S4] verwendete vorhandene/lokale Icons; keine neue Dependency.
- [S5] migrierte Seiten und bewusst erhaltene Detailseitenköpfe.
- [S6] tatsächlich verfügbare Accountaktionen; keine toten Links.
- [S7] Seiten mit begründeter lokaler Lesebreite.
- [S10] Screenshotauflösungen, primäre Pitchauflösung und Prüfergebnisse.
-->
