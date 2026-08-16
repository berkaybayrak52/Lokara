"""Coverage gate for every Page 01b worked example, including suffix variants.

The full data table is committed before the remaining implementation.  The first missing
engine seam is H7 (MDL).  Its contract test is intentionally red without causing a collection or
import error; the implementer can pick it up after this spec slice.
"""

from decimal import Decimal

import lokara_heating_engine
import pytest
from berkay_01b_golden import PAGE_01B_GOLDENS

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


def test_every_page_01b_fixture_and_suffix_variant_has_an_oracle() -> None:
    assert set(PAGE_01B_GOLDENS) == EXPECTED_IDS


@pytest.mark.parametrize(
    "fixture_id",
    [
        "01b-F01",
        "01b-F11",
        "01b-F12",
        "01b-F13",
        "01b-F14",
        "01b-F15",
        "01b-F16",
        "01b-F18",
        "01b-F28a",
        "01b-F28b",
    ],
)
def test_every_party_allocation_oracle_reconciles(fixture_id: str) -> None:
    case = PAGE_01B_GOLDENS[fixture_id]
    shares = case["renter_totals"]
    owner_total = case["owner_total"]
    billable_total = case["billable_total"]
    assert isinstance(shares, tuple)
    assert isinstance(owner_total, int)
    assert isinstance(billable_total, int)
    assert sum(shares) + owner_total == billable_total


def test_berkay_01b_f28b_mdl_gross_branch_rescales_without_a_second_deduction() -> None:
    """H7/M2/M3: the absent MDL seam is the first implementation hand-off.

    This assertion fails as a missing capability, not during import/collection.  The future
    callable consumes confirmed gross positions, the confirmed gross total, and the already
    calculated billable total.  It must use the exact quotient, tolerate the one-cent source
    residual, and return the cent-exact F28b positions.
    """

    rescale = getattr(lokara_heating_engine, "rescale_mdl_gross_positions", None)
    assert callable(rescale), "H7 MDL gross rescaling is not implemented"

    case = PAGE_01B_GOLDENS["01b-F28b"]
    output = rescale(
        gross_positions=(131_874, 77_236, 36_055, 102_029),
        gross_owner=3_405,
        gross_total=350_600,
        billable_total=338_218,
    )
    assert output.renter_totals == case["renter_totals"]
    assert output.owner_total == case["owner_total"]
    assert output.source_difference == 1
    assert output.tolerance == 5
    assert sum(output.renter_totals) + output.owner_total == case["billable_total"]
    assert output.scale == Decimal(338_218) / Decimal(350_600)
