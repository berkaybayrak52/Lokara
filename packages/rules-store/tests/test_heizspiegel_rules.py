"""U2 golden contract for the versioned Heizspiegel rules data.

Source: ``docs/16-uvi.md`` section 8.2 and the source-named
``HEIZSPIEGEL_2025_ROWS`` / ``HEIZSPIEGEL_D2_CONTRACT`` oracles.  The values are
restated here deliberately: this executable fixture must not depend on the
data-only transcription it is meant to carry into production.
"""

from dataclasses import FrozenInstanceError, replace
from datetime import date
from decimal import Decimal
from importlib import import_module
from types import ModuleType
from typing import Any, cast

import pytest
from lokara_domain import RuleEvidence
from lokara_rules_store import RuleNotFoundError, RuleSet, RuleVersion, get_rule
from lokara_uvi_engine import ResolvedHeizspiegelRow

EXPECTED_ROWS = (
    ("80-150", "Erdgas", 62, 121, 207, 208),
    ("80-150", "Heizoel", 100, 165, 263, 264),
    ("80-150", "Fernwaerme", 38, 89, 191, 192),
    ("80-150", "Waermepumpe", 20, 36, 82, 83),
    ("80-150", "Holzpellets", 74, 148, 249, 250),
    ("150-250", "Erdgas", 64, 116, 187, 188),
    ("150-250", "Heizoel", 92, 142, 220, 221),
    ("150-250", "Fernwaerme", 41, 94, 169, 170),
    ("150-250", "Waermepumpe", 18, 33, 77, 78),
    ("150-250", "Holzpellets", 72, 126, 219, 220),
    ("250-500", "Erdgas", 61, 114, 185, 186),
    ("250-500", "Heizoel", 78, 123, 197, 198),
    ("250-500", "Fernwaerme", 36, 112, 203, 204),
    ("250-500", "Waermepumpe", 17, 30, 69, 70),
    ("250-500", "Holzpellets", 60, 113, 196, 197),
    ("ueber-500", "Erdgas", 59, 115, 177, 178),
    ("ueber-500", "Heizoel", 68, 127, 198, 199),
    ("ueber-500", "Fernwaerme", 46, 87, 144, 145),
)

EXPECTED_DEDUCTIONS = {
    "Erdgas": 24,
    "Heizoel": 24,
    "Fernwaerme": 24,
    "Holzpellets": 24,
    "Waermepumpe": 8,
}

EXPECTED_ATTRIBUTION = "Quelle: co2online gGmbH (Heizspiegel)"
EXPECTED_FALLBACK_LABEL = (
    "Vergleichswert der Größenklasse 250–500 m²; für über 500 m² liegt für diesen "
    "Energieträger noch kein Wert vor"
)


@pytest.fixture(scope="module")
def heizspiegel() -> ModuleType:
    try:
        return import_module("lokara_rules_store.rules.heizspiegel")
    except ModuleNotFoundError:
        pytest.fail(
            "U2 production module lokara_rules_store.rules.heizspiegel is missing",
            pytrace=False,
        )


def _resolved_vintage(heizspiegel: ModuleType) -> Any:
    return get_rule(heizspiegel.HEIZSPIEGEL_RULES, date(2025, 10, 1)).value


def _resolve(
    heizspiegel: ModuleType,
    energy_source: str,
    requested_size_class: str,
    *,
    rule_set: object | None = None,
    as_of: date = date(2025, 10, 1),
) -> ResolvedHeizspiegelRow:
    selected_rule_set = heizspiegel.HEIZSPIEGEL_RULES if rule_set is None else rule_set
    return cast(
        ResolvedHeizspiegelRow,
        heizspiegel.resolve_heizspiegel_row(
            selected_rule_set,
            as_of=as_of,
            energy_source=energy_source,
            requested_size_class=requested_size_class,
        ),
    )


def test_2025_vintage_contains_all_18_source_rows_exactly(heizspiegel: ModuleType) -> None:
    vintage = _resolved_vintage(heizspiegel)
    actual = tuple(
        (
            row.size_class,
            row.energy_source,
            row.low_kwh_m2a,
            row.middle_kwh_m2a,
            row.high_kwh_m2a,
            row.too_high_from_kwh_m2a,
        )
        for row in vintage.rows
    )

    assert actual == EXPECTED_ROWS
    assert tuple(dict.fromkeys(row[0] for row in actual)) == (
        "80-150",
        "150-250",
        "250-500",
        "ueber-500",
    )


def test_vintage_metadata_and_deductions_are_exact(heizspiegel: ModuleType) -> None:
    vintage = _resolved_vintage(heizspiegel)

    assert vintage.vintage == "Heizspiegel 2025"
    assert vintage.billing_year == 2024
    assert vintage.source_as_of == "09/2025"
    assert vintage.attribution_de == EXPECTED_ATTRIBUTION
    assert dict(vintage.warm_water_deductions_kwh_m2a) == EXPECTED_DEDUCTIONS
    assert vintage.heat_pump_deduction_status == ("verify-before-production_convention")


def test_vintage_source_row_identity_drives_resolution_evidence(
    heizspiegel: ModuleType,
) -> None:
    vintage_2025 = _resolved_vintage(heizspiegel)
    assert vintage_2025.source_row_identity == "HEIZSPIEGEL_2025_ROWS"

    vintage_2026 = replace(
        vintage_2025,
        vintage="Heizspiegel 2026",
        billing_year=2025,
        source_as_of="09/2026",
        source_row_identity="HEIZSPIEGEL_2026_ROWS",
    )
    two_vintages = RuleSet(
        key="heizspiegel.test-source-row-identity",
        versions=(
            RuleVersion(
                valid_from=date(2025, 10, 1),
                source=EXPECTED_ATTRIBUTION,
                value=vintage_2025,
            ),
            RuleVersion(
                valid_from=date(2026, 10, 1),
                source=EXPECTED_ATTRIBUTION,
                value=vintage_2026,
            ),
        ),
    )

    resolved_2025 = _resolve(
        heizspiegel,
        "Erdgas",
        "80-150",
        rule_set=two_vintages,
        as_of=date(2025, 10, 1),
    )
    resolved_2026 = _resolve(
        heizspiegel,
        "Erdgas",
        "80-150",
        rule_set=two_vintages,
        as_of=date(2026, 10, 1),
    )

    assert any(item.register_row == "HEIZSPIEGEL_2025_ROWS" for item in resolved_2025.evidence)
    assert any(item.register_row == "HEIZSPIEGEL_2026_ROWS" for item in resolved_2026.evidence)
    assert all(item.register_row != "HEIZSPIEGEL_2025_ROWS" for item in resolved_2026.evidence)


def test_resolution_retains_publication_and_effective_rechtsstand(
    heizspiegel: ModuleType,
) -> None:
    resolved_2025 = _resolve(heizspiegel, "Erdgas", "80-150")
    assert {item.rechtsstand for item in resolved_2025.evidence} >= {
        "09/2025",
        "Rechtsstand 10/2025",
    }

    vintage_2025 = _resolved_vintage(heizspiegel)
    vintage_2026 = replace(
        vintage_2025,
        vintage="Heizspiegel 2026",
        billing_year=2025,
        source_as_of="09/2026",
    )
    two_vintages = RuleSet(
        key="heizspiegel.test-effective-rechtsstand",
        versions=(
            RuleVersion(
                valid_from=date(2025, 10, 1),
                source=EXPECTED_ATTRIBUTION,
                value=vintage_2025,
            ),
            RuleVersion(
                valid_from=date(2026, 10, 1),
                source=EXPECTED_ATTRIBUTION,
                value=vintage_2026,
            ),
        ),
    )
    resolved_2026 = _resolve(
        heizspiegel,
        "Erdgas",
        "80-150",
        rule_set=two_vintages,
        as_of=date(2026, 10, 1),
    )

    assert {item.rechtsstand for item in resolved_2026.evidence} >= {
        "09/2026",
        "Rechtsstand 10/2026",
    }


def test_every_explicit_row_resolves_to_the_engine_input_with_evidence(
    heizspiegel: ModuleType,
) -> None:
    for size_class, energy_source, _low, middle, _high, _too_high in EXPECTED_ROWS:
        resolved = _resolve(heizspiegel, energy_source, size_class)

        assert type(resolved) is ResolvedHeizspiegelRow
        assert resolved.energy_source == energy_source
        assert resolved.requested_size_class == size_class
        assert resolved.actual_size_class == size_class
        assert resolved.heizspiegel_mittel_kwh_m2a == Decimal(middle)
        assert resolved.warm_water_deduction_kwh_m2a == Decimal(EXPECTED_DEDUCTIONS[energy_source])
        assert resolved.heizspiegel_vintage == "2025/billing-year-2024"
        assert resolved.fallback_label_de is None
        assert resolved.evidence
        assert all(type(item) is RuleEvidence for item in resolved.evidence)
        assert any(item.register_row == "HEIZSPIEGEL_D2_CONTRACT" for item in resolved.evidence)
        assert any(item.rechtsstand == "09/2025" for item in resolved.evidence)
        assert any(
            item.verification_status == "verify-before-production" for item in resolved.evidence
        )
        assert any(item.source == EXPECTED_ATTRIBUTION for item in resolved.evidence)


@pytest.mark.parametrize("energy_source", ["Waermepumpe", "Holzpellets"])
def test_missing_over_500_rows_fall_back_visibly(
    heizspiegel: ModuleType,
    energy_source: str,
) -> None:
    resolved = _resolve(heizspiegel, energy_source, "ueber-500")
    expected_middle = 30 if energy_source == "Waermepumpe" else 113

    assert resolved.requested_size_class == "ueber-500"
    assert resolved.actual_size_class == "250-500"
    assert resolved.heizspiegel_mittel_kwh_m2a == Decimal(expected_middle)
    assert resolved.warm_water_deduction_kwh_m2a == Decimal(EXPECTED_DEDUCTIONS[energy_source])
    assert resolved.fallback_label_de == EXPECTED_FALLBACK_LABEL


def test_import_validation_rejects_any_non_positive_heat_only_row(
    heizspiegel: ModuleType,
) -> None:
    vintage = _resolved_vintage(heizspiegel)
    invalid_row = replace(vintage.rows[0], middle_kwh_m2a=24)
    invalid_rows = (invalid_row, *vintage.rows[1:])

    with pytest.raises(ValueError, match=r"middle.*deduction.*positive"):
        heizspiegel.validate_heizspiegel_import(
            invalid_rows,
            vintage.warm_water_deductions_kwh_m2a,
        )


def test_rule_data_is_immutable(heizspiegel: ModuleType) -> None:
    vintage = _resolved_vintage(heizspiegel)

    with pytest.raises(FrozenInstanceError):
        vintage.billing_year = 2025
    with pytest.raises(FrozenInstanceError):
        vintage.rows[0].middle_kwh_m2a = 999
    with pytest.raises(TypeError):
        vintage.warm_water_deductions_kwh_m2a["Erdgas"] = 999


def test_2025_vintage_starts_on_the_documented_first_of_october(
    heizspiegel: ModuleType,
) -> None:
    with pytest.raises(RuleNotFoundError):
        get_rule(heizspiegel.HEIZSPIEGEL_RULES, date(2025, 9, 30))

    resolved = get_rule(heizspiegel.HEIZSPIEGEL_RULES, date(2025, 10, 1))
    assert resolved.value.vintage == "Heizspiegel 2025"
    assert resolved.rechtsstand == "Rechtsstand 10/2025"


def test_resolution_uses_vintage_at_month_m_not_newest_version(
    heizspiegel: ModuleType,
) -> None:
    vintage_2025 = _resolved_vintage(heizspiegel)
    changed_row = replace(vintage_2025.rows[0], middle_kwh_m2a=122)
    vintage_2026 = replace(
        vintage_2025,
        vintage="Heizspiegel 2026",
        billing_year=2025,
        source_as_of="09/2026",
        rows=(changed_row, *vintage_2025.rows[1:]),
    )
    two_vintages = RuleSet(
        key="heizspiegel.test-vintage-selection",
        versions=(
            RuleVersion(
                valid_from=date(2025, 10, 1),
                source=EXPECTED_ATTRIBUTION,
                value=vintage_2025,
            ),
            RuleVersion(
                valid_from=date(2026, 10, 1),
                source=EXPECTED_ATTRIBUTION,
                value=vintage_2026,
            ),
        ),
    )

    september_2026 = _resolve(
        heizspiegel,
        "Erdgas",
        "80-150",
        rule_set=two_vintages,
        as_of=date(2026, 9, 1),
    )
    october_2026 = _resolve(
        heizspiegel,
        "Erdgas",
        "80-150",
        rule_set=two_vintages,
        as_of=date(2026, 10, 1),
    )

    assert september_2026.heizspiegel_mittel_kwh_m2a == Decimal(121)
    assert september_2026.heizspiegel_vintage == "2025/billing-year-2024"
    assert october_2026.heizspiegel_mittel_kwh_m2a == Decimal(122)
    assert october_2026.heizspiegel_vintage == "2026/billing-year-2025"
