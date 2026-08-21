"""The Eigentümer-Residuum primitive — RED, written before it exists.

Spec: `docs/02-data-model.md` -> "The Eigentümeranteil is a residual line, not a
party"; `docs/03-nk-heating-engines.md` § 5 (R1/R5, the API-consequence block)
and § 9.2; `docs/08` -> "Die Eigentümerzeile". Primary rule source:
original Page 01
-> **D0**, **D12**, and edge cases **E3** / **E19**. Worked numbers:
`berkay-work/Spec-Seiten/02 · BetrKV — Betriebskosten-Katalog ….md` ->
`09-F07` (his `08-F22`) and `09-F08`. Both fixture numberings are named so the
two pages can be matched later. Every figure asserted here is independently
re-derived in `test_berkay_residual_oracles.py`, which is green today.

**What is RED here and why.** `distribute_cents_owner_residual` does not exist.
`packages/domain/src/lokara_domain/money.py` has `distribute_cents`
(largest-remainder) and `distribute_cents_half_up(..., residual_index=i)`. The
second is *nearly* this rule but says the wrong thing: `residual_index` means
*the owner is the party at index i*, which is precisely the model Berkay
replaced, and it lets a caller pass the owner as a party by accident. So this
module fails at **import** until the primitive exists — that is the intended
RED, not a broken test file.

**The rule.** For one Liegenschaft and one Kostenart (D12):

    eigentuemeranteilCent = gesamtbetragCent - Σ mieteranteilCent

⚠️ *"ALWAYS as a residual, NEVER computed separately"*. The vacancy is not
skipped — it sits in the **denominator** (D0), which is why the residual comes
out at the vacancy share rather than at zero.

**Rechtsnatur.** § 1.4 sets this fest: *"meine feste Modellregel, keine offene
Konvention … setzt es fest um."* No `verify-before-production` flag. The
`Fiktivbelegung bei Leerstand` register row it leans on keeps its own
(`Konvention`, Rechtsstand 07/2026) — the residual is settled, the fictional
person count is not.

⚠️ `09-F07` / `09-F08` are **Betriebskosten** figures. They are asserted here as
pure arithmetic against the primitive, because the *model* is cross-engine and
the primitive lives in `packages/domain`. Its application to `nk-engine` is the
Seite 02 -> `docs/09` row and is deliberately **not** in this slice. Nothing
here imports `nk-engine`.
"""

from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import ClassVar

import pytest
from lokara_domain import cents
from lokara_domain.money import distribute_cents_owner_residual


def _d(*values: int | str) -> list[Decimal]:
    return [Decimal(v) for v in values]


def _split(
    pot: int, renter_weights: Sequence[Decimal | int], owner_weight: Decimal | int
) -> tuple[list[int], int]:
    renters, owner = distribute_cents_owner_residual(
        cents(pot), renter_weights, owner_weight=owner_weight
    )
    return [int(share) for share in renters], int(owner)


def _computed_separately(pot: int, weight: Decimal, denominator: Decimal) -> int:
    """What the figure would be if it were **computed separately** — the thing
    D12 forbids. Used only to show that it differs from the residual."""
    return int((Decimal(pot) * weight / denominator).quantize(Decimal(1), rounding=ROUND_HALF_UP))


class TestBerkay09F07TheResidualWinsOverTheSeparatelyComputedShare:
    """`09-F07` variant A, his `08-F22` — Müllbeseitigung by Personenzahl.

    The clearest numeric consequence of the model, and the reason it is not
    merely a layout rule. 62000 ct, denominator
    `nPersTage = 2.006 + 2 × 31 = 2.068`, where the 62 are the empty unit's
    Fiktivbelegung (D0: 2 fiktive Personen × 31 Tage Leerstand im August).

        Muster    = 62000 × 1095 / 2068 = 32.828,82 -> 32829
        Schneider = 62000 ×  424 / 2068 = 12.711,80 -> 12712
        Weber     = 62000 ×  122 / 2068 =  3.657,64 ->  3658
        Beispiel  = 62000 ×  365 / 2068 = 10.942,94 -> 10943
        Σ = 60142 · Eigentümer = 62000 - 60142 = 1858

    His comment, verbatim: *"getrennt gerechnet wäre der Leerstandsanteil
    62000 × 62 / 2068 = 1858,80 -> 1859. Gerechnet wird 1858. Residuum
    gewinnt."* His annex reaches the same 1858 from the other side (`08-F21`
    prints Müllbeseitigung `18,58`) — two independent sightings in his own
    material.
    """

    POT = 62_000
    RENTERS: ClassVar[list[Decimal]] = _d(1095, 424, 122, 365)
    OWNER_WEIGHT = Decimal(62)
    DENOMINATOR = Decimal(2068)

    def test_the_four_renter_shares_are_each_their_own_round_half_up(self) -> None:
        renters, _ = _split(self.POT, self.RENTERS, self.OWNER_WEIGHT)
        assert renters == [32829, 12712, 3658, 10943]

    def test_the_owner_holds_1858_and_not_its_own_quota_of_1859(self) -> None:
        renters, owner = _split(self.POT, self.RENTERS, self.OWNER_WEIGHT)
        assert sum(renters) == 60_142
        assert owner == 1858  # the residual — what ships
        assert _computed_separately(self.POT, self.OWNER_WEIGHT, self.DENOMINATOR) == 1859
        assert owner != 1859

    def test_the_control_sum_closes(self) -> None:
        renters, owner = _split(self.POT, self.RENTERS, self.OWNER_WEIGHT)
        assert sum(renters) + owner == self.POT

    def test_the_owner_weight_is_in_the_denominator_and_nowhere_else(self) -> None:
        """Dropping the Fiktivbelegung from the denominator would hand the
        vacancy to the renters — his `08-F22` calls that out as the case where
        *"die Mieter 100 % der personenbezogenen Fixkosten"* carry, contrary to
        BGH VIII ZR 159/05 / LG Krefeld 2 S 56/09.
        """
        with_fiction, owner_with = _split(self.POT, self.RENTERS, self.OWNER_WEIGHT)
        without_fiction, owner_without = _split(self.POT, self.RENTERS, Decimal(0))
        assert all(a < b for a, b in zip(with_fiction, without_fiction, strict=True))
        assert owner_with == 1858
        assert owner_without == 0


class TestBerkay09F08AConsumptionKeyedResidualIsGenuinelyZero:
    """`09-F08` — Wasserversorgung 126000 by measured Wasserverbrauch.

    One of the three `0,00` rows of `09-F19` and the case § 1.3 Frage 1 argues
    from. There is no owner weight at all, and not because the model forgot the
    vacancy: D0 leaves consumption denominators untouched, *"a vacant unit
    consumes nothing"*. The denominator is the sum of actually measured
    consumption, the empty unit contributes nothing, and the residual is
    genuinely **0** — not absent, not "not applicable".

        Muster    = 126000 × 95 / 203 = 58.965,52 -> 58966
        Schneider = 126000 × 48 / 203 = 29.793,10 -> 29793
        Weber     = 126000 × 19 / 203 = 11.793,10 -> 11793
        Beispiel  = 126000 × 41 / 203 = 25.448,28 -> 25448
        Σ = 126000 · Eigentümer = 0
    """

    POT = 126_000
    RENTERS: ClassVar[list[Decimal]] = _d(95, 48, 19, 41)

    def test_the_shares_and_the_zero_residual(self) -> None:
        renters, owner = _split(self.POT, self.RENTERS, Decimal(0))
        assert renters == [58966, 29793, 11793, 25448]
        assert owner == 0
        assert sum(renters) + owner == self.POT

    def test_zero_is_a_returned_value_and_not_an_absence(self) -> None:
        """`0` is returned like any other amount, so a renderer that prints
        every residual prints `0,00 €` here. Nothing in the shape can express
        "no row" (`docs/08` -> "Die Eigentümerzeile" § 1)."""
        _, owner = _split(self.POT, self.RENTERS, Decimal(0))
        assert isinstance(owner, int)
        assert owner == 0


class TestThePrimitiveItself:
    """The behaviours the engines rely on that no Berkay fixture states outright."""

    def test_a_fully_let_block_has_owner_weight_zero_and_still_returns_a_residual(self) -> None:
        """§ 1.3 Frage 1 — no vacancy, no self-use, and the line still exists.

        `round_half_up` biases every renter share upward, so Σ Mieter tends to
        exceed the pot and the residual comes out **negative**. -1 ct is the
        ordinary output of a fully-let building and must never be "corrected"
        to 0: the correction would break the control sum, which is the one
        thing this line exists to keep true (`CLAUDE.md` DoD 4 allows it
        explicitly). The pot and weights are the `ww_base` block of the
        299.935 ct fully-let fixture in
        `packages/heating-engine/tests/test_berkay_02_eigentuemer_residuum.py`.
        """
        renters, owner = _split(22_495, _d(50, 30, 20), Decimal(0))
        assert renters == [11_248, 6_749, 4_499]  # each its own round_half_up
        assert owner == -1
        assert sum(renters) + owner == 22_495

    def test_a_fully_let_block_can_land_exactly_on_zero(self) -> None:
        """And then the row prints `0,00 €` — `docs/08` § 1. The `ww_base` block
        of the 240.000 ct fully-let fixture."""
        renters, owner = _split(18_000, _d(50, 30, 20), Decimal(0))
        assert renters == [9_000, 5_400, 3_600]
        assert owner == 0

    def test_a_zero_denominator_puts_the_whole_amount_on_the_owner(self) -> None:
        """Seite 01 **E3** — *"Für diese Kostenart wurden keine Verbrauchswerte
        erfasst; die Kosten verbleiben beim Eigentümer."* Every renter share is
        0, the residual is the whole pot, and the cost is never silently
        re-keyed. Deliberately **not** a `ZeroDivisionError` and **not** a
        `ValueError`: this is a documented business case, and a caller left to
        handle it would have to invent an allocation at the call site.
        """
        renters, owner = _split(12_345, _d(0, 0, 0), Decimal(0))
        assert renters == [0, 0, 0]
        assert owner == 12_345

    def test_a_building_with_no_tenancy_at_all_puts_everything_on_the_owner(self) -> None:
        """Seite 01 **E19** — a unit vacant for the whole period stays in the
        Gesamtverteiler and is never removed from it. With no renters there is
        nothing to allocate and the residual is the pot; an empty renter list is
        a real case, not an input error.
        """
        renters, owner = _split(50_000, [], Decimal(3_650))
        assert renters == []
        assert owner == 50_000

    def test_the_owner_weight_never_becomes_a_share_of_its_own(self) -> None:
        """The structural half of D12's *"NEVER computed separately"*: the owner
        weight only ever enters the **denominator**. Doubling it therefore
        shrinks every renter share and grows the residual — it never produces an
        owner share computed from it.
        """
        small_renters, small_owner = _split(100_000, _d(50, 30, 20), Decimal(100))
        large_renters, large_owner = _split(100_000, _d(50, 30, 20), Decimal(200))
        assert all(b < a for a, b in zip(small_renters, large_renters, strict=True))
        assert large_owner > small_owner
        assert sum(large_renters) + large_owner == 100_000

    def test_negative_weights_are_still_refused(self) -> None:
        with pytest.raises(ValueError):
            _split(1_000, _d(50, -30), Decimal(0))
        with pytest.raises(ValueError):
            _split(1_000, _d(50, 30), Decimal(-1))

    def test_the_result_is_a_pair_and_the_owner_is_not_in_the_renter_list(self) -> None:
        """Shape, not arithmetic: the owner cannot be indexed into as a party,
        which is what makes *"the Eigentümer is not a party"* structural rather
        than a rule somebody has to remember."""
        renters, owner = distribute_cents_owner_residual(
            cents(62_000), _d(1095, 424, 122, 365), owner_weight=Decimal(62)
        )
        assert len(renters) == 4
        assert int(owner) == 1858
        assert 1858 not in [int(share) for share in renters]
