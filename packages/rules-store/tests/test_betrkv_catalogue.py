"""Production checks for Page 02.

The data-only oracle in ``berkay_09_golden.py`` remains deliberately separate.
These tests exercise the rules-store surface which adapters and the API use.
"""

from datetime import date

import pytest
from lokara_domain import AllocationKey
from lokara_rules_store.betrkv_catalogue import (
    CataloguePosition,
    ContractFacts,
    classify_position,
    split_position_at_rule_boundaries,
)


@pytest.mark.parametrize(
    ("cost_type", "allocable", "key"),
    [
        ("grundsteuer", True, AllocationKey.AREA),
        ("wasserversorgung", True, AllocationKey.CONSUMPTION),
        ("hauswart", True, AllocationKey.AREA),
        ("glasfaser_bereitstellung", True, AllocationKey.UNITS),
        ("elektropruefung", True, AllocationKey.AREA),
        ("sonstige", True, AllocationKey.AREA),
        ("verwaltungskosten", False, None),
        ("instandhaltung", False, None),
        ("erneuerung", False, None),
        ("kabel_altentgelt", False, None),
        ("antenne_neuanlage", False, None),
    ],
)
def test_catalogue_resolves_known_identities(
    cost_type: str, allocable: bool, key: AllocationKey | None
) -> None:
    result = classify_position(
        CataloguePosition(cost_type, 10_000, receipt_date=date(2025, 2, 1)),
        ContractFacts(
            allocation_agreed=True,
            named_other_costs=frozenset({"elektropruefung", "sonstige"}),
        ),
    )
    assert result.allocable_cents == (10_000 if allocable else 0)
    assert result.non_allocable_cents == (0 if allocable else 10_000)
    assert result.key is key
    assert result.production_blocked  # all current Page-02 conventions stay visible


def test_missing_agreement_is_conservative_and_never_infers_a_key() -> None:
    result = classify_position(
        CataloguePosition("grundsteuer", 10_000, receipt_date=date(2025, 2, 1)),
        ContractFacts(allocation_agreed=False),
    )
    assert result.allocable_cents == 0
    assert result.non_allocable_cents == 10_000
    assert result.key is None
    assert "umlagevereinbarung-fehlt" in result.findings


def test_nr17_requires_a_named_category_except_the_documented_fallback() -> None:
    ordinary = classify_position(
        CataloguePosition("dachrinnenreinigung", 10_000, receipt_date=date(2025, 2, 1)),
        ContractFacts(allocation_agreed=True),
    )
    fallback = classify_position(
        CataloguePosition("trinkwasseruntersuchung", 10_000, receipt_date=date(2025, 2, 1)),
        ContractFacts(allocation_agreed=True),
    )
    assert ordinary.allocable_cents == 0
    assert fallback.allocable_cents == 10_000
    assert fallback.betrkv_number == "2 Nr. 2"
    assert "trinkwasser-nr17-fallback" in fallback.findings


def test_confirmed_override_is_retained_and_invalid_money_is_refused() -> None:
    result = classify_position(
        CataloguePosition(
            "grundsteuer",
            10_000,
            receipt_date=date(2025, 2, 1),
            non_allocable_cents=2_000,
            key_override=AllocationKey.UNITS,
        ),
        ContractFacts(allocation_agreed=True),
    )
    assert result.allocable_cents == 8_000
    assert result.non_allocable_cents == 2_000
    assert result.key is AllocationKey.UNITS
    assert result.key_source == "override"
    with pytest.raises(ValueError, match="non_allocable_cents"):
        classify_position(
            CataloguePosition(
                "grundsteuer", 100, receipt_date=date(2025, 2, 1), non_allocable_cents=101
            ),
            ContractFacts(allocation_agreed=True),
        )


def test_service_date_wins_over_receipt_date_and_rule_boundaries_split_day_exactly() -> None:
    position = CataloguePosition(
        "grundsteuer",
        36_600,
        receipt_date=date(2025, 1, 1),
        service_from=date(2024, 1, 1),
        service_to=date(2025, 1, 1),
    )
    parts = split_position_at_rule_boundaries(position, (date(2024, 7, 1),))
    assert [(part.amount_cents, part.service_from, part.service_to) for part in parts] == [
        (18_200, date(2024, 1, 1), date(2024, 7, 1)),
        (18_400, date(2024, 7, 1), date(2025, 1, 1)),
    ]
