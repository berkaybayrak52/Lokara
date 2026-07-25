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

from lokara_domain import AllocationKey, format_eur
from lokara_heating_engine import HeatingResult
from lokara_nk_engine import CostItem, NkResult

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

DISCLAIMER = (
    "Dieses Dokument wurde rechtskonform erstellt; es stellt keine Rechts- "
    "oder Steuerberatung dar."
)


@dataclass(frozen=True)
class StatementData:
    """Everything the template needs, already computed and labeled.

    ``rechtsstaende`` are the stamps of every rule version used (deduped,
    display order) — the caller resolves rules, so only the caller knows them.
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


def format_number_de(value: Decimal) -> str:
    """German number formatting for non-money figures (weights, intensities)."""
    is_integral = value == value.to_integral_value()
    grouped = f"{int(value):,}" if is_integral else f"{value.normalize():,f}"
    return grouped.replace(",", "\0").replace(".", ",").replace("\0", ".")


def _party(labels: Mapping[PartyKey, str], unit_id: str | None, tenancy_id: str | None) -> str:
    label = labels.get((unit_id, tenancy_id))
    if label is not None:
        return label
    if tenancy_id is None:
        return "Leerstand/Eigennutzung → Vermieter"
    return f"{unit_id} / {tenancy_id}"


def _nk_section(data: StatementData) -> str:
    rows: list[str] = []
    for cost in data.nk_costs:
        lines = [line for line in data.nk_result.lines if line.cost_id == cost.cost_id]
        rows.append(
            f'<tr class="cost-row"><td colspan="3">{escape(cost.label)}'
            f'<span class="key-label">Umlageschlüssel: '
            f"{escape(_ALLOCATION_KEY_LABELS[cost.key])}</span></td>"
            f'<td class="num">{escape(format_eur(cost.amount))}</td></tr>'
        )
        divisor = _WEIGHT_DISPLAY_DIVISORS.get(cost.key, Decimal(1))
        for line in lines:
            party = _party(data.party_labels, line.unit_id, line.tenancy_id)
            rows.append(
                "<tr>"
                f'<td class="indent">{escape(party)}</td>'
                f'<td class="num">{escape(format_number_de(line.weight / divisor))}</td>'
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
    for line in heating.lines:
        party = _party(data.party_labels, line.unit_id, line.tenancy_id)
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
        co2_block = f"""
  <div class="co2">
    <strong>CO₂-Kostenaufteilung (CO2KostAufG, {escape(co2.rechtsstand)}):</strong>
    Emissionsintensität {escape(format_number_de(co2.intensity_kg_per_sqm))} kg CO₂/m²/Jahr
    → Vermieteranteil {co2.landlord_share_percent} %
    ({escape(format_eur(co2.landlord_amount))}, vor der Umlage abgezogen);
    Mieteranteil {escape(format_eur(co2.renter_amount))}.
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
      <tr><td colspan="5">Summe Heiz- und Warmwasserkosten (inkl. CO₂-Vermieteranteil,
      stimmt centgenau mit den Gesamtkosten überein)</td>
      <td class="num">{escape(total)}</td></tr>
    </tfoot>
  </table>
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
  h1, h2 {{
    font-family: 'Montserrat', 'Helvetica Neue', Arial, sans-serif;
    font-weight: 700;
  }}
  h1 {{ font-size: 18pt; margin: 0 0 2mm; }}
  h2 {{ font-size: 12pt; margin: 8mm 0 3mm; color: var(--color-forest); }}
  .band {{ height: 3mm; background: var(--color-green); margin-bottom: 8mm; }}
  .meta {{ color: var(--color-slate); margin: 0 0 6mm; line-height: 1.5; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{
    background: var(--color-ink); color: var(--color-paper);
    font-weight: 600; text-align: left; padding: 2mm 2.5mm; font-size: 9pt;
  }}
  td {{ padding: 1.8mm 2.5mm; border-bottom: 0.5pt solid var(--color-mint); }}
  td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  td.indent {{ padding-left: 7mm; }}
  tr.cost-row td {{ background: var(--color-mint); font-weight: 600; }}
  .key-label {{ font-weight: 400; color: var(--color-slate); margin-left: 3mm; font-size: 8.5pt; }}
  tfoot td {{
    font-weight: 700; border-top: 1pt solid var(--color-ink); border-bottom: none;
  }}
  .co2 {{
    background: var(--color-mint); border-radius: 8px; padding: 4mm;
    margin-top: 4mm; line-height: 1.5;
  }}
  .note {{ color: var(--color-slate); font-size: 9pt; }}
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
    {rechtsstaende} · Erstellt mit Lokara.<br />
    {escape(DISCLAIMER)}
  </footer>
</body>
</html>"""
