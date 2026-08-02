from datetime import date

import pytest
from lokara_domain import Occupancy, OccupancyOverlapError, build_unit_segments, period

WINDOW_FROM = date(2025, 1, 1)
WINDOW_TO = date(2026, 1, 1)


class TestBuildUnitSegments:
    def test_derives_vacancy_gap_as_landlord_segment(self) -> None:
        # The arch example: renter out Jun 30 → Jul-Dec is a derived landlord gap.
        segments = build_unit_segments(
            "unit-b",
            (Occupancy("unit-b", "ten-2", period("2025-01-01", "2025-07-01")),),
            WINDOW_FROM,
            WINDOW_TO,
        )
        assert [(s.tenancy_id, s.days) for s in segments] == [("ten-2", 181), (None, 184)]
        assert segments[1].start == date(2025, 7, 1)

    def test_full_year_tenancy_yields_single_segment(self) -> None:
        segments = build_unit_segments(
            "unit-a",
            (Occupancy("unit-a", "ten-1", period("2020-05-01")),),
            WINDOW_FROM,
            WINDOW_TO,
        )
        assert [(s.tenancy_id, s.days) for s in segments] == [("ten-1", 365)]

    def test_empty_unit_is_fully_vacant(self) -> None:
        segments = build_unit_segments("unit-x", (), WINDOW_FROM, WINDOW_TO)
        assert [(s.tenancy_id, s.days) for s in segments] == [(None, 365)]

    def test_gap_between_two_tenancies_and_leading_gap(self) -> None:
        segments = build_unit_segments(
            "unit-c",
            (
                Occupancy("unit-c", "ten-old", period("2025-02-01", "2025-04-01")),
                Occupancy("unit-c", "ten-new", period("2025-06-01")),
            ),
            WINDOW_FROM,
            WINDOW_TO,
        )
        assert [(s.tenancy_id, s.days) for s in segments] == [
            (None, 31),
            ("ten-old", 59),
            (None, 61),
            ("ten-new", 214),
        ]

    def test_explicit_self_use_row_stays_landlord_side(self) -> None:
        segments = build_unit_segments(
            "unit-d",
            (Occupancy("unit-d", None, period("2025-01-01", "2025-07-01")),),
            WINDOW_FROM,
            WINDOW_TO,
        )
        assert [(s.tenancy_id, s.days) for s in segments] == [(None, 181), (None, 184)]

    def test_rejects_overlapping_occupancies(self) -> None:
        with pytest.raises(OccupancyOverlapError):
            build_unit_segments(
                "unit-e",
                (
                    Occupancy("unit-e", "ten-1", period("2025-01-01", "2025-07-01")),
                    Occupancy("unit-e", "ten-2", period("2025-06-01")),
                ),
                WINDOW_FROM,
                WINDOW_TO,
            )

    def test_ignores_rows_of_other_units_and_outside_window(self) -> None:
        segments = build_unit_segments(
            "unit-f",
            (
                Occupancy("unit-g", "ten-other", period("2025-01-01")),
                Occupancy("unit-f", "ten-past", period("2020-01-01", "2021-01-01")),
                Occupancy("unit-f", "ten-1", period("2025-01-01")),
            ),
            WINDOW_FROM,
            WINDOW_TO,
        )
        assert [(s.tenancy_id, s.days) for s in segments] == [("ten-1", 365)]
