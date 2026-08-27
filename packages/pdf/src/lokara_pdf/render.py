"""HTML → PDF via headless Chromium (Playwright for Python, sync API).

Sync on purpose: PDF generation is CPU/IO-bound batch work that the API will
run in a worker/threadpool (same reasoning as the sync-def DB routes) — an
async render path can land later without changing this contract. One browser
per call for now; pooling arrives when volume demands it.
"""

from dataclasses import dataclass

from playwright.sync_api import sync_playwright


@dataclass(frozen=True)
class PdfOptions:
    """A4 by default; statements are printed documents."""

    format: str = "A4"
    display_header_footer: bool = False
    footer_template: str = ""


def render_html_to_pdf(html: str, options: PdfOptions | None = None) -> bytes:
    options = options or PdfOptions()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page = browser.new_page()
            page.set_content(html, wait_until="networkidle")
            return page.pdf(
                format=options.format,
                print_background=True,
                margin={"top": "20mm", "bottom": "20mm", "left": "18mm", "right": "18mm"},
                # BFSG / WCAG 2.1 AA. Without this Chromium's print path emits an
                # untagged PDF: no /StructTreeRoot, no /MarkInfo, and `<html lang="de">`
                # is dropped so the file carries no /Lang either. A screen reader then
                # gets an undifferentiated stream of text where the statement has four
                # money columns, and the four BGH minimums are unreachable by structure.
                # Measured on Playwright 1.61.0 / Chromium against the demo statement:
                # tagged=False → root keys /Pages /Type /ViewerPreferences, /Lang None
                # tagged=True  → + /StructTreeRoot /MarkInfo, /Lang "de", 17423 → 19104 B.
                # /Title is NOT supplied by this flag — it comes from <title>, which
                # `statement.py` now sets.
                tagged=True,
                display_header_footer=options.display_header_footer,
                header_template="<span></span>",
                footer_template=options.footer_template,
            )
        finally:
            browser.close()
