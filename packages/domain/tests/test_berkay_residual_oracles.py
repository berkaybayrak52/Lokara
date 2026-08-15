"""Berkay's own arithmetic for the Eigentümer-Residuum, transcribed and checked.

Spec: `docs/02-data-model.md` -> "The Eigentümeranteil is a residual line, not a
party"; `docs/08` -> "Die Eigentümerzeile" § 5. Sources:
`berkay-work/Spec-Seiten/Antworten/Antwort-an-Emir_02.md` § 1 and § 6 items 1-3 (14.08.2026);
`berkay-work/Spec-Seiten/01 · Die Abrechnung ….md` -> **D12** and **08-F21**
(line 757); `berkay-work/Spec-Seiten/02 · BetrKV — Betriebskosten-Katalog ….md`
-> `09-F07` (his `08-F22`), `09-F08`, `09-F19` (his `08-F21`).

**This file is GREEN by design and is not the RED fixture of the slice.** It
calls no engine and no primitive; it is pure transcription arithmetic. It exists
because every RED fixture in
`packages/heating-engine/tests/test_berkay_02_eigentuemer_residuum.py` and in
`test_owner_residual_model.py` is checked against these numbers, and a
transcription error here would silently invalidate all of them. His own request:
*"bitte tut das, verlasst euch nicht auf mein Wort."*

⚠️ These are **Betriebskosten** figures from Seite 02. They are asserted as
arithmetic only. `nk-engine` is deliberately untouched in this slice — its
switch to the residual model belongs to the Seite 02 -> `docs/09` row
(`docs/02` -> "This is cross-engine and binding"). Nothing here imports it.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import ClassVar


def _round_half_up(value: Decimal) -> int:
    return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _computed_separately(pot: int, weight: Decimal, denominator: Decimal) -> int:
    """What a figure would be if it were **computed separately** — the thing
    D12 forbids (*"ALWAYS as a residual, NEVER computed separately"*). Used
    only to show by how much it differs from the residual."""
    return _round_half_up(Decimal(pot) * weight / denominator)


class TestBerkay09F19TheObjectLevelControlSum:
    """`09-F19`, his `08-F21` — the full catalogue run of the reference object.

    His self-check no. 1: *"10.550,69 umgelegt + 175,31 Eigentümer =
    10.726,00. Geht auf 0 auf."* Transcribed as a table so the per-Kostenart
    zeros stay visible next to the non-zeros.
    """

    # (Kostenart, umlagefähig, Σ Mieter, Eigentümer)
    ROWS: ClassVar[tuple[tuple[str, int, int, int], ...]] = (
        ("Grundsteuer", 98_000, 94_826, 3_174),
        ("Wasserversorgung", 126_000, 126_000, 0),
        ("Entwässerung", 84_000, 84_000, 0),
        ("Müllbeseitigung", 62_000, 60_142, 1_858),
        ("Straßenreinigung", 18_000, 17_417, 583),
        ("Gebäudereinigung", 54_000, 52_251, 1_749),
        ("Gartenpflege", 36_000, 34_834, 1_166),
        ("Allgemeinstrom", 24_000, 23_222, 778),
        ("Schornsteinreinigung", 12_000, 11_660, 340),
        ("Versicherung", 145_000, 140_303, 4_697),
        ("Hauswart", 90_000, 87_085, 2_915),
        ("Rauchwarnmelder (Wartung)", 9_600, 9_329, 271),
        ("Heizkosten", 314_000, 314_000, 0),
    )

    def test_every_single_row_reconciles(self) -> None:
        for name, total, renters, owner in self.ROWS:
            assert renters + owner == total, name

    def test_the_object_total_reconciles(self) -> None:
        assert sum(row[1] for row in self.ROWS) == 1_072_600  # 10.726,00 €
        assert sum(row[2] for row in self.ROWS) == 1_055_069  # 10.550,69 €
        assert sum(row[3] for row in self.ROWS) == 17_531  # 175,31 €
        assert 1_055_069 + 17_531 == 1_072_600

    def test_three_rows_carry_a_zero_eigentuemer_amount_and_one_does_not(self) -> None:
        """The pair § 1.3 Frage 1 argues from: zeros and a non-zero in the same
        column, so `0,00` cannot be read as "column not applicable". The three
        zeros are consumption-keyed — D0 leaves consumption denominators
        untouched, *"a vacant unit consumes nothing"* — so the residual there is
        genuinely zero rather than absent.
        """
        zero_rows = {row[0] for row in self.ROWS if row[3] == 0}
        assert zero_rows == {"Wasserversorgung", "Entwässerung", "Heizkosten"}
        grundsteuer = next(row for row in self.ROWS if row[0] == "Grundsteuer")
        assert grundsteuer[3] == 3_174


class TestBerkay09F07TheSeparatelyComputedShareIsADifferentNumber:
    """`09-F07` variant A, his `08-F22` — Müllbeseitigung 62000 by Personenzahl.

    The renter shares round to `32829 / 12712 / 3658 / 10943`, Σ `60142`, so the
    residual is **1858**. Computed separately the vacancy share is
    `62000 × 62 / 2068 = 1858,80 -> 1859`. His comment: *"Gerechnet wird 1858.
    Residuum gewinnt."* His annex reaches the same 1858 from the other side
    (`08-F21` prints Müllbeseitigung `18,58`).

    `nPersTage = 2.006 + 2 × 31 = 2.068` — the 62 are the empty unit's
    Fiktivbelegung (D0: 2 fiktive Personen × 31 Tage). The vacancy is in the
    **denominator**; that is what makes the residual come out at the vacancy
    share instead of at zero.
    """

    POT = 62_000
    RENTER_WEIGHTS: ClassVar[tuple[int, ...]] = (1095, 424, 122, 365)
    OWNER_WEIGHT = 62
    DENOMINATOR = Decimal(2068)

    def test_the_denominator_is_the_renters_plus_the_fiktivbelegung(self) -> None:
        assert sum(self.RENTER_WEIGHTS) == 2_006
        assert sum(self.RENTER_WEIGHTS) + self.OWNER_WEIGHT == self.DENOMINATOR

    def test_each_renter_share_is_its_own_round_half_up(self) -> None:
        shares = [
            _computed_separately(self.POT, Decimal(w), self.DENOMINATOR)
            for w in self.RENTER_WEIGHTS
        ]
        assert shares == [32829, 12712, 3658, 10943]
        assert sum(shares) == 60_142

    def test_the_residual_is_1858_and_the_separate_computation_gives_1859(self) -> None:
        residual = self.POT - 60_142
        separately = _computed_separately(self.POT, Decimal(self.OWNER_WEIGHT), self.DENOMINATOR)
        assert residual == 1858
        assert separately == 1859
        assert residual != separately


class TestBerkay09F08AConsumptionKeyedResidualIsGenuinelyZero:
    """`09-F08` — Wasserversorgung 126000 by measured Wasserverbrauch.

    One of the three `0,00` rows of `09-F19`. The renters' own round_half_up
    shares happen to sum to the pot exactly, so the residual is 0 — and the
    empty unit contributes no weight at all, because D0 leaves consumption
    denominators untouched.
    """

    POT = 126_000
    WEIGHTS: ClassVar[tuple[int, ...]] = (95, 48, 19, 41)
    DENOMINATOR = Decimal(203)

    def test_the_shares_sum_to_the_pot_so_the_residual_is_zero(self) -> None:
        shares = [
            _computed_separately(self.POT, Decimal(w), self.DENOMINATOR) for w in self.WEIGHTS
        ]
        assert shares == [58966, 29793, 11793, 25448]
        assert sum(shares) == self.POT
        assert self.POT - sum(shares) == 0


class TestBerkay08F21TheAnnexOnlyTiesWhenTheAmountIsAResidual:
    """`08-F21`'s proof of the rule, decomposed by **key family**.

    Verbatim from Seite 01 line 792: *"computed separately the vacancy would be
    15.065 (m² keys) + 612 (WE keys) + 1.859 (Personen) = **17.536**. As a
    residual: **17.531**. 5 cents of line-wise rounding drift. Computed
    separately the annex does not tie to the statement — exactly what an auditor
    notices."*

    The decomposition is the better oracle than the bare 17.536: it says *where*
    the drift comes from. Reference object, WE-02 vacant 01.08.-31.08.2025,
    31 Tage, 74 m², fiktive Belegung 2 Personen. `m²·Tage = 74 × 31 = 2.294`
    against `nM2Tage = 70.810`; the WE keys are `je Einheit × 31/365`; the
    Personen key is the class above.

    Block (c) of the Leerstandsaufstellung is `Residuum - Σ (a) = -5`. In his own
    rendering (c) prints `0,00`, because with exactly **one** empty unit the
    per-Kostenart residual column already *is* that unit's (a) figure and the
    17.536 is a counterfactual he never prints. Recorded as `docs/03` § 7 item
    12; the definition used throughout is `(c) = Residuum - Σ (a)`.
    """

    N_M2_TAGE = Decimal(70_810)
    VACANCY_M2_TAGE = Decimal(74 * 31)
    VACANCY_DAYS = Decimal(31)
    PERIOD_DAYS = Decimal(365)
    # (Kostenart, umlagefähig, the residual from 09-F19)
    AREA_KEYED: ClassVar[tuple[tuple[str, int, int], ...]] = (
        ("Grundsteuer", 98_000, 3_174),
        ("Straßenreinigung", 18_000, 583),
        ("Gebäudereinigung", 54_000, 1_749),
        ("Gartenpflege", 36_000, 1_166),
        ("Allgemeinstrom", 24_000, 778),
        ("Versicherung", 145_000, 4_697),
        ("Hauswart", 90_000, 2_915),
    )
    # (Kostenart, je Einheit, the residual from 09-F19)
    UNIT_KEYED: ClassVar[tuple[tuple[str, int, int], ...]] = (
        ("Schornsteinreinigung", 12_000 // 3, 340),
        ("Rauchwarnmelder (Wartung)", 9_600 // 3, 271),
    )

    def test_the_area_keyed_family_drifts_by_three_cents(self) -> None:
        separately = sum(
            _computed_separately(total, self.VACANCY_M2_TAGE, self.N_M2_TAGE)
            for _, total, _ in self.AREA_KEYED
        )
        residual = sum(owner for _, _, owner in self.AREA_KEYED)
        assert separately == 15_065  # his figure
        assert residual == 15_062
        assert residual - separately == -3

    def test_the_unit_keyed_family_drifts_by_one_cent(self) -> None:
        separately = sum(
            _computed_separately(per_unit, self.VACANCY_DAYS, self.PERIOD_DAYS)
            for _, per_unit, _ in self.UNIT_KEYED
        )
        residual = sum(owner for _, _, owner in self.UNIT_KEYED)
        assert separately == 612  # his figure
        assert residual == 611
        assert residual - separately == -1

    def test_the_person_keyed_family_drifts_by_one_cent(self) -> None:
        separately = _computed_separately(62_000, Decimal(62), Decimal(2_068))
        assert separately == 1_859  # his figure
        assert 1_858 - separately == -1

    def test_the_three_families_reproduce_17536_and_17531_and_the_five_cents(self) -> None:
        separately = 15_065 + 612 + 1_859
        residual = 15_062 + 611 + 1_858
        assert separately == 17_536
        assert residual == 17_531
        assert residual - separately == -5
        # And the residual side is the Eigentümer column of 09-F19.
        assert (
            residual
            == 17_531
            == sum(row[3] for row in TestBerkay09F19TheObjectLevelControlSum.ROWS)
        )
