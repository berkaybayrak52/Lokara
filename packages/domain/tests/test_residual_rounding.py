"""R1/R5/K9 - `round_half_up` per share, `Verteilungsrest` to the owner bucket.

Spec: `docs/03-nk-heating-engines.md` -> "Seite 01b … (1) Rounding" and
"Rounding & reconciliation". Source of the rule and of every expected cent:
`berkay-work/…/01b · Heizkosten- & CO₂-Verteilung ….md` § 4 (R1, R5) and § 6
(`01b-F01`, `01b-F26`), plus the Rechtsstand-Register row "Verteilungsrest (K9)".

**These fixtures are written before the implementation exists.** They fail today
with `ImportError: distribute_cents_half_up` - that is the point.

Why a second primitive rather than changing `distribute_cents`: largest-remainder
is still a correct allocation and still has callers. What changes is how a
*Blockbetrag* is allocated **to parties** - there, a leftover cent may not be
handed to whichever renter happens to have the largest fraction, because nothing
on the statement can explain that transfer. It goes to the owner, next to the
vacancy share, which is one printable line (K9 / Seite 01 D12).

K9 is `Konvention` / `verify-before-production`. The register records
*"keine - reine Hauskonvention. Recherche 27.07.2026: keine externe Quelle
vorhanden"*. It is a house rule, and no output may present it as a norm.
"""

from collections.abc import Sequence
from decimal import Decimal
from typing import ClassVar

import pytest
from lokara_domain import cents, distribute_cents
from lokara_domain.money import distribute_cents_half_up


def _d(*values: int | str) -> list[Decimal]:
    return [Decimal(v) for v in values]


def _shares(total: int, weights: Sequence[Decimal], owner: int) -> list[int]:
    return [int(s) for s in distribute_cents_half_up(cents(total), weights, residual_index=owner)]


class TestTheCanonicalGarbageFixtureDoesNotMove:
    """VERIFIED BY THE LEAD, and pinned here so the claim is mechanical.

    `docs/03` -> canonical €1.200 example, `CLAUDE.md` definition of done item 3.
    Unit A 50 m² x 365 d, Unit B renter 30 m² x 181 d, Unit B **vacant**
    30 m² x 184 d (-> landlord), Unit C 20 m² x 365 d.

    The whole R1/R5/K9 change turns on this fixture not moving. It does not: the
    quotas round the same way under both methods and the residual is exactly 0.
    """

    WEIGHTS: ClassVar[list[Decimal]] = _d(18250, 5430, 5520, 7300)  # m²·days
    EXPECTED: ClassVar[list[int]] = [60000, 17852, 18148, 24000]  # 600,00/178,52/181,48/240,00
    OWNER = 2  # the vacant half-year of unit B

    def test_half_up_with_residual_reproduces_the_canonical_shares(self) -> None:
        assert _shares(120_000, self.WEIGHTS, self.OWNER) == self.EXPECTED
        assert sum(self.EXPECTED) == 120_000

    def test_both_methods_agree_here_so_the_change_did_not_move_it(self) -> None:
        largest_remainder = [int(s) for s in distribute_cents(cents(120_000), self.WEIGHTS)]
        assert largest_remainder == _shares(120_000, self.WEIGHTS, self.OWNER) == self.EXPECTED

    def test_the_residual_is_exactly_zero(self) -> None:
        """The owner row is its own exact quota, not a corrected one - so nobody
        can claim the vacancy share of 181,48 € was bent to make the sum work."""
        assert _shares(120_000, self.WEIGHTS, self.OWNER)[self.OWNER] == 18148


class TestBerkay01bF01Blocks:
    """`01b-F01` - the reference object of Seite 01b, block by block.

    Musterstraße 12, 01.01.-31.12.2025 (365 d). WE-01 62 m² Muster 365 d ·
    WE-02 74 m² Schneider 212 d / **Leerstand August 31 d** / Weber 122 d ·
    WE-03 58 m² Beispiel 365 d. `nM2Tage` = 70.810 **including** the vacancy.

    The owner index is the vacancy row in every block. Berkay's Summenprobe:
    334.933 ct auf die Mieter + 3.285 ct Eigentuemer = 338.218 ct umlagefaehig.
    """

    # m²·days: Muster / Schneider / Weber / Beispiel / Leerstand
    M2_DAYS: ClassVar[list[Decimal]] = _d(22630, 15688, 9028, 21170, 2294)
    OWNER = 4

    def test_m2_days_denominator_includes_the_vacancy(self) -> None:
        """K2: the denominator is object-level and carries the vacancy, which is
        what makes the vacancy fall out to the owner automatically (E23)."""
        assert sum(self.M2_DAYS) == Decimal(70810)

    def test_grund_heizung_block(self) -> None:
        """grundHz 66.134 ct. The owner's own quota is 2.143 ct; one cent is
        absorbed as Verteilungsrest, so the owner row prints 2.142."""
        shares = _shares(66_134, self.M2_DAYS, self.OWNER)
        assert shares == [21136, 14652, 8432, 19772, 2142]
        assert sum(shares) == 66_134

    def test_grund_warmwasser_block(self) -> None:
        """grundWw 35.332 ct - same key, same absorbed cent (exact quota 1.145)."""
        shares = _shares(35_332, self.M2_DAYS, self.OWNER)
        assert shares == [11292, 7828, 4505, 10563, 1144]
        assert sum(shares) == 35_332

    def test_verbrauch_heizung_block_leaves_the_owner_one_cent_negative(self) -> None:
        """verbrauchHz 154.312 ct over HKV units 4.100 / 2.520 / 1.080 / 3.050.

        The vacancy segment measured **zero** units (§ 9b Abs. 1: readings at
        Auszug *and* Einzug), so its weight is 0 - and the block overshoots by
        one cent, which lands on the owner as minus 1. A residual rule that
        could not go negative would have to push that cent onto a tenant.
        """
        shares = _shares(154_312, _d(4100, 2520, 1080, 3050, 0), self.OWNER)
        assert shares == [58854, 36174, 15503, 43782, -1]
        assert sum(shares) == 154_312

    def test_verbrauch_warmwasser_block(self) -> None:
        """verbrauchWw 82.440 ct over m³ 34 / 15 / 6 / 23, vacancy 0."""
        shares = _shares(82_440, _d(34, 15, 6, 23, 0), self.OWNER)
        assert shares == [35935, 15854, 6342, 24309, 0]
        assert sum(shares) == 82_440

    def test_the_four_blocks_reconcile_to_umlagefaehig(self) -> None:
        """Berkay's Summenprobe, as one assertion.

        338.218 ct umlagefaehig = 350.600 ct Gesamtkosten minus 12.382 ct
        CO₂-Vermieteranteil (H2, `01b-F01`).
        """
        blocks = (
            (66_134, self.M2_DAYS),
            (35_332, self.M2_DAYS),
            (154_312, _d(4100, 2520, 1080, 3050, 0)),
            (82_440, _d(34, 15, 6, 23, 0)),
        )
        per_party = [0, 0, 0, 0, 0]
        for total, weights in blocks:
            for index, share in enumerate(_shares(total, weights, self.OWNER)):
                per_party[index] += share
        assert per_party == [127217, 74508, 34782, 98426, 3285]
        assert sum(per_party) == 338_218
        assert sum(per_party[:4]) == 334_933


class TestBerkay01bF26TheUncapturedWarmWaterStaysWithTheOwner:
    """`01b-F26` / E22 - unit meters sum to 74 m³, the central meter says 78 m³.

    The distribution runs against the **central** denominator 78, so the 4 m³
    nobody's meter saw stay with the owner (4.227 ct = 42,27 €). Dividing by 74
    instead would push 42,27 € of unmeasured warm water silently onto the
    tenants - the whole point of the fixture.

    Berkay's table prints 4.228 (the owner row's own `round_half_up`); his
    Summenprobe reconciles to 4.227, the residual-derived value, which is what
    K9 actually produces. Recorded as a presentation inconsistency in
    `docs/03` § 7; the fixture asserts the value his checks add up to.
    """

    def test_the_gap_lands_on_the_owner_and_the_tenants_are_untouched(self) -> None:
        # Muster / Schneider / Weber / Beispiel / unerfasst
        shares = _shares(82_440, _d(34, 15, 6, 19, 4), owner=4)
        assert shares == [35935, 15854, 6342, 20082, 4227]
        assert sum(shares) == 82_440


class TestTheResidualPrimitiveItself:
    def test_every_non_owner_share_is_round_half_up_of_its_own_quota(self) -> None:
        """R1: rounded once, at assignment. 100 ct over 3 equal parts is
        33,333… each -> 33 / 33 / 34 by residual, not by fractional ranking."""
        assert _shares(100, _d(1, 1, 1), owner=2) == [33, 33, 34]

    def test_the_residual_can_be_negative(self) -> None:
        """Two shares of 0,5 ct each round **up**, so the block overshoots and
        the owner absorbs a negative Verteilungsrest. R5 working, not a defect
        (`01b-F01` verbrauchHz)."""
        shares = _shares(1, _d(1, 1, 0), owner=2)
        assert shares == [1, 1, -1]
        assert sum(shares) == 1

    def test_sum_always_reconciles_to_the_input_total(self) -> None:
        """The non-negotiable half of the old rule (`docs/03`): the residual is
        *inside* the sum, never an exception to it."""
        for total in (1, 7, 99, 12_345, 338_218):
            assert sum(_shares(total, TestBerkay01bF01Blocks.M2_DAYS, owner=4)) == total

    def test_rejects_a_residual_index_out_of_range(self) -> None:
        with pytest.raises(ValueError):
            distribute_cents_half_up(cents(100), _d(1, 1), residual_index=2)

    def test_rejects_negative_and_non_finite_weights(self) -> None:
        with pytest.raises(ValueError):
            distribute_cents_half_up(cents(100), _d(1, -1), residual_index=0)
        with pytest.raises(ValueError):
            distribute_cents_half_up(cents(100), [Decimal("NaN"), Decimal(1)], residual_index=0)

    def test_rejects_a_zero_weight_sum(self) -> None:
        with pytest.raises(ValueError):
            distribute_cents_half_up(cents(100), _d(0, 0), residual_index=0)


class TestATwoElementSplitIsTheSameAllocationUnderBothMethods:
    """`docs/03` § 9.4 — the load-bearing fact behind four of the ten wiring
    decisions, pinned rather than asserted in prose.

    Four of the heating engine's split sites are two-element **complement**
    splits, not allocations across parties: §§ 7/8 Grund/Verbrauch (H4), the § 9
    Warmwasser separation (H3) and the CO₂ Vermieter/Mieter deduction (H2/R6).
    For those, largest-remainder and `round_half_up`-on-index-0-plus-complement
    are the *same* allocation: the two exact quotas sum to the total, so their
    fractional parts sum to 1, so the single leftover cent goes to the element
    whose fraction exceeds a half — which is what rounding that element half up
    does — and at exactly a half the tie-break picks index 0, i.e. half **up**
    again.

    Consequence, and the reason this class exists: those four sites can move no
    money, so **no fixture may claim they do**, and the absence of a RED test for
    them is not an oversight. What the switch buys there is that the rounded side
    is named by the formula instead of decided by argument order.
    """

    # The shapes those four sites actually pass: a statutory percentage pair, the
    # § 7 Abs. 1 Grundkostenanteil, and a § 9 energy split with a fractional quota.
    WEIGHT_PAIRS: ClassVar[list[list[Decimal]]] = [
        _d(30, 70),
        _d(50, 50),
        _d(60, 40),
        _d(95, 5),
        _d(0, 100),
        [Decimal("0.3"), Decimal("0.7")],
        [Decimal(5000), Decimal(15000)],
        [Decimal("4877.5"), Decimal("15122.5")],
        [Decimal(1), Decimal(3)],
    ]

    def test_the_two_methods_agree_on_every_total(self) -> None:
        for weights in self.WEIGHT_PAIRS:
            for total in range(0, 2001):
                largest_remainder = [int(s) for s in distribute_cents(cents(total), weights)]
                half_up = [
                    int(s)
                    for s in distribute_cents_half_up(cents(total), weights, residual_index=1)
                ]
                assert largest_remainder == half_up, (weights, total)
                assert sum(half_up) == total

    def test_at_exactly_half_a_cent_the_first_element_rounds_up(self) -> None:
        """The direction R6 fixes for the CO₂ deduction (`co2.py`): 50 % of
        261,81 € is 130,905 €, and the half cent belongs to the **landlord's**
        deduction — the tenant-favourable side. Reordering the two elements
        would silently invert this."""
        assert _shares(26_181, _d(50, 50), owner=1) == [13091, 13090]
        assert [int(s) for s in distribute_cents(cents(26_181), _d(50, 50))] == [13091, 13090]
