---
spec_id: 06-zahlungen
titel: Zahlungen — Umsatzliste, Bankanbindung, Zuordnung, Bar- und Teilzahlungen
status: freigegeben
prioritaet: hoch
betrifft: apps/web, apps/api, packages/db, packages/matching-engine, packages/adapters
abhaengig_von: [00-layout-global, 01-dashboard, 02-objekte, 05-abrechnung-erstellen]
repo_stand: Lokara-main @ 2026-08-25
---

## Zweck

Die heutige Seite „Zahlungen“ wird von zwei textlastigen Bereichen („Zuordnung prüfen“ und
„Zahlungsjournal“) zu einer kompakten, filterbaren Umsatzarbeitsfläche umgebaut. Alle Bankumsätze,
manuell erfassten Bankzahlungen und Barzahlungen erscheinen in einer gemeinsamen Liste. Zuordnung,
Ignorieren, Teilzahlung, Überzahlung und Guthaben werden in einer rechten Detail-Sidebar bearbeitet.

Die bestehende Matching-Engine, Forderungslogik und das unveränderliche Zahlungsjournal bleiben die
fachliche Grundlage. finAPI ist vor Launch vorgesehen, im aktuellen Stand aber nur gestubbt. Für die
Demo werden deshalb reproduzierbare, persistierte Demo-Daten durch dieselben Backend-Verträge und
Engines geführt — keine erfundenen Zahlungsbeträge oder Statusberechnungen im Frontend.

## Invarianten

- Pre-Pitch gilt Desktop/Laptop bei 1280, 1440 und 1920 Pixel sowie 200-Prozent-Zoom. Smartphone-,
  Tablet- und native Varianten sind Post-Pitch; Tastatur, Screenreader und sichtbarer Fokus bleiben
  verpflichtend.

- Ausschließlich das aktuelle Designsystem aus `00_Layout-Global.md` verwenden: vorhandene Tokens
  `ink`, `green`, `forest`, `mint`, `slate`, `paper`, `danger`, `warning`, `success` sowie
  `font-display` und `font-sans`. Keine rohe Farbangabe und keine neue Schrift erfinden.
- Portfolio-Standardmodell: Die Seite zeigt standardmäßig alle Konten und Objekte des Accounts. Ein
  Konto-, Objekt- oder Statusfilter ist ein lokaler Listenfilter, kein globaler App-Filter.
- Alle Beträge sind ganzzahlige Cent-Werte. Keine Geldrechnung mit `float` und keine fachliche
  Berechnung im Frontend.
- Forderung, offener Betrag, Verrechnung, Restbetrag, Guthaben, Teilzahlungsstatus, Matching-Ergebnis,
  Abweichung und Kontrollsummen kommen ausschließlich aus Backend beziehungsweise Engines.
- Das Frontend darf weder Beträge noch Statuswerte aus Mietsoll, Prozentfaktoren oder historischen
  Durchschnittswerten erfinden.
- Banktransaktionen, Matching-Vorschläge, Entscheidungen, Journalbuchungen und Korrekturen bleiben
  unveränderliche Nachweise. Korrekturen erfolgen durch neue Ereignisse, niemals durch Überschreiben
  oder Hard-Delete.
- „Ignorieren“ löscht und verändert keinen Bankumsatz. Es ist eine getrennte, nachvollziehbare und
  durch ein neues Ereignis aufhebbare Klassifizierung.
- Eine Matching-Punktzahl ist nur technische Entscheidungshilfe. Sie darf weder als Rechtsbewertung
  noch als Beweis einer Zuordnung dargestellt werden.
- Eine historische Abweichung ist nur ein Prüfhinweis. Sie darf niemals selbständig Geld buchen,
  eine Forderung verändern oder eine Mahnung auslösen.
- Dashboard und Reminder-System konsumieren dieselben serverseitigen Forderungs- und
  Zahlungsprojektionen. Keine zweite Zahlungswahrheit pro Seite.
- Reminder und Mahnwesen erhalten Zahlungsfakten, entscheiden aber selbst über Verzug, Mahnstufe,
  Frist, Zinsen, Gebühren und Kommunikation.
- Rechtliche oder geldrelevante `⚠️ MUSS-INPUT`-Punkte nie raten. Nur den betroffenen Teil überspringen
  und in `## Build-Notes` dokumentieren; den übrigen Spec weiter umsetzen.
- Signal nie allein über Farbe vermitteln. Jeder Zustand braucht Text und, wo passend, zusätzlich
  Form oder Icon.
- Alle account-bezogenen Zeilen bleiben durch App-Logik, account-erhaltende Fremdschlüssel und RLS
  isoliert. Jede neue Route ist owner-gescopet wie die bestehenden Zahlungsrouten.
- Bestehende Tests bleiben grün; Geld-, Unveränderlichkeits-, RLS-, Contract-, Tastatur- und
  Desktop-/Laptop-Fälle werden für die neuen Pfade ergänzt. Smartphone-/Tablet-Varianten sind
  Post-Pitch.

## Befehle

### [P1] Zahlungsseite auf eine gemeinsame Umsatzarbeitsfläche umstellen

- **Datei/Ort:** `apps/web/src/features/zahlungen/zahlungen-page.tsx` sowie die unmittelbar zugehörigen
  Präsentationskomponenten unter `apps/web/src/features/zahlungen/`.
- **Fundstelle:** Der aktuelle Seitenkopf „Zahlungen“, der Abschnitt „Zuordnung prüfen“, der lange
  Warnhinweis zur Matching-Bewertung, der Abschnitt „Zahlungsjournal“ und der Fußtext zur Verrechnung.
- **Ist:** Matching-Vorschläge und Journal werden als zwei große, textlastige Abschnitte untereinander
  gezeigt. Importierte Transaktionen ohne Proposal sind in dieser Darstellung unsichtbar. Die Seite
  bietet keine zentrale Umsatzliste.
- **Soll:** Beide Hauptabschnitte durch eine gemeinsame Umsatzarbeitsfläche ersetzen: kurzer Seitenkopf,
  Kontostatus, Filterleiste und eine Liste aller sichtbaren Umsätze. Matching- und Journalinformationen
  werden in Status, Zeilendetails und Historie integriert.
- **Default:** Untertitel „Bankumsätze prüfen und Zahlungen zuordnen.“ Rechts im Kopf die primäre Aktion
  „Zahlung erfassen“. Die bisherige lange Matching-Warnung nicht dauerhaft oberhalb der Liste zeigen;
  eine kurze Einordnung steht dort, wo die technische Bewertung aufgeklappt wird.
- **Erwartetes Ergebnis:** Nach dem Seitenkopf beginnt unmittelbar die Arbeitsfläche. Kein eigener
  Block „Zuordnung prüfen“ und kein eigener, dauerhaft sichtbarer Block „Zahlungsjournal“. Gebuchte,
  ungeklärte, ignorierte und manuell erfasste Vorgänge sind verschiedene Zustände derselben Liste.
- **Akzeptanz:** Im Standardzustand existiert genau eine sichtbare Umsatzliste. Die Überschriften
  „Zuordnung prüfen“ und „Zahlungsjournal“ strukturieren die Seite nicht mehr als getrennte Listen.
- **Nicht tun:** Matching-Nachweise oder Journalhistorie löschen; sie werden nur in die Details
  verlagert. Keine fachlichen Hinweise ersatzlos entfernen, wenn sie für eine Entscheidung nötig sind.

### [P2] Bankkonten, Synchronisation und Einwilligungsstatus nutzbar ausliefern

- **Datei/Ort:** Bankkonto-Modelle und Adapter bleiben Grundlage; neue beziehungsweise erweiterte
  owner-gescopete Leseverträge in `apps/api`, Spiegelverträge in `apps/web/src/lib/contracts.ts` und
  Abfrage-Hooks unter `apps/web/src/features/zahlungen/queries.ts`.
- **Fundstelle:** `BankAccount` mit `provider`, `provider_account_id`, `normalized_iban`, `display_name`
  und `consent_expires_at`; bestehender Importweg `/bank-accounts/{id}/transactions/import` und die
  Jobs für Sync und Einwilligungsprüfung.
- **Ist:** Das Datenmodell kennt verbundene Konten und Einwilligungsablauf. Die Zahlungsseite kann aber
  weder Konten auflisten noch letzten Abruf, Synchronisationszustand oder Reautorisierungsbedarf zeigen.
- **Soll:** Einen accountweiten Bankkonto-Lesevertrag bereitstellen. Pro Konto mindestens ID,
  Anzeigename, maskierte IBAN, Provideranzeige, Einwilligungsstatus, Ablaufzeit, Zeitpunkt und Ergebnis
  des letzten Abrufs sowie laufenden Synchronisationsstatus liefern. Eine manuelle Aktualisierung nutzt
  den bestehenden serverseitigen Import-/Jobpfad.
- **Default:** Lokaler Kontofilter „Alle Konten“; bei einem Konto ist es direkt ausgewählt. IBAN nur mit
  den letzten vier Zeichen sichtbar. Status: „Aktiv“, „Läuft bald ab“, „Erneut verbinden“, „Wird
  aktualisiert“ oder „Abruf fehlgeschlagen“. „Bald“ ist ein reiner UI-Hinweis 14 Tage vor dem vom
  Backend gelieferten Ablaufdatum.
- **Erwartetes Ergebnis:** Oberhalb der Filter sieht der Nutzer, welche Konten Daten liefern, wann der
  letzte Abruf lief und ob eine erneute Verbindung nötig ist. Ein fehlendes oder abgelaufenes Consent
  erzeugt keine vermeintlich aktuelle Umsatzliste.
- **Akzeptanz:** Die Seite zeigt echte Bankkonto- und Einwilligungsdaten; ein abgelaufenes Consent
  verhindert den Abruf und bietet „Konto erneut verbinden“ statt eines technischen Fehlers.
- **Nicht tun:** OAuth-, Redirect-, Credential- oder Providerwerte erfinden. Keine vollständige IBAN
  unnötig anzeigen. Bereits importierte Nachweise bei Consent-Ablauf nicht löschen.
- **⚠️ MUSS-INPUT:** Produktive finAPI-Vertragsdaten, OAuth-/Redirect-Konfiguration, freigegebene
  Kontotypen und endgültige Reautorisierungsstrecke.

### [P3] Vereinigten serverseitigen Umsatzlistenvertrag schaffen

- **Datei/Ort:** Owner-API unter `/a/{account_id}`, Zahlungsservice, Frontend-Vertrag und Query-Hook.
- **Fundstelle:** Die getrennten Endpoints `/bank-transactions`, `/match-proposals`, `/receivables` und
  `/payment-ledger` sowie der clientseitige Join in `proposal-view.ts`.
- **Ist:** Das Frontend lädt vier unpaginierte Listen und verbindet sie anhand von IDs. Nur Umsätze mit
  Proposal werden zu sichtbaren Review-Zeilen. Bankdaten, Zuordnung, Status und Historie können
  auseinanderlaufen oder unvollständig geladen werden.
- **Soll:** Einen serverseitigen, paginierten Read-Model-Vertrag für die Umsatzliste bereitstellen. Eine
  Zeile enthält Bank- beziehungsweise manuelle Quelle, Kontoreferenz, Betrag, Richtung, Buchungs- und
  Wertstellungsdatum, Gegenpartei, Zweck, Zuordnungsstatus, Ignorierstatus, Abweichung, verknüpfte
  Miet-/Forderungszusammenfassung und verfügbare Aktionen. Kontrollsummen und Status werden serverseitig
  gebildet.
- **Default:** Cursor-Pagination mit 50 Zeilen pro Seite; Sortierung Buchungsdatum absteigend, danach
  stabile ID absteigend. Filter und Suche laufen serverseitig. Alle gespeicherten Banktransaktionen
  erscheinen, auch wenn noch kein Matching-Lauf existiert.
- **Erwartetes Ergebnis:** Das Frontend rendert einen autoritativen Listeneintrag je Umsatz und muss
  keine Geld- oder Statuslogik über vier Payloads rekonstruieren.
- **Akzeptanz:** Ein importierter Umsatz ohne Proposal ist unter „Alle“ und „Nicht zugeordnet“ sichtbar.
  51 Umsätze werden paginiert. Die Reihenfolge ist stabil und neueste zuerst.
- **Nicht tun:** Die bestehenden fachlichen Tabellen zu einer veränderlichen UI-Tabelle verschmelzen;
  der Vertrag ist ein Read Model. Keine RLS- oder Owner-Grenzen abschwächen.

### [P4] Filterleiste, Suche und Statuszähler ergänzen

- **Datei/Ort:** Zahlungsarbeitsfläche im Frontend; Filterparameter und Zähler im Read-Model-Endpoint.
- **Fundstelle:** Oberhalb der neuen Umsatzliste.
- **Ist:** Keine Suche, Zeitraumwahl oder Statusfilter vorhanden.
- **Soll:** Eine kompakte Filterleiste für dieselbe Liste bauen. Statusansichten: „Alle“, „Nicht
  zugeordnet“, „Prüfen“, „Zugeordnet“, „Teilweise“ und „Ignoriert“. Zähler kommen aus dem Backend und
  entsprechen den aktiven Konto-/Zeitraumfiltern.
- **Default:** Standard „Alle“, letzte 90 Tage, alle Konten, neueste zuerst. Zusätzlich Suche über
  Gegenpartei und Verwendungszweck, Zeitraum, Einnahmen/Ausgaben sowie optional Objekt/Mietverhältnis.
  „Filter zurücksetzen“ erscheint erst bei einer Abweichung vom Default.
- **Erwartetes Ergebnis:** „Nicht zugeordnet · 3“ weist auf Arbeit hin, ohne eine zweite Prüfliste zu
  erzeugen. Wechseln des Filters ersetzt nur den Listeninhalt und erhält den Seitenkontext.
- **Akzeptanz:** Jeder Statusfilter liefert nur passende Zeilen und einen serverseitig korrekten Zähler.
  Suche und Zeitraum sind per Tastatur bedienbar und erzeugen keinen horizontalen Seitenscroll.
- **Nicht tun:** Filterzahlen im Frontend aus der aktuell geladenen Seite zählen. Keinen globalen
  Objektfilter in App-Shell oder Seitenkopf einführen.

### [P5] Kompakte Desktop-/Laptop-Umsatzzeile bauen

- **Datei/Ort:** Neue Listen-/Tabellenkomponente unter `apps/web/src/features/zahlungen/`.
- **Fundstelle:** Die heutigen großen `ProposalCard`-Karten und die Journal-Tabelle.
- **Ist:** Ein Vorschlag belegt eine große Karte mit Erklärung und Punktchips; Bank- und Journalzeilen
  sind getrennt.
- **Soll:** Desktop und Laptop als ruhige Tabelle rendern. Je Zeile Auswahl,
  Datum/Zweck, Gegenpartei, Konto, Zuordnungszusammenfassung, Status, Betrag und Aktionen
  „Ignorieren“/„Zuordnen“ beziehungsweise passende Folgeaktionen zeigen.
- **Default:** Desktopspalten: Auswahl, Buchung, Gegenpartei, Zuordnung, Status, Betrag, Aktion. Positive
  und negative Beträge rechtsbündig mit tabellarischen Ziffern; Richtung zusätzlich textlich oder per
  Vorzeichen. Zeilenhöhe kompakt mit gut erkennbaren Klickzielen. Klick auf die
  Zeile öffnet Details; interaktive Unterelemente lösen nicht zusätzlich den Zeilenklick aus.
- **Erwartetes Ergebnis:** Viele Umsätze sind schnell scanbar. „Mieter · Einheit · Miete März 2026“ ist
  verständlicher als eine interne Forderungs-ID. Fehlende Auflösung wird ehrlich als „Nicht
  zugeordnet“ gezeigt.
- **Akzeptanz:** Bei 1280, 1440 und 1920 Pixel sind mindestens zehn typische Zeilen ohne Kartenflut
  erfassbar. Fokus und Hover sind sichtbar; die Gesamtseite scrollt nicht horizontal.
- **Nicht tun:** Interne IDs, rohe Enumwerte oder Matching-Punktwerte in der Standardzeile zeigen.
  Status nicht allein über Grün/Rot ausdrücken.

### [P6] Rechte Buchungsdetail-Sidebar integrieren

- **Datei/Ort:** Neue Detail-Sidebar/Drawer-Komponente in `apps/web/src/features/zahlungen/` für
  Desktop und Laptop.
- **Fundstelle:** Aktion „Zuordnen“ und Klick auf eine Umsatzzeile.
- **Ist:** Entscheidungen finden innerhalb großer Karten statt; es gibt keine persistente Listenansicht
  neben den Details.
- **Soll:** Details rechts einblenden, ohne Listenfilter, Scrollposition oder Auswahl zu verlieren.
  Oben echte Buchungsdaten, darunter serverseitig erlaubte Handlungen und zuletzt eingeklappte
  Matching-/Journalhistorie.
- **Default:** Desktopbreite 400 Pixel, bei 1280 Pixel höchstens 40 % des Viewports. Schließen per
  Schaltfläche, Escape und nach Fokus-Rückgabe auf die auslösende Zeile. Inhalte:
  Gegenpartei, Betrag, Richtung, Buchungs-/Wertstellungsdatum, Zweck, Gegenkonto-IBAN sofern vorhanden,
  eigenes Konto, Status, Zuordnung und Ereignishistorie.
- **Erwartetes Ergebnis:** Der Nutzer kann Umsätze nacheinander prüfen, ohne zwischen Seiten oder
  getrennten Listen zu springen. Die technischen Matching-Signale liegen unter „Warum dieser
  Vorschlag?“ standardmäßig eingeklappt.
- **Akzeptanz:** Öffnen und Schließen erhalten Filter und Scrollposition. Tastaturfokus ist im offenen
  Drawer geführt und kehrt danach zur richtigen Zeile zurück.
- **Nicht tun:** Keine vollständige Bankkennung unnötig offenlegen. Keine Clientberechnung in der
  Sidebar. Keine neue Dialog-/Drawer-Dependency, wenn die vorhandenen UI-Bausteine genügen.

### [P7] Ignorieren als nachvollziehbare, aufhebbare Klassifizierung umsetzen

- **Datei/Ort:** Neues account-gescopetes Klassifizierungs-/Ereignismodell, Owner-API, Listenvertrag und
  Sidebar/Zeilenaktion.
- **Fundstelle:** Checkbox beziehungsweise Aktion „Ignorieren“ an nicht relevanten Umsätzen und der
  Filter „Ignoriert“.
- **Ist:** Es gibt `rejected` und `duplicate` für Matching-Vorschläge, aber keinen allgemeinen
  Ignorierstatus für einen Bankumsatz.
- **Soll:** Ignorieren als separates Ereignis mit Umsatz, Akteur, Zeitpunkt und optionalem Grund
  speichern. Aufheben erzeugt ein neues Ereignis und stellt den Umsatz wieder zur Prüfung, ohne das
  frühere Ereignis zu überschreiben.
- **Default:** Gründe: „Privat / nicht relevant“, „Interne Umbuchung“, „Bereits anderweitig erfasst“ und
  „Sonstiger Grund“. Bei Einzelaktion optional auswählbar; bei Sammelaktion ohne Pflichtgrund zulässig.
  Ignorierte Umsätze wirken nicht auf Forderung, Dashboard-Zahlungs-KPIs, Abrechnung oder Reminder.
- **Erwartetes Ergebnis:** Die Zeile wechselt nach Bestätigung in „Ignoriert“. In der Historie steht,
  wer wann ignoriert beziehungsweise wieder aktiviert hat.
- **Akzeptanz:** „Ignorieren“ verändert keine `bank_transaction` und löscht keine Zeile. „Ignorieren
  aufheben“ macht den Vorgang wieder bearbeitbar und erhält beide Historienereignisse.
- **Nicht tun:** Einen bereits verbuchten Zahlungsnachweis direkt ignorierbar machen. Keine automatische
  Absenderregel in diesem Spec. `rejected`, `duplicate` und `ignored` nicht zu einem Status vermischen.

### [P8] Manuelle Zuordnung mit serverseitiger Vorschau ermöglichen

- **Datei/Ort:** Matching-/Zahlungsservice, pure Settlement-Grenze, neuer Preview- und Confirm-Endpoint,
  Sidebar und Verträge.
- **Fundstelle:** Bestehende Entscheidung bestätigt ausschließlich den Rang-1-Kandidaten; ein
  `UNMATCHED`- oder abgelehnter Umsatz kann nicht frei einer Forderung zugeordnet werden.
- **Ist:** Keine manuelle Auswahl von Mieter, Mietverhältnis oder Forderung. Das Frontend darf keinen
  alternativen `receivable_id` senden.
- **Soll:** Einen ausdrücklich manuellen Zuordnungsweg ergänzen. Nutzer wählt Mietverhältnis und offene
  Forderung beziehungsweise „nach offenen Forderungen verteilen“. Vor Bestätigung liefert das Backend
  eine vollständige Verrechnungsvorschau mit vorher/nachher, Komponenten, Rest und Guthaben. Bestätigung
  schreibt unveränderliche manuelle Entscheidung und Journalbuchung.
- **Default:** Auswahlreihenfolge Objekt → Einheit/Mietverhältnis → offene Forderung. Nur accountgleiche,
  fachlich offene Forderungen anbieten. Der Nutzer kann keine Cent-Aufteilung frei eintippen; er wählt
  Ziel oder Verteilungsmodus, die Engine berechnet.
- **Erwartetes Ergebnis:** Ein zuvor nicht zuordenbarer Eingang kann kontrolliert einer realen offenen
  Forderung zugeordnet werden. Eine abweichende Vorschau muss erneut bestätigt werden.
- **Akzeptanz:** Cross-account- und fremde-Mieter-Zuordnungen werden server- und DB-seitig abgelehnt.
  Vorschau und finale Buchung stimmen centgenau überein oder die Bestätigung wird wegen zwischenzeitlich
  geänderter Projektion mit Konflikt abgelehnt.
- **Nicht tun:** Bestehende unveränderliche Proposal- oder Confirmation-Zeilen umschreiben. Keine
  Saldenberechnung im Frontend. Keine Zuordnung an eine bereits vollständig ausgeglichene Forderung ohne
  explizite Guthabenbehandlung.
- **⚠️ MUSS-INPUT:** Ob eine endgültig abgelehnte Zuordnung später durch eine neue manuelle Zuordnung
  ergänzt werden darf und wie dieser fachliche Unterschied benannt wird.

### [P9] Abweichungen vom Soll und historischen Zahlungsstrom serverseitig erkennen

- **Datei/Ort:** Pure Engine oder klar abgegrenzter Domain-Service für Zahlungsabweichungen,
  persistierbare Ergebnisfelder/Read Model, Tests und Darstellung in Liste/Sidebar.
- **Fundstelle:** Bankumsatz, offene Forderungen, bisherige bestätigte Zahlungen desselben
  Mietverhältnisses und Matching-Signale.
- **Ist:** Die Engine erkennt exakte Beträge und Matching-Signale, liefert aber keinen eigenständigen,
  nutzerfreundlichen Abweichungshinweis zum üblichen Zahlungsstrom.
- **Soll:** Zwei Ergebnisarten strikt trennen: fachliche Sollabweichung gegen konkrete offene
  Forderungen und historische Auffälligkeit gegen bestätigte frühere Zahlungen. Ergebnis enthält Code,
  deutsche serverseitige Kurzbegründung, Referenzwerte und Schwere als Arbeitspriorität — keine
  Rechtsbewertung.
- **Default:** Startsignale: Über-/Unterzahlung, Zahlung nach vollständigem Ausgleich, ungewohnter
  Absender/IBAN, ungewöhnlicher Zeitraum, mögliche Dublette, Rücklastschrift und deutliche Abweichung
  von wiederkehrenden bestätigten Monatszahlungen. Historischer Vergleich erst bei mindestens drei
  bestätigten vergleichbaren Zahlungen; andernfalls kein Muster behaupten.
- **Erwartetes Ergebnis:** Die Liste zeigt beispielsweise „100,00 € über offenem Betrag“ oder
  „Ungewöhnlicher Betrag — bitte prüfen“. Details erklären die belastbare Grundlage, ohne einen
  künstlichen Risikoscore anzuzeigen.
- **Akzeptanz:** Jede Abweichung ist aus gespeicherten Eingaben reproduzierbar und golden getestet. Ein
  Hinweis allein verändert niemals Forderung, Guthaben, Matching oder Reminder.
- **Nicht tun:** Keine KI-/ML-Klassifikation, keine Frontend-Durchschnittsrechnung und keine
  automatische Buchung aus einer historischen Auffälligkeit.

### [P10] Teilzahlungen, Überzahlungen und Guthaben kontrolliert darstellen und buchen

- **Datei/Ort:** Bestehende Settlement-Engine und Ledger bleiben Grundlage; Preview-/Confirm-Verträge,
  Listenstatus, Sidebar und Journaldetails erweitern.
- **Fundstelle:** Enginepfade für `partial`, Überzahlung und `credit_cents`; aktuelle Journalanzeige
  „Guthaben (keine Auszahlung)“.
- **Ist:** Teil- und Überzahlungen sind fachlich teilweise implementiert, aber ohne klaren
  Nutzerkontrollfluss. Guthaben wird aufgezeichnet, jedoch nicht ausgezahlt oder später verrechnet.
- **Soll:** Vorschau zeigt Zahlungsbetrag, verrechneten Betrag, offene Beträge vorher/nachher und
  verbleibende Abweichung. Bei Überzahlung entscheidet der Nutzer ausdrücklich zwischen weiterer
  offener Forderung, Guthabenbuchung, anderer Zuordnung oder „vorerst ungeklärt“. Bei Teilzahlung wird
  der verbleibende offene Betrag sichtbar.
- **Default:** Überzahlung niemals allein aufgrund einer historischen Auffälligkeit automatisch als
  Guthaben buchen. Bestätigtes Guthaben erscheint als „Zugeordnet · X,XX € Guthaben“. Teilzahlung zeigt
  „X,XX € von Y,YY € bezahlt“ und „Z,ZZ € offen“. Beträge kommen aus Preview/Engine.
- **Erwartetes Ergebnis:** Eine Zahlung von 1.000,00 € auf 900,00 € offen zeigt 900,00 € Verrechnung und
  100,00 € Rest. Erst die explizite Guthabenbestätigung schreibt `credit_cents`. Eine Zahlung von
  600,00 € auf 900,00 € setzt die Forderung auf „Teilweise“ und lässt 300,00 € offen.
- **Akzeptanz:** Zahlung = Summe der Allokationen + Guthaben, centgenau. Dashboard, Forderung,
  Zahlungsseite und Reminder sehen denselben verbleibenden Saldo.
- **Nicht tun:** Guthaben automatisch mit einer später entstehenden Forderung verrechnen oder als
  Auszahlung darstellen. Keine abweichende Rundung im Frontend.
- **⚠️ MUSS-INPUT:** Spätere Nutzung von Mieterguthaben: Auszahlung, manuelle Verrechnung oder
  automatische Verrechnung; außerdem Regeln für gemeinsame Mietverhältnisse/Gesamtschuldner.

### [P11] Barzahlungen und manuelle Bankzahlungen unveränderlich erfassen

- **Datei/Ort:** Neues Zahlungsquellen-/manuelles Zahlungsevent im Datenmodell, Owner-API, Service und
  Wizard aus der Aktion „Zahlung erfassen“.
- **Fundstelle:** Seitenkopf der neuen Arbeitsfläche; bestehendes Journal akzeptiert heute nur
  Banktransaktionen als Zahlungsquelle.
- **Ist:** Barzahlungen und außerhalb der Bankanbindung bekannte Zahlungen können nicht im zentralen
  Zahlungsfluss erfasst werden.
- **Soll:** Einstufigen beziehungsweise kurzen mehrstufigen Wizard anbieten. Zahlungsart „Barzahlung“
  oder „Bankzahlung manuell nachtragen“, Datum, Betrag, Mietverhältnis, Forderung/Verteilungsmodus,
  Notiz und optionaler Nachweis. Vor Speicherung dieselbe serverseitige Verrechnungsvorschau wie [P8]
  zeigen. Nach Bestätigung unveränderliches Zahlungsevent und Journalbuchung erzeugen.
- **Default:** Barzahlung erscheint in derselben Umsatzliste mit Quelle „Barzahlung“. Erfasst am und
  Zahlungsdatum getrennt speichern. Kein vorgetäuschtes Bankkonto und keine erfundene Provider-ID.
  Optionaler Nachweis bleibt ohne echten Storage als klar inaktiver späterer Schritt.
- **Erwartetes Ergebnis:** Bar- und Bankzahlungen reduzieren dieselben Forderungen, erzeugen dieselben
  Teilzahlungs-/Guthabenstatus und sind auf Dashboard sowie Reminder sichtbar.
- **Akzeptanz:** Akteur, Erfassungszeitpunkt, Zahlungsdatum, Betrag, Quelle und Allokationen sind
  nachvollziehbar. Eine Korrektur erzeugt ein kompensierendes Ereignis, kein Edit oder Delete.
- **Nicht tun:** Keine Quittung oder Datei als gespeichert darstellen, solange kein Storage existiert.
  Keine Barzahlung als finAPI-Umsatz tarnen.
- **⚠️ MUSS-INPUT:** Rechtlich und produktseitig freigegebener Quittungs-/Nachweisprozess für
  Barzahlungen.

### [P12] Sichere Mehrfachauswahl und Sammelaktionen ergänzen

- **Datei/Ort:** Umsatzliste und Ignorier-API.
- **Fundstelle:** Auswahl-Checkbox je Zeile und Checkbox im Tabellenkopf.
- **Ist:** Keine Mehrfachauswahl.
- **Soll:** Mehrere sichtbare Umsätze auswählen und ausschließlich sichere, homogene Sammelaktionen
  anbieten.
- **Default:** Im ersten Scope nur „Ignorieren“ und „Ignorieren aufheben“. Tabellenkopf wählt nur die
  aktuell sichtbare Seite; Text nennt die Anzahl. Nach Erfolg klare Bestätigung und Auswahl leeren.
- **Erwartetes Ergebnis:** Viele private Ausgaben können effizient ignoriert werden, ohne jede Sidebar
  einzeln zu öffnen.
- **Akzeptanz:** Gemischte Auswahl aus ignorierten und aktiven Umsätzen bietet keine widersprüchliche
  Aktion. Teilfehler werden je Umsatz ausgewiesen und erfolgreiche Ereignisse nicht zurückgerollt, sofern
  der Endpoint keine atomare Gesamtaktion verspricht.
- **Nicht tun:** Keine Sammelzuordnung zu Forderungen und keine Sammel-Guthabenbuchung. Keine Auswahl
  über ungeladene Seiten stillschweigend annehmen.

### [P13] Regelmäßige Mietforderungen backendseitig erzeugen

- **Datei/Ort:** Reiner Forderungserzeugungs-/Schedule-Pfad, Jobs, Datenmodell, API und Golden Tests;
  Mietverhältnisse und zeitliche Vorauszahlungspläne dienen als Inputs.
- **Fundstelle:** `Receivable` unterstützt `rent`, aber im produktiven Pfad wurde nur die Erzeugung von
  `nk_nachzahlung` aus finalisierten Abrechnungen gefunden.
- **Ist:** Ohne regelmäßig erzeugte Mietforderungen kann das System Zahlungseingänge nicht vollständig
  gegen Kaltmiete, NK-/Heizkostenvorauszahlung und weitere Bestandteile prüfen.
- **Soll:** Für relevante Mietperioden idempotent genau eine fachliche Forderung je Mietverhältnis und
  Periode erzeugen. Nominale Komponenten und Fälligkeit stammen aus versionierten Vertrags-/Schedule-
  Daten. Mieterwechsel, Zukunft, Ende des Mietverhältnisses und Leerstand werden zeitlich korrekt
  berücksichtigt.
- **Default:** Keine Forderung für Leerstand oder Eigennutzung erfinden. Eine Forderung trägt die
  Komponenten Kaltmiete, NK-Vorauszahlung, Heizkostenvorauszahlung und Garage nur, wenn sie in den
  autoritativen Vertragsdaten vorhanden sind. Wiederholter Joblauf erzeugt kein Duplikat.
- **Erwartetes Ergebnis:** Jeder Zahlungseingang kann gegen konkrete periodische Sollwerte geprüft
  werden. Objekt, Einheit und Mietverhältnis sind auflösbar.
- **Akzeptanz:** Golden Tests decken Vollzahlung, Teilzahlung, Mieterwechsel, beendetes Mietverhältnis,
  mehrere Mietparteien, Leerstand und wiederholten Joblauf ab. Kontrollsummen der Komponenten stimmen.
- **Nicht tun:** Fälligkeit, Warmmiete, Bestandteile oder gemeinsame Haftung aus UI-Feldern ableiten.
- **⚠️ MUSS-INPUT:** Verbindliche Forderungs- und Fälligkeitsregeln aus Vertrag/Produkt für Miete sowie
  Behandlung gemeinsamer Mietverhältnisse. Bis zur Klärung diesen Block nicht produktiv aktivieren.

### [P14] Abrechnungssalden und Vorauszahlungen an denselben Zahlungsfluss binden

- **Datei/Ort:** Bestehender Statement-Handoff in `apps/api`, Abrechnungs-Readiness aus
  `05_Abrechnung-erstellen.md`, Zahlungsliste und gemeinsame Projektionen.
- **Fundstelle:** `/statements/{statement_id}/receivables`, Kategorie `nk_nachzahlung`, Ledger-Komponente
  `nk_advance_cents` und die manuelle Vorauszahlungserfassung in der heutigen Abrechnungsansicht.
- **Ist:** Positive finalisierte Salden können Forderungen erzeugen. Bestätigte Vorauszahlungen leben
  teilweise in einem separaten Abrechnungsfluss; Guthaben aus Abrechnungen sind keine Forderung und
  werden nicht ausgezahlt.
- **Soll:** Tatsächlich verbuchte Vorauszahlungs-Komponenten aus dem Zahlungsjournal als autoritative
  Quelle für die Abrechnung bereitstellen. Nachzahlungen erscheinen als offene Forderungen in der
  Zahlungsseite. Abrechnungsguthaben erscheinen als Verpflichtung/Saldo, aber nicht als fingierter
  negativer Mietumsatz.
- **Default:** Der finalisierte Centbetrag wird kopiert, niemals im Frontend oder Übergabeweg neu
  berechnet. Bestehende manuelle Vorauszahlungseinträge bleiben als klar gekennzeichnete manuelle
  Quelle erhalten und dürfen nicht doppelt mit Journalzahlungen gezählt werden.
- **Erwartetes Ergebnis:** Abrechnung, Zahlungen und tatsächliche Vorauszahlungen besitzen eine
  konsistente, centgenaue Herkunftskette.
- **Akzeptanz:** Eine zugeordnete NK-Vorauszahlung verändert die Abrechnungsvorschau genau einmal. Eine
  Nachzahlung wird genau einmal als Forderung erzeugt. Korrekturabrechnungen erzeugen keine doppelte
  Periodenforderung.
- **Nicht tun:** Abrechnungssaldo oder Vorauszahlungen im Frontend rekonstruieren. Guthaben ohne
  freigegebenen Prozess automatisch auszahlen oder verrechnen.

### [P15] Persistiertes Demo-finAPI-Szenario ergänzen

- **Datei/Ort:** Demo-Seed unter `packages/db/src/lokara_db/seed.py`, gegebenenfalls vorhandener Stub-
  Adapter und zugehörige Demo-/Seed-Tests und Dokumentation.
- **Fundstelle:** Das bestehende Demo-Bankkonto „Mietkonto Musterstraße 12“ mit Provider `finapi-stub`,
  das aktuell keine Demo-Umsätze, Forderungen, Vorschläge oder Journalbuchungen mitbringt.
- **Ist:** Die Demo-Seite bleibt leer. `01_Dashboard.md` leitet Zahlungswerte prozentual aus dem echten
  Mietsoll ab, weil echte Zahlungsdaten fehlen.
- **Soll:** Reproduzierbare, persistierte Demo-Forderungen, Bankumsätze, Matching-Vorschläge,
  Entscheidungen und Journalereignisse anlegen. Daten durch dieselben Services/Engines führen, die
  später finAPI-Daten verarbeiten. Provider sichtbar als Demo kennzeichnen.
- **Default:** Mindestens: automatisch zugeordnete Vollzahlung, offener Matching-Vorschlag,
  nicht zugeordnete Zahlung, Teilzahlung, Überzahlung mit ausdrücklich bestätigtem Guthaben,
  Betriebskosten-Nachzahlung, mögliche Dublette, Rücklastschrift, ausgehender nicht matchbarer Umsatz,
  Barzahlung, Mieterwechsel sowie ein aktives und ein „bald erneut verbinden“-Kontoszenario. Beträge
  werden aus den dazu gesäten Forderungen abgeleitet, nicht frei im Frontend erfunden.
- **Erwartetes Ergebnis:** Die Demo zeigt sofort eine glaubwürdige finAPI-Zukunftsansicht, ohne zu
  behaupten, eine echte Bankverbindung sei aktiv. Filter, Sidebar, Teilzahlung und Guthaben lassen sich
  vorführen.
- **Akzeptanz:** Demo-Reset stellt exakt denselben Zustand wieder her. Jede sichtbare Summe lässt sich
  auf persistierte Forderung und Zahlung zurückführen. Kein Dashboard-/Frontend-Helfer erfindet diese
  Beträge.
- **Nicht tun:** Keine echten Bankdaten, Zugangsdaten oder persönliche IBANs verwenden. Keine zufälligen
  Laufzeitwerte. Demo-Provider nicht als produktiv verbundene finAPI-Session darstellen.

### [P16] Echte Zahlungsaggregate für Dashboard, Objekte und Reminder liefern

- **Datei/Ort:** Accountweite read-only Projektionen/Endpoints in `apps/api`; Konsumenten in Dashboard,
  Objekt-/Mietverhältnisdetail und späterem Reminder-System.
- **Fundstelle:** `01_Dashboard.md` [D3]/[D4] mit 82-%-/18-%-Demoableitung; heutiger
  `watch_deadlines`-Job mit überfälligen Forderungsfakten.
- **Ist:** Dashboard-Zahlungseingang und offene Posten sind Mock. Der Deadline-Job meldet Fakten, aber
  es gibt noch keinen gemeinsamen UI-Vertrag für Zahlungsstand und Mahnwesen.
- **Soll:** Account-, Objekt- und Mietverhältnisaggregate aus Forderungen und Journal liefern:
  Mietsoll, eingegangen, offen, teilweise, Guthaben, ungeklärte Umsätze und Rücklastschriften. Reminder
  erhält Forderungs-ID, Fälligkeit, offenen Saldo und relevante Zahlungsereignisse.
- **Default:** Dashboard „Mieteinnahmen“ und „Offene Posten“ nach erfolgreicher Zahlungsimplementierung
  auf diese echten Aggregate umstellen. Ungeklärter Bankumsatz ist nicht automatisch offene Miete;
  beide Kennzahlen getrennt führen. Mock-Fallback nur im klaren Demo-Modus und nie parallel als zweite
  Wahrheit.
- **Erwartetes Ergebnis:** Eine Teilzahlung aktualisiert Zahlungsliste, Dashboard, Objektakte und
  Reminder konsistent. Eine ignorierte private Ausgabe beeinflusst keine Kennzahl.
- **Akzeptanz:** Dieselbe Forderungs-ID und derselbe offene Centbetrag erscheinen in allen Konsumenten.
  Contract-Tests verhindern unterschiedliche Summen.
- **Nicht tun:** Mahnstufe, Verzug, Zinsen oder Gebühren in der Zahlungsprojektion berechnen. Keine
  offenen Mieten aus Anzahl ungeklärter Umsätze ableiten.
- **⚠️ MUSS-INPUT:** Rechtlich freigegebene Mahn-, Verzugs-, Zins-, Gebühren- und Eskalationslogik für
  den späteren Reminder-/Mahn-Spec.

### [P17] Lade-, Leer-, Fehler-, Erfolgs- und Berechtigungszustände vereinheitlichen

- **Datei/Ort:** Zahlungsseite, Kontoleiste, Filter, Liste, Sidebar und Wizard.
- **Fundstelle:** Heutige Skeletons und generische Texte „Bitte API und Datenbank prüfen“.
- **Ist:** Fehlertexte sprechen teilweise technisch; der leere Zustand unterscheidet nicht zwischen
  fehlendem Konto, fehlender Einwilligung, noch nicht synchronisiertem Konto und tatsächlich keinen
  Umsätzen.
- **Soll:** Zustände fachlich trennen und jeweils genau eine sinnvolle nächste Aktion anbieten.
- **Default:** Zustände: kein Konto → „Bankkonto verbinden“; Demo ohne Daten → „Demo-Zahlungen laden“;
  Consent fehlt/abgelaufen → „Konto erneut verbinden“; noch nie synchronisiert → „Umsätze abrufen“;
  Filter ohne Treffer → „Keine Umsätze für diese Filter“ + zurücksetzen; echte leere Historie →
  „Noch keine Umsätze“; Teilfehler → Liste erhalten und betroffene Aktion erneut anbieten. Erfolg als
  kurze Statusmeldung, nicht als dauerhaft große Karte.
- **Erwartetes Ergebnis:** Kein Nutzer sieht „Bitte API und Datenbank prüfen“. Ein Fehler löscht keine
  zuvor sichtbare Liste und keine Eingaben im Wizard.
- **Akzeptanz:** Jeder Zustand ist in UI-Tests abgedeckt. Screenreader erhalten Statusmeldungen über
  passende Live-Regionen; Ladezustände haben `aria-busy` und respektieren reduzierte Bewegung.
- **Nicht tun:** Keine technischen Stackbegriffe, rohen HTTP-Codes oder internen IDs im Nutzertext.

### [P18] Desktop-/Laptop-Nutzung, Tastatur und Fokus absichern

- **Datei/Ort:** Alle neuen Komponenten der Zahlungsseite und ihre UI-Tests.
- **Fundstelle:** Tabelle, Filterleiste, Sidebar, Auswahl-Checkboxen und Wizard.
- **Ist:** Bestehende Karten berücksichtigen Fokus nach Entscheidung, aber die neue Listen-/Drawer-
  Interaktion existiert noch nicht.
- **Soll:** Vollständige Tastaturbedienung, sichtbarer Fokus, semantische Tabelle, verständliche
  Checkbox-Labels und korrektes Drawer-Fokusmanagement für Desktop und Laptop umsetzen.
- **Default:** Escape schließt Sidebar; Fokus kehrt zur auslösenden Zeile zurück. Tabellenkopf bleibt
  bei langer Liste sichtbar, sofern ohne Überlagerung umsetzbar. Filter umbrechen beziehungsweise
  scrollen innerhalb ihrer eigenen Fläche; die Seite selbst scrollt im Standardzoom nie horizontal.
- **Erwartetes Ergebnis:** Die komplette Prüfung und Zuordnung ist ohne Maus möglich. Bei 200 % Zoom
  bleiben Inhalte lesbar und Aktionen erreichbar.
- **Akzeptanz:** Tastaturtest deckt Filter → Zeile → Sidebar → Vorschau → Bestätigung → Fokus-Rückkehr
  bei 1280, 1440 und 1920 Pixel sowie 200-Prozent-Zoom ab.
- **Nicht tun:** Keine Aktion nur auf Hover verfügbar machen. Keine Farbe als einziges Statussignal.
  Keine Smartphone-/Tablet-Karten oder Bottom-Sheets Pre-Pitch bauen.

### [P19] Verträge, Geldinvarianten und Historie umfassend testen

- **Datei/Ort:** Golden Tests der reinen Engines, API-/Service-Tests, DB-Migrations-/RLS-Tests,
  Frontend-Contract- und Render-/Interaktionstests.
- **Fundstelle:** Bestehende Matching-, M6-C3a/C3b-, Zahlungen- und RLS-Tests.
- **Ist:** Matching und Ledger sind stark getestet; manuelle Zuordnung, Ignorieren, Barzahlung,
  Abweichungen, vereinigtes Read Model und neue Konsumenten fehlen.
- **Soll:** Neue Pfade gegen Centgenauigkeit, Idempotenz, Unveränderlichkeit, Kontoisolation,
  konkurrierende Änderungen und konsistente Projektionen absichern.
- **Default:** Mindestens Testfälle für Voll-, Teil- und Überzahlung, bestätigtes Guthaben,
  Nicht-Guthaben ohne Bestätigung, Ignorieren/Aufheben, Barzahlung, manuelle Zuordnung, Dublette,
  Rücklastschrift, Mieterwechsel, mehrere Mietverhältnisse, Filter/Pagination, Cross-account-Angriff,
  doppelten Submit und veraltete Preview.
- **Erwartetes Ergebnis:** Kein UI- oder API-Pfad kann mehr Cent verteilen als die Zahlung enthält,
  fremde Forderungen zuordnen, einen Nachweis überschreiben oder Dashboard/Reminder mit einem anderen
  Saldo versorgen.
- **Akzeptanz:** `scripts/gate.sh full` bleibt grün; bei Änderungen am Demo-Pfad zusätzlich der
  nicht-destruktive Demo-Gate. Die bestehenden 13 Bank-Matching-Fixtures bleiben unverändert grün.
- **Nicht tun:** Bestehende Sicherheits- oder Rechtsfixtures abschwächen. Kein destruktives
  `verify_demo_path.sh --fresh` ohne ausdrückliche Freigabe.

## Out of Scope

- Produktive finAPI-Credentials, Vertragsabschluss und Aktivierung einer echten Bankverbindung ohne
  die in [P2] genannten Inputs.
- Vollständiges Mahnwesen, Mahnschreiben, Verzugszinsen, Gebühren, Eskalationsstufen und Versand.
- Automatische Verrechnung von Guthaben mit zukünftigen Forderungen oder Auszahlung an Mieter.
- Partieller Rückzahlungs-/Teil-Rücklastschriftprozess, solange die fachliche Regel nicht freigegeben
  ist.
- Automatische Ignorierregeln nach Absender, Textmuster oder Konto.
- Sammelzuordnung mehrerer Umsätze zu Forderungen.
- KI-/ML-basierte Betrugs- oder Risikoerkennung.
- Vollständige sonstige Buchhaltung/Kategorisierung, DATEV-Logik und Steuerberatung; „sonstige
  Einnahme/Ausgabe“ benötigt einen getrennten fachlichen Übergabevertrag.
- Echter Beleg-/Quittungs-Storage für Barzahlungen.
- Mieterportal-UI. Dieser Spec schafft nur die konsistente, später lesbare Datenbasis.
- Neue Rechts-, Fälligkeits-, Tilgungs-, Zins- oder Mahnlogik ohne freigegebene Primärquelle und
  zugehörige Golden Fixtures.

## Verifikation

- Die Seite zeigt eine gemeinsame, serverseitig paginierte Umsatzliste, neueste zuerst.
- Alle importierten Umsätze sind sichtbar, auch ohne Matching-Proposal.
- Filter „Nicht zugeordnet“, „Prüfen“, „Zugeordnet“, „Teilweise“ und „Ignoriert“ arbeiten auf derselben
  Liste und zeigen serverseitige Zähler.
- „Zuordnen“ öffnet rechts die Buchungsdetails und erhält Listenfilter sowie Scrollposition.
- „Ignorieren“ und „Ignorieren aufheben“ erzeugen Historienereignisse, verändern aber keine
  Banktransaktion und keine Forderung.
- Manuelle Zuordnung nutzt eine serverseitige Preview und schreibt erst nach Bestätigung ein
  unveränderliches Journalereignis.
- Teilzahlung, Überzahlung und Guthaben sind centgenau; die Kontrollsumme Zahlung = Allokationen +
  Guthaben gilt immer.
- Überzahlung wird sichtbar gemeldet und nicht ohne ausdrückliche Nutzerbestätigung als Guthaben
  gebucht.
- Barzahlungen erscheinen in derselben Liste und wirken auf dieselben Forderungen und Aggregate.
- Demo-Reset erzeugt reproduzierbare Demo-Konten, -Forderungen, -Umsätze und -Historien ohne
  Frontend-Mockbeträge.
- Dashboard, Objekt-/Mietverhältnisakte, Abrechnung und Reminder lesen denselben offenen Saldo.
- Ein abgelaufenes Consent verhindert neue Abrufe, löscht aber keine vorhandenen Nachweise.
- Desktop/Laptop bei 1280, 1440 und 1920 Pixel, 200-Prozent-Zoom und reine Tastaturbedienung
  funktionieren ohne verlorenen Fokus oder horizontalen Seitenscroll im Standardzoom.
- Bestehende Matching-, Geld-, RLS- und Unveränderlichkeitstests bleiben grün; neue Pfade sind auf
  allen Ebenen abgesichert.

## Reihenfolge

1. [P13] fachliche Forderungsgrundlage nur nach `⚠️ MUSS-INPUT`; parallel [P2] Kontolesestatus.
2. [P3], [P4] vereinigtes Read Model, Pagination und Filter.
3. [P15] persistiertes Demo-Szenario, damit alle folgenden UI-Zustände real prüfbar sind.
4. [P1], [P5], [P6], [P17], [P18] gemeinsame Arbeitsfläche und Zustände.
5. [P7], [P12] Ignorieren und sichere Sammelaktionen.
6. [P8], [P9], [P10], [P11] manuelle Zuordnung, Abweichungen, Teil-/Über-/Barzahlungen.
7. [P14], [P16] Abrechnung, Dashboard, Objekte und Reminder an dieselben Projektionen anbinden.
8. [P19] vollständige Verifikation und nicht-destruktiver Demo-Abgleich.

## Build-Notes (füllt die KI beim Umsetzen aus)

<!-- Annahmen, Abweichungen und übersprungene MUSS-INPUT-Teile hier eintragen. Erwartet u. a.:
- [P2] finAPI-Produktivkonfiguration fehlte — nur Port, Statusvertrag und Demo-Provider umgesetzt.
- [P8] Regel für neue manuelle Zuordnung nach endgültiger Ablehnung fehlte — diesen Unterpfad ausgelassen.
- [P10] Guthabenverwendung nicht freigegeben — Guthaben nur aufgezeichnet, nicht weiter verrechnet.
- [P11] Quittungs-/Storage-Prozess fehlte — Nachweisfeld sichtbar inaktiv oder ausgelassen.
- [P13] Fälligkeits-/Gesamtschuldnerregel fehlte — produktive Forderungserzeugung nicht aktiviert.
- [P16] Mahnlogik fehlte — ausschließlich Zahlungsfakten an Reminder übergeben.
-->
