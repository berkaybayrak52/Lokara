"""HTML → PDF document service (Playwright for Python).

The engines compute; this package formats and prints. Statement templates
carry the ``Rechtsstand`` stamps and the "keine Rechts- oder Steuerberatung"
disclaimer on every legal output (CLAUDE.md).
"""

from .rechtsstand import rechtsstand_entry
from .render import PdfOptions, render_html_to_pdf
from .statement import (
    DISCLAIMER,
    PartyKey,
    StatementData,
    format_number_de,
    statement_html,
)

__version__ = "0.1.0"

__all__ = [
    "DISCLAIMER",
    "PartyKey",
    "PdfOptions",
    "StatementData",
    "format_number_de",
    "rechtsstand_entry",
    "render_html_to_pdf",
    "statement_html",
]
