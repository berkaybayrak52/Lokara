"""Page 01b A4 RED contracts for normalized self-billing capabilities.

Source: ``berkay-work/Spec-Seiten/01b · Heizkosten- & CO₂-Verteilung ….md``
H1/H1a/H1b/H3/H4 and fixtures F11-F14/F19/F20/F24. Rechtsstand
07/2026. The contracts are pure capability seams; they do not claim the full
self-billing pipeline or the tenant allocations are closed.
"""

from datetime import date
from decimal import Decimal
from typing import Any

import lokara_heating_engine
from berkay_01b_golden import PAGE_01B_GOLDENS
from lokara_domain import cents


def _api(name: str) -> Any:
    value = getattr(lokara_heating_engine, name, None)
    assert callable(value), f"A4 {name} is not implemented"
    return value


def test_h1_baseline_aggregates_the_three_exact_cost_positions() -> None:
    position_type = _api("HeatingCostPosition")
    aggregate = _api("aggregate_plant_cost_positions")
    positions = (
        position_type(kind="fuel", amount=cents(322_000)),
        position_type(kind="operating_electricity", amount=cents(9_600)),
        position_type(kind="maintenance", amount=cents(19_000)),
    )

    result = aggregate(positions=positions, district_heat_disclosure=None)

    assert tuple(int(position.amount) for position in result.positions) == (
        322_000,
        9_600,
        19_000,
    )
    assert int(result.total_cost) == 350_600
    assert sum(int(position.amount) for position in result.positions) == int(result.total_cost)


def test_berkay_01b_f20_aggregates_district_heat_and_carries_supplier_disclosure() -> None:
    position_type = _api("HeatingCostPosition")
    disclosure_type = _api("DistrictHeatDisclosure")
    aggregate = _api("aggregate_plant_cost_positions")

    # Opaque supplier sentinels test identity carry only. They are not legal values.
    disclosure = disclosure_type(
        energy_mix="supplier-stated-energy-mix",
        greenhouse_gas_g_per_kwh=Decimal("123.456"),
        primary_energy_factor=Decimal("7.654"),
        taxes=cents(1_234),
    )
    positions = (
        position_type(kind="district_heat", amount=cents(410_000)),
        position_type(kind="operating_electricity", amount=cents(9_600)),
        position_type(kind="maintenance", amount=cents(19_000)),
    )

    result = aggregate(positions=positions, district_heat_disclosure=disclosure)

    assert int(result.total_cost) == PAGE_01B_GOLDENS["01b-F20"]["plant_total"]
    assert result.district_heat_disclosure is disclosure


def test_berkay_01b_f24_allocates_an_overlapping_invoice_linearly_by_inclusive_days() -> None:
    allocate = _api("allocate_invoice_to_billing_period")
    case = PAGE_01B_GOLDENS["01b-F24"]

    result = allocate(
        amount=cents(360_000),
        invoice_from=date(2024, 11, 1),
        invoice_to=date(2025, 10, 31),
        billing_from=date(2025, 1, 1),
        billing_to=date(2025, 12, 31),
    )

    assert result.invoice_days == case["invoice_days"]
    assert result.overlap_days == case["overlap_days"]
    assert int(result.allocated_amount) == case["allocated_cost"]
    assert result.coverage_ratio == Decimal(304) / Decimal(365)
    assert result.coverage_percent == Decimal(str(case["coverage_percent"]))
    assert result.missing_days == case["missing_days"]
    assert result.warning.code == "invoice_period_incomplete"
    assert result.warning.dismissible is case["warning_dismissible"]
    assert result.warning.blocking is False


def test_berkay_01b_f19_oil_stock_uses_consumption_not_purchases() -> None:
    stock_type = _api("OilStockInput")
    purchase_type = _api("OilPurchase")
    calculate = _api("calculate_oil_consumption")
    case = PAGE_01B_GOLDENS["01b-F19"]

    stock = stock_type(
        opening_litres=Decimal(3_200),
        opening_cost=cents(294_400),
        purchases=(
            purchase_type(litres=Decimal(2_500), cost=cents(245_000)),
            purchase_type(litres=Decimal(2_000), cost=cents(210_000)),
        ),
        closing_litres=Decimal(2_100),
    )
    result = calculate(
        stock=stock,
        heating_value_kwh_per_litre=Decimal(10),
        emission_factor_kg_per_kwh=Decimal("0.266"),
    )

    assert result.available_litres == Decimal(str(case["available_litres"]))
    assert int(result.available_cost) == case["available_cost"]
    assert result.consumed_litres == Decimal(str(case["consumed_litres"]))
    assert result.weighted_cost_per_litre == Decimal(749_400) / Decimal(7_700)
    assert int(result.fuel_cost) == case["fuel_cost"]
    assert int(result.closing_stock_cost) == case["closing_stock"]
    assert result.energy_kwh == Decimal(str(case["energy_kwh"]))
    assert result.co2_grams == case["co2_grams"]
    assert result.co2_cost is None
    assert int(result.fuel_cost) + int(result.closing_stock_cost) == int(result.available_cost)


def test_berkay_01b_f11_measured_ww_energy_has_priority_over_the_volume_formula() -> None:
    separate = _api("separate_warm_water_costs")
    case = PAGE_01B_GOLDENS["01b-F11"]

    result = separate(
        connected_plant=True,
        billable_cost=cents(338_218),
        total_energy_kwh=Decimal(28_000),
        measured_ww_energy_kwh=Decimal(9_100),
        central_ww_volume_m3=Decimal(78),
        hot_water_temperature_c=Decimal(60),
        heated_area_sqm=Decimal(194),
        volume_factor=Decimal("2.5"),
        cold_water_temperature_c=Decimal(10),
        area_fallback_kwh_per_sqm=Decimal(32),
    )

    assert result.method == case["ww_method"]
    assert result.q_ww_kwh == Decimal(str(case["q_ww_kwh"]))
    assert int(result.warm_water_cost) == 109_921
    assert int(result.heating_cost) == 228_297
    assert int(result.warm_water_cost) + int(result.heating_cost) == case["billable_total"]
    assert result.warnings == ()


def test_berkay_01b_f12_missing_measurement_uses_area_and_warns_without_blocking() -> None:
    separate = _api("separate_warm_water_costs")
    case = PAGE_01B_GOLDENS["01b-F12"]

    result = separate(
        connected_plant=True,
        billable_cost=cents(338_218),
        total_energy_kwh=Decimal(28_000),
        measured_ww_energy_kwh=None,
        central_ww_volume_m3=None,
        hot_water_temperature_c=Decimal(60),
        heated_area_sqm=Decimal(194),
        volume_factor=Decimal("2.5"),
        cold_water_temperature_c=Decimal(10),
        area_fallback_kwh_per_sqm=Decimal(32),
    )

    assert result.method == case["ww_method"]
    assert result.q_ww_kwh == Decimal(str(case["q_ww_kwh"]))
    assert int(result.warm_water_cost) == 74_988
    assert int(result.heating_cost) == 263_230
    assert int(result.warm_water_cost) + int(result.heating_cost) == case["billable_total"]
    assert len(result.warnings) == 1
    assert result.warnings[0].code == case["warning"]
    assert result.warnings[0].blocking is False


def test_berkay_01b_f13_non_connected_plant_keeps_one_heating_block() -> None:
    separate = _api("separate_warm_water_costs")
    form_blocks = _api("form_heating_cost_blocks")
    case = PAGE_01B_GOLDENS["01b-F13"]

    separation = separate(
        connected_plant=False,
        billable_cost=cents(338_218),
        total_energy_kwh=Decimal(28_000),
        measured_ww_energy_kwh=None,
        central_ww_volume_m3=None,
        hot_water_temperature_c=Decimal(60),
        heated_area_sqm=Decimal(194),
        volume_factor=Decimal("2.5"),
        cold_water_temperature_c=Decimal(10),
        area_fallback_kwh_per_sqm=Decimal(32),
    )
    blocks = form_blocks(
        heating_cost=separation.heating_cost,
        warm_water_cost=separation.warm_water_cost,
        base_share_percent=30,
    )

    assert separation.method == "not_connected"
    assert int(separation.heating_cost) == case["heating_cost"]
    assert int(separation.warm_water_cost) == case["warm_water_cost"]
    assert int(blocks.heating_base) == case["heating_base"]
    assert int(blocks.heating_consumption) == case["heating_consumption"]
    assert int(blocks.warm_water_base) == 0
    assert int(blocks.warm_water_consumption) == 0
    assert int(blocks.total) == case["billable_total"]


def test_berkay_01b_f14_custom_50_percent_share_forms_exact_complementary_pots() -> None:
    form_blocks = _api("form_heating_cost_blocks")
    case = PAGE_01B_GOLDENS["01b-F14"]

    blocks = form_blocks(
        heating_cost=cents(220_446),
        warm_water_cost=cents(117_772),
        base_share_percent=50,
    )

    assert int(blocks.heating_base) == case["heating_base"]
    assert int(blocks.heating_consumption) == case["heating_consumption"]
    assert int(blocks.warm_water_base) == case["warm_water_base"]
    assert int(blocks.warm_water_consumption) == case["warm_water_consumption"]
    assert int(blocks.total) == case["billable_total"]


def test_berkay_01b_f14_owner_burden_preview_is_visible_before_saving() -> None:
    preview = _api("calculate_owner_burden_preview")
    case = PAGE_01B_GOLDENS["01b-F14"]

    result = preview(
        current_owner_total=cents(3_285),
        proposed_owner_total=cents(5_478),
    )

    assert int(result.current_owner_total) == case["current_owner_total"]
    assert int(result.proposed_owner_total) == case["proposed_owner_total"]
    assert int(result.change) == case["owner_increase"]
    assert result.increases_owner_burden is True
    assert result.show_before_save is True
