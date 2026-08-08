"""Gate: a figure and the calculation that justifies it stay on one sheet.

Spec: `docs/08` → **4b — Pagination: which blocks may break, and what may never
be separated**. Rechtsstand 08/2026. Written before the stylesheet change, red on
purpose. Found by `statement-reviewer` (**I1**), promoted out of the "I" bucket
by the lead on 05.08.2026.

**The defect.** The rendered demo is 3 pages and roughly 40 % blank — page 1
ends at ~78 % height, page 2 at ~57 %, page 3 at ~48 %. Cause:
`break-inside: avoid` on `.cost-split` and `.party-change`. Each block refuses to
split, does not fit the space left on the page, and takes a fresh one — pushing
itself down and leaving the space above it empty.

**The consequence is legal, not cosmetic.** BGH formal minimum #3 ends up on a
*different sheet of paper* from the numbers it justifies: a renter reads their
share in the money table on page 1 and has to turn the page to find the basis it
was computed from. A statement whose *Berechnung* is not next to its result is
the formal defect `docs/08` exists to close, reintroduced by a stylesheet
declaration.

**And it was backwards.** `.basis-table` — the carrier of minimums #2 *and* #3,
and the only block containing two tables where the second's column meanings are
defined by the first — was the one carrier *without* `break-inside: avoid`. Not
triggered on this fixture. It will be with eight parties.

The shape of the rule, which is what this file pins: **break at the seams, never
inside a statement.** `break-inside: avoid` is correct on the smallest element
that is one indivisible claim — a table row, a list item — and wrong on every
container above it.

Deliberately a **stylesheet** assertion, like
`packages/pdf/tests/test_statement_legal_typography.py`. Rendering the PDF and
measuring boxes tests Chromium, and a page-count golden over one demo fixture
encodes the fixture's size rather than a rule: it goes red for a *correct*
reason — one more unit — which is how a gate gets deleted instead of fixed.
`docs/08` → 4b, *"What is pinned, and what honestly cannot be"* records the one
property that matters and cannot be expressed at all: that the money table and
its disclosure share a sheet. It depends on the party count and is simply false
for a large enough building, so it is a design constraint on future changes,
never a test.
"""

import re

from lokara_pdf import statement_html
from lokara_pdf.demo import build_demo_statement

# The three heating-disclosure carriers (`docs/08` → 4a) plus the per-party
# total (`docs/08` → "`Ihr Anteil gesamt`"). Each grows with the number of
# parties, so each must be *breakable*: a block that may not split cannot be
# laid out beyond one page, and long before that it strands the page above it.
GROWING_CARRIERS = (".cost-split", ".basis-table", ".party-change", ".party-total")

# The smallest elements that are one indivisible claim. A party's label and their
# Bemessung are one statement; split across a page boundary a renter reads a
# figure with no name, or a name with no figure. A derivation line —
# `… × (181 von 365 Tagen) = rd. 5,95 m³` — is never legible in halves.
ATOMIC_CLAIMS = ("tr", ".apportionment li")

# A column header separated from its first row leaves a page of unlabelled
# numbers — and in `.basis-table` the *first* table is what gives the second's
# `Fläche·Tage` / `Verbrauch Warmwasser` columns their meaning.
KEEP_WITH_NEXT = ("thead", ".disclosure-title")

MIN_ORPHANS_WIDOWS = 2

_STYLE = re.compile(r"<style>(.*?)</style>", re.DOTALL)
_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.DOTALL)
_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def stylesheet() -> dict[str, dict[str, str]]:
    """`{selector: {property: value}}` — comments dropped, whitespace flattened.

    Same reader as the typography gate. Kept as a local copy rather than shared:
    a helper imported across two gates is a helper that gets loosened to make one
    of them pass.
    """
    html = statement_html(build_demo_statement())
    match = _STYLE.search(html)
    assert match is not None, "the statement carries no <style> block"

    rules: dict[str, dict[str, str]] = {}
    for selector, body in _RULE.findall(_COMMENT.sub("", match.group(1))):
        declarations = {}
        for declaration in body.split(";"):
            if ":" not in declaration:
                continue
            prop, _, value = declaration.partition(":")
            declarations[prop.strip()] = re.sub(r"\s+", " ", value).strip()
        for one in selector.split(","):
            key = re.sub(r"\s+", " ", one).strip()
            if key:
                rules.setdefault(key, {}).update(declarations)
    return rules


def declarations(selector: str) -> dict[str, str]:
    """The stylesheet's own rule for a selector, or a named failure.

    A selector the stylesheet never mentions is an unset page-break rule, which
    is the defect in one of its two forms — report it by name rather than raise a
    `KeyError` three frames deep.
    """
    rules = stylesheet()
    declared = rules.get(selector)
    assert declared is not None, (
        f"the stylesheet declares no rule for {selector!r}, so its page-break "
        "behaviour is whatever the renderer defaults to — docs/08 → 4b"
    )
    return declared


class TestBlocksThatGrowMayBreak:
    """`docs/08` → 4b: the carriers that grow with the party count must **not**
    declare `break-inside: avoid`. Breaking a disclosure block across pages is
    normal; stranding the page above it is the defect."""

    def test_no_growing_carrier_refuses_to_break(self) -> None:
        rules = stylesheet()
        offenders = {
            selector: rules[selector]["break-inside"]
            for selector in GROWING_CARRIERS
            if rules.get(selector, {}).get("break-inside") == "avoid"
        }

        assert offenders == {}, (
            f"{sorted(offenders)} declare `break-inside: avoid`. Each grows with the number of "
            "parties; refusing to split makes the block take a fresh page and leaves BGH "
            "minimum #3 on a different sheet from the figures it justifies (docs/08 → 4b)"
        )

    def test_every_growing_carrier_is_still_declared(self) -> None:
        """Guard on the list above: a growing block added without a page-break
        decision falls through this file otherwise. `.party-total` joined the
        list on 06.08.2026 — it is one row per party, so it grows exactly like
        the three disclosure blocks do."""
        rules = stylesheet()

        for selector in GROWING_CARRIERS:
            assert selector in rules, (
                f"{selector} is a `docs/08` carrier that grows with the party count and the "
                "stylesheet no longer declares it"
            )


class TestAStatementIsNeverSplit:
    """The other half of the rule: `break-inside: avoid` belongs on the smallest
    element that is one indivisible claim."""

    def test_a_table_row_is_atomic(self) -> None:
        for selector in ATOMIC_CLAIMS:
            assert declarations(selector).get("break-inside") == "avoid", (
                f"{selector} may be split by a page break — a party's label and their Bemessung "
                "are one statement (docs/08 → 4b)"
            )

    def test_a_header_stays_with_what_it_labels(self) -> None:
        for selector in KEEP_WITH_NEXT:
            assert declarations(selector).get("break-after") == "avoid", (
                f"{selector} may be left at the foot of a page, separated from the content it "
                "labels (docs/08 → 4b)"
            )

    def test_no_single_line_is_stranded(self) -> None:
        rules = stylesheet()

        for selector in GROWING_CARRIERS:
            declared = rules.get(selector, {})
            for prop in ("orphans", "widows"):
                value = declared.get(prop)
                assert value is not None and int(value) >= MIN_ORPHANS_WIDOWS, (
                    f"{selector} {{ {prop}: {value} }} — a stranded line of a legal disclosure "
                    "carries no verification content and reads as an error (docs/08 → 4b)"
                )
