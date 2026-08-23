"""Red gate for Round-4 Block (c) on the statement.

Spec: ``docs/03-nk-heating-engines.md`` § 1.1 and
``docs/08-statement-document.md`` → "Die Eigentümerzeile" § 5a.  Block (c)
is an audit subline of the already printed owner residual.  It is not a fifth
heating pot and not a new allocation row.
"""

import re
from dataclasses import replace

from lokara_domain import cents
from lokara_pdf import StatementData, statement_html
from lokara_pdf.demo import build_demo_statement

OWNER_LABEL = "Eigentümeranteil"
ROUNDING_LABEL = "davon Rundungsdifferenz"

_TAG = re.compile(r"<[^>]+>")
_ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.DOTALL)
_EUR = re.compile(r"-?\d{1,3}(?:\.\d{3})*,\d{2}\s*€")


def _plain(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ").replace("\u202f", " "))


def _text(value: str) -> str:
    return _plain(_TAG.sub(" ", value))


def _heating_rows(data: StatementData, html: str) -> list[str]:
    heading = f"<h2>{data.heating_cost_label}</h2>"
    start = html.find(heading)
    assert start >= 0, "the rendered statement carries no heating section"
    table_end = html.find("</table>", start)
    assert table_end > start, "the heating section carries no money table"
    table = html[start : table_end + len("</table>")]
    body = table[table.find("<tbody") : table.find("</tbody>")]
    return _ROW.findall(body)


def _rounding_fixture() -> StatementData:
    """The rendered value is carried by the engine result; PDF must not derive it.

    The canonical demo has a zero difference.  Replacing just this audit field
    gives the renderer a deterministic non-zero Block-(c) case while keeping
    every owner-residual money column fixed for the regression below.
    """
    data = build_demo_statement()
    heating = data.heating_result
    assert heating is not None
    owner = replace(heating.owner_residual, rounding_difference=cents(-2))
    return replace(data, heating_result=replace(heating, owner_residual=owner))


def _euro_figures(row: str) -> list[str]:
    return _EUR.findall(_plain(row))


def test_non_zero_rounding_difference_is_directly_below_the_owner_residual() -> None:
    data = _rounding_fixture()
    rows = _heating_rows(data, statement_html(data))
    owner_index = next(
        i for i, row in enumerate(rows) if _text(row).strip().startswith(OWNER_LABEL)
    )

    assert owner_index + 1 < len(rows), (
        "a non-zero Block-(c) value is absent below the Eigentümeranteil"
    )
    assert _text(rows[owner_index + 1]).strip().startswith(ROUNDING_LABEL), (
        "a non-zero Block-(c) value must render directly below the "
        "Eigentümeranteil, not as a separate disclosure or allocation"
    )


def test_rounding_subline_uses_exact_copy_and_only_its_carried_amount() -> None:
    data = _rounding_fixture()
    rows = _heating_rows(data, statement_html(data))
    rounding_rows = [row for row in rows if _text(row).strip().startswith(ROUNDING_LABEL)]

    assert rounding_rows, "a non-zero Block-(c) value renders no rounding subline"
    [rounding_row] = rounding_rows

    assert _text(rounding_row).strip() == "davon Rundungsdifferenz -0,02 €"
    assert _euro_figures(rounding_row) == ["-0,02 €"]
    for forbidden in ("Topf", "Quote", "%", "‰", "Bemessung", "Summe", "Umlage", "Verteilung"):
        assert forbidden not in _text(rounding_row), (
            "Block (c) became a separate pot, quota, Bemessung, total, or allocation: "
            f"{_text(rounding_row)!r}"
        )


def test_zero_rounding_difference_is_suppressed() -> None:
    data = build_demo_statement()
    heating = data.heating_result
    assert heating is not None
    assert int(heating.owner_residual.rounding_difference) == 0

    assert ROUNDING_LABEL not in _text(statement_html(data))


def test_rounding_subline_does_not_change_owner_residual_totals() -> None:
    data = _rounding_fixture()
    heating = data.heating_result
    assert heating is not None
    owner = heating.owner_residual
    rows = _heating_rows(data, statement_html(data))
    owner_row = next(row for row in rows if _text(row).strip().startswith(OWNER_LABEL))

    assert _euro_figures(owner_row) == [
        "345,14 €",
        "554,87 €",
        "115,05 €",
        "268,44 €",
        "1.283,50 €",
    ]
    assert int(owner.total) == 128_350
    assert int(owner.rounding_difference) == -2
