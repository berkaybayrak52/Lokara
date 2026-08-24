"""German single-renter document for an archived monthly UVI result."""
# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from html import escape

from .formatting import format_number_de

_MONTHS_DE = (
    "Januar",
    "Februar",
    "März",
    "April",
    "Mai",
    "Juni",
    "Juli",
    "August",
    "September",
    "Oktober",
    "November",
    "Dezember",
)


@dataclass(frozen=True, slots=True)
class UviDocumentBlock:
    heading_de: str
    status: str
    value_kwh: int | None
    reference_kwh: int | None
    delta_kwh: int | None
    percent: Decimal | None
    label_de: str | None
    basis_de: str | None
    attribution_de: str | None
    provenance_de: tuple[str, ...]
    data_quality_flag: str | None


@dataclass(frozen=True, slots=True)
class UviDocumentData:
    title_de: str
    target_month: date
    unit_label: str
    block_a: UviDocumentBlock
    block_b: UviDocumentBlock
    block_c: UviDocumentBlock
    block_d_or_d2: UviDocumentBlock
    legal_risks_de: tuple[str, ...]
    unresolved_conflicts_de: tuple[str, ...]
    rechtsstand: str
    disclaimer: str


def _number(value: int | Decimal) -> str:
    return format_number_de(Decimal(value))


def _block_html(block: UviDocumentBlock) -> str:
    if block.status != "ready" and (block.label_de is None or not block.label_de.strip()):
        raise ValueError("Ein nicht bereiter UVI-Block benötigt eine freigegebene label_de.")
    lines: list[str] = []
    if block.value_kwh is not None:
        lines.append(f"<p><strong>Verbrauch:</strong> {_number(block.value_kwh)} kWh</p>")
    if block.reference_kwh is not None:
        lines.append(f"<p><strong>Vergleichswert:</strong> {_number(block.reference_kwh)} kWh</p>")
    if block.delta_kwh is not None:
        sign = "+" if block.delta_kwh > 0 else ""
        lines.append(f"<p><strong>Abweichung:</strong> {sign}{_number(block.delta_kwh)} kWh</p>")
    if block.percent is not None:
        sign = "+" if block.percent > 0 else ""
        lines.append(f"<p><strong>Prozent:</strong> {sign}{_number(block.percent)} %</p>")
    for value, class_name in (
        (block.label_de, "label"),
        (block.basis_de, "basis"),
        (block.attribution_de, "source"),
    ):
        if value:
            lines.append(f'<p class="{class_name}">{escape(value)}</p>')
    if block.provenance_de:
        items = "".join(f"<li>{escape(item)}</li>" for item in block.provenance_de)
        lines.append(f'<ul class="provenance">{items}</ul>')
    content = "".join(lines)
    return f'<section class="block"><h2>{escape(block.heading_de)}</h2>{content}</section>'


def _notices(heading: str, values: tuple[str, ...]) -> str:
    if not values:
        return ""
    items = "".join(f"<li>{escape(value)}</li>" for value in values)
    return f'<section class="notices"><h2>{escape(heading)}</h2><ul>{items}</ul></section>'


def uvi_document_html(data: UviDocumentData) -> str:
    """Render archive-shaped data only; no rule or source resolution occurs here."""

    month = f"{_MONTHS_DE[data.target_month.month - 1]} {data.target_month.year}"
    month_numeric = f"{data.target_month.month:02d}/{data.target_month.year}"
    blocks = "".join(
        _block_html(block)
        for block in (data.block_a, data.block_b, data.block_c, data.block_d_or_d2)
    )
    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <title>{escape(data.title_de)}</title>
  <style>
    @page {{ size: A4; margin: 18mm; }}
    :root {{ color: #17202a; background: #fff; font-family: Arial, sans-serif; }}
    body {{ margin: 0; font-size: 11pt; line-height: 1.45; }}
    h1 {{ font-size: 22pt; margin: 0 0 8mm; }}
    h2 {{ font-size: 13pt; margin: 0 0 3mm; }}
    p {{ margin: 1.5mm 0; }}
    .meta {{ border-bottom: 1px solid #80909f; padding-bottom: 5mm; margin-bottom: 6mm; }}
    .block, .notices {{ break-inside: avoid; border: 1px solid #c5cdd5; border-radius: 3mm; padding: 5mm; margin: 0 0 5mm; }}
    .label, .basis {{ font-weight: 700; }}
    .source, .provenance {{ color: #34495e; }}
    footer {{ border-top: 1px solid #80909f; margin-top: 7mm; padding-top: 4mm; font-size: 9pt; }}
  </style>
</head>
<body>
  <main>
    <h1>{escape(data.title_de)}</h1>
    <div class="meta"><p><strong>Monat:</strong> {escape(month)} ({month_numeric})</p><p><strong>Einheit:</strong> {escape(data.unit_label)}</p></div>
    {blocks}
    {_notices("Rechtliche Hinweise", data.legal_risks_de)}
    {_notices("Offene Prüfpunkte", data.unresolved_conflicts_de)}
  </main>
  <footer><p>Rechtsstand {escape(data.rechtsstand)}</p><p>{escape(data.disclaimer)}</p></footer>
</body>
</html>"""
