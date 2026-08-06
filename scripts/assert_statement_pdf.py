#!/usr/bin/env python3
"""Read the rendered statement PDF and assert the numbers a human would read.

This closes the blind spot `docs/03` names explicitly:

    "De-scale at the render boundary. Engine values are scaled integers (money = cents;
     areas/weights = x100 fixed-point). The presentation layer must convert back before
     display, or a Bemessung of 18.250 m2*Tage renders as 1.825.000. **Tests comparing
     integers stay green through this bug** - read the rendered PDF before calling an
     output done."

196 passing pytest cases cannot catch that class of bug, because they compare engine
integers to engine integers. This script compares *rendered text* to the golden table
in `docs/03` and to the demo figures in `DEMO-RUNBOOK.md`, so a de-scaling regression
fails a command instead of surviving to the pitch.

Run via verify_demo_path.sh, or directly:

    uv run --with pypdf python scripts/assert_statement_pdf.py \
        packages/pdf/output/nk-heating-statement-demo.pdf
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# --- the goldens -----------------------------------------------------------------
# Every string here traces to a committed spec. If one of these changes, the spec
# changed, and the change belongs in docs/ before it belongs here.

MUST_APPEAR: dict[str, str] = {
    # docs/03 canonical EUR 1,200 garbage-cost fixture
    "1.200,00": "docs/03: NK total",
    "600,00": "docs/03: Unit A / Renter 1 (50 m2, 365 d)",
    "178,52": "docs/03: Unit B / Renter 2 (30 m2, 181 d)",
    "181,48": "docs/03: Unit B vacancy -> landlord (30 m2, 184 d)",
    "240,00": "docs/03: Unit C / Renter 3 (20 m2, 365 d)",
    # docs/06 heating + CO2 demo figures
    "10.300,00": "docs/06: heating invoice total",
    # Re-based when the demo CO2 fixture was corrected (2.000 kg / 300,00 EUR implied
    # 150 EUR/t against the 2025 statutory 55 EUR/t). The 585:415 ratio did NOT move --
    # 778,79 / 1.331,26 = 0,5850 exactly. Only the pot moved, because the
    # CO2-Vermieteranteil is deducted before the renter-facing split.
    "778,79": "docs/06: unit B heating, Mieter share (585 permille)",
    "552,47": "docs/06: unit B heating, Vermieter share (415 permille)",
    # --- de-scaled forms of the fields slice 4 newly put on the page (I7).
    # Asserted POSITIVELY rather than as absence-of-the-leak-form, on purpose. The leak
    # forms of two of these are `10.000` and `40.000`, which are entirely plausible euro
    # amounts on a larger building -- a negative canary on those would fire falsely the
    # first time someone bills a 40.000,00 EUR heating invoice. The de-scaled form is
    # unambiguous, so requiring it catches the same regression without planting a
    # future false positive.
    "100 m²": "heated_area_sqm de-scaled from area_sqm_x100 (leak form: 10.000)",
    "4.000 kg": "total_co2_kg de-scaled from co2_kg_x1000 (leak form: 4.000.000)",
    "40 m³": "ww_consumption_weight_m3 de-scaled from value_x1000 (leak form: 40.000)",
    # CLAUDE.md: every legal output shows its Rechtsstand
    "Rechtsstand": "CLAUDE.md: legal outputs carry Rechtsstand MM/JJJJ",
    # --- the de-scaling canaries: these are the *human* figures, not the scaled ints
    "18.250": "docs/03: Bemessung for Unit A in m2*Tage (NOT 1.825.000)",
    "36.500": "docs/03: total Bemessung in m2*Tage (NOT 3.650.000)",
    # The bare figures above would survive a regression that dropped or changed the unit,
    # and the unit is where a de-scaling error actually reads as wrong to a human. Written
    # with a PLAIN space: the document joins figure and unit with U+00A0, so the direct
    # `in text` check fails and only the whitespace-stripped `flat` path matches. Do not
    # extend this leftward to include "Wohnflaeche" — PDF extraction renders the ligature
    # as U+FB02 and the golden then fails both paths.
    "Gesamtbemessung: 36.500 m²·Tage": "docs/08: the denominator BGH minimum #3 needs",
}

MUST_NOT_APPEAR: dict[str, str] = {
    "1.825.000": "scaled integer leaked: AREA weight not divided by 100",
    "3.650.000": "scaled integer leaked: total AREA weight not divided by 100",
    "120000": "scaled integer leaked: NK total printed in cents",
    "1030000": "scaled integer leaked: heating total printed in cents",
    # x1000 scaling is nastier than x100: 4.000.000 and 4.000 differ only by punctuation
    # a German reader skims past, and LONG_DIGIT_RUN below only catches the UNFORMATTED
    # 4000000 -- the grouped form is what would actually reach the page. Listed here
    # because no legitimate figure on this statement is in the millions; its x100
    # siblings (10.000, 40.000) are deliberately NOT listed, see MUST_APPEAR above.
    "4.000.000": "scaled integer leaked: total_co2_kg not divided by 1000",
}

# No legitimate figure on this statement has seven or more consecutive digits.
# A run that long is almost always a cents value or a x100 weight that escaped
# formatting. Kept separate from MUST_NOT_APPEAR so the message can be specific.
LONG_DIGIT_RUN = re.compile(r"(?<!\d)\d{7,}(?!\d)")


def extract_text(pdf: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        print(
            "assert_statement_pdf: pypdf is not importable.\n"
            "  Run through: uv run --with pypdf python scripts/assert_statement_pdf.py ...",
            file=sys.stderr,
        )
        raise SystemExit(2) from None

    reader = PdfReader(str(pdf))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: assert_statement_pdf.py <statement.pdf>", file=sys.stderr)
        return 2
    pdf = Path(argv[0])
    if not pdf.is_file():
        print(f"assert_statement_pdf: {pdf} does not exist", file=sys.stderr)
        return 2

    text = extract_text(pdf)
    # PDF extraction sometimes splits a number across a line break inside a table cell.
    flat = re.sub(r"\s+", "", text)

    failures: list[str] = []

    for needle, why in MUST_APPEAR.items():
        if needle not in text and needle.replace(" ", "") not in flat:
            failures.append(f"MISSING  {needle!r} — {why}")

    for needle, why in MUST_NOT_APPEAR.items():
        if needle in text or needle in flat:
            failures.append(f"PRESENT  {needle!r} — {why}")

    for match in LONG_DIGIT_RUN.finditer(text):
        failures.append(
            f"SUSPECT  {match.group()!r} — 7+ digit run; no figure on this statement is "
            f"that long. Likely an un-de-scaled cents value or x100 weight (docs/03)."
        )

    if failures:
        print(
            f"statement PDF: {len(failures)} problem(s) in {pdf}\n",
            file=sys.stderr,
        )
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        print(
            "\nThe engines can be cent-exact and the document still wrong. If a golden "
            "genuinely changed, change docs/ first, then this file.",
            file=sys.stderr,
        )
        return 1

    print(
        f"statement PDF: clean — {len(MUST_APPEAR)} golden(s) present, "
        f"{len(MUST_NOT_APPEAR)} scale-leak canary(ies) absent ({len(text)} chars read)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
