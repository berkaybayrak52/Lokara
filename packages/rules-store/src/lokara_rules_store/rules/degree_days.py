"""Monthly degree-day (Gradtagszahlen) weights for mid-period apportionment.

Used when a renter changes mid-period without an interim meter reading: the
unit's consumption is apportioned across occupants by these month weights
(promille of the heating year, Jan..Dec, summing to 1000).

The *method* is statutory — § 9b Abs. 2 HeizkostenV permits apportioning an
unread period by Gradtagszahlen, Abs. 3 puts Grund- und Warmwasserkosten on
Zeitanteile. The *numbers* are not: the promille table is a VDI convention.
`source` therefore names both halves, separated by the semicolon, so a statement
citing § 9b never presents the table as a Rechtsnorm.

TODO(verify): this is the widely used Promille-Tabelle (VDI convention), not a
statute — verify the exact table against the current VDI source before
production use.

`valid_from`/`Rechtsstand 01/1981` date the **table**. § 9b's own in-force date
is not verified anywhere (it needs the BGBl. history of the HeizkostenV), so no
output may pair the paragraph with that stamp. Spec:
`docs/08-statement-document.md` → "The method's statutory basis (§ 9b
HeizkostenV) is a prerequisite, not an assumption".
"""

from datetime import date

from lokara_domain import DegreeDayTable

from ..store import RuleSet, RuleVersion

DEGREE_DAY_TABLE: RuleSet[DegreeDayTable] = RuleSet(
    key="heating.degree-day-promille",
    versions=(
        RuleVersion(
            valid_from=date(1981, 1, 1),
            # The em dash appears exactly once and last: the renderer drops
            # everything after it, so the internal marker never reaches a tenant.
            source=(
                "§ 9b Abs. 2 und Abs. 3 HeizkostenV; Gradtagszahlen nach anerkannter "
                "Promilletabelle (VDI-Konvention, keine Rechtsnorm) "
                "— verify before production"
            ),
            value=DegreeDayTable(
                promille_by_month=(170, 150, 130, 80, 40, 15, 10, 10, 30, 80, 120, 165),
            ),
        ),
    ),
)
