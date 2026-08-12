"""The energy reference (Ho/Hu) travels with the number, and never converts.

German gas invoices bill in **Brennwert** (Ho) kWh; the EBeV 2030 fallback
emission factor is **Heizwert** (Hu)-based, because § 3 Abs. 1 Nr. 3
CO2KostAufG demands the *heizwertbezogene* Emissionsfaktor in so many words.
Multiplying Ho-kWh by an Hu factor overstates the emissions by roughly 11 %,
which at a step boundary of the CO2KostAufG Anlage is a whole Stufe,
systematically against the landlord, on a document the tenant may rely on — and
it fails **silently**, because every intermediate looks plausible.

**There is no conversion step anywhere, and none may be added.** That is the
whole design: a `x 0,903` correction is a step somebody forgets, or applies
twice. The factor declares its reference, the kWh quantity declares the same
one, and a mismatch is a hard error refused at the boundary
(:class:`EnergyReferenceMismatchError`) — never a silent coercion. The rule is
generic: wherever kWh is *derived* (m³ of gas, litres of oil at 10 kWh/l), the
derived quantity carries the reference the invoice carries. The reference is a
property of the quantity, not of the fuel.

Scope: the fallback factors these types carry are `nur Fallback` (K4) — they
apply only where the supplier failed to state the mass under § 3 CO2KostAufG.
Where the supplier states it (the normal case), no factor is read at all.

Spec: `docs/03-nk-heating-engines.md` → "Seite 01b … (4) Ho/Hu — the energy
reference travels with the number". Values live in `lokara-rules-store`.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

_GRAMS_PER_KG = Decimal(1000)


class EnergyReference(StrEnum):
    """Bezugsgröße of a kWh quantity: Brennwert (Ho) or Heizwert (Hu)."""

    HO = "HO"  # Brennwert — what a German gas invoice bills in
    HU = "HU"  # Heizwert — what § 3 Abs. 1 Nr. 3 CO2KostAufG's factor refers to


@dataclass(frozen=True)
class EmissionFactor:
    """A CO₂ emission factor together with the reference its kWh must carry.

    The reference lives **on the value**, not in a comment next to it: that is
    what makes a mismatch checkable at all.
    """

    kg_co2_per_kwh: Decimal
    reference: EnergyReference


_BEZUG = {EnergyReference.HO: "Brennwert (Ho)", EnergyReference.HU: "Heizwert (Hu)"}


class EnergyReferenceMismatchError(ValueError):
    """A kWh quantity met a factor of the other reference. Refused, never converted."""

    def __init__(self, energy_reference: EnergyReference, factor: EmissionFactor) -> None:
        super().__init__(
            "CO₂-Berechnung nicht möglich: Die Energiemenge ist in "
            f"{_BEZUG[energy_reference]}-Kilowattstunden angegeben, der Emissionsfaktor "
            f"({factor.kg_co2_per_kwh} kg CO₂/kWh) bezieht sich aber auf "
            f"{_BEZUG[factor.reference]}. Beide Angaben müssen dieselbe Bezugsgröße haben; "
            "eine Umrechnung findet bewusst nicht statt (§ 3 Abs. 1 Nr. 3 CO2KostAufG "
            "verlangt den heizwertbezogenen Emissionsfaktor). Bitte den Faktor mit der "
            "passenden Bezugsgröße hinterlegen oder die Energiemenge in der Bezugsgröße "
            "des Faktors erfassen."
        )


def co2_grams_from_energy(
    energy_kwh: Decimal, energy_reference: EnergyReference, factor: EmissionFactor
) -> int:
    """kWh × kg CO₂/kWh → **integer grams** (R4), and only when the references match.

    R4 keeps emissions in whole grams internally; kg with one decimal and
    kg/m²/a with two are display roundings, and the CO₂ step lookup uses the
    unrounded value.
    """
    if not energy_kwh.is_finite() or energy_kwh < 0:
        raise ValueError(f"Energy quantity must be finite and >= 0, got: {energy_kwh}")
    if energy_reference is not factor.reference:
        raise EnergyReferenceMismatchError(energy_reference, factor)
    grams = energy_kwh * factor.kg_co2_per_kwh * _GRAMS_PER_KG
    return int(grams.quantize(Decimal(1), rounding=ROUND_HALF_UP))
