# 08 · Bank-Matching — Nachtrag F03

**Kontext:** Zeile 5 deklariert `BANKMATCH-F01 … BANKMATCH-F13` (13 Fixtures), in §6 waren aber nur 12 ausformuliert — **F03 fehlte**. Als einziger Edge Case ohne Fixture blieb **E12 (Doublette / Re-Import)** übrig. Unten der fehlende F03. Einfügen zwischen F02 und F04.

**Zusätzlich** in §5 den E12-Punkt am Ende ergänzen um die Fixture-Referenz:

> - **E12** Doppelte Bewegung → `isPotentialDuplicate` → Review, nicht still verwerfen; exakter Re-Import über `id` dedupen **(F03)**.

---

### BANKMATCH-F03 — Doublette / exakter Re-Import (E12)

Zwei Mechanismen, die klar getrennt bleiben müssen: der **finAPI-Verdacht** (Mensch entscheidet) und der **bit-identische Re-Import** (still dedupen).

**Fall A — `isPotentialDuplicate` (finAPI-Verdacht).** Mieter A, IBAN_A eindeutig bekannt, Forderung 2026-07 open 108000. Bewegung: `amount` 108000, IBAN_A, `purpose` „Miete Juli", **`isPotentialDuplicate = true`** (finAPI flaggt, weil kurz zuvor gleicher Betrag/Empfänger einging).

- Obwohl S_iban 60 einen Auto-Kandidaten ergäbe: Kanal-Regel Schritt 1 (`isPotentialDuplicate = true`) sticht → **Needs Review statt Auto**. Bewegung wird **nicht still verworfen** — der Vermieter entscheidet.
- Bestätigt der Vermieter „echte zweite Zahlung" → normale Verrechnung; hier zweite Zahlung auf bereits gedeckte Periode → Überzahlung → FIFO/Guthaben (Mechanik wie F04).
- Bestätigt er „Doublette" → Bewegung verworfen, keine Verrechnung, keine Tilgung.
- **Summenprobe:** bis zur Entscheidung 0 zugeordnet; nach „Doublette" 0, nach „echte Zahlung" nach F04-Logik. ✓

**Fall B — exakter Re-Import (`id`-Dedupe).** Dieselbe Bewegung mit **identischem `id`** kommt im nächsten AIS-Abruf erneut (finAPI liefert Überlappungsfenster).

- Dedupe über `id` **vor** Kanal/Scoring → zweiter Datensatz wird **still verworfen**, kein zweites Scoring, keine Doppel-Verrechnung. Kein Review-Eintrag nötig, weil bit-identisch bereits verarbeitet.
- Abgrenzung zu Fall A: gleiche `id` = derselbe Umsatz (Dedupe); `isPotentialDuplicate` = **anderer** Umsatz, der einem früheren ähnelt (Review).
- **Summenprobe:** Forderung bleibt bei genau **einer** Tilgung 108000; kein Doppelabzug. ✓
