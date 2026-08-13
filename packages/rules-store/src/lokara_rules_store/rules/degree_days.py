"""Monthly degree-day (Gradtagszahlen) weights for mid-period apportionment.

Used when a renter changes mid-period without an interim meter reading: the
unit's consumption is apportioned across occupants by these month weights
(**Zehntelpromille** of the heating year, Jan..Dec, summing to 10 000).

The *method* is statutory — § 9b Abs. 2 HeizkostenV permits apportioning an
unread period by Gradtagszahlen, Abs. 3 puts Grund- und Warmwasserkosten on
Zeitanteile. The *numbers* are not: the table is a VDI convention. `source`
therefore names both halves, separated by the semicolon, so a statement citing
§ 9b never presents the table as a Rechtsnorm.

**K3 (12.08.2026): VDI 2067 Blatt 1, Ausgabe 12/1983, Tabelle 22**, replacing the
unsourced table `170 150 130 80 40 15 10 10 30 80 120 165` that carried
`TODO(verify)` and pointed at nothing anybody could check. Eight months agree,
four do not (Jun, Jul, Aug, Dez). § 9b Abs. 2 demands *"Gradtagszahlen nach
anerkannten Regeln der Technik"* and prints no table, so it is a convention
either way — but a convention with a citation beats one without. The flag stays
`verify before production`.

Jun/Jul/Aug are 13,3 / 13,3 / 13,4 ‰ (400/3), which is why the stored unit is
Zehntelpromille: see `DegreeDayTable`. Display value = stored / 10.

`valid_from`/`Rechtsstand 12/1983` date the **VDI edition**, not § 9b — the
paragraph's own in-force date is not verified anywhere (it needs the BGBl.
history of the HeizkostenV), so no output may pair the paragraph with that
stamp. Spec: `docs/03-nk-heating-engines.md` → "Seite 01b … (2) K3" and
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
            valid_from=date(1983, 12, 1),
            # The em dash appears exactly once and last: the renderer drops
            # everything after it, so the internal marker never reaches a tenant.
            source=(
                "§ 9b Abs. 2 und Abs. 3 HeizkostenV; Gradtagszahlen nach VDI 2067 Blatt 1, "
                "Ausgabe 12/1983, Tabelle 22 (Konvention, keine Rechtsnorm) "
                "— verify before production"
            ),
            value=DegreeDayTable(
                # Jan   Feb   Mär   Apr  Mai  Jun  Jul  Aug  Sep  Okt  Nov   Dez
                tenth_promille_by_month=(
                    1700,
                    1500,
                    1300,
                    800,
                    400,
                    133,
                    133,
                    134,
                    300,
                    800,
                    1200,
                    1600,
                ),
            ),
        ),
    ),
)
