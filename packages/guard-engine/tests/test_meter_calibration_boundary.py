from datetime import date

from lokara_guard_engine import (
    GuardSourceIdentity,
    MeterCalibrationInput,
    MeterCalibrationRuleBundle,
    RuleEvidence,
    evaluate_meter_calibration,
)


def test_eichfrist_boundary_day_is_still_in_expiry_month_not_exceeded() -> None:
    rules = MeterCalibrationRuleBundle(
        evidence=(RuleEvidence("test", "W2", "MessEV", "08/2026", "verify-before-production"),),
        unresolved_conflicts=(),
        years_by_medium={"warm_water": 6},
        legacy_years_by_medium={"warm_water": 5},
        medium_labels_de={"warm_water": "Warmwasser"},
        excluded_media=(),
        expiry_month=12,
        expiry_day=31,
        warning_de="{boundary_date}",
        channels_by_stage={},
        resolution_event="test",
    )
    result = evaluate_meter_calibration(
        MeterCalibrationInput(
            GuardSourceIdentity("meter", "m-1"),
            date(2026, 12, 31),
            date(2020, 6, 15),
            "warm_water",
            "WW",
        ),
        rules,
    )
    assert result.stage == "expiry_month"
    assert result.boundary_date == date(2026, 12, 31)
