# M9-Risiko- und Rechtsentscheidungen (offen)

Dieses Dokument protokolliert offene Rechtsentscheidungen. Es trifft keine Entscheidung über
Aufbewahrung, Löschung oder Anonymisierung.

## Eichfrist-Grenze

Der aktuelle Guard behandelt den berechneten `valid_until`-Tag als noch nicht überschritten
(`today == valid_until` bleibt im Ablauf; erst ein späterer Tag ist überschritten). Ob die
zugrunde liegende Eichfrist rechtlich als letzter gültiger Tag inklusive zu verstehen ist, muss
an MessEG/MessEV-Primärquelle bestätigt werden; diese Implementierung ist keine Rechtsentscheidung.

## Aufbewahrung und Art. 17 DSGVO

| Append-only-Tabelle / Daten | § 147 AO / GoBD-Basis im Checkout | Lösch-/Anonymisierungspfad | Status |
|---|---|---|---|
| `uvi_run` (UVI-Eingaben, Ergebnisse, Mieterbezug) | nicht abschließend belegt | kein implementierter Pfad; rechtliche Aufbewahrungsentscheidung erforderlich | OFFENE LÜCKE |
| `uvi_delivery_event` | nicht abschließend belegt | kein implementierter Pfad | OFFENE LÜCKE |
| `meter_reading`, `monthly_meter_reading`, Quellenlinks | nicht abschließend belegt | Korrektur nur per Nachfolger; kein Art.-17-Pfad | OFFENE LÜCKE |
| `tenancy_delivery_address` | nicht abschließend belegt | kein implementierter Pfad | OFFENE LÜCKE |
| `renter`, `tenancy_party` | nicht abschließend belegt | keine Anonymisierungsroutine dokumentiert | OFFENE LÜCKE |
| `landlord` | nicht abschließend belegt | keine Anonymisierungsroutine dokumentiert | OFFENE LÜCKE |
| `iban_history` | nicht abschließend belegt | zeitliche Nachfolger, aber kein Art.-17-Pfad | OFFENE LÜCKE |
| `email_attempt`, `email_delivery_status_event` | nicht abschließend belegt | kein Lösch-/Anonymisierungspfad dokumentiert | OFFENE LÜCKE |
| `statement_document_archive`, `renter_delivery_artifact` | GoBD/§147 AO als mögliche Grundlage, konkrete Zuordnung offen | unveränderliche Bytes; kein freigegebener Anonymisierungspfad | OFFENE LÜCKE |

Für jede Zeile muss der Eigentümer vor Produktion die gesetzliche Aufbewahrungsfrist, den
Ausnahmetatbestand für Art. 17, die Sperrfrist sowie einen nachweisbaren Lösch- oder
irreversiblen Anonymisierungspfad festlegen. Unlöschbarkeit ohne bestätigte Grundlage bleibt ein
Produktionsblocker.

## Rechtsstand-Register

`berkay-work/Rechtsstand-Register/Rechtsstand-Register.csv` ist in diesem Checkout vorhanden.
Der aktuelle Stand enthält 180 Zeilen, davon 130 mit `verify-before-production`. Die Datei unter
`berkay-work/` wurde nicht geändert.

## Begriff „Discovery-token expansion“

Der Begriff bezeichnet `guard_discovery_source_token(account_id)` und
`_resolve_guard_sources` in `apps/api/src/lokara_api/routers/guards_delivery.py`.
Das Token `account-scope:{account_id}` wird in alle accountbezogenen IDs aus `Unit`,
`RenterDeliveryArtifact`, `Statement`, `Tenancy` und `Meter` aufgelöst. Die offene
Prüfung betrifft die unbeschränkte Expansion und das dadurch mögliche Wachstum
unveränderlicher Wächter-Evidenz. Sie betrifft weder UVI-Support-Codes noch
Authentifizierungstoken. Der Laufzeitbefund bleibt `verify-before-production`;
die Dokumentationskorrektur behebt ihn nicht.
