"""Monthly degree-day (Gradtagszahlen) weights for mid-period apportionment.

Used when a renter changes mid-period without an interim meter reading: the
unit's consumption is apportioned across occupants by these month weights
(promille of the heating year, Jan..Dec, summing to 1000).

TODO(verify): this is the widely used Promille-Tabelle (VDI convention), not a
statute — verify the exact table against the current VDI source before
production use.
"""

from datetime import date

from lokara_domain import DegreeDayTable

from ..store import RuleSet, RuleVersion

DEGREE_DAY_TABLE: RuleSet[DegreeDayTable] = RuleSet(
    key="heating.degree-day-promille",
    versions=(
        RuleVersion(
            valid_from=date(1981, 1, 1),
            source="Anerkannte Gradtagszahlen-Promilletabelle (VDI) — verify before production",
            value=DegreeDayTable(
                promille_by_month=(170, 150, 130, 80, 40, 15, 10, 10, 30, 80, 120, 165),
            ),
        ),
    ),
)
