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
            )
        finally:
            browser.close()
