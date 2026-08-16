"""Cent-exact oracles transcribed from Berkay Page 01b and later Antworten.

This module is data only.  It deliberately does not import the implementation, so an
implementer cannot make an oracle pass by deriving the expected value from the code under test.
Money is integer cents.  ``renter_totals`` plus ``owner_total`` always reconciles to
``billable_total`` where a party allocation exists.

Source precedence applied here:

* Antwort 03 § 6 replaces Page 01b R4/E3 and therefore re-expects F05.
* Antwort 03 § 4 conflicts with the current Rechtsstand CSV on the Erdgas Hu/Ho values.
  No value-dependent mass-fallback oracle is added for that unresolved pair.
* F31's two Cologne climate factors are placeholders.  Only its structural assertions and
  the real DWD import values are test oracles.
"""

from typing import Final

Golden = dict[str, object]

PAGE_01B_GOLDENS: Final[dict[str, Golden]] = {
    "01b-F01": {
        "plant_total": 350_600,
        "co2_landlord": 12_382,
        "billable_total": 338_218,
        "renter_totals": (127_217, 74_508, 34_782, 98_426),
        "owner_total": 3_285,
    },
    "01b-F02": {
        "blocked_by": "erdgas_hu_ho_register_conflict",
        "warning": "supplier_co2_missing",
        "missing_supplier_cost": "refuse_without_factor_lookup",
    },
    "01b-F03": {
        "intensity": "12.0",
        "landlord_percent": 10,
        "co2_landlord": 1_280,
        "billable_total": 349_320,
    },
    "01b-F04": {
        "intensity": "52.0",
        "landlord_percent": 95,
        "co2_landlord": 52_710,
        "billable_total": 297_890,
    },
    "01b-F05": {
        "intensity": "12.0",
        "landlord_percent": 10,
        "co2_landlord": 1_280,
        "billable_total": 349_320,
    },
    "01b-F06": {
        "period_days": 275,
        "intensity": "28.7",
        "landlord_percent": 40,
        "co2_landlord": 9_240,
        "billable_total": 341_360,
    },
    "01b-F07": {
        "energy_source": "erdgas",
        "building_type": "nichtwohn",
        "connected_plant": True,
        "landlord_percent": 50,
        "co2_landlord": 15_477,
        "billable_total": 335_123,
    },
    "01b-F08": {
        "protection_kinds": ("denkmalschutz", "milieuschutz"),
        "landlord_percent": 20,
        "co2_landlord": 6_191,
        "billable_total": 344_409,
        "proof_required": True,
    },
    "01b-F09": {
        "full_exclusion": True,
        "landlord_percent": 0,
        "co2_landlord": 0,
        "billable_total": 350_600,
        "proof_required": True,
    },
    "01b-F10": {
        "energy_sources": ("waermepumpe", "biomasse"),
        "co2_module": "off",
        "co2_landlord": 0,
        "billable_total": 350_600,
        "disclosure": False,
    },
    "01b-F11": {
        "q_ww_kwh": "9100.000",
        "billable_total": 338_218,
        "renter_totals": (126_917, 74_739, 34_910, 98_365),
        "owner_total": 3_287,
    },
    "01b-F12": {
        "q_ww_kwh": "6208.000",
        "billable_total": 338_218,
        "renter_totals": (125_584, 75_769, 35_486, 98_092),
        "owner_total": 3_287,
        "warning": "ww_area_fallback",
    },
    "01b-F13": {
        "connected_plant": False,
        "billable_total": 338_218,
        "renter_totals": (122_723, 77_979, 36_721, 97_507),
        "owner_total": 3_288,
    },
    "01b-F14": {
        "base_percent": 50,
        "billable_total": 338_218,
        "renter_totals": (121_752, 74_628, 37_165, 99_195),
        "owner_total": 5_478,
    },
    "01b-F15": {
        "heat_meter_kwh": (9_000, 5_250, 2_250, 5_000),
        "billable_total": 338_218,
        "renter_totals": (132_959, 76_015, 35_428, 90_531),
        "owner_total": 3_285,
    },
    "01b-F16": {
        "degree_day_units": ("2147.8", "1404.0", "48.2"),
        "billable_total": 338_218,
        "renter_totals": (127_217, 69_165, 39_433, 98_426),
        "owner_total": 3_977,
    },
    "01b-F17": {
        "estimated_units": "620.0",
        "affected_area_percent": "9.28",
        "renter_example": 98_426,
        "provenance_required": True,
    },
    "01b-F18": {
        "missing_unit_ids": ("WE-03",),
        "affected_area_sqm": "58",
        "building_area_sqm": "194",
        "affected_area_percent": "29.90",
        "distribution": "area_only",
        "billable_total": 338_218,
        "renter_totals": (108_090, 74_932, 43_121, 101_117),
        "owner_total": 10_958,
    },
    "01b-F19": {
        "consumed_litres": "5600",
        "fuel_cost": 545_018,
        "closing_stock": 204_382,
        "co2_grams": 14_896_000,
        "landlord_percent": 50,
        "co2_cost_fallback": "refuse",
    },
    "01b-F20": {
        "plant_total": 438_600,
        "intensity": "25.1",
        "landlord_percent": 30,
        "co2_landlord": 8_040,
        "billable_total": 430_560,
        "closure": "partial_until_h1_aggregation_and_section_6a_disclosure",
    },
    "01b-F21": {"error": "zero_consumption_denominator", "sample_risk_15_percent": 19_083},
    "01b-F22": {
        "rejected_delta": "-1460.0",
        "replacement_segments": ("420.0", "1040.0"),
        "replacement_total": "1460.0",
    },
    "01b-F23": {
        "high_intensity": "74.7",
        "low_intensity": "4.1",
        "warning_only": True,
    },
    "01b-F24": {
        "invoice_days": 365,
        "overlap_days": 304,
        "allocated_cost": 299_836,
        "coverage_percent": "83.29",
        "missing_days": 61,
    },
    "01b-F25": {
        "base_heating_cost": 127_217,
        "risk_3_percent": 3_817,
        "risk_15_percent": 19_083,
        "auto_deduct": False,
    },
    "01b-F26": {
        "central_m3": "78",
        "unit_m3": "74",
        "gap_percent": "5.13",
        "signal": "none",
        "unmetered_owner": 4_227,
    },
    "01b-F26b": {"central_m3": "78", "unit_m3": "69", "gap_percent": "11.54", "signal": "notice"},
    "01b-F26c": {"central_m3": "78", "unit_m3": "61", "gap_percent": "21.79", "signal": "warning"},
    "01b-F27": {
        "unit_totals": ("4100.0", "2520.0", "1080.0", "3050.0"),
        "plant_total_units": "10750.0",
        "device_rounding_dp": 1,
    },
    "01b-F28a": {
        "branch": "mdl_net",
        "billable_total": 338_218,
        "renter_totals": (127_217, 74_508, 34_782, 98_426),
        "owner_total": 3_285,
        "second_co2_deduction": 0,
    },
    "01b-F28b": {
        "branch": "mdl_gross",
        "gross_total": 350_600,
        "gross_positions_total": 350_599,
        "gross_tolerance": 5,
        "billable_total": 338_218,
        "renter_totals": (127_217, 74_508, 34_782, 98_426),
        "owner_total": 3_285,
    },
    "01b-F29": {
        "branch": "mdl_net",
        "control_total": 338_218,
        "ocr_positions_total": 306_914,
        "difference": 31_304,
        "blocked": True,
    },
    "01b-F30": {
        "heating_costs": (127_217, 74_508, 34_782, 98_426),
        "risk_3_percent": (3_817, 2_235, 1_043, 2_953),
        "risk_total": 10_048,
        "auto_deduct": False,
    },
    "01b-F31": {
        "comparison_kind": "heat_adjusted_ww_raw",
        "missing_factor_fallback": "raw_labelled",
        "missing_prior_period": "note_no_graph",
        "graph_required": True,
        "placeholder_values_forbidden": True,
    },
}
