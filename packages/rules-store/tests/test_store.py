from datetime import date

import pytest
from lokara_rules_store import (
    RuleNotFoundError,
    RuleSet,
    RuleVersion,
    format_rechtsstand,
    get_rule,
)

SAMPLE: RuleSet[int] = RuleSet(
    key="sample.rate",
    versions=(
        RuleVersion(valid_from=date(2020, 1, 1), source="v2020", value=20),
        RuleVersion(valid_from=date(2023, 7, 1), source="v2023", value=23),
        RuleVersion(
            valid_from=date(2018, 1, 1), source="v2018", value=18, valid_to=date(2020, 1, 1)
        ),
    ),
)


class TestGetRule:
    def test_resolves_the_version_valid_as_of_the_date(self) -> None:
        assert get_rule(SAMPLE, date(2019, 6, 1)).value == 18
        assert get_rule(SAMPLE, date(2021, 1, 1)).value == 20
        assert get_rule(SAMPLE, date(2023, 7, 1)).value == 23
        assert get_rule(SAMPLE, date(2030, 1, 1)).value == 23

    def test_stamps_rechtsstand_from_the_matched_version(self) -> None:
        resolved = get_rule(SAMPLE, date(2024, 3, 15))
        assert resolved.rechtsstand == "Rechtsstand 07/2023"
        assert resolved.source == "v2023"

    def test_raises_before_the_first_version(self) -> None:
        with pytest.raises(RuleNotFoundError):
            get_rule(SAMPLE, date(2017, 12, 31))

    def test_valid_to_is_exclusive(self) -> None:
        assert get_rule(SAMPLE, date(2019, 12, 31)).value == 18
        assert get_rule(SAMPLE, date(2020, 1, 1)).value == 20


class TestFormatRechtsstand:
    def test_zero_pads_the_month(self) -> None:
        assert format_rechtsstand(date(2023, 1, 1)) == "Rechtsstand 01/2023"
        assert format_rechtsstand(date(2024, 11, 30)) == "Rechtsstand 11/2024"
