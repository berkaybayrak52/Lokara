"""R1/R5/K9 at the **engine** boundary — the rule is transcribed, the engine ignores it.

Spec: `docs/03-nk-heating-engines.md` -> "9. Wiring R1/R5/K9 and the Ho/Hu
boundary into the engine", and § 1 (1) / § 4 (H3, H4, H6) / § 5 (R1, R5) of the
Seite-01b transcription. Rule source: `berkay-work/…/01b · Heizkosten- &
CO₂-Verteilung ….md`; the convention K9 is the Rechtsstand-Register row
*"Verteilungsrest (K9)"*, `Konvention` / `verify-before-production`,
**Rechtsstand 07/2026**. It is a house rule and no output may present it as a norm.

**What is RED here and why.** `distribute_cents_half_up` exists in
`packages/domain` with its own passing tests and **zero production callers**:
`heating-engine` still allocates every block with the largest-remainder
`distribute_cents` at all ten of its split sites. So the primitive is right and
nothing uses it. These fixtures are the first callers.

The difference is not cosmetic. Largest-remainder hands the leftover cent to
whichever **renter** happens to have the largest fraction — a transfer between
tenants that nothing on the statement can explain. R1/R5/K9 gives every renter
its own `round_half_up` and puts the `Verteilungsrest` (`Blockbetrag - Σ
Anteile`) on the **owner** row, next to the vacancy share, which is one
printable line (Seite 01 D12).

Not asserted here, because the input shape cannot express it: `01b-F01`'s
verbrauchHz block, where the residual is **-1 ct** (the vacancy segment measured
zero units). `HeatingUnit` carries one reading per unit, not one per tenancy
(§ 9b Abs. 1 needs two), so that case stays where it already lives —
`packages/domain/tests/test_residual_rounding.py`. `docs/03` § 8 records the gap.

⚠️ `08-F01` (the MDL path) and `01b-F01` (self-billing) compute the same building
from different inputs. They are **two data paths** and must never be asserted
against each other. Nothing in this file mixes them; do not "unify" them.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import ClassVar

from lokara_domain import (
    Cents,
    Co2Step,
    Co2Table,
    DegreeDayTable,
    HeatingSplitBounds,
    Occupancy,
    WarmWaterFormula,
    cents,
    distribute_cents,
    distribute_cents_half_up,
    period,
)
from lokara_heating_engine import (
    HeatingInput,
    HeatingResult,
    HeatingRules,
    HeatingUnit,
    WarmWaterInput,
    calculate_heating_statement,
)
from lokara_heating_engine.co2 import split_co2_cost

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
# K3 as it stands in `packages/rules-store` (VDI 2067 Bl. 1, Ausgabe 12/1983,
# Tab. 22), inline so this file pins one rounding rule and not two: a change to
# the table must break the degree-day fixtures, not these.
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
# building, so the shape below is the one the demo path actually runs.
UNITS = (
    HeatingUnit("unit-a", 5000, heat_consumption=Decimal(600), ww_consumption_m3=Decimal(20)),
    HeatingUnit("unit-b", 3000, heat_consumption=Decimal(250), ww_consumption_m3=Decimal(12)),
    HeatingUnit("unit-c", 2000, heat_consumption=Decimal(150), ww_consumption_m3=Decimal(8)),
)
# Unit B's renter leaves 30 Jun -> the flat is vacant Jul-Dec, which is the one
# landlord party and therefore the owner bucket of every block (docs/03 § 9.2).
OCCUPANCIES_WITH_VACANCY = (
    Occupancy("unit-a", "ten-a", period("2025-01-01")),
    Occupancy("unit-b", "ten-b", period("2024-08-01", "2025-07-01")),
    Occupancy("unit-c", "ten-c", period("2023-01-01")),
)
OCCUPANCIES_FULLY_LET = (
    Occupancy("unit-a", "ten-a", period("2025-01-01")),
    Occupancy("unit-b", "ten-b", period("2024-08-01")),
    Occupancy("unit-c", "ten-c", period("2023-01-01")),
)

OWNER_INDEX = 2  # unit-b's landlord party, third in the deterministic party order


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


def _rows(result: HeatingResult) -> list[tuple[str, str | None, int, int, int, int, int]]:
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


def _round_half_up(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _assert_block_follows_r1_r5(
    label: str, pot: Cents, weights: list[Decimal], shares: list[int], owner_index: int
) -> None:
    """The rule itself, applied to the engine's own disclosed Bemessungen.

    Written as a property rather than as a second copy of the golden table so
    that it cannot be satisfied by copying whatever the engine currently emits:
    R1 fixes every renter share, R5 fixes the owner's, and the two together fix
    the block. Largest-remainder cannot satisfy both wherever it disagrees.
    """
    weight_sum = sum(weights, Decimal(0))
    for index, (weight, share) in enumerate(zip(weights, shares, strict=True)):
        if index == owner_index:
            continue
        quota = Decimal(int(pot)) * weight / weight_sum
        assert share == _round_half_up(quota), f"{label}: party {index} is not R1 round_half_up"
    others = sum(share for index, share in enumerate(shares) if index != owner_index)
    assert shares[owner_index] == int(pot) - others, f"{label}: owner does not hold the R5 residual"
    # Non-negotiable, and unchanged by R5: the residual is *inside* the sum.
    assert sum(shares) == int(pot), f"{label}: block does not reconcile"


class TestEveryBlockIsAllocatedByR1R5K9:
    """Heizkosten 2.910,00 €, 20.000 kWh, 40 m³ Warmwasser (Q_ww = 5.000 kWh
    -> 25 %), Grundkosten 30 %. Chosen because all four blocks leave a
    Verteilungsrest, and because it moves cents in **both** directions.

    Against the engine as it stands (largest-remainder), R1/R5/K9 moves four
    cents across three parties:

    | Block   | Party            | today | R1/R5/K9 |
    | ------- | ---------------- | ----- | -------- |
    | grundHz | unit-a           | 32737 | **32738** (its own round_half_up) |
    | grundHz | owner (unit-b)   |  9902 | **9901**  (the residual) |
    | verbrHz | unit-b renter    | 22279 | **22278** (its own round_half_up) |
    | verbrHz | owner (unit-b)   | 15915 | **15916** (the residual) |
    | grundWw | unit-a / owner   | 10912 / 3301 | **10913 / 3300** |
    | verbrWw | unit-a / owner   | 25462 / 7702 | **25463 / 7701** |

    The verbrauchHz row is the one that matters legally: today a **renter** is
    charged a cent that its own share does not produce, because another party's
    fraction ranked lower. Under K9 that cent sits on the Eigentümer row, where
    a single sentence explains it.
    """

    TOTAL = 291_000

    def test_the_golden_table(self) -> None:
        result = _statement(self.TOTAL, OCCUPANCIES_WITH_VACANCY)
        assert _rows(result) == [
            ("unit-a", "ten-a", 32738, 91665, 10913, 25463, 160779),
            ("unit-b", "ten-b", 9741, 22278, 3247, 7576, 42842),
            ("unit-b", None, 9901, 15916, 3300, 7701, 36818),
            ("unit-c", "ten-c", 13095, 22916, 4365, 10185, 50561),
        ]
        assert sum(int(line.total) for line in result.lines) == self.TOTAL
        assert result.total == self.TOTAL

    def test_each_of_the_four_blocks_obeys_r1_and_r5(self) -> None:
        result = _statement(self.TOTAL, OCCUPANCIES_WITH_VACANCY)
        area = [line.base_weight_sqm_days_x100 for line in result.lines]
        heat = [line.heat_consumption_weight for line in result.lines]
        water = [line.ww_consumption_weight_m3 for line in result.lines]
        assert all(w is not None for w in heat) and all(w is not None for w in water)

        _assert_block_follows_r1_r5(
            "grundHz",
            result.heat_base_pot,
            area,
            [int(line.heating_base) for line in result.lines],
            OWNER_INDEX,
        )
        _assert_block_follows_r1_r5(
            "verbrauchHz",
            result.heat_cons_pot,
            [w for w in heat if w is not None],
            [int(line.heating_consumption) for line in result.lines],
            OWNER_INDEX,
        )
        _assert_block_follows_r1_r5(
            "grundWw",
            result.ww_base_pot,
            area,
            [int(line.ww_base) for line in result.lines],
            OWNER_INDEX,
        )
        _assert_block_follows_r1_r5(
            "verbrauchWw",
            result.ww_cons_pot,
            [w for w in water if w is not None],
            [int(line.ww_consumption) for line in result.lines],
            OWNER_INDEX,
        )

    def test_the_same_row_absorbs_the_residual_in_all_four_blocks(self) -> None:
        """K9's justification is that **one** Eigentümer line explains every
        ±ct of the statement. It cannot, if a different row absorbs per block.
        """
        result = _statement(self.TOTAL, OCCUPANCIES_WITH_VACANCY)
        owner = result.lines[OWNER_INDEX]
        assert owner.tenancy_id is None
        assert (owner.unit_id, owner.days) == ("unit-b", 184)  # Jul-Dec vacancy

    def test_the_residual_is_at_most_one_cent_per_block(self) -> None:
        """±1 ct per block is expected and correct (`docs/03` § 1 (1), R5). A
        larger deviation is not a rounding rest but a broken denominator.
        """
        result = _statement(self.TOTAL, OCCUPANCIES_WITH_VACANCY)
        owner = result.lines[OWNER_INDEX]
        area = [line.base_weight_sqm_days_x100 for line in result.lines]
        area_sum = sum(area, Decimal(0))
        for label, pot, share in (
            ("grundHz", result.heat_base_pot, int(owner.heating_base)),
            ("grundWw", result.ww_base_pot, int(owner.ww_base)),
        ):
            own_quota = _round_half_up(Decimal(int(pot)) * area[OWNER_INDEX] / area_sum)
            assert abs(share - own_quota) <= 1, label


class TestABlockWithNoLandlordPartyKeepsLargestRemainder:
    """docs/03 § 9.2 convention 2 — **our** convention, not Berkay's.

    His model has one owner bucket per Liegenschaft, always. Ours derives a
    landlord party from vacancy, so a fully let building has **no owner bucket**
    at all — and the engine may not make a block reconcile by handing the
    residual to a renter, which is the one thing K9 exists to forbid. Until an
    unconditional Eigentümer line exists (`docs/02` + `docs/08` + PDF, its own
    slice), such a block stays on largest-remainder.

    2.999,35 € is picked because every one of the four blocks leaves a cent
    over, so any residual-to-a-tenant reading would visibly move this table.
    """

    TOTAL = 299_935

    def test_the_fully_let_building_does_not_move(self) -> None:
        result = _statement(self.TOTAL, OCCUPANCIES_FULLY_LET)
        assert all(line.tenancy_id is not None for line in result.lines)
        assert _rows(result) == [
            ("unit-a", "ten-a", 33743, 94480, 11248, 26244, 165715),
            ("unit-b", "ten-b", 20245, 39366, 6748, 15747, 82106),
            ("unit-c", "ten-c", 13497, 23620, 4499, 10498, 52114),
        ]
        assert sum(int(line.total) for line in result.lines) == self.TOTAL

    def test_each_block_still_reconciles_to_its_pot(self) -> None:
        result = _statement(self.TOTAL, OCCUPANCIES_FULLY_LET)
        assert sum(int(line.heating_base) for line in result.lines) == int(result.heat_base_pot)
        assert sum(int(line.heating_consumption) for line in result.lines) == int(
            result.heat_cons_pot
        )
        assert sum(int(line.ww_base) for line in result.lines) == int(result.ww_base_pot)
        assert sum(int(line.ww_consumption) for line in result.lines) == int(result.ww_cons_pot)


class TestBerkay01bF26TheOwnerValueIsTheResidualAndNotARoundedQuota:
    """`01b-F26` / E22 — a guard on the oracle, at the primitive level.

    Unit meters sum to 74 m³, the central meter says 78 m³; the distribution
    runs against the **central** denominator, so the 4 m³ nobody's meter saw
    stay with the owner. **The oracle is 4.227 ct, and the reason is that it is
    the `Verteilungsrest` (`Blockbetrag - Σ Anteile`), not a rounded quota.**
    The owner's *own* `round_half_up` would be 4.228 — do not "fix" the oracle
    by recomputing it as a quota. Berkay's table prints 4.228 and his own
    Summenprobe reconciles to 4.227 (`docs/03` § 7 no. 7).

    The trap this class exists to close: largest-remainder — what the engine
    does today — also produces **4.228**, i.e. it coincides with the *printed*
    value his own check contradicts. Anyone verifying the current engine against
    his table would conclude it is right. It is not: it also moves a cent off
    the fourth tenant (20.081 instead of its own 20.082).

    E22's shape is not expressible through `calculate_heating_statement` (the
    engine's warm-water denominator is Σ of the unit meters, never a central
    volume), so this stays a primitive-level assertion until E22 is modelled.
    """

    # Muster / Schneider / Weber / Beispiel / unerfasst
    WEIGHTS: ClassVar[list[Decimal]] = [Decimal(m3) for m3 in (34, 15, 6, 19, 4)]
    BLOCK = 82_440
    OWNER = 4

    def test_the_owner_holds_the_residual(self) -> None:
        shares = [
            int(s)
            for s in distribute_cents_half_up(
                cents(self.BLOCK), self.WEIGHTS, residual_index=self.OWNER
            )
        ]
        assert shares == [35935, 15854, 6342, 20082, 4227]
        assert sum(shares) == self.BLOCK

    def test_what_the_engine_produces_today_differs_on_two_rows(self) -> None:
        largest_remainder = [int(s) for s in distribute_cents(cents(self.BLOCK), self.WEIGHTS)]
        assert largest_remainder == [35935, 15854, 6342, 20081, 4228]
        assert sum(largest_remainder) == self.BLOCK

    def test_the_owners_own_quota_is_not_the_oracle(self) -> None:
        weight_sum = sum(self.WEIGHTS, Decimal(0))
        own_quota = _round_half_up(Decimal(self.BLOCK) * self.WEIGHTS[self.OWNER] / weight_sum)
        assert own_quota == 4228  # the printed figure — and not what K9 assigns
        assert own_quota != 4227


class TestTheCo2SplitRoundsTheLandlordsDeductionHalfUp:
    """docs/03 § 9.3 — `co2.py:166` is a two-way statutory split, so it has **no
    owner bucket**; what the switch to `distribute_cents_half_up` buys there is
    the rounding *direction*, which R6/H2 put on the landlord's **deduction**
    (`co2AbzugVermieterCent = round_half_up(co2Cent × vermieterAnteil/100)`,
    then `umlagefaehigCent = gesamtCent - co2Abzug`).

    **This class is green today and must stay green.** The switch moves no money
    at a two-element split (§ 9.4). It is here because the current code gets the
    direction right only by accident — largest-remainder's tie-break happens to
    prefer index 0 — and swapping the two list entries would silently invert it
    at an exact half cent, in the direction that costs the tenant.
    """

    TABLE: Co2Table = (
        Co2Step(max_intensity_exclusive=Decimal(12), landlord_share_percent=0),
        Co2Step(max_intensity_exclusive=Decimal(17), landlord_share_percent=10),
        Co2Step(max_intensity_exclusive=Decimal(22), landlord_share_percent=20),
        Co2Step(max_intensity_exclusive=Decimal(27), landlord_share_percent=30),
        Co2Step(max_intensity_exclusive=Decimal(32), landlord_share_percent=40),
        Co2Step(max_intensity_exclusive=Decimal(37), landlord_share_percent=50),
        Co2Step(max_intensity_exclusive=Decimal(42), landlord_share_percent=60),
        Co2Step(max_intensity_exclusive=Decimal(47), landlord_share_percent=70),
        Co2Step(max_intensity_exclusive=Decimal(52), landlord_share_percent=80),
        Co2Step(max_intensity_exclusive=None, landlord_share_percent=95),
    )

    def test_half_a_cent_goes_to_the_deduction_not_to_the_renter_side(self) -> None:
        # 3.620 kg / 100 m² -> 36,2 kg/m²/a -> Stufe 32 - < 37 -> Vermieter 50 %.
        # 50 % of 261,81 € is 130,905 € — exactly half a cent.
        result = split_co2_cost(
            total_co2_kg=Decimal(3620),
            co2_cost=cents(26_181),
            heated_area_sqm=Decimal(100),
            table=self.TABLE,
            rechtsstand="Rechtsstand 01/2023",
            billing_period=YEAR_2025,
        )
        assert result.landlord_share_percent == 50
        assert int(result.landlord_amount) == 13091  # round_half_up, R6
        assert int(result.renter_amount) == 13090  # the complement
        assert int(result.landlord_amount) + int(result.renter_amount) == 26_181
