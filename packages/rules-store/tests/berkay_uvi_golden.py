"""Data-only oracle for the UVI, DWD, and Heizspiegel transcription.

The map names its sources and cases instead of inventing a ``16-Fxx`` namespace.
It imports no production code and does not claim that a UVI engine or importer exists.
"""

from typing import Final

UVI_EXAMPLES: Final[dict[str, dict[str, object]]] = {
    "emir_spec_block_a_kwh": {
        "reading_start_x1000": 12_340_000,
        "reading_end_x1000": 13_240_000,
        "measurement_unit": "KWH",
        "movement_kwh": "900",
        "result_kwh": 900,
    },
    "emir_spec_block_b_previous_month": {
        "current_kwh": 900,
        "previous_kwh": 850,
        "delta_kwh": 50,
        "percent": "5.9",
    },
    "emir_spec_block_c_weather_adjusted": {
        "current_kwh": 900,
        "previous_year_kwh": 1_000,
        "degree_days_current": 590,
        "degree_days_previous_year": 620,
        "adjusted_previous_year_unrounded_kwh": "951.6129032258064516129032258",
        "adjusted_previous_year_kwh": 952,
        "delta_unrounded_kwh": "-51.6129032258064516129032258",
        "delta_kwh": -52,
        "percent": "-5.5",
        "input_status": "arithmetic_fixture_not_authoritative_monthly_dwd_data",
        "rounding_note": "source_example_percent_uses_rounded_display_values",
    },
    "emir_spec_block_d_building_cross_section": {
        "target": {"area_sqm": 80, "kwh": 900},
        "comparables": (
            {"area_sqm": 100, "kwh": 1_300},
            {"area_sqm": 120, "kwh": 1_560},
        ),
        "valid_units_including_target": 3,
        "minimum_valid_units_including_target": 3,
        "average_intensity_kwh_m2": "13.0",
        "expected_kwh": 1_040,
        "delta_kwh": -140,
        "percent": "-13.5",
    },
    "approved_block_d2_heat_only": {
        "energy_source": "Erdgas",
        "size_class": "250-500",
        "heizspiegel_mittel_kwh_m2a": 114,
        "warm_water_deduction_kwh_m2a": 24,
        "heat_only_kwh_m2a": 90,
        "area_sqm": 80,
        "degree_day_share": "0.19",
        "norm_annual_kwh": 7_200,
        "norm_month_kwh": 1_368,
        "current_heat_kwh": 1_500,
        "delta_kwh": 132,
        "percent": "9.6",
        "label": "normierter, gebäudebezogener Richtwert",
        "attribution": "Quelle: co2online gGmbH (Heizspiegel)",
    },
    "approved_hkv_provisional": {
        "measured_rolling_building_heat_kwh": 10_000,
        "unit_hkv_units": 300,
        "building_hkv_units": 1_000,
        "provisional_unit_kwh": 3_000,
        "label": "provisorisch, Endwert erst zur Jahresabrechnung",
        "missing_building_total_result": "blocked",
    },
    "approved_block_c_raw_weather_fallback": {
        "current_kwh": 900,
        "previous_year_kwh": 1_000,
        "monthly_degree_days": None,
        "raw_delta_kwh": -100,
        "raw_percent": "-10.0",
        "label": "nicht witterungsbereinigt",
        "implicit_factor_one": False,
    },
    "approved_linear_mid_month_interpolation": {
        "readings": (
            ("2025-01-15", "1000"),
            ("2025-02-15", "1310"),
            ("2025-03-15", "1590"),
        ),
        "interpolated_boundaries": (("2025-02-01", "1170"), ("2025-03-01", "1450")),
        "february_consumption_kwh": 280,
        "method": "linear_by_elapsed_days",
        "provenance_required": True,
    },
}


DWD_ANNUAL_CLIMATE_FACTOR_PLZ_FIXTURES: Final[dict[str, str]] = {
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


DWD_ANNUAL_IMPORT_CONTRACT: Final[dict[str, object]] = {
    "dataset": "DWD CDC v22.3 climate_correction_factor",
    "calendar_year_file": "KF_20250101_20251231.csv",
    "verified_record_count": 8_234,
    "minimum_record_count": 7_000,
    "delimiter": ";",
    "encoding": "ASCII",
    "csv_headers": ("DatAnf", "DatEnd", "PLZ", "KF"),
    "xml_headers": ("VON_DATUM", "BIS_DATUM", "KLFK_POLZ", "KLIMAFAKTOR"),
    "decimal_separator": ".",
    "postal_code_width": 5,
    "plz_1067_normalized": "01067",
    "factor_minimum": "0.40",
    "factor_maximum": "1.80",
    "observed_minimum": "0.49",
    "observed_maximum": "1.33",
    "reject_duplicate_plz": True,
    "idempotency_key": ("plz", "period_from", "period_to"),
    "second_import_same_file_changes_rows": False,
    "delete_old_periods": False,
    "direction": "factor_above_one_increases_adjusted_consumption",
    "missing_plz": "raw_labelled_comparison_never_implicit_one",
    "attribution": "Quelle: Deutscher Wetterdienst",
    "monthly_degree_day_dataset": None,
    "station_to_plz_mapping": None,
    "monthly_uvi_status": "verify-before-production",
}


DWD_LATEST_STATE: Final[dict[str, object]] = {
    "earlier_snapshot_file": "KF_20250501_20260430_k.csv",
    "earlier_snapshot_published": "2026-06-15",
    "latest_verified_file": "KF_20250601_20260531",
    "latest_verified_period": ("2025-06-01", "2026-05-31"),
    "latest_verified_published": "2026-07-15",
    "verified_on": "2026-08-13",
    "disposition": "may_2026_end_date_supersedes_stale_april_2026_headline",
}


HEIZSPIEGEL_2025_ROWS: Final[tuple[dict[str, object], ...]] = (
    {"size": "80-150", "energy": "Erdgas", "low": 62, "middle": 121, "high": 207, "too_high": 208},
    {
        "size": "80-150",
        "energy": "Heizoel",
        "low": 100,
        "middle": 165,
        "high": 263,
        "too_high": 264,
    },
    {
        "size": "80-150",
        "energy": "Fernwaerme",
        "low": 38,
        "middle": 89,
        "high": 191,
        "too_high": 192,
    },
    {
        "size": "80-150",
        "energy": "Waermepumpe",
        "low": 20,
        "middle": 36,
        "high": 82,
        "too_high": 83,
    },
    {
        "size": "80-150",
        "energy": "Holzpellets",
        "low": 74,
        "middle": 148,
        "high": 249,
        "too_high": 250,
    },
    {"size": "150-250", "energy": "Erdgas", "low": 64, "middle": 116, "high": 187, "too_high": 188},
    {
        "size": "150-250",
        "energy": "Heizoel",
        "low": 92,
        "middle": 142,
        "high": 220,
        "too_high": 221,
    },
    {
        "size": "150-250",
        "energy": "Fernwaerme",
        "low": 41,
        "middle": 94,
        "high": 169,
        "too_high": 170,
    },
    {
        "size": "150-250",
        "energy": "Waermepumpe",
        "low": 18,
        "middle": 33,
        "high": 77,
        "too_high": 78,
    },
    {
        "size": "150-250",
        "energy": "Holzpellets",
        "low": 72,
        "middle": 126,
        "high": 219,
        "too_high": 220,
    },
    {"size": "250-500", "energy": "Erdgas", "low": 61, "middle": 114, "high": 185, "too_high": 186},
    {
        "size": "250-500",
        "energy": "Heizoel",
        "low": 78,
        "middle": 123,
        "high": 197,
        "too_high": 198,
    },
    {
        "size": "250-500",
        "energy": "Fernwaerme",
        "low": 36,
        "middle": 112,
        "high": 203,
        "too_high": 204,
    },
    {
        "size": "250-500",
        "energy": "Waermepumpe",
        "low": 17,
        "middle": 30,
        "high": 69,
        "too_high": 70,
    },
    {
        "size": "250-500",
        "energy": "Holzpellets",
        "low": 60,
        "middle": 113,
        "high": 196,
        "too_high": 197,
    },
    {
        "size": "ueber-500",
        "energy": "Erdgas",
        "low": 59,
        "middle": 115,
        "high": 177,
        "too_high": 178,
    },
    {
        "size": "ueber-500",
        "energy": "Heizoel",
        "low": 68,
        "middle": 127,
        "high": 198,
        "too_high": 199,
    },
    {
        "size": "ueber-500",
        "energy": "Fernwaerme",
        "low": 46,
        "middle": 87,
        "high": 144,
        "too_high": 145,
    },
)


HEIZSPIEGEL_D2_CONTRACT: Final[dict[str, object]] = {
    "year": 2025,
    "billing_year": 2024,
    "as_of": "09/2025",
    "unit": "kWh/(m2*a)",
    "source_includes": "space_heat_plus_hot_water",
    "comparison_quantity": "space_heat_only",
    "deductions": {
        "Erdgas": 24,
        "Heizoel": 24,
        "Fernwaerme": 24,
        "Holzpellets": 24,
        "Waermepumpe": 8,
    },
    "heat_pump_deduction_status": "verify-before-production_convention",
    "non_positive_heat_only_result": "block_with_data_quality_flag",
    "missing_over_500": ("Waermepumpe", "Holzpellets"),
    "missing_over_500_fallback": "250-500",
    "fallback_label": (
        "Vergleichswert der Größenklasse 250–500 m²; für über 500 m² liegt für diesen "
        "Energieträger noch kein Wert vor"
    ),
    "output_label": "normierter, gebäudebezogener Richtwert",
    "attribution": "Quelle: co2online gGmbH (Heizspiegel)",
    "appropriateness_verdict": False,
}


UVI_REGISTER_ROWS: Final[tuple[dict[str, object], ...]] = (
    {
        "csv_row": 4,
        "name": "UVI-Turnus",
        "value": "monatlich ab 01.01.2022 — nur wenn fernablesbare Ausstattung vorhanden",
        "flag": "geprüft",
        "source": "gesetze-im-internet.de/heizkostenv/__6a.html",
        "basis": "§ 6a Abs. 1 Nr. 2 HeizkostenV",
        "nature": "Verordnung",
        "rechtsstand": "07/2026",
    },
    {
        "csv_row": 11,
        "name": "Vermutungswirkung Witterungsbereinigung",
        "value": "Bekanntmachung von BMWi + BMI im Bundesanzeiger — EXISTENZ NICHT VERIFIZIERT",
        "flag": "verify-before-production",
        "source": "gesetze-im-internet.de/heizkostenv/__6a.html",
        "basis": "§ 6a Abs. 3 S. 4 HeizkostenV",
        "nature": "Verordnung",
        "rechtsstand": "07/2026",
    },
    {
        "csv_row": 17,
        "name": "Kürzungsrecht — fehlende fernablesbare Ausstattung",
        "value": "3 %",
        "flag": "verify-before-production",
        "source": "gesetze-im-internet.de/heizkostenv/__12.html",
        "basis": "§ 12 Abs. 1 S. 2 HeizkostenV",
        "nature": "Verordnung",
        "rechtsstand": "07/2026",
    },
    {
        "csv_row": 21,
        "name": "Durchschnittsnutzer-Vergleichswerte (K13)",
        "value": (
            "Heizspiegel co2online; commercial use only with permission; annual-statement "
            "online-reference wording is superseded for monthly UVI"
        ),
        "flag": "verify-before-production",
        "source": "heizspiegel.de/heizkosten-pruefen/methodik-heizspiegel",
        "basis": "§ 6a Abs. 2 Nr. 3, Abs. 3 S. 1 Nr. 4 HeizkostenV",
        "nature": "Konvention",
        "rechtsstand": "07/2026",
    },
    {
        "csv_row": 29,
        "name": "§ 6a Abs. 3 — Pflichtinformationen zur Abrechnung",
        "value": (
            "energy mix, THG, primary-energy factor, taxes and fees, equipment/readout/billing "
            "costs, contacts, dispute notice, average-user comparison, graphical "
            "weather-adjusted prior-year comparison"
        ),
        "flag": "geprüft",
        "source": "gesetze-im-internet.de/heizkostenv/__6a.html",
        "basis": "§ 6a Abs. 3 S. 1 Nr. 1–5 HeizkostenV",
        "nature": "Verordnung",
        "rechtsstand": "07/2026",
    },
    {
        "csv_row": 30,
        "name": "Nachrüstfrist fernablesbare Ausstattung",
        "value": "31.12.2026",
        "flag": "geprüft",
        "source": "gesetze-im-internet.de/heizkostenv/BJNR002610981.html",
        "basis": "§ 5 Abs. 2 HeizkostenV",
        "nature": "Verordnung",
        "rechtsstand": "07/2026",
    },
    {
        "csv_row": 35,
        "name": "Klimafaktoren DWD (K12)",
        "value": (
            "KF = degree days TRY Potsdam / location; about 8200 PLZ; rolling 12-month periods; "
            "about six-week delay; GeoNutzV attribution"
        ),
        "flag": "verify-before-production",
        "source": "dwd.de/DE/leistungen/klimafaktoren/klimafaktoren.html",
        "basis": "§ 6a Abs. 3 S. 3 HeizkostenV i. V. m. § 82 Abs. 3 GEG",
        "nature": "Konvention",
        "rechtsstand": "07/2026",
    },
    {
        "csv_row": 43,
        "name": "Kürzungsrecht — fehlende oder unvollständige § 6a-Information",
        "value": "3 %",
        "flag": "verify-before-production",
        "source": "gesetze-im-internet.de/heizkostenv/__12.html",
        "basis": "§ 12 Abs. 1 S. 3 i. V. m. § 6a HeizkostenV",
        "nature": "Verordnung",
        "rechtsstand": "07/2026",
    },
    {
        "csv_row": 45,
        "name": "Verbrauchsvergleich — Umfang und Bereinigung",
        "value": "heat and hot water; weather-adjust heat only and show hot water unadjusted",
        "flag": "verify-before-production",
        "source": "gesetze-im-internet.de/heizkostenv/__6a.html",
        "basis": "§ 6a Abs. 3 S. 2–3 HeizkostenV",
        "nature": "Verordnung",
        "rechtsstand": "07/2026",
    },
    {
        "csv_row": 50,
        "name": "Umlagefähige Betriebskosten der Heizanlage",
        "value": (
            "closed § 7(2) catalogue including calculation, allocation and § 6a information "
            "costs; § 8(2) water additions"
        ),
        "flag": "verify-before-production",
        "source": "gesetze-im-internet.de/heizkostenv/__7.html",
        "basis": "§ 7 Abs. 2; § 8 Abs. 2; § 7 Abs. 4; § 8 Abs. 4 HeizkostenV",
        "nature": "Verordnung",
        "rechtsstand": "07/2026",
    },
    {
        "csv_row": 51,
        "name": "Informationspflichten bei nicht verbrauchsbasierter Abrechnung",
        "value": "only § 6a Abs. 3 Nr. 2 and 3 when not based on consumption or readings",
        "flag": "verify-before-production",
        "source": "gesetze-im-internet.de/heizkostenv/__6a.html",
        "basis": "§ 6a Abs. 5 HeizkostenV",
        "nature": "Verordnung",
        "rechtsstand": "07/2026",
    },
    {
        "csv_row": 117,
        "name": "W4 · UVI-Fälligkeit Monatsende (KONVENTION-D3)",
        "value": "",
        "flag": "verify-before-production",
        "source": "gesetze-im-internet.de/heizkostenv/__6a.html",
        "basis": (
            "§ 6a Abs. 1 Nr. 2 — month end uncertain; year-round versus heating season uncertain"
        ),
        "nature": "Konvention",
        "rechtsstand": "10/2023",
    },
)


UVI_SOURCE_SECTIONS: Final[tuple[str, ...]] = (
    "Emir_Spec_UVI_metadata_and_document_map",
    "Emir_Spec_UVI_0_done",
    "Emir_Spec_UVI_1_data_and_cadence",
    "Emir_Spec_UVI_2_ingestion",
    "Emir_Spec_UVI_3_weather_source",
    "Emir_Spec_UVI_4_blocks_a_b_c_d_d2_and_legal_content",
    "Emir_Spec_UVI_5_renter_surface",
    "Emir_Spec_UVI_6_delivery",
    "Emir_Spec_UVI_7_correctness_gates",
    "Emir_Spec_UVI_8_build_sequence",
    "Emir_Spec_UVI_9_decisions",
    "DWD_import_spec_1_through_7",
    "DWD_latest_state_complete",
    "Heizspiegel_2025_all_18_data_rows",
    "Page_01b_H8_F31_and_out_of_scope",
    "Page_05_W4",
    "Non_Goals_V1_Page_01b_all_11_rows",
    "README_for_Emir_complete_relevant_audit",
    "Rechtsstand_register_12_rows",
    "historical_disposition_docs_03_appendix_d",
)


UVI_NON_GOALS: Final[tuple[str, ...]] = (
    "recalculate_or_override_mdl_statement_inputs",
    "floor_heating_co2_reimbursement_calculator",
    "non_residential_beyond_current_50_50_co2_split",
    "renovation_or_amortization_calculator",
    "arge_3_10_and_bved_webservices_are_deferred_in_dated_non_goals",
    "ocr_model_prompt_and_confidence_internals",
    "automatic_application_of_reduction_rights",
    "device_installation_calibration_or_k_value_audit",
    "document_inspection_workflow_showing_other_renters_consumption",
    "proprietary_average_user_values_from_lokara_data",
    "co2_price_table_fallback_from_2026",
)


SUPERSESSION_LEDGER: Final[dict[str, object]] = {
    "dwd_minimum_0_50": "replaced_by_0_40_after_observed_0_49",
    "latest_state_april_2026_end": "replaced_by_verified_may_2026_end_file",
    "uvi_renter_membership_role": "renter_is_person_tenancy_context_never_membership_role",
    "uvi_money_largest_remainder": "no_uvi_money_allocation_heating_money_remains_docs_03",
    "block_d_threshold_other_units": "three_valid_units_including_target",
    "block_d2_heat_plus_hot_water": "heat_only_after_source_specific_warm_water_deduction",
    "old_block_d2_result": {
        "norm_month_kwh": 1_733,
        "delta_kwh": 467,
        "percent": "27.0",
        "status": "history_only_replaced_by_approved_heat_only_example",
    },
    "missing_over_500_omit_or_extrapolate": "use_250_500_with_visible_label",
}
