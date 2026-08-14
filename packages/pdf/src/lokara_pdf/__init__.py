"""HTML → PDF document service (Playwright for Python).

The engines compute; this package formats and prints. Statement templates
carry the ``Rechtsstand`` stamps and the "keine Rechts- oder Steuerberatung"
disclaimer on every legal output (CLAUDE.md).
"""

from .formatting import format_number_de
from .heating_disclosure import OWNER_LABEL
from .rechtsstand import rechtsstand_entry
from .render import PdfOptions, render_html_to_pdf
from .statement import (
    DISCLAIMER,
    PartyKey,
    StatementData,
    statement_html,
)

__version__ = "0.1.0"

__all__ = [
    "DISCLAIMER",
    "OWNER_LABEL",
    "PartyKey",
    "PdfOptions",
    "StatementData",
    "format_number_de",
    "rechtsstand_entry",
    "render_html_to_pdf",
    "statement_html",
]
