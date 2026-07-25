"""Vision / OCR port — Beleg extraction and legacy-data import (one pipeline, M4).

An uploaded invoice becomes candidate field values plus a confidence; the review
UI shows low-confidence fields for correction. Extraction never writes a cost
entry on its own — a human confirms, which is what keeps an OCR miss from
becoming a wrong statement.

TODO(provider): the real implementation needs **EU processing + an AVV** and is
a listed sub-processor; chosen before any real customer document flows.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from lokara_domain import Cents, cents


@dataclass(frozen=True)
class SourceDocument:
    """The raw upload. The bytes stay opaque to everything but the adapter."""

    file_name: str
    content: bytes


@dataclass(frozen=True)
class ExtractedInvoiceFields:
    """Normalized extraction result. ``confidence`` is a Decimal in [0, 1] — a
    ratio, not money, but kept exact so fixtures stay deterministic."""

    vendor_name: str
    invoice_date: date
    total_amount: Cents
    cost_category: str
    confidence: Decimal

    def __post_init__(self) -> None:
        if not Decimal(0) <= self.confidence <= Decimal(1):
            raise ValueError(f"confidence must be within [0, 1], got {self.confidence}")


class VisionGateway(Protocol):
    """Port: extract invoice fields from an uploaded document."""

    def extract_invoice(self, document: SourceDocument) -> ExtractedInvoiceFields: ...


class StubVisionGateway:
    """Canned-demo stub (the M4 pitch flow): every upload "extracts" the garbage
    invoice of the demo scenario, so the UX flow is identical to the real one.

    TODO(provider): EU + AVV vision provider.
    """

    def extract_invoice(self, document: SourceDocument) -> ExtractedInvoiceFields:
        del document  # the canned demo ignores the upload's content
        return ExtractedInvoiceFields(
            vendor_name="Stadtreinigung Frankfurt GmbH",
            invoice_date=date(2025, 12, 15),
            total_amount=cents(120000),
            cost_category="Müllabfuhr",
            confidence=Decimal("0.97"),
        )
