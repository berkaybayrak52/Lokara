"""DWD adapter boundary for rolling annual PLZ climate factors.

The annual climate factor is distinct from the monthly ``hdd_3807`` dataset.
This module normalizes DWD CSV/XML records before they reach domain code.

TODO(provider): fetch the published files from the DWD Climate Data Center and
pass their contents through the normalization functions below.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from io import StringIO
from typing import Final, Protocol
from xml.etree import ElementTree

DWD_ANNUAL_SOURCE_VERSION: Final = "v22.3"
DWD_ATTRIBUTION: Final = "Quelle: Deutscher Wetterdienst"

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
