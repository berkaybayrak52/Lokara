"""Gate: the heating footer says what its figure *is*, and never claims that the
column of party amounts adds up to it.

Spec: `docs/08` → "Heating table footer — the figure is the Gesamtkosten, not the
column's sum".

The heating `tfoot` prints the Gesamtkosten (10.300,00 €). The party amounts
above it sum to 10.142,92 €, because the CO₂-Vermieteranteil is deducted before
the renter-facing split (§ 7 Abs. 1 CO2KostAufG) and is not a row in the table.
(That figure was 10.240,00 € until the demo's CO₂ fixture was corrected on
05.08.2026 — `docs/06` → "Scenario 2 — the fuel, the emissions and the CO₂
price". Every assertion below reads both figures off the engine result, so the
re-base moves nothing in this file except this sentence.)
The old wording — "(inkl. CO₂-Vermieteranteil, stimmt centgenau mit den
Gesamtkosten überein)" — is literally true about the *figure* and reads as a
claim about the *column*, which is false. It is also the Betriebskosten footer's
wording verbatim, where the same claim does hold: same sentence, two meanings,
one page.

So this file pins three things:
1. the arithmetic claim stays on the Betriebskosten footer and disappears from
   the heating one — asserted per section, not as "the two strings differ";
2. the required German copy of `docs/08` is present, with both euro figures
   derived from the engine result, never typed in;
3. the arithmetic that motivates all of it — the rendered party amounts sum to
   *less* than the footer figure, by exactly the CO₂-Vermieteranteil. If a
   future change drops the CO₂ deduction (making them equal), that surfaces here
   instead of quietly making the footer's old wording true again.

The fixture is the demo composition — both real engines, rules resolved from the
rules-store. No hand-written `HeatingResult`.
"""

import re
from decimal import Decimal
from html import escape

from lokara_domain import cents, format_eur
from lokara_heating_engine import HeatingResult
from lokara_pdf import StatementData, statement_html
from lokara_pdf.demo import build_demo_statement

# The Betriebskosten footer's claim. True there (the indented party rows do sum
# to the printed figure); false about the heating column.
ARITHMETIC_CLAIM = "stimmt centgenau mit den Gesamtkosten überein"

_NK_HEADING = "<h2>Betriebskosten</h2>"

_NUM_CELL = re.compile(r'<td class="num">(.*?)</td>', re.DOTALL)
_ROW = re.compile(r"<tr>(.*?)</tr>", re.DOTALL)


def _plain(text: str) -> str:
    """NBSP/narrow-NBSP and source line breaks are formatting choices, not part
    of the spec — the template already wraps footer copy mid-sentence, and
    ``scripts/assert_statement_pdf.py`` flattens whitespace the same way.
    """
    return re.sub(r"\s+", " ", text.replace("\xa0", " ").replace("\u202f", " "))


def _eur(value: int) -> str:
    """`format_eur` of an amount, normalised the same way the HTML is."""
    return _plain(format_eur(cents(value)))


def _sections(data: StatementData) -> tuple[str, str]:
    """(Betriebskosten section, heating section) of the rendered statement."""
    html = _plain(statement_html(data))
    heating_heading = f"<h2>{escape(data.heating_cost_label)}</h2>"
    _, found_nk, rest = html.partition(_NK_HEADING)
    nk, found_heating, heating = rest.partition(heating_heading)
    assert found_nk and found_heating, "fixture no longer renders both sections"
    return nk, heating


def _block(section: str, tag: str) -> str:
    match = re.search(rf"<{tag}>(.*?)</{tag}>", section, re.DOTALL)
    assert match is not None, f"no <{tag}> in section"
    return match.group(1)


def _cents_from_de(rendered: str) -> int:
    """'5.657,60 €' -> 565760. Reads the page, not the engine."""
    figure = _plain(rendered).replace("€", "").strip().replace(".", "").replace(",", ".")
    return int((Decimal(figure) * 100).to_integral_value())


def _heating(data: StatementData) -> HeatingResult:
    heating = data.heating_result
    assert heating is not None, "fixture lost its heating section"
    return heating


def test_heating_footer_drops_the_betriebskosten_arithmetic_claim() -> None:
    """The same sentence cannot mean two things on one page. It stays where it is
    true and goes where it is not."""
    nk, heating = _sections(build_demo_statement())

    # The Betriebskosten footer keeps its wording: the claim is true there.
    assert ARITHMETIC_CLAIM in nk
    assert ARITHMETIC_CLAIM not in heating


def test_heating_footer_states_the_gesamtkosten_and_the_co2_difference() -> None:
    """docs/08 → "Required rendered text (heating footer)". Both figures come
    from the engine result; nothing here is typed in."""
    data = build_demo_statement()
    heating = _heating(data)
    co2 = heating.co2
    assert co2 is not None, "the demo fixture carries a CO₂ split"

    share_sum = _eur(sum(int(line.total) for line in heating.lines))
    landlord_co2 = _eur(int(co2.landlord_amount))
    _nk, section = _sections(data)

    assert "Gesamtkosten Heizung und Warmwasser (inkl. CO₂-Vermieteranteil)" in section
    assert f"Summe der oben ausgewiesenen Anteile: {share_sum}" in section
    assert f"Die Differenz von {landlord_co2} ist der CO₂-Vermieteranteil" in section
    assert "vor der Umlage abgezogen (§ 7 Abs. 1 CO2KostAufG)" in section

    # And the word that carried the false implication is gone: a tfoot labelled
    # "Summe <cost>" under a column of amounts means "these, added up".
    assert "Summe Heiz- und Warmwasserkosten" not in section


def test_rendered_heating_shares_are_less_than_the_footer_figure() -> None:
    """The fact the reword exists for: the column really does not add up, and the
    gap is exactly the CO₂-Vermieteranteil. Read off the page, so a renderer bug
    and an engine change both surface."""
    data = build_demo_statement()
    heating = _heating(data)
    co2 = heating.co2
    assert co2 is not None

    _nk, section = _sections(data)
    body_rows = _ROW.findall(_block(section, "tbody"))
    assert len(body_rows) == len(heating.lines)
    # Last numeric cell of each party row is that party's Summe.
    rendered_shares = [_cents_from_de(_NUM_CELL.findall(row)[-1]) for row in body_rows]

    # The page shows what the engine computed...
    assert rendered_shares == [int(line.total) for line in heating.lines]

    footer_figures = _NUM_CELL.findall(_block(section, "tfoot"))
    assert len(footer_figures) == 1, "the footer's amount column carries exactly one figure"
    assert _cents_from_de(footer_figures[0]) == int(heating.total)

    # ...and it is strictly smaller than the footer figure, by the CO₂ share the
    # landlord bears (§ 7 Abs. 1 CO2KostAufG, deducted before the split).
    assert sum(rendered_shares) < int(heating.total)
    assert int(heating.total) - sum(rendered_shares) == int(co2.landlord_amount)
