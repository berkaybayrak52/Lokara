"""Gate: every party reads one number about themselves — and it is an `Anteil`,
never a `Saldo`.

Spec: `docs/08` → "`Ihr Anteil gesamt` — the per-party total, and why it is never
a Saldo". Rechtsstand 08/2026. Written before the template change, **red on
purpose**.

**The defect.** No per-party grand total exists anywhere on the document.
Wohnung A's renter reads `600,00 €` in the Betriebskosten table and `5.603,97 €`
in the heating table — in practice on a different sheet — and is never told one
number about themselves. Two disconnected tables, no bottom line. That is BGH
formal minimum #3 (*Berechnung des Anteils des Mieters*) left half-rendered: both
addends are printed, their sum is not.

**Nothing here is a new calculation.** `Anteil gesamt = Betriebskosten-Anteil +
Heizungs-Anteil`, per party, both addends already computed and already rounded by
the engines. This file therefore reads every expected figure *off the engine
result* and every actual figure *off the rendered page*; no euro amount is typed
in. If the engines re-base (as the CO₂ fixture did on 05.08.2026), the assertions
move with them and only this docstring goes stale.

**Why the label matters as much as the arithmetic.** BGH minimum #4 is
*Vorauszahlungen minus Anteil = Nachzahlung oder Guthaben*. This document renders
only the middle term — #4 is blocked on the M6 payment ledger, by decision. So
the vocabulary that asserts the other two terms is forbidden page-wide
(`test_the_page_never_implies_a_balance`), and the one sentence that names the
missing quantity is required. A label that asserts more than the arithmetic
supports is the same class of error as the false `= 5,95 m³` identity this file's
neighbours fixed.

The fixture is the demo composition — both real engines, rules resolved from the
rules-store. No hand-written `NkResult` or `HeatingResult`.
"""

import re
from decimal import Decimal

from lokara_domain import cents, format_eur
from lokara_pdf import StatementData, statement_html
from lokara_pdf.demo import build_demo_statement

# The carrier. One element, one class (`docs/08` → "Carrier, tier and page
# breaks"); tier 1 in `test_statement_legal_typography.py`, breakable in
# `test_statement_pagination.py`.
CARRIER = "party-total"

# Fixed copy — `docs/08` → "Required rendered text". The two money-column headers
# are *not* here: they name the sections the figures come from, so they are read
# off the document itself (the NK `<h2>` and `StatementData.heating_cost_label`).
# A summary column that renames its source section makes the reader hunt for it.
HEADING = "Anteile je Partei"
TOTAL_COLUMN = "Anteil gesamt"
SUM_ROW_LABEL = "Summe der Anteile"

# `docs/08` → "Die Eigentümerzeile" § 3a, added 14.08.2026. The landlord side
# collapses into **one** row here — otherwise the NK asymmetry surfaces as two
# rows for one owner (`Wohnung B — Leerstand … → Vermieter` for the NK share and
# `Eigentümeranteil` for the heating residual) in the one table whose whole job
# is to give each party a single number. Same word as the heating money table,
# Block B and the annex.
OWNER_LABEL = "Eigentümeranteil"

# The sentence that has to accompany the figure. `geleistete` is § 556 Abs. 3
# BGB's own word: it says *which* quantity is missing, not merely that something
# is. It states no right, no deadline and no payment instruction — all three
# would be claims this document has not transcribed — and it does not contain the
# word `Saldo`, which would put the forbidden term in the one place a reader
# scans for it.
COMPLETENESS_SENTENCE = (
    "Der Anteil gesamt ist die Summe der in derselben Zeile ausgewiesenen "
    "Anteile; geleistete Vorauszahlungen sind darin nicht berücksichtigt."
)

# Words this page cannot support, asserted **page-wide** rather than inside the
# block — a balance implied in the footer is the same defect one section later.
#
# Checked against the rendered page on 06.08.2026 before this file was written:
# all six occur **zero** times today, case-insensitively, so none of them needed
# narrowing to the block. If a later slice introduces one legitimately (a payment
# section at M6 is the expected case), narrow *that one* term to the block and
# say why here — do not drop it.
FORBIDDEN_VOCABULARY = (
    "Saldo",  # asserts two sides were netted. Only one side exists.
    "Nachzahlung",  # asserts the sign of a balance
    "Guthaben",  # ditto, the other sign
    "zu zahlen",  # asserts the figure is what the renter still owes
    "offener Betrag",  # ditto
    "fällig",  # ditto, plus a due date this document does not carry
)

_TAG = re.compile(r"<[^>]+>")
_ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.DOTALL)
# German money as this document prints it: `5.603,97 €`, NBSP before the sign.
_EUR = re.compile(r"-?\d{1,3}(?:\.\d{3})*,\d{2}\s*€")


def _plain(text: str) -> str:
    """NBSP/narrow-NBSP and source line breaks are formatting choices, not part
    of the spec — the template wraps copy mid-sentence and
    ``scripts/assert_statement_pdf.py`` flattens whitespace the same way.
    """
    return re.sub(r"\s+", " ", text.replace("\xa0", " ").replace("\u202f", " "))


def _text(html: str) -> str:
    """Rendered text of a fragment: tags stripped, whitespace flattened."""
    return _plain(_TAG.sub(" ", html))


def _cents_from_de(rendered: str) -> int:
    """'5.603,97 €' -> 560397. Reads the page, not the engine."""
    figure = _plain(rendered).replace("€", "").strip().replace(".", "").replace(",", ".")
    return int((Decimal(figure) * 100).to_integral_value())


def _figures(fragment: str) -> list[int]:
    """Every euro amount in a fragment, in document order, as integer cents.

    Deliberately parsed out of the *text* rather than out of ``td.num`` cells:
    what `docs/08` fixes is which figures a reader sees in which order, and a
    gate that pins the implementer's markup instead would go red on a correct
    refactor.
    """
    return [_cents_from_de(match) for match in _EUR.findall(_plain(fragment))]


def _block(html: str) -> str:
    """The `.party-total` block: from its opening tag to the `<footer>`.

    `docs/08` → "Where it renders, and why there": the block is the **last** one
    of the statement body, between ``{_heating_section(data)}`` and ``<footer>``.
    Slicing to the footer rather than matching a closing tag keeps this gate
    agnostic about whether the carrier is a ``div``, a ``section`` or the table
    itself — one element, one class, is the whole requirement.
    """
    marks = [m.start() for m in re.finditer(rf'class="[^"]*\b{CARRIER}\b[^"]*"', html)]
    assert marks, (
        f"the rendered statement carries no .{CARRIER} block — no party is told "
        "one number about themselves (docs/08, BGH minimum #3)"
    )
    assert len(marks) == 1, f".{CARRIER} is one element, one class — found {len(marks)}"

    footer = html.find("<footer")
    assert footer > marks[0], (
        f".{CARRIER} must render last in the statement body, immediately before "
        "the footer — it is the only position where both of its addends are "
        "already on the page (docs/08)"
    )
    return html[html.rfind("<", 0, marks[0]) : footer]


def _party_order(data: StatementData) -> list[str]:
    """Row labels in the order the money tables introduce them, `Eigentümeranteil`
    last.

    Renters first, by first appearance over the Betriebskosten lines and then the
    heating lines — a reader reads down two tables and down this one, and a
    different order makes them search. The Eigentümer row is appended **last
    regardless**, because it is the reconciling line rather than a party
    (`docs/08` → "Die Eigentümerzeile" § 3a).
    """
    keys: list[tuple[str | None, str | None]] = []
    heating = data.heating_result
    seen: list[tuple[str | None, str | None]] = [
        *((line.unit_id, line.tenancy_id) for line in data.nk_result.lines),
        *(() if heating is None else ((line.unit_id, line.tenancy_id) for line in heating.lines)),
    ]
    for key in seen:
        if key not in keys and key[1] is not None:
            keys.append(key)
    return [data.party_labels[key] for key in keys] + [OWNER_LABEL]


def _expected_shares(data: StatementData) -> dict[str, tuple[int, int]]:
    """`{row label: (Betriebskosten cents, Heizkosten cents)}` from the engines.

    Summed per row across *all* cost items: the demo bills one NK cost today, and
    a second one must land in the same row rather than a second one.

    **The landlord side collapses into one `Eigentümeranteil` row** — `docs/08`
    § 3a. Its heating figure is the Liegenschafts-Residuum; its Betriebskosten
    figure is the sum of `nk-engine`'s per-unit landlord parties, which still
    exist because NK keeps largest-remainder until Seite 02 lands in `docs/09`.
    Summing them here is a **display** aggregation and asserts nothing about how
    they were computed: the Betriebskosten table above still itemises them per
    unit, and no copy on this block calls the NK part a residual.
    """
    shares: dict[str, tuple[int, int]] = {label: (0, 0) for label in _party_order(data)}
    for nk_line in data.nk_result.lines:
        label = (
            OWNER_LABEL
            if nk_line.tenancy_id is None
            else data.party_labels[(nk_line.unit_id, nk_line.tenancy_id)]
        )
        nk, heat = shares[label]
        shares[label] = (nk + int(nk_line.amount), heat)
    heating = data.heating_result
    if heating is not None:
        for heat_line in heating.lines:
            label = data.party_labels[(heat_line.unit_id, heat_line.tenancy_id)]
            nk, heat = shares[label]
            shares[label] = (nk, heat + int(heat_line.total))
        nk, heat = shares[OWNER_LABEL]
        shares[OWNER_LABEL] = (nk, heat + int(heating.owner_residual.total))
    return shares


def _rows(block: str) -> list[tuple[str, list[int]]]:
    """`[(row text, figures in cents)]` for every `<tr>` in the block."""
    return [(_text(row), _figures(row)) for row in _ROW.findall(block)]


def _row_for(block: str, label: str) -> list[int]:
    """The figures on the row that carries `label`, or a named failure."""
    matches = [figures for text, figures in _rows(block) if label in text]
    assert len(matches) == 1, (
        f"{label!r} must appear on exactly one row of the .{CARRIER} block "
        f"— found {len(matches)}. Two labels for one arithmetic is drift "
        "(docs/08, 'Which parties get a row, and which label')"
    )
    return matches[0]


def test_the_block_renders_its_required_copy() -> None:
    """`docs/08` → "Required rendered text". The heading and the Σ label are fixed
    copy; the two money-column headers must name their source sections, which is
    why they are read off the document rather than typed here."""
    data = build_demo_statement()
    block = _text(_block(statement_html(data)))

    assert HEADING in block
    assert "Partei" in block
    assert TOTAL_COLUMN in block
    assert SUM_ROW_LABEL in block

    # The money columns name the sections the figures come from: `Betriebskosten`
    # is the NK section's own <h2>, the heating header is the heating <h2>.
    assert "Betriebskosten" in block
    assert data.heating_cost_label in block


def test_the_heading_reuses_the_disclosure_title_idiom() -> None:
    """`docs/08`: the heading uses the existing `.disclosure-title` class, so it
    inherits 4b's "a heading never ends a page alone" rule rather than
    introducing a second heading idiom that the pagination gate does not see."""
    block = _block(statement_html(build_demo_statement()))

    title = re.compile(r'<[^>]*class="[^"]*\bdisclosure-title\b[^"]*"[^>]*>(.*?)<', re.DOTALL)
    heading = title.search(block)
    assert heading is not None, (
        f'the .{CARRIER} heading must carry class="disclosure-title" (docs/08) '
        "— otherwise `thead, .disclosure-title { break-after: avoid }` does not "
        "reach it and the heading can be stranded at the foot of a page"
    )
    assert HEADING in _plain(heading.group(1))


def test_every_party_gets_a_row_and_the_owner_gets_exactly_one() -> None:
    """`docs/08` → "Which parties get a row, and which label", as amended by
    "Die Eigentümerzeile" § 3a (14.08.2026).

    The owner's line is under the *same* header and gets no second, softer
    label. Two reasons, both unchanged by the model: omitting it makes the Σ row
    false (the printed rows are the addends of the printed total), and the
    owner's share is a real figure with a real bearer — a blank or a `—` in a
    money column reads as zero.

    What *did* change: it is **one** `Eigentümeranteil` row rather than one row
    per vacant unit, and it renders last because it is the reconciling line
    rather than a party.
    """
    data = build_demo_statement()
    block = _block(statement_html(data))
    expected = _party_order(data)

    rendered = [text for text, figures in _rows(block) if len(figures) == 3]
    rendered_parties = [text for text in rendered if SUM_ROW_LABEL not in text]

    assert len(rendered_parties) == len(expected), (
        f"the .{CARRIER} block prints {len(rendered_parties)} party rows for "
        f"{len(expected)} parties (docs/08: every party gets a row)"
    )
    for row, label in zip(rendered_parties, expected, strict=True):
        assert label in row, (
            f"expected {label!r} here — row order is the order the money tables "
            "introduce the parties (docs/08)"
        )

    # Named explicitly, because this is the row that would be dropped: the
    # owner's, and with it the truth of the Σ row.
    assert rendered_parties[-1].strip().startswith(OWNER_LABEL), (
        "the Eigentümeranteil row must render last — it is the reconciling "
        "line, not a party (docs/08 § 3a)"
    )
    assert _row_for(block, OWNER_LABEL)
    # …and the per-unit landlord label is no longer a row of *this* block. It
    # is still on the page, in the Betriebskosten table, which keeps its
    # per-unit landlord party until Seite 02 lands in `docs/09`.
    vacancy = data.party_labels[("unit-b", None)]
    assert "Vermieter" in vacancy, "fixture no longer carries a landlord vacancy party"
    assert vacancy not in _text(block)


def test_each_party_row_is_the_sum_of_that_party_two_shares() -> None:
    """The arithmetic, read back off the rendered page.

    Three figures per row, in column order: Betriebskosten, Heiz- und
    Warmwasserkosten, Anteil gesamt. The first two must be the amounts the money
    tables already print for that party, and the third must be their sum to the
    cent. Integer cents throughout — the sum is of two already-rounded engine
    amounts, so no rounding rule is introduced here (docs/08).
    """
    data = build_demo_statement()
    block = _block(statement_html(data))

    for label, (nk, heat) in _expected_shares(data).items():
        figures = _row_for(block, label)
        assert len(figures) == 3, (
            f"{label}: expected Betriebskosten, {data.heating_cost_label} and "
            f"{TOTAL_COLUMN}, got {len(figures)} figures"
        )
        assert figures[0] == nk, f"{label}: Betriebskosten column"
        assert figures[1] == heat, f"{label}: {data.heating_cost_label} column"
        assert figures[2] == nk + heat, (
            f"{label}: {TOTAL_COLUMN} must be {format_eur(cents(nk + heat))} — the sum "
            "of the two figures on its own row, nothing re-derived (docs/08)"
        )


def test_the_columns_reconcile_to_their_printed_sums() -> None:
    """The two reconciliations. `sum(shares) == input_total`, the invariant every
    allocation test in this repo carries — here asserted over *rendered text*, so
    a renderer bug surfaces as loudly as an engine one.

    1. Each column's printed party figures sum exactly to that column's printed Σ.
    2. The `Anteil gesamt` Σ equals the other two Σs added.

    Note what the heating Σ is **not**: `heating_result.total` is the Gesamtkosten
    (10.300,00 €), and this column sums to 10.142,92 € — the difference is the
    CO₂-Vermieteranteil, deducted before the renter-facing split (§ 7 Abs. 1
    CO2KostAufG) and carried by no party. The heating footer already prints that
    difference, named and cited; this block does not repeat it, and 11.342,92 €
    is deliberately not 11.500,00 €.
    """
    data = build_demo_statement()
    block = _block(statement_html(data))

    party_rows = [_row_for(block, label) for label in _party_order(data)]
    printed_sums = _row_for(block, SUM_ROW_LABEL)
    assert len(printed_sums) == 3, f"the {SUM_ROW_LABEL!r} row carries three Σ figures"

    for column, name in enumerate(("Betriebskosten", data.heating_cost_label, TOTAL_COLUMN)):
        column_sum = sum(row[column] for row in party_rows)
        assert column_sum == printed_sums[column], (
            f"{name}: the party figures add up to {format_eur(cents(column_sum))} but "
            f"the Σ row prints {format_eur(cents(printed_sums[column]))}. `Summe` is "
            "licensed here only because the rows above really are its addends "
            "(docs/08)"
        )

    assert printed_sums[2] == printed_sums[0] + printed_sums[1], (
        f"{TOTAL_COLUMN} Σ must be the other two Σs added"
    )

    # ...and both engine totals are still what the columns reconcile to.
    heating = data.heating_result
    assert heating is not None, "fixture lost its heating section"
    assert printed_sums[0] == int(data.nk_result.total)
    assert printed_sums[1] == sum(int(line.total) for line in heating.lines)


def test_the_block_says_the_vorauszahlungen_are_not_deducted() -> None:
    """Without this sentence the fact is inferred wrongly by every reader who has
    ever received a utility statement: they read a total and assume it is what
    they owe. `docs/08` → "The one sentence that has to accompany it"."""
    block = _text(_block(statement_html(build_demo_statement())))

    assert COMPLETENESS_SENTENCE in block, (
        "the per-party total must name the quantity it does not contain — "
        "`geleistete Vorauszahlungen`, § 556 Abs. 3 BGB's own word (docs/08)"
    )


def test_the_page_never_implies_a_balance() -> None:
    """`Anteil` is what the figure is. Every word below asserts BGH minimum #4 —
    *advances paid minus share owed = Nachzahlung oder Guthaben* — of which this
    document renders only the middle term.

    Asserted **page-wide**, not inside the block: a balance implied in the footer
    or a column header is the same defect one section later. All six terms occur
    zero times today (checked 06.08.2026), so nothing needed narrowing. They
    become available at M6, when the payment ledger puts the deduction on the
    page — what licenses the word is the deduction being printed, not the figure
    being convenient.
    """
    page = _plain(statement_html(build_demo_statement())).casefold()

    present = [word for word in FORBIDDEN_VOCABULARY if word.casefold() in page]
    assert not present, (
        "the statement uses vocabulary that asserts a balance it does not "
        "compute: " + ", ".join(present) + " (docs/08 → 'The label is `Anteil`')"
    )


def test_the_document_does_not_address_a_reader_it_does_not_have() -> None:
    """`Ihr Anteil gesamt` is the correct form for the Mieter-Einzelabrechnung —
    one party, one addressee. Today's render is the Vermieter-Gesamtübersicht:
    four parties, no addressee block, and one of the parties is the landlord
    reading it. `Ihr` there addresses the landlord as though they were the
    tenant (docs/08, "And that is the ruling on the second person")."""
    block = _text(_block(statement_html(build_demo_statement())))

    assert not re.search(r"\bIhr\w*\b", block), (
        f"the .{CARRIER} column header is `{TOTAL_COLUMN}` on this document; the "
        "second person belongs to the Einzelabrechnung, which has an addressee"
    )
