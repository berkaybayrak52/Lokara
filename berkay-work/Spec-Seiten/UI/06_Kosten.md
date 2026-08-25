# 03_Kosten — Redesign „Kosten erfassen"

spec_id: `03-kosten`
titel: Kosten erfassen — Redesign (Liste + einstufiger Wizard + BetrKV-Katalog-Picker)
status: freigegeben
prioritaet: hoch
betrifft: `apps/web` (Feature „kosten", App-Shell-Navigation). Enthält normative **Erwartungen an das Backend** (`apps/api`, `packages/rules-store`), die Emir parallel umsetzt.
abhaengig_von: `00_Layout-Global` (freigegeben); Emirs technische Contract-Reparatur (läuft parallel, kein eigener Spec — Emir baut das Backend „entsprechend den Frontend-Erwartungen aus den Adjustment-Specs")
repo_stand: `Lokara-main @ 2026-08-24`

---

## Zweck

Die Seite „Kosten erfassen" wird von einer zweispaltigen Tabelle-plus-Formular-Ansicht zu einer **einspaltigen Listen-Seite** umgebaut; das Erfassen neuer Kosten läuft über einen **einstufigen Wizard auf eigener Route**. Statt frei getippter Kostenart wählt der Nutzer aus dem **BetrKV-Katalog**; der Umlageschlüssel wird ehrlich (greift beim Anlegen), Löschen wird zu Stornieren mit Begründung, und der Beleg-Import erscheint als sichtbarer, aber inaktiver **Beta**-Modus. Reine UI/UX-Arbeit — die Rechen-, Klassifizierungs- und Rechtslogik liegt bei Emirs Backend.

## Invarianten

- Pre-Pitch gilt Desktop/Laptop bei 1280, 1440 und 1920 Pixel sowie 200-Prozent-Zoom. Smartphone-,
  Tablet- und native Varianten sind Post-Pitch; Tastatur, Screenreader und sichtbarer Fokus bleiben
  verpflichtend.

- Nur vorhandene Design-Tokens verwenden (`ink`, `green`, `forest`, `mint`, `slate`, `paper` aus dem UI-Package), Schriften Montserrat/Manrope. **Keine rohe Farbangabe**, keine neue npm-Dependency.
- Nur die im jeweiligen Befehl **benannten Dateien/Stellen** ändern. Keine unbeteiligte Datei anfassen.
- Bestehende Tests bleiben grün, die Typprüfung bleibt sauber.
- **Keine Rechen-, Geld- oder Rechtslogik verändern.** Katalog-Inhalt, Klassifizierung und Umlage-Berechnung sind Backend. Dieser Spec zeigt nur an, was das Backend zurückgibt, und schickt, was es erwartet.
- **Parallelbetrieb mit Emirs Reparatur:** Redesign und technische Reparatur fassen teils dieselben Dateien an (`costs-page.tsx`, `cost-form.ts`, `queries.ts`, `contracts.ts`). Bei Konflikt hat die hier beschriebene **Ziel-Optik und das Ziel-Verhalten Vorrang**; die Datenanbindung folgt den „Erwartung an Backend"-Blöcken. Reihenfolge egal — das Endergebnis muss beides erfüllen.
- **„Erwartung an Backend"-Blöcke sind normativ.** Sie benennen in Worten (Feldnamen/Typen erlaubt, **kein Code**), welche Daten das Frontend erwartet bzw. sendet. Emir baut Backend/Contract passend. Wo ein erwartetes Feld beim Bauen noch fehlt, den betroffenen UI-Teil defensiv behandeln (leer/ausgegraut) statt abstürzen, und in Build-Notes vermerken.
- App-Rahmen/Sidebar aus `00_Layout` erben (A-Modell). **Kein globaler Objekt-Filter** — der seiten-lokale Objekt-Umschalter der Kosten-Seite ist davon ausdrücklich ausgenommen (Kosten sind fachlich pro Objekt).
- Bauen statt fragen: jeder freie Parameter hat einen Default. Bei Unklarheit naheliegendste Variante, nicht anhalten, Annahme in `## Build-Notes`. `⚠️ MUSS-INPUT` nie erfinden — Teilpunkt überspringen, loggen, Rest bauen.

## Befehle

### [K1] Kosten-Seite auf einspaltige Liste umbauen

- **Datei/Ort:** Hauptkomponente der Seite „Kosten erfassen" (Feature „kosten", die Seiten-Komponente mit dem Objekt-Umschalter und dem zweispaltigen Inhaltsbereich).
- **Fundstelle:** Die Komponente, deren Kopf mit der Überschrift „Kosten erfassen" und dem Untertitel „Betriebskosten je Objekt und Abrechnungszeitraum. Der Umlageschlüssel wird pro Kostenart gewählt und kann jederzeit geändert werden — die Abrechnung rechnet neu, erfasste Daten bleiben erhalten." beginnt; darunter aktuell ein zweispaltiges Raster mit links dem Bereich „Erfasste Kosten" (Tabelle) und rechts der Karte „Kostenart erfassen".
- **Ist:** Zweispaltiges Raster (grob 3-zu-2): links die Kostentabelle, rechts ein fest eingeblendetes Erfassungsformular.
- **Soll:** Das rechte Formular von der Seite entfernen (es wandert in den Wizard, siehe [K3]). Die Seite wird **einspaltig**: oben eine Steuerleiste, darunter die Kostenliste über die volle Inhaltsbreite.
- **Default:** Steuerleiste als eine Zeile über der Liste — links der Objekt-Umschalter ([K12]), rechts ein primärer Button „Kosten erfassen", der den Wizard öffnet ([K3]). Der Jahr-Filter kommt aus Emirs Listenfilter ([K2]), nicht als eigenes Element hier. Inhaltsbreite wie auf den anderen Seiten (Seiten-Standardbreite, nicht schmaler als die bisherige Tabelle).
- **Erwartetes Ergebnis:** Unter dem unveränderten Seitenkopf steht eine Steuerleiste (Objekt-Umschalter links, Button „Kosten erfassen" rechtsbündig, in der Marken-Primärfarbe wie andere Primär-Buttons). Darunter die Kostenliste als Tabelle über die volle Breite, in einer Karte wie bisher. Kein zweites Formular mehr rechts. Der Leerzustand „Noch keine Kosten erfasst" bleibt, sein Beschreibungstext wird angepasst (siehe unten). Abstände und Kartenstil folgen `00_Layout`.
- **Akzeptanz:** Auf der Kosten-Seite gibt es keine rechte Formularspalte mehr; oben steht ein Button „Kosten erfassen"; die Liste nimmt die volle Breite ein.
- **Nicht tun:** Den Seitenkopf-Text (Überschrift + Untertitel) nicht ändern. Die Tabellen-Spaltenlogik nur wie in [K10]/[K11]/[K13] beschrieben anfassen. Keine Berechnung berühren.

### [K2] Liste nach Abrechnungsjahr filterbar machen (über Emirs Listenfilter)

- **Datei/Ort:** Kosten-Liste; Abstimmung mit Emirs generischem Listenfilter.
- **Fundstelle:** Der Bereich „Erfasste Kosten" — aktuell werden alle Kosten des gewählten Objekts ungefiltert gezeigt (Tabellen-Beschriftung „Erfasste Kostenarten mit ihrem Umlageschlüssel. Ein Wechsel des Schlüssels löscht keine Daten.").
- **Ist:** Keine Jahr-/Zeitraum-Filterung. Alle Kostenzeilen des Objekts stehen untereinander.
- **Soll:** Die Liste muss nach **Abrechnungsjahr** filterbar sein. Das Bedienelement liefert Emirs generischer Listenfilter (kommt parallel für alle Listen). Dieser Spec baut **kein eigenes Jahr-Dropdown**, sondern fordert Jahr als Filteroption ein.
- **⚠️ Abstimmpunkt mit Emir:** Der generische Filter muss für die Kostenliste eine **Jahr-Auswahl** anbieten (eine Liste auswählbarer Jahre), nicht nur eine Freitext-Suche über die Tabelle — sonst fehlt die „ein Jahr auf einmal"-Sicht, die der Grund für die Anforderung ist.
- **Default:** Auswählbare Jahre = die Jahre, die von vorhandenen Kosten berührt werden, plus das laufende Jahr. Eine Kostenart, deren Zeitraum über den Jahreswechsel geht, erscheint in **jedem** Jahr, das ihr Zeitraum berührt. Vorauswahl = jüngstes Jahr mit Kosten.
- **Erwartetes Ergebnis:** Über oder an der Liste sitzt die Jahr-Auswahl aus Emirs Filter; die Auswahl eines Jahres reduziert die Liste auf die Kosten dieses Jahres. Optik des Filters folgt Emirs Filter-Komponente (dieser Spec schreibt sie nicht vor).
- **Akzeptanz:** Man kann die Kostenliste auf ein einzelnes Abrechnungsjahr einschränken.
- **Nicht tun:** Kein eigenes Jahr-Dropdown bauen, das Emirs Filter dupliziert. Kein globaler Header-Filter (nur listen-lokal).

### [K3] Erfassen als einstufigen Wizard auf eigener Route

- **Datei/Ort:** Neue Wizard-Seite/Route im Feature „kosten"; dazu der Button „Kosten erfassen" aus [K1].
- **Fundstelle:** Die bisherige rechte Karte „Kostenart erfassen" mit der Beschreibung „Eingaben werden automatisch als Entwurf gespeichert — nichts geht beim Abbrechen verloren." samt ihren Feldern (Kostenart, Betrag in € (Gesamtkosten), Zeitraum von / bis (exklusiv), Umlageschlüssel, ggf. „Direkt zuordnen an").
- **Ist:** Das Erfassungsformular ist fest rechts auf der Kosten-Seite eingebettet.
- **Soll:** Das Erfassen auf eine **eigene Route** als einstufigen Wizard umsetzen (Muster wie die Objekte-Wizards aus `02_Objekte`: eigene Route, **kein Modal/Dialog-Paket** — das gibt es im UI-Package nicht). Der Button „Kosten erfassen" navigiert dorthin. Ein Schritt (das Formular), danach ein Bestätigungszustand.
- **Default:** Route `/a/{Konto}/kosten/neu`, das aktuell gewählte Objekt wird als Query-Parameter `objektId` mitgegeben (fällt der Parameter weg, gilt dieselbe Objektauflösung wie auf der Liste: einziges Objekt automatisch, sonst Objektwahl im Wizard). Nach dem Speichern: Bestätigungszustand mit Text „Kostenart erfasst." und zwei Aktionen — „Noch eine Kostenart erfassen" (leert das Formular, bleibt im Wizard) und „Fertig" (zurück zur Kostenliste). Der Entwurf-Autospeicher der bisherigen Karte bleibt erhalten.
- **Erwartetes Ergebnis:** Klick auf „Kosten erfassen" öffnet eine eigene Seite mit eigenem Kopf („Kosten erfassen" als Titel, kurzer Rückweg/Abbrechen zur Liste). Darunter der Modus-Umschalter ([K4]) und das Formular ([K6]–[K9]). Der Absende-Button trägt weiter „Kostenart erfassen" (Ladezustand „Wird erfasst…"). Nach Erfolg erscheint der Bestätigungszustand mit den zwei Aktionen; „Noch eine Kostenart erfassen" setzt das Formular auf leer zurück und bleibt auf der Wizard-Seite, „Fertig" führt zurück zur Liste, wo die neue Kostenart erscheint. Bei Eingabefehlern bleibt der Nutzer im Formular mit Feldhinweisen.
- **Akzeptanz:** „Kosten erfassen" führt auf eine eigene Seite (eigene URL); die Kosten-Liste selbst enthält kein Erfassungsformular mehr; nach dem Speichern erscheint eine Bestätigung mit „Noch eine Kostenart erfassen" und „Fertig".
- **Nicht tun:** Kein Modal/Dialog. Keine zweite Schrittseite (der Wizard ist bewusst einstufig). Die Entwurf-Autospeicher-Logik nicht entfernen.

### [K4] Modus-Umschalter im Wizard — „Aus Beleg" als inaktives Beta

- **Datei/Ort:** Oberster Bereich der Wizard-Seite aus [K3].
- **Fundstelle:** Der Kopf des Wizard-Formulars, direkt über den Eingabefeldern.
- **Ist:** Es gibt aktuell einen eigenen Menüpunkt „Beleg-Upload" mit eigener Seite (Upload → Erkannte Felder → Übernehmen). Im Erfassungsformular selbst gibt es keinen Modus-Umschalter.
- **Soll:** Oben im Wizard ein Segmented-Control mit zwei Optionen: „Manuell erfassen" (aktiv, vorausgewählt) und „Aus Beleg (Beta)" (**sichtbar, aber inaktiv/ausgegraut, nicht klickbar**). Bei „Aus Beleg" **kein** Datei-Uploader und **keine** Erkennung — nur ein kurzer Hinweis. Muster wie die inaktiven Bild-Slots aus `02_Objekte` [O12]: sichtbar, ehrlich als „kommt bald" markiert, ohne Schein-Funktion.
- **Default:** Das Label der zweiten Option trägt ein kleines „Beta"-Kennzeichen. Der inaktive Zustand nutzt die gedämpfte Darstellung wie ein deaktivierter Button/Tab (reduzierte Deckkraft, Cursor „nicht erlaubt", nicht fokussierbar). Unter dem Umschalter, wenn „Aus Beleg" visuell angedeutet wird, ein Satz in der Sekundär-Textfarbe (`slate`): „Automatische Belegerkennung kommt bald."
- **Erwartetes Ergebnis:** Im Wizard sieht der Nutzer zwei Reiter/Segmente. „Manuell erfassen" ist aktiv und zeigt das Formular. „Aus Beleg (Beta)" ist sichtbar, ausgegraut und lässt sich nicht anklicken oder per Tastatur fokussieren; es öffnet nichts. Kein Upload-Feld, kein Fortschritt, kein Aufruf einer Erkennung.
- **Akzeptanz:** „Aus Beleg (Beta)" ist sichtbar, aber nicht bedienbar; es existiert kein Datei-Uploader im Wizard; „Manuell erfassen" ist vorausgewählt.
- **Nicht tun:** Keinen Uploader, keinen Erkennungs-/Extraktions-Flow bauen. Keine Extraktions-Route aufrufen. Den bestehenden Beleg-Backendcode nicht anfassen (Emirs Sache).

### [K5] Menüpunkt „Beleg-Upload" aus der Navigation entfernen

- **Datei/Ort:** Die App-Shell / linke Navigation (die gemeinsame Portal-Shell-Komponente mit den Navigationspunkten „Übersicht", „Objekte", „Kosten erfassen", „Beleg-Upload", „Zähler", „Abrechnung erstellen").
- **Fundstelle:** Der Navigationseintrag mit dem Text „Beleg-Upload" in der Sidebar-Liste.
- **Ist:** „Beleg-Upload" ist ein eigener Navigationspunkt mit eigener Seite.
- **Soll:** Den Navigationspunkt „Beleg-Upload" **entfernen**. Beleg lebt künftig ausschließlich als inaktiver Beta-Modus im Kosten-Wizard ([K4]).
- **Erwartetes Ergebnis:** Die Sidebar zeigt „Übersicht", „Objekte", „Kosten erfassen", „Zähler", „Abrechnung erstellen" — ohne „Beleg-Upload". Reihenfolge und Stil der übrigen Punkte unverändert.
- **Akzeptanz:** In der Navigation taucht „Beleg-Upload" nicht mehr auf; eine Suche im Frontend nach dem Navigations-Label findet keinen sichtbaren Menüeintrag mehr.
- **Nicht tun:** Die bestehende Beleg-Seite/-Route selbst nicht löschen oder umbauen (ob die Route bleibt oder entkoppelt wird, entscheidet Emir). Keine anderen Navigationspunkte anfassen.

### [K6] BetrKV-Katalog-Picker als erstes Wizard-Feld

- **Datei/Ort:** Das Wizard-Formular ([K3]), erstes Eingabefeld; dazu der Contract/Datenbezug für die Katalogliste.
- **Fundstelle:** Das bisherige erste Feld „Kostenart" mit dem Hinweis „z. B. Müllabfuhr" (ein freies Texteingabefeld).
- **Ist:** „Kostenart" ist ein Freitextfeld. Es trägt keine rechtliche Bedeutung, und das Backend verlangt inzwischen eine Katalog-Identität, die das Formular nicht liefert.
- **Soll:** Das erste Feld wird ein **auswählbarer BetrKV-Katalog-Picker**: eine durchsuchbare Auswahl echter Betriebskosten-Arten, gruppiert in „Umlagefähig" und „Nicht umlagefähig", je Eintrag mit Anzeigename und BetrKV-Nummer. Die getroffene Wahl bestimmt die rechtliche Kostenart (Katalog-Identität) und belegt den Umlageschlüssel vor ([K8]).
- **Erwartung an Backend (normativ):** Ein lesender Endpoint liefert die Katalogpositionen. Jede Position trägt in Worten: eine technische Kennung (`catalogueId` / `costType`), einen Anzeigenamen (`label`), eine BetrKV-Nummer (`betrkvNumber`, kann bei nicht-umlagefähigen Positionen fehlen), einen Vorschlags-Umlageschlüssel (`defaultKey`, einer der sechs Schlüssel AREA/PERSONS/CONSUMPTION/UNITS/DIRECT/MEA; fehlt bei nicht-umlagefähigen Positionen), ein Benennungspflicht-Kennzeichen (`namingRequired`, ja/nein) und ein Umlagefähig-Kennzeichen (`allocable`, ja/nein). Beim Anlegen sendet das Formular die gewählte `catalogueId` als Pflichtwert.
- **Default:** Picker als Kombination aus Suchfeld und gruppierter Optionsliste. Anzeige je Zeile: Anzeigename, dahinter dezent die BetrKV-Nummer (z. B. „Aufzug · § 2 Nr. 7"). Gruppenüberschriften „Umlagefähig" (zuerst) und „Nicht umlagefähig". Sortierung innerhalb der Gruppe alphabetisch nach Anzeigename. Kein vorbelegter Wert — Platzhalter „Kostenart wählen …". Ist der Endpoint beim Bauen noch nicht vorhanden, das Feld leer/deaktiviert zeigen und in Build-Notes vermerken (kein hartkodierter Katalog im Frontend).
- **Erwartetes Ergebnis:** Als erstes Feld im Wizard steht „Kostenart (BetrKV)". Der Nutzer tippt/scrollt und wählt eine Position; die Liste ist in umlagefähig/nicht umlagefähig getrennt, jede Zeile zeigt die BetrKV-Nummer. Nach der Wahl steht der Umlageschlüssel entsprechend vorbelegt ([K8]). Feldstil, Fokus- und Fehlerzustände wie die übrigen Formularfelder (Tokens, Montserrat/Manrope).
- **Akzeptanz:** Das erste Wizard-Feld ist eine Auswahl aus dem BetrKV-Katalog (kein freies Kostenart-Textfeld mehr); die Optionen sind nach umlagefähig/nicht umlagefähig gruppiert und zeigen BetrKV-Nummern; die Auswahl wird beim Anlegen als Katalog-Identität mitgesendet.
- **Nicht tun:** Den Katalog **nicht** im Frontend hartkodieren (kommt aus dem Endpoint). Keine Rechtszuordnung/BetrKV-Nummer selbst erfinden.

### [K7] Freitext als optionale „Bezeichnung" behalten

- **Datei/Ort:** Wizard-Formular, direkt unter dem Katalog-Picker.
- **Fundstelle:** Der bisherige Freitext des Feldes „Kostenart" — sein Eingabezweck (eigene Benennung, z. B. „Müllabfuhr", Belegbezug).
- **Ist:** Der Freitext war die Kostenart selbst.
- **Soll:** Den Freitext als **optionales Feld „Bezeichnung"** unter dem Picker erhalten — eine eigene Benennung/Beleg-Notiz ohne Rechtswirkung. Beim Anlegen als Anzeige-Label (`label`) mitsenden.
- **Default:** Beschriftung „Bezeichnung (optional)", Hinweis „Eigene Benennung, z. B. Rechnungsnummer oder ‚Müllabfuhr Q1'". Bleibt das Feld leer, wird der Anzeigename der gewählten Katalogposition als Label verwendet.
- **Erwartetes Ergebnis:** Unter der Kostenart-Auswahl steht ein optionales Textfeld „Bezeichnung". Leere Eingabe ist erlaubt; dann trägt die Kostenzeile in der Liste den Katalog-Anzeigenamen. Ist eine Bezeichnung gesetzt, erscheint sie als Label der Zeile.
- **Akzeptanz:** Es gibt ein optionales Bezeichnungsfeld getrennt von der Kostenart-Auswahl; ohne Eingabe lässt sich trotzdem speichern.
- **Nicht tun:** Das Bezeichnungsfeld nicht zur Pflicht machen. Es nicht als rechtliche Kostenart verwenden.

### [K8] Umlageschlüssel aus Katalog-Default vorbelegen und wirksam senden

- **Datei/Ort:** Wizard-Formular, Feld „Umlageschlüssel" und die Absende-Werte.
- **Fundstelle:** Das Feld „Umlageschlüssel" mit dem Hilfetext „Später jederzeit änderbar, ohne Datenverlust." und (bei Direktzuordnung) das Zusatzfeld „Direkt zuordnen an" mit dem Platzhalter „Einheit wählen …".
- **Ist:** Der Umlageschlüssel ist frei wählbar, wird beim Anlegen aber vom Backend ignoriert (der Schlüssel kommt aus dem Katalog-Default) — die Auswahl im Formular ist heute wirkungslos.
- **Soll:** Nach Wahl der Kostenart ([K6]) das Schlüssel-Feld mit dem `defaultKey` der Position **vorbelegen**. Der Nutzer darf ihn ändern. Beim Anlegen greift die Wahl wirklich: weicht der gewählte Schlüssel vom Katalog-Default ab, wird er als **Schlüssel-Übersteuerung** (`keyOverride`) mitgesendet; steht der Default unverändert, wird kein Override gesendet (das Backend nimmt dann den Katalog-Default, die Herkunft bleibt „catalogue").
- **Erwartung an Backend (normativ):** Der Anlege-Aufruf akzeptiert neben der `catalogueId` optional eine Schlüssel-Übersteuerung `keyOverride` (einer der sechs Schlüssel) sowie bei Direktzuordnung das Ziel (Einheit `directUnitId`). Ohne `keyOverride` verwendet das Backend den Katalog-Default der Position.
- **Default:** Vorbelegung = `defaultKey` der gewählten Position. Die sechs Schlüssel behalten ihre Anzeigenamen („Wohnfläche (m²·Tage)", „Personenzahl (Personen·Tage)", „Verbrauch", „Einheiten (Einheiten·Tage)", „Direktzuordnung", „Miteigentumsanteile (MEA·Tage)"). Bei „Direktzuordnung" erscheint wie bisher das Feld „Direkt zuordnen an" mit Einheitenauswahl (Pflicht, wenn Direktzuordnung gewählt).
- **Erwartetes Ergebnis:** Sobald eine Kostenart gewählt ist, steht im Schlüssel-Feld der passende Vorschlag. Ändert der Nutzer ihn, wird die Änderung beim Speichern wirksam (die neue Kostenzeile trägt den gewählten Schlüssel, nicht stumm den Default). Der Hilfetext „Später jederzeit änderbar, ohne Datenverlust." bleibt. Bei „Direktzuordnung" muss eine Einheit gewählt werden, sonst Feldfehler.
- **Akzeptanz:** Der im Wizard gewählte Umlageschlüssel erscheint nach dem Speichern an der Kostenzeile (die Wahl ist nicht mehr wirkungslos); bei gleichbleibendem Default wird keine Übersteuerung gesendet.
- **Nicht tun:** Die spätere Schlüssel-Änderung in der Liste (der bestehende versionierte Wechsel über den Zeilen-Auswähler) nicht anfassen — sie funktioniert und bleibt.

### [K9] Nicht-umlagefähige Kostenart sichtbar führen

- **Datei/Ort:** Wizard-Formular, Bereich unter der Kostenart-Auswahl / am Absende-Button.
- **Fundstelle:** Der Zustand nach Wahl einer Katalogposition, deren Umlagefähig-Kennzeichen `allocable` = nein ist (z. B. Verwaltungskosten, Instandhaltung).
- **Ist:** Es gibt keine Freitext-/Katalogunterscheidung; ein nicht-umlagefähiger Fall würde heute nur als stummer Serverfehler auftreten.
- **Soll:** Wählt der Nutzer eine **nicht umlagefähige** Position, zeigt der Wizard das klar an und erklärt es, statt in einen stummen Fehler zu laufen. Der Schlüssel-Teil entfällt für diesen Fall (es gibt keinen `defaultKey`).
- **Default:** Ein Hinweisblock in der Warnfarbe (Token-Warnung, nicht rot-destruktiv), Text: „Diese Kostenart ist nach BetrKV **nicht auf Mieter umlagefähig**. Sie kann erfasst, aber nicht auf die Mieter umgelegt werden." Das Schlüssel-Feld wird ausgeblendet oder deaktiviert. Der Absende-Button bleibt bedienbar (Erfassen zu Dokumentationszwecken ist erlaubt), trägt aber den Zusatz bzw. Titel „Nicht umlagefähig erfassen". Ob das Backend nicht-umlagefähige Kosten annimmt, ist Emirs Entscheidung; führt der Absende-Versuch zu einem fachlichen Fehler, diesen als verständlichen Hinweis zeigen, nicht als generischen 422.
- **Erwartetes Ergebnis:** Nach Wahl einer nicht-umlagefähigen Position sieht der Nutzer sofort den Hinweis, dass diese Kosten nicht umlagefähig sind; das Schlüssel-Feld ist weg/deaktiviert; der Nutzer versteht, warum keine Umlage erfolgt.
- **Akzeptanz:** Bei Auswahl einer nicht-umlagefähigen Kostenart erscheint ein verständlicher Hinweis und kein Umlageschlüssel-Feld; es gibt keinen rohen technischen Fehler.
- **Nicht tun:** Die Umlagefähigkeit **nicht** im Frontend selbst bestimmen — sie kommt aus dem `allocable`-Kennzeichen der Katalogposition. Keine Rechtsauskunft-Texte über den obigen Hinweis hinaus erfinden.

### [K10] Status-Spalte in der Kostenliste

- **Datei/Ort:** Die Kostenliste (Tabelle) auf der Kosten-Seite.
- **Fundstelle:** Die Tabelle „Erfasste Kosten" mit den Spalten „Kostenart", „Betrag", „Zeitraum", „Umlageschlüssel" und der Aktionsspalte.
- **Ist:** Die Liste zeigt keinen Klassifizierungs-Status. Ob eine Kostenart abrechnungsreif ist oder noch geprüft werden muss, ist unsichtbar.
- **Soll:** Eine **Status-Spalte** ergänzen, die je Kostenzeile zeigt, ob sie abrechnungsreif ist oder noch Prüfung braucht, samt der zurückgemeldeten Prüf-Hinweise.
- **Erwartung an Backend (normativ):** Jede Kostenzeile liefert ein Kennzeichen „vor Produktion prüfen" (`productionBlocked`, ja/nein) und eine Liste von Prüf-Hinweisen als Kurzcodes (`classificationFindings`, z. B. `verify-before-production`, `nr17-nicht-benannt`, `umlagevereinbarung-fehlt`, `lohnanteil-vorgeschlagen`).
- **Default:** Statusanzeige als kleine Badge: bei `productionBlocked` = ja → Badge „Prüfen" in der Warnfarbe; sonst → Badge „Abrechnungsreif" in der Erfolgsfarbe (`green`/`forest`). Unter der Badge die Hinweise als kurze Liste, jeder Code über eine Zuordnungstabelle in einen verständlichen Satz übersetzt; unbekannte Codes im Klartext zeigen. Start-Zuordnung (anpassbar, in Build-Notes vermerken):
  - `verify-before-production` → „Vor Produktivnutzung rechtlich prüfen."
  - `nr17-nicht-benannt` → „Als sonstige Betriebskosten im Mietvertrag nicht benannt."
  - `umlagevereinbarung-fehlt` → „Keine Umlagevereinbarung hinterlegt."
  - `mehrbelastungsklausel-fehlt` → „Neue Kostenart ohne Mehrbelastungsklausel."
  - `lohnanteil-vorgeschlagen` → „Lohnanteil geschätzt — bitte prüfen."
  - `trinkwasser-nr17-fallback` → „Ersatzweise als Wasserkosten geführt."
- **Erwartetes Ergebnis:** Die Tabelle hat eine zusätzliche Spalte „Status". Jede Zeile zeigt „Abrechnungsreif" oder „Prüfen" als farbige Badge; wo Hinweise vorliegen, stehen sie als kurze, verständliche Sätze darunter. Fehlen die Felder (Backend noch nicht so weit), zeigt die Spalte neutral „—" statt eines Absturzes.
- **Akzeptanz:** Die Liste hat eine Status-Spalte; Kostenzeilen mit `productionBlocked` = ja tragen sichtbar „Prüfen"; vorhandene Hinweise erscheinen in Klartext.
- **Nicht tun:** Den Status **nicht** im Frontend berechnen — er kommt aus den gelieferten Feldern. Keine eigenen Rechtsbewertungen erfinden.

### [K11] „Löschen" durch „Stornieren" mit Begründung ersetzen

- **Datei/Ort:** Die Aktionsspalte der Kostenliste.
- **Fundstelle:** Die zweistufige Löschaktion mit dem roten Auslöser „Löschen", der Rückfrage „Wirklich löschen?", dem Bestätigungs-Button „Löschen" und „Abbrechen".
- **Ist:** Zweistufiges Hard-Delete. (Der zugehörige Lösch-Weg im Backend existiert nicht mehr — Löschen läuft heute ins Leere.)
- **Soll:** Die Aktion in **„Stornieren"** umbenennen und um ein **Pflicht-Begründungsfeld** erweitern. Statt endgültigem Löschen wird die Kostenzeile mit Grund storniert (die Historie bleibt).
- **Erwartung an Backend (normativ):** Das Stornieren ruft einen Void-Weg auf, der eine **Pflicht-Begründung** (`reason`, nicht leer) entgegennimmt und die Kostenzeile ungültig setzt, ohne sie zu löschen. Kein Hard-Delete.
- **Default:** Auslöser heißt „Stornieren" (weiterhin dezent/destruktiv-getönt). Klick öffnet inline eine kleine Bestätigung: kurzes Pflichtfeld „Grund der Stornierung" (Platzhalter „z. B. Doppelt erfasst / falscher Betrag"), Button „Stornieren" (destruktiv), Button „Abbrechen". Leerer Grund → Button deaktiviert bzw. Feldfehler „Bitte einen Grund angeben.". Nach Erfolg verschwindet die Zeile aus der aktiven Liste. Optionaler Folgehinweis „Durch Korrektur ersetzen" darf gezeigt werden, ist aber nicht Pflicht dieses Specs.
- **Erwartetes Ergebnis:** In der Aktionsspalte steht „Stornieren". Klick zeigt ein Begründungsfeld; ohne Grund lässt sich nicht stornieren. Nach Bestätigung ist die Kostenzeile aus der aktiven Liste entfernt, aber nicht hart gelöscht.
- **Akzeptanz:** Die Aktion heißt „Stornieren"; sie verlangt eine nicht-leere Begründung; sie ruft den Void-Weg auf, nicht ein Hard-Delete.
- **Nicht tun:** Kein endgültiges Löschen mehr anbieten. Die Begründung nicht optional machen.

### [K12] Objekt-Umschalter beibehalten und in die neue Steuerleiste einfügen

- **Datei/Ort:** Die Steuerleiste der Kosten-Liste ([K1]).
- **Fundstelle:** Die bisherige Objekt-Umschalt-Reihe (Button-Gruppe mit `aria-label` „Objekt wählen", die bei mehr als einem Objekt erscheint) und der Leerzustand „Noch kein Objekt".
- **Ist:** Der Objekt-Umschalter steht als lose Button-Reihe über dem zweispaltigen Inhalt; bei genau einem Objekt wird es automatisch gewählt; ohne Objekt erscheint der Leerzustand mit Link zu „Objekte".
- **Soll:** Den Objekt-Umschalter unverändert im Verhalten in die neue Steuerleiste (links) einordnen und visuell an das Redesign angleichen. Verhalten (ein Objekt automatisch, mehrere als Umschalter, kein Objekt → Leerzustand) bleibt.
- **Default:** Der Umschalter bleibt eine Segment-/Button-Reihe mit `aria-pressed` für das aktive Objekt; Stil an `00_Layout` angeglichen. Der Leerzustand „Noch kein Objekt" mit Link zu „Objekte" bleibt inhaltlich; der Beschreibungstext bleibt.
- **Erwartetes Ergebnis:** Links in der Steuerleiste steht der Objekt-Umschalter; die Auswahl filtert die Liste (und den Wizard-Kontext) wie bisher pro Objekt. Bei einem Objekt kein Umschalter; ohne Objekt der Leerzustand.
- **Akzeptanz:** Der Objekt-Umschalter funktioniert wie zuvor, steht aber in der neuen Steuerleiste; er ist kein globaler Header-Filter.
- **Nicht tun:** Den Objekt-Umschalter nicht in einen globalen Filter verwandeln. Die Objektauflösungs-Logik nicht ändern.

### [K13] Visuelle Politur von Liste und Wizard nach 00_Layout

- **Datei/Ort:** Die Kosten-Liste und die Wizard-Seite.
- **Fundstelle:** Die gesamte sichtbare Oberfläche der Kosten-Seite und des Wizards (Karten, Tabelle, Formularfelder, Buttons, Leer-/Erfolgs-/Fehlerzustände wie „Noch keine Kosten erfasst", „Gespeichert.", „Erfassen fehlgeschlagen.").
- **Ist:** Funktionale, aber ungeschliffene Standard-Darstellung; teils an das alte Zweispalten-Layout gebunden.
- **Soll:** Liste und Wizard konsistent auf den Lokara-Look bringen — Kartenstil, Typo (Montserrat/Manrope), Abstände, Zustände (Ruhe/Hover/aktiv/Fokus), Markenakzent wie in `00_Layout` (z. B. linke Akzentkante `border-l-4 border-green` / `text-forest` an Sektionsköpfen, `items-start` bei Kartenreihen).
- **Default:** Denselben Karten-, Tabellen- und Button-Stil wie auf den bereits überarbeiteten Seiten (Dashboard/Objekte) verwenden. Leerzustandstext der Liste anpassen, da rechts kein Formular mehr steht: aus „Erfassen Sie rechts die erste Kostenart — z. B. Müllabfuhr 1.200,00 € nach Wohnfläche." wird „Erfassen Sie über ‚Kosten erfassen' die erste Kostenart — z. B. Müllabfuhr 1.200,00 € nach Wohnfläche." Erfolg-/Fehler-/Entwurf-Hinweise des Formulars in den Wizard übernehmen.
- **Erwartetes Ergebnis:** Kosten-Liste und Wizard wirken wie ein Teil derselben App wie Dashboard und Objekte: gleiche Kartenanmutung, gleiche Typo, gleiche Zustände und Akzente. Der Listen-Leerzustand verweist auf den „Kosten erfassen"-Button statt auf ein rechtes Formular.
- **Akzeptanz:** Liste und Wizard nutzen ausschließlich Tokens/Schriften des Systems; der Leerzustandstext verweist nicht mehr auf ein „rechts" stehendes Formular; die Zustände (Erfolg/Fehler/Entwurf) erscheinen im Wizard.
- **Nicht tun:** Keine rohen Farben, keine neue Dependency. Keine Texte der Rechen-/Rechtslogik verändern.

## Out of Scope

- Die echte Belegerkennung/OCR-Funktion (bleibt inaktiv, „Aus Beleg" ist Beta) und der bestehende Beleg-Backend-Stub.
- Befund 3 („None" statt „Leerstand/Eigennutzung → Vermieter") — sitzt in der Abrechnungs-/Statement-Ansicht, nicht auf der Kosten-Seite; eigener späterer Spec.
- Echter Bild-/Beleg-Speicher.
- Emirs technische Contract-Reparatur selbst (Katalog-Endpoint, Void-Weg, Schema-Erweiterungen) — hier nur als Erwartung benannt, nicht als Bauauftrag ans Frontend.
- Das generische Listenfilter-Bedienelement (baut Emir); dieser Spec fordert nur „Jahr als Filteroption".

## Verifikation

- Die Kosten-Seite ist einspaltig: oben Steuerleiste (Objekt-Umschalter + „Kosten erfassen"), darunter die Liste über volle Breite; kein rechtes Formular mehr.
- „Kosten erfassen" öffnet eine eigene Wizard-Seite mit Modus-Umschalter „Manuell erfassen" (aktiv) / „Aus Beleg (Beta)" (sichtbar, inaktiv, kein Uploader).
- Im Wizard wählt man die Kostenart aus dem BetrKV-Katalog (gruppiert umlagefähig/nicht, mit BetrKV-Nummer); eine optionale „Bezeichnung" ist getrennt; der Umlageschlüssel steht passend vorbelegt und ist wirksam.
- Nach dem Speichern erscheint eine Bestätigung mit „Noch eine Kostenart erfassen" / „Fertig"; die neue Kostenart steht in der Liste.
- Die Liste hat eine Status-Spalte (Abrechnungsreif/Prüfen + Hinweise) und lässt sich nach Abrechnungsjahr filtern (über Emirs Filter, mit Jahr-Auswahl).
- Die Aktion heißt „Stornieren" und verlangt eine Begründung; kein Hard-Delete.
- In der Navigation gibt es keinen Menüpunkt „Beleg-Upload" mehr.
- Nur Tokens/Schriften des Systems; Typprüfung sauber; bestehende Tests grün.

## Build-Notes (füllt die KI aus)

- (leer — Annahmen und Abweichungen hier eintragen)
