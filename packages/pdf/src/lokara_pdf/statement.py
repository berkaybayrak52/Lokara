"""The NK + heating/CO₂ statement template (M3 layout, first cut in Phase D).

The engines compute; this layer only formats their results. Every legal output
carries the ``Rechtsstand MM/JJJJ`` stamps of the rules that produced it and
the "tool, not advice" disclaimer (CLAUDE.md). German copy, docs/05 design
tokens, no ad-hoc colors.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from html import escape

from lokara_domain import AllocationKey, MeasurementUnit, cents, format_eur
from lokara_heating_engine import HeatingResult
from lokara_nk_engine import CostItem, NkResult, ShareLine

from .formatting import format_number_de
from .heating_disclosure import co2_grounds, heating_disclosure_html
from .measurement_units import UNIT_SYMBOLS

# (unit_id, tenancy_id) as they appear on result lines; tenancy_id=None is the
# landlord side (vacancy/self-use) of that unit.
PartyKey = tuple[str | None, str | None]

_ALLOCATION_KEY_LABELS: dict[AllocationKey, str] = {
    AllocationKey.AREA: "Wohnfläche (m²·Tage)",
    AllocationKey.PERSONS: "Personenzahl (Personen·Tage)",
    AllocationKey.CONSUMPTION: "Verbrauch",
    AllocationKey.UNITS: "Einheiten (Einheiten·Tage)",
    AllocationKey.DIRECT: "Direktzuordnung",
    AllocationKey.MEA: "Miteigentumsanteile (MEA·Tage)",
}

# Engine weights are fixed-point (m² × 100, MEA × 10000); the statement shows
# the human figure the docs/03 table shows — 18,250 m²·Tage, not 1,825,000.
_WEIGHT_DISPLAY_DIVISORS: dict[AllocationKey, Decimal] = {
    AllocationKey.AREA: Decimal(100),
    AllocationKey.MEA: Decimal(10000),
}

# Unit of the reference total (Gesamtbemessung) per key — docs/08 table. Keys
# absent here are resolved in _reference_total_unit(): CONSUMPTION reads the
# Maßeinheit off the engine result, DIRECT depends on the target.
_REFERENCE_TOTAL_UNITS: dict[AllocationKey, str] = {
    AllocationKey.AREA: "m²·Tage",
    AllocationKey.PERSONS: "Personen·Tage",
    AllocationKey.UNITS: "Einheiten·Tage",
    AllocationKey.MEA: "MEA·Tage",
}

DISCLAIMER = (
    "Dieses Dokument wurde rechtskonform erstellt; es stellt keine Rechts- oder Steuerberatung dar."
)


@dataclass(frozen=True)
class StatementData:
    """Everything the template needs, already computed and labeled.

    ``rechtsstaende`` is one entry per rule version used (deduped, display
    order), each naming the rule *and* carrying its date —
    ``§ 7 Abs. 1 HeizkostenV 03/1989``. The caller resolves the rules, so only
    the caller knows them; ``rechtsstand_entry`` composes an entry from a
    ``ResolvedRule``. A bare date discloses nothing (docs/08 item 6), so the
    footer prints the word ``Rechtsstand`` once and every date after it is named.
    """

    landlord_name: str
    building_label: str
    period_label: str
    nk_result: NkResult
    nk_costs: tuple[CostItem, ...]
    party_labels: Mapping[PartyKey, str]
    rechtsstaende: tuple[str, ...]
    heating_result: HeatingResult | None = None
    heating_cost_label: str = field(default="Heiz- und Warmwasserkosten")


def _display_weight(key: AllocationKey, weight: Decimal) -> Decimal:
    """De-scale an engine weight to the human figure (docs/03).

    The single de-scaling site for both the per-party Bemessung and the
    Gesamtbemessung — two sites drift apart, and integer-comparing tests stay
    green while they do.
    """
    return weight / _WEIGHT_DISPLAY_DIVISORS.get(key, Decimal(1))


def _reference_total_unit(cost: CostItem, consumption_unit: MeasurementUnit | None) -> str | None:
    """Unit of this cost's Gesamtbemessung, or None if none is printed.

    docs/08: DIRECT → a tenancy has a denominator of 1 (noise, no row); DIRECT →
    a unit is day-split inside that unit and does have one, in Tage.

    CONSUMPTION takes the Maßeinheit the engine divided in, read off the result
    (docs/08 → "`MeasurementUnit` travels with the value"). Where the rows
    supplied none the engine resolves None and no denominator is printed at all:
    a guessed unit on a Verbrauchsabrechnung is a defect that reaches a tenant,
    and a unit-free figure in this column invites the renter to assume one.
    """
    if cost.key is AllocationKey.DIRECT:
        return None if cost.direct_tenancy_id is not None else "Tage"
    if cost.key is AllocationKey.CONSUMPTION:
        return None if consumption_unit is None else UNIT_SYMBOLS[consumption_unit]
    return _REFERENCE_TOTAL_UNITS.get(cost.key)


def _key_label(cost: CostItem, consumption_unit: MeasurementUnit | None) -> str:
    """The Umlageschlüssel, with the unit where the key has one (docs/08).

    A figure column whose unit appears only in its denominator is a column the
    renter has to reconstruct. The label names the **unit**, never a device:
    outside the heating column the Maßeinheit does not determine the device —
    m³ is a cold- or a hot-water meter — so a device name here would state a
    fact the data does not carry.
    """
    label = _ALLOCATION_KEY_LABELS[cost.key]
    if cost.key is AllocationKey.CONSUMPTION and consumption_unit is not None:
        return f"{label} ({UNIT_SYMBOLS[consumption_unit]})"
    return label


def _reference_total(
    cost: CostItem, lines: list[ShareLine], consumption_unit: MeasurementUnit | None
) -> str:
    """`· Gesamtbemessung: 36.500 m²·Tage` — the denominator the engine divided
    by, so the tenant can check their share (docs/08, BGH minimum #2/#3).

    The **sum** is de-scaled once; de-scaling per line and summing would
    reintroduce the rounding error the engine avoids (docs/08 → Rounding).

    Figure and unit are joined by a non-breaking space, as ``format_eur`` joins
    the amount and the euro sign.
    """
    unit = _reference_total_unit(cost, consumption_unit)
    if unit is None or not lines:
        return ""
    total = _display_weight(cost.key, sum((line.weight for line in lines), Decimal(0)))
    # <span class="ref-total"> only prevents the figure from being split off its
    # label when the cost header wraps; it inherits .key-label's tokens.
    return (
        ' · <span class="ref-total">Gesamtbemessung: '
        f"{escape(format_number_de(total))} {escape(unit)}</span>"
    )


def _party(labels: Mapping[PartyKey, str], unit_id: str | None, tenancy_id: str | None) -> str:
    label = labels.get((unit_id, tenancy_id))
    if label is not None:
        return label
    if tenancy_id is None:
        return "Leerstand/Eigennutzung → Vermieter"
    return f"{unit_id} / {tenancy_id}"


def _nk_section(data: StatementData) -> str:
    rows: list[str] = []
    # One field today, because `NkInput.consumptions` is one flat tuple shared by
    # every CONSUMPTION cost — "one key, one unit" is literally true (docs/08).
    consumption_unit = data.nk_result.consumption_unit
    for cost in data.nk_costs:
        lines = [line for line in data.nk_result.lines if line.cost_id == cost.cost_id]
        rows.append(
            f'<tr class="cost-row"><td colspan="3">{escape(cost.label)}'
            f'<span class="key-label">Umlageschlüssel: '
            f"{escape(_key_label(cost, consumption_unit))}"
            f"{_reference_total(cost, lines, consumption_unit)}</span></td>"
            f'<td class="num">{escape(format_eur(cost.amount))}</td></tr>'
        )
        for line in lines:
            party = _party(data.party_labels, line.unit_id, line.tenancy_id)
            rows.append(
                "<tr>"
                f'<td class="indent">{escape(party)}</td>'
                f'<td class="num">'
                f"{escape(format_number_de(_display_weight(cost.key, line.weight)))}</td>"
                f"<td></td>"
                f'<td class="num">{escape(format_eur(line.amount))}</td>'
                "</tr>"
            )
    total = format_eur(data.nk_result.total)
    return f"""
  <h2>Betriebskosten</h2>
  <table>
    <thead>
      <tr><th>Kostenart / Partei</th><th class="num">Bemessung</th><th></th>
      <th class="num">Anteil</th></tr>
    </thead>
    <tbody>
      {"".join(rows)}
    </tbody>
    <tfoot>
      <tr><td colspan="3">Summe Betriebskosten (stimmt centgenau mit den
      Gesamtkosten überein)</td><td class="num">{escape(total)}</td></tr>
    </tfoot>
  </table>"""


def _heating_section(data: StatementData) -> str:
    heating = data.heating_result
    if heating is None:
        return ""
    rows = []
    # Resolved once and handed to the disclosure blocks: the same label names a
    # party in the money table, in Block B and in Block C, so a reader can follow
    # one row across all three.
    party_labels = tuple(
        _party(data.party_labels, line.unit_id, line.tenancy_id) for line in heating.lines
    )
    for line, party in zip(heating.lines, party_labels, strict=True):
        rows.append(
            "<tr>"
            f"<td>{escape(party)}</td>"
            f'<td class="num">{escape(format_eur(line.heating_base))}</td>'
            f'<td class="num">{escape(format_eur(line.heating_consumption))}</td>'
            f'<td class="num">{escape(format_eur(line.ww_base))}</td>'
            f'<td class="num">{escape(format_eur(line.ww_consumption))}</td>'
            f'<td class="num">{escape(format_eur(line.total))}</td>'
            "</tr>"
        )

    co2_block = ""
    if heating.co2 is not None:
        co2 = heating.co2
        # § 7 Abs. 3 CO2KostAufG wants the Einstufung *and* its grounds. The
        # grounds line is appended to this block rather than given a surface of
        # its own — same disclosure, one place to read it (docs/08 item 5).
        co2_block = f"""
  <div class="co2">
    <strong>CO₂-Kostenaufteilung (CO2KostAufG, {escape(co2.rechtsstand)}):</strong>
    Emissionsintensität {escape(format_number_de(co2.intensity_kg_per_sqm))} kg CO₂/m²/Jahr
    → Vermieteranteil {co2.landlord_share_percent} %
    ({escape(format_eur(co2.landlord_amount))}, vor der Umlage abgezogen);
    Mieteranteil {escape(format_eur(co2.renter_amount))}.
    {co2_grounds(co2)}
  </div>"""

    notes = []
    if heating.estimated_unit_ids:
        estimated = ", ".join(escape(u) for u in heating.estimated_unit_ids)
        notes.append(
            f"<p class='note'>Fehlende Ablesungen wurden gemäß § 9a HeizkostenV "
            f"geschätzt (Einheiten: {estimated}).</p>"
        )
    if heating.consumption_fallback_to_area:
        notes.append(
            "<p class='note'>Mehr als 25 % der Fläche ohne Ablesung — der "
            "Verbrauchsanteil wurde nach Wohnfläche umgelegt (§ 9a Abs. 2 HeizkostenV).</p>"
        )

    # The footer figure is the Gesamtkosten — *not* the sum of the column above
    # it: the CO₂-Vermieteranteil is deducted before the renter-facing split
    # (§ 7 Abs. 1 CO2KostAufG) and is not a row in this table, so the party
    # shares add up to less. docs/08 → "Heating table footer". One code path for
    # both branches: without a CO₂ split the two figures are equal by
    # construction, and printing them still beats asserting the equality in
    # words — the reader adds the printed numbers, the document claims nothing.
    # Fixed copy, deliberately not derived from ``heating_cost_label`` (that
    # field spells "Heiz- und Warmwasserkosten" → "Gesamtkosten Heiz- und
    # Warmwasserkosten").
    footer_label = "Gesamtkosten Heizung und Warmwasser"
    share_sum = cents(sum(int(line.total) for line in heating.lines))
    reconciliation = f"Summe der oben ausgewiesenen Anteile: {escape(format_eur(share_sum))}."
    if heating.co2 is not None:
        footer_label += " (inkl. CO₂-Vermieteranteil)"
        reconciliation += (
            f" Die Differenz von {escape(format_eur(heating.co2.landlord_amount))} "
            "ist der CO₂-Vermieteranteil; er wird vor der Umlage abgezogen "
            "(§ 7 Abs. 1 CO2KostAufG)."
        )

    total = format_eur(heating.total)
    return f"""
  <h2>{escape(data.heating_cost_label)}</h2>
  <table>
    <thead>
      <tr><th>Partei</th><th class="num">Grundkosten<br>Heizung</th>
      <th class="num">Verbrauch<br>Heizung</th><th class="num">Grundkosten<br>Warmwasser</th>
      <th class="num">Verbrauch<br>Warmwasser</th><th class="num">Summe</th></tr>
    </thead>
    <tbody>
      {"".join(rows)}
    </tbody>
    <tfoot>
      <tr><td colspan="5">{footer_label}<span class="foot-note">{reconciliation}</span></td>
      <td class="num">{escape(total)}</td></tr>
    </tfoot>
  </table>
  {heating_disclosure_html(heating, party_labels)}
  {co2_block}
  {"".join(notes)}"""


def statement_html(data: StatementData) -> str:
    rechtsstaende = " · ".join(escape(r) for r in data.rechtsstaende)
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8" />
<style>
  /* docs/05 design tokens — no ad-hoc colors */
  :root {{
    --color-ink: #18212a;
    --color-green: #1a6558;
    --color-forest: #123f37;
    --color-mint: #e7efeb;
    --color-slate: #5c6a6b;
    --color-paper: #fbfbfa;
  }}
  body {{
    font-family: 'Manrope', 'Helvetica Neue', Arial, sans-serif;
    color: var(--color-ink);
    background: var(--color-paper);
    margin: 0;
    font-size: 10pt;
  }}
  h1, h2, h3 {{
    font-family: 'Montserrat', 'Helvetica Neue', Arial, sans-serif;
    font-weight: 700;
  }}
  h1 {{ font-size: 18pt; margin: 0 0 2mm; }}
  h2 {{ font-size: 12pt; margin: 8mm 0 3mm; color: var(--color-forest); }}
  .band {{ height: 3mm; background: var(--color-green); margin-bottom: 8mm; }}
  .meta {{ color: var(--color-slate); margin: 0 0 6mm; line-height: 1.5; }}
  table {{ width: 100%; border-collapse: collapse; }}
  /* Pagination (docs/08 → 4b): break at the seams, never inside a statement.
     `break-inside: avoid` belongs on the SMALLEST element that is one
     indivisible claim and is wrong on every container above it. A row is one
     claim — a party's label and their figure; split across a sheet, a reader
     gets a figure with no name or a name with no figure. */
  tr {{ break-inside: avoid; }}
  /* A column header separated from its first row leaves a page of unlabelled
     numbers. In the disclosure block the FIRST table is also what gives the
     second's columns their meaning. */
  thead {{ break-after: avoid; }}
  th {{
    background: var(--color-ink); color: var(--color-paper);
    font-weight: 600; text-align: left; padding: 2mm 2.5mm; font-size: 9pt;
  }}
  td {{ padding: 1.8mm 2.5mm; border-bottom: 0.5pt solid var(--color-mint); }}
  td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  td.indent {{ padding-left: 7mm; }}
  tr.cost-row td {{ background: var(--color-mint); font-weight: 600; }}
  /* Tier 1 (docs/05, docs/08): carries BGH minimum #2 and the denominator #3
     rests on. No font-size — it inherits body copy, so `legal-t1-size` holds
     even if body copy moves. Forest Deep on the cost row's Mint is 10,01:1
     (>= 7:1, SC 1.4.6); weight 400 against the row's 600 keeps the label
     secondary without buying that quietness with contrast.
     Comments here render into the document's <style>; keep domain vocabulary
     out of them so text-occurrence gates count the page, not the stylesheet. */
  .key-label {{ font-weight: 400; color: var(--color-forest); margin-left: 3mm; }}
  /* The reference total stays one unbroken phrase when the cost header wraps. */
  .ref-total {{ white-space: nowrap; }}
  tfoot td {{
    font-weight: 700; border-top: 1pt solid var(--color-ink); border-bottom: none;
    /* Keeps the amount on the label's line when the cell has a second line. */
    vertical-align: top;
  }}
  /* Second line of a footer cell: the reconciliation sentence. Tier 1 — it
     reconciles the total a reader adds up. Inherits body copy (no font-size);
     Forest Deep on Paper is 11,32:1 (>= 7:1, SC 1.4.6). Quieter than the footer
     label through weight, not through size or ink. */
  tfoot .foot-note {{
    display: block; font-weight: 400; color: var(--color-forest);
    line-height: 1.4; margin-top: 1.2mm;
  }}
  .co2 {{
    background: var(--color-mint); border-radius: 8px; padding: 4mm;
    margin-top: 4mm; line-height: 1.5;
  }}
  /* Estimation / fallback disclosure. Tier 1: it changes how the printed
     allocation key must be read, so it inherits body copy and takes Forest Deep
     on Paper (11,32:1). line-height 1.5 is the hygiene both tiers owe (>= 1,4);
     it is running prose and is now set at body size. */
  .note {{ color: var(--color-forest); line-height: 1.5; }}
  /* The three heating-disclosure carriers. All tier 1: no font-size, so each
     inherits body copy, and Forest Deep on Paper is 11,32:1 (>= 7:1, SC 1.4.6).
     They sit on Paper rather than on a tinted panel — three stacked slabs under
     the money table would be ornament, not clarity — and they recede below it
     through weight and a hairline rule, never through a lighter ink. Declared
     one selector each, because a grouped rule is not addressable per carrier.
     Keep every comment in this stylesheet English: it ships inside the document
     and the text-occurrence gates count the whole file.
     All three GROW with the number of parties, so none of them may refuse to
     break (docs/08 → 4b): a block that cannot split cannot be laid out beyond
     one sheet, and long before that it strands the page above it and lands the
     justification on a different sheet from the figures it justifies. Splitting
     such a block is normal; stranding it is the defect. `orphans`/`widows` keep
     a lone line of running prose off a sheet on its own. */
  .cost-split {{
    color: var(--color-forest); line-height: 1.5; margin-top: 6mm;
    padding-top: 4mm; border-top: 0.5pt solid var(--color-mint);
    orphans: 2; widows: 2;
  }}
  .basis-table {{
    color: var(--color-forest); line-height: 1.5; margin-top: 6mm;
    padding-top: 4mm; border-top: 0.5pt solid var(--color-mint);
    orphans: 2; widows: 2;
  }}
  .party-change {{
    color: var(--color-forest); line-height: 1.5; margin-top: 6mm;
    padding-top: 4mm; border-top: 0.5pt solid var(--color-mint);
    orphans: 2; widows: 2;
  }}
  /* A heading alone at the foot of a sheet is the same defect at its smallest
     scale, and the cheapest one to prevent. */
  .disclosure-title {{
    font-size: 10.5pt; font-weight: 600; margin: 0 0 2.5mm; break-after: avoid;
  }}
  .cost-split p, .party-change p {{ margin: 0 0 1.5mm; }}
  /* Which rule was applied, then what the rule permits: the second is quieter
     by weight alone, so both stay at the tier-1 pair. */
  .cost-split .rule-line {{ font-weight: 600; margin-top: 3.5mm; }}
  .cost-split .rule-bound {{ font-weight: 400; }}
  .cost-split .formula, .cost-split .pot-figures, .apportionment li {{
    font-variant-numeric: tabular-nums;
  }}
  .cost-split td {{ border-bottom: none; padding: 0.9mm 0; }}
  .cost-split .split-sum td {{
    border-top: 0.5pt solid var(--color-forest); font-weight: 600;
  }}
  .cost-split .pots {{ margin-top: 1.5mm; }}
  .basis-table table {{ margin-bottom: 4mm; }}
  .basis-table th {{
    background: none; color: var(--color-forest); font-size: inherit; font-weight: 600;
    padding: 1.5mm 2.5mm; border-bottom: 0.5pt solid var(--color-forest);
  }}
  .basis-table td {{ padding: 1.5mm 2.5mm; }}
  .basis-table tfoot td {{
    font-weight: 600; border-top: 0.5pt solid var(--color-forest);
  }}
  /* The column table names a money column, its key and its denominator. The
     first column holds the shortest phrases, so it gets just enough width to
     keep them on one line; the key is prose and may wrap. */
  .basis-table .columns th:first-child, .basis-table .columns td:first-child {{ width: 29%; }}
  .basis-table .columns th:last-child, .basis-table .columns td:last-child {{ width: 24%; }}
  /* The one cell in the reference-total column that holds prose instead of a
     figure. Left-aligned and with tabular figures switched off, so it cannot be
     mistaken for a broken number in a column of denominators. */
  .basis-table td .withheld {{
    display: block; text-align: left; font-variant-numeric: normal;
  }}
  /* Both notes sit directly beneath the table they qualify — adjacency is part
     of the rule, not a layout preference. Tier 1, so no font-size and no
     lighter ink: they recede by weight and by the space above them. */
  .basis-table .withheld-note, .basis-table .rounding-note {{
    margin: 0 0 4mm; font-weight: 400;
  }}
  .basis-table .rounding-note {{ margin-bottom: 0; }}
  /* The sentence that says what the list below it is. Separated from the list
     by a break it leaves bare derivation lines on a fresh sheet with nothing
     naming what was apportioned — the same defect the headings are held to,
     one scale down. */
  .apportionment-lead {{ break-after: avoid; }}
  .apportionment {{ margin: 0 0 2mm; padding-left: 5mm; list-style: none; }}
  /* One derivation line is one statement and is never legible in halves. */
  .apportionment li {{ margin-bottom: 0.8mm; break-inside: avoid; }}
  .party-change .caveat {{ margin-top: 2.5mm; }}
  .co2-grounds {{ display: block; margin-top: 2mm; }}
  footer {{
    color: var(--color-slate); font-size: 8pt; border-top: 0.5pt solid var(--color-slate);
    padding-top: 3mm; margin-top: 10mm; line-height: 1.6;
  }}
</style>
</head>
<body>
  <div class="band"></div>
  <h1>Betriebs- und Heizkostenabrechnung</h1>
  <p class="meta">
    {escape(data.building_label)} · Abrechnungszeitraum {escape(data.period_label)}<br />
    Vermieter: {escape(data.landlord_name)}
  </p>
  {_nk_section(data)}
  {_heating_section(data)}
  <footer>
    Rechtsstand: {rechtsstaende} · Erstellt mit Lokara.<br />
    {escape(DISCLAIMER)}
  </footer>
</body>
</html>"""
