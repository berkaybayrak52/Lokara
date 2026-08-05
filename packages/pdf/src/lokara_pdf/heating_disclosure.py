"""The Heizkostenabrechnung's disclosure blocks A, B and C.

Spec: ``docs/08-statement-document.md`` → "Heizkostenabrechnung — the heating
table's disclosure", items 1–5, in the rendered form fixed by **4a**. Every
figure here is read off ``HeatingResult``; nothing is recomputed, nothing is
read from the engine *input*, and no legal value is resolved a second time.

Three carriers, one element and one class each, in document order:

* ``.cost-split``  — Block A, the §§ 7/8/9 vertical split of the Gesamtkosten
* ``.basis-table`` — Block B, Umlageschlüssel + Gesamtbemessung + per-party
  Bemessung of each money column
* ``.party-change``— Block C, the § 9b apportionment at a Nutzerwechsel

All three are **tier 1** (docs/05): they inherit body copy and take Forest Deep
on Paper (11,32:1). Where a block has to recede it does so by weight, never by
a lighter ink.

Two rules run through the whole module:

1. **``None`` means "not applied", never "not carried".** A branch that did not
   run prints nothing at all — not ``0``, not ``—``. Printing the warm-water
   split of a building without central warm water, or a Gradtagszahl that
   determined no euro, is a false disclosure.
2. **De-scale once, at the boundary.** ``base_weight_sqm_days_x100`` is ×100
   fixed point: the *sum* is divided by 100 once, never per line, and the
   printed values are rounded by largest remainder so they add up to the
   printed Gesamtbemessung.
"""

from collections.abc import Sequence
from decimal import Decimal
from html import escape

from lokara_domain import Cents, format_eur
from lokara_heating_engine import Co2Result, HeatingLine, HeatingResult, WarmWaterSeparation

from .formatting import display_figure, format_number_de, largest_remainder_display

# Glyphs are copy, not decoration (docs/08 → 4a). Written as escapes: a literal
# U+2212 trips RUF001, and a hyphen in its place turns a deduction into a dash.
MINUS = "\N{MINUS SIGN}"
# Figure and unit are one phrase, as `format_eur` joins the amount and the €.
NBSP = "\N{NO-BREAK SPACE}"

AREA_KEY_LABEL = "Wohnfläche (m²·Tage)"
AREA_UNIT = "m²·Tage"
WARM_WATER_KEY_LABEL = "Erfasster Warmwasserverbrauch (m³)"
CUBIC_METRE = "m³"

# ×100 fixed point → the human figure (docs/03). The heating base Bemessung is
# an area weight, so it carries the same divisor the NK table applies.
_AREA_WEIGHT_DIVISOR = Decimal(100)


class DisclosureDataError(ValueError):
    """A result claims a branch ran but did not carry that branch's operands.

    Raised rather than papered over: `docs/08` requires the wrong branch to be
    unprintable, and a plausible-looking formula built from a missing operand is
    exactly the failure the carried-intermediates contract exists to prevent.
    """


def _required(value: Decimal | None, field: str) -> Decimal:
    if value is None:
        raise DisclosureDataError(f"heating result carries no {field} for the branch it reports")
    return value


def _required_days(value: int | None, field: str) -> int:
    if value is None:
        raise DisclosureDataError(f"heating result carries no {field} for the branch it reports")
    return value


def _num(value: Decimal) -> str:
    return escape(format_number_de(value))


def _eur(amount: Cents) -> str:
    return escape(format_eur(amount))


def _percent(share: Decimal) -> str:
    """`0.7` → `70`. Derived from the resolved rule value on the result, so the
    page can never state a ratio the engine did not apply."""
    return _num(share * 100)


def _with_unit(value: Decimal, unit: str) -> str:
    return f"{_num(value)}{NBSP}{escape(unit)}"


# --- Block A — Aufteilung der Gesamtkosten -----------------------------------


def _amount_row(label: str, amount: Cents, *, css: str = "") -> str:
    row_class = f' class="{css}"' if css else ""
    return f'<tr{row_class}><td>{label}</td><td class="num">{_eur(amount)}</td></tr>'


def _warm_water_separation_lines(separation: WarmWaterSeparation) -> list[str]:
    """§ 9 HeizkostenV. The two branches print different text, and the operands
    come from the resolved rule value the engine used — never a literal here.

    The fallback branch is legally weaker than a measurement and reads as one:
    *nicht gemessen* and *Ersatzwert* say so before the figure appears, and the
    measured branch never prints either word.
    """
    if separation.method == "MEASURED":
        return [
            '<p class="formula">'
            f"Q(WW) = {_num(_required(separation.factor_kwh_per_m3_kelvin, 'Faktor'))} kWh/(m³·K)"
            f" × {_num(_required(separation.volume_m3, 'Volumen'))} m³"
            f" × ({_num(_required(separation.hot_temp_c, 'Warmwassertemperatur'))} °C {MINUS}"
            f" {_num(_required(separation.cold_temp_c, 'Kaltwassertemperatur'))} °C)"
            f" = {_num(separation.q_ww_kwh)} kWh"
            f" von {_num(separation.total_energy_kwh)} kWh Gesamtenergie</p>"
        ]
    return [
        "<p>Warmwasserverbrauch nicht gemessen — Ersatzwert nach § 9 Abs. 2 HeizkostenV:</p>",
        '<p class="formula">'
        f"{_num(_required(separation.area_fallback_kwh_per_sqm_year, 'Ersatzwert'))}"
        " kWh je m² Wohnfläche und Jahr"
        f" × {_num(_required(separation.heated_area_sqm, 'beheizte Fläche'))} m²"
        f" × {_num(Decimal(_required_days(separation.period_days, 'Tage')))}"
        f" von {_num(Decimal(_required_days(separation.reference_year_days, 'Bezugsjahr')))} Tagen"
        f" = {_num(separation.q_ww_kwh)} kWh von {_num(separation.total_energy_kwh)} kWh</p>",
    ]


def cost_split_block(heating: HeatingResult) -> str:
    """Block A — how the Gesamtkosten became the four pots (items 1, 2, 3)."""
    money_rows = [_amount_row("Gesamtkosten Heizung und Warmwasser", heating.total)]
    if heating.co2 is not None:
        money_rows.append(
            _amount_row(
                f"{MINUS} CO₂-Vermieteranteil (§ 7 Abs. 1 CO2KostAufG)",
                heating.co2.landlord_amount,
            )
        )
    # Without a CO₂ split the two figures are equal by construction and both are
    # still printed: the reader sees that no deduction was made, and the page
    # asserts no equality in words (docs/08 → 4a, "Two branch forms").
    money_rows.append(_amount_row("= umlagefähige Kosten", heating.billable_cost, css="split-sum"))

    parts = [
        '<h3 class="disclosure-title">Aufteilung der Gesamtkosten (HeizkostenV)</h3>',
        f'<table class="split">{"".join(money_rows)}</table>',
    ]

    separation = heating.warm_water_separation
    if separation is not None:
        parts.append(
            '<p class="rule-line">§ 9 HeizkostenV — Trennung von Heizung und Warmwasser</p>'
        )
        parts.extend(_warm_water_separation_lines(separation))
        parts.append(
            f'<p class="formula">→ Warmwasser {_eur(heating.ww_pot)}'
            f" · Heizung {_eur(heating.heating_pot)}</p>"
        )

    share = heating.applied_consumption_share
    bounds = heating.split_bounds
    parts.append(
        '<p class="rule-line">§§ 7, 8 HeizkostenV — Grund- und Verbrauchskosten:'
        f" angewendet {_percent(1 - share)}{NBSP}% Grundkosten"
        f" / {_percent(share)}{NBSP}% Verbrauch</p>"
    )
    # What was applied and what the law permits are two facts, printed as two:
    # a share alone says nothing about whether it was lawful.
    parts.append(
        f'<p class="rule-bound">(zulässiger Rahmen:'
        f" {_percent(bounds.min_consumption_share)}{NBSP}%"
        f" bis {_percent(bounds.max_consumption_share)}{NBSP}% Verbrauchskosten,"
        " § 7 Abs. 1 HeizkostenV)</p>"
    )

    pot_rows = [_pot_row("Heizung:", heating.heat_base_pot, heating.heat_cons_pot)]
    # No central warm water → nothing was separated and both pots are 0 by
    # construction; a printed `Warmwasser: Grundkosten 0,00 €` would state a
    # split that does not exist (docs/08 → 4a, correction 4).
    if separation is not None:
        pot_rows.append(_pot_row("Warmwasser:", heating.ww_base_pot, heating.ww_cons_pot))
    parts.append(f'<table class="split pots">{"".join(pot_rows)}</table>')

    return f'<section class="cost-split">{"".join(parts)}</section>'


def _pot_row(label: str, base: Cents, consumption: Cents) -> str:
    return (
        f"<tr><td>{label}</td>"
        f'<td class="pot-figures">Grundkosten {_eur(base)}'
        f" · Verbrauchskosten {_eur(consumption)}</td></tr>"
    )


# --- Block B — Bemessungsgrundlagen ------------------------------------------


def _cells(cells: Sequence[str], *, head: bool = False, numeric_from: int = 1) -> str:
    tag = "th" if head else "td"
    rendered = []
    for index, cell in enumerate(cells):
        css = ' class="num"' if index >= numeric_from else ""
        rendered.append(f"<{tag}{css}>{cell}</{tag}>")
    return f"<tr>{''.join(rendered)}</tr>"


def basis_table_block(
    heating: HeatingResult,
    party_labels: Sequence[str],
    warm_water_display: Sequence[Decimal] | None,
) -> str:
    """Block B — the Umlageschlüssel and Gesamtbemessung of every money column,
    then every party's Bemessung in each of them (items 1 and 2, BGH #2/#3).

    The `Verbrauch Heizung` column is absent from both halves: its measurement
    unit is not carried into the statement (docs/08 → gaps), and a guessed unit
    on a Verbrauchsabrechnung is a defect that reaches a renter. That absence is
    unrelated to a § 9a Abs. 2 fallback and must not be read as one.
    """
    lines = heating.lines
    has_warm_water = heating.warm_water_separation is not None

    area_values = [line.base_weight_sqm_days_x100 for line in lines]
    # The sum is de-scaled once — per-line division and then summing would
    # reintroduce the rounding error the engine avoids (docs/08).
    area_total = display_figure(sum(area_values, Decimal(0)) / _AREA_WEIGHT_DIVISOR)
    area_display = largest_remainder_display(
        [value / _AREA_WEIGHT_DIVISOR for value in area_values], area_total
    )
    area_total_text = _with_unit(area_total, AREA_UNIT)

    def column_row(column: str, key_label: str, total: str) -> str:
        # Only the Gesamtbemessung is a figure; the Umlageschlüssel is prose and
        # stays left-aligned beside it.
        return _cells([column, escape(key_label), total], numeric_from=2)

    column_rows = [column_row("Grundkosten Heizung", AREA_KEY_LABEL, area_total_text)]
    ww_total_text = ""
    if has_warm_water:
        column_rows.append(column_row("Grundkosten Warmwasser", AREA_KEY_LABEL, area_total_text))
        if warm_water_display is not None:
            ww_total_text = _with_unit(sum(warm_water_display, Decimal(0)), CUBIC_METRE)
            column_rows.append(
                column_row("Verbrauch Warmwasser", WARM_WATER_KEY_LABEL, ww_total_text)
            )
        else:
            # § 9a Abs. 2: the area key *was* the applied key for this column, so
            # that is what the row states — and no m³ Bemessung appears anywhere.
            column_rows.append(column_row("Verbrauch Warmwasser", AREA_KEY_LABEL, area_total_text))

    party_head = ["Partei", "Fläche·Tage"]
    if warm_water_display is not None:
        party_head.append("Verbrauch Warmwasser")
    party_rows = []
    for index, label in enumerate(party_labels):
        cells = [escape(label), _num(area_display[index])]
        if warm_water_display is not None:
            cells.append(_with_unit(warm_water_display[index], CUBIC_METRE))
        party_rows.append(_cells(cells))
    total_cells = ["Gesamtbemessung", _num(area_total)]
    if warm_water_display is not None:
        total_cells.append(ww_total_text)

    return f"""<section class="basis-table">
    <h3 class="disclosure-title">Bemessungsgrundlagen</h3>
    <table>
      <thead>{_cells(["Spalte", "Umlageschlüssel", "Gesamtbemessung"], head=True, numeric_from=2)}
      </thead>
      <tbody>{"".join(column_rows)}</tbody>
    </table>
    <table>
      <thead>{_cells(party_head, head=True)}</thead>
      <tbody>{"".join(party_rows)}</tbody>
      <tfoot>{_cells(total_cells)}</tfoot>
    </table>
  </section>"""


# --- Block C — Nutzerwechsel --------------------------------------------------

DEGREE_DAY_CAVEAT = (
    "Gradtagszahlen sind eine anerkannte Konvention (VDI-Promilletabelle), "
    "keine gesetzliche Vorgabe."
)


def _promille_line(label: str, line: HeatingLine) -> str:
    """Never a bare promille: over a partial billing period a unit's parties sum
    to less than 1.000 ‰ and the bare figure would read as an error."""
    return (
        f"<li>{escape(label)}: {_num(line.degree_day_promille)} ‰"
        f" von {_num(line.unit_degree_day_promille_total)} ‰</li>"
    )


def _day_share_line(
    label: str, line: HeatingLine, reading: Decimal | None, share: Decimal | None
) -> str:
    days = f"{_num(Decimal(line.days))} von {_num(Decimal(line.unit_total_days))} Tagen"
    if reading is None or share is None:
        # Without a warm-water Bemessung the m³ operands belong to a column that
        # was not applied; only the day fraction is a fact about this party.
        return f"<li>{escape(label)}: {days}</li>"
    return (
        f"<li>{escape(label)}: {_with_unit(reading, CUBIC_METRE)} × {days}"
        f" = {_with_unit(share, CUBIC_METRE)}</li>"
    )


def party_change_blocks(
    heating: HeatingResult,
    party_labels: Sequence[str],
    warm_water_display: Sequence[Decimal] | None,
) -> str:
    """Block C — one block per unit used by more than one party (item 4).

    The segments are named by the party label the money table already prints:
    `HeatingLine` carries no dates, and taking them from the engine *input*
    alongside the result is the drift docs/08 forbids (4a, correction 1). For
    the same reason the heading names no unit — nothing carries a unit label
    into the statement.
    """
    shows_promille = not heating.heat_fallback_to_area

    units: dict[str, list[int]] = {}
    for index, line in enumerate(heating.lines):
        units.setdefault(line.unit_id, []).append(index)

    blocks = []
    for indexes in units.values():
        if len(indexes) < 2:
            continue
        parts = [
            '<h3 class="disclosure-title">Nutzerwechsel — Aufteilung des erfassten Verbrauchs</h3>',
            "<p>Diese Einheit wurde im Abrechnungszeitraum von mehreren Parteien genutzt.</p>",
        ]
        if shows_promille:
            # § 9a Abs. 2 replaced the consumption key ⇒ the degree-day
            # apportionment determined no euro on the page, and disclosing it
            # would state a method that was not applied (4a, correction 3).
            parts.append(
                "<p>Der für die Einheit erfasste Wärmeverbrauch wurde nach monatlichen"
                " Gradtagszahlen auf die Nutzungszeiträume aufgeteilt:</p>"
            )
            parts.append(
                '<ul class="apportionment">'
                + "".join(
                    _promille_line(party_labels[index], heating.lines[index]) for index in indexes
                )
                + "</ul>"
            )

        # The unit's own reading is the exact sum of its parties' Bemessungen —
        # never carried twice, so the two can never disagree.
        reading = (
            None
            if warm_water_display is None
            else sum((warm_water_display[index] for index in indexes), Decimal(0))
        )
        parts.append(
            "<p>Grundkosten werden nach Tagen aufgeteilt:</p>"
            if reading is None
            else "<p>Grundkosten und Warmwasserverbrauch werden nach Tagen aufgeteilt:</p>"
        )
        parts.append(
            '<ul class="apportionment">'
            + "".join(
                _day_share_line(
                    party_labels[index],
                    heating.lines[index],
                    reading,
                    None if warm_water_display is None else warm_water_display[index],
                )
                for index in indexes
            )
            + "</ul>"
        )
        if shows_promille:
            # The caveat renders wherever a ‰ figure renders, not only in the
            # footer: presenting a convention as law invites a renter to check a
            # statute that does not contain the number. No Rechtsstand stamp —
            # 01/1981 dates the promille table, not § 9b (4a, correction 2).
            parts.append(f'<p class="caveat">{escape(DEGREE_DAY_CAVEAT)}</p>')
        blocks.append(f'<section class="party-change">{"".join(parts)}</section>')
    return "".join(blocks)


# --- item 5's remainder: the § 7 Abs. 3 Berechnungsgrundlagen -----------------


def _einstufung(co2: Co2Result) -> str:
    """The Einstufung as the intensity band actually compared against.

    `Co2Step` carries no ordinal, so a step *number* would be invented; the
    bounds are already shortened by `period_factor` on the result, so nothing is
    multiplied a second time here (§ 5 Abs. 1 S. 4 CO2KostAufG).
    """
    low, high = co2.band_min_inclusive, co2.band_max_exclusive
    unit = "kg CO₂/m²/Jahr"
    if low is not None and high is not None:
        return f"{_num(low)} bis unter {_num(high)} {escape(unit)}"
    if high is not None:
        return f"unter {_num(high)} {escape(unit)}"
    if low is not None:
        return f"ab {_num(low)} {escape(unit)}"
    return ""


def co2_grounds(co2: Co2Result) -> str:
    """§ 7 Abs. 3 CO2KostAufG — the two inputs the intensity was computed from,
    the band they selected, and the amount being split (so the renter can add
    `240,00 + 60,00 = 300,00`). Appended to the existing block, no new surface.
    """
    band = _einstufung(co2)
    einstufung = f" · Einstufung: {band}" if band else ""
    return (
        '<span class="co2-grounds">Berechnungsgrundlagen:'
        f" CO₂-Emissionen des Gebäudes {_with_unit(co2.total_co2_kg, 'kg')}"
        f" · beheizte Fläche {_with_unit(co2.heated_area_sqm, 'm²')}"
        f" → {_with_unit(co2.intensity_kg_per_sqm, 'kg CO₂/m²/Jahr')}"
        f"{einstufung}"
        f" · CO₂-Kosten {_eur(co2.co2_cost)}</span>"
    )


def warm_water_display_weights(heating: HeatingResult) -> list[Decimal] | None:
    """The printed m³ Bemessung per party — the single source Blocks B and C
    both read, so the derivation in C ends at the figure the table in B shows.

    ``None`` when no m³ Bemessung was applied (no central warm water, or § 9a
    Abs. 2 replaced that column's key): not applied is not the same as zero, and
    neither block may print a figure for it.
    """
    if heating.warm_water_separation is None or heating.ww_fallback_to_area:
        return None
    values = [
        _required(line.ww_consumption_weight_m3, "Warmwasserbemessung") for line in heating.lines
    ]
    return largest_remainder_display(values, display_figure(sum(values, Decimal(0))))


def heating_disclosure_html(heating: HeatingResult, party_labels: Sequence[str]) -> str:
    """Blocks A, B and C in document order, directly beneath the money table."""
    warm_water = warm_water_display_weights(heating)
    return "".join(
        (
            cost_split_block(heating),
            basis_table_block(heating, party_labels, warm_water),
            party_change_blocks(heating, party_labels, warm_water),
        )
    )
