"""HTML → PDF document service (Playwright for Python).

The engines compute; this package formats and prints. Statement templates
carry the ``Rechtsstand`` stamps and the "keine Rechts- oder Steuerberatung"
disclaimer on every legal output (CLAUDE.md).
"""

from .anlage_v_overview import (
    TAX_DISCLAIMER,
    AnlageVOverviewData,
    AnlageVOverviewLine,
    AnlageVSourceRef,
    anlage_v_overview_html,
)
from .building_overview import (
    BuildingOverviewData,
    BuildingOverviewFact,
    BuildingOverviewKpi,
    BuildingOverviewUnit,
    building_overview_filename,
    building_overview_html,
)
from .formatting import format_number_de
from .heating_disclosure import OWNER_LABEL
from .investment_bank_pdf import (
    DEFAULT_BANK_LAYOUT_SNAPSHOT,
    InvestmentBankPdfData,
    investment_bank_pdf_html,
    render_investment_bank_pdf,
)
from .rechtsstand import rechtsstand_entry
from .render import PdfOptions, render_html_to_pdf
from .statement import (
    DISCLAIMER,
    PartyKey,
    StatementData,
    statement_html,
)
from .uvi_document import UviDocumentBlock, UviDocumentData, uvi_document_html

__version__ = "0.1.0"

__all__ = [
    "DEFAULT_BANK_LAYOUT_SNAPSHOT",
    "DISCLAIMER",
    "OWNER_LABEL",
    "TAX_DISCLAIMER",
    "AnlageVOverviewData",
    "AnlageVOverviewLine",
    "AnlageVSourceRef",
    "BuildingOverviewData",
    "BuildingOverviewFact",
    "BuildingOverviewKpi",
    "BuildingOverviewUnit",
    "InvestmentBankPdfData",
    "PartyKey",
    "PdfOptions",
    "StatementData",
    "UviDocumentBlock",
    "UviDocumentData",
    "anlage_v_overview_html",
    "building_overview_filename",
    "building_overview_html",
    "format_number_de",
    "investment_bank_pdf_html",
    "rechtsstand_entry",
    "render_html_to_pdf",
    "render_investment_bank_pdf",
    "statement_html",
    "uvi_document_html",
]
