"""Render gate: the statement actually becomes a PDF via headless Chromium.

Needs the Playwright Chromium binary. Locally without it the test skips;
in CI ``LOKARA_REQUIRE_PDF=1`` turns a missing browser into a hard failure so
the gate can't silently skip (same pattern as the DB isolation suite).
"""

import os

import pytest
from lokara_pdf import render_html_to_pdf, statement_html
from lokara_pdf.demo import build_demo_statement
from playwright._impl._errors import Error as PlaywrightError


def test_statement_renders_to_pdf() -> None:
    html = statement_html(build_demo_statement())
    try:
        pdf = render_html_to_pdf(html)
    except PlaywrightError as exc:
        if os.environ.get("LOKARA_REQUIRE_PDF"):
            raise
        pytest.skip(f"Playwright Chromium unavailable: {exc}")

    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 10_000  # a real multi-table document, not an empty page
