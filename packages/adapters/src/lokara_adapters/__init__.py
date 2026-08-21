"""External-edge ports as Protocols + fixture stubs.

Every paid/external edge (bank, vision/OCR, email, meter/MDL, Destatis, DATEV)
is a Python ``Protocol`` port with a stub that returns fixture data — used in
dev, tests, and the pitch demo. Each adapter normalizes to an internal model
**before** any engine sees it; no engine or domain module ever imports a vendor
SDK (CLAUDE.md). ``TODO(provider)`` marks where each real EU+AVV implementation
plugs in.
"""

from .bank import BankGateway, BankTransaction, StubBankGateway, TransactionDirection
from .datev import (
    DatevDeliveryReference,
    DatevExportFile,
    DatevGateway,
    DeliveredExport,
    StubDatevGateway,
)
from .destatis import (
    VPI_SERIES_CODE,
    PriceIndexGateway,
    PriceIndexValue,
    StubPriceIndexGateway,
)
from .email import (
    DeliveryStatus,
    EmailDeliveryReceipt,
    EmailGateway,
    OutgoingEmail,
    SentEmail,
    StubEmailGateway,
)
from .meter import (
    MeasurementUnit,
    MeterConsumption,
    MeterDevice,
    MeterDeviceSegmentation,
    MeterGateway,
    MeterKind,
    MeterReading,
    MeterReadingSpan,
    ReadingReason,
    ReadingSource,
    StubMeterGateway,
    consumption_by_meter,
    device_reading_segments,
)
from .vision import (
    ExtractedInvoiceFields,
    FieldConfidences,
    SourceDocument,
    StubVisionGateway,
    VisionGateway,
)

__version__ = "0.1.0"

__all__ = [
    "VPI_SERIES_CODE",
    "BankGateway",
    "BankTransaction",
    "DatevDeliveryReference",
    "DatevExportFile",
    "DatevGateway",
    "DeliveredExport",
    "DeliveryStatus",
    "EmailDeliveryReceipt",
    "EmailGateway",
    "ExtractedInvoiceFields",
    "FieldConfidences",
    "MeasurementUnit",
    "MeterConsumption",
    "MeterDevice",
    "MeterDeviceSegmentation",
    "MeterGateway",
    "MeterKind",
    "MeterReading",
    "MeterReadingSpan",
    "OutgoingEmail",
    "PriceIndexGateway",
    "PriceIndexValue",
    "ReadingReason",
    "ReadingSource",
    "SentEmail",
    "SourceDocument",
    "StubBankGateway",
    "StubDatevGateway",
    "StubEmailGateway",
    "StubMeterGateway",
    "StubPriceIndexGateway",
    "StubVisionGateway",
    "TransactionDirection",
    "VisionGateway",
    "consumption_by_meter",
    "device_reading_segments",
]
