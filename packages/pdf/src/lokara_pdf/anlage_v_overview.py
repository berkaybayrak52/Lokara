"""German, archive-shaped Anlage-V overview."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from html import escape

# The statement disclaimer names the Betriebs- und Heizkostenabrechnung, which this
# document is not — an Anlage-V overview under § 21 EStG contains no Abrechnung at all.
# This is CLAUDE.md § 6's approved wording, and it is the same sentence the /steuern
# workspace shows, so the two surfaces no longer disagree.
TAX_DISCLAIMER = "Lokara ist ein Werkzeug: rechtskonform, keine Rechts- oder Steuerberatung."


@dataclass(frozen=True, slots=True)
class AnlageVSourceRef:
    """Identity-free, server-produced source summary."""

    kind: str
    count: int
    tax_year: int


@dataclass(frozen=True, slots=True)
class AnlageVOverviewLine:
    label_de: str
    amount_cents: int
    source_refs: tuple[AnlageVSourceRef, ...]

    def __post_init__(self) -> None:
        if not all(isinstance(value, AnlageVSourceRef) for value in self.source_refs):
            raise TypeError("source_refs must contain only AnlageVSourceRef values")


@dataclass(frozen=True, slots=True)
class AnlageVOverviewData:
    title_de: str
    building_label: str
    tax_year: int
    generated_at: datetime
    lines: tuple[AnlageVOverviewLine, ...]
    blockers_de: tuple[str, ...]
    rechtsstand: str
    production_blocked: bool
    disclaimer: str
    verified_test_bundle_id: str | None = None


def _money(amount_cents: int) -> str:
    amount = Decimal(amount_cents) / Decimal(100)
    return f"{amount:,.2f}".replace(",", "\0").replace(".", ",").replace("\0", ".")


def _source_ref_text(source_ref: AnlageVSourceRef) -> str:
    labels = {
        "payment_events": "Zahlungseingänge",
        "cost_events": "Kosten",
        "afa_record": "AfA-Nachweis",
        "tax_calculation": "Berechnung Steuerjahr",
    }
    if source_ref.count < 0:
        raise ValueError("source reference count must not be negative")
    label = labels.get(source_ref.kind)
    if label is None:
        raise ValueError("unsupported structured source reference")
    return f"{label} {source_ref.tax_year} ({source_ref.count})"


def anlage_v_overview_html(data: AnlageVOverviewData) -> str:
    """Render deterministic HTML without resolving live rules or identities."""
    if not data.production_blocked and not data.verified_test_bundle_id:
        raise ValueError("unblocked archive requires a verified test bundle")
    rendered_refs: dict[int, tuple[str, ...]] = {}
    for line in data.lines:
        rendered_refs[id(line)] = tuple(_source_ref_text(ref) for ref in line.source_refs)
    rows = "".join(
        "<tr>"
        f'<th scope="row">{escape(line.label_de)}</th>'
        f"<td>{escape(_money(line.amount_cents))} €</td>"
        f"<td>{escape(', '.join(rendered_refs[id(line)]))}</td>"
        "</tr>"
        for line in data.lines
    )
    blockers = "".join(f"<li>{escape(value)}</li>" for value in data.blockers_de)
    # docs/11 § 3.6: "every overview states the form year and source status"; § 8: no
    # unverified line, account or EXTF parameter is presented as production-ready. The
    # bundle id was checked at the top of this function and then never rendered, so the
    # one document this pipeline can actually produce carried no source status at all.
    if data.verified_test_bundle_id:
        status_text = (
            f"Erzeugt aus reinen Testwerten (Bündel {data.verified_test_bundle_id}). "
            "Anlage-V-Zeilennummern, SKR-Konten und EXTF-Parameter sind nicht verifiziert. "
            "Dieses Dokument ist ein technischer Nachweis und darf nicht beim Finanzamt "
            "eingereicht werden."
        )
    else:
        status_text = (
            "Erzeugt aus den gespeicherten Quellen dieses Kontos. Die unten aufgeführten "
            "Werte sind nicht verifiziert."
        )
    source_status = (
        f'<section class="source-status"><h2>Quellenstatus</h2><p>{escape(status_text)}</p>'
        f"<p>Formularjahr {data.tax_year}</p></section>"
    )
    blocked = (
        f'<section class="blocked"><h2>Export gesperrt</h2><ul>{blockers}</ul></section>'
        if data.production_blocked
        else ""
    )
    generated_iso = data.generated_at.isoformat()
    generated_de = data.generated_at.strftime("%d.%m.%Y, %H:%M Uhr")
    amounts = {line.label_de: line.amount_cents for line in data.lines}
    cold_rent = amounts.get("Kaltmiete")
    advances = amounts.get("Nebenkostenvorauszahlungen")
    costs = amounts.get("Werbungskosten")
    result = amounts.get("Ergebnis")
    reconciliation = ""
    if None not in (cold_rent, advances, costs, result):
        assert cold_rent is not None
        assert advances is not None
        assert costs is not None
        assert result is not None
        if cold_rent + advances - costs != result:
            raise ValueError("Ergebnis stimmt nicht mit der Abstimmung überein")
        reconciliation = (
            '<section class="reconciliation"><h2>Abstimmung</h2>'
            f"<p><strong>Einnahmen gesamt:</strong> {_money(cold_rent + advances)} € "
            f"(Kaltmiete {_money(cold_rent)} € + Nebenkostenvorauszahlungen "
            f"{_money(advances)} €)</p>"
            f"<p>{_money(cold_rent)} € + {_money(advances)} € - {_money(costs)} € "
            f"= {_money(result)} €</p></section>"
        )
    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <title>{escape(data.title_de)}</title>
  <style>
    @page {{ size: A4; margin: 18mm; }}
    :root {{ color: #18212a; background: #fbfbfa; font-family: Arial, sans-serif; }}
    body {{ margin: 0; font-size: 11pt; line-height: 1.45; }}
    h1 {{ font-size: 22pt; margin: 0 0 4mm; }}
    h2 {{ font-size: 13pt; }}
    .meta {{ margin-bottom: 7mm; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom: 1px solid #5c6a6b; padding: 3mm 2mm; text-align: left; }}
    th {{ font-weight: 600; }}
    td:nth-child(2) {{ text-align: right; white-space: nowrap; }}
    .blocked {{ border: 2px solid #a4262c; background: #fbeae9; padding: 4mm; margin-top: 7mm; }}
    .source-status {{
      border: 1px solid #5c6a6b; background: #f2f4f3; padding: 4mm; margin-top: 7mm;
    }}
    footer {{
      border-top: 1px solid #5c6a6b; margin-top: 8mm; padding-top: 4mm;
      font-size: 9pt; color: #5c6a6b;
    }}
  </style>
</head>
<body>
  <main>
    <h1>{escape(data.title_de)}</h1>
    <div class="meta">
      <p><strong>Objekt:</strong> {escape(data.building_label)}</p>
      <p><strong>Steuerjahr {data.tax_year}</strong></p>
      <p><time datetime="{escape(generated_iso)}">Erstellt: {escape(generated_de)}</time></p>
    </div>
    <table><thead><tr><th>Position</th><th>Betrag</th><th>Quellen</th></tr></thead><tbody>{rows}</tbody></table>
    {reconciliation}
    {source_status}
    {blocked}
  </main>
  <footer><p>Rechtsstand {escape(data.rechtsstand)}</p><p>{escape(data.disclaimer)}</p></footer>
</body>
</html>"""
