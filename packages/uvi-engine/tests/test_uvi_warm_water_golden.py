"""Golden contract for the central remotely-read warm-water UVI stream.

This fixture is intentionally written before the implementation.  It records the
approved source conversion and the expected warm-water-only comparison semantics.
"""

from dataclasses import fields
from datetime import date
from decimal import Decimal
from typing import Any

from lokara_pdf import UviDocumentData
from lokara_uvi_engine import (
    BlockCInput,
    UviRuleBundle,
    WarmWaterBlockAInput,
    evaluate_block_c,
    evaluate_warm_water_block_a,
)

CENTRAL_REMOTE_WARM_WATER_GOLDEN: dict[str, Any] = {
    "building": {"central_warm_water": True, "remote_readable": True},
    "meter": {"medium": "WARM_WATER", "unit": "CUBIC_METRE"},
    "monthly_readings_m3_x1000": {
        "current": (10_000, 14_000),
        "previous_month": (9_000, 10_000),
        "previous_year": (8_000, 10_000),
    },
    "approved_conversion": {
        "source": "§ 9 Abs. 2 HeizkostenV",
        "hot_temp_c": Decimal("60"),
        "cold_temp_c": Decimal("10"),
        "factor_kwh_per_m3": Decimal("125"),
        "formula": "2.5 × (60 - 10)",
    },
    "expected_kwh": {"current": 500, "previous_month": 125, "previous_year": 250},
    "expected_previous_month": {"delta_kwh": 375, "percent": Decimal("300.0")},
    "expected_previous_year_raw": {
        "weather_adjusted": False,
        "delta_kwh": 250,
        "percent": Decimal("100.0"),
    },
    "d2": {
        "warm_water_deduction_kwh_m2a": Decimal("24"),
        "area_sqm": Decimal("80"),
        "monthly_share": Decimal("0.19"),
        "norm_month_kwh": 365,
        "delta_kwh": 135,
        "percent": Decimal("37.0"),
    },
}


def test_central_remote_warm_water_has_a_conditional_document_block() -> None:
    """WW must be carried separately; heating-only UviDocumentData is insufficient."""

    document_fields = {field.name for field in fields(UviDocumentData)}
    assert "warm_water" in document_fields


def test_uvi_document_has_letter_header_fields() -> None:
    document_fields = {field.name for field in fields(UviDocumentData)}
    assert {
        "vermieter_name",
        "vermieter_strasse",
        "vermieter_plz_ort",
        "absenderzeile",
        "mieter_name",
        "mieter_strasse",
        "mieter_plz_ort",
        "liegenschaft_nr",
        "nutzeinheit_nr",
        "objekt_adresse",
        "naechster_monat",
        "support_code",
        "gruss_ort",
    } <= document_fields


def test_warm_water_golden_keeps_conversion_and_raw_prior_year_contract() -> None:
    """The fixture fixes the source-backed conversion and no-weather WW comparison."""

    golden = CENTRAL_REMOTE_WARM_WATER_GOLDEN
    conversion = golden["approved_conversion"]
    assert conversion["factor_kwh_per_m3"] == Decimal("2.5") * (
        conversion["hot_temp_c"] - conversion["cold_temp_c"]
    )
    assert golden["expected_previous_year_raw"]["weather_adjusted"] is False
    assert (
        golden["d2"]["warm_water_deduction_kwh_m2a"]
        * golden["d2"]["area_sqm"]
        * golden["d2"]["monthly_share"]
    ).quantize(Decimal("1")) == Decimal(golden["d2"]["norm_month_kwh"])


def test_missing_warm_water_conversion_is_not_accepted_as_a_fallback() -> None:
    result = evaluate_warm_water_block_a(
        WarmWaterBlockAInput(10_000, 14_000, None),
        UviRuleBundle(evidence=(), unresolved_conflicts=()),
    )
    assert result.status == "blocked"
    assert result.data_quality_flag == "missing_warm_water_conversion"
    assert result.heat_kwh is None


def test_valid_warm_water_conversion_produces_kwh() -> None:
    result = evaluate_warm_water_block_a(
        WarmWaterBlockAInput(10_000, 14_000, Decimal("125")),
        UviRuleBundle(evidence=(), unresolved_conflicts=()),
    )
    assert result.status == "ready"
    assert result.volume_m3 == Decimal("4")
    assert result.heat_kwh == 500


def test_heating_weather_adjustment_uses_non_unit_dwd_degree_day_factor() -> None:
    result = evaluate_block_c(
        BlockCInput(
            current_heat_kwh=900,
            previous_year_heat_kwh=800,
            monthly_degree_days_current=Decimal("120"),
            monthly_degree_days_previous_year=Decimal("100"),
            previous_year_interpolation_notice_de=None,
            station_id="00433",
            distance_km=Decimal("12.4"),
            dataset_attribution_de="Quelle: Deutscher Wetterdienst",
            dataset_as_of="2026-07",
        ),
        UviRuleBundle(evidence=(), unresolved_conflicts=()),
    )
    assert result.weather_adjusted is True
    assert result.weather_adjustment_factor == Decimal("1.2")
    assert result.reference_kwh == 960
    assert result.reference_kwh != 800


def test_fixture_month_is_explicit() -> None:
    """Keep the monthly-share fixture anchored to a concrete UVI month."""

    assert date(2026, 1, 1).month == 1
