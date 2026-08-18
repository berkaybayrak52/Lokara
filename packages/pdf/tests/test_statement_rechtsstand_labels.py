"""Gate: every `Rechtsstand` on the page names the rule it stamps.

Spec: `docs/08` → "Heizkostenabrechnung — the heating table's disclosure" → item 6
("M2 — every `Rechtsstand` names its statute").

The footer once printed `Rechtsstand 03/1989 · Rechtsstand 01/2009 · Rechtsstand
12/1983 · Rechtsstand 01/2023` — four bare dates, the label repeated four times,
and `HeizkostenV` nowhere on the page. `Rechtsstand 12/1983` is the
Gradtagszahlen table, which no reader could know; worse, an unlabelled 12/1983 date
standing between three statutory ones reads as *law from 1983*, which is exactly
what a VDI convention is not. A stamp that names no rule discloses nothing.

Required form (docs/08), the label once and each rule named beside its date:

    Rechtsstand: § 7 Abs. 1 HeizkostenV 03/1989 · § 9 Abs. 2 HeizkostenV 01/2009 ·
    Gradtagszahlen-Promilletabelle (VDI-Konvention, keine Rechtsnorm) 12/1983 ·
    § 5 Abs. 1 i. V. m. Anlage CO2KostAufG 01/2023 · Erstellt mit Lokara.

This is **presentation only**: the three statutory labels are already carried by
`packages/rules-store` as `ResolvedRule.source` and were simply thrown away by
the caller. Nothing this file asserts changes what the store resolves, and no
legal value enters it.

Two things the assertions deliberately do:

- They resolve the sources **from the store**, in the test, rather than typing
  them in. A hardcoded literal that happens to match still passes — no test can
  catch that — but a store edit that moves a citation surfaces here instead of
  on a tenant's statement.
- They are scoped to the `<footer>`. `Rechtsstand 01/2023` legitimately appears a
  second time inside the CO₂ block, where it *is* labelled (`CO2KostAufG,
  Rechtsstand 01/2023`); a page-wide canary would forbid the one occurrence that
  is already correct.

The fixture is the demo composition — real engines, rules resolved from the
rules-store for `AS_OF`. No hand-written stamps.
"""

import re

from lokara_pdf import rechtsstand_entry, statement_html
from lokara_pdf.demo import AS_OF, build_demo_statement
from lokara_rules_store import (
    CO2_FALLBACK_EMISSION_FACTORS,
    CO2_SPLIT_TABLE,
    DEGREE_DAY_TABLE,
    HEATING_SPLIT_BOUNDS,
    WARM_WATER_FORMULA,
    get_rule,
)

# The degree-day table is not a statute, so it has no citation to print. Its
# `source` in the store is "Anerkannte Gradtagszahlen-Promilletabelle (VDI) —
# verify before production": everything after the em dash is a developer marker
# and must never reach a tenant. docs/08 fixes the rendered label instead, and
# the qualifier is the point of it — a convention presented as law is worse than
# no disclosure at all.
DEGREE_DAY_LABEL = "Gradtagszahlen-Promilletabelle (VDI-Konvention, keine Rechtsnorm)"
INTERNAL_MARKER = "verify before production"

_FOOTER = re.compile(r"<footer>(.*?)</footer>", re.DOTALL)

# NBSP (U+00A0) and narrow NBSP (U+202F) — the template joins a figure to its
# unit with one. Spelled as code points: a literal trips RUF001.
_SPACES = ("\xa0", chr(0x202F))


def _plain(text: str) -> str:
    """NBSP and source line breaks are formatting choices, not part of the spec —
    `scripts/assert_statement_pdf.py` flattens whitespace the same way."""
    for space in _SPACES:
        text = text.replace(space, " ")
    return re.sub(r"\s+", " ", text).strip()


def _footer(html: str) -> str:
    match = _FOOTER.search(html)
    assert match is not None, "the statement has no <footer> — the Rechtsstände live there"
    return _plain(match.group(1))


def _stamp(rechtsstand: str) -> str:
    """`Rechtsstand 03/1989` → `03/1989`. The label is printed once, up front."""
    return rechtsstand.removeprefix("Rechtsstand ").strip()


def _rendered_footer() -> str:
    return _footer(statement_html(build_demo_statement()))


def test_each_statutory_rechtsstand_names_its_source() -> None:
    """docs/08 item 6: the citation the store already carries, beside its date."""
    footer = _rendered_footer()

    for rule_set in (HEATING_SPLIT_BOUNDS, WARM_WATER_FORMULA, CO2_SPLIT_TABLE):
        resolved = get_rule(rule_set, AS_OF)
        expected = f"{resolved.source} {_stamp(resolved.rechtsstand)}"
        assert expected in footer, f"{resolved.key}: footer does not carry {expected!r}"


def test_the_degree_day_stamp_is_labelled_as_a_convention() -> None:
    """The one stamp that is not law must say so where it is printed, and the
    store's internal marker must not reach the page."""
    html = statement_html(build_demo_statement())
    footer = _footer(html)
    degree_days = get_rule(DEGREE_DAY_TABLE, AS_OF)

    assert f"{DEGREE_DAY_LABEL} {_stamp(degree_days.rechtsstand)}" in footer
    assert INTERNAL_MARKER not in _plain(html), "developer marker leaked onto the statement"


def test_shared_co2_fallback_public_provenance_is_clean() -> None:
    """K4 is shared by three fuels: its public label carries only common
    provenance and the EBeV effective date, never register-review metadata or
    Erdgas-only conversion provenance. The CSV remains the internal source of
    truth for those fields (`docs/03` public provenance boundary)."""
    resolved = get_rule(CO2_FALLBACK_EMISSION_FACTORS, AS_OF)
    entry = rechtsstand_entry(resolved)
    public_surfaces = {
        "ResolvedRule.source": resolved.source,
        "rechtsstand_entry": entry,
    }
    forbidden = (
        "geprüft",
        "verify before production",
        "Register-Rechtsstand",
        "07/2026",
        "0,903",
        "0.903",
    )

    actual = {
        "leaks": {
            name: tuple(token for token in forbidden if token in text)
            for name, text in public_surfaces.items()
        },
        "resolved_rechtsstand": resolved.rechtsstand,
        "entry_dates": tuple(re.findall(r"\b\d{2}/\d{4}\b", entry)),
    }
    expected = {
        "leaks": {
            "ResolvedRule.source": (),
            "rechtsstand_entry": (),
        },
        "resolved_rechtsstand": "Rechtsstand 01/2023",
        "entry_dates": ("01/2023",),
    }
    assert actual == expected


def test_no_bare_rechtsstand_remains_in_the_footer() -> None:
    """The label is printed once as a prefix; every date after it is named.

    `Rechtsstand 12/1983` standing alone is the defect this slice exists for, so
    it is asserted absent by name as well as by the general rule.
    """
    footer = _rendered_footer()

    assert footer.count("Rechtsstand") == 1, (
        "the label repeats — docs/08 prints `Rechtsstand:` once, then label+date per rule"
    )
    tail = footer.removeprefix("Rechtsstand:").strip()
    for rule_set in (
        HEATING_SPLIT_BOUNDS,
        WARM_WATER_FORMULA,
        DEGREE_DAY_TABLE,
        CO2_SPLIT_TABLE,
    ):
        bare = get_rule(rule_set, AS_OF).rechtsstand
        assert bare not in tail, f"{bare!r} is printed without naming the rule it stamps"


def test_heizkostenv_appears_on_the_statement() -> None:
    """Blunt, and the reason the slice exists: a Heizkostenabrechnung that never
    names the HeizkostenV. Both § 7 and § 9 are resolved for this statement, so
    the ordinance is named at least twice."""
    html = _plain(statement_html(build_demo_statement()))

    assert html.count("HeizkostenV") >= 2


def test_the_footer_still_carries_the_disclaimer() -> None:
    """Regression guard: reworking the stamps must not push the "tool, not
    advice" line off the page (CLAUDE.md)."""
    footer = _rendered_footer()

    assert "keine Rechts- oder Steuerberatung" in footer
    assert "Erstellt mit Lokara." in footer
