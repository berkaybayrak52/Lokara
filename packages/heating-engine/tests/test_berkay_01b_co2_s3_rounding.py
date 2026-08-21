"""§ 5 Abs. 1 S. 3 CO2KostAufG — round the specific CO₂ intensity to one
decimal before classification.

Source: original Page 01b and approved `docs/03-nk-heating-engines.md`
decision 3/R8. Rechtsstand
08/2026. Official norm: https://www.gesetze-im-internet.de/co2kostaufg/__5.html

Berkay confirms that R4/E3 and the old `01b-F05` are superseded. The order is
raw -> annualise (H2) -> round to one decimal -> classify, and the same rounded
value is printed. `ROUND_HALF_UP` remains explicitly a Lokara convention:
neither the statute nor Berkay specifies the tie mode.

These are intentionally red before the engine implementation.
"""

from dataclasses import fields
from decimal import Decimal

from lokara_domain import Co2Step, Co2Table, Period, cents, period
from lokara_heating_engine import landlord_share_percent_for_intensity
from lokara_heating_engine.co2 import split_co2_cost
from lokara_heating_engine.inputs import Co2Result

CO2_TABLE: Co2Table = (
    Co2Step(max_intensity_exclusive=Decimal(12), landlord_share_percent=0),
    Co2Step(max_intensity_exclusive=Decimal(17), landlord_share_percent=10),
    Co2Step(max_intensity_exclusive=Decimal(22), landlord_share_percent=20),
    Co2Step(max_intensity_exclusive=Decimal(27), landlord_share_percent=30),
    Co2Step(max_intensity_exclusive=Decimal(32), landlord_share_percent=40),
    Co2Step(max_intensity_exclusive=Decimal(37), landlord_share_percent=50),
    Co2Step(max_intensity_exclusive=Decimal(42), landlord_share_percent=60),
    Co2Step(max_intensity_exclusive=Decimal(47), landlord_share_percent=70),
    Co2Step(max_intensity_exclusive=Decimal(52), landlord_share_percent=80),
    Co2Step(max_intensity_exclusive=None, landlord_share_percent=95),
)

FULL_YEAR = period("2025-01-01", "2026-01-01")
SHORT_275 = period("2025-04-01", "2026-01-01")
AREA_100 = Decimal(100)
AREA_194 = Decimal(194)
RECHTSSTAND = "Rechtsstand 01/2023"


def _split(
    total_co2_kg: str,
    co2_cost: int,
    *,
    area: Decimal = AREA_100,
    billing_period: Period = FULL_YEAR,
) -> Co2Result:
    return split_co2_cost(
        total_co2_kg=Decimal(total_co2_kg),
        co2_cost=cents(co2_cost),
        heated_area_sqm=area,
        table=CO2_TABLE,
        rechtsstand=RECHTSSTAND,
        billing_period=billing_period,
    )


def _assert_reconciles(result: Co2Result) -> None:
    assert int(result.landlord_amount) + int(result.renter_amount) == int(result.co2_cost)


class TestThe12Boundary:
    def test_11_95_rounds_up_into_the_10_percent_step(self) -> None:
        result = _split("1195", 10_000)
        assert result.intensity_kg_per_sqm == Decimal("12.0")
        assert result.landlord_share_percent == 10
        assert result.band_min_inclusive == Decimal(12)
        assert result.band_max_exclusive == Decimal(17)
        assert int(result.landlord_amount) == 1_000
        assert int(result.renter_amount) == 9_000
        _assert_reconciles(result)

    def test_11_9499_stays_in_the_zero_percent_step(self) -> None:
        result = _split("1194.99", 10_000)
        assert result.intensity_kg_per_sqm == Decimal("11.9")
        assert result.landlord_share_percent == 0
        assert result.band_min_inclusive is None
        assert result.band_max_exclusive == Decimal(12)
        assert int(result.landlord_amount) == 0
        assert int(result.renter_amount) == 10_000
        _assert_reconciles(result)

    def test_12_04_rounds_to_the_bound_without_demotion(self) -> None:
        result = _split("1204", 10_000)
        assert result.intensity_kg_per_sqm == Decimal("12.0")
        assert result.landlord_share_percent == 10
        assert result.band_min_inclusive == Decimal(12)
        assert result.band_max_exclusive == Decimal(17)
        assert int(result.landlord_amount) == 1_000
        assert int(result.renter_amount) == 9_000
        _assert_reconciles(result)

    def test_public_lookup_applies_s3_at_both_sides(self) -> None:
        assert landlord_share_percent_for_intensity(Decimal("11.95"), CO2_TABLE) == 10
        assert landlord_share_percent_for_intensity(Decimal("11.9499"), CO2_TABLE) == 0
        assert landlord_share_percent_for_intensity(Decimal("12.04"), CO2_TABLE) == 10


class TestBerkay01bF05:
    TOTAL_HEATING_COST = 350_600

    def test_reexpected_intensity_step_and_money(self) -> None:
        result = _split("2327.9", 12_803, area=AREA_194)

        assert result.intensity_kg_per_sqm == Decimal("12.0")
        assert result.landlord_share_percent == 10
        assert result.band_min_inclusive == Decimal(12)
        assert result.band_max_exclusive == Decimal(17)
        assert int(result.landlord_amount) == 1_280
        assert int(result.renter_amount) == 11_523
        assert self.TOTAL_HEATING_COST - int(result.landlord_amount) == 349_320
        _assert_reconciles(result)


class TestOrderOfOperations:
    def test_annualise_then_round_selects_step_2(self) -> None:
        # 902 kg / 100 m² = 9,02 over 275 days; annualised = 11,972.
        result = _split("902", 10_000, billing_period=SHORT_275)

        assert result.period_days == 275
        assert result.annualisation_factor == Decimal(365) / Decimal(275)
        assert result.intensity_kg_per_sqm == Decimal("12.0")
        assert result.landlord_share_percent == 10
        assert int(result.landlord_amount) == 1_000
        assert int(result.renter_amount) == 9_000
        _assert_reconciles(result)

    def test_rounding_before_annualisation_would_select_step_1(self) -> None:
        raw = Decimal("9.02")
        rounded_first = raw.quantize(Decimal("0.1")) * Decimal(365) / Decimal(275)
        annualised_first = raw * Decimal(365) / Decimal(275)

        assert landlord_share_percent_for_intensity(rounded_first, CO2_TABLE) == 0
        assert annualised_first == Decimal("11.972")
        assert landlord_share_percent_for_intensity(annualised_first, CO2_TABLE) == 10


class TestResultShape:
    def test_the_only_intensity_field_is_the_quantized_classified_value(self) -> None:
        result = _split("1196", 10_000)
        intensity_fields = [field.name for field in fields(result) if "intensity" in field.name]

        assert intensity_fields == ["intensity_kg_per_sqm"]
        assert result.intensity_kg_per_sqm == Decimal("12.0")
        assert result.intensity_kg_per_sqm.as_tuple().exponent == -1
        _assert_reconciles(result)


def test_the_statutory_table_bounds_and_percentages_do_not_change() -> None:
    assert tuple(
        (step.max_intensity_exclusive, step.landlord_share_percent) for step in CO2_TABLE
    ) == (
        (Decimal(12), 0),
        (Decimal(17), 10),
        (Decimal(22), 20),
        (Decimal(27), 30),
        (Decimal(32), 40),
        (Decimal(37), 50),
        (Decimal(42), 60),
        (Decimal(47), 70),
        (Decimal(52), 80),
        (None, 95),
    )
