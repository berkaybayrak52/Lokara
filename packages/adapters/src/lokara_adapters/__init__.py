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
    DWD_MONTHLY_ATTRIBUTION,
    DWD_MONTHLY_SOURCE_PATH,
    LATEST_VERIFIED_ANNUAL_PUBLICATION,
    AnnualClimateFactor,
    AnnualClimateFactorGateway,
    AnnualClimateFactorPublication,
    AnnualClimateFactorResolution,
    DwdAnnualImportError,
    MonthlyDegreeDayImportError,
    MonthlyDegreeDayRecord,
    MonthlyStationAssignment,
    PlzCentroid,
    StubAnnualClimateFactorGateway,
    assign_monthly_station,
    merge_annual_climate_factors,
    parse_annual_climate_factor_csv,
    parse_annual_climate_factor_xml,
    parse_monthly_degree_day_rows,
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
from .geocoding import (
    DisabledGeocodingGateway,
    GeocodingGateway,
    GeocodingResult,
    NominatimGeocodingGateway,
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
    "DWD_MONTHLY_ATTRIBUTION",
    "DWD_MONTHLY_SOURCE_PATH",
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
    "DisabledGeocodingGateway",
    "DwdAnnualImportError",
    "EmailDeliveryReceipt",
    "EmailGateway",
    "ExtractedInvoiceFields",
    "FieldConfidences",
    "GeocodingGateway",
    "GeocodingResult",
    "MeasurementUnit",
    "MeterConsumption",
    "MeterDevice",
    "MeterDeviceSegmentation",
    "MeterGateway",
    "MeterKind",
    "MeterReading",
    "MeterReadingSpan",
    "MonthlyDegreeDayImportError",
    "MonthlyDegreeDayRecord",
    "MonthlyStationAssignment",
    "NominatimGeocodingGateway",
    "OutgoingEmail",
    "PlzCentroid",
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
    "assign_monthly_station",
    "cents_from_provider_amount",
    "consumption_by_meter",
    "device_reading_segments",
    "merge_annual_climate_factors",
    "normalize_transaction",
    "parse_annual_climate_factor_csv",
    "parse_annual_climate_factor_xml",
    "parse_monthly_degree_day_rows",
    "resolve_annual_climate_factor",
]
