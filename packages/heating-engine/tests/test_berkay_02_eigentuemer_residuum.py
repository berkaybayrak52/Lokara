"""The Eigentümerzeile at the engine boundary — RED, written before the shape exists.

Spec: `docs/02-data-model.md` -> "The Eigentümeranteil is a residual line, not a
party"; `docs/03-nk-heating-engines.md` § 9.2 (which supersedes the two
conventions this file's predecessor asserted); `docs/08` -> "Die
Eigentümerzeile", §§ 1-6. Primary rule text: original Page 01 -> **D0**, **D12**,
**08-F21**, edge cases **E3** / **E17** / **E19**. Numeric oracles:
`09-F07` (his `08-F22`) and `09-F19` (his `08-F21`), re-derived in
`packages/domain/tests/test_berkay_residual_oracles.py`.

**What is RED here and why.** Three things do not exist yet:

1. `OwnerResidual` / `OwnerResidualOrigin` — so this module fails at **import**.
2. `HeatingResult.owner_residual` — the engine has no Eigentümerzeile at all. It
   emits a *landlord party per unit* inside `lines`, derived from the vacancy
   segments, and emits **none** where nothing is vacant.
3. Half-up on a fully-let block — today `_allocate_to_parties` falls back to
   largest-remainder when `_owner_index` is `None` (`docs/03` § 9.2 convention
   2, explicitly rejected by Berkay: *"Euer Largest-Remainder-Vorschlag … soll
   **nicht** verwendet werden."*).

**What is not RED, and must stay that way.** The demo path does not move: the
demo building has a vacancy on `unit-b`, so it has exactly one landlord party
and that party's amount already *is* the residual. `scripts/assert_statement_pdf.py`
and its 776,52 / 554,74 goldens hold across this change. Seven blocks in the
suite move, all fully-let, all by 1 ct, all with the Eigentümerzeile at
**-0,01 €**.

**The rule.** Per block (D12), and for heating in *"allen vier Blöcken in
dieselbe Zeile"* (§ 1.3 Frage 3):

    eigentuemerCent[block] = blockbetragCent[block] - Σ mieteranteilCent[block]

**Rechtsnatur.** § 1.4: *"meine feste Modellregel, keine offene Konvention …
setzt es fest um."* No `verify-before-production` flag on the residual itself.
K9 keeps its flag for what remains of it — the `round_half_up` direction.
"""

from dataclasses import fields
from decimal import ROUND_HALF_UP, Decimal
from typing import ClassVar

from lokara_domain import (
    DegreeDayTable,
    HeatingSplitBounds,
    Occupancy,
    WarmWaterFormula,
    cents,
    period,
)
from lokara_heating_engine import (
    HeatingInput,
    HeatingResult,
    HeatingRules,
    HeatingUnit,
    OwnerResidual,
    WarmWaterInput,
    calculate_heating_statement,
)

YEAR_2025 = period("2025-01-01", "2026-01-01")

SPLIT_BOUNDS = HeatingSplitBounds(
    min_consumption_share=Decimal("0.5"), max_consumption_share=Decimal("0.7")
)
WW_FORMULA = WarmWaterFormula(
    factor_kwh_per_m3_kelvin=Decimal("2.5"),
    hot_temp_c=Decimal(60),
    cold_temp_c=Decimal(10),
    area_fallback_kwh_per_sqm_year=Decimal(32),
)
# K3 as it stands in `packages/rules-store`, inline for the same reason as in
# `test_berkay_01b_residual_wiring.py`: a change to the table must break the
# degree-day fixtures, not these.
DEGREE_DAYS = DegreeDayTable(
    tenth_promille_by_month=(1700, 1500, 1300, 800, 400, 133, 133, 134, 300, 800, 1200, 1600)
)
RULES = HeatingRules(
    consumption_share=Decimal("0.7"),
    split_bounds=SPLIT_BOUNDS,
    warm_water_formula=WW_FORMULA,
    degree_days=DEGREE_DAYS,
)

# 50 / 30 / 20 m², one warm-water and one heat meter each — the canonical demo
# composition, so these run the shape the demo path actually runs.
UNITS = (
    HeatingUnit("unit-a", 5000, heat_consumption=Decimal(600), ww_consumption_m3=Decimal(20)),
    HeatingUnit("unit-b", 3000, heat_consumption=Decimal(250), ww_consumption_m3=Decimal(12)),
    HeatingUnit("unit-c", 2000, heat_consumption=Decimal(150), ww_consumption_m3=Decimal(8)),
)
FULLY_LET = (
    Occupancy("unit-a", "ten-a", period("2025-01-01")),
    Occupancy("unit-b", "ten-b", period("2024-08-01")),
    Occupancy("unit-c", "ten-c", period("2023-01-01")),
)
# Unit B's renter leaves 30.06. -> vacant Jul-Dec (184 days).
ONE_VACANT = (
    Occupancy("unit-a", "ten-a", period("2025-01-01")),
    Occupancy("unit-b", "ten-b", period("2024-08-01", "2025-07-01")),
    Occupancy("unit-c", "ten-c", period("2023-01-01")),
)
# ... and unit C's leaves 30.09. -> vacant Oct-Dec (92 days). Two landlord
# parties today; one Eigentümerzeile under the model.
TWO_VACANT = (
    Occupancy("unit-a", "ten-a", period("2025-01-01")),
    Occupancy("unit-b", "ten-b", period("2024-08-01", "2025-07-01")),
    Occupancy("unit-c", "ten-c", period("2023-01-01", "2025-10-01")),
)

Row = tuple[str, str | None, int, int, int, int, int]


def _statement(total_cost: int, occupancies: tuple[Occupancy, ...]) -> HeatingResult:
    return calculate_heating_statement(
        HeatingInput(
            billing_period=YEAR_2025,
            total_cost=cents(total_cost),
            total_energy_kwh=Decimal(20000),
            units=UNITS,
            occupancies=occupancies,
            rules=RULES,
            warm_water=WarmWaterInput(volume_m3=Decimal(40)),
        )
    )


def _rows(result: HeatingResult) -> list[Row]:
    return [
        (
            line.unit_id,
            line.tenancy_id,
            int(line.heating_base),
            int(line.heating_consumption),
            int(line.ww_base),
            int(line.ww_consumption),
            int(line.total),
        )
        for line in result.lines
    ]


def _owner_columns(owner: OwnerResidual) -> tuple[int, int, int, int, int]:
    return (
        int(owner.heating_base),
        int(owner.heating_consumption),
        int(owner.ww_base),
        int(owner.ww_consumption),
        int(owner.total),
    )


def _round_half_up(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _assert_block_is_a_residual(
    label: str, pot: int, weights: list[Decimal], renter_shares: list[int], owner_share: int
) -> None:
    """The rule as a property, not as a second copy of the golden table.

    Written this way so it cannot be satisfied by pasting whatever the engine
    emits: every renter share must be its own `round_half_up` against a
    denominator that **includes** the owner's Bemessung (D0), and the owner must
    be exactly what is left. Largest-remainder cannot satisfy both wherever they
    disagree.
    """
    denominator = sum(weights, Decimal(0))
    for index, (weight, share) in enumerate(zip(weights, renter_shares, strict=True)):
        quota = Decimal(pot) * weight / denominator
        assert share == _round_half_up(quota), f"{label}: renter {index} is not R1 round_half_up"
    assert owner_share == pot - sum(renter_shares), f"{label}: owner is not the residual"
    assert sum(renter_shares) + owner_share == pot, f"{label}: block does not reconcile"


class TestAFullyLetBuildingStillHasAnEigentuemerzeile:
    """§ 1.3 Frage 1 — *"Existiert die Eigentümerzeile immer? → **Ja.** Auch bei
    0,00 €, auch ohne Leerstand, auch ohne Eigennutzung."*

    **The case the whole row exists for, and the one this repo had none of.**
    Today a fully-let building produces no landlord party, so
    `_owner_index` returns `None` and the block falls back to largest-remainder
    (`docs/03` § 9.2 convention 2 — rejected). Under the model every renter gets
    its own `round_half_up` and the rest lands on the Eigentümerzeile.

    2.999,35 € is the total the superseded
    `TestABlockWithNoLandlordPartyKeepsLargestRemainder` used, kept on purpose so
    the two tables can be diffed: every one of the four blocks leaves a cent
    over, and each one moves.

    | Block   | today (largest-remainder) | under the model |
    | ------- | ------------------------- | --------------- |
    | grundHz | 33743 / 20245 / 13497     | 33743 / **20246** / 13497 · owner **-1** |
    | verbrHz | 94480 / 39366 / 23620     | 94480 / **39367** / 23620 · owner **-1** |
    | grundWw | 11248 /  6748 /  4499     | 11248 /  **6749** /  4499 · owner **-1** |
    | verbrWw | 26244 / 15747 / 10498     | **26245** / 15747 / 10498 · owner **-1** |
    """

    TOTAL = 299_935

    def test_the_golden_table_and_the_owner_row(self) -> None:
        result = _statement(self.TOTAL, FULLY_LET)
        assert _rows(result) == [
            ("unit-a", "ten-a", 33743, 94480, 11248, 26245, 165716),
            ("unit-b", "ten-b", 20246, 39367, 6749, 15747, 82109),
            ("unit-c", "ten-c", 13497, 23620, 4499, 10498, 52114),
        ]
        assert _owner_columns(result.owner_residual) == (-1, -1, -1, -1, -4)

    def test_the_lines_contain_no_landlord_party_at_all(self) -> None:
        """`tenancy_id is None` no longer occurs: the Eigentümer is not a party,
        so there is no party slot an owner share could be written into."""
        result = _statement(self.TOTAL, FULLY_LET)
        assert all(line.tenancy_id is not None for line in result.lines)
        assert len(result.lines) == 3

    def test_a_negative_residual_is_lawful_and_is_not_clamped(self) -> None:
        """`round_half_up` biases the renter shares upward, so Σ Mieter exceeds
        the pot by a cent per block and the owner absorbs it with a minus sign.
        -0,04 € across four blocks. Clamping it to 0 would break the control
        sum, which is the one thing this line exists to keep true (`CLAUDE.md`
        DoD 4 allows the negative explicitly).
        """
        owner = _statement(self.TOTAL, FULLY_LET).owner_residual
        assert int(owner.total) == -4
        assert int(owner.total) < 0

    def test_it_has_no_origins_and_no_bemessung(self) -> None:
        """Block (a) is empty — nothing stood empty — so the whole residual is
        block (c). `docs/08` § 2: with no vacancy and no self-use the Bemessung
        column stays **empty**, which is `None` and not `0`; a `0` would print
        as a Bemessung of zero and imply a base that does not exist.
        """
        owner = _statement(self.TOTAL, FULLY_LET).owner_residual
        assert owner.origins == ()
        assert int(owner.rounding_difference) == int(owner.total) == -4
        assert owner.base_weight_sqm_days_x100 is None
        assert owner.heat_consumption_weight is None
        assert owner.ww_consumption_weight_m3 is None

    def test_every_block_obeys_the_residual_rule(self) -> None:
        result = _statement(self.TOTAL, FULLY_LET)
        owner = result.owner_residual
        area = [line.base_weight_sqm_days_x100 for line in result.lines]
        heat = [line.heat_consumption_weight for line in result.lines]
        water = [line.ww_consumption_weight_m3 for line in result.lines]
        assert all(w is not None for w in heat) and all(w is not None for w in water)
        _assert_block_is_a_residual(
            "grundHz",
            int(result.heat_base_pot),
            area,
            [int(line.heating_base) for line in result.lines],
            int(owner.heating_base),
        )
        _assert_block_is_a_residual(
            "verbrauchHz",
            int(result.heat_cons_pot),
            [w for w in heat if w is not None],
            [int(line.heating_consumption) for line in result.lines],
            int(owner.heating_consumption),
        )
        _assert_block_is_a_residual(
            "grundWw",
            int(result.ww_base_pot),
            area,
            [int(line.ww_base) for line in result.lines],
            int(owner.ww_base),
        )
        _assert_block_is_a_residual(
            "verbrauchWw",
            int(result.ww_cons_pot),
            [w for w in water if w is not None],
            [int(line.ww_consumption) for line in result.lines],
            int(owner.ww_consumption),
        )


class TestTheEigentuemerzeileAtExactlyZero:
    """The `0,00 €` case, explicitly — his `09-F19` rows for Wasserversorgung,
    Entwässerung and Heizkosten, reached through the heating engine.

    2.400,00 € on the fully-let composition, chosen because every block then
    divides exactly and the residual is genuinely zero in all four:

        Gesamtkosten            240.000
        Q_ww = 40 m³ × 2,5 × 50 K = 5.000 kWh von 20.000  -> 25 %
        ww_pot   = 240000 × 25 %  =  60.000 · heating_pot = 180.000
        grundHz  = 180000 × 30 %  =  54.000 · verbrauchHz = 126.000
        grundWw  =  60000 × 30 %  =  18.000 · verbrauchWw =  42.000
        50/30/20 and 600/250/150 both divide those exactly -> Σ Mieter == pot

    **Zero here means zero, not absent.** The row still renders, and its four
    columns each print `0,00 €` (`docs/08` § 1).
    """

    TOTAL = 240_000

    def test_every_renter_share_is_exact_and_the_residual_is_zero(self) -> None:
        result = _statement(self.TOTAL, FULLY_LET)
        assert _rows(result) == [
            ("unit-a", "ten-a", 27000, 75600, 9000, 21000, 132600),
            ("unit-b", "ten-b", 16200, 31500, 5400, 12600, 65700),
            ("unit-c", "ten-c", 10800, 18900, 3600, 8400, 41700),
        ]
        assert _owner_columns(result.owner_residual) == (0, 0, 0, 0, 0)

    def test_the_row_exists_even_though_every_column_is_zero(self) -> None:
        """The whole point of § 1.3 Frage 1: a suppressed zero row and an
        omitted row are indistinguishable on paper, and only one of them is
        honest. `owner_residual` is a required field, never `None`.
        """
        owner = _statement(self.TOTAL, FULLY_LET).owner_residual
        assert owner is not None
        assert isinstance(owner, OwnerResidual)
        assert int(owner.total) == 0
        assert int(owner.rounding_difference) == 0

    def test_the_pots_are_the_ones_the_docstring_derives(self) -> None:
        """Guards the oracle itself: if the § 9 separation or the §§ 7/8 ratio
        ever moved, the four zeros above would be an accident rather than the
        exact division this fixture is built on."""
        result = _statement(self.TOTAL, FULLY_LET)
        assert int(result.ww_pot) == 60_000
        assert int(result.heating_pot) == 180_000
        assert int(result.heat_base_pot) == 54_000
        assert int(result.heat_cons_pot) == 126_000
        assert int(result.ww_base_pot) == 18_000
        assert int(result.ww_cons_pot) == 42_000


class TestTheResidualBeatsTheSeparatelyComputedVacancyShare:
    """D12: *"ALWAYS as a residual, NEVER computed separately"* — with a case
    where the two are different numbers, so the rule has a consequence.

    The oracle is Berkay's own arithmetic in `09-F07` / his `08-F22`
    (`packages/domain/tests/test_berkay_residual_oracles.py`): renter shares
    round to Σ 60142, the residual is **1858**, and the separately computed
    vacancy share `62000 × 62 / 2068 = 1858,80` rounds to **1859**. *"Gerechnet
    wird 1858. Residuum gewinnt."*

    Here the same collision at the engine, on one vacant unit and 2.910,00 €:

    | Block   | residual | its own round_half_up | Δ |
    | ------- | -------- | --------------------- | - |
    | grundHz |  **9901** |  9902 | -1 |
    | verbrHz | **15916** | 15915 | +1 |
    | grundWw |  **3300** |  3301 | -1 |
    | verbrWw |  **7701** |  7702 | -1 |
    | total   | **36818** | 36820 | **-2**  -> block (c) |

    The right-hand column is what block **(a)** of the Leerstandsaufstellung
    carries per unit; the left-hand column is what the Gesamtübersicht prints.
    Their difference is block **(c)** — the same structure as his 17.531 vs
    17.536 in `08-F21`, at a smaller scale.
    """

    TOTAL = 291_000
    OWNER_COLUMNS = (9901, 15916, 3300, 7701, 36818)
    ORIGIN_COLUMNS = (9902, 15915, 3301, 7702, 36820)

    def test_the_printed_amount_is_the_residual(self) -> None:
        result = _statement(self.TOTAL, ONE_VACANT)
        assert _owner_columns(result.owner_residual) == self.OWNER_COLUMNS

    def test_block_a_carries_the_separately_computed_figure_instead(self) -> None:
        owner = _statement(self.TOTAL, ONE_VACANT).owner_residual
        assert len(owner.origins) == 1
        origin = owner.origins[0]
        assert origin.unit_id == "unit-b"
        assert (
            int(origin.heating_base),
            int(origin.heating_consumption),
            int(origin.ww_base),
            int(origin.ww_consumption),
            int(origin.total),
        ) == self.ORIGIN_COLUMNS

    def test_block_c_is_the_difference_and_belongs_to_no_unit(self) -> None:
        owner = _statement(self.TOTAL, ONE_VACANT).owner_residual
        origins_total = sum(int(origin.total) for origin in owner.origins)
        assert origins_total == 36_820
        assert int(owner.total) == 36_818
        assert int(owner.rounding_difference) == int(owner.total) - origins_total == -2

    def test_the_renter_lines_do_not_move(self) -> None:
        """The collapse is a shape change here, not a money change: with exactly
        one vacant unit the engine's landlord party already held the residual.
        This is why the demo path does not move, and the assertion is here so a
        future change that *does* move it is caught.
        """
        result = _statement(self.TOTAL, ONE_VACANT)
        assert _rows(result) == [
            ("unit-a", "ten-a", 32738, 91665, 10913, 25463, 160779),
            ("unit-b", "ten-b", 9741, 22278, 3247, 7576, 42842),
            ("unit-c", "ten-c", 13095, 22916, 4365, 10185, 50561),
        ]

    def test_the_bemessung_is_the_fiktivbelegung_of_the_empty_unit(self) -> None:
        """`docs/08` § 2 — with vacancy the row carries the Fiktivbelegung (D0)
        as Bemessung, and only that. 30,00 m² × 184 Tage = 5.520 m²·Tage,
        carried ×100 like every other weight in the engine."""
        owner = _statement(self.TOTAL, ONE_VACANT).owner_residual
        assert owner.base_weight_sqm_days_x100 == Decimal(3000 * 184)
        assert owner.origins[0].days == 184


class TestSeveralVacantUnitsCollapseIntoOneLine:
    """§ 1.2: *"Bitte kollabiert die aus Belegung abgeleiteten Vermieterparteien
    zu einem einzigen Liegenschafts-Residuum pro Kostenart."* And § 1.3 Frage 3:
    *"in allen vier Blöcken in dieselbe Zeile."*

    Unit B vacant Jul-Dec (184 Tage), unit C vacant Oct-Dec (92 Tage). Today the
    engine emits **two** landlord rows and § 9.2 convention 1 decided which of
    them absorbed the rest — the convention Berkay called unnecessary. Under the
    model there is one row, and the per-unit figures move to block (a):

        Eigentümerzeile  13202 / 24166 /  4400 / 10268  = 52036   (the residual)
        (a) unit-b        9902 / 15915 /  3301 /  7702  = 36820
        (a) unit-c        3301 /  8250 /  1100 /  2567  = 15218
                                                 Σ (a)  = 52038
        (c) Rundungsdifferenz                           =    -2

    The Leerstandsaufstellung still itemises (a) per empty unit, because the
    landlord needs it per object for Anlage V (§ 1.4) — *"Aggregation im
    Display, Herkunft in den Daten."*
    """

    TOTAL = 291_000

    def test_there_is_exactly_one_owner_row_across_all_four_blocks(self) -> None:
        result = _statement(self.TOTAL, TWO_VACANT)
        assert all(line.tenancy_id is not None for line in result.lines)
        assert len(result.lines) == 3
        assert _owner_columns(result.owner_residual) == (13202, 24166, 4400, 10268, 52036)

    def test_the_per_unit_origin_is_still_retrievable(self) -> None:
        owner = _statement(self.TOTAL, TWO_VACANT).owner_residual
        assert [origin.unit_id for origin in owner.origins] == ["unit-b", "unit-c"]
        assert [int(origin.total) for origin in owner.origins] == [36820, 15218]
        assert [origin.days for origin in owner.origins] == [184, 92]

    def test_block_c_is_non_zero_precisely_because_a_is_itemised(self) -> None:
        """With **one** empty unit his `08-F21` prints `(c) 0,00`, because the
        per-Kostenart residual column already *is* that unit's (a) figure. With
        more than one, (a) has to be computed per unit and (c) picks up the
        drift. Both readings are the same definition: `(c) = Residuum - Σ (a)`
        (`docs/03` § 7 item 12).
        """
        owner = _statement(self.TOTAL, TWO_VACANT).owner_residual
        origins_total = sum(int(origin.total) for origin in owner.origins)
        assert origins_total == 52_038
        assert int(owner.total) == 52_036
        assert int(owner.rounding_difference) == -2

    def test_the_bemessung_aggregates_over_both_empty_units(self) -> None:
        """30,00 m² × 184 Tage + 20,00 m² × 92 Tage = 7.360 m²·Tage."""
        owner = _statement(self.TOTAL, TWO_VACANT).owner_residual
        assert owner.base_weight_sqm_days_x100 == Decimal(3000 * 184 + 2000 * 92)
        assert owner.base_weight_sqm_days_x100 == sum(
            (origin.base_weight_sqm_days_x100 for origin in owner.origins), Decimal(0)
        )

    def test_the_consumption_bemessungen_aggregate_the_same_way(self) -> None:
        owner = _statement(self.TOTAL, TWO_VACANT).owner_residual
        heat = [origin.heat_consumption_weight for origin in owner.origins]
        water = [origin.ww_consumption_weight_m3 for origin in owner.origins]
        assert all(w is not None for w in heat) and all(w is not None for w in water)
        heat_sum = sum((w for w in heat if w is not None), Decimal(0))
        water_sum = sum((w for w in water if w is not None), Decimal(0))
        assert owner.heat_consumption_weight == heat_sum
        assert owner.ww_consumption_weight_m3 == water_sum


class TestTheControlSumClosesInEveryComposition:
    """*"Σ umgelegt + Eigentümeranteil = Gesamtkosten"* — § 1.1, and his self-check
    no. 1 at the object level (`10.550,69 + 175,31 = 10.726,00`).

    Asserted per block **and** in total, over all three compositions, because a
    residual that only reconciles in the aggregate would hide a block where the
    rest went to the wrong place. `sum(shares) == input_total` in every
    allocation test — `CLAUDE.md`, unchanged by the model.
    """

    CASES: ClassVar[tuple[tuple[str, int, tuple[Occupancy, ...]], ...]] = (
        ("fully let", 299_935, FULLY_LET),
        ("fully let, exact", 240_000, FULLY_LET),
        ("one vacant unit", 291_000, ONE_VACANT),
        ("two vacant units", 291_000, TWO_VACANT),
    )

    def test_each_block_reconciles_to_its_pot(self) -> None:
        for label, total, occupancies in self.CASES:
            result = _statement(total, occupancies)
            owner = result.owner_residual
            for name, pot, shares, owner_share in (
                (
                    "grundHz",
                    int(result.heat_base_pot),
                    [int(line.heating_base) for line in result.lines],
                    int(owner.heating_base),
                ),
                (
                    "verbrauchHz",
                    int(result.heat_cons_pot),
                    [int(line.heating_consumption) for line in result.lines],
                    int(owner.heating_consumption),
                ),
                (
                    "grundWw",
                    int(result.ww_base_pot),
                    [int(line.ww_base) for line in result.lines],
                    int(owner.ww_base),
                ),
                (
                    "verbrauchWw",
                    int(result.ww_cons_pot),
                    [int(line.ww_consumption) for line in result.lines],
                    int(owner.ww_consumption),
                ),
            ):
                assert sum(shares) + owner_share == pot, f"{label} / {name}"

    def test_the_object_total_reconciles(self) -> None:
        for label, total, occupancies in self.CASES:
            result = _statement(total, occupancies)
            renters = sum(int(line.total) for line in result.lines)
            assert renters + int(result.owner_residual.total) == total, label
            assert int(result.total) == total, label

    def test_the_owner_total_is_the_sum_of_its_own_four_columns(self) -> None:
        for label, total, occupancies in self.CASES:
            owner = _statement(total, occupancies).owner_residual
            columns = (
                int(owner.heating_base)
                + int(owner.heating_consumption)
                + int(owner.ww_base)
                + int(owner.ww_consumption)
            )
            assert columns == int(owner.total), label


class TestNoQuotaIsEmittedOnTheEigentuemerzeile:
    """§ 1.3 Frage 2, blockquote: *"Druckt in der Eigentümerzeile **keine**
    Quote/Prozentzahl. Eine gedruckte Quote würde eine Verteilungsbasis
    suggerieren, die es nicht gibt — der Betrag ist ein Rest, keine Quote."*

    Enforced by **shape**, not by discipline: if the result type has no
    percentage field, a renderer cannot print one, and no later reviewer has to
    remember the rule. This is the same argument the `Saldo` vocabulary ban uses
    in `docs/08`.
    """

    FORBIDDEN: ClassVar[tuple[str, ...]] = (
        "quote",
        "percent",
        "prozent",
        "share_percent",
        "ratio",
        "promille",
        "permille",
    )

    def test_the_owner_residual_type_has_no_quota_field(self) -> None:
        names = {field.name.lower() for field in fields(OwnerResidual)}
        for forbidden in self.FORBIDDEN:
            assert not any(forbidden in name for name in names), (
                f"OwnerResidual exposes a quota-like field matching {forbidden!r}: {sorted(names)}"
            )

    def test_the_amount_cannot_be_reproduced_from_the_bemessung(self) -> None:
        """The positive statement behind the prohibition: even where the
        Fiktivbelegung *is* printed, `Bemessung × Quote` does not give the
        printed amount. On the grundHz block of the one-vacant case the quota
        route gives 9902 and the row prints 9901 — which is exactly why a
        printed percentage would be misleading rather than merely redundant.
        """
        result = _statement(291_000, ONE_VACANT)
        owner = result.owner_residual
        assert owner.base_weight_sqm_days_x100 is not None
        denominator = sum(
            (line.base_weight_sqm_days_x100 for line in result.lines),
            owner.base_weight_sqm_days_x100,
        )
        quota_route = _round_half_up(
            Decimal(int(result.heat_base_pot)) * owner.base_weight_sqm_days_x100 / denominator
        )
        assert quota_route == 9902
        assert int(owner.heating_base) == 9901
        assert quota_route != int(owner.heating_base)
