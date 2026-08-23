"""Red § 12 HeizkostenV engine contract from the Round-4 source oracle."""

from decimal import Decimal
from typing import cast

import pytest
from berkay_section12_golden import SECTION12_GOLDENS
from lokara_domain import Cents, cents, period
from lokara_heating_engine import (
    MdlCo2Calculation,
    MdlStatementInput,
    Page01bStatementResult,
    RiskTriggers,
    Section12ReductionResult,
    Section12RenterReduction,
    calculate_page01b_statement,
)
from test_page01b_orchestrator import CO2_TABLE, _result

_MDL_COMPONENTS = cast(dict[str, object], SECTION12_GOLDENS["mdl_components"])
_SINGLE_COMPONENTS = cast(dict[str, tuple[int, int, int, int, int]], _MDL_COMPONENTS["single"])
_COMBINATIONS = cast(
    dict[tuple[str, ...], tuple[int, int, int, int, int]], _MDL_COMPONENTS["combinations"]
)


def _mdl(
    *,
    risks: RiskTriggers | None = None,
    non_consumption: tuple[int, ...] | None = (10_005,),
    positions: tuple[int, ...] = (10_005,),
) -> Page01bStatementResult:
    return calculate_page01b_statement(
        MdlStatementInput(
            branch="NET",
            renter_ids=("Muster",),
            renter_positions=positions,
            renter_non_consumption_positions=non_consumption,
            owner_position=0,
            confirmed_total=sum(positions),
            risks=RiskTriggers() if risks is None else risks,
        )
    )


def _reduction(result: Page01bStatementResult) -> Section12ReductionResult:
    reduction = result.section12_reduction
    assert reduction is not None
    return reduction


def _renter(result: Page01bStatementResult) -> Section12RenterReduction:
    reduction = _reduction(result)
    assert reduction.is_complete is True
    assert len(reduction.renters) == 1
    return reduction.renters[0]


def _net_claim(renter: Section12RenterReduction) -> Cents:
    assert renter.net_claim is not None
    return renter.net_claim


def _components(renter: Section12RenterReduction) -> tuple[int, int, int, int, int]:
    return (
        int(renter.non_consumption_15_percent),
        int(renter.remote_readability_3_percent),
        int(renter.section_6a_information_3_percent),
        int(renter.total_deduction),
        int(_net_claim(renter)),
    )


@pytest.mark.parametrize(
    ("risks", "expected"),
    [
        (
            RiskTriggers(consumption_billing_missing=True),
            _SINGLE_COMPONENTS["consumption_billing_missing"],
        ),
        (
            RiskTriggers(remote_readability_missing=True),
            _SINGLE_COMPONENTS["remote_readability_missing"],
        ),
        (
            RiskTriggers(section_6a_information_missing=True),
            _SINGLE_COMPONENTS["section_6a_information_missing"],
        ),
        *(
            (
                RiskTriggers(**{ground: True for ground in grounds}),
                expected,
            )
            for grounds, expected in _COMBINATIONS.items()
        ),
    ],
)
def test_section12_components_are_independent_and_non_cascading(
    risks: RiskTriggers, expected: tuple[int, int, int, int, int]
) -> None:
    renter = _renter(_mdl(risks=risks))
    assert int(renter.gross_claim) == 10_005
    assert _components(renter) == expected


def test_section12_cap_is_21_percent_after_each_component_is_rounded() -> None:
    result = _mdl(
        risks=RiskTriggers(
            consumption_billing_missing=True,
            remote_readability_missing=True,
            section_6a_information_missing=True,
        )
    )
    renter = _renter(result)
    assert int(renter.total_deduction) == 2_101
    reduction_ratio = Decimal(int(renter.total_deduction)) / Decimal(int(renter.gross_claim))
    assert reduction_ratio <= Decimal("0.21")
    assert _reduction(result).warnings == (cast(str, SECTION12_GOLDENS["warning"]),)


def test_section12_zero_value_components_keep_the_gross_audit_value() -> None:
    renter = _renter(
        _mdl(
            risks=RiskTriggers(
                consumption_billing_missing=True,
                remote_readability_missing=True,
                section_6a_information_missing=True,
            ),
            non_consumption=(0,),
            positions=(0,),
        )
    )
    assert _components(renter) == (0, 0, 0, 0, 0)


def test_section12_self_billing_uses_line_non_consumption_columns_and_reconciles() -> None:
    result = _result(
        risks=RiskTriggers(
            consumption_billing_missing=True,
            remote_readability_missing=True,
            section_6a_information_missing=True,
        )
    )
    reduction = _reduction(result)
    assert reduction.is_complete is True
    actual = tuple(
        (
            renter.renter_id,
            int(renter.gross_claim),
            int(renter.non_consumption_15_percent),
            int(renter.remote_readability_3_percent),
            int(renter.section_6a_information_3_percent),
            int(renter.total_deduction),
            int(_net_claim(renter)),
        )
        for renter in reduction.renters
    )
    assert actual == cast(
        tuple[tuple[str, int, int, int, int, int, int], ...],
        SECTION12_GOLDENS["self_billing_all_grounds"],
    )
    assert all(r.gross_claim - r.total_deduction == _net_claim(r) for r in reduction.renters)


@pytest.mark.parametrize(
    "non_consumption",
    (None, (), (-1,), (10_006,)),
)
def test_section12_mdl_invalid_or_missing_splits_are_explicitly_incomplete(
    non_consumption: tuple[int, ...] | None,
) -> None:
    result = _mdl(non_consumption=non_consumption)
    reduction = _reduction(result)
    assert reduction.is_complete is False
    assert reduction.renters[0].net_claim is None


def test_section12_mdl_net_and_gross_paths_reconcile_with_supplied_splits() -> None:
    net = _mdl(risks=RiskTriggers(remote_readability_missing=True))
    net_renter = _renter(net)
    assert net_renter.gross_claim - net_renter.total_deduction == _net_claim(net_renter)

    gross = calculate_page01b_statement(
        MdlStatementInput(
            branch="GROSS",
            renter_ids=("Muster",),
            renter_positions=(10_005,),
            renter_non_consumption_positions=(10_005,),
            owner_position=0,
            confirmed_total=10_005,
            risks=RiskTriggers(remote_readability_missing=True),
            co2=MdlCo2Calculation(
                total_co2_kg=Decimal(100),
                co2_cost=cents(0),
                heated_area_sqm=Decimal(100),
                table=CO2_TABLE,
                rechtsstand="Rechtsstand 01/2023",
                billing_period=period("2025-01-01", "2026-01-01"),
            ),
        )
    )
    gross_renter = _renter(gross)
    assert gross_renter.gross_claim - gross_renter.total_deduction == _net_claim(gross_renter)
