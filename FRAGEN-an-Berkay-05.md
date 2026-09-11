# Offene Nachlieferungen nach Berkays Antwort — Runde 5

Emir · Stand 11.09.2026 · nach Berkays Antwort auf `FRAGEN-an-Berkay-05.md`

Berkay hat alle fachlichen Entscheidungen aus Runde 5 beantwortet. Die Regeln sind in ihren
Owning Docs transkribiert:

- Teil-Eigennutzung und M10-Aktivierung/-Portaltexte: `docs/02-data-model.md` und
  `docs/04-web-app-structure.md`;
- Eichfristen und Jahresende-Regel: `docs/12-guards-deadlines.md`;
- Bank-Matching, Gesamtschuld, Guthaben und Identitätskorrektur: `docs/15-bank-matching.md`;
- UVI-Texte, PLZ-Quelle und Registerstatus: `docs/16-uvi.md`;
- Ausführungsstatus: `PLAN.md`.

## Noch nicht im Repository

### Seite 07 — zwei Begleitdateien

Berkay nennt diese Dateien als geliefert, aber sie sind am 11.09.2026 weder im Lokara-Arbeitsbaum
noch an anderer Stelle unter `/Users/berkaybayrak/Desktop` vorhanden:

- `Lokara_Investitionsmodul_Demo.html`
- `AfA-Wizard_Konzept_Entwurf.md`

Ihr Inhalt wird nicht rekonstruiert. Bis die Dateien tatsächlich verfügbar sind, bleibt diese
Nachlieferung offen. Sie sind Entwurfsstände; bei Abweichungen gewinnt Seite 07 für die Demo und
Seite 03 für den AfA-Wizard.

### Rechtsstand-Register — Berkay-Synchronisierung

Lokara ändert das von Berkay gepflegte Register nicht. Die Workspace-Datei
`berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv` ergibt am 11.09.2026 mit einem echten
CSV-Parser **180 Datensätze**: 130 `verify-before-production` und 50 `geprüft`. Berkays Herleitung
„180 Zeilen einschließlich Kopfzeile = 179 Einträge“ ist für diese Datei falsch: sie enthält einen
Zeilenumbruch in einem CSV-Feld und kein abschließendes Newline. Die Datei enthält außerdem noch die
alten Werte in den von Berkay als Zeilen 128/129 bezeichneten W2-Einträgen. Aus der Antwort stehen
deshalb noch aus:

- neue Zeilen `R-UVI-01`, `R-UVI-02` und `R-01-D0-02`;
- Korrektur der bestehenden Zeilen 128 und 129 mit Änderungsdatum 11.09.2026.

Die überholte Prosa-Zahl „51 → 62“ wird nicht verwendet. Maßgeblich bleibt allein der mit einem
CSV-Parser ermittelte Datensatzstand des Registers; die aktuelle Zahl ist kein zweiter Sollwert.

## Keine offene M10-Textfrage

`M10-COPY-01…06` ist vollständig geliefert. M10-R4 ist dadurch nicht mehr copy-blocked. Die
einheitliche numerische HTTP-Statuswahl für Aktivierungsablehnungen bleibt eine technische
R1-Vertragsentscheidung, keine offene Berkay-Textfrage.
