"""DWD adapter boundary for rolling annual PLZ climate factors.

The annual climate factor is distinct from the monthly ``hdd_3807`` dataset.
This module normalizes DWD CSV/XML records before they reach domain code.

TODO(provider): fetch the published files from the DWD Climate Data Center and
pass their contents through the normalization functions below.
"""

from __future__ import annotations

import csv
import re
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from io import StringIO
from math import atan2, cos, radians, sin, sqrt
from typing import Final, Protocol
from xml.etree import ElementTree

DWD_ANNUAL_SOURCE_VERSION: Final = "v22.3"
DWD_ATTRIBUTION: Final = "Quelle: Deutscher Wetterdienst"
DWD_MONTHLY_SOURCE_PATH: Final = (
    "opendata.dwd.de/climate_environment/CDC/derived_germany/techn/monthly/"
    "heating_degreedays/hdd_3807/"
)
DWD_MONTHLY_ATTRIBUTION: Final = "Quelle: Deutscher Wetterdienst"

_EARTH_MEAN_RADIUS_KM: Final = Decimal("6371.0088")
_DISTANCE_QUANTUM_KM: Final = Decimal("0.000001")
_MONTHLY_STANDARD: Final = "VDI 3807"
_MONTHLY_UNIT: Final = "Kd"
_MONTHLY_NATURE: Final = "external_source_DWD_GeoNutzV"
_MONTHLY_RECHTSSTAND: Final = "08/2026"
_MONTHLY_VERIFICATION_STATUS: Final = "verify-before-production"
_ASSIGNMENT_NATURE: Final = "Konvention"
_ASSIGNMENT_METHOD: Final = "nearest_common_valid_station_great_circle"
_ASSIGNMENT_METHOD_VERSION: Final = "1"
_MONTHLY_RECORD_PARSER_ORIGIN: Final = object()

_CSV_HEADER: Final = ("DatAnf", "DatEnd", "PLZ", "KF")
_MINIMUM_RECORD_COUNT: Final = 7_000
_MINIMUM_FACTOR: Final = Decimal("0.40")
_MAXIMUM_FACTOR: Final = Decimal("1.80")
_CSV_FILE_NAME: Final = re.compile(
    r"KF_(?P<period_from>[0-9]{8})_(?P<period_to>[0-9]{8})(?P<comma>_k)?\.csv"
)
_XML_FILE_NAME: Final = re.compile(r"KF_(?P<period_from>[0-9]{8})_(?P<period_to>[0-9]{8})\.xml")


class DwdAnnualImportError(ValueError):
    """The annual DWD source cannot be normalized safely."""


class MonthlyDegreeDayImportError(ValueError):
    """A monthly DWD degree-day row cannot be normalized safely."""


@dataclass(frozen=True, init=False)
class MonthlyDegreeDayRecord:
    """One normalized station row from the monthly DWD hdd_3807 dataset."""

    station_id: str
    latitude: Decimal
    longitude: Decimal
    station_name: str
    month: str
    valid_day_count: int
    monthly_degree_days: Decimal
    heating_day_count: int
    ten_year_mean: Decimal
    source_path: str
    source_file: str
    standard: str
    heating_limit_celsius: int
    reference_room_temperature_celsius: int
    unit: str
    attribution: str
    nature: str
    rechtsstand: str
    verification_status: str
    _parser_origin: object = field(repr=False, compare=False)

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        raise MonthlyDegreeDayImportError("monthly records require parser-origin construction")


@dataclass(frozen=True)
class PlzCentroid:
    """A caller-supplied centroid from an explicitly versioned PLZ dataset."""

    plz: str
    latitude: Decimal
    longitude: Decimal
    dataset_identity: str
    dataset_version: str

    def __post_init__(self) -> None:
        _validate_plz_centroid(self)


@dataclass(frozen=True)
class MonthlyStationAssignment:
    """Deterministic assignment fields ready for later immutable persistence."""

    plz: str
    month: str
    comparison_month: str
    station_id: str
    distance_km: Decimal
    centroid_dataset_identity: str
    centroid_dataset_version: str
    distance_exceeds_50_km: bool
    target_source_file: str
    comparison_source_file: str
    assignment_nature: str
    rechtsstand: str
    verification_status: str
    assignment_method: str
    assignment_method_version: str


@dataclass(frozen=True)
class AnnualClimateFactor:
    """One normalized annual climate factor with its publication evidence."""

    plz: str
    period_from: date
    period_to: date
    factor: Decimal
    source_file: str
    source_version: str
    published_on: date
    attribution: str


@dataclass(frozen=True)
class AnnualClimateFactorPublication:
    """Metadata for a verified DWD annual-factor publication."""

    file_name: str
    period_from: date
    period_to: date
    published_on: date


@dataclass(frozen=True)
class AnnualClimateFactorResolution:
    """Resolved factor, or an explicit instruction to keep the raw comparison."""

    climate_factor: Decimal | None
    use_raw_comparison: bool


LATEST_VERIFIED_ANNUAL_PUBLICATION: Final = AnnualClimateFactorPublication(
    file_name="KF_20250601_20260531",
    period_from=date(2025, 6, 1),
    period_to=date(2026, 5, 31),
    published_on=date(2026, 7, 15),
)


class AnnualClimateFactorGateway(Protocol):
    """Port for normalized annual PLZ climate factors."""

    def list_climate_factors(
        self, period_from: date, period_to: date
    ) -> tuple[AnnualClimateFactor, ...]:
        """Return factors for exactly one rolling annual period."""
        ...


_FIXTURE_PERIOD_FROM: Final = date(2025, 1, 1)
_FIXTURE_PERIOD_TO: Final = date(2025, 12, 31)
_FIXTURE_PUBLICATION_DATE: Final = date(2026, 2, 15)
_FIXTURE_FILE: Final = "KF_20250101_20251231.csv"
_FIXTURE_FACTORS: Final = (
    ("01067", Decimal("1.14")),
    ("01099", Decimal("1.02")),
    ("01328", Decimal("0.98")),
    ("01773", Decimal("0.83")),
    ("02625", Decimal("1.05")),
    ("03042", Decimal("1.12")),
    ("04103", Decimal("1.15")),
    ("04109", Decimal("1.14")),
    ("06108", Decimal("1.15")),
)


class StubAnnualClimateFactorGateway:
    """Nine-row fixture stub. TODO(provider): DWD CDC-backed gateway."""

    def list_climate_factors(
        self, period_from: date, period_to: date
    ) -> tuple[AnnualClimateFactor, ...]:
        if (period_from, period_to) != (_FIXTURE_PERIOD_FROM, _FIXTURE_PERIOD_TO):
            return ()
        return tuple(
            AnnualClimateFactor(
                plz=plz,
                period_from=_FIXTURE_PERIOD_FROM,
                period_to=_FIXTURE_PERIOD_TO,
                factor=factor,
                source_file=_FIXTURE_FILE,
                source_version=DWD_ANNUAL_SOURCE_VERSION,
                published_on=_FIXTURE_PUBLICATION_DATE,
                attribution=DWD_ATTRIBUTION,
            )
            for plz, factor in _FIXTURE_FACTORS
        )


def _parse_month(value: str) -> tuple[int, int]:
    if re.fullmatch(r"[0-9]{6}", value) is None:
        raise MonthlyDegreeDayImportError("invalid monthly yyyymm month")
    year = int(value[:4])
    month = int(value[4:])
    if year < 1 or not 1 <= month <= 12:
        raise MonthlyDegreeDayImportError("invalid monthly yyyymm month")
    return year, month


def _parse_exact_decimal(
    value: str,
    *,
    field: str,
    minimum: Decimal,
    maximum: Decimal | None = None,
) -> Decimal:
    raw = value.strip()
    if re.fullmatch(r"-?[0-9]+(?:\.[0-9]+)?", raw) is None:
        raise MonthlyDegreeDayImportError(f"invalid decimal {field}")
    try:
        parsed = Decimal(raw)
    except InvalidOperation as exc:
        raise MonthlyDegreeDayImportError(f"invalid decimal {field}") from exc
    if not parsed.is_finite() or parsed < minimum or (maximum is not None and parsed > maximum):
        raise MonthlyDegreeDayImportError(f"invalid nonnegative {field}")
    return parsed


def _parse_monthly_coordinate(value: str, *, latitude: bool) -> Decimal:
    field = "latitude" if latitude else "longitude"
    limit = Decimal("90") if latitude else Decimal("180")
    return _parse_exact_decimal(
        value,
        field=f"{field} coordinate",
        minimum=-limit,
        maximum=limit,
    )


def _parse_day_count(value: str, *, field: str, maximum: int) -> int:
    raw = value.strip()
    if re.fullmatch(r"[0-9]+", raw) is None:
        raise MonthlyDegreeDayImportError(f"invalid {field} day count")
    parsed = int(raw)
    if parsed > maximum:
        raise MonthlyDegreeDayImportError(f"invalid {field} day count")
    return parsed


def _validate_plz_centroid(centroid: PlzCentroid) -> None:
    if type(centroid.latitude) is not Decimal or not centroid.latitude.is_finite():
        raise MonthlyDegreeDayImportError("invalid centroid latitude coordinate")
    if type(centroid.longitude) is not Decimal or not centroid.longitude.is_finite():
        raise MonthlyDegreeDayImportError("invalid centroid longitude coordinate")
    if not Decimal("-90") <= centroid.latitude <= Decimal("90"):
        raise MonthlyDegreeDayImportError("invalid centroid latitude coordinate")
    if not Decimal("-180") <= centroid.longitude <= Decimal("180"):
        raise MonthlyDegreeDayImportError("invalid centroid longitude coordinate")
    if (
        type(centroid.dataset_identity) is not str
        or type(centroid.dataset_version) is not str
        or not centroid.dataset_identity.strip()
        or not centroid.dataset_version.strip()
    ):
        raise MonthlyDegreeDayImportError("centroid dataset identity and version are required")
    if type(centroid.plz) is not str:
        raise MonthlyDegreeDayImportError("invalid centroid PLZ")
    try:
        normalized_plz = _normalize_plz(centroid.plz)
    except DwdAnnualImportError as exc:
        raise MonthlyDegreeDayImportError("invalid centroid PLZ") from exc
    object.__setattr__(centroid, "plz", normalized_plz)
    object.__setattr__(centroid, "dataset_identity", centroid.dataset_identity.strip())
    object.__setattr__(centroid, "dataset_version", centroid.dataset_version.strip())


def _monthly_record_from_parser(
    *,
    station_id: str,
    latitude: Decimal,
    longitude: Decimal,
    station_name: str,
    month: str,
    valid_day_count: int,
    monthly_degree_days: Decimal,
    heating_day_count: int,
    ten_year_mean: Decimal,
    source_path: str,
    source_file: str,
    standard: str,
    heating_limit_celsius: int,
    reference_room_temperature_celsius: int,
    unit: str,
    attribution: str,
    nature: str,
    rechtsstand: str,
    verification_status: str,
) -> MonthlyDegreeDayRecord:
    record = object.__new__(MonthlyDegreeDayRecord)
    values: dict[str, object] = {
        "station_id": station_id,
        "latitude": latitude,
        "longitude": longitude,
        "station_name": station_name,
        "month": month,
        "valid_day_count": valid_day_count,
        "monthly_degree_days": monthly_degree_days,
        "heating_day_count": heating_day_count,
        "ten_year_mean": ten_year_mean,
        "source_path": source_path,
        "source_file": source_file,
        "standard": standard,
        "heating_limit_celsius": heating_limit_celsius,
        "reference_room_temperature_celsius": reference_room_temperature_celsius,
        "unit": unit,
        "attribution": attribution,
        "nature": nature,
        "rechtsstand": rechtsstand,
        "verification_status": verification_status,
        "_parser_origin": _MONTHLY_RECORD_PARSER_ORIGIN,
    }
    for name, value in values.items():
        object.__setattr__(record, name, value)
    return record


def parse_monthly_degree_day_rows(
    rows: tuple[tuple[str, ...], ...],
    *,
    target_month: str,
    source_file: str,
) -> tuple[MonthlyDegreeDayRecord, ...]:
    """Normalize already-tokenized, ordered nine-field hdd_3807 rows."""

    year, month_number = _parse_month(target_month)
    maximum_days = monthrange(year, month_number)[1]
    if not source_file.strip():
        raise MonthlyDegreeDayImportError("monthly source file is required")

    records: list[MonthlyDegreeDayRecord] = []
    station_ids: set[str] = set()
    for row in rows:
        try:
            row_length = len(row)
        except TypeError as exc:
            raise MonthlyDegreeDayImportError("monthly row must have nine fields") from exc
        if row_length != 9:
            raise MonthlyDegreeDayImportError("monthly row shape must have nine fields")
        if not all(isinstance(value, str) for value in row):
            raise MonthlyDegreeDayImportError("monthly row must contain nine text fields")

        station_id = row[0].strip()
        station_name = row[3].strip()
        row_month = row[4].strip()
        if not station_id or not station_name:
            raise MonthlyDegreeDayImportError("monthly station identity is required")
        _parse_month(row_month)
        if row_month != target_month:
            raise MonthlyDegreeDayImportError("monthly row month does not match target month")
        if station_id in station_ids:
            raise MonthlyDegreeDayImportError("duplicate monthly station row")

        valid_day_count = _parse_day_count(row[5], field="valid", maximum=maximum_days)
        heating_day_count = _parse_day_count(row[7], field="heating", maximum=maximum_days)
        if heating_day_count > valid_day_count:
            raise MonthlyDegreeDayImportError("heating day count exceeds valid day count")
        station_ids.add(station_id)
        records.append(
            _monthly_record_from_parser(
                station_id=station_id,
                latitude=_parse_monthly_coordinate(row[1], latitude=True),
                longitude=_parse_monthly_coordinate(row[2], latitude=False),
                station_name=station_name,
                month=row_month,
                valid_day_count=valid_day_count,
                monthly_degree_days=_parse_exact_decimal(
                    row[6],
                    field="monthly degree-day value",
                    minimum=Decimal("0"),
                ),
                heating_day_count=heating_day_count,
                ten_year_mean=_parse_exact_decimal(
                    row[8],
                    field="ten-year mean degree-day value",
                    minimum=Decimal("0"),
                ),
                source_path=DWD_MONTHLY_SOURCE_PATH,
                source_file=source_file.strip(),
                standard=_MONTHLY_STANDARD,
                heating_limit_celsius=15,
                reference_room_temperature_celsius=20,
                unit=_MONTHLY_UNIT,
                attribution=DWD_MONTHLY_ATTRIBUTION,
                nature=_MONTHLY_NATURE,
                rechtsstand=_MONTHLY_RECHTSSTAND,
                verification_status=_MONTHLY_VERIFICATION_STATUS,
            )
        )
    return tuple(records)


def _great_circle_distance_km(
    *,
    from_latitude: Decimal,
    from_longitude: Decimal,
    to_latitude: Decimal,
    to_longitude: Decimal,
) -> Decimal:
    from_latitude_radians = radians(float(from_latitude))
    to_latitude_radians = radians(float(to_latitude))
    latitude_delta = to_latitude_radians - from_latitude_radians
    longitude_delta = radians(float(to_longitude - from_longitude))
    haversine = sin(latitude_delta / 2) ** 2 + (
        cos(from_latitude_radians) * cos(to_latitude_radians) * sin(longitude_delta / 2) ** 2
    )
    central_angle = 2 * atan2(sqrt(haversine), sqrt(max(0.0, 1 - haversine)))
    return (_EARTH_MEAN_RADIUS_KM * Decimal(str(central_angle))).quantize(
        _DISTANCE_QUANTUM_KM,
        rounding=ROUND_HALF_UP,
    )


def _validated_month_records(
    records: tuple[MonthlyDegreeDayRecord, ...],
    *,
    expected_month: str,
) -> tuple[dict[str, MonthlyDegreeDayRecord], str]:
    year, month_number = _parse_month(expected_month)
    maximum_days = monthrange(year, month_number)[1]
    if not records:
        raise MonthlyDegreeDayImportError("monthly records require one source file")

    by_station: dict[str, MonthlyDegreeDayRecord] = {}
    source_files: set[str] = set()
    has_unsealed_record = False
    for record in records:
        if type(record) is not MonthlyDegreeDayRecord:
            raise MonthlyDegreeDayImportError("invalid monthly record type or parser origin")
        if getattr(record, "_parser_origin", None) is not _MONTHLY_RECORD_PARSER_ORIGIN:
            has_unsealed_record = True
        if (
            type(record.station_id) is not str
            or not record.station_id.strip()
            or record.station_id != record.station_id.strip()
            or type(record.station_name) is not str
            or not record.station_name.strip()
            or record.station_name != record.station_name.strip()
        ):
            raise MonthlyDegreeDayImportError("invalid monthly station identity")
        if record.station_id in by_station:
            raise MonthlyDegreeDayImportError("duplicate monthly station identity")
        if type(record.latitude) is not Decimal or not record.latitude.is_finite():
            raise MonthlyDegreeDayImportError("invalid monthly latitude coordinate")
        if type(record.longitude) is not Decimal or not record.longitude.is_finite():
            raise MonthlyDegreeDayImportError("invalid monthly longitude coordinate")
        if not Decimal("-90") <= record.latitude <= Decimal("90"):
            raise MonthlyDegreeDayImportError("invalid monthly latitude coordinate")
        if not Decimal("-180") <= record.longitude <= Decimal("180"):
            raise MonthlyDegreeDayImportError("invalid monthly longitude coordinate")
        if type(record.month) is not str:
            raise MonthlyDegreeDayImportError("invalid monthly record month")
        _parse_month(record.month)
        if record.month != expected_month:
            raise MonthlyDegreeDayImportError("monthly record month does not match assignment")
        if (
            type(record.valid_day_count) is not int
            or not 0 <= record.valid_day_count <= maximum_days
        ):
            raise MonthlyDegreeDayImportError("invalid valid day count")
        if (
            type(record.heating_day_count) is not int
            or not 0 <= record.heating_day_count <= record.valid_day_count
        ):
            raise MonthlyDegreeDayImportError("invalid heating day count")
        for value in (record.monthly_degree_days, record.ten_year_mean):
            if type(value) is not Decimal or not value.is_finite() or value < 0:
                raise MonthlyDegreeDayImportError("invalid monthly degree-day decimal")
        if (
            type(record.source_path) is not str
            or type(record.standard) is not str
            or type(record.heating_limit_celsius) is not int
            or type(record.reference_room_temperature_celsius) is not int
            or type(record.unit) is not str
            or type(record.attribution) is not str
            or type(record.nature) is not str
            or type(record.rechtsstand) is not str
            or type(record.verification_status) is not str
            or record.source_path != DWD_MONTHLY_SOURCE_PATH
            or record.standard != _MONTHLY_STANDARD
            or record.heating_limit_celsius != 15
            or record.reference_room_temperature_celsius != 20
            or record.unit != _MONTHLY_UNIT
            or record.attribution != DWD_MONTHLY_ATTRIBUTION
            or record.nature != _MONTHLY_NATURE
            or record.rechtsstand != _MONTHLY_RECHTSSTAND
            or record.verification_status != _MONTHLY_VERIFICATION_STATUS
        ):
            raise MonthlyDegreeDayImportError("invalid monthly record provenance metadata")
        if (
            type(record.source_file) is not str
            or not record.source_file.strip()
            or record.source_file != record.source_file.strip()
        ):
            raise MonthlyDegreeDayImportError("invalid monthly source file")
        source_files.add(record.source_file)
        by_station[record.station_id] = record

    if len(source_files) != 1:
        raise MonthlyDegreeDayImportError("monthly records must share one source file")
    if has_unsealed_record:
        raise MonthlyDegreeDayImportError("invalid monthly record parser origin")
    return by_station, next(iter(source_files))


def assign_monthly_station(
    *,
    centroid: PlzCentroid,
    target_month: str,
    comparison_month: str,
    target_records: tuple[MonthlyDegreeDayRecord, ...],
    comparison_records: tuple[MonthlyDegreeDayRecord, ...],
) -> MonthlyStationAssignment | None:
    """Choose the nearest station valid in both months, with a stable tie-break."""

    if type(centroid) is not PlzCentroid:
        raise MonthlyDegreeDayImportError("invalid PLZ centroid type")
    _validate_plz_centroid(centroid)
    target_by_station, target_source_file = _validated_month_records(
        target_records,
        expected_month=target_month,
    )
    comparison_by_station, comparison_source_file = _validated_month_records(
        comparison_records,
        expected_month=comparison_month,
    )
    shared_station_ids = target_by_station.keys() & comparison_by_station.keys()
    for station_id in shared_station_ids:
        target_record = target_by_station[station_id]
        comparison_record = comparison_by_station[station_id]
        if (
            target_record.latitude != comparison_record.latitude
            or target_record.longitude != comparison_record.longitude
        ):
            raise MonthlyDegreeDayImportError(
                "monthly station coordinate drift between compared months"
            )
    common_station_ids = {
        station_id
        for station_id in shared_station_ids
        if target_by_station[station_id].valid_day_count >= 25
        and comparison_by_station[station_id].valid_day_count >= 25
    }
    if not common_station_ids:
        return None

    candidates = [
        (
            _great_circle_distance_km(
                from_latitude=centroid.latitude,
                from_longitude=centroid.longitude,
                to_latitude=target_by_station[station_id].latitude,
                to_longitude=target_by_station[station_id].longitude,
            ),
            station_id,
        )
        for station_id in common_station_ids
    ]
    distance_km, station_id = min(candidates, key=lambda candidate: candidate)
    return MonthlyStationAssignment(
        plz=centroid.plz,
        month=target_month,
        comparison_month=comparison_month,
        station_id=station_id,
        distance_km=distance_km,
        centroid_dataset_identity=centroid.dataset_identity,
        centroid_dataset_version=centroid.dataset_version,
        distance_exceeds_50_km=distance_km > Decimal("50"),
        target_source_file=target_source_file,
        comparison_source_file=comparison_source_file,
        assignment_nature=_ASSIGNMENT_NATURE,
        rechtsstand=_MONTHLY_RECHTSSTAND,
        verification_status=_MONTHLY_VERIFICATION_STATUS,
        assignment_method=_ASSIGNMENT_METHOD,
        assignment_method_version=_ASSIGNMENT_METHOD_VERSION,
    )


def _parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError as exc:
        raise DwdAnnualImportError("invalid annual period date") from exc


def _parse_file_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y%m%d").date()
    except ValueError as exc:
        raise DwdAnnualImportError("invalid annual file-name period") from exc


def _period_after_12_months(period_from: date) -> date:
    try:
        return period_from.replace(year=period_from.year + 1)
    except ValueError:
        return period_from.replace(year=period_from.year + 1, day=28)


def _parse_file_period(
    file_name: str,
    *,
    xml: bool,
    published_on: date,
) -> tuple[date, date, bool]:
    match = (_XML_FILE_NAME if xml else _CSV_FILE_NAME).fullmatch(file_name)
    if match is None:
        raise DwdAnnualImportError("unsupported annual file name")
    period_from = _parse_file_date(match.group("period_from"))
    period_to = _parse_file_date(match.group("period_to"))
    if period_to + timedelta(days=1) != _period_after_12_months(period_from):
        raise DwdAnnualImportError("annual file period is not exactly 12 months inclusive")
    if published_on < period_to:
        raise DwdAnnualImportError("publication date precedes annual file period end")
    return period_from, period_to, not xml and match.group("comma") is not None


def _normalize_plz(value: str) -> str:
    raw = value.strip()
    if not raw.isascii() or not raw.isdigit() or not 1 <= len(raw) <= 5:
        raise DwdAnnualImportError("invalid PLZ")
    return raw.zfill(5)


def _parse_factor(value: str, *, comma_decimal: bool) -> Decimal:
    raw = value.strip()
    separator = "," if comma_decimal else "."
    if re.fullmatch(rf"[0-9]+{re.escape(separator)}[0-9]+", raw) is None:
        raise DwdAnnualImportError("invalid decimal factor")
    if comma_decimal:
        raw = raw.replace(",", ".")
    try:
        factor = Decimal(raw)
    except InvalidOperation as exc:
        raise DwdAnnualImportError("invalid decimal factor") from exc
    if not factor.is_finite() or not _MINIMUM_FACTOR <= factor <= _MAXIMUM_FACTOR:
        raise DwdAnnualImportError("annual factor outside accepted range")
    return factor


def _normalize_record(
    *,
    period_from_raw: str,
    period_to_raw: str,
    plz_raw: str,
    factor_raw: str,
    comma_decimal: bool,
    file_name: str,
    published_on: date,
    expected_period: tuple[date, date],
) -> AnnualClimateFactor:
    period_from = _parse_date(period_from_raw.strip())
    period_to = _parse_date(period_to_raw.strip())
    if (period_from, period_to) != expected_period:
        raise DwdAnnualImportError("row period does not match annual file-name period")
    return AnnualClimateFactor(
        plz=_normalize_plz(plz_raw),
        period_from=period_from,
        period_to=period_to,
        factor=_parse_factor(factor_raw, comma_decimal=comma_decimal),
        source_file=file_name,
        source_version=DWD_ANNUAL_SOURCE_VERSION,
        published_on=published_on,
        attribution=DWD_ATTRIBUTION,
    )


def _validate_records(
    records: list[AnnualClimateFactor],
) -> tuple[AnnualClimateFactor, ...]:
    if len(records) < _MINIMUM_RECORD_COUNT:
        raise DwdAnnualImportError("incomplete annual import: fewer than 7,000 records")
    identities: set[tuple[str, date, date]] = set()
    for record in records:
        identity = (record.plz, record.period_from, record.period_to)
        if identity in identities:
            raise DwdAnnualImportError("duplicate annual climate-factor identity")
        identities.add(identity)
    return tuple(records)


def parse_annual_climate_factor_csv(
    content: str,
    *,
    file_name: str,
    published_on: date,
) -> tuple[AnnualClimateFactor, ...]:
    """Parse one strict semicolon-separated annual DWD file."""

    period_from, period_to, comma_decimal = _parse_file_period(
        file_name,
        xml=False,
        published_on=published_on,
    )
    reader = csv.reader(StringIO(content), delimiter=";")
    try:
        header = tuple(next(reader))
    except StopIteration as exc:
        raise DwdAnnualImportError("missing annual CSV header") from exc
    if header != _CSV_HEADER:
        raise DwdAnnualImportError("invalid annual CSV header")

    records: list[AnnualClimateFactor] = []
    for row in reader:
        if len(row) != len(_CSV_HEADER):
            raise DwdAnnualImportError("invalid annual CSV row shape")
        records.append(
            _normalize_record(
                period_from_raw=row[0],
                period_to_raw=row[1],
                plz_raw=row[2],
                factor_raw=row[3],
                comma_decimal=comma_decimal,
                file_name=file_name,
                published_on=published_on,
                expected_period=(period_from, period_to),
            )
        )
    return _validate_records(records)


def _required_xml_text(row: ElementTree.Element, field: str) -> str:
    value = row.findtext(field)
    if value is None:
        raise DwdAnnualImportError(f"missing XML field {field}")
    return value


def parse_annual_climate_factor_xml(
    content: str,
    *,
    file_name: str,
    published_on: date,
) -> tuple[AnnualClimateFactor, ...]:
    """Parse the XML representation of an annual DWD publication."""

    period_from, period_to, _comma_decimal = _parse_file_period(
        file_name,
        xml=True,
        published_on=published_on,
    )
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        raise DwdAnnualImportError("invalid annual XML") from exc
    records = [
        _normalize_record(
            period_from_raw=_required_xml_text(row, "VON_DATUM"),
            period_to_raw=_required_xml_text(row, "BIS_DATUM"),
            plz_raw=_required_xml_text(row, "KLFK_POLZ"),
            factor_raw=_required_xml_text(row, "KLIMAFAKTOR"),
            comma_decimal=False,
            file_name=file_name,
            published_on=published_on,
            expected_period=(period_from, period_to),
        )
        for row in root.findall("ROW")
    ]
    return _validate_records(records)


def merge_annual_climate_factors(
    existing: tuple[AnnualClimateFactor, ...],
    incoming: tuple[AnnualClimateFactor, ...],
) -> tuple[AnnualClimateFactor, ...]:
    """Return an incoming-wins upsert without deleting older identities."""

    by_identity = {(row.plz, row.period_from, row.period_to): row for row in existing}
    by_identity.update({(row.plz, row.period_from, row.period_to): row for row in incoming})
    return tuple(by_identity[identity] for identity in sorted(by_identity))


def resolve_annual_climate_factor(
    records: tuple[AnnualClimateFactor, ...],
    *,
    plz: str,
    period_from: date,
    period_to: date,
) -> AnnualClimateFactorResolution:
    """Resolve one exact identity, preserving an explicit raw fallback state."""

    normalized_plz = _normalize_plz(plz)
    for record in records:
        if (
            record.plz == normalized_plz
            and record.period_from == period_from
            and record.period_to == period_to
        ):
            return AnnualClimateFactorResolution(
                climate_factor=record.factor,
                use_raw_comparison=False,
            )
    return AnnualClimateFactorResolution(
        climate_factor=None,
        use_raw_comparison=True,
    )
