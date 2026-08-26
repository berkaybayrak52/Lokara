"""German object overview — its own document type, not a statement.

The renderer takes values. It never recomputes rent, area, a balance or a
state: the server snapshot decided all of them, and a second arithmetic here
would be a second truth on paper (04_Objekt-Dashboard.md OD13).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from html import escape

DOCUMENT_TITLE_DE = "Objektübersicht"
# Neither a Betriebskostenabrechnung nor a legal notice, and it says so.
DOCUMENT_NOTE_DE = (
    "Diese Objektübersicht ist eine interne Zusammenstellung zum genannten "
    "Datenstand. Sie ist keine Betriebskostenabrechnung, kein Kontoauszug und "
    "kein rechtliches Schreiben."
)


@dataclass(frozen=True, slots=True)
class BuildingOverviewKpi:
    label_de: str
    value_de: str


@dataclass(frozen=True, slots=True)
class BuildingOverviewUnit:
    label: str
    state_de: str
    parties_de: str
    area_de: str
    cold_rent_de: str
    balance_de: str


@dataclass(frozen=True, slots=True)
class BuildingOverviewFact:
    text_de: str
    unit_label: str | None


@dataclass(frozen=True, slots=True)
class BuildingOverviewData:
    building_name: str
    address_de: str
    building_type_de: str
    as_of: date
    generated_at: datetime
    kpis: tuple[BuildingOverviewKpi, ...]
    units: tuple[BuildingOverviewUnit, ...]
    facts: tuple[BuildingOverviewFact, ...]


def _de_date(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def building_overview_filename(building_name: str, as_of: date) -> str:
    """`Objektübersicht_<name>_<YYYY-MM-DD>.pdf` with a filesystem-safe name.

    Party names never reach a filename (OD14), only the object's own name.
    """
    cleaned = "".join(
        character if character.isalnum() or character in "-_" else "-"
        for character in building_name.strip()
    ).strip("-")
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return f"Objektübersicht_{cleaned or 'Objekt'}_{as_of.isoformat()}.pdf"


def building_overview_html(data: BuildingOverviewData) -> str:
    """Deterministic A4 HTML for one object snapshot."""
    kpi_cells = "".join(
        f'<div class="kpi"><span class="kpi-label">{escape(kpi.label_de)}</span>'
        f'<span class="kpi-value">{escape(kpi.value_de)}</span></div>'
        for kpi in data.kpis
    )
    unit_rows = "".join(
        "<tr>"
        f'<th scope="row">{escape(unit.label)}</th>'
        f"<td>{escape(unit.state_de)}</td>"
        f"<td>{escape(unit.parties_de)}</td>"
        f'<td class="num">{escape(unit.area_de)}</td>'
        f'<td class="num">{escape(unit.cold_rent_de)}</td>'
        f'<td class="num">{escape(unit.balance_de)}</td>'
        "</tr>"
        for unit in data.units
    )
    if not unit_rows:
        unit_rows = (
            '<tr><td colspan="6">Für dieses Objekt sind noch keine Einheiten erfasst.</td></tr>'
        )
    facts_section = ""
    if data.facts:
        items = "".join(
            f"<li>{escape(fact.text_de)}"
            + (f" · {escape(fact.unit_label)}" if fact.unit_label else "")
            + "</li>"
            for fact in data.facts
        )
        facts_section = f"<section><h2>Hinweise</h2><ul>{items}</ul></section>"

    generated_iso = data.generated_at.isoformat()
    generated_de = data.generated_at.strftime("%d.%m.%Y, %H:%M Uhr")
    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <title>{escape(DOCUMENT_TITLE_DE)} — {escape(data.building_name)}</title>
  <style>
    @page {{
      size: A4;
      margin: 18mm;
      @bottom-right {{ content: counter(page) " / " counter(pages); }}
    }}
    :root {{ color: #18212a; background: #fbfbfa; font-family: Arial, sans-serif; }}
    body {{ margin: 0; font-size: 10.5pt; line-height: 1.45; }}
    h1 {{ font-size: 21pt; margin: 0 0 2mm; }}
    h2 {{ font-size: 12pt; margin: 7mm 0 2mm; }}
    .meta p {{ margin: 0 0 1mm; }}
    .kpis {{ display: flex; gap: 4mm; margin-top: 5mm; }}
    .kpi {{
      flex: 1; border: 1px solid #c9d6d2; border-radius: 2mm; padding: 3mm;
    }}
    .kpi-label {{ display: block; font-size: 8.5pt; color: #5c6a6b; }}
    .kpi-value {{ display: block; font-size: 12pt; font-weight: 600; margin-top: 1mm; }}
    table {{ border-collapse: collapse; width: 100%; }}
    thead {{ display: table-header-group; }}
    tr {{ break-inside: avoid; }}
    th, td {{
      border-bottom: 1px solid #c9d6d2; padding: 2.5mm 2mm;
      text-align: left; vertical-align: top;
    }}
    thead th {{ border-bottom: 1px solid #5c6a6b; font-weight: 600; }}
    .num {{ text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }}
    ul {{ margin: 0; padding-left: 5mm; }}
    footer {{
      border-top: 1px solid #5c6a6b; margin-top: 8mm; padding-top: 3mm;
      font-size: 8.5pt; color: #5c6a6b;
    }}
  </style>
</head>
<body>
  <main>
    <h1>{escape(DOCUMENT_TITLE_DE)}</h1>
    <div class="meta">
      <p><strong>{escape(data.building_name)}</strong></p>
      <p>{escape(data.address_de)}</p>
      <p>{escape(data.building_type_de)}</p>
      <p>Datenstand: {escape(_de_date(data.as_of))}</p>
    </div>
    <div class="kpis">{kpi_cells}</div>
    <section>
      <h2>Einheiten</h2>
      <table>
        <thead>
          <tr>
            <th>Einheit</th><th>Zustand</th><th>Mietpartei</th>
            <th class="num">Fläche</th><th class="num">Kaltmiete</th><th class="num">Saldo</th>
          </tr>
        </thead>
        <tbody>{unit_rows}</tbody>
      </table>
    </section>
    {facts_section}
  </main>
  <footer>
    <p>{escape(DOCUMENT_NOTE_DE)}</p>
    <p><time datetime="{escape(generated_iso)}">Erstellt: {escape(generated_de)}</time></p>
  </footer>
</body>
</html>"""
