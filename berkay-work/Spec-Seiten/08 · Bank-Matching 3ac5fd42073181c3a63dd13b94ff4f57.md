# 08 · Bank-Matching

Blockiert: M6
Emir-Prio: 8
Fixtures: BANKMATCH-F01 … BANKMATCH-F13
Nr: 08
Optional: Yes
Phase: 5
Rechtsstand-Einträge: siehe [kanonisches Rechtsstand-Register](../Rechtsstand-Register/Rechtsstand-Register.csv)
Status: Fertig
Ziel-Datei: NEU (Nummer vergibt Emir)
Zuletzt bearbeitet von: 29. Juli 2026 14:15

> **Optional.** Emir wörtlich: *„Lowest priority; this is heuristics, not law. Only write it if you have strong opinions on…"* — bewusst aus Phase 5 herausgenommen und als Zeitpuffer geführt.
> 

> **Ziel-Datei:** NEU — Nummer vergibt Emir beim Transkribieren
> 

> **Fixtures:** `BANKMATCH-F01 …`
> 

> **Blockiert:** M6
> 

---

## 1. Zweck

Ordnet eingehende Kontobewegungen (finAPI AIS) automatisch der offenen Sollstellung eines Mieters zu — für den Vermieter, damit Zahlungseingang, Rückstand und Guthaben ohne manuelles Abhaken stimmen. Reine Zuordnungs-Heuristik; erzeugt keine Buchungen im Rechtssinn, sondern Vorschläge mit Konfidenz.

## 2. Rechtsgrundlage

Das Matching selbst hat **keine** Rechtsgrundlage — es ist durchgehend **[KONVENTION]**. Rechtlich gebunden ist nur, **wie eine erkannte Zahlung auf Forderungen verrechnet wird**:

- **§ 362 BGB** (Erfüllung) — Rechtsstand 07/2026, Gesetz. Vollständige Zahlung tilgt die Forderung.
- **§ 366 Abs. 1 BGB** (Tilgungsbestimmung) — 07/2026, Gesetz. Ein im Verwendungszweck genannter Zeitraum/Zweck ist eine Tilgungsbestimmung des Schuldners und hat **Vorrang** vor jeder Engine-Reihenfolge.
- **§ 366 Abs. 2 BGB** (gesetzliche Reihenfolge ohne Bestimmung) — 07/2026, Gesetz. Fehlt die Bestimmung: fällige vor nicht fälligen, unter mehreren fälligen die **ältere** zuerst → begründet FIFO.
- **§ 367 BGB** (Reihenfolge innerhalb einer Schuld) — 07/2026, Gesetz. Kosten → Zinsen → Hauptforderung. Relevant, sobald Mahnkosten/Verzugszinsen offen sind (Übergabe von Seite 05).

Alles Übrige — Signalgewichte, Schwellen, IBAN-first-Auto-Regel, Float→Cent-Rundung, Komponenten-Split, Text-Normalisierung, IBAN-Lernen — ist **[KONVENTION]**, `verify-before-production`.

## 3. Inputs

**Kontobewegung** (Quelle: Bank via finAPI AIS, echte finAPI-Feldnamen):

| Feld | Typ | Hinweis |
| --- | --- | --- |
| `id` | Integer | Dedupe exakter Re-Importe |
| `accountId` | Integer | Vermieterkonto |
| `amount` | **Float EUR** | Beim Import kaufmännisch auf **Cent** runden: `round(amount·100)`, Dezimal- nicht Binärarithmetik |
| `bankBookingDate` | Datum | maßgeblich für „fällig" (§ 366 Abs. 2) |
| `finapiBookingDate` | Datum | kann in Zukunft liegende Umsätze aufs Importdatum ziehen — **nicht** für fällig verwenden |
| `valueDate` | Datum |  |
| `counterpartIban` | String, **nullable** | Bareinzahlung/manche Institute liefern keine |
| `counterpartName` | String, nullable, max 80 |  |
| `purpose` | String, nullable, max 2000 | Verwendungszweck |
| `endToEndReference` | String, nullable | Rückverknüpfung bei Reversal |
| `counterpartMandateReference` | String, nullable | Rückverknüpfung bei Reversal |
| `bankTransactionCode` / `type` | String, nullable | SEPA-Return-Erkennung |
| `isPotentialDuplicate` | Bool | finAPI flaggt Doubletten selbst → E12 |

**Offene Sollstellung** (Quelle: Lokara-DB **und Seite 01 NK-Nachzahlung**):

| Feld | Typ |
| --- | --- |
| `receivable_id` | String |
| `tenant_id` | String |
| `period` | YYYY-MM |
| `due_date` | Datum, taggenau |
| `expected_cents` | Integer |
| `open_cents` | Integer, ≤ expected |
| `status` | {open, partial, settled} |
| `category` | {Miete, NK-Nachzahlung} |
| Zusammensetzung | `kaltmiete_cents`, `nk_vz_cents`, `heiz_vz_cents`, `garage_cents` (Summe = `expected_cents`) |

**Mieter-Matching-Profil** (Quelle: Vertrag + gelernt):

| Feld | Typ | Hinweis |
| --- | --- | --- |
| `known_ibans[]` | String[] | wächst durch bestätigte Matches; IBAN am Vertrag = **Kann-Feld**, nie Pflicht |
| `payment_code` | String, optional | nur Booster, nie Auto-Auslöser |
| `surname` | String |  |

Alle Beträge Integer-Cent. **Keine Rundung** an irgendeinem Rechenschritt außer dem Float→Cent-Import — exakte Ganzzahlarithmetik.

## 4. Formel

**Schritt 1 — Kanal.** `amount < 0` oder SEPA-Return-Code → Reversal-Pfad (Schritt 6). `amount > 0` → Scoring. `= 0` → ignorieren. `isPotentialDuplicate = true` → Review statt Auto.

**Schritt 2 — Kandidaten.** Je Bewegung: alle Forderungen mit `status ∈ {open, partial}` der Mieter desselben `accountId`.

**Schritt 3 — Signalpunkte** je (Bewegung, Mieter)-Paar **[alle Werte KONVENTION]**:

- `S_iban`: `counterpartIban` ∈ `known_ibans` **und** eindeutig einem Mieter → **+60**; IBAN gehört zu mehreren Mietern (Gemeinschaftskonto) → **+20**; sonst 0.
- `S_amount`: `amount == receivable.open_cents` → **+30**; sonst 0. (Keine Toleranzbänder — Abweichung = Teil-/Überzahlung, kein „ungefähr".)
- `S_ref`: `purpose` enthält `payment_code` → **+15**; sonst wenn `purpose` enthält `surname` → **+10**; sonst 0 (Maximum, nicht additiv).
- `S_e2e`: `endToEndReference`/`counterpartMandateReference` entspricht gespeicherter Referenz → **+15**.
- `S_month`: `purpose` enthält Periodentoken = `receivable.period` → **+5**.

Text-Normalisierung vor Vergleich: lowercase, Sonder-/Leerzeichen entfernen, Code als Teilstring **[KONVENTION]**.

**Schritt 4 — Konfidenz.** `confidence = min(100, S_iban + S_amount + S_ref + S_e2e + S_month)`.

**Schritt 5 — Entscheidung [Schwellen KONVENTION]:**

> **Auto-Match setzt eine eindeutige, bekannte IBAN voraus.** Betrag steuert nur die Verrechnung, nicht die Identität.
> 
- **Auto-Match** ⟺ genau **ein** Mieter mit `S_iban = 60` (eindeutig bekannte IBAN), kein zweiter mit 60.
- Keine bekannte IBAN → höchstens **Needs Review**, rangiert nach Betrag → Code → Name → E2E. Bestätigung **lernt** die IBAN → ab dann Auto.
- Mehrdeutige IBAN (Gemeinschaftskonto) → nie Auto → Review.
- Kein Signal → **Unmatched** (manuell).

**Schritt 6 — Verrechnung** (nach Auto/Bestätigung, in Reihenfolge):

1. Nennt der Verwendungszweck eine Periode/Forderung → diese ist Zielforderung (§ 366 Abs. 1). Sonst FIFO: fällige vor nicht fälligen, ältere zuerst (§ 366 Abs. 2).
2. Innerhalb der Zielforderung: offene Kosten → Zinsen → Hauptforderung (§ 367).
3. `amount == open_cents` → `settled` (§ 362). `amount < open_cents` → Teilzahlung: `open_cents -= amount`, `status = partial`. `amount > open_cents` → Forderung `settled`, Rest `R = amount − open_cents` → nächste Forderung nach (1), wiederholen; kein offener Posten mehr → Rest ins **Guthaben** des Mieters.
4. **Komponenten-Split** je Zahlung: Vollzahlung → Komponenten auf Nennwert. Teilzahlung `P < expected` → `Komp_paid = round(Komp_nominal · P / expected)`, Differenz zur Summe per Largest-Remainder ausgleichen → exakt. `nk_vz_paid` speist die Jahres-Summe der geleisteten NK-VZ. **[KONVENTION: proportional]**

**Reversal-Pfad:** Erkennung über `bankTransactionCode`/`type` (SEPA-Return) **oder** `amount < 0`. Ursprungs-Match über `endToEndReference`/`counterpartMandateReference`, Fallback (IBAN+Betrag+Datum). Zuordnung zurücknehmen, `open_cents` wiederherstellen, `status = open`, Flag „Zahlung zurückgegeben" → Übergabe an Seite 05 (§ 543-Wächter).

## 5. Edge Cases

- **E1** Betrag exakt, keine IBAN + kein Zweck → Review oder Unmatched je Score (F02).
- **E2** IBAN bekannt, Betrag weicht ab → Auto-Match, Teilzahlung (F11).
- **E3** Mehrere Mieter identischer Sollbetrag, kein IBAN/Zweck → Unmatched (F05).
- **E4** `counterpartIban = null` (Bareinzahlung) → IBAN-Signal fällt weg (F09).
- **E5** Negativbetrag / SEPA-Return → Reversal (F06).
- **E6** Rundung — nur beim Float→Cent-Import (F10), sonst keine.
- **E7** Gemeinschaftskonto: eine IBAN → mehrere Mieter → nie Auto (F07).
- **E8** Mieter zahlt von neuer IBAN → IBAN-Signal 0, Rückfall auf Review + Neu-Lernen (Mechanik F13).
- **E9** Vorauszahlung/Dauerauftrag für existierende, nicht fällige Forderung (F08).
- **E10** Teilzahlung → Restforderung + Komponenten-Split (F11).
- **E11** Überzahlung → FIFO + Guthaben (F04).
- **E12** Doppelte Bewegung → `isPotentialDuplicate` → Review, nicht still verwerfen; exakter Re-Import über `id` dedupen.

## 6. Beispielrechnungen

Referenz-Zusammensetzung (sofern nicht anders genannt): Kaltmiete 85000 + NK-VZ 15000 + Heiz-VZ 8000 = **108000 Cent (1.080,00 €)**.

### BANKMATCH-F01 — Clean Auto-Match + Erfüllung

Mieter A (IBAN_A eindeutig bekannt). Forderung 2026-07, `open_cents` 108000. Bewegung: `amount` 108000, IBAN_A, `purpose` „Miete Juli 2026".

- S_iban +60 (eindeutig) → **Auto-Match** (Regel Schritt 5).
- Verrechnung: Zweck nennt Periode 07 = Zielforderung (§ 366 Abs. 1); 108000 == 108000 → `settled` (§ 362); Vollzahlung → Komponenten auf Nennwert.
- **Summenprobe:** 108000 zugeordnet = 108000 gebucht (85000+15000+8000). ✓

### BANKMATCH-F02 — Betrag + Nachname → Review (E1)

Mieter B, keine IBAN gespeichert. Forderung 2026-07 open 108000. Bewegung: `amount` 108000, IBAN unbekannt, `purpose` „Ueberweisung Schulz".

- S_iban 0 → **kein Auto**. S_amount 30 + surname „Schulz" 10 = 40 → **Needs Review**, B Rang 1.
- Bestätigung → IBAN → `B.known_ibans`.
- **Summenprobe:** vor Freigabe 0 zugeordnet. ✓

### BANKMATCH-F04 — Überzahlung, FIFO + Guthaben (E11)

Mieter A, zwei offene Forderungen: 2026-07 open 108000 (älter), 2026-08 open 108000. Bewegung: `amount` 220000, IBAN_A, `purpose` „Miete" (keine Periode).

- S_iban 60 → Auto-Match A. Keine Tilgungsbestimmung → FIFO (§ 366 Abs. 2).
- 2026-07: 220000 − 108000 = **112000** Rest, `settled`.
- 2026-08: 112000 − 108000 = **4000** Rest, `settled`.
- kein offener Posten → Rest 4000 → **Guthaben A = 4000 (40,00 €)**.
- **Summenprobe:** 108000 + 108000 + 4000 = 220000. ✓

### BANKMATCH-F05 — Zwei gleiche Sollbeträge, kein IBAN/Zweck → Unmatched (E3)

Mieter C und D, beide open 2026-07 108000, keine IBAN. Bewegung: `amount` 108000, IBAN unbekannt, `purpose` „Miete".

- C: S_amount 30. D: 30. Keine IBAN → **kein Auto**; bestScore 30 → **Unmatched**, C/D nur schwache Hinweise.
- **Summenprobe:** 0 zugeordnet. ✓

### BANKMATCH-F06 — Rücklastschrift / Reversal (E5)

Vorher F01: 2026-07 `settled`. Bank storniert. Bewegung: SEPA-Return-Code, `amount` −108000, `endToEndReference` = Ursprung.

- Reversal-Pfad. Ursprungs-Match über E2E gefunden.
- Rücknahme: 2026-07 `open_cents` zurück auf 108000, `status = open`, Flag „Zahlung zurückgegeben" → Seite 05 (§ 543).
- **Summenprobe:** gebucht 108000 − storniert 108000 = 0 netto; Forderung wieder offen 108000. ✓

### BANKMATCH-F07 — Gemeinschaftskonto, IBAN → zwei Mieter (E7)

Mieter C (Code LOK-5001) und D, gemeinsame IBAN_J. Beide open 2026-07 108000. Bewegung: `amount` 108000, IBAN_J, `purpose` „LOK-5001 Miete".

- C: S_iban +20 (mehrdeutig) + S_amount 30 + S_ref (Code) 15 = 65. D: +20 + 30 = 50.
- Mehrdeutige IBAN → **nie Auto** → **Needs Review**, C Rang 1, D Rang 2.
- **Summenprobe:** 0 zugeordnet vor Freigabe. ✓

### BANKMATCH-F08 — Vorauszahlung auf existierende, nicht fällige Forderung (E9)

2026-07 bereits `settled`. Forderung 2026-08 open 108000, `due_date` 2026-08-03 (künftig). Bewegung 2026-07-28: `amount` 108000, IBAN_A, `purpose` „Miete August".

- S_iban 60 → **Auto-Match**.
- Verrechnung: Zweck „August" (§ 366 Abs. 1) → Zielforderung 2026-08, obwohl nicht fällig; 108000 == 108000 → `settled`, Kennzeichen „im Voraus gezahlt".
- Existiert keine Forderung für die Periode, wird keine angelegt → Rest ins Guthaben (wie F04).
- **Summenprobe:** 108000 = 108000. ✓

### BANKMATCH-F09 — IBAN null (Bareinzahlung) trotz Code → Review (E4)

Mieter A, Forderung 2026-09 open 108000. Bewegung: `amount` 108000, `counterpartIban` = null, `purpose` „Bareinzahlung Mueller LOK-4711".

- S_iban 0 (null) → **kein Auto**. S_amount 30 + S_ref (Code) 15 = 45 → **Needs Review**, A Rang 1. Keine IBAN lernbar (null).
- **Summenprobe:** 0 zugeordnet vor Freigabe. ✓

### BANKMATCH-F10 — Float→Cent-Import (E6)

finAPI `amount` = 1080.00 (Float) → `round(1080.00·100)` = 108000 Cent. Grenzfall `amount` = 1080.005 → `round(108000.5)` = 108001 (kaufmännisch, Dezimalarithmetik).

- **Summenprobe:** Cent-Betrag konsistent mit Kontosaldo. ✓

### BANKMATCH-F11 — Teilzahlung mit Komponenten-Split (E2/E10)

Zusammensetzung 85000 / 15000 / 8000 = 108000. Zahlung 100000, IBAN_A eindeutig → Auto (Betrag ≠ Soll → Teilzahlung).

- Kaltmiete: round(85000·100000/108000) = round(78703.70) = **78704**
- NK-VZ: round(15000·100000/108000) = round(13888.89) = **13889**
- Heiz-VZ: round(8000·100000/108000) = round(7407.41) = **7407**
- Split-Summe 78704 + 13889 + 7407 = 100000 → exakt, kein Largest-Remainder nötig.
- Restforderung 108000 − 100000 = 8000, `status = partial`. `nk_vz_paid` += 13889.
- **Summenprobe:** zugeordnet 100000 + Rest 8000 = 108000. ✓

### BANKMATCH-F12 — NK-Nachzahlung als Auto-Forderung (Seite-01-Handoff)

Seite 01 liefert für A: Nachzahlung 24500 (245,00 €), `category = NK-Nachzahlung`, `due_date` 2026-09-30. Eingang 2026-09-20, `amount` 24500, IBAN_A, `purpose` „Nachzahlung Nebenkosten 2025".

- S_iban 60 → **Auto-Match**, ohne Code.
- Verrechnung: Zweck = Tilgungsbestimmung (§ 366 Abs. 1) → Zielforderung NK-Nachzahlung, nicht laufende Miete; 24500 == 24500 → `settled` (§ 362); Einzelposten, kein Split.
- **Summenprobe:** 24500 = 24500. ✓

### BANKMATCH-F13 — Erstzahlung ohne Code, Lernen (IBAN-first)

Neuer Mieter E, IBAN **nicht** vorbelegt, kein Code. Erster Eingang 108000, `purpose` „Miete E. Yilmaz".

- S_iban 0 → kein Auto. S_amount 30 + Name „Yilmaz" 10 = 40 → **Needs Review**, E Rang 1.
- Vermieter bestätigt → `counterpartIban` → `E.known_ibans`.
- Folgemonat: IBAN_E bekannt eindeutig → **Auto**, dauerhaft, ohne Code. Variante: IBAN als Kann-Feld am Vertrag erfasst → schon dieser erste Eingang wäre Auto.
- **Summenprobe:** vor Bestätigung 0 zugeordnet. ✓

## 7. Out of Scope

- **Auszahlung** von Guthaben (PIS) — V1 verschoben (nur AIS). Engine markiert Guthaben, zahlt nicht aus.
- **Verzugszinsen-/Mahnkosten-Berechnung** selbst → Seite 05 (§ 543); Seite 08 konsumiert nur deren offene Posten in § 367-Reihenfolge.
- **SEPA-Lastschrifteinzug** durch Lokara — findet nicht statt (Mieter pusht, V1 nur AIS).
- **Ausgaben-/Rechnungs-Kategorisierung** → Rechnungserfassung.
- **Steuerliche Behandlung** von Zahlungseingängen.
- **Objektzuordnung** unterhalb Mieterebene — über `tenant_id → Objekt`, nicht über die Bewegung.
- **Mieterübergreifende Verrechnung/Kontokorrent** — jede Zahlung bleibt einem Mieter zugeordnet.