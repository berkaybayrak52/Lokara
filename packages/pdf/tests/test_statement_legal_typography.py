"""Gate: legally required disclosure is readable — at the bar its *job* earns.

Spec: `docs/05` → "Legally required disclosure — two tiers, split by what the
content is for", the four named rules (`legal-t1-size`, `legal-t1-contrast`,
`legal-t2-contrast`, `legal-t2-scale`) and the measured ratios of the brand
pairs. `docs/08` → "Which text on the statement is legally required" names
*which* text on this document carries which tier; it deliberately carries no
thresholds.

**Two tiers, not one flat bar.** An earlier version of this file held everything
legally required to a single AAA + body-size rule. That was ruled wrong on
04.08.2026: the bar follows what the content is *for*, never a number.

**Tier 1 — verification content.** The four BGH formal minimums and anything
that explains them: Umlageschlüssel, Bemessung, Gesamtbemessung, the amounts,
the CO₂ reconciliation. German case law requires the statement to be
*verständlich für einen durchschnittlichen Mieter*, and this is precisely the
content that requirement is about.

1. `legal-t1-size` — **never smaller than body copy**, read from the
   stylesheet's own `body { font-size }`. Not an absolute point floor: DIN 1450
   specifies legibility by x-height and reading distance, so no point number
   falls out of it, and the brand faces are not embedded in the PDF anyway. Not
   "not the smallest text on the page" either — that is satisfiable by shrinking
   everything else, which makes the page worse and turns this green.
2. `legal-t1-contrast` — **≥ 7:1** on its own background (WCAG 2.1 Level AAA,
   SC 1.4.6 *Contrast (Enhanced)*) → Petrol Ink or Forest Deep. Slate keeps its
   `docs/05` role (secondary text on Paper, 5,44:1) and leaves tier 1.

**Tier 2 — provenance and attestation.** The `Rechtsstand` stamps and the
disclaimer. These are *not* part of the BGH minimums — `Rechtsstand` is our own
rule from `CLAUDE.md`. They must be present and legible, not prominent.

3. `legal-t2-contrast` — **≥ 4,5:1** (WCAG 2.1 Level AA, SC 1.4.3 *Contrast
   (Minimum)*), i.e. never below the page's ordinary bar.
4. **No size floor, deliberately.** Quoting the ruling, because it is the rule
   and not a footnote to it: *"I am not inventing a second magic number, and any
   ratio I picked would land conveniently on the current 8 pt, which is the same
   error as the 9,0 pt floor."* The tier-2 code path below therefore has **no
   size branch at all** — see `test_tier2_provenance_is_legible_not_prominent`.
   Adding one is a spec change in `docs/05` first, a test change second.
5. `legal-t2-scale` is **not** asserted here: it is a user-zoom / text-scaling
   rule and a print PDF discharges it by the medium (the viewer zooms the whole
   page). Stated in `docs/05`, not measurable against this stylesheet.

Both tiers carry **line-height ≥ 1,4** wherever one is declared.

Deliberately a **stylesheet** assertion, not a pixel one. Rendering a PDF and
measuring glyphs would test Chromium; what is being fixed here is a declaration.
The contrast arithmetic is the WCAG 2.1 relative-luminance formula, computed
from the tokens the template itself declares — so a token edit that quietly
darkens Mint cannot make a failing pair pass by accident.
"""

import re

from lokara_pdf import statement_html
from lokara_pdf.demo import build_demo_statement

# docs/05 palette, transcribed. Asserted against the template's own `:root` so
# this file fails loudly if the tokens drift rather than silently re-basing the
# contrast maths on a new colour.
DOCS05_TOKENS = {
    "--color-ink": "#18212a",
    "--color-green": "#1a6558",
    "--color-forest": "#123f37",
    "--color-mint": "#e7efeb",
    "--color-slate": "#5c6a6b",
    "--color-paper": "#fbfbfa",
}

# WCAG 2.1 SC 1.4.6 (AAA) for tier 1, SC 1.4.3 (AA) for tier 2. No size constant
# exists to declare for either tier — see `docs/05`, "Why there is no absolute pt
# floor". Tier 1's size rule is comparative (body copy is the reference); tier 2
# has no size rule.
MIN_TIER1_CONTRAST = 7.0
MIN_TIER2_CONTRAST = 4.5
MIN_LEGAL_LINE_HEIGHT = 1.4

# Selector → the token its text actually sits on. Hand-mapped because CSS
# inheritance is not resolvable from a stylesheet alone; `test_backgrounds_are_
# as_this_file_assumes` keeps the mapping honest.
#
# This is the *carrier list* from `docs/08` → "Which text on the statement is
# legally required". The tiers below must partition it exactly; a carrier added
# here without a tier fails `test_every_legal_carrier_is_in_exactly_one_tier`
# rather than sliding through untested.
LEGAL_SURFACES = {
    ".key-label": "--color-mint",  # Umlageschlüssel + Gesamtbemessung (BGH #2/#3)
    "tfoot .foot-note": "--color-paper",  # the heating footer's reconciliation
    ".note": "--color-paper",  # § 9a estimation / fallback disclosure
    ".co2": "--color-mint",  # CO2KostAufG § 7 Abs. 3
    ".cost-split": "--color-paper",  # Block A — §§ 7/8/9 split of the Gesamtkosten
    ".basis-table": "--color-paper",  # Block B — Umlageschlüssel/Bemessung per column
    ".party-change": "--color-paper",  # Block C — § 9b Nutzerwechsel apportionment
    "footer": "--color-paper",  # Rechtsstand + disclaimer
}

# Tier 1 — verification content. A reader recomputes their own share from this.
#
# `.note` is here on purpose. Its two strings are both § 9a HeizkostenV notices,
# and both change how the renter must read their own Bemessung: one says the
# Verbrauch figure is an *estimate, not a reading*, the other says the
# consumption key was *replaced by the area key* — i.e. the Umlageschlüssel
# printed in `.key-label` is not the one that was applied. Neither is incidental
# copy; both sit inside BGH minimums #2 and #3. (docs/08, "Why `.note` is tier 1")
#
# The three heating-disclosure blocks are here for the same reason and by the
# same test — "can the reader verify a number with it?" (docs/05, "Assigning a
# carrier to a tier"). Block A is the vertical half of the tenant's calculation,
# Block B is the horizontal half (Umlageschlüssel, Bemessung, Gesamtbemessung),
# Block C derives the Bemessung the money table prints. Their surfaces are
# Paper — docs/08 → 4a, "Carriers, and their tier".
TIER_1_VERIFICATION = frozenset(
    {
        ".key-label",
        "tfoot .foot-note",
        ".note",
        ".co2",
        ".cost-split",
        ".basis-table",
        ".party-change",
    }
)

# Tier 2 — provenance and attestation. States where the rules came from and what
# the document is not. No number is recomputed from it, and no court requires it:
# `Rechtsstand` is our own rule (`CLAUDE.md`).
TIER_2_PROVENANCE = frozenset({"footer"})

_STYLE = re.compile(r"<style>(.*?)</style>", re.DOTALL)
_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.DOTALL)
_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
_VAR = re.compile(r"var\(\s*(--[a-z0-9-]+)\s*\)")


def _stylesheet() -> dict[str, dict[str, str]]:
    """`{selector: {property: value}}` — whitespace-normalised, comments dropped."""
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
        rules[re.sub(r"\s+", " ", selector).strip()] = declarations
    return rules


def _tokens(rules: dict[str, dict[str, str]]) -> dict[str, str]:
    return {k: v.lower() for k, v in rules[":root"].items() if k.startswith("--color")}


def _declarations(rules: dict[str, dict[str, str]], selector: str) -> dict[str, str]:
    """The stylesheet's own rule for a legal carrier.

    A carrier the stylesheet never mentions is untested typography — this reports
    it by name instead of raising a `KeyError` three frames deep.
    """
    declared = rules.get(selector)
    assert declared is not None, (
        f"{selector} carries legally required text (docs/08) but the stylesheet "
        "declares no rule for it, so its tier cannot be checked"
    )
    return declared


def _pt(value: str, *, selector: str, prop: str) -> float:
    """Point size of a declaration. Anything but `pt` fails rather than skips —
    a unit this file cannot compare is a hole in the gate, not a pass."""
    match = re.fullmatch(r"([0-9.]+)pt", value)
    assert match is not None, (
        f"{selector} {{ {prop}: {value} }} — this gate compares point sizes; "
        "extend it before introducing another unit"
    )
    return float(match.group(1))


def _luminance(hex_color: str) -> float:
    """WCAG 2.1 relative luminance."""
    raw = hex_color.lstrip("#")
    channels = [int(raw[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground: str, background: str) -> float:
    lighter, darker = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def _contrast_violations(
    rules: dict[str, dict[str, str]], selectors: frozenset[str], floor: float
) -> list[str]:
    """Every selector in `selectors` below `floor`, as report lines.

    Accumulating rather than asserting per selector is the point: an implementer
    fixing this needs the whole set in one run, not whichever selector the
    iteration order trips on first.
    """
    tokens = _tokens(rules)
    violations = []
    for selector in sorted(selectors):
        declared = _declarations(rules, selector).get("color")
        if declared is None:
            continue  # inherits body → Petrol Ink, the highest pair available
        match = _VAR.search(declared)
        assert match is not None, f"{selector} {{ color: {declared} }} — tokens only (docs/05)"
        ratio = contrast(tokens[match.group(1)], tokens[LEGAL_SURFACES[selector]])
        if ratio < floor:
            violations.append(
                f"{selector}: {match.group(1)} on {LEGAL_SURFACES[selector]} is {ratio:.2f}:1"
            )
    return violations


def test_the_tokens_are_the_docs05_palette() -> None:
    """The contrast maths below is only meaningful against the real palette."""
    assert _tokens(_stylesheet()) == DOCS05_TOKENS


def test_backgrounds_are_as_this_file_assumes() -> None:
    """Keeps `LEGAL_SURFACES` honest: the Umlageschlüssel line sits on the cost
    row's Mint, and the page ground is Paper."""
    rules = _stylesheet()

    assert _VAR.search(rules["tr.cost-row td"]["background"]).group(1) == "--color-mint"  # type: ignore[union-attr]
    assert _VAR.search(rules["body"]["background"]).group(1) == "--color-paper"  # type: ignore[union-attr]
    assert _VAR.search(rules[".co2"]["background"]).group(1) == "--color-mint"  # type: ignore[union-attr]


def test_every_legal_carrier_is_in_exactly_one_tier() -> None:
    """No carrier of legally required text may be untiered.

    `docs/05` → "Every carrier of legally required text belongs to exactly one
    tier — unassigned is not a state." Without this, adding a carrier to
    `LEGAL_SURFACES` (or to the template, and then here) while forgetting the
    tier would give it *no* assertions at all and still show green.
    """
    tiered = TIER_1_VERIFICATION | TIER_2_PROVENANCE

    untiered = sorted(set(LEGAL_SURFACES) - tiered)
    assert not untiered, (
        "legally required carriers with no tier: "
        + ", ".join(untiered)
        + " — assign each in docs/08 (verification content → 1, provenance → 2)"
    )

    unknown = sorted(tiered - set(LEGAL_SURFACES))
    assert not unknown, (
        "tiered selectors missing from LEGAL_SURFACES (so their background is "
        "unmapped): " + ", ".join(unknown)
    )

    both = sorted(TIER_1_VERIFICATION & TIER_2_PROVENANCE)
    assert not both, "selectors claimed by both tiers: " + ", ".join(both)


def test_every_legal_carrier_is_declared_in_the_stylesheet() -> None:
    """A tier is only enforceable against a rule that exists.

    The checks below skip a carrier that declares no `color` (it inherits body
    copy, the highest pair available) and no `font-size` (same). That skip is
    correct for a *declared* carrier and wrong for a missing one: a class the
    stylesheet never mentions would collect no assertions at all and still show
    green — the same hole `test_every_legal_carrier_is_in_exactly_one_tier`
    closes one step earlier.
    """
    rules = _stylesheet()

    missing = sorted(selector for selector in LEGAL_SURFACES if selector not in rules)
    assert not missing, (
        "legally required carriers with no stylesheet rule: "
        + ", ".join(missing)
        + " — declare each one (docs/08 names them, docs/05 sets the bars)"
    )


def test_tier1_verification_content_is_never_smaller_than_body_copy() -> None:
    """`legal-t1-size` (docs/05). The reference is the stylesheet's own body
    font-size — 10 pt today — not a constant, and not "the smallest text on the
    page": anchoring to the page minimum would let a shrunken caption elsewhere
    lower the bar for the tenant's verification content.

    Every violation is reported at once; the implementer needs the whole set, not
    whichever selector iteration order happens to reach first."""
    rules = _stylesheet()
    body = _pt(rules["body"]["font-size"], selector="body", prop="font-size")

    too_small = []
    for selector in sorted(TIER_1_VERIFICATION):
        declared = _declarations(rules, selector).get("font-size")
        if declared is None:
            continue  # inherits body — at the reference by construction
        size = _pt(declared, selector=selector, prop="font-size")
        if size < body:
            too_small.append(f"{selector} is {size} pt")

    assert not too_small, (
        f"tier-1 verification content is set below the {body} pt body copy: " + ", ".join(too_small)
    )


def test_tier1_verification_content_meets_the_aaa_contrast_floor() -> None:
    """`legal-t1-contrast` (docs/05): ≥ 7:1 → Ink (13,91 on Mint, 15,72 on Paper)
    or Forest (10,01 / 11,32). Slate on Mint is 4,81 and is exactly what
    `.key-label` uses today; Slate on Paper is 5,44 and is what `tfoot
    .foot-note` and `.note` use."""
    violations = _contrast_violations(_stylesheet(), TIER_1_VERIFICATION, MIN_TIER1_CONTRAST)

    assert not violations, (
        f"tier-1 verification content needs {MIN_TIER1_CONTRAST}:1 "
        "(WCAG 2.1 AAA, SC 1.4.6): " + "; ".join(violations)
    )


def test_tier2_provenance_is_legible_not_prominent() -> None:
    """`legal-t2-contrast` (docs/05): ≥ 4,5:1, WCAG 2.1 AA SC 1.4.3 — the same
    bar as body copy, so provenance text is never *below* the page's ordinary
    standard. Slate on Paper is 5,44 and clears it.

    **There is no size branch in this test and there must not be one.** `docs/05`:
    the `Rechtsstand` stamps and the disclaimer are not BGH minimums, and no
    honest size threshold exists for them — *"any ratio I picked would land
    conveniently on the current 8 pt, which is the same error as the 9,0 pt
    floor."* `legal-t2-scale` is likewise absent: user zoom is a viewer property
    of a print PDF, not a stylesheet declaration this file can read. Adding
    either assertion means changing `docs/05` first.
    """
    violations = _contrast_violations(_stylesheet(), TIER_2_PROVENANCE, MIN_TIER2_CONTRAST)

    assert not violations, (
        f"tier-2 provenance text needs {MIN_TIER2_CONTRAST}:1 "
        "(WCAG 2.1 AA, SC 1.4.3): " + "; ".join(violations)
    )


def test_legal_disclosure_meets_the_line_height_floor() -> None:
    """Typographic hygiene, both tiers (docs/05)."""
    rules = _stylesheet()

    cramped = []
    for selector in sorted(LEGAL_SURFACES):
        declared = _declarations(rules, selector).get("line-height")
        if declared is None:
            continue
        if float(declared) < MIN_LEGAL_LINE_HEIGHT:
            cramped.append(f"{selector}: line-height {declared}")

    assert not cramped, (
        f"legally required text needs line-height ≥ {MIN_LEGAL_LINE_HEIGHT}: " + ", ".join(cramped)
    )


def test_numeric_columns_stay_tabular() -> None:
    """Figures a tenant compares column-wise must align (docs/05, typographic
    hygiene). Already true — pinned so a font change does not quietly drop it."""
    rules = _stylesheet()

    assert "tabular-nums" in rules["td.num, th.num"]["font-variant-numeric"]
