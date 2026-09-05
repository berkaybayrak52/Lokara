"""docs/16 § 9: annual DWD climate-factor boundary and import guards.

This test deliberately restates the approved oracle values instead of importing the
data-only oracle.  The annual PLZ climate factor is not the monthly ``hdd_3807``
dataset; monthly parsing and station assignment belong to the next U3 sub-slice.
"""

import socket
from dataclasses import FrozenInstanceError, fields, replace
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Final

import lokara_adapters.dwd as dwd_adapter
import pytest
from lokara_adapters.dwd import (
    DWD_ANNUAL_SOURCE_VERSION,
    DWD_ATTRIBUTION,
    LATEST_VERIFIED_ANNUAL_PUBLICATION,
    AnnualClimateFactor,
    AnnualClimateFactorGateway,
    AnnualClimateFactorResolution,
    DwdAnnualImportError,
    StubAnnualClimateFactorGateway,
    merge_annual_climate_factors,
    parse_annual_climate_factor_csv,
    parse_annual_climate_factor_xml,
    resolve_annual_climate_factor,
)
from lokara_domain import DegreeDayTable
from lokara_heating_engine import AnnualClimateFactor as HeatingAnnualClimateFactor
from lokara_heating_engine import (
    AnnualComparisonInput,
    calculate_annual_comparison,
)

CALENDAR_FROM: Final = date(2025, 1, 1)
CALENDAR_TO: Final = date(2025, 12, 31)
CALENDAR_FILE: Final = "KF_20250101_20251231.csv"
COMMA_CALENDAR_FILE: Final = "KF_20250101_20251231_k.csv"
XML_CALENDAR_FILE: Final = "KF_20250101_20251231.xml"
PUBLISHED_ON: Final = date(2026, 2, 15)
MINIMUM_ROWS: Final = 7_000
VERIFIED_2025_ROWS: Final = 8_234

VERIFIED_2025_FACTORS: Final[dict[str, str]] = {
    "01067": "1.14",
    "01099": "1.02",
    "01328": "0.98",
    "01773": "0.83",
    "02625": "1.05",
    "03042": "1.12",
    "04103": "1.15",
    "04109": "1.14",
    "06108": "1.15",
}

MONTHLY_API_NAMES: Final = (
    "DWD_MONTHLY_ATTRIBUTION",
    "DWD_MONTHLY_SOURCE_PATH",
    "MonthlyDegreeDayImportError",
    "MonthlyDegreeDayRecord",
    "MonthlyStationAssignment",
    "PlzCentroid",
    "assign_monthly_station",
    "parse_monthly_degree_day_rows",
)
MONTHLY_API_MISSING: Final = tuple(
    name for name in MONTHLY_API_NAMES if not hasattr(dwd_adapter, name)
)
MONTHLY_API_UNAVAILABLE: Final = pytest.mark.skipif(
    bool(MONTHLY_API_MISSING),
    reason="U3b monthly DWD API is not implemented",
)
MONTHLY_IMPORT_ERROR: Any = getattr(dwd_adapter, "MonthlyDegreeDayImportError", ValueError)
MONTHLY_RECORD_TYPE: Any = getattr(dwd_adapter, "MonthlyDegreeDayRecord", object)
MONTHLY_ASSIGNMENT_TYPE: Any = getattr(dwd_adapter, "MonthlyStationAssignment", object)
PLZ_CENTROID_TYPE: Any = getattr(dwd_adapter, "PlzCentroid", object)
PARSE_MONTHLY_ROWS: Any = getattr(dwd_adapter, "parse_monthly_degree_day_rows", None)
ASSIGN_MONTHLY_STATION: Any = getattr(dwd_adapter, "assign_monthly_station", None)
ASSIGN_MONTHLY_STATION_FOR_PLZ: Any = getattr(dwd_adapter, "assign_monthly_station_for_plz", None)
MONTHLY_SOURCE_PATH_API: Any = getattr(dwd_adapter, "DWD_MONTHLY_SOURCE_PATH", None)
MONTHLY_ATTRIBUTION_API: Any = getattr(dwd_adapter, "DWD_MONTHLY_ATTRIBUTION", None)

MONTHLY_SOURCE_PATH: Final = (
    "opendata.dwd.de/climate_environment/CDC/derived_germany/techn/monthly/"
    "heating_degreedays/hdd_3807/"
)
TARGET_MONTH: Final = "202501"
COMPARISON_MONTH: Final = "202401"
MONTHLY_SOURCE_FILE: Final = "monthly-source-202501"
EARTH_MEAN_RADIUS_KM: Final = Decimal("6371.0088")
DISTANCE_QUANTUM_KM: Final = Decimal("0.000001")
DISTANCE_ROUNDING: Final = ROUND_HALF_UP


def _monthly_row(
    *,
    station_id: str = "001",
    latitude: str = "51.0500",
    longitude: str = "13.7400",
    station_name: str = "Dresden",
    month: str = TARGET_MONTH,
    valid_day_count: str = "31",
    monthly_degree_days: str = "590.25",
    heating_day_count: str = "27",
    ten_year_mean: str = "610.125",
) -> tuple[str, ...]:
    return (
        station_id,
        latitude,
        longitude,
        station_name,
        month,
        valid_day_count,
        monthly_degree_days,
        heating_day_count,
        ten_year_mean,
    )


def _parse_monthly(
    rows: tuple[tuple[str, ...], ...],
    *,
    target_month: str = TARGET_MONTH,
    source_file: str = MONTHLY_SOURCE_FILE,
) -> tuple[Any, ...]:
    return PARSE_MONTHLY_ROWS(  # type: ignore[no-any-return]
        rows,
        target_month=target_month,
        source_file=source_file,
    )


def _forge_monthly_record(record: Any, **changes: object) -> Any:
    """Bypass construction only to prove assignment revalidates hostile objects."""

    forged = object.__new__(type(record))
    for field in fields(record):
        if field.name.startswith("_"):
            continue
        object.__setattr__(
            forged,
            field.name,
            changes.get(field.name, getattr(record, field.name)),
        )
    return forged


def _source_plz(plz: str) -> str:
    """The DWD source omits leading zeroes; normalization must restore them."""
    return str(int(plz))


def _source_rows(count: int, *, comma_decimal: bool = False) -> list[tuple[str, str]]:
    fixed = [(_source_plz(plz), factor) for plz, factor in VERIFIED_2025_FACTORS.items()]
    used = {plz for plz, _factor in fixed}
    generated: list[tuple[str, str]] = []
    candidate = 10_000
    while len(fixed) + len(generated) < count:
        raw_plz = str(candidate)
        candidate += 1
        if raw_plz in used:
            continue
        used.add(raw_plz)
        generated.append((raw_plz, "1.00"))
    rows = fixed + generated
    if comma_decimal:
        return [(plz, factor.replace(".", ",")) for plz, factor in rows]
    return rows


def _csv(
    count: int = MINIMUM_ROWS,
    *,
    header: str = "DatAnf;DatEnd;PLZ;KF",
    comma_decimal: bool = False,
    rows: list[tuple[str, str]] | None = None,
    period_from: str = "01.01.2025",
    period_to: str = "31.12.2025",
) -> str:
    body = rows if rows is not None else _source_rows(count, comma_decimal=comma_decimal)
    lines = [header]
    lines.extend(f"{period_from};{period_to};{plz};{factor}" for plz, factor in body)
    return "\n".join(lines)


def _xml(
    count: int = MINIMUM_ROWS,
    *,
    period_from: str = "01.01.2025",
    period_to: str = "31.12.2025",
) -> str:
    rows = "".join(
        "<ROW>"
        f"<VON_DATUM>{period_from}</VON_DATUM>"
        f"<BIS_DATUM>{period_to}</BIS_DATUM>"
        f"<KLFK_POLZ>{plz}</KLFK_POLZ>"
        f"<KLIMAFAKTOR>{factor}</KLIMAFAKTOR>"
        "</ROW>"
        for plz, factor in _source_rows(count)
    )
    return f"<CLIMATE_CORRECTION_FACTORS>{rows}</CLIMATE_CORRECTION_FACTORS>"


def _parse_csv(
    content: str,
    *,
    file_name: str = CALENDAR_FILE,
    published_on: date = PUBLISHED_ON,
) -> tuple[AnnualClimateFactor, ...]:
    return parse_annual_climate_factor_csv(
        content,
        file_name=file_name,
        published_on=published_on,
    )


class TestNormalizedAnnualBoundary:
    def test_record_is_frozen_and_keeps_exact_source_metadata(self) -> None:
        record = _parse_csv(_csv())[0]

        assert isinstance(record, AnnualClimateFactor)
        assert record.period_from == CALENDAR_FROM
        assert record.period_to == CALENDAR_TO
        assert record.source_file == CALENDAR_FILE
        assert record.source_version == "v22.3"
        assert record.published_on == PUBLISHED_ON
        assert record.attribution == "Quelle: Deutscher Wetterdienst"
        with pytest.raises(FrozenInstanceError):
            record.factor = Decimal("1.15")  # type: ignore[misc]

    def test_stub_returns_normalized_records_through_the_port(self) -> None:
        gateway: AnnualClimateFactorGateway = StubAnnualClimateFactorGateway()

        returned = gateway.list_climate_factors(CALENDAR_FROM, CALENDAR_TO)

        assert {row.plz: row.factor for row in returned} == {
            plz: Decimal(factor) for plz, factor in VERIFIED_2025_FACTORS.items()
        }
        assert all(isinstance(row, AnnualClimateFactor) for row in returned)
        assert gateway.list_climate_factors(date(2024, 1, 1), date(2024, 12, 31)) == ()

    def test_latest_verified_file_metadata_is_not_the_stale_april_headline(self) -> None:
        assert DWD_ANNUAL_SOURCE_VERSION == "v22.3"
        assert DWD_ATTRIBUTION == "Quelle: Deutscher Wetterdienst"
        assert LATEST_VERIFIED_ANNUAL_PUBLICATION.file_name == "KF_20250601_20260531"
        assert LATEST_VERIFIED_ANNUAL_PUBLICATION.period_from == date(2025, 6, 1)
        assert LATEST_VERIFIED_ANNUAL_PUBLICATION.period_to == date(2026, 5, 31)
        assert LATEST_VERIFIED_ANNUAL_PUBLICATION.published_on == date(2026, 7, 15)


class TestAnnualDwdFormats:
    def test_point_decimal_csv_restores_leading_zeroes_and_all_nine_values(self) -> None:
        records = _parse_csv(_csv(VERIFIED_2025_ROWS))
        by_plz = {row.plz: row.factor for row in records}

        assert len(records) == VERIFIED_2025_ROWS
        assert {plz: by_plz[plz] for plz in VERIFIED_2025_FACTORS} == {
            plz: Decimal(factor) for plz, factor in VERIFIED_2025_FACTORS.items()
        }
        assert all(len(row.plz) == 5 for row in records)
        assert all(isinstance(row.factor, Decimal) for row in records)

    def test_comma_decimal_k_csv_is_equivalent(self) -> None:
        records = _parse_csv(
            _csv(comma_decimal=True),
            file_name=COMMA_CALENDAR_FILE,
        )
        by_plz = {row.plz: row.factor for row in records}

        assert by_plz["01067"] == Decimal("1.14")
        assert by_plz["01773"] == Decimal("0.83")

    def test_xml_fields_are_equivalent_to_csv_fields(self) -> None:
        csv_records = _parse_csv(_csv())
        xml_records = parse_annual_climate_factor_xml(
            _xml(),
            file_name=XML_CALENDAR_FILE,
            published_on=PUBLISHED_ON,
        )

        assert [(row.plz, row.period_from, row.period_to, row.factor) for row in xml_records] == [
            (row.plz, row.period_from, row.period_to, row.factor) for row in csv_records
        ]


class TestAnnualFileAndPeriodProvenance:
    @pytest.mark.parametrize(
        "file_name",
        [
            "DWD_20250101_20251231.csv",
            "KF_20250101.csv",
            "KF_202501_20251231.csv",
            "KF_20251301_20251231.csv",
            "KF_20250101_20251231.txt",
            XML_CALENDAR_FILE,
        ],
    )
    def test_csv_rejects_unsupported_or_malformed_file_names(self, file_name: str) -> None:
        with pytest.raises(DwdAnnualImportError, match=r"file|name|period"):
            _parse_csv(_csv(), file_name=file_name)

    @pytest.mark.parametrize(
        "file_name",
        [
            "DWD_20250101_20251231.xml",
            "KF_20250101.xml",
            "KF_202501_20251231.xml",
            "KF_20251301_20251231.xml",
            "KF_20250101_20251231.txt",
            CALENDAR_FILE,
            "KF_20250101_20251231_k.xml",
        ],
    )
    def test_xml_rejects_unsupported_or_malformed_file_names(self, file_name: str) -> None:
        with pytest.raises(DwdAnnualImportError, match=r"file|name|period"):
            parse_annual_climate_factor_xml(
                _xml(),
                file_name=file_name,
                published_on=PUBLISHED_ON,
            )

    @pytest.mark.parametrize("file_name", [CALENDAR_FILE, COMMA_CALENDAR_FILE])
    def test_supported_csv_names_bind_the_encoded_period(self, file_name: str) -> None:
        comma_decimal = file_name == COMMA_CALENDAR_FILE

        records = _parse_csv(
            _csv(comma_decimal=comma_decimal),
            file_name=file_name,
        )

        assert {(row.period_from, row.period_to) for row in records} == {
            (CALENDAR_FROM, CALENDAR_TO)
        }

    def test_supported_xml_name_binds_the_encoded_period(self) -> None:
        records = parse_annual_climate_factor_xml(
            _xml(),
            file_name=XML_CALENDAR_FILE,
            published_on=PUBLISHED_ON,
        )

        assert {(row.period_from, row.period_to) for row in records} == {
            (CALENDAR_FROM, CALENDAR_TO)
        }

    def test_csv_rejects_filename_dates_that_disagree_with_row_dates(self) -> None:
        with pytest.raises(DwdAnnualImportError, match="period"):
            _parse_csv(_csv(), file_name="KF_20240101_20241231.csv")

    def test_xml_rejects_filename_dates_that_disagree_with_row_dates(self) -> None:
        with pytest.raises(DwdAnnualImportError, match="period"):
            parse_annual_climate_factor_xml(
                _xml(),
                file_name="KF_20240101_20241231.xml",
                published_on=PUBLISHED_ON,
            )

    def test_csv_rejects_mixed_periods_inside_one_file(self) -> None:
        mixed = _csv().replace(
            "01.01.2025;31.12.2025;",
            "01.02.2025;31.01.2026;",
            1,
        )
        with pytest.raises(DwdAnnualImportError, match="period"):
            _parse_csv(mixed)

    def test_xml_rejects_mixed_periods_inside_one_file(self) -> None:
        mixed = _xml().replace(
            "<VON_DATUM>01.01.2025</VON_DATUM><BIS_DATUM>31.12.2025</BIS_DATUM>",
            "<VON_DATUM>01.02.2025</VON_DATUM><BIS_DATUM>31.01.2026</BIS_DATUM>",
            1,
        )
        with pytest.raises(DwdAnnualImportError, match="period"):
            parse_annual_climate_factor_xml(
                mixed,
                file_name=XML_CALENDAR_FILE,
                published_on=PUBLISHED_ON,
            )

    @pytest.mark.parametrize(
        ("period_from", "period_to", "file_name"),
        [
            ("01.01.2025", "30.12.2025", "KF_20250101_20251230.csv"),
            ("01.02.2025", "01.02.2026", "KF_20250201_20260201.csv"),
        ],
    )
    def test_csv_rejects_period_that_is_not_exactly_12_months_inclusive(
        self,
        period_from: str,
        period_to: str,
        file_name: str,
    ) -> None:
        with pytest.raises(DwdAnnualImportError, match=r"12.month|period"):
            _parse_csv(
                _csv(period_from=period_from, period_to=period_to),
                file_name=file_name,
            )

    @pytest.mark.parametrize(
        ("period_from", "period_to", "file_name"),
        [
            ("01.01.2025", "30.12.2025", "KF_20250101_20251230.xml"),
            ("01.02.2025", "01.02.2026", "KF_20250201_20260201.xml"),
        ],
    )
    def test_xml_rejects_period_that_is_not_exactly_12_months_inclusive(
        self,
        period_from: str,
        period_to: str,
        file_name: str,
    ) -> None:
        with pytest.raises(DwdAnnualImportError, match=r"12.month|period"):
            parse_annual_climate_factor_xml(
                _xml(period_from=period_from, period_to=period_to),
                file_name=file_name,
                published_on=PUBLISHED_ON,
            )

    @pytest.mark.parametrize("file_name", [CALENDAR_FILE, COMMA_CALENDAR_FILE])
    def test_csv_rejects_publication_before_period_end(self, file_name: str) -> None:
        with pytest.raises(DwdAnnualImportError, match=r"publication|published|period"):
            _parse_csv(
                _csv(comma_decimal=file_name == COMMA_CALENDAR_FILE),
                file_name=file_name,
                published_on=date(2025, 12, 30),
            )

    def test_xml_rejects_publication_before_period_end(self) -> None:
        with pytest.raises(DwdAnnualImportError, match=r"publication|published|period"):
            parse_annual_climate_factor_xml(
                _xml(),
                file_name=XML_CALENDAR_FILE,
                published_on=date(2025, 12, 30),
            )


class TestAnnualDwdImportGuards:
    @pytest.mark.parametrize(
        "header",
        [
            "DatAnf;DatEnd;KF;PLZ",
            "DatAnf;DatEnd;PLZ",
            "DatAnf;DatEnd;PLZ;KF;Extra",
        ],
    )
    def test_header_must_be_exact(self, header: str) -> None:
        with pytest.raises(DwdAnnualImportError, match="header"):
            _parse_csv(_csv(header=header))

    def test_fewer_than_7000_rows_is_rejected_and_threshold_is_not_a_caller_option(self) -> None:
        with pytest.raises(DwdAnnualImportError, match=r"7.?000|complete"):
            _parse_csv(_csv(MINIMUM_ROWS - 1))
        with pytest.raises(TypeError):
            parse_annual_climate_factor_csv(
                _csv(MINIMUM_ROWS - 1),
                file_name=CALENDAR_FILE,
                published_on=PUBLISHED_ON,
                minimum_record_count=MINIMUM_ROWS - 1,  # type: ignore[call-arg]
            )

    def test_duplicate_identity_is_rejected(self) -> None:
        rows = _source_rows(MINIMUM_ROWS)
        rows[-1] = rows[0]
        with pytest.raises(DwdAnnualImportError, match="duplicate"):
            _parse_csv(_csv(rows=rows))

    @pytest.mark.parametrize("factor", ["0.39", "1.81", "not-a-decimal"])
    def test_out_of_range_or_non_decimal_factor_is_rejected(self, factor: str) -> None:
        rows = _source_rows(MINIMUM_ROWS)
        rows[0] = (rows[0][0], factor)
        with pytest.raises(DwdAnnualImportError, match=r"factor|decimal|range"):
            _parse_csv(_csv(rows=rows))

    @pytest.mark.parametrize("factor", ["0.40", "1.80"])
    def test_range_boundaries_are_inclusive_and_exact(self, factor: str) -> None:
        rows = _source_rows(MINIMUM_ROWS)
        rows[0] = (rows[0][0], factor)

        parsed = _parse_csv(_csv(rows=rows))

        assert parsed[0].factor == Decimal(factor)


class TestAnnualMergeAndResolution:
    def test_retry_is_idempotent_and_an_update_never_deletes_an_older_period(self) -> None:
        existing = (
            AnnualClimateFactor(
                plz="01067",
                period_from=date(2024, 1, 1),
                period_to=date(2024, 12, 31),
                factor=Decimal("1.08"),
                source_file="KF_20240101_20241231.csv",
                source_version=DWD_ANNUAL_SOURCE_VERSION,
                published_on=date(2025, 2, 15),
                attribution=DWD_ATTRIBUTION,
            ),
        )
        incoming = _parse_csv(_csv())

        first_merge = merge_annual_climate_factors(existing, incoming)
        retry = merge_annual_climate_factors(first_merge, incoming)

        assert retry == first_merge
        assert existing[0] in first_merge
        assert len(first_merge) == len(incoming) + 1

    def test_same_identity_is_updated_by_incoming_record(self) -> None:
        incoming = _parse_csv(_csv())
        original = incoming[0]
        changed = AnnualClimateFactor(
            plz=original.plz,
            period_from=original.period_from,
            period_to=original.period_to,
            factor=Decimal("1.16"),
            source_file="corrected.csv",
            source_version=original.source_version,
            published_on=date(2026, 2, 16),
            attribution=original.attribution,
        )

        merged = merge_annual_climate_factors(incoming, (changed,))
        by_identity = {(row.plz, row.period_from, row.period_to): row for row in merged}

        assert len(merged) == len(incoming)
        assert by_identity[("01067", CALENDAR_FROM, CALENDAR_TO)] == changed

    def test_missing_plz_returns_explicit_raw_state_without_factor_or_wording(self) -> None:
        resolution = resolve_annual_climate_factor(
            _parse_csv(_csv()),
            plz="99999",
            period_from=CALENDAR_FROM,
            period_to=CALENDAR_TO,
        )

        assert resolution == AnnualClimateFactorResolution(
            climate_factor=None,
            use_raw_comparison=True,
        )
        assert {field.name for field in fields(resolution)} == {
            "climate_factor",
            "use_raw_comparison",
        }

    def test_found_plz_returns_factor_and_disables_raw_state(self) -> None:
        resolution = resolve_annual_climate_factor(
            _parse_csv(_csv()),
            plz="01067",
            period_from=CALENDAR_FROM,
            period_to=CALENDAR_TO,
        )

        assert resolution == AnnualClimateFactorResolution(
            climate_factor=Decimal("1.14"),
            use_raw_comparison=False,
        )

    def test_heating_engine_owns_factor_direction_using_the_normalized_adapter_value(self) -> None:
        record = _parse_csv(_csv())[0]
        current_factor = HeatingAnnualClimateFactor(
            value=record.factor,
            period_label="01.01.2025–31.12.2025",
            source_label=record.attribution,
        )
        previous_factor = HeatingAnnualClimateFactor(
            value=Decimal("1.00"),
            period_label="01.01.2024–31.12.2024",
            source_label=record.attribution,
        )

        result = calculate_annual_comparison(
            AnnualComparisonInput(
                current_heat=Decimal("1000"),
                previous_heat=Decimal("1000"),
                current_warm_water=None,
                previous_warm_water=None,
                current_factor=current_factor,
                previous_factor=previous_factor,
            )
        )

        assert result.current_heat_adjusted == Decimal("1140.00")
        assert result.current_heat_adjusted > result.current_heat_raw

    def test_adapter_does_not_duplicate_the_heating_engine_calculation(self) -> None:
        assert not hasattr(dwd_adapter, "adjust_annual_heat")


def test_u3b_monthly_api_exists() -> None:
    assert MONTHLY_API_MISSING == (), f"missing U3b monthly DWD API: {MONTHLY_API_MISSING}"


@MONTHLY_API_UNAVAILABLE
class TestU3bMonthlyNormalizedBoundary:
    def test_nine_source_columns_become_one_frozen_record_with_exact_metadata(self) -> None:
        record = _parse_monthly((_monthly_row(),))[0]

        assert isinstance(record, MONTHLY_RECORD_TYPE)
        assert (
            record.station_id,
            record.latitude,
            record.longitude,
            record.station_name,
            record.month,
            record.valid_day_count,
            record.monthly_degree_days,
            record.heating_day_count,
            record.ten_year_mean,
        ) == (
            "001",
            Decimal("51.0500"),
            Decimal("13.7400"),
            "Dresden",
            TARGET_MONTH,
            31,
            Decimal("590.25"),
            27,
            Decimal("610.125"),
        )
        assert record.source_path == MONTHLY_SOURCE_PATH
        assert record.source_file == MONTHLY_SOURCE_FILE
        assert record.standard == "VDI 3807"
        assert record.heating_limit_celsius == 15
        assert record.reference_room_temperature_celsius == 20
        assert record.unit == "Kd"
        assert record.attribution == "Quelle: Deutscher Wetterdienst"
        assert record.nature == "external_source_DWD_GeoNutzV"
        assert record.rechtsstand == "08/2026"
        assert record.verification_status == "verify-before-production"
        assert MONTHLY_SOURCE_PATH_API == MONTHLY_SOURCE_PATH
        assert MONTHLY_ATTRIBUTION_API == "Quelle: Deutscher Wetterdienst"
        with pytest.raises(FrozenInstanceError):
            record.monthly_degree_days = Decimal("591")

    def test_parser_accepts_incomplete_month_but_preserves_valid_day_count(self) -> None:
        record = _parse_monthly((_monthly_row(valid_day_count="24", heating_day_count="24"),))[0]

        assert record.valid_day_count == 24

    @pytest.mark.parametrize(
        "row",
        [
            _monthly_row()[:-1],
            (*_monthly_row(), "unexpected"),
        ],
    )
    def test_parser_rejects_any_shape_other_than_the_documented_nine_columns(
        self, row: tuple[str, ...]
    ) -> None:
        with pytest.raises(MONTHLY_IMPORT_ERROR, match=r"nine|9|shape"):
            _parse_monthly((row,))

    def test_parser_rejects_mixed_months_in_one_file(self) -> None:
        with pytest.raises(MONTHLY_IMPORT_ERROR, match="month"):
            _parse_monthly(
                (
                    _monthly_row(station_id="001"),
                    _monthly_row(station_id="002", month=COMPARISON_MONTH),
                )
            )

    @pytest.mark.parametrize("month", ["20251", "202500", "202513", "2025-01"])
    def test_parser_rejects_invalid_or_non_target_yyyymm(self, month: str) -> None:
        with pytest.raises(MONTHLY_IMPORT_ERROR, match="month"):
            _parse_monthly((_monthly_row(month=month),))

    def test_parser_rejects_duplicate_station_rows_for_the_target_month(self) -> None:
        with pytest.raises(MONTHLY_IMPORT_ERROR, match="duplicate"):
            _parse_monthly((_monthly_row(), _monthly_row()))

    @pytest.mark.parametrize(
        ("latitude", "longitude"),
        [
            ("90.0001", "0"),
            ("-90.0001", "0"),
            ("0", "180.0001"),
            ("0", "-180.0001"),
            ("NaN", "0"),
            ("0", "Infinity"),
        ],
    )
    def test_parser_rejects_invalid_coordinate_bounds(self, latitude: str, longitude: str) -> None:
        with pytest.raises(MONTHLY_IMPORT_ERROR, match=r"coordinate|latitude|longitude"):
            _parse_monthly((_monthly_row(latitude=latitude, longitude=longitude),))

    @pytest.mark.parametrize(
        ("latitude", "longitude"),
        [("90", "180"), ("-90", "-180")],
    )
    def test_coordinate_bounds_are_inclusive_and_exact_decimals(
        self, latitude: str, longitude: str
    ) -> None:
        record = _parse_monthly((_monthly_row(latitude=latitude, longitude=longitude),))[0]

        assert record.latitude == Decimal(latitude)
        assert record.longitude == Decimal(longitude)

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("monthly_degree_days", "-0.01"),
            ("monthly_degree_days", "NaN"),
            ("monthly_degree_days", "590,25"),
            ("ten_year_mean", "-0.01"),
            ("ten_year_mean", "Infinity"),
            ("ten_year_mean", "610,125"),
        ],
    )
    def test_degree_day_values_must_be_nonnegative_finite_exact_decimals(
        self, field_name: str, value: str
    ) -> None:
        row = _monthly_row(**{field_name: value})
        with pytest.raises(MONTHLY_IMPORT_ERROR, match=r"degree|decimal|nonnegative"):
            _parse_monthly((row,))

    @pytest.mark.parametrize(
        ("target_month", "valid_day_count", "heating_day_count"),
        [
            ("202501", "-1", "0"),
            ("202501", "32", "0"),
            ("202502", "29", "0"),
            ("202402", "30", "0"),
            ("202501", "31.0", "0"),
            ("202501", "31", "32"),
            ("202501", "20", "21"),
            ("202501", "31", "-1"),
        ],
    )
    def test_day_counts_obey_calendar_month_and_valid_day_semantics(
        self,
        target_month: str,
        valid_day_count: str,
        heating_day_count: str,
    ) -> None:
        with pytest.raises(MONTHLY_IMPORT_ERROR, match=r"day|count"):
            _parse_monthly(
                (
                    _monthly_row(
                        month=target_month,
                        valid_day_count=valid_day_count,
                        heating_day_count=heating_day_count,
                    ),
                ),
                target_month=target_month,
            )

    def test_leap_year_day_count_is_accepted(self) -> None:
        record = _parse_monthly(
            (
                _monthly_row(
                    month="202402",
                    valid_day_count="29",
                    heating_day_count="29",
                ),
            ),
            target_month="202402",
        )[0]

        assert record.valid_day_count == 29

    def test_parser_boundary_does_not_claim_an_unsourced_header_or_delimiter(self) -> None:
        parameters = fields(MONTHLY_RECORD_TYPE)

        assert tuple(field.name for field in parameters[:9]) == (
            "station_id",
            "latitude",
            "longitude",
            "station_name",
            "month",
            "valid_day_count",
            "monthly_degree_days",
            "heating_day_count",
            "ten_year_mean",
        )

    def test_annual_factor_and_vdi_2067_apportionment_table_are_not_monthly_rows(
        self,
    ) -> None:
        annual = AnnualClimateFactor(
            plz="01067",
            period_from=CALENDAR_FROM,
            period_to=CALENDAR_TO,
            factor=Decimal("1.14"),
            source_file=CALENDAR_FILE,
            source_version=DWD_ANNUAL_SOURCE_VERSION,
            published_on=PUBLISHED_ON,
            attribution=DWD_ATTRIBUTION,
        )
        apportionment = DegreeDayTable(
            tenth_promille_by_month=(
                1700,
                1500,
                1300,
                800,
                400,
                133,
                133,
                134,
                300,
                800,
                1200,
                1600,
            )
        )

        with pytest.raises(MONTHLY_IMPORT_ERROR, match=r"row|nine|9|shape"):
            PARSE_MONTHLY_ROWS(
                (annual,),
                target_month=TARGET_MONTH,
                source_file=MONTHLY_SOURCE_FILE,
            )
        with pytest.raises(MONTHLY_IMPORT_ERROR, match=r"row|nine|9|shape"):
            PARSE_MONTHLY_ROWS(
                (apportionment,),
                target_month=TARGET_MONTH,
                source_file=MONTHLY_SOURCE_FILE,
            )


@MONTHLY_API_UNAVAILABLE
class TestU3bMonthlyStationAssignment:
    def _centroid(
        self,
        *,
        latitude: str = "51.0500",
        longitude: str = "13.7400",
    ) -> Any:
        return PLZ_CENTROID_TYPE(
            plz="01067",
            latitude=Decimal(latitude),
            longitude=Decimal(longitude),
            dataset_identity="plz-centroids-example",
            dataset_version="2026-08-test",
        )

    def _records(
        self,
        month: str,
        *rows: tuple[str, ...],
    ) -> tuple[Any, ...]:
        return _parse_monthly(tuple(rows), target_month=month, source_file=f"source-{month}")

    def test_same_valid_station_is_selected_for_both_months_and_returns_persistence_fields(
        self,
    ) -> None:
        target = self._records(TARGET_MONTH, _monthly_row(month=TARGET_MONTH))
        comparison = self._records(
            COMPARISON_MONTH,
            _monthly_row(month=COMPARISON_MONTH, monthly_degree_days="620"),
        )

        result = ASSIGN_MONTHLY_STATION(
            centroid=self._centroid(),
            target_month=TARGET_MONTH,
            comparison_month=COMPARISON_MONTH,
            target_records=target,
            comparison_records=comparison,
        )

        assert isinstance(result, MONTHLY_ASSIGNMENT_TYPE)
        assert result.plz == "01067"
        assert result.month == TARGET_MONTH
        assert result.comparison_month == COMPARISON_MONTH
        assert result.station_id == "001"
        assert result.distance_km == pytest.approx(0.0)
        assert result.centroid_dataset_identity == "plz-centroids-example"
        assert result.centroid_dataset_version == "2026-08-test"
        assert result.distance_exceeds_50_km is False
        assert not hasattr(result, "label_de")
        with pytest.raises(FrozenInstanceError):
            result.station_id = "002"

    def test_plz_entrypoint_uses_the_vendored_lookup_offline_and_preserves_explicit_compatibility(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        assert callable(ASSIGN_MONTHLY_STATION_FOR_PLZ), (
            "U3 assign_monthly_station_for_plz entrypoint is missing"
        )
        target = self._records(
            TARGET_MONTH,
            _monthly_row(latitude="51.05754959999999", longitude="13.7170648"),
        )
        comparison = self._records(
            COMPARISON_MONTH,
            _monthly_row(
                month=COMPARISON_MONTH,
                latitude="51.05754959999999",
                longitude="13.7170648",
            ),
        )
        explicit_centroid = PLZ_CENTROID_TYPE(
            plz="01067",
            latitude=Decimal("51.05754959999999"),
            longitude=Decimal("13.7170648"),
            dataset_identity="WZBSocialScienceCenter/plz_geocoord",
            dataset_version="2019-01",
        )
        explicit = ASSIGN_MONTHLY_STATION(
            centroid=explicit_centroid,
            target_month=TARGET_MONTH,
            comparison_month=COMPARISON_MONTH,
            target_records=target,
            comparison_records=comparison,
        )

        def refuse_network(*_args: object, **_kwargs: object) -> None:
            raise AssertionError("PLZ assignment must not open a network connection")

        monkeypatch.setattr(socket, "create_connection", refuse_network)
        resolved = ASSIGN_MONTHLY_STATION_FOR_PLZ(
            plz="01067",
            target_month=TARGET_MONTH,
            comparison_month=COMPARISON_MONTH,
            target_records=target,
            comparison_records=comparison,
        )

        assert resolved == explicit
        assert resolved.centroid_dataset_identity == "WZBSocialScienceCenter/plz_geocoord"
        assert resolved.centroid_dataset_version == "2019-01"

    def test_nearest_station_invalid_in_comparison_month_walks_to_next_common_station(
        self,
    ) -> None:
        target = self._records(
            TARGET_MONTH,
            _monthly_row(station_id="near", longitude="13.7410"),
            _monthly_row(station_id="farther", longitude="13.8000"),
        )
        comparison = self._records(
            COMPARISON_MONTH,
            _monthly_row(
                station_id="near",
                longitude="13.7410",
                month=COMPARISON_MONTH,
                valid_day_count="24",
                heating_day_count="24",
            ),
            _monthly_row(
                station_id="farther",
                longitude="13.8000",
                month=COMPARISON_MONTH,
            ),
        )

        result = ASSIGN_MONTHLY_STATION(
            centroid=self._centroid(),
            target_month=TARGET_MONTH,
            comparison_month=COMPARISON_MONTH,
            target_records=target,
            comparison_records=comparison,
        )

        assert result is not None
        assert result.station_id == "farther"

    @pytest.mark.parametrize(("target_days", "comparison_days"), [("24", "31"), ("31", "24")])
    def test_station_requires_at_least_25_valid_days_in_both_months(
        self, target_days: str, comparison_days: str
    ) -> None:
        target = self._records(
            TARGET_MONTH,
            _monthly_row(valid_day_count=target_days, heating_day_count=target_days),
        )
        comparison = self._records(
            COMPARISON_MONTH,
            _monthly_row(
                month=COMPARISON_MONTH,
                valid_day_count=comparison_days,
                heating_day_count=comparison_days,
            ),
        )

        result = ASSIGN_MONTHLY_STATION(
            centroid=self._centroid(),
            target_month=TARGET_MONTH,
            comparison_month=COMPARISON_MONTH,
            target_records=target,
            comparison_records=comparison,
        )

        assert result is None

    def test_no_common_valid_station_returns_no_assignment(self) -> None:
        target = self._records(
            TARGET_MONTH,
            _monthly_row(station_id="target-only"),
        )
        comparison = self._records(
            COMPARISON_MONTH,
            _monthly_row(station_id="comparison-only", month=COMPARISON_MONTH),
        )

        result = ASSIGN_MONTHLY_STATION(
            centroid=self._centroid(),
            target_month=TARGET_MONTH,
            comparison_month=COMPARISON_MONTH,
            target_records=target,
            comparison_records=comparison,
        )

        assert result is None

    def test_equal_distance_uses_station_id_as_deterministic_tie_break(self) -> None:
        target = self._records(
            TARGET_MONTH,
            _monthly_row(station_id="B", longitude="13.7300"),
            _monthly_row(station_id="A", longitude="13.7500"),
        )
        comparison = self._records(
            COMPARISON_MONTH,
            _monthly_row(station_id="B", longitude="13.7300", month=COMPARISON_MONTH),
            _monthly_row(station_id="A", longitude="13.7500", month=COMPARISON_MONTH),
        )

        result = ASSIGN_MONTHLY_STATION(
            centroid=self._centroid(),
            target_month=TARGET_MONTH,
            comparison_month=COMPARISON_MONTH,
            target_records=target,
            comparison_records=comparison,
        )

        assert result is not None
        assert result.station_id == "A"

    def test_distance_over_50_km_is_a_boolean_without_german_wording(self) -> None:
        target = self._records(
            TARGET_MONTH,
            _monthly_row(latitude="52.0000", longitude="13.7400"),
        )
        comparison = self._records(
            COMPARISON_MONTH,
            _monthly_row(latitude="52.0000", longitude="13.7400", month=COMPARISON_MONTH),
        )

        result = ASSIGN_MONTHLY_STATION(
            centroid=self._centroid(),
            target_month=TARGET_MONTH,
            comparison_month=COMPARISON_MONTH,
            target_records=target,
            comparison_records=comparison,
        )

        assert result is not None
        assert result.distance_km > 50
        assert result.distance_exceeds_50_km is True
        assert not hasattr(result, "label_de")

    def test_assignment_requires_a_caller_supplied_versioned_centroid(self) -> None:
        target = self._records(TARGET_MONTH, _monthly_row())
        comparison = self._records(
            COMPARISON_MONTH,
            _monthly_row(month=COMPARISON_MONTH),
        )

        with pytest.raises(TypeError):
            ASSIGN_MONTHLY_STATION(
                target_month=TARGET_MONTH,
                comparison_month=COMPARISON_MONTH,
                target_records=target,
                comparison_records=comparison,
            )

        assert not hasattr(dwd_adapter, "DEFAULT_PLZ_CENTROIDS")
        assert not hasattr(dwd_adapter, "fetch_plz_centroid")
        assert not hasattr(dwd_adapter, "persist_monthly_station_assignment")

    def test_coordinate_drift_for_same_station_between_months_fails_safely(self) -> None:
        target = self._records(TARGET_MONTH, _monthly_row())
        comparison = self._records(
            COMPARISON_MONTH,
            _monthly_row(
                month=COMPARISON_MONTH,
                latitude="51.0501",
                longitude="13.7400",
            ),
        )

        with pytest.raises(MONTHLY_IMPORT_ERROR, match=r"coordinate|drift|station"):
            ASSIGN_MONTHLY_STATION(
                centroid=self._centroid(),
                target_month=TARGET_MONTH,
                comparison_month=COMPARISON_MONTH,
                target_records=target,
                comparison_records=comparison,
            )

    @pytest.mark.parametrize(
        ("field_name", "bad_value"),
        [
            ("station_id", ""),
            ("station_name", ""),
            ("latitude", 51.05),
            ("latitude", Decimal("NaN")),
            ("latitude", Decimal("90.0001")),
            ("longitude", 13.74),
            ("longitude", Decimal("Infinity")),
            ("longitude", Decimal("180.0001")),
            ("month", "202513"),
            ("month", COMPARISON_MONTH),
            ("valid_day_count", "31"),
            ("valid_day_count", 32),
            ("monthly_degree_days", 590.25),
            ("monthly_degree_days", Decimal("NaN")),
            ("monthly_degree_days", Decimal("-0.01")),
            ("heating_day_count", "27"),
            ("heating_day_count", 32),
            ("ten_year_mean", 610.125),
            ("ten_year_mean", Decimal("Infinity")),
            ("ten_year_mean", Decimal("-0.01")),
            ("source_path", "forged-path"),
            ("source_file", ""),
            ("standard", "VDI 2067"),
            ("heating_limit_celsius", 16),
            ("reference_room_temperature_celsius", 19),
            ("unit", "K"),
            ("attribution", "forged attribution"),
            ("nature", "forged nature"),
            ("rechtsstand", "07/2026"),
            ("verification_status", "geprueft"),
        ],
    )
    def test_assignment_revalidates_forged_target_record_fields(
        self, field_name: str, bad_value: object
    ) -> None:
        canonical = self._records(TARGET_MONTH, _monthly_row())[0]
        forged = _forge_monthly_record(canonical, **{field_name: bad_value})
        comparison = self._records(
            COMPARISON_MONTH,
            _monthly_row(month=COMPARISON_MONTH),
        )

        with pytest.raises(MONTHLY_IMPORT_ERROR):
            ASSIGN_MONTHLY_STATION(
                centroid=self._centroid(),
                target_month=TARGET_MONTH,
                comparison_month=COMPARISON_MONTH,
                target_records=(forged,),
                comparison_records=comparison,
            )

    def test_assignment_revalidates_forged_comparison_record(self) -> None:
        target = self._records(TARGET_MONTH, _monthly_row())
        canonical = self._records(
            COMPARISON_MONTH,
            _monthly_row(month=COMPARISON_MONTH),
        )[0]
        forged = _forge_monthly_record(canonical, attribution="forged attribution")

        with pytest.raises(MONTHLY_IMPORT_ERROR):
            ASSIGN_MONTHLY_STATION(
                centroid=self._centroid(),
                target_month=TARGET_MONTH,
                comparison_month=COMPARISON_MONTH,
                target_records=target,
                comparison_records=(forged,),
            )

    def test_assignment_requires_exact_record_type_not_subclass_or_lookalike(self) -> None:
        canonical = self._records(TARGET_MONTH, _monthly_row())[0]
        comparison = self._records(
            COMPARISON_MONTH,
            _monthly_row(month=COMPARISON_MONTH),
        )

        class RecordSubclass(MONTHLY_RECORD_TYPE):  # type: ignore[misc]
            pass

        subclass = object.__new__(RecordSubclass)
        for field in fields(canonical):
            if not field.name.startswith("_"):
                object.__setattr__(subclass, field.name, getattr(canonical, field.name))

        for forged in (subclass, object()):
            with pytest.raises(MONTHLY_IMPORT_ERROR, match=r"record|type"):
                ASSIGN_MONTHLY_STATION(
                    centroid=self._centroid(),
                    target_month=TARGET_MONTH,
                    comparison_month=COMPARISON_MONTH,
                    target_records=(forged,),
                    comparison_records=comparison,
                )

    def test_assignment_rejects_duplicate_station_identity_in_either_month(self) -> None:
        target_record = self._records(TARGET_MONTH, _monthly_row())[0]
        comparison_record = self._records(
            COMPARISON_MONTH,
            _monthly_row(month=COMPARISON_MONTH),
        )[0]

        for target, comparison in (
            ((target_record, target_record), (comparison_record,)),
            ((target_record,), (comparison_record, comparison_record)),
        ):
            with pytest.raises(MONTHLY_IMPORT_ERROR, match="duplicate"):
                ASSIGN_MONTHLY_STATION(
                    centroid=self._centroid(),
                    target_month=TARGET_MONTH,
                    comparison_month=COMPARISON_MONTH,
                    target_records=target,
                    comparison_records=comparison,
                )

    def test_assignment_requires_one_common_nonempty_source_file_per_month(self) -> None:
        target = self._records(
            TARGET_MONTH,
            _monthly_row(station_id="001"),
            _monthly_row(station_id="002", longitude="13.7500"),
        )
        comparison = self._records(
            COMPARISON_MONTH,
            _monthly_row(station_id="001", month=COMPARISON_MONTH),
            _monthly_row(station_id="002", month=COMPARISON_MONTH, longitude="13.7500"),
        )
        target_with_mixed_sources = (
            target[0],
            _forge_monthly_record(target[1], source_file="other-target-source"),
        )

        with pytest.raises(MONTHLY_IMPORT_ERROR, match=r"source.file|source file"):
            ASSIGN_MONTHLY_STATION(
                centroid=self._centroid(),
                target_month=TARGET_MONTH,
                comparison_month=COMPARISON_MONTH,
                target_records=target_with_mixed_sources,
                comparison_records=comparison,
            )

    def test_assignment_evidence_is_sufficient_for_u4_reproduction(self) -> None:
        target = self._records(TARGET_MONTH, _monthly_row())
        comparison = self._records(
            COMPARISON_MONTH,
            _monthly_row(month=COMPARISON_MONTH),
        )

        result = ASSIGN_MONTHLY_STATION(
            centroid=self._centroid(),
            target_month=TARGET_MONTH,
            comparison_month=COMPARISON_MONTH,
            target_records=target,
            comparison_records=comparison,
        )

        assert result is not None
        assert result.target_source_file == f"source-{TARGET_MONTH}"
        assert result.comparison_source_file == f"source-{COMPARISON_MONTH}"
        assert result.assignment_nature == "Konvention"
        assert result.rechtsstand == "08/2026"
        assert result.verification_status == "verify-before-production"
        assert result.assignment_method == "nearest_common_valid_station_great_circle"
        assert result.assignment_method_version == "1"

    def test_stable_distance_uses_mean_earth_radius_and_half_up_six_decimals(self) -> None:
        target = self._records(
            TARGET_MONTH,
            _monthly_row(latitude="0", longitude="1"),
        )
        comparison = self._records(
            COMPARISON_MONTH,
            _monthly_row(latitude="0", longitude="1", month=COMPARISON_MONTH),
        )

        result = ASSIGN_MONTHLY_STATION(
            centroid=self._centroid(latitude="0", longitude="0"),
            target_month=TARGET_MONTH,
            comparison_month=COMPARISON_MONTH,
            target_records=target,
            comparison_records=comparison,
        )

        assert result is not None
        expected = (EARTH_MEAN_RADIUS_KM * Decimal("0.017453292519943295")).quantize(
            DISTANCE_QUANTUM_KM,
            rounding=DISTANCE_ROUNDING,
        )
        assert result.distance_km == expected == Decimal("111.195080")
        assert result.distance_km.as_tuple().exponent == -6

    def test_stable_quantized_distance_drives_ranking_then_station_id_tie_break(
        self,
    ) -> None:
        target = self._records(
            TARGET_MONTH,
            _monthly_row(station_id="A", latitude="0", longitude="0.00899320723452684"),
            _monthly_row(station_id="B", latitude="0", longitude="0.00899320453656575"),
        )
        comparison = self._records(
            COMPARISON_MONTH,
            _monthly_row(
                station_id="A",
                latitude="0",
                longitude="0.00899320723452684",
                month=COMPARISON_MONTH,
            ),
            _monthly_row(
                station_id="B",
                latitude="0",
                longitude="0.00899320453656575",
                month=COMPARISON_MONTH,
            ),
        )

        result = ASSIGN_MONTHLY_STATION(
            centroid=self._centroid(latitude="0", longitude="0"),
            target_month=TARGET_MONTH,
            comparison_month=COMPARISON_MONTH,
            target_records=target,
            comparison_records=comparison,
        )

        assert result is not None
        assert result.station_id == "A"
        assert result.distance_km == Decimal("1.000000")

    @pytest.mark.parametrize(
        ("latitude", "expected_distance", "expected_over_50"),
        [
            ("0.44966018545955044", Decimal("50.000000"), False),
            ("0.44966018725819124", Decimal("50.000001"), True),
        ],
    )
    def test_stable_quantized_distance_drives_50_km_flag(
        self,
        latitude: str,
        expected_distance: Decimal,
        expected_over_50: bool,
    ) -> None:
        target = self._records(
            TARGET_MONTH,
            _monthly_row(latitude=latitude, longitude="0"),
        )
        comparison = self._records(
            COMPARISON_MONTH,
            _monthly_row(latitude=latitude, longitude="0", month=COMPARISON_MONTH),
        )

        result = ASSIGN_MONTHLY_STATION(
            centroid=self._centroid(latitude="0", longitude="0"),
            target_month=TARGET_MONTH,
            comparison_month=COMPARISON_MONTH,
            target_records=target,
            comparison_records=comparison,
        )

        assert result is not None
        assert result.distance_km == expected_distance
        assert result.distance_exceeds_50_km is expected_over_50

    def test_parser_origin_seals_public_direct_record_construction(self) -> None:
        parsed = self._records(TARGET_MONTH, _monthly_row())[0]
        canonical_public_values = {
            field.name: getattr(parsed, field.name)
            for field in fields(parsed)
            if not field.name.startswith("_")
        }

        with pytest.raises(MONTHLY_IMPORT_ERROR, match=r"parser|origin|construct"):
            MONTHLY_RECORD_TYPE(**canonical_public_values)

    def test_parser_origin_seals_dataclasses_replace_clone(self) -> None:
        parsed = self._records(TARGET_MONTH, _monthly_row())[0]

        with pytest.raises(MONTHLY_IMPORT_ERROR, match=r"parser|origin|construct"):
            replace(parsed)

    def test_parser_origin_records_are_accepted_but_same_shaped_lookalikes_are_not(
        self,
    ) -> None:
        target = self._records(TARGET_MONTH, _monthly_row())
        comparison = self._records(
            COMPARISON_MONTH,
            _monthly_row(month=COMPARISON_MONTH),
        )

        class RecordLookalike:
            pass

        lookalike = RecordLookalike()
        for field in fields(target[0]):
            if not field.name.startswith("_"):
                setattr(lookalike, field.name, getattr(target[0], field.name))

        result = ASSIGN_MONTHLY_STATION(
            centroid=self._centroid(),
            target_month=TARGET_MONTH,
            comparison_month=COMPARISON_MONTH,
            target_records=target,
            comparison_records=comparison,
        )
        assert result is not None
        assert result.station_id == "001"

        with pytest.raises(MONTHLY_IMPORT_ERROR, match=r"record|type|origin"):
            ASSIGN_MONTHLY_STATION(
                centroid=self._centroid(),
                target_month=TARGET_MONTH,
                comparison_month=COMPARISON_MONTH,
                target_records=(lookalike,),
                comparison_records=comparison,
            )
