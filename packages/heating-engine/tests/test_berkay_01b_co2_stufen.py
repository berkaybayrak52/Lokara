"""H2/R8 - CO₂ Einstufung: annualise, round to one decimal, classify.

Spec: `docs/03-nk-heating-engines.md` -> "Seite 01b … (3) CO₂ short billing
period" and § 6 (E2/E3/E4). Source of every expected cent:
`berkay-work/…/01b · Heizkosten- & CO₂-Verteilung ….md` fixtures `01b-F02`
… `01b-F06`. Reference object: Musterstraße 12, 194 m², Gesamtkosten 350.600 ct.

**What is RED here and why.** The short-period rule changes. The engine today
implements the § 5 Abs. 1 S. 4 reading - *shorten the Anlage's bounds by
days/reference-year, leave the intensity as the period figure*. Berkay's H2
**annualises the intensity** and looks it up against the **unshortened** table.

Both readings select the **same step** (`i x 365/d < b` <=> `i < b x d/365`), so
no Einstufung and no euro moves on selection. They differ in the figure that is
**printed**, and the printed figure is what § 7 Abs. 3 CO2KostAufG is about: the
old reading printed a 275-day figure under a `kg CO₂/m²/a` header, against a
band (20,34-24,11) that appears in no statute annex.

⚠️ Do not "fix" this back to the shortened table. The superseded section is kept
and marked in `docs/03`; read it before touching `co2.py`.

Amended by `Antwort-an-Emir_03.md` § 6: R4/E3 and the old `01b-F05` are
superseded. The annualised value is rounded to one decimal before lookup, and
that same rounded value is printed.
"""

from decimal import Decimal

from lokara_domain import (
    Co2Step,
    Co2Table,
    EmissionFactor,
    EnergyReference,
    Period,
    cents,
    co2_grams_from_energy,
    period,
)
from lokara_heating_engine import landlord_share_percent_for_intensity
from lokara_heating_engine.co2 import split_co2_cost
from lokara_heating_engine.inputs import Co2Result

# DO NOT MOVE - bounds and shares both survived Berkay's audit unchanged
# (`docs/03` -> "What did not move").
# Intervals are left-closed, right-open on both sides of the audit.
CO2_TABLE: Co2Table = (
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

AREA = Decimal(194)
GESAMTKOSTEN = 350_600
FULL_YEAR_2025 = period("2025-01-01", "2026-01-01")  # 365 days
RECHTSSTAND = "Rechtsstand 01/2023"


def _split(total_co2_kg: str, co2_cost: int, billing_period: Period = FULL_YEAR_2025) -> Co2Result:
    return split_co2_cost(
        total_co2_kg=Decimal(total_co2_kg),
        co2_cost=cents(co2_cost),
        heated_area_sqm=AREA,
        table=CO2_TABLE,
        rechtsstand=RECHTSSTAND,
        billing_period=billing_period,
    )


class TestStepBoundariesAreLeftClosed:
    """E2 - exactly on a bound belongs to the **higher** step."""

    def test_berkay_01b_f03_exactly_12_00_is_step_2(self) -> None:
        """2.328 kg / 194 m² = 12,00 exactly -> Vermieter 10 %.

        `co2Cent` 12.804 -> abzug 12.804 x 0,10 = 1.280,4 -> 1.280 (12,80 €)
        -> umlagefaehig 350.600 - 1.280 = 349.320 (3.493,20 €).
        """
        result = _split("2328", 12_804)
        assert result.intensity_kg_per_sqm == Decimal("12.0")
        assert result.landlord_share_percent == 10
        assert int(result.landlord_amount) == 1_280
        assert int(result.renter_amount) == 11_524
        assert GESAMTKOSTEN - int(result.landlord_amount) == 349_320

    def test_berkay_01b_f04_exactly_52_00_is_the_open_ended_top_step(self) -> None:
        """10.088 kg / 194 m² = 52,00 exactly -> Vermieter 95 %.

        `co2Cent` 55.484 -> abzug 52.709,8 -> 52.710 (527,10 €)
        -> umlagefaehig 297.890 (2.978,90 €).
        """
        result = _split("10088", 55_484)
        assert result.intensity_kg_per_sqm == Decimal("52.0")
        assert result.landlord_share_percent == 95
        assert int(result.landlord_amount) == 52_710
        assert GESAMTKOSTEN - int(result.landlord_amount) == 297_890

    def test_the_bounds_themselves_did_not_move(self) -> None:
        """The table stays fixed; R8 changes the value compared against it."""
        assert landlord_share_percent_for_intensity(Decimal("11.99"), CO2_TABLE) == 10
        assert landlord_share_percent_for_intensity(Decimal("11.9499"), CO2_TABLE) == 0
        assert landlord_share_percent_for_intensity(Decimal(12), CO2_TABLE) == 10
        assert landlord_share_percent_for_intensity(Decimal(17), CO2_TABLE) == 20
        assert landlord_share_percent_for_intensity(Decimal(22), CO2_TABLE) == 30
        assert landlord_share_percent_for_intensity(Decimal(27), CO2_TABLE) == 40
        assert landlord_share_percent_for_intensity(Decimal(32), CO2_TABLE) == 50
        assert landlord_share_percent_for_intensity(Decimal(37), CO2_TABLE) == 60
        assert landlord_share_percent_for_intensity(Decimal(42), CO2_TABLE) == 70
        assert landlord_share_percent_for_intensity(Decimal(47), CO2_TABLE) == 80
        assert landlord_share_percent_for_intensity(Decimal(52), CO2_TABLE) == 95


class TestTheLookupUsesTheRoundedValue:
    """E3/R4 are superseded by § 5 Abs. 1 S. 3 and Antwort 03 § 6."""

    def test_berkay_01b_f05_rounds_to_12_0_and_classifies_in_step_2(self) -> None:
        """2.327,9 kg / 194 m² = 11,999484535… -> 12,0 -> Stufe 2.

        Vermieteranteil 10 %, abzug 1.280, umlagefaehig 349.320.
        `co2Cent` = 2.327,9/1000 x 5.500 = 12.803,45 -> 12.803 (128,03 €).
        """
        result = _split("2327.9", 12_803)
        assert result.intensity_kg_per_sqm == Decimal("12.0")
        assert result.landlord_share_percent == 10
        assert int(result.landlord_amount) == 1_280
        assert int(result.renter_amount) == 11_523
        assert int(result.landlord_amount) + int(result.renter_amount) == 12_803
        assert GESAMTKOSTEN - int(result.landlord_amount) == 349_320


class TestShortBillingPeriodIsAnnualised:
    """E4 / H2 - `01b-F06`, 01.04.-31.12.2025 = 275 days.

    4.200 kg over 194 m² is 21,649484… kg/m² **for the period**. Annualised:
    21,649484… x 365/275 = **28,734770…** -> Stufe 27 bis unter 32 -> 40 %.
    `abzug` = 23.100 x 0,40 = 9.240 (92,40 €) -> umlagefaehig 341.360.

    Berkay: without the annualisation the naive reading lands in Stufe 17-<22
    (20 %) and is wrong by 46,20 €.
    """

    SHORT_PERIOD = period("2025-04-01", "2026-01-01")

    def test_the_disclosed_intensity_is_the_annualised_figure(self) -> None:
        result = _split("4200", 23_100, self.SHORT_PERIOD)
        expected = Decimal(4200) / AREA * Decimal(365) / Decimal(275)
        assert result.intensity_kg_per_sqm == expected.quantize(Decimal("0.1"))
        assert result.intensity_kg_per_sqm == Decimal("28.7")

    def test_the_annualisation_factor_is_365_over_the_period_days(self) -> None:
        """Replaces `period_factor` (which was <= 1 and shortened the bounds).
        The new factor is >= 1 and multiplies the intensity. The rename is
        deliberate: an inverted meaning behind an old name is how a renderer
        silently prints the wrong band.
        """
        result = _split("4200", 23_100, self.SHORT_PERIOD)
        assert result.annualisation_factor == Decimal(365) / Decimal(275)
        assert result.period_days == 275
        assert result.reference_year_days == 365

    def test_the_band_printed_is_the_unshortened_anlage_band(self) -> None:
        """27 bis unter 32 - the pair a tenant can look up in the published
        Anlage. The superseded reading printed 20,34 - 24,11, which appears in
        no annex.
        """
        result = _split("4200", 23_100, self.SHORT_PERIOD)
        assert result.band_min_inclusive == Decimal(27)
        assert result.band_max_exclusive == Decimal(32)

    def test_the_money_is_unchanged_because_both_readings_select_the_same_step(self) -> None:
        """The claim that makes this change safe, asserted rather than believed:
        `i x 365/d < b` <=> `i < b x d/365`, so the Einstufung is 40 % either
        way and only the printed figure moves.
        """
        result = _split("4200", 23_100, self.SHORT_PERIOD)
        assert result.landlord_share_percent == 40
        assert int(result.landlord_amount) == 9_240
        assert GESAMTKOSTEN - int(result.landlord_amount) == 341_360
        period_figure = Decimal(4200) / AREA
        shortened_lower = Decimal(27) * Decimal(275) / Decimal(365)
        shortened_upper = Decimal(32) * Decimal(275) / Decimal(365)
        assert shortened_lower <= period_figure < shortened_upper

    def test_a_full_year_is_not_annualised(self) -> None:
        """`nTage in (365, 366)` -> factor exactly 1. The demo path is a full
        calendar year, so nothing on it moves."""
        result = _split("5628", 30_954)
        assert result.annualisation_factor == Decimal(1)
        assert result.intensity_kg_per_sqm == Decimal("29.0")
        assert result.landlord_share_percent == 40
        assert int(result.landlord_amount) == 12_382

    def test_a_full_leap_year_is_not_annualised_either(self) -> None:
        leap = period("2024-01-01", "2025-01-01")  # 366 days
        result = _split("5628", 30_954, leap)
        assert result.annualisation_factor == Decimal(1)
        assert result.period_days == 366


class TestBerkay01bF02TheFallbackReachesTheSameStep:
    """E1 mass fallback uses the CSV factor; supplier cost is a separate input."""

    def test_the_csv_hu_factor_reproduces_the_f02_mass_and_f01_step(self) -> None:
        factor = EmissionFactor(Decimal("0.201"), EnergyReference.HU)
        grams = co2_grams_from_energy(Decimal(28000), EnergyReference.HU, factor)
        assert grams == 5_628_000

        # 30.954 ct is supplied here only to exercise downstream F02/F01 parity.
        # The separate F02 refusal fixture forbids deriving it when the supplier omitted it.
        result = _split(str(Decimal(grams) / Decimal(1000)), 30_954)
        assert result.intensity_kg_per_sqm == Decimal("29.0")
        assert result.landlord_share_percent == 40
        assert int(result.landlord_amount) == 12_382
        assert GESAMTKOSTEN - int(result.landlord_amount) == 338_218
