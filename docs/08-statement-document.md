# 08 — The Abrechnung document (formal content)

> **Status: ⏳ spec pending.** This file records the **known gaps** found by reviewing the first
> rendered statement, so they aren't lost. The full layout spec replaces the body below when it lands;
> build from this file, not from a pasted spec.
>
> ⚠️ **Not legal advice.** The requirements below are the well-established formal minimums; confirm the
> specifics with a Fachanwalt/Steuerberater before shipping to real tenants (`docs/07`).

---

## Why this file exists

`docs/03` specifies the **math** in depth; nothing specified the **document**. So the first PDF renders
the engine's output faithfully and is still not an Abrechnung a landlord could send. The math is the
hard part and it's correct — what's missing is document completeness, not new calculation.

## The four formal minimum requirements

Settled BGH case law: a Betriebskostenabrechnung must contain all four.

| # | Requirement | First render |
| --- | --- | --- |
| 1 | **Zusammenstellung der Gesamtkosten** (per cost type) | ✅ |
| 2 | **Angabe + Erläuterung des Verteilerschlüssels** | ✅ — e.g. "Wohnfläche (m²·Tage)" |
| 3 | **Berechnung des Anteils des Mieters** | ✅ — day-weighted, cent-exact |
| 4 | **Abzug der geleisteten Vorauszahlungen** → **Saldo** | ❌ **missing** |

**#4 is the point of the document for the tenant:** advances paid − share owed = **Nachzahlung oder
Guthaben**. The data model already anticipates it (`docs/02`: the statement's Nachzahlung/Guthaben
becomes a `Payment` in the Ledger); it is simply not on the page.

## Two documents from one calculation ⚠️

The first render shows **every party's name and share to everyone**. That is right for the landlord and
**wrong — and a DSGVO problem — for the tenant**.

| Document | Audience | Contents |
| --- | --- | --- |
| **Vermieter-Gesamtübersicht** | landlord (internal) | all parties, full reconciliation — *what the first render already is* |
| **Mieter-Einzelabrechnung** | one tenant (the envelope) | **only that tenant's** share, their advances, their balance. **No other tenant's name or amount.** |

Both derive from the same engine result — this is a rendering split, not a second calculation.

## Also missing from the tenant document

- **Addressee block + date** — the statement is addressed to one tenant (name, address).
- **Reference totals so the share is verifiable** — Gesamtfläche / Gesamteinheiten / Gesamtverbrauch
  alongside the tenant's own value.
- **Heating consumption values** — meter start/end readings (HeizkostenV gives the tenant a right to
  check); wire from `Zähler` data, not fixtures.
- **§556 deadline context** — the 12-month Abrechnungsfrist, and the tenant's Einwendungsfrist.
- **Payment details** — IBAN/reference for a Nachzahlung, or how a Guthaben is settled.
- **Multiple cost types** — the engine handles n; the demo seeds one. See below.

## BetrKV cost-type catalogue (to specify)

`BetrKV §2` enumerates the umlagefähige Betriebskosten (Grundsteuer, Wasser, Abwasser, Aufzug,
Straßenreinigung, Müllbeseitigung, Gebäudereinigung, Gartenpflege, Beleuchtung, Schornsteinreinigung,
Sach-/Haftpflichtversicherung, Hauswart, Gemeinschaftsantenne, Wäschepflege, sonstige Betriebskosten).
Needed from the Notion page: the **canonical list with default allocation keys per type**, and which are
**not** umlagefähig (Instandhaltung, Verwaltung) so the UI can warn rather than silently allocate them.

→ lands in `packages/rules-store` with a `Rechtsstand`, never hardcoded in an engine.

## Open questions the spec must answer

- [ ] Layout of the Mieter-Einzelabrechnung (sections, order, what appears per cost type)
- [ ] Exact **Vorauszahlung → Saldo** block wording and arithmetic
- [ ] Which reference totals accompany each allocation key
- [ ] Heating: how consumption values and the CO₂ split are presented to the tenant
- [ ] Required legal notices (§556 frist, Einwendungsfrist, disclaimer placement)
- [ ] BetrKV cost-type catalogue + default keys + non-umlagefähig flags
- [ ] A **worked example** with real numbers → becomes the golden fixture for the document layer

## Interim framing for the 06.08 pitch

The current PDF is the **landlord's calculation view**, and it's honest to present it as such:

> *"This is the landlord's calculation view — every party, reconciling to the cent. The tenant letter,
> with advance payments and the resulting balance, is the next document off the same engine."*

True, and it reads as roadmap rather than gap. Do **not** present it as the document a tenant receives.
