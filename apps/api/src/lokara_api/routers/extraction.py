"""Beleg-Upload (docs/04 M4, canned) — upload → prefill → confirm.

Three properties define this router, and all three are deliberate:

1. **It writes nothing.** Extraction returns a *proposal*. The cost entry is
   created by the ordinary ``POST /buildings/{id}/costs`` after the user
   confirms — same validation, same integer cents, same append-only allocation
   key. An OCR miss can therefore never reach a statement without a human
   having looked at it.
2. **It suggests no cost type.** The extracted ``cost_category`` becomes the
   free-text label the manual form already takes. Mapping a category to a
   BetrKV type (and to that type's default Umlageschlüssel) needs the cost-type
   catalogue, which is a **pending spec** (docs/08) — guessing it here would
   put invented German law into the product.
3. **The provider is a stub.** ``StubVisionGateway`` is a fixture behind the
   Phase D port; a real EU + AVV provider swaps in behind the same Protocol.
   The response says so, so no screen can imply an integration that is absent.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, HTTPException, UploadFile
from lokara_adapters import (
    ExtractedInvoiceFields,
    SourceDocument,
    StubVisionGateway,
    VisionGateway,
)
from lokara_db import CostEntry
from lokara_domain import AllocationKey, cents, format_eur
from sqlalchemy import select

from ..deps import PathAccountSession
from ..schemas import (
    ExtractionDuplicate,
    ExtractionFieldOut,
    ExtractionOut,
    ExtractionPrefill,
)
from ..statement_service import BILLING_END, BILLING_START

router = APIRouter(prefix="/a/{account_id}")

# Below this, the review UI marks the field "bitte prüfen". A product rule, so
# it lives on the server: one threshold, not one per client.
LOW_CONFIDENCE_PERCENT = 90

MAX_UPLOAD_MB = 10
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
ALLOWED_SUFFIXES = (".pdf", ".png", ".jpg", ".jpeg")

# Named in the UI so a demo can never be mistaken for a live integration.
PROVIDER_LABEL = "Demo-Extraktion (Stub — kein externer Anbieter)"

# The document carries an invoice date, not a billing period, and it says
# nothing about how the cost is apportioned. Both come from the form's defaults
# and are listed as such.
NOT_EXTRACTED = ["Abrechnungszeitraum", "Umlageschlüssel"]


def _percent(confidence: Decimal) -> int:
    return int((confidence * 100).to_integral_value(rounding=ROUND_HALF_UP))


def _field(
    field_id: str, label: str, value: str, confidence: Decimal, *, stored: bool, note: str | None
) -> ExtractionFieldOut:
    percent = _percent(confidence)
    return ExtractionFieldOut(
        id=field_id,
        label=label,
        value=value,
        confidence_percent=percent,
        needs_review=percent < LOW_CONFIDENCE_PERCENT,
        stored=stored,
        note=note,
    )


def _german_date(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def _fields(extracted: ExtractedInvoiceFields) -> list[ExtractionFieldOut]:
    confidences = extracted.field_confidences
    return [
        _field(
            "costCategory",
            "Kostenart",
            extracted.cost_category,
            confidences.cost_category,
            stored=True,
            note="Aus dem Beleg abgeleitet, nicht abgelesen — bitte prüfen.",
        ),
        _field(
            "totalAmount",
            "Betrag",
            format_eur(cents(extracted.total_amount)),
            confidences.total_amount,
            stored=True,
            note=None,
        ),
        _field(
            "invoiceDate",
            "Rechnungsdatum",
            _german_date(extracted.invoice_date),
            confidences.invoice_date,
            stored=False,
            note="Wird noch nicht gespeichert — der Belegdatensatz folgt mit der Belegablage.",
        ),
        _field(
            "vendorName",
            "Lieferant",
            extracted.vendor_name,
            confidences.vendor_name,
            stored=False,
            note="Wird noch nicht gespeichert — der Belegdatensatz folgt mit der Belegablage.",
        ),
    ]


def _duplicate(
    session: PathAccountSession, building_id: str, extracted: ExtractedInvoiceFields
) -> ExtractionDuplicate | None:
    """Same label, same amount, overlapping period — almost certainly the same
    invoice entered twice.

    A warning, never a block: two identical Abschlagsrechnungen in one period
    are legitimate, and refusing them would be the tool overruling the user.
    """
    existing = session.scalars(
        select(CostEntry)
        .where(
            CostEntry.building_id == building_id,
            CostEntry.amount_cents == extracted.total_amount,
            CostEntry.period_from < BILLING_END,
            CostEntry.period_to > BILLING_START,
        )
        .order_by(CostEntry.created_at, CostEntry.id)
    ).all()
    match = next(
        (c for c in existing if c.label.casefold() == extracted.cost_category.casefold()), None
    )
    if match is None:
        return None
    return ExtractionDuplicate(
        cost_id=match.id,
        label=match.label,
        amount_eur=format_eur(cents(match.amount_cents)),
    )


def _read_upload(file: UploadFile) -> SourceDocument:
    name = file.filename or "beleg"
    if not name.lower().endswith(ALLOWED_SUFFIXES):
        raise HTTPException(
            status_code=422,
            detail="Nur PDF-, PNG- oder JPG-Dateien können ausgelesen werden.",
        )
    # Cap the read itself rather than trusting the declared size — one byte
    # over the limit is enough to know it is too large.
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413, detail=f"Die Datei ist größer als {MAX_UPLOAD_MB} MB."
        )
    if not content:
        raise HTTPException(status_code=422, detail="Die Datei ist leer.")
    return SourceDocument(file_name=name, content=content)


@router.post("/buildings/{building_id}/extractions")
def extract_invoice(
    account_id: str,
    building_id: str,
    file: UploadFile,
    session: PathAccountSession,
) -> ExtractionOut:
    """Read an uploaded Beleg and return a proposal. Persists nothing.

    Scoped like every other route: the dependency has already verified the
    caller's membership and opened the RLS transaction, so the duplicate lookup
    below can only ever see this account's costs.
    """
    del account_id  # scoping happened in the dependency
    document = _read_upload(file)
    gateway: VisionGateway = StubVisionGateway()
    extracted = gateway.extract_invoice(document)

    return ExtractionOut(
        document_name=document.file_name,
        provider_label=PROVIDER_LABEL,
        document_confidence_percent=_percent(extracted.confidence),
        fields=_fields(extracted),
        prefill=ExtractionPrefill(
            label=extracted.cost_category,
            amount_cents=extracted.total_amount,
            period_from=BILLING_START,
            period_to=BILLING_END,
            # Not read from the document — see NOT_EXTRACTED. The form's own
            # default, surfaced so the user chooses knowingly.
            key=AllocationKey.AREA,
        ),
        not_extracted=NOT_EXTRACTED,
        duplicate=_duplicate(session, building_id, extracted),
    )
