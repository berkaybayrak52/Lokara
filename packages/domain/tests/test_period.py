from datetime import date

import pytest
from lokara_domain import days_between, overlap_days, period, periods_overlap


class TestPeriod:
    def test_builds_half_open_periods(self) -> None:
        p = period("2025-01-01", "2025-07-01")
        assert p.valid_from == date(2025, 1, 1)
        assert p.valid_to == date(2025, 7, 1)
        assert period("2025-01-01").valid_to is None

    def test_rejects_inverted_ranges(self) -> None:
        with pytest.raises(ValueError):
            period("2025-07-01", "2025-01-01")
        with pytest.raises(ValueError):
            period("2025-01-01", "2025-01-01")


class TestDayCounting:
    def test_days_between_is_half_open(self) -> None:
        assert days_between(date(2025, 1, 1), date(2026, 1, 1)) == 365
        assert days_between(date(2024, 1, 1), date(2025, 1, 1)) == 366  # leap year
        assert days_between(date(2025, 1, 1), date(2025, 1, 2)) == 1

    def test_overlap_days_clips_to_the_window(self) -> None:
        window_from, window_to = date(2025, 1, 1), date(2026, 1, 1)
        # The arch example: move-out Jun 30 → tenancy ends (exclusive) Jul 1 → 181 days.
        assert overlap_days(period("2025-01-01", "2025-07-01"), window_from, window_to) == 181
        assert overlap_days(period("2024-06-01", "2025-07-01"), window_from, window_to) == 181
        assert overlap_days(period("2025-07-01"), window_from, window_to) == 184
        assert overlap_days(period("2026-02-01"), window_from, window_to) == 0
        assert overlap_days(period("2020-01-01", "2024-12-31"), window_from, window_to) == 0

    def test_periods_overlap(self) -> None:
        assert periods_overlap(period("2025-01-01", "2025-07-01"), period("2025-06-30")) is True
        assert periods_overlap(period("2025-01-01", "2025-07-01"), period("2025-07-01")) is False
        assert periods_overlap(period("2025-01-01"), period("2030-01-01")) is True
