"""Vision / OCR port — Beleg extraction and legacy-data import (one pipeline, M4).

An uploaded invoice becomes candidate field values plus a confidence; the review
UI shows low-confidence fields for correction. Extraction never writes a cost
entry on its own — a human confirms, which is what keeps an OCR miss from
becoming a wrong statement.

**Confidence is per field, not only per document.** A single document-level
score cannot answer the one question the review UI exists to answer — *which*
field should I look at? Real providers (Document AI, Form Recognizer) report
both: a document-level read quality and a per-entity confidence. The port
mirrors that.

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


def _check_unit_interval(name: str, value: Decimal) -> None:
    if not Decimal(0) <= value <= Decimal(1):
        raise ValueError(f"{name} must be within [0, 1], got {value}")


@dataclass(frozen=True)
class FieldConfidences:
    """Per-field confidence, each a Decimal in [0, 1] — a ratio, not money, but
    kept exact so fixtures stay deterministic."""

    vendor_name: Decimal
    invoice_date: Decimal
    total_amount: Decimal
    cost_category: Decimal

    def __post_init__(self) -> None:
        _check_unit_interval("vendor_name confidence", self.vendor_name)
        _check_unit_interval("invoice_date confidence", self.invoice_date)
        _check_unit_interval("total_amount confidence", self.total_amount)
        _check_unit_interval("cost_category confidence", self.cost_category)


@dataclass(frozen=True)
class ExtractedInvoiceFields:
    """Normalized extraction result.

    ``confidence`` is how well the *document* was read; ``field_confidences``
    is per value. They are independent: a crisp scan (high document score) can
    still carry a shaky ``cost_category``, because that field is a
    classification rather than a read.
    """

    vendor_name: str
    invoice_date: date
    total_amount: Cents
    cost_category: str
    confidence: Decimal
    field_confidences: FieldConfidences

    def __post_init__(self) -> None:
        _check_unit_interval("confidence", self.confidence)


class VisionGateway(Protocol):
    """Port: extract invoice fields from an uploaded document."""

    def extract_invoice(self, document: SourceDocument) -> ExtractedInvoiceFields: ...


class StubVisionGateway:
    """Canned-demo stub (the M4 pitch flow): every upload "extracts" the garbage
    invoice of the demo scenario, so the UX flow is identical to the real one.

    The per-field scores are not decoration. ``cost_category`` sits far below
    the rest because it is the one value a provider *infers* rather than reads
    — and the BetrKV cost-type catalogue it would infer against is still a
    pending spec (docs/08). A low score there is the honest state, and it sends
    the reviewer to the field that actually needs a human.

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
            field_confidences=FieldConfidences(
                vendor_name=Decimal("0.98"),  # printed header block
                invoice_date=Decimal("0.99"),
                total_amount=Decimal("0.97"),  # the Gesamtbetrag line
                cost_category=Decimal("0.62"),  # inferred, not read
            ),
        )
