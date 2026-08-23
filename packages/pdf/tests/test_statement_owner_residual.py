"""Gate: the Eigentümerzeile renders, carries no Quote, and closes the column.

Spec: `docs/08-statement-document.md` → **"Die Eigentümerzeile — always printed,
never a Quote"**, §§ 1-4. Model: `docs/02` → "The Eigentümeranteil is a residual
line, not a party". Rule source: approved `docs/03` § 9.2 and original Page 01
**D12**. Rechtsstand 08/2026. Written before the
template change, **red on purpose**.

**The defect.** The heating money table renders one row per party out of
`HeatingResult.lines`, and the landlord's vacancy share is one of those rows
(`Wohnung B — Leerstand ab 01.07.2025 → Vermieter`). Under Berkay's model the
Eigentümeranteil is **not a party**: it is one structural residual line per
Liegenschaft that exists in every building, including a fully let one, where the
current renderer has no row to print at all. § 1.3 Frage 1: *"Existiert die
Eigentümerzeile immer? → **Ja.** Auch bei 0,00 €, auch ohne Leerstand, auch ohne
Eigennutzung."*

**Why the Quote prohibition is a rendering gate and not a code comment.** The
amount is a **remainder**, not a share. § 1.3 Frage 2: *"Eine gedruckte Quote
würde eine Verteilungsbasis suggerieren, die es nicht gibt."* And it is not
hypothetical — on the demo the quota route and the residual are different
numbers (`09-F07`: 1.858 vs 1.859; the engine fixture: 9.901 vs 9.902), so a
printed percentage would show a base that produces a different figure than the
one next to it.

⚠️ **Scope of the no-percentage assertion: the Eigentümer row, not the page.**
Block C prints `585,0 ‰ von 1.000 ‰` legitimately under § 9b Abs. 2 HeizkostenV,
so a page-wide ban would forbid a required disclosure. `docs/08` § 2 carries the
same correction.

The row/column assertions read every expected figure from the engine result and
every actual figure from the rendered page, the way
`test_statement_party_totals.py` does it. One copy-regression fixture deliberately
pins the demo arithmetic (10.142,92 - 8.859,55 = 1.283,37): those three numbers
are the evidence that ``umlagefähige Kosten`` and ``Gesamtkosten`` are not
interchangeable in the required sentence.
"""

import re
from decimal import Decimal

from lokara_pdf import StatementData, statement_html
from lokara_pdf.demo import build_demo_statement

# Fixed copy — `docs/08` → "Die Eigentümerzeile" § 4. The label is Berkay's own
# word in `08-F21` (*"Eigentümeranteil gesamt (= Gesamtübersicht)"*), so one word
# means one thing across the statement, the summary block and the annex.
OWNER_LABEL = "Eigentümeranteil"

# Required wherever the row renders. Without it a reader who tries to reconstruct
# the row from a Bemessung finds no quota and concludes the page is wrong.
RESIDUAL_SENTENCE = (
    "Der Eigentümeranteil ist der Restbetrag: umlagefähige Heiz- und "
    "Warmwasserkosten abzüglich der Summe der Mieteranteile. Er enthält den auf "
    "Leerstand und Eigennutzung entfallenden Anteil sowie die zeilenweise "
    "Rundungsdifferenz. Er wird nicht aus einer Quote berechnet."
)

# Forbidden **on this row**. `Quote` is the word § 1.3 Frage 2 names; `%` and `‰`
# are the two symbols this document already uses elsewhere; `von` catches the
# `x von y` construction Block B and Block C use for real denominators.
FORBIDDEN_ON_THE_ROW = ("%", "‰", "Quote", "Prozent", " von ")

_TAG = re.compile(r"<[^>]+>")
_ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.DOTALL)
_EUR = re.compile(r"-?\d{1,3}(?:\.\d{3})*,\d{2}\s*€")


def _plain(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\xa0", " ").replace("\u202f", " "))


def _text(html: str) -> str:
    return _plain(_TAG.sub(" ", html))


def _cents_from_de(rendered: str) -> int:
    figure = _plain(rendered).replace("€", "").strip().replace(".", "").replace(",", ".")
    return int((Decimal(figure) * 100).to_integral_value())


def _figures(fragment: str) -> list[int]:
    return [_cents_from_de(match) for match in _EUR.findall(_plain(fragment))]


def _heating_table(data: StatementData, html: str) -> str:
    """The heating money table: from its `<h2>` to the end of that table.

    Sliced by the section heading rather than by an index, so the gate stays
    agnostic about how many tables the document grows later.
    """
    heading = f"<h2>{data.heating_cost_label}</h2>"
    start = html.find(heading)
    assert start >= 0, "the rendered statement carries no heating section"
    end = html.find("</table>", start)
    assert end > start, "the heating section carries no money table"
    return html[start : end + len("</table>")]


def _body_rows(table: str) -> list[str]:
    body = table[table.find("<tbody") : table.find("</tbody>")]
    return _ROW.findall(body)


class TestTheRowRenders:
    """§ 1 — unconditionally, and as the last row of the money table."""

    def test_the_heating_table_carries_an_eigentuemeranteil_row(self) -> None:
        data = build_demo_statement()
        rows = _body_rows(_heating_table(data, statement_html(data)))
        labels = [_text(row).strip() for row in rows]
        assert any(label.startswith(OWNER_LABEL) for label in labels), (
            "the heating table has no Eigentümeranteil row — the residual that "
            "closes every column is unprinted (docs/08 § 1, Seite 01 D12)"
        )

    def test_it_is_the_last_money_row_and_there_is_exactly_one(self) -> None:
        """Last, because it is the reconciling line: the reader adds the rows
        above and the last one closes the column. Exactly one, because § 1.2
        collapses every derived landlord party into a single Liegenschafts-
        Residuum — *"eine Residuumszeile, die es strukturell immer gibt"*."""
        data = build_demo_statement()
        rows = _body_rows(_heating_table(data, statement_html(data)))
        owner_rows = [i for i, row in enumerate(rows) if _text(row).strip().startswith(OWNER_LABEL)]
        assert len(owner_rows) == 1, f"expected one Eigentümeranteil row, found {len(owner_rows)}"
        # Round-4 Block (c), where non-zero, is an audit *subline* directly
        # below this residual rather than another money/allocation row.  The
        # owner residual itself remains the final row with all five money
        # columns; `test_statement_rounding_difference.py` owns the subline.
        following = rows[owner_rows[0] + 1 :]
        assert all(_text(row).strip().startswith("davon Rundungsdifferenz") for row in following), (
            "the owner residual may only be followed by its Block-(c) audit subline"
        )

    def test_the_old_per_unit_landlord_row_is_gone_from_the_heating_table(self) -> None:
        """The vacancy no longer gets a *party* row here. It is still named in
        the Betriebskosten table (which keeps its per-unit landlord party until
        Seite 02 lands in `docs/09`) and in Block C, so nothing is hidden — but
        the heating money table must not show one owner twice.
        """
        data = build_demo_statement()
        html = statement_html(data)
        landlord_label = data.party_labels[("unit-b", None)]
        assert landlord_label not in _text(_heating_table(data, html))
        # …and it is still on the page, in the Betriebskosten table.
        assert landlord_label in _text(html)


class TestTheAmountIsTheResidual:
    """§§ 1 and 4 — the five printed figures are the residual's own, read off
    the engine result rather than typed in."""

    def test_the_row_prints_the_four_blocks_and_their_total(self) -> None:
        data = build_demo_statement()
        heating = data.heating_result
        assert heating is not None
        owner = heating.owner_residual
        rows = _body_rows(_heating_table(data, statement_html(data)))
        printed = _figures(rows[-1])
        assert printed == [
            int(owner.heating_base),
            int(owner.heating_consumption),
            int(owner.ww_base),
            int(owner.ww_consumption),
            int(owner.total),
        ]

    def test_the_printed_row_totals_close_the_column(self) -> None:
        """The reconciliation, read off the page: the renter rows plus the
        Eigentümerzeile are the addends of the umlagefähige Kosten. Before this
        change the column was short by the vacancy share's row, which is exactly
        what the table's own `Summe der oben ausgewiesenen Anteile` sentence
        promises to account for.
        """
        data = build_demo_statement()
        heating = data.heating_result
        assert heating is not None
        rows = _body_rows(_heating_table(data, statement_html(data)))
        row_totals = [_figures(row)[-1] for row in rows]
        assert sum(row_totals) == int(heating.billable_cost)

    def test_the_footers_sum_sentence_counts_the_eigentuemerzeile(self) -> None:
        """`Summe der oben ausgewiesenen Anteile: X` must be the sum of what is
        actually above it. Leaving the residual out of that figure would restate
        the defect the heating-footer section exists to fix."""
        data = build_demo_statement()
        heating = data.heating_result
        assert heating is not None
        table = _heating_table(data, statement_html(data))
        rows = _body_rows(table)
        row_totals = [_figures(row)[-1] for row in rows]
        foot = table[table.find("<tfoot") :]
        # The amount, not "everything up to the next full stop" — German
        # thousands separators *are* full stops, so `[^.]+` would truncate
        # `1.281,10 €` to `1`.
        match = re.search(rf"Summe der oben ausgewiesenen Anteile:\s*({_EUR.pattern})", _text(foot))
        assert match is not None, "the heating footer lost its reconciliation sentence"
        assert _cents_from_de(match.group(1)) == sum(row_totals)


class TestNoQuoteIsPrinted:
    """§ 2 — the amount is a remainder, and a printed quota would imply an
    allocation base that does not exist."""

    def test_the_row_carries_no_percentage_and_no_quota(self) -> None:
        data = build_demo_statement()
        rows = _body_rows(_heating_table(data, statement_html(data)))
        # Found by its label rather than taken as `rows[-1]`, so this fails
        # loudly while the row does not exist instead of quietly passing
        # against whatever the last renter row happens to be.
        owner_row = next((row for row in rows if _text(row).strip().startswith(OWNER_LABEL)), None)
        assert owner_row is not None, "no Eigentümeranteil row to check for a Quote"
        rendered = _text(owner_row)
        for forbidden in FORBIDDEN_ON_THE_ROW:
            assert forbidden not in rendered, (
                f"the Eigentümeranteil row prints {forbidden!r} — the amount is a "
                f"Rest, not a Quote (docs/03 § 9.2; docs/08 § 3.3): {rendered!r}"
            )

    def test_the_promille_disclosure_elsewhere_is_untouched(self) -> None:
        """The counter-assertion that keeps the rule scoped to the row: Block C's
        Gradtagszahlen are a **required** § 9b Abs. 2 disclosure and still print
        a ‰ figure. A page-wide ban would have deleted them."""
        html = statement_html(build_demo_statement())
        assert "‰" in _text(html)


class TestTheRequiredSentence:
    """§ 4 — required copy wherever the row renders."""

    def test_the_residual_sentence_renders(self) -> None:
        html = statement_html(build_demo_statement())
        assert _plain(RESIDUAL_SENTENCE) in _text(html)

    def test_it_renders_once(self) -> None:
        """One statement of one rule. Repeating it under every table is how two
        copies drift into two wordings."""
        html = _text(statement_html(build_demo_statement()))
        assert html.count(_plain(RESIDUAL_SENTENCE)) == 1

    def test_the_demo_sentence_describes_the_billable_residual_not_total_cost(self) -> None:
        """The residual closes the renter-facing, CO₂-adjusted pot.

        It is not ``Gesamtkosten - Mieteranteile``: that would leave the
        landlord's CO₂ share inside the owner residual a second time.
        """
        data = build_demo_statement()
        heating = data.heating_result
        assert heating is not None
        renter_cents = sum(int(line.total) for line in heating.lines)
        owner_cents = int(heating.owner_residual.total)

        assert int(heating.billable_cost) == 1_014_292
        assert renter_cents == 885_942
        assert owner_cents == 128_350
        assert int(heating.billable_cost) - renter_cents == owner_cents
        assert int(heating.total) == 1_030_000
        assert int(heating.total) - renter_cents != owner_cents
