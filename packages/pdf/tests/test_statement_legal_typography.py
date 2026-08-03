"""Gate: legally required disclosure is not the hardest thing to read on the page.

Spec: `docs/08` → "Heizkostenabrechnung — the heating table's disclosure" →
"Typographic floor for legally required disclosure". Tokens: `docs/05`.

Today the **Umlageschlüssel + Gesamtbemessung** line — BGH formal minimum #2 plus
the denominator that minimum #3 rests on — is the smallest and lowest-contrast
text on the statement: 8,5 pt Slate on Mint, a measured **4,81:1**. It clears AA
with 0,31 to spare and it is still the wrong way round: the decorative CO₂ panel
is 10 pt Ink on Mint at 13,91:1, and the tenant's own money is 10 pt Ink at
15,72:1. A disclosure a reader squints at is a disclosure in form only.

The floor this file pins, for text `docs/08` marks as legally required (the four
BGH minimums, every heating disclosure, the `Rechtsstand` footer):

1. **≥ 9 pt**, and never smaller than any other text on the page — asserted as a
   stylesheet-wide floor, because "smallest" is a property of the whole page.
2. **≥ 7:1 contrast** on its own background → Petrol Ink or Forest Deep. Slate
   keeps its `docs/05` role (secondary text on Paper, 5,44:1) and leaves legal
   text.
3. **line-height ≥ 1,4** wherever one is declared.

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

MIN_LEGAL_FONT_PT = 9.0
MIN_LEGAL_CONTRAST = 7.0
MIN_LEGAL_LINE_HEIGHT = 1.4

# Selector → the token its text actually sits on. Hand-mapped because CSS
# inheritance is not resolvable from a stylesheet alone; `test_backgrounds_are_
# as_this_file_assumes` keeps the mapping honest.
LEGAL_SURFACES = {
    ".key-label": "--color-mint",  # Umlageschlüssel + Gesamtbemessung (BGH #2/#3)
    "tfoot .foot-note": "--color-paper",  # the heating footer's reconciliation
    ".note": "--color-paper",  # § 9a estimation / fallback disclosure
    ".co2": "--color-mint",  # CO2KostAufG § 7 Abs. 3
    "footer": "--color-paper",  # Rechtsstand + disclaimer
}

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


def test_legal_disclosure_meets_the_size_floor() -> None:
    """docs/08: ≥ 9 pt. `.key-label` and `tfoot .foot-note` are 8,5 pt today."""
    rules = _stylesheet()

    for selector in LEGAL_SURFACES:
        declared = rules[selector].get("font-size")
        if declared is None:
            continue  # inherits body (10 pt) — above the floor by construction
        size = _pt(declared, selector=selector, prop="font-size")
        assert size >= MIN_LEGAL_FONT_PT, (
            f"{selector} is {size} pt — legally required text has a {MIN_LEGAL_FONT_PT} pt floor"
        )


def test_no_text_on_the_page_is_smaller_than_the_legal_floor() -> None:
    """The floor is also comparative: legally required content must not be the
    smallest text on the page. Asserted page-wide so raising `.key-label` while
    shrinking something else cannot satisfy the previous test hollowly."""
    rules = _stylesheet()

    for selector, declarations in rules.items():
        declared = declarations.get("font-size")
        if declared is None:
            continue
        size = _pt(declared, selector=selector, prop="font-size")
        assert size >= MIN_LEGAL_FONT_PT, f"{selector} declares {size} pt"


def test_legal_disclosure_meets_the_contrast_floor() -> None:
    """docs/08: ≥ 7:1 → Ink (13,91 on Mint) or Forest (10,01). Slate on Mint is
    4,81 and is exactly what `.key-label` uses today."""
    rules = _stylesheet()
    tokens = _tokens(rules)

    for selector, background in LEGAL_SURFACES.items():
        declared = rules[selector].get("color")
        if declared is None:
            continue  # inherits body → Petrol Ink, the highest pair available
        match = _VAR.search(declared)
        assert match is not None, f"{selector} {{ color: {declared} }} — tokens only (docs/05)"
        ratio = contrast(tokens[match.group(1)], tokens[background])
        assert ratio >= MIN_LEGAL_CONTRAST, (
            f"{selector}: {match.group(1)} on {background} is {ratio:.2f}:1 — "
            f"legally required text needs {MIN_LEGAL_CONTRAST}:1"
        )


def test_legal_disclosure_meets_the_line_height_floor() -> None:
    rules = _stylesheet()

    for selector in LEGAL_SURFACES:
        declared = rules[selector].get("line-height")
        if declared is None:
            continue
        assert float(declared) >= MIN_LEGAL_LINE_HEIGHT, f"{selector}: line-height {declared}"


def test_numeric_columns_stay_tabular() -> None:
    """Figures a tenant compares column-wise must align (docs/08 floor, item 4).
    Already true — pinned so a font change does not quietly drop it."""
    rules = _stylesheet()

    assert "tabular-nums" in rules["td.num, th.num"]["font-variant-numeric"]
