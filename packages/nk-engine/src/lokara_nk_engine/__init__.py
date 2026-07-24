"""Pure NK (Betriebskosten) allocation engine — M1.

No web framework, no DB, no vendor SDK: normalized inputs in, deterministic
cent-exact shares out (docs/03). Depends only on lokara-domain.
"""

from .engine import calculate_nk_statement
from .inputs import (
    ConsumptionValue,
    CostItem,
    NkInput,
    NkInputError,
    NkResult,
    PersonCountPeriod,
    ShareLine,
    UnitBasis,
)

__version__ = "0.1.0"

__all__ = [
    "ConsumptionValue",
    "CostItem",
    "NkInput",
    "NkInputError",
    "NkResult",
    "PersonCountPeriod",
    "ShareLine",
    "UnitBasis",
    "calculate_nk_statement",
]
