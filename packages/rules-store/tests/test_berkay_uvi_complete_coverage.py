"""Coverage and arithmetic checks for the data-only UVI transcription oracle."""

from decimal import ROUND_HALF_UP, Decimal

from berkay_uvi_golden import (
    DWD_ANNUAL_CLIMATE_FACTOR_PLZ_FIXTURES,
    DWD_ANNUAL_IMPORT_CONTRACT,
    DWD_LATEST_STATE,
    DWD_MONTHLY_DEGREE_DAY_CONTRACT,
    DWD_STATION_ASSIGNMENT_CONTRACT,
    HEIZSPIEGEL_2025_ROWS,
    HEIZSPIEGEL_D2_CONTRACT,
    HEIZSPIEGEL_VINTAGE_MAINTENANCE,
    SUPERSESSION_LEDGER,
    UVI_DISPLAY_ROUNDING_RULE,
    UVI_EXAMPLES,
    UVI_NON_GOALS,
    UVI_REGISTER_ROWS,
    UVI_SOURCE_SECTIONS,
)


def _half_up(value: Decimal, places: str = "1") -> Decimal:
    return value.quantize(Decimal(places), rounding=ROUND_HALF_UP)


def _case(name: str) -> dict[str, object]:
    return UVI_EXAMPLES[name]


def _int(case: dict[str, object], key: str) -> int:
    value = case[key]
    assert isinstance(value, int)
    return value


def _text(case: dict[str, object], key: str) -> str:
    value = case[key]
    assert isinstance(value, str)
    return value


def test_complete_source_register_and_non_goal_surfaces() -> None:
    assert len(UVI_SOURCE_SECTIONS) == 20
    assert len(set(UVI_SOURCE_SECTIONS)) == 20
    assert tuple(row["csv_row"] for row in UVI_REGISTER_ROWS) == (
        4,
        11,
        17,
        21,
        29,
        30,
        35,
        43,
        45,
        50,
        51,
        117,
    )
    assert tuple(row["flag"] for row in UVI_REGISTER_ROWS).count("geprüft") == 3
    assert tuple(row["flag"] for row in UVI_REGISTER_ROWS).count("verify-before-production") == 9
    for row in UVI_REGISTER_ROWS:
        assert row["source"]
        assert row["basis"]
        assert row["nature"]
        assert row["rechtsstand"]
    assert len(UVI_NON_GOALS) == 11
    assert len(set(UVI_NON_GOALS)) == 11


def test_blocks_a_and_b_match_the_annex_examples() -> None:
    block_a = _case("emir_spec_block_a_kwh")
    movement = (
        Decimal(_int(block_a, "reading_end_x1000")) - Decimal(_int(block_a, "reading_start_x1000"))
    ) / Decimal(1000)
    assert movement == Decimal(_text(block_a, "movement_kwh"))
    assert _half_up(movement) == Decimal(_int(block_a, "result_kwh"))

    block_b = _case("emir_spec_block_b_previous_month")
    delta = _int(block_b, "current_kwh") - _int(block_b, "previous_kwh")
    percent = Decimal(delta) / Decimal(_int(block_b, "previous_kwh")) * 100
    assert delta == _int(block_b, "delta_kwh")
    assert _half_up(percent, "0.1") == Decimal(_text(block_b, "percent"))


def test_block_c_uses_monthly_degree_days_and_preserves_raw_fallback() -> None:
    block_c = _case("emir_spec_block_c_weather_adjusted")
    adjusted = (
        Decimal(_int(block_c, "previous_year_kwh"))
        * Decimal(_int(block_c, "degree_days_current"))
        / Decimal(_int(block_c, "degree_days_previous_year"))
    )
    delta = Decimal(_int(block_c, "current_kwh")) - adjusted
    source_percent = (
        Decimal(_int(block_c, "delta_kwh"))
        / Decimal(_int(block_c, "adjusted_previous_year_kwh"))
        * 100
    )
    assert adjusted == Decimal(_text(block_c, "adjusted_previous_year_unrounded_kwh"))
    assert _half_up(adjusted) == Decimal(_int(block_c, "adjusted_previous_year_kwh"))
    assert delta == Decimal(_text(block_c, "delta_unrounded_kwh"))
    assert _half_up(delta) == Decimal(_int(block_c, "delta_kwh"))
    assert _half_up(source_percent, "0.1") == Decimal(_text(block_c, "percent"))
    assert block_c["input_status"] == "arithmetic_fixture_not_authoritative_monthly_dwd_data"
    assert block_c["rounding_note"] == "round4_displayed_kwh_control_adjacent_percent"

    fallback = _case("approved_block_c_raw_weather_fallback")
    raw_delta = _int(fallback, "current_kwh") - _int(fallback, "previous_year_kwh")
    raw_percent = Decimal(raw_delta) / Decimal(_int(fallback, "previous_year_kwh")) * 100
    assert fallback["monthly_degree_days"] is None
    assert raw_delta == _int(fallback, "raw_delta_kwh")
    assert _half_up(raw_percent, "0.1") == Decimal(_text(fallback, "raw_percent"))
    assert fallback["label"] == "nicht witterungsbereinigt"
    assert fallback["implicit_factor_one"] is False


def test_block_d_normalizes_by_area_and_counts_target_in_three_valid_units() -> None:
    case = _case("emir_spec_block_d_building_cross_section")
    target = case["target"]
    comparables = case["comparables"]
    assert isinstance(target, dict)
    assert isinstance(comparables, tuple)
    assert _int(case, "valid_units_including_target") == 3
    assert _int(case, "minimum_valid_units_including_target") == 3
    intensities = tuple(
        Decimal(comparable["kwh"]) / Decimal(comparable["area_sqm"]) for comparable in comparables
    )
    average = sum(intensities, Decimal(0)) / Decimal(len(intensities))
    expected = average * Decimal(target["area_sqm"])
    delta = Decimal(target["kwh"]) - expected
    percent = delta / expected * 100
    assert average == Decimal(_text(case, "average_intensity_kwh_m2"))
    assert expected == Decimal(_int(case, "expected_kwh"))
    assert delta == Decimal(_int(case, "delta_kwh"))
    assert _half_up(percent, "0.1") == Decimal(_text(case, "percent"))


def test_corrected_d2_compares_heat_with_heat_and_reconciles_exactly() -> None:
    case = _case("approved_block_d2_heat_only")
    heat_only = _int(case, "heizspiegel_mittel_kwh_m2a") - _int(
        case, "warm_water_deduction_kwh_m2a"
    )
    annual = heat_only * _int(case, "area_sqm")
    monthly = Decimal(annual) * Decimal(_text(case, "degree_day_share"))
    delta = Decimal(_int(case, "current_heat_kwh")) - monthly
    percent = delta / monthly * 100
    assert heat_only == _int(case, "heat_only_kwh_m2a") == 90
    assert annual == _int(case, "norm_annual_kwh") == 7_200
    assert _half_up(monthly) == Decimal(_int(case, "norm_month_kwh")) == Decimal(1_368)
    assert _half_up(delta) == Decimal(_int(case, "delta_kwh")) == Decimal(132)
    assert _half_up(percent, "0.1") == Decimal(_text(case, "percent")) == Decimal("9.6")
    assert case["attribution"] == HEIZSPIEGEL_D2_CONTRACT["attribution"]
    old = SUPERSESSION_LEDGER["old_block_d2_result"]
    assert isinstance(old, dict)
    assert old["status"] == "history_only_replaced_by_approved_heat_only_example"


def test_hkv_provisional_and_linear_interpolation_conventions_are_exact() -> None:
    hkv = _case("approved_hkv_provisional")
    provisional = (
        Decimal(_int(hkv, "measured_rolling_building_heat_kwh"))
        * Decimal(_int(hkv, "unit_hkv_units"))
        / Decimal(_int(hkv, "building_hkv_units"))
    )
    assert provisional == Decimal(_int(hkv, "provisional_unit_kwh"))
    assert hkv["missing_building_total_result"] == "blocked"

    interpolation = _case("approved_linear_mid_month_interpolation")
    boundaries = interpolation["interpolated_boundaries"]
    assert isinstance(boundaries, tuple)
    assert Decimal(boundaries[1][1]) - Decimal(boundaries[0][1]) == Decimal(
        _int(interpolation, "february_consumption_kwh")
    )
    assert interpolation["method"] == "linear_by_elapsed_days"
    assert interpolation["provenance_required"] is True


def test_all_nine_annual_dwd_fixtures_and_import_guards_are_preserved() -> None:
    assert len(DWD_ANNUAL_CLIMATE_FACTOR_PLZ_FIXTURES) == 9
    assert DWD_ANNUAL_CLIMATE_FACTOR_PLZ_FIXTURES["01067"] == "1.14"
    assert DWD_ANNUAL_CLIMATE_FACTOR_PLZ_FIXTURES["04103"] == "1.15"
    assert DWD_ANNUAL_IMPORT_CONTRACT["csv_headers"] == ("DatAnf", "DatEnd", "PLZ", "KF")
    assert DWD_ANNUAL_IMPORT_CONTRACT["plz_1067_normalized"] == "01067"
    assert DWD_ANNUAL_IMPORT_CONTRACT["verified_record_count"] == 8_234
    assert DWD_ANNUAL_IMPORT_CONTRACT["minimum_record_count"] == 7_000
    assert Decimal(str(DWD_ANNUAL_IMPORT_CONTRACT["factor_minimum"])) == Decimal("0.40")
    assert Decimal(str(DWD_ANNUAL_IMPORT_CONTRACT["factor_maximum"])) == Decimal("1.80")
    assert DWD_ANNUAL_IMPORT_CONTRACT["reject_duplicate_plz"] is True
    assert DWD_ANNUAL_IMPORT_CONTRACT["second_import_same_file_changes_rows"] is False
    assert DWD_ANNUAL_IMPORT_CONTRACT["delete_old_periods"] is False
    assert DWD_ANNUAL_IMPORT_CONTRACT["direction"] == (
        "factor_above_one_increases_adjusted_consumption"
    )
    assert DWD_ANNUAL_IMPORT_CONTRACT["monthly_degree_day_dataset"] == "DWD_hdd_3807"
    assert DWD_ANNUAL_IMPORT_CONTRACT["station_to_plz_mapping"] == (
        "persisted_nearest_valid_station_convention"
    )
    assert DWD_ANNUAL_IMPORT_CONTRACT["monthly_uvi_status"] == (
        "specified; production blocked by unchosen PLZ geodataset and missing UVI register rows"
    )


def test_round4_monthly_degree_day_contract_is_complete_and_distinct_from_annual_DWD() -> None:
    assert DWD_MONTHLY_DEGREE_DAY_CONTRACT["source"] == "Antwort-an-Emir_04.md § 7.1"
    assert DWD_MONTHLY_DEGREE_DAY_CONTRACT["rechtsstand"] == "08/2026"
    assert str(DWD_MONTHLY_DEGREE_DAY_CONTRACT["path"]).endswith(
        "monthly/heating_degreedays/hdd_3807/"
    )
    assert DWD_MONTHLY_DEGREE_DAY_CONTRACT["recent_since"] == "2019-01-01"
    assert DWD_MONTHLY_DEGREE_DAY_CONTRACT["standard"] == "VDI 3807"
    assert DWD_MONTHLY_DEGREE_DAY_CONTRACT["heating_limit_celsius"] == 15
    assert DWD_MONTHLY_DEGREE_DAY_CONTRACT["reference_room_temperature_celsius"] == 20
    assert DWD_MONTHLY_DEGREE_DAY_CONTRACT["unit"] == "Kd"
    columns = DWD_MONTHLY_DEGREE_DAY_CONTRACT["columns"]
    assert isinstance(columns, tuple)
    assert columns == (
        "station_id",
        "latitude",
        "longitude",
        "station_name",
        "month_yyyymm",
        "valid_day_count",
        "monthly_degree_days",
        "heating_day_count",
        "ten_year_mean",
    )
    assert DWD_MONTHLY_DEGREE_DAY_CONTRACT["file_structure"] == "one_file_per_month"
    assert DWD_MONTHLY_DEGREE_DAY_CONTRACT["update_frequency"] == "monthly"
    assert DWD_MONTHLY_DEGREE_DAY_CONTRACT["attribution"] == "Quelle: Deutscher Wetterdienst"


def test_round4_station_assignment_is_persisted_auditable_and_keeps_PLZ_gap_open() -> None:
    assert DWD_STATION_ASSIGNMENT_CONTRACT["source"] == "Antwort-an-Emir_04.md § 7.1"
    assert DWD_STATION_ASSIGNMENT_CONTRACT["rechtsstand"] == "08/2026"
    steps = DWD_STATION_ASSIGNMENT_CONTRACT["steps"]
    assert isinstance(steps, tuple)
    assert len(steps) == 4
    assert DWD_STATION_ASSIGNMENT_CONTRACT["min_valid_days"] == 25
    assert DWD_STATION_ASSIGNMENT_CONTRACT["distance_label_threshold_km_exclusive"] == 50
    assert DWD_STATION_ASSIGNMENT_CONTRACT["same_station_in_both_compared_months"] is True
    assert DWD_STATION_ASSIGNMENT_CONTRACT["no_common_station"] == (
        "walk_next_nearest_fallback_chain"
    )
    assert DWD_STATION_ASSIGNMENT_CONTRACT["persistence_key"] == ("plz", "month")
    assert DWD_STATION_ASSIGNMENT_CONTRACT["persisted_fields"] == (
        "station_id",
        "distance_km",
    )
    assert DWD_STATION_ASSIGNMENT_CONTRACT["persist_never_recompute"] is True
    assert DWD_STATION_ASSIGNMENT_CONTRACT["coordinates_source"] == "DWD_file"
    assert DWD_STATION_ASSIGNMENT_CONTRACT["PLZ_geodataset"] is None
    assert DWD_STATION_ASSIGNMENT_CONTRACT["PLZ_geodataset_status"] == "UNSICHER_unselected"
    assert DWD_STATION_ASSIGNMENT_CONTRACT["nature"] == "Konvention"
    assert DWD_STATION_ASSIGNMENT_CONTRACT["flag"] == "verify-before-production"


def test_round4_display_rounding_rule_preserves_all_current_golden_values() -> None:
    assert UVI_DISPLAY_ROUNDING_RULE["source"] == "Antwort-an-Emir_04.md § 7.2"
    assert UVI_DISPLAY_ROUNDING_RULE["rechtsstand"] == "08/2026"
    assert UVI_DISPLAY_ROUNDING_RULE["nature"] == "Konvention"
    rows = UVI_DISPLAY_ROUNDING_RULE["block_reverification"]
    assert isinstance(rows, tuple)
    assert tuple(row["block"] for row in rows) == ("B", "C", "D", "D2")
    assert tuple(row["approved_percent"] for row in rows) == ("5.9", "-5.5", "-13.5", "9.6")
    assert UVI_DISPLAY_ROUNDING_RULE["only_divergent_block"] == "C"
    source_D2 = UVI_DISPLAY_ROUNDING_RULE["berkay_D2_verification_row"]
    assert isinstance(source_D2, dict)
    assert source_D2["figures"] == (1_733, 467, "27.0")
    assert source_D2["status"] == "superseded_heat_plus_hot_water_result_not_current"


def test_round4_heizspiegel_vintage_maintenance_prevents_retroactive_change() -> None:
    assert HEIZSPIEGEL_VINTAGE_MAINTENANCE["source"] == "Antwort-an-Emir_04.md § 7.3"
    assert HEIZSPIEGEL_VINTAGE_MAINTENANCE["rechtsstand"] == "08/2026"
    assert HEIZSPIEGEL_VINTAGE_MAINTENANCE["trigger"] == "yearly_on_01_October"
    steps = HEIZSPIEGEL_VINTAGE_MAINTENANCE["steps"]
    assert isinstance(steps, tuple)
    assert len(steps) == 6
    assert steps[-1] == "store_as_of_year_and_use_vintage_valid_at_UVI_month_M_never_newest"
    assert HEIZSPIEGEL_VINTAGE_MAINTENANCE["JAZ_assumption"] == 3
    assert HEIZSPIEGEL_VINTAGE_MAINTENANCE["negative_guard_scope"] == (
        "every_energy_source_x_size_class"
    )
    assert HEIZSPIEGEL_VINTAGE_MAINTENANCE["negative_guard_hit"] == ("stop_import_do_not_render")
    assert HEIZSPIEGEL_VINTAGE_MAINTENANCE["source_and_values_owner"] == "Berkay"
    assert HEIZSPIEGEL_VINTAGE_MAINTENANCE["import_guard_and_test_owner"] == "Emir"
    assert HEIZSPIEGEL_VINTAGE_MAINTENANCE["delivered_UVI_changes_retroactively"] is False
    assert HEIZSPIEGEL_VINTAGE_MAINTENANCE["vintage_binding"] == ("UVI_record_not_retrieval_time")
    assert HEIZSPIEGEL_VINTAGE_MAINTENANCE["heat_pump_8_kwh_status"] == (
        "unconfirmed_verify-before-production_convention"
    )


def test_latest_state_supersedes_the_stale_april_snapshot() -> None:
    assert DWD_LATEST_STATE["latest_verified_file"] == "KF_20250601_20260531"
    assert DWD_LATEST_STATE["latest_verified_period"] == ("2025-06-01", "2026-05-31")
    assert DWD_LATEST_STATE["latest_verified_published"] == "2026-07-15"
    assert DWD_LATEST_STATE["disposition"] == (
        "may_2026_end_date_supersedes_stale_april_2026_headline"
    )


def test_all_18_heizspiegel_rows_deductions_guards_fallback_and_attribution() -> None:
    assert len(HEIZSPIEGEL_2025_ROWS) == 18
    assert len({(row["size"], row["energy"]) for row in HEIZSPIEGEL_2025_ROWS}) == 18
    for row in HEIZSPIEGEL_2025_ROWS:
        bands = (row["low"], row["middle"], row["high"], row["too_high"])
        assert all(isinstance(value, int) for value in bands)
        low, middle, high, too_high = bands
        assert isinstance(low, int)
        assert isinstance(middle, int)
        assert isinstance(high, int)
        assert isinstance(too_high, int)
        assert low < middle < high < too_high

    deductions = HEIZSPIEGEL_D2_CONTRACT["deductions"]
    assert isinstance(deductions, dict)
    assert deductions == {
        "Erdgas": 24,
        "Heizoel": 24,
        "Fernwaerme": 24,
        "Holzpellets": 24,
        "Waermepumpe": 8,
    }
    for row in HEIZSPIEGEL_2025_ROWS:
        middle = row["middle"]
        deduction = deductions[str(row["energy"])]
        assert isinstance(middle, int)
        assert isinstance(deduction, int)
        heat_only = middle - deduction
        assert heat_only > 0
    assert HEIZSPIEGEL_D2_CONTRACT["non_positive_heat_only_result"] == (
        "block_with_data_quality_flag"
    )
    assert HEIZSPIEGEL_D2_CONTRACT["missing_over_500"] == (
        "Waermepumpe",
        "Holzpellets",
    )
    assert HEIZSPIEGEL_D2_CONTRACT["missing_over_500_fallback"] == "250-500"
    assert "250–500" in str(HEIZSPIEGEL_D2_CONTRACT["fallback_label"])
    assert HEIZSPIEGEL_D2_CONTRACT["attribution"] == ("Quelle: co2online gGmbH (Heizspiegel)")
    assert HEIZSPIEGEL_D2_CONTRACT["appropriateness_verdict"] is False


def test_identity_money_and_threshold_conflicts_are_explicitly_superseded() -> None:
    assert SUPERSESSION_LEDGER["uvi_renter_membership_role"] == (
        "renter_is_person_tenancy_context_never_membership_role"
    )
    assert SUPERSESSION_LEDGER["uvi_money_largest_remainder"] == (
        "no_uvi_money_allocation_heating_money_remains_docs_03"
    )
    assert SUPERSESSION_LEDGER["block_d_threshold_other_units"] == (
        "three_valid_units_including_target"
    )
    assert SUPERSESSION_LEDGER["dwd_minimum_0_50"] == ("replaced_by_0_40_after_observed_0_49")
    assert SUPERSESSION_LEDGER["monthly_DWD_dataset_missing"] == ("resolved_by_round4_DWD_hdd_3807")
    assert SUPERSESSION_LEDGER["block_C_rounding_order"] == (
        "resolved_by_round4_displayed_values_win"
    )
