"""K3 - Gradtagszahlen per VDI 2067 Blatt 1, Ausgabe 12/1983, Tabelle 22.

Spec: `docs/03-nk-heating-engines.md` -> "Seite 01b … (2) K3". Source:
`berkay-work/…/01b · Heizkosten- & CO₂-Verteilung ….md` § 2 (K3), fixture
`01b-F16`, and the Rechtsstand-Register row "Gradtagszahltabelle VDI (K3)".

**Why the table moved.** The built table (`170 150 130 80 40 15 10 10 30 80 120
165`) carried `TODO(verify)` and was sourced to nothing. Berkay's is sourced to a
named VDI edition and table number. Eight months agree; Jun, Jul, Aug and Dez do
not. § 9b Abs. 2 HeizkostenV demands *"Gradtagszahlen nach anerkannten Regeln der
Technik"* and prints no table, so it is a convention either way - but a
convention with a citation beats one without. Flag stays
`verify-before-production`.

**Why the type moved with it.** 13,3 / 13,3 / 13,4 is 400/3 split three ways and
cannot be an integer promille. Stored unit: **Zehntelpromille, sum 10 000**.

Fails today with `TypeError: unexpected keyword argument
'tenth_promille_by_month'`.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from lokara_domain import DegreeDayTable
from lokara_heating_engine.degree_days import degree_day_weight


# Built per call rather than at module level: the keyword does not exist yet, and
# a module-level TypeError would collapse the whole file into one collection error
# instead of showing which rule each assertion pins.
def vdi_2067_tab_22() -> DegreeDayTable:
    return DegreeDayTable(
        tenth_promille_by_month=(1700, 1500, 1300, 800, 400, 133, 133, 134, 300, 800, 1200, 1600)
    )


def _round_1dp(value: Decimal) -> Decimal:
    """R7 / K11 - device units carry one decimal place, `round_half_up`."""
    return value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)


def _round_cents(value: Decimal) -> int:
    """R1 - money is rounded once, at assignment."""
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


class TestTheTableItself:
    def test_the_weight_of_a_whole_month_is_its_stored_tenth_promille(self) -> None:
        assert degree_day_weight(date(2025, 6, 1), 30, vdi_2067_tab_22()) == Decimal(133)
        assert degree_day_weight(date(2025, 8, 1), 31, vdi_2067_tab_22()) == Decimal(134)
        assert degree_day_weight(date(2025, 12, 1), 31, vdi_2067_tab_22()) == Decimal(1600)

    def test_a_full_year_is_10000_tenth_promille(self) -> None:
        assert degree_day_weight(date(2025, 1, 1), 365, vdi_2067_tab_22()) == Decimal(10_000)

    def test_the_half_year_split_the_demo_prints_moves_to_583_3(self) -> None:
        """Jan-Jun 5833 (583,3 permille) and Jul-Dec 4167 (416,7 permille),
        replacing 585,0 / 415,0.

        This is the entire money consequence of K3: the demo's unit-B heating
        row re-bases **778,79 € / 552,47 € -> 776,52 € / 554,74 €** (`docs/06`).
        Recomputed under both rounding methods - the demo chain is identical
        under largest-remainder and under R5/K9 - so the pair moves for exactly
        one reason, and it is this table.
        """
        jan_jun = degree_day_weight(date(2025, 1, 1), 181, vdi_2067_tab_22())
        jul_dec = degree_day_weight(date(2025, 7, 1), 184, vdi_2067_tab_22())
        assert jan_jun == Decimal(5833)
        assert jul_dec == Decimal(4167)
        assert jan_jun + jul_dec == Decimal(10_000)

    def test_the_demo_pot_splits_776_52_to_554_74(self) -> None:
        """The pair itself, on the demo's heating-consumption pot of 532.503 ct
        and unit B's single annual reading of 250 units. Pinned here as the
        anchor `DEMO-RUNBOOK.md`, `scripts/assert_statement_pdf.py` and the PDF
        goldens are re-based against - so the runbook figure has a source.
        """
        pot = Decimal(532_503)
        unit_b = Decimal(250)  # unit B's single annual reading
        weights = [
            Decimal(600),
            unit_b * Decimal(5833) / 10_000,
            unit_b * Decimal(4167) / 10_000,
            Decimal(150),
        ]
        total_weight = sum(weights, Decimal(0))
        renter = _round_cents(pot * weights[1] / total_weight)
        landlord = _round_cents(pot * weights[2] / total_weight)
        assert (renter, landlord) == (77_652, 55_474)  # was 77_879 / 55_247 under 585/415


class TestBerkay01bF16TenantChangeWithoutAnInterimReading:
    """`01b-F16` / E12 - § 9b Abs. 3, WE-02 has one annual reading of 3.600,0.

    Schneider left 31.07., Weber moved in 01.09., August was vacant, and nobody
    read the devices. The unread period is apportioned by K3.

    Against `01b-F01` (a real interim reading): Schneider **-53,43 €**, Weber
    **+46,51 €**. That difference is the argument for forcing the Auszugs-
    ablesung in the UI, and it is why this fixture exists.
    """

    UNITS = Decimal("3600.0")

    def test_the_three_segments_carry_their_own_month_weights(self) -> None:
        schneider = degree_day_weight(date(2025, 1, 1), 212, vdi_2067_tab_22())  # Jan-Jul
        vacancy = degree_day_weight(date(2025, 8, 1), 31, vdi_2067_tab_22())  # Aug
        weber = degree_day_weight(date(2025, 9, 1), 122, vdi_2067_tab_22())  # Sep-Dec
        assert (schneider, vacancy, weber) == (Decimal(5966), Decimal(134), Decimal(3900))
        assert schneider + vacancy + weber == Decimal(10_000)

    def test_the_apportioned_units_round_to_one_decimal_with_the_rest_to_the_owner(self) -> None:
        """R7: 2.147,8 / 1.404,0, and the vacancy segment takes the remainder
        48,2 - not its own 48,24. The residual principle applies to units too.
        """
        schneider = _round_1dp(self.UNITS * Decimal(5966) / 10_000)
        weber = _round_1dp(self.UNITS * Decimal(3900) / 10_000)
        vacancy = self.UNITS - schneider - weber
        assert (schneider, weber, vacancy) == (
            Decimal("2147.8"),
            Decimal("1404.0"),
            Decimal("48.2"),
        )

    def test_the_consumption_block_lands_on_the_printed_cents(self) -> None:
        """verbrauchHz 154.312 ct over the plant denominator 10.750,0 units.

        Berkay's Summenprobe: 334.241 ct auf die Mieter + 3.977 ct Eigentuemer
        = 338.218 ct. The vacancy segment's own `round_half_up` is 692 ct; the
        owner bucket receives the block's residual, 691 ct, which is the figure
        his own Probe reconciles to (`docs/03` § 7 no. 7).
        """
        denominator = Decimal("10750.0")
        block = Decimal(154_312)
        muster = _round_cents(block * Decimal("4100.0") / denominator)
        schneider = _round_cents(block * Decimal("2147.8") / denominator)
        weber = _round_cents(block * Decimal("1404.0") / denominator)
        beispiel = _round_cents(block * Decimal("3050.0") / denominator)
        assert (muster, schneider, weber, beispiel) == (58_854, 30_831, 20_154, 43_782)
        owner = int(block) - (muster + schneider + weber + beispiel)
        assert owner == 691
        assert _round_cents(block * Decimal("48.2") / denominator) == 692  # its own quota

        # The other three blocks are unchanged from 01b-F01.
        other_blocks = {"muster": 68_363, "schneider": 38_334, "weber": 19_279, "beispiel": 54_644}
        assert muster + other_blocks["muster"] == 127_217
        assert schneider + other_blocks["schneider"] == 69_165
        assert weber + other_blocks["weber"] == 39_433
        assert beispiel + other_blocks["beispiel"] == 98_426
        assert 127_217 + 69_165 + 39_433 + 98_426 == 334_241

    def test_the_cost_of_not_forcing_an_interim_reading(self) -> None:
        """Against `01b-F01`: Schneider 74.508 -> 69.165 (-53,43 €),
        Weber 34.782 -> 39.433 (+46,51 €). Same building, same money, a
        different tenant paying it."""
        assert 69_165 - 74_508 == -5_343
        assert 39_433 - 34_782 == 4_651
