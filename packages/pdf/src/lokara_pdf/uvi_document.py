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
    warm_water: UviDocumentBlock | None = None
    warm_water_block_b: UviDocumentBlock | None = None
    warm_water_block_c: UviDocumentBlock | None = None
    warm_water_block_d2: UviDocumentBlock | None = None
    vermieter_name: str | None = None
    vermieter_strasse: str | None = None
    vermieter_plz_ort: str | None = None
    vermieter_telefon: str | None = None
    vermieter_email: str | None = None
    vermieter_logo: str | None = None
    absenderzeile: str | None = None
    mieter_name: str | None = None
    mieter_strasse: str | None = None
    mieter_plz_ort: str | None = None
    liegenschaft_nr: str | None = None
    nutzeinheit_nr: str | None = None
    objekt_adresse: str | None = None
    naechster_monat: str | None = None
    support_code: str | None = None
    gruss_ort: str | None = None
    heating_prior_year_raw_kwh: int | None = None
    heating_prior_year_raw_delta_kwh: int | None = None
    heating_prior_year_raw_percent: Decimal | None = None
    warm_water_prior_year_raw_kwh: int | None = None
    warm_water_prior_year_raw_delta_kwh: int | None = None
    warm_water_prior_year_raw_percent: Decimal | None = None
    dwd_station: str | None = None


def _number(value: int | Decimal) -> str:
    return format_number_de(Decimal(value))


def _percent_number(value: Decimal) -> str:
    return f"{value:.1f}".replace(".", ",")


def _provenance_text(value: str) -> str:
    if value.startswith("Heizspiegel ") and " · Abrechnungsjahr " in value:
        value = value.replace("Heizspiegel ", "Heizspiegel-Vintage: ", 1)
    if value.startswith(("Zielmonat ", "Vorjahresmonat ")):
        for month_number, month_name in enumerate(_MONTHS_DE, start=1):
            value = value.replace(f"{month_number:02d}/", f"{month_name} ", 1)
    return value


def _block_html(block: UviDocumentBlock) -> str:
    if block.status != "ready" and (block.label_de is None or not block.label_de.strip()):
        raise ValueError("Ein nicht bereiter UVI-Block benötigt eine freigegebene label_de.")
    lines: list[str] = []

    def signed(value: int | Decimal | None) -> str:
        if value is None:
            return "—"
        sign = "+" if value > 0 else ""
        return f"{sign}{_number(value)}"

    lines.append(
        '<table class="consumption"><thead><tr><th>Wert kWh</th><th>Δ kWh</th>'
        "<th>Prozent</th></tr></thead><tbody><tr>"
        f"<td>{escape(_number(block.value_kwh)) if block.value_kwh is not None else '—'}</td>"
        f"<td>{escape(signed(block.delta_kwh))}</td>"
        f"<td>{escape(('+' if block.percent > 0 else '') + _percent_number(block.percent)) if block.percent is not None else '—'} %</td>"
        "</tr></tbody></table>"
    )
    for value, class_name in (
        (block.label_de, "label"),
        (block.basis_de, "basis"),
        (block.attribution_de, "source"),
    ):
        if value:
            lines.append(f'<p class="{class_name}">{escape(value)}</p>')
    if block.provenance_de:
        items = "".join(
            f"<li>{escape(_provenance_text(item))}</li>" for item in block.provenance_de
        )
        lines.append(f'<ul class="provenance">{items}</ul>')
    content = "".join(lines)
    return f'<section class="block"><h2>{escape(block.heading_de)}</h2>{content}</section>'


def _comparison_table(rows: tuple[tuple[str, int | None, int | None, Decimal | None], ...]) -> str:
    rendered = "".join(
        "<tr>"
        f"<td>{escape(label)}</td><td>{'—' if value is None else escape(_number(value))}</td>"
        f"<td>{'—' if delta is None else escape(('+' if delta > 0 else '') + _number(delta))}</td>"
        f"<td>{'—' if percent is None else escape(('+' if percent > 0 else '') + _percent_number(percent))}"
        " %</td></tr>"
        for label, value, delta, percent in rows
    )
    return (
        '<table class="comparison"><thead><tr><th></th><th>Wert kWh</th>'
        "<th>Δ kWh</th><th>Prozent</th></tr></thead><tbody>"
        f"{rendered}</tbody></table>"
    )


def _comparison_audit_html(label: str, block: UviDocumentBlock | None) -> str:
    if block is None:
        return ""
    facts = tuple(
        value for value in (block.label_de, block.basis_de, block.attribution_de) if value
    )
    if not facts and not block.provenance_de:
        return ""
    text = " · ".join(escape(value) for value in facts)
    provenance = " · ".join(escape(_provenance_text(item)) for item in block.provenance_de)
    separator = " · " if text and provenance else ""
    return (
        f'<p class="comparison-audit"><strong>{escape(label)}:</strong> '
        f"{text}{separator}{provenance}</p>"
    )


def _has_source(block: UviDocumentBlock, *needles: str) -> bool:
    values = (
        block.label_de,
        block.basis_de,
        block.attribution_de,
        *block.provenance_de,
    )
    return any(
        needle.casefold() in value.casefold() for value in values if value for needle in needles
    )


def _weather_comparison_label(block: UviDocumentBlock) -> str:
    if _has_source(block, "nicht witterungsbereinigt", "Rohvergleich"):
        return "Vorjahresmonat"
    return (
        "Vorjahresmonat (witterungsbereinigt)"
        if _has_source(block, "Deutscher Wetterdienst", "DWD", "witterungsbereinigt")
        else "Vorjahresmonat"
    )


def _average_comparison_label(block: UviDocumentBlock) -> str:
    if _has_source(block, "Vergleich im Gebäude", "Nutzeinheiten"):
        return "Vergleich im Gebäude"
    return "Vergleich Durchschnittsnutzer"


def _notices(heading: str, values: tuple[str, ...]) -> str:
    if not values:
        return ""
    items = "".join(f"<li>{escape(value)}</li>" for value in values)
    return f'<section class="notices"><h2>{escape(heading)}</h2><ul>{items}</ul></section>'


def uvi_document_html(data: UviDocumentData) -> str:
    """Render archive-shaped data only; no rule or source resolution occurs here."""

    month = f"{_MONTHS_DE[data.target_month.month - 1]} {data.target_month.year}"
    for block in (
        data.block_a,
        data.block_b,
        data.block_c,
        data.block_d_or_d2,
        data.warm_water,
        data.warm_water_block_b,
        data.warm_water_block_c,
        data.warm_water_block_d2,
    ):
        if block is not None and block.status != "ready" and not (block.label_de or "").strip():
            raise ValueError("Ein nicht bereiter UVI-Block benötigt eine freigegebene label_de.")
    sender = " · ".join(
        value
        for value in (data.vermieter_name, data.vermieter_strasse, data.vermieter_plz_ort)
        if value
    )
    weather_label = _weather_comparison_label(data.block_c)
    average_label = _average_comparison_label(data.block_d_or_d2)
    heating_rows = (
        ("Vormonat", data.block_b.reference_kwh, data.block_b.delta_kwh, data.block_b.percent),
        (
            "Vorjahresmonat",
            data.heating_prior_year_raw_kwh,
            data.heating_prior_year_raw_delta_kwh,
            data.heating_prior_year_raw_percent,
        ),
        (
            weather_label,
            data.block_c.reference_kwh,
            data.block_c.delta_kwh,
            data.block_c.percent,
        ),
        (
            average_label,
            data.block_d_or_d2.reference_kwh,
            data.block_d_or_d2.delta_kwh,
            data.block_d_or_d2.percent,
        ),
    )
    warm_block_b = data.warm_water_block_b or data.warm_water
    warm_block_c = data.warm_water_block_c
    warm_block_d2 = data.warm_water_block_d2 or data.warm_water
    warm_rows = (
        None
        if data.warm_water is None
        else (
            (
                "Vormonat",
                warm_block_b.reference_kwh if warm_block_b is not None else None,
                warm_block_b.delta_kwh if warm_block_b is not None else None,
                warm_block_b.percent if warm_block_b is not None else None,
            ),
            (
                "Vorjahresmonat",
                (
                    warm_block_c.reference_kwh
                    if warm_block_c is not None
                    else data.warm_water_prior_year_raw_kwh
                ),
                (
                    warm_block_c.delta_kwh
                    if warm_block_c is not None
                    else data.warm_water_prior_year_raw_delta_kwh
                ),
                (
                    warm_block_c.percent
                    if warm_block_c is not None
                    else data.warm_water_prior_year_raw_percent
                ),
            ),
            (
                "Vergleich Durchschnittsnutzer",
                warm_block_d2.reference_kwh if warm_block_d2 is not None else None,
                warm_block_d2.delta_kwh if warm_block_d2 is not None else None,
                warm_block_d2.percent if warm_block_d2 is not None else None,
            ),
        )
    )
    heating_audit = "".join(
        (
            _comparison_audit_html("Vormonat", data.block_b),
            _comparison_audit_html(weather_label, data.block_c),
            _comparison_audit_html(average_label, data.block_d_or_d2),
        )
    )
    blocks = f'<div class="consumption-box"><div class="accent"></div><div class="box-inner"><h2>Ihre Verbräuche in Kilowattstunden (kWh)</h2><section class="stream"><h2>HEIZUNG</h2><div class="current"><strong>{escape(_number(data.block_a.value_kwh or 0))}</strong> kWh <span>für {escape(month)}</span></div>{_comparison_table(heating_rows)}{heating_audit}</section>'
    if warm_rows is not None and data.warm_water is not None:
        warm_audit = "".join(
            (
                _comparison_audit_html("Vormonat", data.warm_water_block_b),
                _comparison_audit_html("Vorjahresmonat", data.warm_water_block_c),
                _comparison_audit_html("Vergleich Durchschnittsnutzer", data.warm_water_block_d2),
            )
        )
        blocks += f'<section class="stream warm"><h2>WARMWASSER</h2><div class="current"><strong>{escape(_number(data.warm_water.value_kwh or 0))}</strong> kWh <span>für {escape(month)}</span></div>{_comparison_table(warm_rows)}{warm_audit}</section>'
    blocks += "</div></div>"
    notes = " ".join(
        block.label_de
        for block in (data.block_a, data.block_b, data.block_c, data.block_d_or_d2, data.warm_water)
        if block is not None and block.label_de
    )
    credit_parts: list[str] = []
    if _has_source(data.block_d_or_d2, "Heizspiegel", "co2online"):
        credit_parts.append(
            "Vergleichswerte auf Basis des bundesweiten Heizspiegels gelten ausschließlich für den Vergleich Durchschnittsnutzer, © co2online gemeinnützige GmbH – heizspiegel.de."
        )
    if _has_source(data.block_c, "Deutscher Wetterdienst", "DWD"):
        weather_credit = "Die DWD-Gradtagszahlen gelten ausschließlich für den witterungsbereinigten Vorjahresvergleich."
        if data.dwd_station:
            weather_credit += f" Station {data.dwd_station}."
        credit_parts.append(weather_credit)
    credit_parts.append(f"Rechtsstand {data.rechtsstand}.")
    credit = " ".join(credit_parts)
    return f"""<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <title>{escape(data.title_de)}</title>
  <style>
    @page {{ size: 210mm 297mm; margin: 0; }}
    html, body {{ margin: 0; padding: 0; background: #fff; color: #1a1d1f; font-family: Manrope, Arial, sans-serif; }}
    .page {{ box-sizing: border-box; width: 100%; min-height: 257mm; display: flex; flex-direction: column; gap: 1.2mm; }}
    .letterhead, .recipient-row {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 10mm; flex-shrink: 0; }}
    .letterhead {{ gap: 12mm; min-height: 18mm; }} .sender {{ text-align: right; font-size: 7.2pt; line-height: 1.25; color: #5c6a6b; }} .sender strong {{ color: #1a1d1f; }}
    .logo {{ width: 46mm; height: 11mm; border: .3mm dashed #cdcfD1; display: flex; align-items: center; justify-content: center; font-size: 7pt; color: #9aa0a6; }} .logo img {{ max-width: 44mm; max-height: 10mm; }}
    .recipient-row {{ min-height: 26mm; }} .recipient {{ width: 82mm; }} .sender-line {{ font-size: 6.2pt; letter-spacing: .06em; color: #5c6a6b; border-bottom: .3mm solid #e3e5e7; padding-bottom: .6mm; }} .recipient-address {{ margin-top: 1mm; font-size: 8.5pt; line-height: 1.3; }}
    .unit-box {{ width: 66mm; border: .3mm solid #e3e5e7; border-radius: 1mm; padding: 2mm 3mm; font-size: 7.4pt; }} .unit-box h2 {{ font-size: 6.2pt; letter-spacing: .08em; color: #5c6a6b; margin: 0 0 1mm; }} .unit-box p {{ display: flex; justify-content: space-between; margin: .7mm 0; }}
    h1 {{ font-size: 12.5pt; margin: 0; line-height: 1.25; }} .intro {{ margin: 1.5mm 0 0; font-size: 8.4pt; line-height: 1.45; color: #5c6a6b; }}
    .consumption-box {{ border: .3mm solid #e3e5e7; border-radius: 1.5mm; flex-shrink: 0; }} .accent {{ height: 1mm; background: #1a6558; }} .box-inner {{ padding: 1.5mm 4mm 1.8mm; }} .box-inner > h2 {{ font-size: 8pt; margin: 0; }} .stream {{ margin-top: 1.5mm; }} .stream.warm {{ margin-top: 2mm; padding-top: 1.5mm; border-top: .3mm solid #e3e5e7; }} .stream h2 {{ font-size: 6.8pt; letter-spacing: .12em; color: #1a6558; margin: 0; }} .current {{ margin-top: .5mm; font-size: 8.5pt; color: #5c6a6b; }} .current strong {{ font-size: 12pt; color: #1a1d1f; }} .current span {{ font-size: 7pt; color: #5c6a6b; }}
    .comparison {{ width: 100%; margin-top: .8mm; border-collapse: collapse; font-size: 7.5pt; line-height: 1.2; }} .comparison th, .comparison td {{ padding: .65mm 0; border-bottom: .25mm solid #eff1f2; text-align: right; white-space: nowrap; }} .comparison th:first-child, .comparison td:first-child {{ text-align: left; color: #5c6a6b; width: 100%; }} .comparison th {{ font-size: 6pt; letter-spacing: .04em; color: #5c6a6b; }} .comparison td:not(:first-child) {{ font-weight: 600; }} .comparison td:last-child {{ color: #1a6558; font-weight: 700; }} .comparison-audit {{ font-size: 5.7pt; line-height: 1.2; color: #5c6a6b; margin: .45mm 0; }}
    .credit, .disclaimer, .next {{ flex-shrink: 0; color: #5c6a6b; max-width: 160mm; }} .note {{ font-size: 7.4pt; color: #5c6a6b; margin: 1mm 0; }} .credit {{ font-size: 7pt; line-height: 1.45; margin: 0; }} .disclaimer {{ font-style: italic; font-size: 7.4pt; line-height: 1.45; margin: 0; }} .next {{ font-size: 9pt; color: #5c6a6b; margin: 0; }}
    .notices {{ font-size: 6.5pt; line-height: 1.2; }} .notices h2 {{ font-size: 7.2pt; margin: 0; }} .notices ul {{ margin: .4mm 0; padding-left: 4mm; }} .questions {{ padding-top: 1mm; border-top: .3mm solid #e3e5e7; flex-shrink: 0; }} .questions h2 {{ font-size: 8pt; margin: 0; }} .contacts {{ display: flex; gap: 8mm; margin-top: .6mm; font-size: 7.4pt; line-height: 1.25; }} .contacts span {{ color: #5c6a6b; }} .greeting {{ font-size: 7.5pt; line-height: 1.25; margin-top: .8mm; }} .lokara-footer {{ margin-top: auto; padding-top: 1mm; font-size: 6.2pt; letter-spacing: .1em; color: #5c6a6b; }}
  </style>
</head>
<body>
  <section class="page">
    <div class="letterhead"><div class="logo">{escape(data.vermieter_logo or "Vermieter_Logo")}</div><div class="sender"><strong>{escape(data.vermieter_name or "—")}</strong><br>{escape(data.vermieter_strasse or "—")}<br>{escape(data.vermieter_plz_ort or "—")}<br>{escape(data.vermieter_telefon or "—")}<br>{escape(data.vermieter_email or "—")}</div></div>
    <div class="recipient-row"><div class="recipient"><div class="sender-line">{escape(data.absenderzeile or sender)}</div><div class="recipient-address">{escape(data.mieter_name or "—")}<br>{escape(data.mieter_strasse or "—")}<br><span>{escape(data.mieter_plz_ort or "—")}</span></div></div><div class="unit-box"><h2>DATEN ZUR NUTZEINHEIT</h2><p><span>Liegenschaft-Nr.</span><strong>{escape(data.liegenschaft_nr or "—")}</strong></p><p><span>Nutzeinheit-Nr.</span><strong>{escape(data.nutzeinheit_nr or "—")}</strong></p><p><span>Wohnung / Stockwerk</span><strong>{escape(data.unit_label)}</strong></p></div></div>
    <div><h1>Ihre Verbrauchsinformation für {escape(month)} </h1><p class="intro">Nach § 6a Heizkostenverordnung informieren wir Sie monatlich über Ihren Verbrauch in der Liegenschaft {escape(data.objekt_adresse or "—")}.</p></div>
    {blocks}{f'<p class="note">{escape(notes)}</p>' if notes else ""}
    {_notices("Rechtliche Hinweise", data.legal_risks_de)}{_notices("Offene Prüfpunkte", data.unresolved_conflicts_de)}
    <p class="credit">{escape(credit)}</p><p class="disclaimer">{escape(data.disclaimer)} Verbrauchsindikation; die Jahresabrechnung kann abweichen.</p><p class="next">Ihre nächste Verbrauchsinformation erhalten Sie im {escape(data.naechster_monat or "—")}.</p>
    <div class="questions"><h2>Sie haben Fragen?</h2><div class="contacts"><div><span>Telefon</span><br><strong>{escape(data.vermieter_telefon or "—")}</strong></div><div><span>E-Mail</span><br><strong>{escape(data.vermieter_email or "—")}</strong></div><div><span>Vorgangsnummer</span><br><strong>{escape(data.support_code or "—")}</strong></div></div></div>
    <div class="greeting"><div>{escape(data.gruss_ort or "—")}</div><div>Mit freundlichen Grüßen</div><div><strong>{escape(data.vermieter_name or "—")}</strong></div></div><div class="lokara-footer">Erstellt mit Lokara</div>
  </section>
</body>
</html>"""
