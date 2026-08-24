"""External-edge ports as Protocols + fixture stubs.

Every paid/external edge (bank, vision/OCR, email, meter/MDL, Destatis, DATEV)
is a Python ``Protocol`` port with a stub that returns fixture data — used in
dev, tests, and the pitch demo. Each adapter normalizes to an internal model
**before** any engine sees it; no engine or domain module ever imports a vendor
SDK (CLAUDE.md). ``TODO(provider)`` marks where each real EU+AVV implementation
plugs in.
"""

from .bank import (
    BankGateway,
    BankTransaction,
    StubBankGateway,
    cents_from_provider_amount,
    normalize_transaction,
)
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
from .dwd import (
    DWD_ANNUAL_SOURCE_VERSION,
    DWD_ATTRIBUTION,
    LATEST_VERIFIED_ANNUAL_PUBLICATION,
    AnnualClimateFactor,
    AnnualClimateFactorGateway,
    AnnualClimateFactorPublication,
    AnnualClimateFactorResolution,
    DwdAnnualImportError,
    StubAnnualClimateFactorGateway,
    merge_annual_climate_factors,
    parse_annual_climate_factor_csv,
    parse_annual_climate_factor_xml,
    resolve_annual_climate_factor,
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
from .scheduler import (
    ScheduledJob,
    SchedulerPort,
    StubScheduler,
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
    "DWD_ANNUAL_SOURCE_VERSION",
    "DWD_ATTRIBUTION",
    "LATEST_VERIFIED_ANNUAL_PUBLICATION",
    "VPI_SERIES_CODE",
    "AnnualClimateFactor",
    "AnnualClimateFactorGateway",
    "AnnualClimateFactorPublication",
    "AnnualClimateFactorResolution",
    "BankGateway",
    "BankTransaction",
    "DatevDeliveryReference",
    "DatevExportFile",
    "DatevGateway",
    "DeliveredExport",
    "DeliveryStatus",
    "DwdAnnualImportError",
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
    "ScheduledJob",
    "SchedulerPort",
    "SentEmail",
    "SourceDocument",
    "StubAnnualClimateFactorGateway",
    "StubBankGateway",
    "StubDatevGateway",
    "StubEmailGateway",
    "StubMeterGateway",
    "StubPriceIndexGateway",
    "StubScheduler",
    "StubVisionGateway",
    "VisionGateway",
    "cents_from_provider_amount",
    "consumption_by_meter",
    "device_reading_segments",
    "merge_annual_climate_factors",
    "normalize_transaction",
    "parse_annual_climate_factor_csv",
    "parse_annual_climate_factor_xml",
    "resolve_annual_climate_factor",
]
