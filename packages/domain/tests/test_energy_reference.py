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

# Authoritative Rechtsstand-Register CSV values for F02, preserved in approved
# `docs/03` decision 4 and Appendix C. Rechtsstand 07/2026, status geprüft.
ERDGAS_HU = EmissionFactor(kg_co2_per_kwh=Decimal("0.201"), reference=EnergyReference.HU)
ERDGAS_HO = EmissionFactor(kg_co2_per_kwh=Decimal("0.181"), reference=EnergyReference.HO)
ERDGAS_HU_TO_HO = Decimal("0.903")
HEIZOEL_HU = EmissionFactor(kg_co2_per_kwh=Decimal("0.266"), reference=EnergyReference.HU)
FLUESSIGGAS_HU = EmissionFactor(kg_co2_per_kwh=Decimal("0.236"), reference=EnergyReference.HU)


class TestMatchingReferences:
    def test_berkay_01b_f02_uses_the_authoritative_csv_pair(self) -> None:
        assert ERDGAS_HU.reference is EnergyReference.HU
        assert ERDGAS_HO.reference is EnergyReference.HO
        assert co2_grams_from_energy(Decimal(28000), EnergyReference.HU, ERDGAS_HU) == 5_628_000
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


class TestTheRegisterConversionMetadata:
    def test_the_csv_conversion_is_preserved_but_the_engine_uses_direct_factors(self) -> None:
        assert ERDGAS_HU.kg_co2_per_kwh * ERDGAS_HU_TO_HO == Decimal("0.181503")
        assert ERDGAS_HO.kg_co2_per_kwh == Decimal("0.181")
