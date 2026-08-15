# DWD-Klimafaktoren — Import-Spec für Lokara

**Zweck:** Witterungsbereinigung des Heizverbrauchs für den Vorjahresvergleich nach § 6a Abs. 3 HeizkostenV (Seite 01b, K12).
**Stand:** 26.07.2026 · Format am realen Datensatz verifiziert (Datei `KF_20250101_20251231`, veröffentlicht 16.02.2026)
**Für:** Emir (Implementierung), Berkay (Freigabe)

---

## 1. Quelle

| | |
|---|---|
| Verzeichnis | `https://opendata.dwd.de/climate_environment/CDC/derived_germany/techn/monthly/climate_correction_factor/recent/` |
| Datensatz-ID | `urn:x-wmo:md:de.dwd.cdc::derivgermany-techn-monthly-climate_correction_factor-recent` |
| Version | v22.3 |
| Herausgeber | Deutscher Wetterdienst, Regionales Klimabüro Essen, klima.essen@dwd.de |
| Lizenz | **GeoNutzV** — Quellenangabe Pflicht: `Quelle: Deutscher Wetterdienst` |
| Kosten | keine |
| Abdeckung | ca. 8 200 Zustell-PLZ, ganz Deutschland, ab 01.01.2019 |
| Aktualisierung | **ca. 6 Wochen nach Monatsende.** Beobachtet: Datei für 01.01.–31.12.2025 ist am 16.02.2026 erschienen; Veröffentlichungen liegen regelmäßig zwischen dem 15. und 18. des Monats |

**Definition:** `KF = G(TRY, Potsdam) / G(Ort, Zeitraum)` — Quotient aus den Gradtagen der Referenzstation Potsdam (TRY 2011) und den tatsächlichen Jahresgradtagen der PLZ. Gradtage nach **VDI 3807** aus DWD-Stationsmessdaten (Tagesmittel) plus Regressionsverfahren.
Referenzort ist seit 01.05.2014 **Potsdam** (vorher Würzburg). Alte Würzburg-Faktoren nur auf Anfrage bei klima.essen@dwd.de — für Lokara irrelevant.

**Richtung (Testfall!):** milderes Jahr → weniger Gradtage → **KF > 1** → bereinigter Verbrauch **höher** als der Rohverbrauch. Die Invertierung dieses Verhältnisses ist der klassische Implementierungsfehler und im Ergebnis unsichtbar.

---

## 2. Dateien

Pro Zeitraum liegen drei Dateien vor:

| Datei | Inhalt | Größe |
|---|---|---|
| `KF_<VON>_<BIS>.csv` | Dezimal**punkt** | ~238 KB |
| `KF_<VON>_<BIS>_k.csv` | Dezimal**komma** (seit 04/2023) | ~238 KB |
| `KF_<VON>_<BIS>.xml` | gleiche Daten als XML | ~1,4 MB |

`<VON>`/`<BIS>` im Format `YYYYMMDD`. Es sind **gleitende 12-Monats-Zeiträume**, monatlich versetzt — für ein Kalenderjahr-Abrechnungsjahr wird `KF_YYYY0101_YYYY1231` gebraucht.

**Empfehlung: `KF_<VON>_<BIS>.csv` (Punkt-Variante) importieren**, nicht die `_k`-Variante. Punkt-Dezimaltrennung erspart das Locale-Parsing; die `_k`-Datei existiert für Excel-Nutzer, nicht für Importer.

### XML-Struktur (verifiziert)

```xml
<dataroot generated="2026-2-16T06:17:17">
  <KF_die_letzten_12>
    <KLFK_POLZ>1067</KLFK_POLZ>
    <VON_DATUM>20250101</VON_DATUM>
    <BIS_DATUM>20251231</BIS_DATUM>
    <KLIMAFAKTOR>1.14</KLIMAFAKTOR>
  </KF_die_letzten_12>
  ...
</dataroot>
```

### ⚠️ Falle: führende Null

`KLFK_POLZ` steht **ohne führende Null** — `1067` bedeutet PLZ **01067** (Dresden), `4103` bedeutet **04103** (Leipzig). Beim Import auf 5 Stellen linksbündig mit Nullen auffüllen. Ohne diese Zeile trifft der Lookup für alle PLZ in 0…-Gebieten (Sachsen, Sachsen-Anhalt, Thüringen, Brandenburg) ins Leere und die Bereinigung fällt still aus.

---

## 3. Zieltabelle

```sql
CREATE TABLE klimafaktor (
  plz          CHAR(5)        NOT NULL,   -- 5-stellig, führende Null erhalten
  zeitraum_von DATE           NOT NULL,
  zeitraum_bis DATE           NOT NULL,
  kf           NUMERIC(4,2)   NOT NULL,
  quelle       TEXT           NOT NULL DEFAULT 'DWD CDC v22.3',
  importiert_am TIMESTAMPTZ   NOT NULL DEFAULT now(),
  PRIMARY KEY (plz, zeitraum_von, zeitraum_bis)
);
```

Import ist **idempotent** (UPSERT auf dem Primärschlüssel). Alte Zeiträume werden nie gelöscht — Abrechnungen zurückliegender Jahre müssen reproduzierbar bleiben.

---

## 4. Importer (Referenz, Python)

```python
import csv, io, urllib.request, datetime

BASE = ("https://opendata.dwd.de/climate_environment/CDC/derived_germany/"
        "techn/monthly/climate_correction_factor/recent/")

def import_kf(von: str, bis: str, conn):
    """von/bis im Format YYYYMMDD, z.B. import_kf('20250101','20251231', conn)"""
    url = f"{BASE}KF_{von}_{bis}.csv"
    raw = urllib.request.urlopen(url, timeout=60).read().decode("latin-1")

    rows, seen = [], set()
    for rec in csv.DictReader(io.StringIO(raw), delimiter=";"):
        rec = { (k or "").strip().upper(): (v or "").strip() for k, v in rec.items() }
        plz = rec["PLZ"].zfill(5)                    # <- führende Null (CSV-Spalte heißt PLZ, NICHT KLFK_POLZ)
        kf  = float(rec["KF"].replace(",", "."))     # CSV-Spalte heißt KF, NICHT KLIMAFAKTOR
        if not (0.40 <= kf <= 1.80):                  # Plausibilitätsband (real beobachtetes Min = 0,49 → Puffer)
            raise ValueError(f"KF ausserhalb Band: {plz} = {kf}")
        if plz in seen:
            raise ValueError(f"PLZ doppelt: {plz}")
        seen.add(plz)
        rows.append((plz,
                     datetime.datetime.strptime(rec["DATANF"], "%Y%m%d").date(),  # CSV-Spalte DatAnf
                     datetime.datetime.strptime(rec["DATEND"], "%Y%m%d").date(),  # CSV-Spalte DatEnd
                     kf))

    if len(rows) < 7000:                              # erwartet ~8200
        raise ValueError(f"Nur {len(rows)} Datensaetze — Datei unvollstaendig")

    with conn.cursor() as cur:
        cur.executemany("""
            INSERT INTO klimafaktor (plz, zeitraum_von, zeitraum_bis, kf)
            VALUES (%s,%s,%s,%s)
            ON CONFLICT (plz, zeitraum_von, zeitraum_bis)
            DO UPDATE SET kf = EXCLUDED.kf, importiert_am = now()
        """, rows)
    conn.commit()
    return len(rows)
```

**Verifiziert am 13.08.2026** an der echten Datei `KF_20250101_20251231.csv` (8.234 Datensätze):

- **Kopfzeile:** `DatAnf;DatEnd;PLZ;KF` — ⚠️ die CSV-Spalten heißen **anders als die XML-Felder** (XML: `KLFK_POLZ`, `KLIMAFAKTOR`, `VON_DATUM`, `BIS_DATUM`). Der Importer oben wurde entsprechend auf die CSV-Namen (`PLZ`, `KF`, `DatAnf`→`DATANF`, `DatEnd`→`DATEND`) korrigiert. Wer den XML-Pfad nimmt, benutzt die XML-Namen.
- **Trennzeichen:** `;` (bestätigt). **Encoding:** ASCII (`latin-1` und `utf-8` funktionieren beide). **Dezimaltrenner:** Punkt in der `.csv` (z. B. `1.14`), Komma nur in der `_k.csv`.
- **PLZ ohne führende Null** bestätigt (`1067` = 01067) → `zfill(5)` bleibt Pflicht.
- **KF-Wertebereich real: 0,49 – 1,33.** Das alte Plausibilitätsband ab 0,50 hätte den echten Wert 0,49 abgewiesen und den Import abgebrochen → Untergrenze auf **0,40** gesenkt.
- **Alle 9 Fixtures exakt reproduziert** (01067→1,14 · 01099→1,02 · 01328→0,98 · 01773→0,83 · 02625→1,05 · 03042→1,12 · 04103→1,15 · 04109→1,14 · 06108→1,15).

---

## 5. Test-Fixtures (echte Werte, Zeitraum 01.01.–31.12.2025)

| PLZ | Ort (ungefähr) | KF |
|---|---|---|
| 01067 | Dresden-Innenstadt | **1,14** |
| 01099 | Dresden-Neustadt | **1,02** |
| 01328 | Dresden-Schönfeld | **0,98** |
| 01773 | Altenberg (Erzgebirge) | **0,83** |
| 02625 | Bautzen | **1,05** |
| 03042 | Cottbus | **1,12** |
| 04103 | Leipzig-Zentrum | **1,15** |
| 04109 | Leipzig-Zentrum West | **1,14** |
| 06108 | Halle (Saale) | **1,15** |

Die Spreizung 0,83 bis 1,15 innerhalb weniger Kilometer (Dresden-Innenstadt 1,14 vs. Altenberg 0,83) ist real und kein Datenfehler — Höhenlage. Sie zeigt zugleich, warum eine bundeseinheitliche Pauschale die Bereinigung nicht ersetzen kann.

**Pflicht-Unit-Tests:**

1. `01067` → 1,14 (führende Null korrekt verarbeitet)
2. Datensatzzahl ≥ 7 000
3. Keine PLZ doppelt
4. Alle KF im Band 0,50–1,80
5. Richtungstest: KF > 1 erhöht den bereinigten Verbrauch
6. Zweiter Import derselben Datei ändert keine Zeile (Idempotenz)
7. Fehlende PLZ im Lookup → Vergleich wird **unbereinigt** ausgegeben plus Hinweistext; **niemals** still 1,00 einsetzen

---

## 6. Betrieb

- **Cron im Lokara-Backend**, monatlich am 18., 03:00 Uhr. Nicht früher — DWD veröffentlicht zwischen dem 15. und 18.
- Fehlschlag (404, unvollständige Datei, Plausibilitätsverstoß) → Alert, **kein** stiller Abbruch. Der alte Datenbestand bleibt gültig; ein fehlender Monat ist unkritisch, ein falscher Faktor nicht.
- **Überwachung parallel:** geplante Claude-Aufgabe `dwd-klimafaktoren-monitor` (17. des Monats, 09:00) meldet, wenn eine neue Datei erschienen ist. Sie lädt die Daten **nicht** — sie beobachtet nur das Verzeichnis.
- Rechtsstand-Register: Eintrag `Klimafaktor | DWD CDC v22.3 | § 6a Abs. 3 HeizkostenV / § 82 GEG | Rechtsnatur: Konvention | Prüfen bis: jährlich`.

---

## 7. Quellenangabe im Produkt

Fußzeile des Abrechnungs-PDF, im Block der § 6a-Abs.-3-Informationen:

> Witterungsbereinigung mit Klimafaktoren des Deutschen Wetterdienstes (Referenzort Potsdam).
> Quelle: Deutscher Wetterdienst.
