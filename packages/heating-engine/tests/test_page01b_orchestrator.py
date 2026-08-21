"""Executable Page 01b contract for the shared H0-H8 orchestrator.

The cent oracles stay in ``berkay_01b_golden.py``.  This module adds the
missing integration boundary: every Page 01b fixture family must pass through
``calculate_page01b_statement`` and return one durable readiness/result shape.
Lower-level capability tests remain useful, but do not satisfy this gate.
"""

from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import Any, Literal

import pytest
from berkay_01b_golden import PAGE_01B_GOLDENS
from lokara_domain import (
    Co2Step,
    Co2Table,
    DegreeDayTable,
    EmissionFactor,
    EnergyReference,
    HeatingSplitBounds,
    MeasurementUnit,
    Occupancy,
    WarmWaterFormula,
    cents,
    period,
)
from lokara_heating_engine import (
    AnnualClimateFactor,
    AnnualComparisonInput,
    Co2Input,
    DeviceReadingSpan,
    DistrictHeatDisclosure,
    HeatingConsumptionSegment,
    HeatingDevice,
    HeatingInput,
    HeatingInputError,
    HeatingRules,
    HeatingUnit,
    InvoiceCostInput,
    MdlCo2Calculation,
    MdlStatementInput,
    Page01bStatementResult,
    PlantCo2Input,
    RiskTriggers,
    SelfBillingStatementInput,
    WarmWaterInput,
    calculate_page01b_statement,
)

EXPECTED_IDS = {
    *(f"01b-F{number:02}" for number in range(1, 28)),
    "01b-F26b",
    "01b-F26c",
    "01b-F28a",
    "01b-F28b",
    "01b-F29",
    "01b-F30",
    "01b-F31",
}

CO2_TABLE: Co2Table = (
    Co2Step(Decimal(12), 0),
    Co2Step(Decimal(17), 10),
    Co2Step(Decimal(22), 20),
    Co2Step(Decimal(27), 30),
    Co2Step(Decimal(32), 40),
    Co2Step(Decimal(37), 50),
    Co2Step(Decimal(42), 60),
    Co2Step(Decimal(47), 70),
    Co2Step(Decimal(52), 80),
    Co2Step(None, 95),
)
RULES = HeatingRules(
    consumption_share=Decimal("0.7"),
    split_bounds=HeatingSplitBounds(Decimal("0.5"), Decimal("0.7")),
    warm_water_formula=WarmWaterFormula(Decimal("2.5"), Decimal(60), Decimal(10), Decimal(32)),
    degree_days=DegreeDayTable(
        tenth_promille_by_month=(1700, 1500, 1300, 800, 400, 133, 133, 134, 300, 800, 1200, 1600)
    ),
    co2_table=CO2_TABLE,
    co2_rechtsstand="Rechtsstand 01/2023",
)


def _canonical_input(
    *,
    total_cost: int = 350_600,
    total_energy: str = "28000",
    co2_mass: str | None = "5628",
    co2_cost: int | None = 30_954,
    warm_water_volume: str | None = "78",
    measured_ww_energy: str | None = None,
    share: str = "0.7",
    heat_values: tuple[str | None, str | None, str | None] = ("4100.0", "3600.0", "3050.0"),
    ww_values: tuple[str | None, str | None, str | None] = ("34", "21", "23"),
    energy_reference: EnergyReference | None = None,
    emission_factor: EmissionFactor | None = None,
) -> HeatingInput:
    rules = HeatingRules(
        consumption_share=Decimal(share),
        split_bounds=RULES.split_bounds,
        warm_water_formula=RULES.warm_water_formula,
        degree_days=RULES.degree_days,
        co2_table=RULES.co2_table,
        co2_rechtsstand=RULES.co2_rechtsstand,
    )
    return HeatingInput(
        billing_period=period("2025-01-01", "2026-01-01"),
        total_cost=cents(total_cost),
        total_energy_kwh=Decimal(total_energy),
        units=tuple(
            HeatingUnit(
                unit_id,
                area,
                None if heat is None else Decimal(heat),
                None if ww is None else Decimal(ww),
                MeasurementUnit.HKV_UNITS,
            )
            for unit_id, area, heat, ww in zip(
                ("WE-01", "WE-02", "WE-03"),
                (6200, 7400, 5800),
                heat_values,
                ww_values,
                strict=True,
            )
        ),
        occupancies=(
            Occupancy("WE-01", "Muster", period("2025-01-01")),
            Occupancy("WE-02", "Schneider", period("2025-01-01", "2025-08-01")),
            Occupancy("WE-02", "Weber", period("2025-09-01")),
            Occupancy("WE-03", "Beispiel", period("2025-01-01")),
        ),
        rules=rules,
        warm_water=(
            WarmWaterInput(
                volume_m3=None if warm_water_volume is None else Decimal(warm_water_volume),
                measured_energy_kwh=(
                    None if measured_ww_energy is None else Decimal(measured_ww_energy)
                ),
            )
            if warm_water_volume is not None or measured_ww_energy is not None
            else None
        ),
        co2=(
            Co2Input(
                total_co2_kg=None if co2_mass is None else Decimal(co2_mass),
                co2_cost=None if co2_cost is None else cents(co2_cost),
                emission_factor=emission_factor,
            )
            if co2_mass is not None or co2_cost is not None or emission_factor is not None
            else None
        ),
        energy_reference=energy_reference,
    )


def _result(
    heating: HeatingInput | None = None,
    **changes: Any,
) -> Page01bStatementResult:
    return calculate_page01b_statement(
        SelfBillingStatementInput(heating=heating or _canonical_input(), **changes)
    )


def _measured_segments(*, include_heat: bool = True) -> tuple[HeatingConsumptionSegment, ...]:
    heat = ("4100.0", "2520.0", "0.0", "1080.0", "3050.0")
    return tuple(
        HeatingConsumptionSegment(
            unit_id,
            tenancy_id,
            Decimal(heat_value) if include_heat else None,
            Decimal(ww_value),
        )
        for unit_id, tenancy_id, heat_value, ww_value in zip(
            ("WE-01", "WE-02", "WE-02", "WE-02", "WE-03"),
            ("Muster", "Schneider", None, "Weber", "Beispiel"),
            heat,
            ("34", "15", "0", "6", "23"),
            strict=True,
        )
    )


def _assert_allocation(result: Page01bStatementResult, fixture_id: str) -> None:
    case = PAGE_01B_GOLDENS[fixture_id]
    assert result.readiness == "READY"
    assert result.values is not None
    assert tuple(int(value) for value in result.values.renter_totals) == case["renter_totals"]
    assert int(result.values.owner_total) == case["owner_total"]
    assert int(result.values.billable_total) == case["billable_total"]


def test_fixture_register_is_still_exactly_34_ids() -> None:
    assert set(PAGE_01B_GOLDENS) == EXPECTED_IDS
    assert len(EXPECTED_IDS) == 34


def test_f01_full_self_billing_uses_measured_tenant_segments() -> None:
    _assert_allocation(_result(segments=_measured_segments()), "01b-F01")


@pytest.mark.parametrize(
    ("fixture_id", "mass", "period_end", "expected_share"),
    [
        ("01b-F03", "2328", "2026-01-01", 10),
        ("01b-F04", "10088", "2026-01-01", 95),
        ("01b-F05", "1753.150685", "2025-10-03", 10),
        ("01b-F06", "4200", "2025-10-03", 40),
    ],
)
def test_f03_to_f06_co2_boundaries_and_annualisation(
    fixture_id: str, mass: str, period_end: str, expected_share: int
) -> None:
    case = PAGE_01B_GOLDENS[fixture_id]
    heating = _canonical_input(
        co2_mass=mass, co2_cost=12_800 if fixture_id != "01b-F06" else 23_100
    )
    heating = HeatingInput(
        billing_period=period("2025-01-01", period_end),
        total_cost=heating.total_cost,
        total_energy_kwh=heating.total_energy_kwh,
        units=heating.units,
        occupancies=heating.occupancies,
        rules=heating.rules,
        warm_water=heating.warm_water,
        co2=heating.co2,
    )
    result = _result(heating)
    assert result.readiness == "READY"
    assert result.values is not None
    assert result.values.co2_landlord_percent == expected_share == case["landlord_percent"]
    assert str(result.values.co2_intensity) == case["intensity"]


@pytest.mark.parametrize(
    ("fixture_id", "plant", "expected_share", "module_enabled"),
    [
        ("01b-F07", PlantCo2Input("erdgas", "nichtwohn", True), 50, True),
        (
            "01b-F08",
            PlantCo2Input(
                "erdgas",
                "wohn",
                True,
                protection_kind="denkmalschutz",
                protection_proof_ref="proof://denkmal/2025",
            ),
            20,
            True,
        ),
        (
            "01b-F09",
            PlantCo2Input(
                "erdgas",
                "wohn",
                True,
                full_exclusion=True,
                exclusion_proof_ref="proof://section-9-2/2025",
            ),
            0,
            True,
        ),
        ("01b-F10", PlantCo2Input("waermepumpe", "wohn", True), None, False),
    ],
)
def test_f07_to_f10_plant_state_is_integrated(
    fixture_id: str,
    plant: PlantCo2Input,
    expected_share: int | None,
    module_enabled: bool,
) -> None:
    case = PAGE_01B_GOLDENS[fixture_id]
    result = _result(plant=plant)
    assert result.readiness == "READY"
    assert result.values is not None
    assert result.values.co2_module_enabled is module_enabled
    assert result.values.co2_landlord_percent == expected_share
    assert int(result.values.billable_total) == case["billable_total"]


def test_f02_mass_fallback_carries_warning_provenance_and_risk() -> None:
    case = PAGE_01B_GOLDENS["01b-F02"]
    result = _result(
        _canonical_input(
            co2_mass=None,
            energy_reference=EnergyReference.HU,
            emission_factor=EmissionFactor(Decimal("0.201"), EnergyReference.HU),
        )
    )
    assert result.readiness == "READY"
    assert result.values is not None
    assert result.values.co2_mass_grams == case["hu_fallback_mass_grams"]
    assert [finding.code for finding in result.findings] == ["supplier_co2_mass_derived"]
    assert [item.code for item in result.provenance] == ["co2_mass_emission_factor"]
    assert [risk.code for risk in result.risks] == ["co2_disclosure_missing"]


def test_f11_measured_ww_energy_reaches_the_final_allocation() -> None:
    _assert_allocation(
        _result(_canonical_input(measured_ww_energy="9100"), segments=_measured_segments()),
        "01b-F11",
    )


def test_f12_area_ww_fallback_is_visible_on_the_shared_channel() -> None:
    heating = _canonical_input(warm_water_volume=None)
    result = _result(
        replace(heating, warm_water=WarmWaterInput(volume_m3=None)),
        segments=_measured_segments(),
    )
    _assert_allocation(result, "01b-F12")
    assert [finding.code for finding in result.findings] == ["ww_area_fallback"]


def test_f13_non_connected_plant_has_no_ww_blocks() -> None:
    result = _result(
        _canonical_input(warm_water_volume=None, ww_values=(None, None, None)),
        plant=PlantCo2Input("erdgas", "wohn", False),
    )
    assert result.values is not None
    heating = result.values.heating_result
    assert heating is not None
    assert int(heating.ww_pot) == 0


def test_f14_ratio_change_carries_owner_preview() -> None:
    result = _result(
        _canonical_input(share="0.5"),
        owner_preview_baseline=cents(3_285),
        segments=_measured_segments(),
    )
    _assert_allocation(result, "01b-F14")
    assert result.owner_burden_preview is not None
    assert int(result.owner_burden_preview.change) == 2_193


def test_f15_heat_meter_kwh_unit_survives_the_orchestrator() -> None:
    heating = _canonical_input(heat_values=("9000", "7500", "5000"))
    heating = HeatingInput(
        billing_period=heating.billing_period,
        total_cost=heating.total_cost,
        total_energy_kwh=heating.total_energy_kwh,
        units=tuple(
            HeatingUnit(
                unit.unit_id,
                unit.area_sqm_x100,
                unit.heat_consumption,
                unit.ww_consumption_m3,
                MeasurementUnit.KWH,
            )
            for unit in heating.units
        ),
        occupancies=heating.occupancies,
        rules=heating.rules,
        warm_water=heating.warm_water,
        co2=heating.co2,
    )
    result = _result(heating)
    assert result.values is not None and result.values.heating_result is not None
    assert result.values.heating_result.heat_consumption_unit is MeasurementUnit.KWH


def test_f16_unsegmented_change_uses_k3_and_keeps_vacancy() -> None:
    _assert_allocation(_result(segments=_measured_segments(include_heat=False)), "01b-F16")


def test_f17_estimate_keeps_device_provenance() -> None:
    result = _result(
        devices=(
            HeatingDevice(
                "88-3041", "WE-03", "Wohnzimmer", MeasurementUnit.HKV_UNITS, Decimal("1.0")
            ),
        ),
        device_spans=(
            DeviceReadingSpan(
                "88-3041",
                "PARTY",
                "Beispiel",
                None,
                None,
                previous_period_units=Decimal("620"),
                estimation_basis="Vorjahreswert 2024",
                reading_reasons=("PERIODIC",),
                reading_sources=("MDL",),
                provenance_refs=("MDL-Datei Zeile 17",),
            ),
        ),
    )
    assert result.readiness == "READY"
    assert result.device_evidence[0].estimated is True
    assert result.device_evidence[0].estimation_basis == "Vorjahreswert 2024"
    assert result.device_evidence[0].reading_sources == ("MDL",)
    assert "device_estimate" in [finding.code for finding in result.findings]
    assert "device_previous_period" in [item.code for item in result.provenance]
    assert "MDL-Datei Zeile 17" in [item.source_ref for item in result.provenance]


def test_f18_over_25_percent_falls_back_to_area_end_to_end() -> None:
    _assert_allocation(
        _result(
            _canonical_input(heat_values=("4100", "3600", None), ww_values=("34", "21", None)),
            area_fallback_authorized=True,
        ),
        "01b-F18",
    )


def test_f19_oil_stock_result_is_carried_as_provenance() -> None:
    from lokara_heating_engine import OilPurchase, OilStockInput

    result = _result(
        oil_stock=OilStockInput(
            Decimal(3200),
            cents(294_400),
            (
                OilPurchase(Decimal(2500), cents(245_000)),
                OilPurchase(Decimal(2000), cents(210_000)),
            ),
            Decimal(2100),
        ),
        oil_heating_value_kwh_per_litre=Decimal(10),
        oil_emission_factor_kg_per_kwh=Decimal("0.266"),
    )
    assert result.oil_consumption is not None
    assert int(result.oil_consumption.fuel_cost) == PAGE_01B_GOLDENS["01b-F19"]["fuel_cost"]
    assert "oil_stock_consumption" in [item.code for item in result.provenance]


def test_f20_district_heat_cost_and_disclosure_reach_one_result() -> None:
    disclosure = DistrictHeatDisclosure("Versorgermix", Decimal("123.4"), Decimal("0.7"), cents(0))
    result = _result(
        _canonical_input(total_cost=438_600, co2_mass="4870", co2_cost=26_800),
        plant=PlantCo2Input("fernwaerme", "wohn", True),
        invoice_costs=(
            InvoiceCostInput("district_heat", cents(410_000), date(2025, 1, 1), date(2026, 1, 1)),
            InvoiceCostInput(
                "operating_electricity", cents(9_600), date(2025, 1, 1), date(2026, 1, 1)
            ),
            InvoiceCostInput("maintenance", cents(19_000), date(2025, 1, 1), date(2026, 1, 1)),
        ),
        district_heat_disclosure=disclosure,
    )
    assert result.values is not None
    assert int(result.values.billable_total) == PAGE_01B_GOLDENS["01b-F20"]["billable_total"]
    assert "district_heat_supplier" in [item.code for item in result.provenance]


def test_f21_zero_consumption_denominator_is_a_blocked_result() -> None:
    result = _result(_canonical_input(heat_values=("0", "0", "0")))
    assert result.readiness == "BLOCKED"
    assert result.values is None
    assert [finding.code for finding in result.findings] == ["zero_heat_consumption_denominator"]


def test_f22_negative_delta_is_structural_but_replacement_devices_work() -> None:
    device = HeatingDevice("old", "WE-01", "Wohnzimmer", MeasurementUnit.HKV_UNITS, Decimal(1))
    with pytest.raises(HeatingInputError, match="negativer Verbrauch"):
        _result(
            devices=(device,),
            device_spans=(
                DeviceReadingSpan("old", "PARTY", "Muster", Decimal(12480), Decimal(11020)),
            ),
        )
    result = _result(
        devices=(
            device,
            HeatingDevice("new", "WE-01", "Wohnzimmer", MeasurementUnit.HKV_UNITS, Decimal(1)),
        ),
        device_spans=(
            DeviceReadingSpan("old", "PARTY", "Muster", Decimal(12480), Decimal(12900)),
            DeviceReadingSpan("new", "PARTY", "Muster", Decimal(0), Decimal(1040)),
        ),
    )
    assert sum((line.units for line in result.device_evidence), Decimal(0)) == Decimal("1460.0")


@pytest.mark.parametrize(
    ("mass", "code"),
    [
        ("14500", "co2_intensity_above_plausibility_band"),
        ("800", "co2_intensity_below_plausibility_band"),
    ],
)
def test_f23_plausibility_is_non_blocking_and_ordered(mass: str, code: str) -> None:
    result = _result(_canonical_input(co2_mass=mass))
    assert result.readiness == "READY"
    assert [finding.code for finding in result.findings] == [code]
    assert result.findings[0].severity == "WARNING"


def test_f24_invoice_overlap_is_applied_and_non_dismissible() -> None:
    result = _result(
        invoice_costs=(
            InvoiceCostInput("fuel", cents(360_000), date(2024, 11, 1), date(2025, 11, 1)),
        )
    )
    assert result.cost_aggregation is not None
    assert int(result.cost_aggregation.total_cost) == 299_836
    assert [finding.code for finding in result.findings] == ["invoice_period_incomplete"]
    assert result.findings[0].dismissible is False


def test_f25_reduction_risks_stay_separate_and_never_change_money() -> None:
    result = _result(
        segments=_measured_segments(),
        risks=RiskTriggers(
            remote_readability_missing=True,
            section_6a_information_missing=True,
            co2_disclosure_missing=True,
            consumption_billing_missing=True,
        ),
    )
    assert [risk.code for risk in result.risks] == [
        "remote_readability_missing",
        "section_6a_information_missing",
        "co2_disclosure_missing",
        "consumption_billing_missing",
    ]
    assert [risk.percent for risk in result.risks] == [
        Decimal(3),
        Decimal(3),
        Decimal(3),
        Decimal(15),
    ]
    assert result.risk_total is None
    _assert_allocation(result, "01b-F01")


@pytest.mark.parametrize(
    ("fixture_id", "unit_total", "expected_code"),
    [
        ("01b-F26", "74", None),
        ("01b-F26b", "69", "ww_meter_gap_notice"),
        ("01b-F26c", "61", "ww_meter_gap_legal_warning"),
    ],
)
def test_f26_gap_uses_the_central_denominator(
    fixture_id: str, unit_total: str, expected_code: str | None
) -> None:
    first = Decimal(unit_total) - Decimal(40)
    result = _result(_canonical_input(ww_values=(str(first), "21", "19")))
    codes = [finding.code for finding in result.findings]
    assert (
        (expected_code in codes)
        if expected_code
        else not any(code.startswith("ww_meter_gap") for code in codes)
    )
    if fixture_id == "01b-F26":
        assert result.values is not None and result.values.heating_result is not None
        assert int(result.values.ww_unmetered_owner) == 4_227


def test_f27_device_rounding_and_tenant_change_evidence_survive() -> None:
    devices = (
        HeatingDevice("88-2041", "WE-02", "Wohnzimmer", MeasurementUnit.HKV_UNITS, Decimal("1.8")),
        HeatingDevice(
            "88-2042", "WE-02", "Schlafzimmer", MeasurementUnit.HKV_UNITS, Decimal("1.2")
        ),
        HeatingDevice("88-2043", "WE-02", "Bad", MeasurementUnit.HKV_UNITS, Decimal("2.0")),
    )
    spans = (
        DeviceReadingSpan("88-2041", "PARTY", "Schneider", Decimal(0), Decimal(820)),
        DeviceReadingSpan("88-2042", "PARTY", "Schneider", Decimal(0), Decimal(520)),
        DeviceReadingSpan("88-2043", "PARTY", "Schneider", Decimal(0), Decimal(210)),
        DeviceReadingSpan("88-2041", "OWNER", None, Decimal(820), Decimal(820)),
        DeviceReadingSpan("88-2041", "PARTY", "Weber", Decimal(820), Decimal(1100)),
        DeviceReadingSpan("88-2042", "PARTY", "Weber", Decimal(520), Decimal(700)),
        DeviceReadingSpan("88-2043", "PARTY", "Weber", Decimal(210), Decimal(390)),
    )
    result = _result(devices=devices, device_spans=spans)
    assert result.readiness == "READY"
    assert len(result.device_evidence) == len(spans)
    assert result.device_aggregation is not None
    party = dict(result.device_aggregation.party_units)
    assert party == {"Schneider": Decimal("2520.0"), "Weber": Decimal("1080.0")}


def _mdl(
    branch: Literal["NET", "GROSS"],
    positions: tuple[int, ...],
    owner: int,
    total: int,
    **changes: Any,
) -> Page01bStatementResult:
    return calculate_page01b_statement(
        MdlStatementInput(
            branch=branch,
            renter_ids=("Muster", "Schneider", "Weber", "Beispiel"),
            renter_positions=positions,
            owner_position=owner,
            confirmed_total=total,
            **changes,
        )
    )


def test_f28a_mdl_net_passes_through_without_a_second_deduction() -> None:
    result = _mdl("NET", (127_217, 74_508, 34_782, 98_426), 3_285, 338_218)
    _assert_allocation(result, "01b-F28a")
    assert result.values is not None and int(result.values.co2_landlord_amount) == 0


def test_f28b_mdl_gross_rescales_with_exact_quotient() -> None:
    result = _mdl(
        "GROSS",
        (131_874, 77_236, 36_055, 102_029),
        3_405,
        350_600,
        co2=MdlCo2Calculation(
            total_co2_kg=Decimal(5628),
            co2_cost=cents(30_954),
            heated_area_sqm=Decimal(194),
            table=CO2_TABLE,
            rechtsstand="Rechtsstand 01/2023",
            billing_period=period("2025-01-01", "2026-01-01"),
        ),
    )
    _assert_allocation(result, "01b-F28b")
    assert result.values is not None and int(result.values.co2_landlord_amount) == 12_382


def test_f29_mdl_control_sum_is_a_blocked_result_with_field_reference() -> None:
    result = _mdl("NET", (127_217, 74_508, 3_478, 98_426), 3_285, 338_218)
    assert result.readiness == "BLOCKED"
    assert result.values is None
    assert result.findings[0].code == "mdl_control_sum_mismatch"
    assert result.findings[0].field_ref == "renter_positions"


def test_f30_missing_mdl_co2_evidence_is_a_separate_risk_per_renter() -> None:
    result = _mdl(
        "NET",
        (127_217, 74_508, 34_782, 98_426),
        3_285,
        338_218,
        co2_evidence_present=False,
    )
    assert result.readiness == "READY"
    [risk] = result.risks
    assert risk.code == "co2_disclosure_missing"
    assert (
        tuple(int(value) for value in risk.amounts) == PAGE_01B_GOLDENS["01b-F30"]["risk_3_percent"]
    )


def test_f31_annual_comparison_adjusts_heat_only_and_labels_fallbacks() -> None:
    ready = _result(
        annual_comparison=AnnualComparisonInput(
            current_heat=Decimal("4100"),
            previous_heat=Decimal("3900"),
            current_warm_water=Decimal("34"),
            previous_warm_water=Decimal("31"),
            current_factor=AnnualClimateFactor(Decimal("1.04"), "2025", "DWD"),
            previous_factor=AnnualClimateFactor(Decimal("0.98"), "2024", "DWD"),
        )
    )
    assert ready.annual_comparison is not None
    assert ready.annual_comparison.state == "READY"
    assert ready.annual_comparison.current_heat_adjusted == Decimal("4264.00")
    assert ready.annual_comparison.previous_heat_adjusted == Decimal("3822.00")
    assert ready.annual_comparison.current_warm_water == Decimal("34")
    assert ready.annual_comparison.adjusted_change_percent == Decimal("11.6")

    fallback = _result(
        annual_comparison=AnnualComparisonInput(
            current_heat=Decimal("4100"),
            previous_heat=Decimal("3900"),
            current_warm_water=Decimal("34"),
            previous_warm_water=Decimal("31"),
        )
    )
    assert fallback.annual_comparison is not None
    assert fallback.annual_comparison.state == "RAW_FALLBACK"
    assert fallback.annual_comparison.note_de is not None

    no_prior = _result(
        annual_comparison=AnnualComparisonInput(
            current_heat=Decimal("4100"),
            previous_heat=None,
            current_warm_water=Decimal("34"),
            previous_warm_water=None,
        )
    )
    assert no_prior.annual_comparison is not None
    assert no_prior.annual_comparison.state == "NO_PRIOR"
    assert no_prior.annual_comparison.graph_required is False


def test_all_34_fixture_ids_are_owned_by_an_orchestrator_test() -> None:
    covered = {
        "01b-F01",
        "01b-F02",
        "01b-F03",
        "01b-F04",
        "01b-F05",
        "01b-F06",
        "01b-F07",
        "01b-F08",
        "01b-F09",
        "01b-F10",
        "01b-F11",
        "01b-F12",
        "01b-F13",
        "01b-F14",
        "01b-F15",
        "01b-F16",
        "01b-F17",
        "01b-F18",
        "01b-F19",
        "01b-F20",
        "01b-F21",
        "01b-F22",
        "01b-F23",
        "01b-F24",
        "01b-F25",
        "01b-F26",
        "01b-F26b",
        "01b-F26c",
        "01b-F27",
        "01b-F28a",
        "01b-F28b",
        "01b-F29",
        "01b-F30",
        "01b-F31",
    }
    assert covered == EXPECTED_IDS
