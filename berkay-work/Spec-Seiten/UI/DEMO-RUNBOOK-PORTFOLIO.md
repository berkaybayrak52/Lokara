# DEMO-RUNBOOK-PORTFOLIO.md — realistische Lokara-Portfolio-Demo

Dieses Runbook beschreibt das nächste vollständige Demo-Szenario. Es ersetzt das bestehende
`DEMO-RUNBOOK.md` nicht: Der dort dokumentierte kanonische 1.200-€-Abrechnungsfall bleibt als
technisches Rechen-Fixture erhalten und wird als Teil des größeren Portfolios weiterverwendet.

Zielbild: Die Demo wirkt wie ein Konto, das seit mehreren Monaten aktiv mit Lokara arbeitet. Objekte,
Mietverhältnisse, Kosten, Zähler, Forderungen, Bankumsätze, Barzahlungen, Zuordnungen und Dashboard-
Summen stammen aus einem gemeinsamen, reproduzierbaren Seed. Keine Seite erfindet eigene Beträge.

---

## 1. Dynamischer Demo-Stichtag

Der Seed verwendet einen expliziten `demo_today`-Stichtag. Im normalen lokalen Demo-Lauf entspricht er
dem aktuellen Datum in der konfigurierten Account-Zeitzone. Tests dürfen ihn fest vorgeben.

Davon werden folgende Zeiträume abgeleitet:

- `M0`: laufender Kalendermonat von `demo_today`;
- `M-1` bis `M-8`: die acht davorliegenden vollständigen Kalendermonate;
- `Y-1`: das vollständige Kalenderjahr vor dem Jahr von `demo_today`;
- „heute“, „überfällig“ und Consent-Ablauf werden ausschließlich aus `demo_today` beziehungsweise einem
  expliziten timezone-aware `demo_now` berechnet.

### Determinismus

- Feste IDs, Namen, Adressen, Vertragsbeträge, Kosten und Zählerwerte.
- Keine Zufallszahlen zur Laufzeit.
- Derselbe `demo_today` erzeugt bytegleich dieselben fachlichen Demo-Eingaben.
- Ein späterer Kalendermonat verschiebt Monatsperioden und Status kontrolliert weiter, ohne Identitäten
  oder historische Grundmuster zu verändern.
- Geld bleibt in ganzzahligen Cent; Zeitreihen verwenden echte Kalendergrenzen, keine „30 Tage = Monat“-\
  Abkürzung.
- `Demo zurücksetzen` stellt exakt den für den aktuellen Stichtag erwarteten Zustand wieder her.

### Ehrliche Kennzeichnung

- Bankkonto-Provider: `finapi-demo`, sichtbarer Text „Demo-Bankverbindung“.
- Kein Text behauptet, dass eine echte finAPI-Session oder ein echtes Bankkonto verbunden ist.
- Demo-OCR, E-Mail-Eingang, Foto-Upload und Versand bleiben als Demo/Beta/inaktiv gekennzeichnet, solange
  die echten Integrationen fehlen.
- Mieterportal, Nachrichten und allgemeine Einheiten-Dokumente werden nur dann als aktiv dargestellt,
  wenn persistierte Demo-Datensätze, Berechtigungen und die zugehörigen Produktpfade umgesetzt sind.
  Bis dahin erscheinen die vorgesehenen Zustände ausschließlich als inaktiver Zukunftsausblick.
- Lokara bewertet **niemals die rechtliche Zulässigkeit einer Mieterhöhung**. Die Demo darf nur
  dokumentierte Vertragsfakten wie Vertragsbeginn, Vertragsart und die letzte erfasste Mietänderung
  anzeigen. Sie zeigt weder „Mieterhöhung möglich“, einen frühesten zulässigen Termin noch eine
  rechtliche Empfehlung.

### Pre-Pitch-Anzeigegeräte

- Die Portfolio-Demo wird als Desktop-/Laptop-Web-App vorgeführt.
- Verbindliche Abnahmebreiten sind 1280, 1440 und 1920 Pixel; primäre Pitch-Auflösung ist die
  tatsächlich verwendete Präsentationsauflösung, standardmäßig 1920 × 1080.
- 200-Prozent-Zoom, Tastatur, Screenreader-Grundstruktur und sichtbarer Fokus bleiben Bestandteil der
  Pre-Pitch-Abnahme.
- Eigenständige Smartphone-/Tablet-Informationsarchitektur, Touch-Navigation, mobile Web-Abnahme und
  native iOS-/Android-App sind Post-Pitch. Die Demo behauptet diese Produktvarianten nicht.

---

## 2. Portfolio und Objekte

### Objekt A — Musterstraße 12, Frankfurt am Main

Bestandsobjekt und kanonischer Abrechnungsfall. Das Gebäude bleibt die Quelle des bestehenden
1.200-€-Golden-Fixtures.

| Einheit | Nutzung | Fläche | Aktueller Zustand | Kaltmiete | NK-VZ | Heiz-VZ | Monatliches Soll |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| Wohnung A · EG links | Wohnen | 50,00 m² | Anna Beispiel, aktiv seit 01.04.2023 | 950,00 € | 160,00 € | 60,00 € | **1.170,00 €** |
| Wohnung B · EG rechts | Wohnen | 30,00 m² | Mieterwechsel, aktuelle Partei seit Beginn `M-5` | 680,00 € | 110,00 € | 40,00 € | **830,00 €** |
| Wohnung C · 1. OG links | Wohnen | 20,00 m² | Clara Vorlage, aktiv seit 01.01.2024 | 520,00 € | 80,00 € | 30,00 € | **630,00 €** |
| Wohnung D · 1. OG rechts | Wohnen | 45,00 m² | David Sommer, aktiv seit 01.02.2022 | 780,00 € | 140,00 € | 50,00 € | **970,00 €** |
| Dachgeschoss | Wohnen | 62,00 m² | Eva König, aktiv seit 01.09.2024 | 1.100,00 € | 180,00 € | 70,00 € | **1.350,00 €** |
| Ladenlokal | Gewerbe | 78,00 m² | Kiez Café GmbH, aktiv seit 01.06.2021 | 1.450,00 € | 220,00 € | 80,00 € | **1.750,00 €** |

Aktuelles monatliches Soll Objekt A: **6.700,00 €**.

Historie Wohnung B:

- Bernd Muster: Mietende am letzten Tag von `M-7`;
- genau ein voller Kalendermonat Leerstand in `M-6`;
- Fatma Yilmaz: Mietbeginn am ersten Tag von `M-5`;
- alte Zahlungen bleiben Bernd zugeordnet, neue Forderungen und Zahlungen gehören ausschließlich Fatma;
- der Leerstandsmonat erzeugt keine Mieterforderung.

### Objekt B — Lindenweg 8, Mainz

Kleines Wohnhaus mit Leerstand und Eigennutzung.

| Einheit | Nutzung | Fläche | Aktueller Zustand | Kaltmiete | NK-VZ | Heiz-VZ | Monatliches Soll |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| Wohnung 1 · EG | Wohnen | 58,00 m² | Jonas Weber, aktiv | 890,00 € | 155,00 € | 55,00 € | **1.100,00 €** |
| Wohnung 2 · 1. OG | Wohnen | 49,00 m² | Lea Neumann, aktiv | 760,00 € | 130,00 € | 50,00 € | **940,00 €** |
| Wohnung 3 · 2. OG | Wohnen | 66,00 m² | Maria Santos, aktiv | 990,00 € | 165,00 € | 65,00 € | **1.220,00 €** |
| Einliegerwohnung | Wohnen | 42,00 m² | Leerstand seit Beginn `M-2` | 650,00 € zuletzt | 115,00 € | 45,00 € | **0,00 € aktuell** |

Aktuelles monatliches Soll Objekt B: **3.260,00 €**.

Für die Einliegerwohnung existiert ein beendetes Mietverhältnis bis zum letzten Tag von `M-3`. Die
Einheit ist weder als offene Mietforderung noch als „Mieter zahlt nicht“ zu behandeln. Optional wird
ein zeitlich begrenzter Eigennutzungszeitraum ab Beginn `M0` geführt, damit Leerstand und Eigennutzung
auf Objekt- und Abrechnungsseiten unterscheidbar bleiben.

### Objekt C — Hafenallee 27, Wiesbaden

Gemischt genutztes Objekt mit höheren Beträgen und mehreren Kontobewegungen.

| Einheit | Nutzung | Fläche | Aktueller Zustand | Kaltmiete | NK-VZ | Heiz-VZ | Monatliches Soll |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| Loft 1 | Wohnen | 82,00 m² | Noah Richter, aktiv | 1.250,00 € | 200,00 € | 80,00 € | **1.530,00 €** |
| Loft 2 | Wohnen | 74,00 m² | Sophie Klein, aktiv | 1.080,00 € | 175,00 € | 65,00 € | **1.320,00 €** |
| Büroeinheit | Gewerbe | 132,00 m² | Rheinblick Design UG, aktiv | 2.100,00 € | 330,00 € | 120,00 € | **2.550,00 €** |

Aktuelles monatliches Soll Objekt C: **5.400,00 €**.

### Portfolio-Kontrollsumme

| Kennzahl | Wert |
| --- | ---: |
| Objekte | **3** |
| Einheiten | **13** |
| aktuell vermietete Einheiten | **12** |
| aktuell nicht vermietet/eigengenutzt | **1** |
| monatliches aktuelles Mietsoll | **15.360,00 €** |

Das Mietsoll ist die Summe der zwölf aktiven Mietverhältnisse. Es wird backendseitig aus den zum
Stichtag gültigen Vertrags- und Vorauszahlungsperioden gebildet, nicht als Portfolio-Konstante an das
Frontend geliefert.

### Einheitenakten-Zusatzdaten

Diese synthetischen Stammdaten ergänzen die Einheiten-Demo. Kaltmiete je Quadratmeter wird nicht als
zweite Konstante gespeichert, sondern serverseitig aus der zum Stichtag gültigen Kaltmiete und der
erfassten Fläche projiziert. Fehlt einer der beiden Werte, zeigt die Einheitenakte „–“.

| Einheit | Zimmer | Ausstattung (Auswahl) | Garage/Stellplatz | Vertragsart | Letzte dokumentierte Mietänderung |
| --- | ---: | --- | --- | --- | --- |
| Musterstraße · Wohnung A | 2 | Einbauküche, Keller | kein Stellplatz | unbefristeter Wohnraummietvertrag | Beginn `M-18`, neuer Kaltmietbetrag dokumentiert |
| Musterstraße · Wohnung B | 1 | Keller | kein Stellplatz | unbefristeter Wohnraummietvertrag | keine Änderung seit Mietbeginn `M-5` |
| Musterstraße · Wohnung C | 1 | Balkon, Keller | kein Stellplatz | unbefristeter Wohnraummietvertrag | keine dokumentierte Änderung |
| Musterstraße · Wohnung D | 2 | Einbauküche, Balkon | Außenstellplatz, separat ausgewiesen | unbefristeter Wohnraummietvertrag | Beginn `M-14`, neuer Kaltmietbetrag dokumentiert |
| Musterstraße · Dachgeschoss | 3 | Einbauküche, Keller | Garage, im Mietverhältnis eingebunden | unbefristeter Wohnraummietvertrag | keine Änderung seit Mietbeginn |
| Musterstraße · Ladenlokal | – | Lagerraum, Kundentoilette | zwei Außenstellplätze, separat ausgewiesen | befristeter Gewerbemietvertrag | Beginn `M-20`, Nachtrag dokumentiert |
| Lindenweg · Wohnung 1 | 2 | Balkon, Keller | kein Stellplatz | unbefristeter Wohnraummietvertrag | Beginn `M-13`, neuer Kaltmietbetrag dokumentiert |
| Lindenweg · Wohnung 2 | 2 | Einbauküche, Keller | Carport, im Mietverhältnis eingebunden | unbefristeter Wohnraummietvertrag | keine dokumentierte Änderung |
| Lindenweg · Wohnung 3 | 3 | Balkon, Gäste-WC | kein Stellplatz | unbefristeter Wohnraummietvertrag | Beginn `M-16`, neuer Kaltmietbetrag dokumentiert |
| Lindenweg · Einliegerwohnung | 1 | möbliert, Terrasse | kein Stellplatz | letztes Mietverhältnis beendet | letzte Änderung gehört zum beendeten Vertrag |
| Hafenallee · Loft 1 | 3 | Aufzug, Einbauküche, Balkon | Tiefgaragenstellplatz, separat ausgewiesen | unbefristeter Wohnraummietvertrag | Beginn `M-12`, neuer Kaltmietbetrag dokumentiert |
| Hafenallee · Loft 2 | 2 | Aufzug, Balkon | kein Stellplatz | unbefristeter Wohnraummietvertrag | keine dokumentierte Änderung |
| Hafenallee · Büroeinheit | – | Aufzug, Teeküche, Serverraum | drei Stellplätze, im Vertrag eingebunden | befristeter Gewerbemietvertrag | Beginn `M-15`, Nachtrag dokumentiert |

„Im Mietverhältnis eingebunden“ und „separat ausgewiesen“ sind reine Vertragsfakten. Die Demo leitet
daraus keine zusätzliche Forderung ab, solange Betrag, Periode und Forderungskomponente nicht
ausdrücklich im autoritativen Vertrags- und Forderungsmodell vorhanden sind. Zimmer bleiben bei
Gewerbeeinheiten leer; das Frontend setzt dort nicht ersatzweise einen geratenen Wert ein.

### Mieterportal, Nachrichten und Einheiten-Dokumente

Die folgenden Zustände sorgen später für unterschiedliche Einheitenakten. Namen und Inhalte sind
synthetisch. Ein Portalzugang gehört einer konkreten Mietpartei innerhalb eines Mietverhältnisses;
bei mehreren Parteien wird nicht still nur die erste Person eingeladen.

| Einheit/Mietpartei | Portalzustand | Nachrichten | Dokumente |
| --- | --- | --- | --- |
| Wohnung A · Anna Beispiel | aktiv, letzter Zugriff `demo_now - 3 Tage` | 1 ungelesene Nachricht „Rückfrage zur Abrechnung“ | Mietvertrag, Übergabeprotokoll, letzte Mietänderung, finalisierte Abrechnung |
| Wohnung B · Fatma Yilmaz | noch nicht eingeladen | keine Konversation | Mietvertrag, Übergabeprotokoll |
| Dachgeschoss · Eva König | Einladung offen seit `demo_now - 4 Tage` | keine Konversation | Mietvertrag, Nachtrag |
| Lindenweg Wohnung 1 · Jonas Weber | aktiv | 2 Nachrichten, zuletzt „Teilzahlung M0“ | Mietvertrag, Übergabeprotokoll |
| Lindenweg Wohnung 3 · Maria Santos | aktiv | 1 gelesene Konversation zur ungeklärten Überzahlung | Mietvertrag, letzte Mietänderung |
| Loft 2 · Sophie Klein | aktiv | keine Konversation; Einheitenakte bietet „Nachricht schreiben“ | Mietvertrag, Übergabeprotokoll |
| Büroeinheit · Rheinblick Design UG | zwei aktive Portalpersonen | 1 ungelesene Nachricht „Zählerstand Büro“ | Gewerbemietvertrag, Nachtrag, Übergabeprotokoll |

Portalaktionen verwenden je nach Zustand „Mieterportal einrichten“, „Einladung erneut senden“ oder
„Portalzugriff verwalten“. Ein erneuter Versand erzeugt keine zweite aktive Berechtigung. Ohne echten
Versandadapter darf die Demo höchstens eine persistierte Demo-Einladung erzeugen und kennzeichnet sie
als Demo; sie behauptet keine zugestellte E-Mail.

Das Nachrichten-Widget zeigt höchstens die drei neuesten Konversationen und verlinkt anschließend in
das Nachrichtenportal. Ohne Nachrichten erscheint „Noch keine Nachrichten“ mit „Nachricht schreiben“.
Dieser Button ist nur aktiv, wenn Nachrichtenpersistenz, Empfängerberechtigung und Versandpfad echt
vorhanden sind.

Allgemeine Einheiten-Dokumente erhalten mindestens Dokumentart, Dateiname, Mietverhältnisbezug,
Erstellzeitpunkt, Größe und Sichtbarkeit für das Mieterportal. Ohne echten Storage bleiben Öffnen,
Download, Upload und Löschen inaktiv. Finalisierte Abrechnungsdokumente verwenden weiterhin ihr
bestehendes unveränderliches Archiv und werden nicht in einen zweiten Dokumentbestand kopiert.

---

## 3. Personen und Matching-Profile

Jede aktive Mietpartei erhält einen Matching-Datensatz mit normalisiertem Nachnamen und optionalem
Zahlungscode. Namen, Codes und Demo-IBANs sind synthetisch.

| Mietpartei | Zahlungscode | Erwartetes Zahlungsverhalten |
| --- | --- | --- |
| Anna Beispiel | `M12-A` | pünktlich, bekannte IBAN, exakter Betrag |
| Fatma Yilmaz | `M12-B` | neue IBAN seit Mietbeginn, einmal manuell bestätigt |
| Clara Vorlage | `M12-C` | Dauerauftrag am letzten Bankarbeitstag des Vormonats |
| David Sommer | `M12-D` | regelmäßig am 3. Kalendertag |
| Eva König | `M12-DG` | gemeinsames Konto, Absendername wechselt gelegentlich |
| Kiez Café GmbH | `M12-LADEN` | Geschäftszahlung mit Buchungsreferenz |
| Jonas Weber | `LW8-1` | pünktlich, einmalige Teilzahlung in `M0` |
| Lea Neumann | `LW8-2` | pünktlich, einmal 2 Tage verspätet |
| Maria Santos | `LW8-3` | Überzahlung in `M0`, Nutzerprüfung erforderlich |
| Noah Richter | `HA27-L1` | exakter Dauerauftrag |
| Sophie Klein | `HA27-L2` | in `M0` noch nicht eingegangen |
| Rheinblick Design UG | `HA27-BUERO` | Zahlung auf separates Mietkonto |

Die historische Mustererkennung darf erst nach mindestens drei bestätigten vergleichbaren Zahlungen
einen Hinweis „abweichend vom üblichen Zahlungsstrom“ erzeugen. Das Muster ist Entscheidungshilfe,
keine automatische Buchungsregel.

---

## 4. Demo-Bankkonten

| Konto | Demo-IBAN | Zweck | Consent-Zustand |
| --- | --- | --- | --- |
| Mietkonto Wohnen | endet auf `5937` | Objekte A und B | aktiv, Ablauf `demo_now + 90 Tage` |
| Mietkonto Hafenallee | endet auf `1842` | Objekt C | aktiv, Ablauf `demo_now + 12 Tage`, UI zeigt „Läuft bald ab“ |
| Rücklagenkonto | endet auf `7710` | Rücklagen/sonstige Bewegungen | aktiv, keine Mietzuordnung im Standard |

Alle drei Konten verwenden den Provider `finapi-demo`. Die vollständigen synthetischen IBANs liegen nur
im Seed; die Standardoberfläche zeigt Anzeigename und letzte vier Zeichen.

Der „letzte erfolgreiche Abruf“ liegt bei jedem Laden reproduzierbar am `demo_now` minus 12 Minuten.
Der nächste Klick auf „Umsätze aktualisieren“ darf den Zeitpunkt echt aktualisieren, erzeugt aber keine
zufälligen neuen Umsätze.

---

## 5. Forderungshistorie

### Wiederkehrende Mieten

- Für jedes in einem Monat aktive Mietverhältnis wird genau eine idempotente Forderung erzeugt.
- Komponenten: Kaltmiete, NK-Vorauszahlung und Heizkostenvorauszahlung gemäß der für den Monat gültigen
  versionierten Vertragsdaten.
- Perioden `M-8` bis `M0` werden angelegt.
- Keine Forderung für Wohnung B im Leerstandsmonat `M-6`.
- Keine Forderung für die Einliegerwohnung ab Ende ihres Mietverhältnisses.
- Wiederholtes Seeden oder Reset erzeugt keine doppelten Forderungen.

### Abrechnung und Nachzahlung

Das bestehende Golden-Fixture für Musterstraße 12 bleibt erhalten:

| Position | Wert |
| --- | ---: |
| Müllabfuhr, Abrechnungsjahr `Y-1` | **1.200,00 €** |
| Heizungs- und Warmwasserkosten | **10.300,00 €** |
| CO₂-Kosten darin | **261,80 €** |

Zusätzlich existiert eine finalisierte Demo-Abrechnung für Anna Beispiel mit einer offenen
Betriebskosten-Nachzahlung von **245,00 €**, fällig an einem explizit gesäten Datum in `M0`. Der Betrag
wird aus dem finalisierten Settlement kopiert, nicht neu berechnet.

Ein Abrechnungsguthaben von **86,40 €** für Clara Vorlage wird als Verpflichtung/Guthabeninformation
geführt und nicht als negative Mietforderung erfunden. Eine Auszahlung oder automatische Verrechnung
ist nicht Teil der Demo.

---

## 6. Mehrmonatige Zahlungshistorie

### Grundmuster `M-8` bis `M-2`

Die Demo zeigt, dass das Konto seit Monaten benutzt wird:

- alle regulären Forderungen werden als echte Banktransaktionen importiert;
- die Mehrheit wird automatisch über bekannte eindeutige IBAN und exakten Betrag zugeordnet;
- Clara zahlt regelmäßig kurz vor Monatsbeginn; die Forderungsperiode bleibt trotzdem korrekt;
- Lea zahlt in `M-4` zwei Tage nach ihrem üblichen Zeitpunkt, aber vollständig;
- Fatmas erste Zahlung in `M-5` kommt von einer neuen IBAN, wird manuell bestätigt und lernt die IBAN;
- ab `M-4` können ihre eindeutigen Zahlungen automatisch zugeordnet werden;
- Rheinblick Design zahlt auf das separate Mietkonto Hafenallee;
- ausgehende Kontobewegungen bleiben sichtbar, werden aber nicht gegen Mietforderungen gematcht.

Pro vollständigem historischen Monat entstehen ungefähr 14 bis 18 Bewegungen: elf Mietzahlungen,
Bankgebühren/sonstige Ausgaben, eine Rücklagenumbuchung und gelegentliche Korrektur- oder
Abrechnungsbewegungen. Damit enthält die Startliste je nach Stichtag ungefähr 120 bis 150 Umsätze.

### Gezielte historische Sonderfälle

| Periode | Umsatz | Betrag | Erwartetes Ergebnis |
| --- | --- | ---: | --- |
| `M-5` | Erste Zahlung Fatma Yilmaz | 830,00 € | Review, manuell bestätigt, IBAN gelernt |
| `M-4` | Lea Neumann, vollständige Miete | 940,00 € | automatisch zugeordnet, historischer Zeitpunkt leicht abweichend |
| `M-3` | Kiez Café GmbH, doppelt importierte Provider-ID | 1.750,00 € | zweiter Import übersprungen, keine zweite Zeile |
| `M-3` | Ähnlicher zweiter Umsatz Kiez Café | 1.750,00 € | als mögliche Dublette behalten und sichtbar geprüft |
| `M-2` | Rücklastschrift zu David Sommer | −970,00 € | kompensierendes Journalereignis, Forderung wieder offen |
| `M-2` | Ersatzüberweisung David Sommer | 970,00 € | Forderung erneut ausgeglichen |
| `M-1` | Barzahlung für Nachzahlung | 120,00 € | Quelle Barzahlung, Teilzahlung auf 245,00 € Nachzahlung |

---

## 7. Laufender Monat `M0` — sichtbare Demo-Arbeit

Der laufende Monat ist bewusst noch nicht vollständig erledigt. So bietet die Seite echte Aktionen.

### Reguläre und automatisch zugeordnete Eingänge

| Gegenpartei | Betrag | Ergebnis |
| --- | ---: | --- |
| Anna Beispiel | 1.170,00 € | automatisch zugeordnet, Monatsmiete ausgeglichen |
| Fatma Yilmaz | 830,00 € | automatisch zugeordnet |
| Clara Vorlage | 630,00 € | automatisch zugeordnet, Eingang vor Monatsbeginn möglich |
| David Sommer | 970,00 € | automatisch zugeordnet |
| Eva König / abweichender Kontoinhaber | 1.350,00 € | Review wegen Absenderwechsel, Betrag/Periode passen |
| Kiez Café GmbH | 1.750,00 € | automatisch zugeordnet |
| Lea Neumann | 940,00 € | automatisch zugeordnet |
| Noah Richter | 1.530,00 € | automatisch zugeordnet |
| Rheinblick Design UG | 2.550,00 € | automatisch auf Mietkonto Hafenallee zugeordnet |

Automatisch beziehungsweise eindeutig eingegangene Summe ohne die noch offene Eva-Prüfung:
**10.370,00 €**. Mit bestätigter Eva-Zahlung: **11.720,00 €**.

### Teilzahlung

Jonas Weber zahlt **600,00 €** auf eine Monatsforderung von **1.100,00 €**.

Erwartete Sidebar-Vorschau:

- Zahlung: 600,00 €;
- Forderung: 1.100,00 €;
- verrechnet: 600,00 €;
- verbleibend offen: 500,00 €;
- neuer Forderungsstatus: „Teilweise bezahlt“;
- Dashboard und Reminder zeigen nur die verbleibenden 500,00 €.

### Überzahlung und Guthabenprüfung

Maria Santos überweist **1.320,00 €** auf eine Monatsforderung von **1.220,00 €**.

Erwartete Sidebar-Vorschau:

- Zahlung: 1.320,00 €;
- offene Forderung: 1.220,00 €;
- mögliche Verrechnung: 1.220,00 €;
- verbleibende Abweichung: 100,00 €;
- Hinweis „100,00 € über offenem Betrag — bitte prüfen“;
- Optionen „Andere offene Forderung“, „Als Guthaben verbuchen“ und „Vorerst ungeklärt lassen“;
- Demo-Startzustand: noch nicht bestätigt, damit die Aktion live vorgeführt werden kann.

Nach ausdrücklicher Guthabenbestätigung wird die Forderung ausgeglichen und ein Guthaben von 100,00 €
im unveränderlichen Journal geführt. Keine automatische Verrechnung mit `M+1`.

### Noch fehlender Zahlungseingang

Für Sophie Klein ist die Forderung über **1.320,00 €** vorhanden, aber in `M0` noch keine Zahlung
importiert. Die Zahlungsseite erfindet keinen Umsatz. Dashboard zeigt den offenen Betrag; das
Reminder-System erhält nur Fälligkeit und offenen Saldo und entscheidet separat, ob bereits Handlungs-
bedarf besteht.

### Offene Betriebskosten-Nachzahlung

Von Annas 245,00-€-Nachzahlung wurden in `M-1` bar 120,00 € verbucht. Offen bleiben **125,00 €**.
Die Teilzahlung ist sowohl in der Zahlungshistorie als auch in der Abrechnung/Forderungsansicht sichtbar.

### Nicht zugeordnete und ignorierbare Umsätze

| Umsatz | Betrag | Konto | Demo-Aktion |
| --- | ---: | --- | --- |
| „Überweisung Emir P.“ ohne passenden Code | +50,00 € | Mietkonto Wohnen | nicht zugeordnet, Sidebar öffnen |
| PayPal Europe Einkauf | −7,50 € | Rücklagenkonto | als privat/nicht relevant ignorieren |
| Bankentgelt Kontoführung | −9,90 € | Mietkonto Wohnen | sonstige Ausgabe oder ignorieren |
| Interne Umbuchung Rücklage | −500,00 € / +500,00 € | Mietkonto/Rücklagenkonto | als interne Umbuchung ignorieren |
| Erstattung Versicherung | +184,60 € | Rücklagenkonto | sonstige Einnahme, keine Mietforderung |

### M0-Kontrollsummen vor Live-Aktionen

| Kennzahl | Wert |
| --- | ---: |
| aktuelles Mietsoll | **15.360,00 €** |
| eindeutig/automatisch zugeordnet | **10.370,00 €** |
| Review Eva, passend aber unbestätigt | **1.350,00 €** |
| Teilzahlung Jonas eingegangen | **600,00 €** |
| Überzahlung Maria ungeklärt | **1.320,00 €** |
| Sophie noch ohne Zahlung | **1.320,00 € offen** |
| offener Rest Jonas | **500,00 €** |
| offener Rest Nachzahlung Anna | **125,00 €** |
| ungeklärter Überzahlungsrest Maria | **100,00 €** |

Die Dashboard-Kennzahl „eingegangene Miete“ darf nur serverseitig fachlich verbuchte Beträge zählen.
Unbestätigte Reviews und ungeklärte Überzahlungsreste werden getrennt als Prüfbestand gezeigt, nicht
vorsorglich in Einnahmen oder offene Miete eingerechnet.

---

## 8. Kosten, Zähler und Abrechnungen

### Kostenbestand

Jedes Objekt besitzt mehrere Kostenzeilen für `Y-1` und einige laufende Kosten in `M0`:

- Musterstraße 12: Müllabfuhr 1.200,00 €, Heizung/Warmwasser 10.300,00 €, Gebäudeversicherung,
  Hausreinigung und Allgemeinstrom;
- Lindenweg 8: Wasser/Abwasser, Müll, Versicherung, Gartenpflege und Heizung;
- Hafenallee 27: Versicherung, Aufzug, Reinigung, Allgemeinstrom und Heizung;
- mindestens eine Position mit Status „Prüfen“, damit der Kosten-Wizard und Readiness-Block sichtbar
  sind;
- keine Kostenposition wird im Frontend hartcodiert oder doppelt als Zahlungsumsatz gezählt.

### Zählerbestand

- Die bestehenden Musterstraße-Zähler und Golden-Werte bleiben unverändert.
- Lindenweg 8 erhält Hauptwärmezähler sowie Wohnungszähler für die vermieteten Einheiten.
- Hafenallee 27 zeigt gemischte Geräte und einen Zähler mit bald ablaufender Eichfrist.
- Ein bewusst abgelaufener, nicht für die Golden-Heizberechnung verwendeter Kaltwasserzähler bleibt als
  Reminder-Demofall erhalten.

### Abrechnungszustände

- Musterstraße 12: `Y-1` finalisiert beziehungsweise vollständig vorschaufähig; kanonischer 1.200-€-
  Fall bleibt präsentierbar.
- Lindenweg 8: Entwurf mit fehlender Endablesung oder noch zu prüfender Kostenposition.
- Hafenallee 27: noch kein Entwurf; positive Onboarding-Aktion „Abrechnung erstellen“.

So zeigt die Abrechnungsliste drei realistische Lebenszykluszustände statt drei identischer Beispiele.

---

## 9. Dashboard-Zielwerte

Das Dashboard liest ausschließlich Portfolio-Aggregate aus dem Backend.

### Stabile Strukturwerte

- 3 Objekte;
- 13 Einheiten;
- 12 aktuell vermietet;
- 1 nicht vermietet/eigengenutzt;
- 15.360,00 € aktuelles Monatsmietsoll.

### Dynamische Finanzwerte

- „Eingegangene Miete“ entspricht der Summe fachlich verbuchter M0-Mietallokationen;
- „Offene Posten“ entspricht offenen Forderungssalden, nicht ungeklärten Bankumsätzen;
- „Zu prüfen“ zählt offene Reviews, nicht automatisch alle nicht zugeordneten Ausgaben;
- der 12-Monats-Cashflow wird aus gesäten Bank- und manuellen Zahlungsereignissen aggregiert;
- nach Bestätigung von Eva, Jonas oder Maria ändern sich die Kennzahlen ohne Reset und ohne neue
  Frontend-Mockwerte.

Der bisherige Dashboard-Demohelfer mit 82-%-/18-%-Ableitung wird nach Anbindung dieser echten Demo-
Aggregate nicht parallel weiterverwendet.

---

## 10. Vorführung — empfohlener Klickpfad

### 1 — Demo laden und Dashboard

- **Demo-Szenario laden** beziehungsweise **Demo zurücksetzen**.
- Zeigen: 3 Objekte, 13 Einheiten, 12 vermietet und echte Finanzwerte.
- Sagen: „Das ist kein Screenshot. Alle Seiten lesen denselben reproduzierbaren Demo-Datensatz.“

### 2 — Objekte

- Zwischen Liste und Karte wechseln.
- Musterstraße 12 öffnen und den Mieterwechsel in Wohnung B zeigen.
- Lindenweg 8 öffnen und Leerstand/Eigennutzung von einer offenen Mietforderung abgrenzen.
- Annas Einheit öffnen und Eckdaten, aktuelles Mietverhältnis, dokumentierte Mietänderung,
  Zahlungs-/Nachzahlungssaldo, Portalstatus, Nachricht und Dokumente als zusammenhängende
  Einheitenakte zeigen.
- Fatmas Einheit als Kontrast öffnen: Portal noch nicht eingerichtet, keine Nachrichten und keine
  dokumentierte Mietänderung seit Mietbeginn. Keine fehlenden Werte durch Frontend-Mocks auffüllen.

### 3 — Zahlungen

- Filter „Nicht zugeordnet“ und „Prüfen“ zeigen.
- Eva-Zahlung öffnen und den Vorschlag bestätigen.
- Jonas-Teilzahlung zeigen: 600,00 € bezahlt, 500,00 € offen.
- Maria-Überzahlung öffnen und 100,00 € ausdrücklich als Guthaben verbuchen.
- PayPal-Umsatz ignorieren und anschließend im Filter „Ignoriert“ zeigen.
- Annas Barzahlung auf die Betriebskosten-Nachzahlung zeigen.

### 4 — Dashboard erneut

- Ohne Reload-Zwang zurückkehren.
- Geänderte Zahlungssumme, Prüfbestand und offene Posten zeigen.
- Erklären, dass ungeklärte Umsätze und offene Forderungen getrennte Kennzahlen sind.

### 5 — Kosten und Zähler

- Einen abrechnungsreifen und einen zu prüfenden Kostenfall zeigen.
- Bestehende Golden-Zähler und einen Eichfrist-Hinweis zeigen.
- Keine produktive OCR- oder Funkintegration behaupten.

### 6 — Abrechnung

- Drei Lebenszykluszustände in der Abrechnungsliste zeigen.
- Musterstraße öffnen und den bestehenden 1.200-€-Fall/PDF vorführen.
- Zeigen, dass bestätigte Zahlungsbestandteile und offene Nachzahlung aus demselben Journal stammen.

---

## 11. Ehrliche Antworten

**Sind die Bankdaten echt?**

Nein. Es sind synthetische, persistierte Demo-Bankdaten hinter demselben Adapter- und Datenvertrag,
den später finAPI bedient. Die Demo zeigt den vorgesehenen Produktfluss, nicht eine aktive Bank-
verbindung.

**Sind die Beträge hartcodiert?**

Vertrags-, Kosten- und Demo-Transaktionsinputs sind reproduzierbare Seed-Fixtures. Salden, Status,
Zuordnungen, Teilzahlungen, Guthaben und Dashboard-Aggregate werden daraus im Backend berechnet. Das
Frontend besitzt keine eigene Geldlogik.

**Warum verschieben sich die Monate?**

Das Portfolio soll dauerhaft wie ein aktiv genutztes Konto wirken. Der Seed leitet Perioden relativ
zum expliziten Demo-Stichtag ab. Tests können denselben Stichtag einfrieren und bleiben deterministisch.

**Kann das Guthaben automatisch mit dem nächsten Monat verrechnet werden?**

Noch nicht. Die Demo zeichnet das bestätigte Guthaben nachvollziehbar auf. Auszahlung oder spätere
Verrechnung benötigen eine gesondert freigegebene Produkt- und Rechtsregel.

**Ist das Mahnwesen fertig?**

Nein. Lokara kann offene Forderung, Fälligkeit und Zahlungshistorie liefern. Mahnstufe, Verzug, Zinsen,
Gebühren und Schreiben gehören in den später freizugebenden Reminder-/Mahnfluss.

**Bewertet Lokara, ob eine Mieterhöhung rechtlich zulässig ist?**

Nein. Lokara zeigt ausschließlich die im System dokumentierten Vertrags- und Änderungsdaten. Es
berechnet und empfiehlt weder die rechtliche Zulässigkeit noch einen frühesten zulässigen Termin für
eine Mieterhöhung.

---

## 12. Seed- und Reset-Anforderungen

- Seed und Reset sind account-gescopet und idempotent.
- Feste Demo-IDs verwenden; Perioden enthalten den abgeleiteten Monat, wo mehrere Monatszeilen nötig
  sind.
- Unveränderliche Belege nicht überschreiben. Wenn ein bestehender Demo-Nachweis fachlich korrigiert
  werden muss, eine neue Version beziehungsweise ein kompensierendes Ereignis anlegen.
- Reset entfernt beziehungsweise neutralisiert nur Demo-Zustände, ohne echte andere Accounts zu lesen
  oder zu verändern.
- Child-before-parent-Reihenfolge für entfernbare Demozeilen einhalten.
- Demo-Reset darf keine aktiven Membership-/Person-Zeilen löschen und den Nutzer nicht aussperren.
- Consent-Ablauf und „letzter Abruf“ aus `demo_now` neu ableiten; fachliche historische Buchungsdaten
  bleiben an `demo_today` gebunden.
- Kein produktiver Provider-Aufruf während Seed, Test oder Reset.
- Jede neue Demo-Tabelle ist in Reset, RLS-/FK-Prüfung und Demo-Gate berücksichtigt.

---

## 13. Green-light-Checkliste

- [ ] Demo-Reset erzeugt genau 3 sichtbare Objekte und 13 Einheiten.
- [ ] Portfolio-Soll beträgt 15.360,00 € für den laufenden Monat.
- [ ] Mieterwechsel Wohnung B zeigt Altpartei, Leerstandsmonat und aktuelle Partei korrekt.
- [ ] Einliegerwohnung erzeugt nach Mietende keine offene Mieterforderung.
- [ ] Einheitenakten zeigen Fläche, Zimmer, Nutzung, Ausstattung, Garage/Stellplatz und Vertragsart
  nur aus persistierten Stammdaten; Kaltmiete je Quadratmeter stammt aus der Backend-Projektion.
- [ ] Die letzte Mietänderung erscheint ausschließlich als dokumentiertes historisches Faktum; keine
  Einheit zeigt „Mieterhöhung möglich“ oder einen rechtlich bewerteten Folgetermin.
- [ ] Anna, Fatma, Eva, Jonas, Maria, Sophie und Rheinblick Design zeigen die vorgesehenen
  unterschiedlichen Portal-, Nachrichten- und Dokumentzustände.
- [ ] Mehrere Portalpersonen eines Mietverhältnisses bleiben getrennte Berechtigungen; erneuter
  Einladungsversand erzeugt kein Duplikat.
- [ ] Ohne echte Nachrichten-/Storage-/Versandintegration bleiben die betreffenden Aktionen sichtbar
  ehrlich inaktiv und erzeugen keinen Schein-Request.
- [ ] Zahlungsseite enthält ungefähr 120–150 mehrmonatige Umsätze.
- [ ] Alle, Prüfen, Nicht zugeordnet, Zugeordnet, Teilweise und Ignoriert sind befüllt.
- [ ] Jonas zeigt 600,00 € Zahlung und 500,00 € Rest.
- [ ] Maria zeigt 100,00 € ungeklärte Überzahlung und lässt sich ausdrücklich als Guthaben bestätigen.
- [ ] Sophie zeigt 1.320,00 € offene Forderung ohne erfundenen Bankumsatz.
- [ ] Annas Nachzahlung zeigt nach 120,00 € Barzahlung noch 125,00 € offen.
- [ ] Eva-Bestätigung aktualisiert Liste, Journal und Dashboard konsistent.
- [ ] PayPal-Umsatz lässt sich ignorieren und wieder aktivieren, ohne die Bankzeile zu verändern.
- [ ] Dashboard-Cashflow stammt aus den gesäten Zahlungsereignissen, nicht aus Prozent-Mocks.
- [ ] Musterstraße-PDF und bestehende Golden-Zahlen bleiben unverändert reproduzierbar.
- [ ] Lindenweg-Entwurf zeigt einen echten Readiness-Hinweis.
- [ ] Consent „läuft bald ab“ erscheint nur beim Konto Hafenallee.
- [ ] Typprüfung, Full-Gate und nicht-destruktiver Demo-Gate sind grün.

---

## 14. Noch nicht vorführen

- echte finAPI-Anmeldung oder Bankzugang;
- automatisches Mahnschreiben, Verzugszins oder Gebührenberechnung;
- automatische Guthabenverrechnung oder Auszahlung;
- produktive OCR-, Foto-, E-Mail- oder Funkintegration;
- echter Dokumentversand an Mieter;
- vollständiges Mieterportal und Vertragsgenerator;
- rechtliche Bewertung, Empfehlung oder Terminberechnung für eine Mieterhöhung;
- Steuer- oder Rechtsberatungsaussagen.

Diese Grenzen schwächen die Demo nicht: Sie trennt bereits funktionierende Fach- und Datenflüsse
ehrlich von Provider- und Zukunftsintegrationen.
