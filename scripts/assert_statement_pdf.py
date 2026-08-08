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
    # --- slice 5: the Massainheit travels meter -> statement. Without these the whole
    # Verbrauch Heizung column could regress to the withheld sentence and this gate would
    # stay green -- and that column is 5.325,03 EUR, 52 % of the umlagefaehige Kosten.
    "1.000 HKV-Einheiten": "docs/08 slice 5: Verbrauch Heizung Gesamtbemessung (BGH #3)",
    "600 HKV-Einheiten": "docs/08 slice 5: unit A's own heat Bemessung",
    "Heizkostenverteiler": "docs/08 rule 6: the device named once (BGH #2 Erlaeuterung)",
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
    # --- Anteile je Partei. The whole block could stop rendering and every other golden
    # above would still pass, because none of them live in it. These cannot appear by
    # accident: the sum exists nowhere else on the page, the label is unique to the block.
    "11.342,92": "docs/08: Summe der Anteile — the figure that proves the block rendered",
    "Summe der Anteile": "docs/08: the block's total row",
    "geleistete Vorauszahlungen": "docs/08: BGH #4 named as absent, in §556 Abs.3 BGB's own word",
    # docs/07's positioning claim, in the form CLAUDE.md mandates.
    "keine Rechts- oder Steuerberatung": "CLAUDE.md: the disclaimer every legal output carries",
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
    "1.000.000": "scaled integer leaked: heat Bemessung total not divided by 1000",
    # `600.000` is NOT listed, deliberately, for the same reason 10.000 and 40.000 are not:
    # six digits is a plausible euro amount on a larger building, so a negative canary
    # there would fire falsely one day. `600 HKV-Einheiten` in MUST_APPEAR catches the same
    # regression from the other side. Worth noting LONG_DIGIT_RUN misses it twice over --
    # six digits is under the 7+ threshold, and the grouped form is not a digit run at all.
    #
    # --- claim-strength canaries. docs/07 fixes the positioning word as `rechtskonform`
    # and forbids `rechtssicher`; and the disclaimer must describe the TOOL, never attest
    # to this artifact. "Dieses Dokument wurde rechtskonform erstellt" was a per-document
    # warranty on a statement that does not render BGH minimum #4 at all.
    "rechtssicher": "docs/07: forbidden claim — the word is `rechtskonform`, never this",
    "Dokument wurde rechtskonform": "docs/07: per-artifact warranty; the claim is about the tool",
}

# Structural properties of the PDF itself, read from the document catalog rather than the
# text layer. Tagging was raised in three consecutive reviews and caught by nothing,
# because every check in this tree reads extracted text and none of this appears there.
# BFSG has been in force since 28.06.2025 and an untagged PDF fails WCAG 1.3.1 and 3.1.1
# at document level, so this is the accessibility DoD on the primary deliverable.
STRUCTURE_REQUIRED: dict[str, str] = {
    "/StructTreeRoot": "WCAG 1.3.1 — no tag tree, no way to navigate the columns",
    "/MarkInfo": "the marked-content flag that says the tag tree is real",
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


def check_structure(pdf: Path) -> list[str]:
    """Read the document catalog, not the text layer.

    `/Lang` and `/Title` are independent of tagging: `/Lang` comes from `<html lang>` and
    `/Title` from `<title>`, and Chromium's print path drops the first and ignores the
    second unless it is set. A file with no `/Title` is announced by its filename in a
    screen reader and in a document list.
    """
    from pypdf import PdfReader

    reader = PdfReader(str(pdf))
    root = reader.trailer["/Root"]
    problems: list[str] = []

    for key, why in STRUCTURE_REQUIRED.items():
        if key not in root:
            problems.append(f"MISSING  {key} in the document catalog — {why}")

    if not root.get("/Lang"):
        problems.append(
            "MISSING  /Lang — WCAG 3.1.1. A screen reader reads German with an English "
            'voice. Set <html lang="de">; Chromium only carries it through when tagged.'
        )
    if not (reader.metadata or {}).get("/Title"):
        problems.append(
            "MISSING  /Title — the document announces itself by filename. Comes from "
            "<title>, independently of tagging."
        )
    return problems


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

    failures.extend(check_structure(pdf))

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
