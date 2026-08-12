"""K4 — CO₂ emission factors used **only** when the supplier stated no mass.

§ 3 Abs. 1 Nr. 1 CO2KostAufG obliges the fuel or heat supplier to state the
Brennstoffemissionen in kg CO₂ on the invoice, and the landlord copies that
figure. These factors are the Ersatzwert for the supplier's breach of that duty
(*nur Fallback*) — there is no Anwendungspflicht, and a statement must never
present them as the invoiced factor.

Each value carries the **energy reference** (Ho/Hu) its kWh must be counted in,
because § 3 Abs. 1 Nr. 3 demands the *heizwertbezogene* factor while German gas
invoices bill in Brennwert. Nothing converts between the two anywhere in the
system: a mismatch is refused (`lokara_domain.co2_grams_from_energy`). See
`docs/03-nk-heating-engines.md` → "Seite 01b … (4) Ho/Hu".

Values are the Rechtsstand-Register rows "Emissionsfaktor Erdgas / Heizöl /
Flüssiggas (K4)", imported as-is (CLAUDE.md precedence rule 3) with their flags:
Rechtsnatur **Konvention**, **verify before production**, register-Rechtsstand
07/2026. `valid_from` dates the underlying legal source (EBeV 2030, Anlage 2
Teil 4, in force since 01.01.2023), which is what an as-of law-date lookup for a
2025 billing period must resolve against.

Two register facts deliberately preserved rather than smoothed over:

* The register states **no Brennwert (Ho) counterpart** for Heizöl or
  Flüssiggas. None is invented — an Ho quantity of either has no factor and is
  refused rather than converted.
* The Erdgas pair is not exactly reciprocal (0,201 × 0,903 = 0,181503, not
  0,181). Recorded as an open discrepancy in `docs/03` § 7 no. 2, not resolved
  here; it is a further argument for the no-conversion design. The lead's brief
  carries a third pair (Hu 0,2016 / Ho 0,1820) — open item no. 1, likewise not
  decided here.
"""

from datetime import date
from decimal import Decimal
from types import MappingProxyType
from typing import Final

from lokara_domain import EmissionFactor, EnergyReference

from ..store import RuleSet, RuleVersion

# Fuel key (`energietraeger`) → the factor for each reference the register states.
type Co2FallbackEmissionFactors = MappingProxyType[
    str, MappingProxyType[EnergyReference, EmissionFactor]
]

_FACTORS_EBEV_2030: Final[Co2FallbackEmissionFactors] = MappingProxyType(
    {
        # Anlage 2 Teil 4 Nr. 6 EBeV 2030: 0,0558 t CO₂/GJ × 0,0036 GJ/kWh.
        "erdgas": MappingProxyType(
            {
                EnergyReference.HU: EmissionFactor(
                    kg_co2_per_kwh=Decimal("0.201"), reference=EnergyReference.HU
                ),
                # Same register row: "alternativ direkt 0,181 kg CO₂/kWh(Ho)".
                EnergyReference.HO: EmissionFactor(
                    kg_co2_per_kwh=Decimal("0.181"), reference=EnergyReference.HO
                ),
            }
        ),
        # Nr. 3b (Gasöl zu Heizzwecken / Heizöl EL): 0,074 t CO₂/GJ.
        "heizoel": MappingProxyType(
            {
                EnergyReference.HU: EmissionFactor(
                    kg_co2_per_kwh=Decimal("0.266"), reference=EnergyReference.HU
                )
            }
        ),
        # Nr. 5b (Flüssiggas zu Heizzwecken): 0,0655 t CO₂/GJ = 0,2358, kaufmännisch
        # 0,236 — the register corrected this from 0,234 on 27.07.2026.
        "fluessiggas": MappingProxyType(
            {
                EnergyReference.HU: EmissionFactor(
                    kg_co2_per_kwh=Decimal("0.236"), reference=EnergyReference.HU
                )
            }
        ),
    }
)

CO2_FALLBACK_EMISSION_FACTORS: RuleSet[Co2FallbackEmissionFactors] = RuleSet(
    key="co2kostaufg.fallback-emissionsfaktoren",
    versions=(
        RuleVersion(
            valid_from=date(2023, 1, 1),
            # The em dash appears exactly once and last: the renderer drops
            # everything after it, so the internal marker never reaches a tenant.
            source=(
                "Standardwerte EBeV 2030 Anlage 2 Teil 4 (Nr. 6 Erdgas, Nr. 3b Heizöl EL, "
                "Nr. 5b Flüssiggas); keine Anwendungspflicht, nur Fallback bei fehlender "
                "Lieferantenangabe nach § 3 CO2KostAufG (Konvention, keine Rechtsnorm) "
                "— verify before production"
            ),
            value=_FACTORS_EBEV_2030,
        ),
    ),
)
