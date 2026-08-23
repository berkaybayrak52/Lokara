"""Normalized NK engine inputs/outputs.

Plain frozen dataclasses — adapters map DB rows to these; no SQLAlchemy or
vendor types ever reach the engine (docs/03 shared engine contract).
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from lokara_domain import AllocationKey, Cents, MeasurementUnit, Occupancy, Period


@dataclass(frozen=True)
class UnitBasis:
    unit_id: str
    # Fixed-point m² × 100 (docs/02: areas are integers, never floats).
    area_sqm_x100: int
    # Miteigentumsanteil × 10000, only needed for the MEA key.
    mea_x10000: int | None = None


@dataclass(frozen=True)
class PersonCountPeriod:
    """Temporal person count of one party — a row, never a scalar (docs/02).

    ``tenancy_id=None`` is the **D0 Fiktivbelegung** row: the fictional occupancy
    a vacant unit contributes to the person-day denominator (`docs/02` § 5
    "D0 Fiktivbelegung", original Page 01 § 4 D0). It is the same landlord-side
    convention `ConsumptionValue.tenancy_id=None` already uses, and it exists so
    the person key can express what the area and unit keys get for free — a
    vacant unit stays in the Gesamtverteiler (BGH VIII ZR 159/05).

    The count is **derived by the caller, never invented by it**: last known
    occupancy of the unit, minimum 1, day-exact, switchable to always-1 or off
    (`Konvention`, `verify-before-production`, Rechtsstand 07/2026). The engine
    stays pure and history-free and takes the derived figure as given; deriving
    it needs a person-count history the engine deliberately does not carry.
    `docs/02` § 5 records why this layering was chosen over an engine-side one.

    ``unit_id`` is which unit the fictional occupancy belongs to, and is only
    meaningful on a landlord row: a renter row's unit comes from its tenancy.
    """

    tenancy_id: str | None
    count: int
    period: Period
    unit_id: str | None = None


@dataclass(frozen=True)
class ConsumptionValue:
    """Period-resolved consumption of one party, normalized upstream by the
    meter adapter. tenancy_id=None attributes the value to the landlord.

    `measurement_unit` is the Maßeinheit `value` is counted in, carried on the
    row that carries the value: the defect this closes *is* a value that
    travelled without its unit, and a side channel beside the result would let
    the two arrive by routes that can silently disagree (docs/08 rule 1).
    `None` — the default — propagates to `NkResult.consumption_unit`, and the
    statement then withholds the reference total instead of guessing one.
    """

    unit_id: str
    tenancy_id: str | None
    value: Decimal
    measurement_unit: MeasurementUnit | None = None


@dataclass(frozen=True)
class CostItem:
    cost_id: str
    label: str
    amount: Cents
    # The key comes from a per-period assignment, never from the cost row
    # itself — re-running with a different key destroys no data (docs/03).
    key: AllocationKey
    direct_unit_id: str | None = None
    direct_tenancy_id: str | None = None


@dataclass(frozen=True)
class NkInput:
    billing_period: Period
    units: tuple[UnitBasis, ...]
    occupancies: tuple[Occupancy, ...]
    costs: tuple[CostItem, ...]
    person_counts: tuple[PersonCountPeriod, ...] = field(default=())
    consumptions: tuple[ConsumptionValue, ...] = field(default=())


@dataclass(frozen=True)
class ShareLine:
    """One allocated share of one cost. tenancy_id=None → landlord side
    (vacancy/self-use). The PDF layer formats these; the engine only computes."""

    cost_id: str
    unit_id: str | None
    tenancy_id: str | None
    weight: Decimal
    amount: Cents


@dataclass(frozen=True)
class NkResult:
    lines: tuple[ShareLine, ...]
    total: Cents
    # The Maßeinheit of the CONSUMPTION key's Bemessungen — the label on the
    # reference total (Gesamtbemessung) the renter checks the denominator by.
    # `None` iff no consumption value was supplied or any supplied row carried
    # no unit; the statement then prints no reference total rather than a
    # guessed unit (docs/08 rules 2/3). Required, no default: a disclosure
    # field a caller can omit silently is the failure this contract forbids.
    #
    # One field because `NkInput.consumptions` is one flat tuple shared by
    # every CONSUMPTION cost — "one key" is literally true today. When a
    # second, independently metered key becomes expressible this becomes a
    # mapping keyed by that key's identity (docs/08: named, not designed).
    consumption_unit: MeasurementUnit | None


class NkInputError(ValueError):
    pass


class BillingWindowTooLongError(NkInputError):
    """The Abrechnungszeitraum exceeds 12 months (`docs/02` § 5 step 1, `08-F15`).

    A named subclass rather than a message a caller has to recognise by its
    text: the application layer owes a landlord a German sentence
    (`CLAUDE.md` § 9.3), and matching English engine prose to produce it would
    make the copy break silently the next time the message is reworded. The
    dates travel as fields so that sentence can name them.
    """

    def __init__(self, window_from: date, window_to: date, maximum_to: date) -> None:
        self.window_from = window_from
        self.window_to = window_to
        self.maximum_to = maximum_to
        super().__init__(
            f"Billing period {window_from.isoformat()}–{window_to.isoformat()} is longer "
            "than 12 months; an Abrechnungszeitraum may not exceed 12 months"
        )
