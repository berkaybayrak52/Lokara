"""docs/16 § 9: annual DWD climate-factor boundary and import guards.

This test deliberately restates the approved oracle values instead of importing the
data-only oracle.  The annual PLZ climate factor is not the monthly ``hdd_3807``
dataset; monthly parsing and station assignment belong to the next U3 sub-slice.
"""

from dataclasses import FrozenInstanceError, fields
from datetime import date
from decimal import Decimal
from typing import Final

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
