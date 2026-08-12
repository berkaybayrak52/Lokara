"""Ho vs. Hu - the energy reference travels with the number, and never converts.

Spec: `docs/03-nk-heating-engines.md` -> "Seite 01b … (4) Ho/Hu". Source:
`berkay-work/…/01b · Heizkosten- & CO₂-Verteilung ….md` § 3.2/§ 4 (H2, K4) and
the Rechtsstand-Register row "Emissionsfaktor Erdgas (K4)".

**The failure this exists to prevent.** German gas invoices bill in Brennwert
(Ho) kWh. The EBeV 2030 fallback factor is Heizwert (Hu)-based - § 3 Abs. 1
Nr. 3 CO2KostAufG demands the *heizwertbezogene* factor in so many words.
Ho-kWh x Hu-factor overstates emissions by roughly 11 %, which at a step
boundary is a whole Stufe, systematically against the landlord, on a document
the tenant may rely on. And it fails **silently**: every intermediate looks
plausible. Berkay: harden this before any real CO₂ split ships.

**The design, taken as given: there is no conversion step anywhere.** A
`x 0,903` correction is a step somebody forgets, or applies twice. Instead the
factor declares its `bezug` and the kWh declares the same one; a mismatch is a
hard error, never a silent coercion.

**Scope.** These factors are `nur Fallback` (K4): they apply only where the
supplier has failed to state the mass under § 3 CO2KostAufG. Where the supplier
states it - the normal case, and the demo case (`docs/06`) - no factor is read.

Written before the implementation exists: fails today with `ImportError`.
"""

from decimal import Decimal

import pytest
from lokara_domain import (
    EmissionFactor,
    EnergyReference,
    EnergyReferenceMismatchError,
    co2_grams_from_energy,
)

# Values from the Rechtsstand-Register, imported as-is (CLAUDE.md precedence
# rule 3), flags intact: all four are `verify-before-production`, Rechtsnatur
# `Konvention`, source EBeV 2030 Anlage 2 Teil 4. The lead's brief carries a
# different Erdgas pair (Hu 0,2016 / Ho 0,1820) - recorded as an open
# discrepancy in `docs/03` § 7 and deliberately NOT resolved here.
ERDGAS_HU = EmissionFactor(kg_co2_per_kwh=Decimal("0.201"), reference=EnergyReference.HU)
ERDGAS_HO = EmissionFactor(kg_co2_per_kwh=Decimal("0.181"), reference=EnergyReference.HO)
HEIZOEL_HU = EmissionFactor(kg_co2_per_kwh=Decimal("0.266"), reference=EnergyReference.HU)
FLUESSIGGAS_HU = EmissionFactor(kg_co2_per_kwh=Decimal("0.236"), reference=EnergyReference.HU)


class TestMatchingReferences:
    def test_berkay_01b_f02_the_hu_fallback_of_the_reference_object(self) -> None:
        """`01b-F02` / E1 - the supplier stated no CO₂ figures (§ 3 breach).

        28.000 kWh declared **Hi/Hu** (his input field `rechnung.mengeKwh` is
        Hi) x 0,201 kg/kWh = 5.628 kg, which is exactly the mass `01b-F01` gets
        from the invoice. Every downstream figure of F02 is therefore identical
        to F01; what differs is the warning and the § 7 Abs. 4 risk flag.

        R4: the internal unit is the **integer gram**.
        """
        grams = co2_grams_from_energy(Decimal(28000), EnergyReference.HU, ERDGAS_HU)
        assert grams == 5_628_000
        assert isinstance(grams, int)

    def test_the_same_invoice_read_as_brennwert_uses_the_ho_factor_directly(self) -> None:
        """28.000 kWh(Ho) x 0,181 = 5.068 kg. No conversion happened on the way.

        Against the wrong pairing - 28.000 Ho-kWh x the **Hu** factor - this is
        5.628 kg vs 5.068 kg, i.e. 11,0 % too high. That is the defect, in one
        line of arithmetic.
        """
        assert co2_grams_from_energy(Decimal(28000), EnergyReference.HO, ERDGAS_HO) == 5_068_000

    def test_heizoel_and_fluessiggas_carry_the_heizwert_reference(self) -> None:
        """Both register rows are Hu (EBeV Anlage 2 Teil 4 Nr. 3b / 5b) and the
        register states **no Ho counterpart** for either. None is invented."""
        assert HEIZOEL_HU.reference is EnergyReference.HU
        assert FLUESSIGGAS_HU.reference is EnergyReference.HU
        assert co2_grams_from_energy(Decimal(56000), EnergyReference.HU, HEIZOEL_HU) == 14_896_000

    def test_the_oil_path_derives_kwh_at_the_same_reference_as_the_invoice(self) -> None:
        """`01b-F19` / K7: 5.600 l consumed x 10 kWh/l = 56.000 kWh, and that
        derived quantity carries the invoice's reference. The generic form of
        the rule: whenever the engine derives kWh from m³ or litres itself, it
        uses the reference the invoice uses.
        """
        litres_consumed = Decimal(5600)
        derived_kwh = litres_consumed * Decimal(10)
        grams = co2_grams_from_energy(derived_kwh, EnergyReference.HU, HEIZOEL_HU)
        assert grams == 14_896_000
        # 14.896 kg over 420 m² -> 35,47 kg/m²/a -> Stufe 32-<37 -> Vermieter 50 %.
        assert Decimal(grams) / Decimal(10**6) / Decimal(420) < Decimal(37)


class TestAReferenceMismatchIsAHardError:
    def test_brennwert_kwh_against_a_heizwert_factor_is_refused(self) -> None:
        """The exact silent-failure case: an Erdgas invoice (Ho) met by the
        EBeV Hu factor. It must not compute a number at all."""
        with pytest.raises(EnergyReferenceMismatchError):
            co2_grams_from_energy(Decimal(28000), EnergyReference.HO, ERDGAS_HU)

    def test_heizwert_kwh_against_a_brennwert_factor_is_refused(self) -> None:
        with pytest.raises(EnergyReferenceMismatchError):
            co2_grams_from_energy(Decimal(28000), EnergyReference.HU, ERDGAS_HO)

    def test_the_error_does_not_coerce_a_value_on_the_way_out(self) -> None:
        """There is no conversion path, so there is nothing to fall back to.
        A future 'helpful' `x 0,903` here would reintroduce exactly the step
        this design removed.
        """
        with pytest.raises(EnergyReferenceMismatchError) as raised:
            co2_grams_from_energy(Decimal(28000), EnergyReference.HO, ERDGAS_HU)
        assert "0.903" not in str(raised.value)

    def test_an_ho_quantity_of_oil_has_no_factor_and_is_refused(self) -> None:
        """The register carries no Ho factor for Heizöl. Refusing is the correct
        outcome; converting would be inventing a legal number."""
        with pytest.raises(EnergyReferenceMismatchError):
            co2_grams_from_energy(Decimal(56000), EnergyReference.HO, HEIZOEL_HU)


class TestTheRegisterPairIsNotExactlyReciprocal:
    def test_the_two_erdgas_factors_agree_only_to_about_a_third_of_a_percent(self) -> None:
        """Recorded, not resolved (`docs/03` § 7, open discrepancy 2).

        The register says *"beide Wege fuehren zum selben Ergebnis"*, but
        0,201 x 0,903 = 0,181503, not 0,181. On 28.000 kWh that is 5.082 kg via
        the conversion against 5.068 kg direct - 14 kg apart. A further argument
        for the no-conversion design, and a question for Berkay.
        """
        converted = ERDGAS_HU.kg_co2_per_kwh * Decimal("0.903")
        assert converted == Decimal("0.181503")
        assert converted != ERDGAS_HO.kg_co2_per_kwh
        drift = (converted - ERDGAS_HO.kg_co2_per_kwh) / ERDGAS_HO.kg_co2_per_kwh
        assert Decimal("0.002") < drift < Decimal("0.004")
