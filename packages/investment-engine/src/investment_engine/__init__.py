"""Pure, deterministic investment-planning calculations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Protocol, cast

DASH = "—"
INCOMPLETE_BADGE = "Daten unvollständig"
NOT_APPLICABLE_DSCR = "n/a (kein Fremdkapital)"

_KPI_NAMES = (
    "factor",
    "gross_yield",
    "net_yield",
    "dscr",
    "equity_return",
    "cashflow",
    "break_even",
)
_CONVENTION_IDS = tuple(f"14-K{number:02}" for number in range(1, 20))
_BANK_BLOCKS = (
    "header_disclosure",
    "investment",
    "financing_ltv",
    "rent_and_planning_costs",
    "seven_kpis",
    "sensitivity",
    "twelve_month_schedule",
    "assumptions_method",
    "disclosure",
)
_DISCLOSURE = (
    "Vom Vermieter erstellte Zusammenfassung auf Basis eigener Angaben und Annahmen. "
    "Keine Immobilienbewertung, kein Beleihungswert, kein Gutachten, keine "
    "Bonitätsauskunft."
)
_PRODUCT_DISCLAIMER = "rechtskonform, keine Rechts- oder Steuerberatung"
_METHOD_DEFINITIONS = {
    "14-K01": "Kaufpreisfaktor aus Kaufpreis und Ist-Jahreskaltmiete.",
    "14-K02": "Bruttomietrendite aus Ist-Jahreskaltmiete und Kaufpreis.",
    "14-K03": "Nettomietrendite aus NOI und Gesamtinvestition.",
    "14-K04": "DSCR aus NOI und vollem jährlichem Kapitaldienst.",
    "14-K05": "Gebäudeanteil und AfA-Satz sind ohne verknüpfte Daten Annahmen.",
    "14-K06": "Verknüpfte Page-03-Werte gehen Wizard-Werten und Annahmen vor.",
    "14-K07": "Kennzahlen verwenden ein normalisiertes volles Jahr.",
    "14-K08": "Eigenkapitalrendite wird vor und nach Steuer inklusive Tilgung gezeigt.",
    "14-K09": "Rücklage und Mietausfallwagnis mindern nicht die Steuerbasis.",
    "14-K10": "Break-even hält die Eurobeträge der Planungskosten konstant.",
    "14-K11": "Es gibt keine Gesamtwertung oder Kaufempfehlung.",
    "14-K12": "Faktor und Brutto nutzen Ist-Miete, weitere Kennzahlen Effektivmiete.",
    "14-K13": "Der Grenzsteuersatz ist eine bearbeitbare Annahme.",
}


class _InputLike(Protocol):
    facts: Mapping[str, object]


class _RulesLike(Protocol):
    @property
    def default_building_share_bp(self) -> int: ...

    @property
    def default_afa_rate_bp(self) -> int: ...

    @property
    def default_marginal_tax_bp(self) -> int: ...

    @property
    def interest_sensitivity_offsets_bp(self) -> tuple[int, ...]: ...

    @property
    def repayment_sensitivity_steps_bp(self) -> tuple[int, ...]: ...

    @property
    def dscr_amber_hundredths(self) -> int: ...

    @property
    def dscr_green_hundredths(self) -> int: ...

    @property
    def cashflow_amber_cents(self) -> int: ...

    @property
    def cashflow_green_cents(self) -> int: ...

    @property
    def source_evidence(self) -> tuple[str, ...]: ...

    @property
    def rechtsstand(self) -> str: ...

    @property
    def production_blocked(self) -> bool: ...


@dataclass(frozen=True)
class InvestmentInput:
    facts: Mapping[str, object]


@dataclass(frozen=True)
class InvestmentRuleBundle:
    default_building_share_bp: int
    default_afa_rate_bp: int
    default_marginal_tax_bp: int
    interest_sensitivity_offsets_bp: tuple[int, ...]
    repayment_sensitivity_steps_bp: tuple[int, ...]
    dscr_amber_hundredths: int
    dscr_green_hundredths: int
    cashflow_amber_cents: int
    cashflow_green_cents: int
    source_evidence: tuple[str, ...]
    rechtsstand: str
    production_blocked: bool


@dataclass(frozen=True)
class RepaymentControlResult:
    requested_monthly_annuity_cents: int
    first_interest_cents: int
    applied_monthly_annuity_cents: int
    clamped: bool
    guard_text: str


@dataclass(frozen=True)
class InvestmentResult:
    outcome: str
    calculated_values: dict[str, object]
    kpi_slots: dict[str, dict[str, object]]
    source_evidence: tuple[str, ...]
    rechtsstand: str
    production_blocked: bool
    applied_conventions: tuple[str, ...]
    financing_provenance: dict[str, object]
    afa_provenance: dict[str, object]
    tax_provenance: dict[str, object]
    bank_view: dict[str, object]
    interest_sensitivity: tuple[dict[str, object], ...]
    repayment_sensitivity: tuple[dict[str, object], ...]
    repayment_axis_meaning: str
    tax_scenario_label: str
    findings: tuple[str, ...]
    warnings: tuple[str, ...]
    guard: dict[str, object]


@dataclass(frozen=True)
class _Annuity:
    monthly_cents: int
    schedule: tuple[tuple[int, int, int, int], ...]
    annual_interest_cents: int
    annual_repayment_cents: int
    annual_debt_service_cents: int
    closing_balance_cents: int


def _field(value: object, name: str, default: Any = None) -> Any:
    return value.get(name, default) if isinstance(value, Mapping) else getattr(value, name, default)


def _rules(value: InvestmentRuleBundle | _RulesLike | Mapping[str, object]) -> InvestmentRuleBundle:
    interest_offsets = _rule_integer_tuple(
        value,
        "interest_sensitivity_offsets_bp",
        expected_length=5,
    )
    repayment_steps = _rule_integer_tuple(
        value,
        "repayment_sensitivity_steps_bp",
        expected_length=4,
    )
    rule_values = InvestmentRuleBundle(
        default_building_share_bp=_rule_integer(value, "default_building_share_bp"),
        default_afa_rate_bp=_rule_integer(value, "default_afa_rate_bp"),
        default_marginal_tax_bp=_rule_integer(value, "default_marginal_tax_bp"),
        interest_sensitivity_offsets_bp=interest_offsets,
        repayment_sensitivity_steps_bp=repayment_steps,
        dscr_amber_hundredths=_rule_integer(value, "dscr_amber_hundredths"),
        dscr_green_hundredths=_rule_integer(value, "dscr_green_hundredths"),
        cashflow_amber_cents=_rule_integer(value, "cashflow_amber_cents"),
        cashflow_green_cents=_rule_integer(value, "cashflow_green_cents"),
        source_evidence=_rule_string_tuple(value, "source_evidence"),
        rechtsstand=_rule_string(value, "rechtsstand"),
        production_blocked=_rule_boolean(value, "production_blocked"),
    )
    _validate_rule_ranges(rule_values)
    return rule_values


def _rule_integer(value: object, name: str) -> int:
    return _integer_value(_field(value, name), name)


def _rule_integer_tuple(
    value: object,
    name: str,
    *,
    expected_length: int,
) -> tuple[int, ...]:
    raw = _field(value, name)
    if not isinstance(raw, tuple):
        raise TypeError(f"{name} must be a tuple")
    result = tuple(_integer_value(item, name) for item in raw)
    if len(result) != expected_length:
        raise ValueError(f"{name} must contain exactly {expected_length} values")
    return result


def _rule_string_tuple(value: object, name: str) -> tuple[str, ...]:
    raw = _field(value, name)
    if not isinstance(raw, tuple) or any(not isinstance(item, str) for item in raw):
        raise TypeError(f"{name} must be a tuple of strings")
    return raw


def _rule_string(value: object, name: str) -> str:
    raw = _field(value, name)
    if not isinstance(raw, str):
        raise TypeError(f"{name} must be a string")
    return raw


def _rule_boolean(value: object, name: str) -> bool:
    raw = _field(value, name)
    if not isinstance(raw, bool):
        raise TypeError(f"{name} must be a boolean")
    return raw


def _validate_rule_ranges(rules: InvestmentRuleBundle) -> None:
    if not 0 <= rules.default_building_share_bp <= 10_000:
        raise ValueError("default_building_share_bp is outside the documented range")
    if rules.default_afa_rate_bp < 0:
        raise ValueError("default_afa_rate_bp is outside the documented range")
    if not 0 <= rules.default_marginal_tax_bp < 10_000:
        raise ValueError("default_marginal_tax_bp is outside the documented range")
    if (
        tuple(sorted(rules.interest_sensitivity_offsets_bp))
        != (rules.interest_sensitivity_offsets_bp)
        or rules.interest_sensitivity_offsets_bp.count(0) != 1
    ):
        raise ValueError(
            "interest_sensitivity_offsets_bp must be ordered and contain one base value"
        )
    if any(step <= 0 for step in rules.repayment_sensitivity_steps_bp):
        raise ValueError("repayment_sensitivity_steps_bp is outside the documented range")
    if any(
        current >= following
        for current, following in zip(
            rules.repayment_sensitivity_steps_bp,
            rules.repayment_sensitivity_steps_bp[1:],
            strict=False,
        )
    ):
        raise ValueError("repayment_sensitivity_steps_bp must be strictly ordered")
    if rules.dscr_amber_hundredths < 0:
        raise ValueError("dscr_amber_hundredths is outside the documented range")
    if rules.dscr_green_hundredths < 0:
        raise ValueError("dscr_green_hundredths is outside the documented range")
    if rules.dscr_amber_hundredths > rules.dscr_green_hundredths:
        raise ValueError("dscr_amber_hundredths must not exceed dscr_green_hundredths")
    if rules.cashflow_amber_cents > rules.cashflow_green_cents:
        raise ValueError("cashflow_amber_cents must not exceed cashflow_green_cents")
    if not rules.source_evidence or any(not item.strip() for item in rules.source_evidence):
        raise ValueError("source_evidence must contain nonblank values")
    if not rules.rechtsstand.strip():
        raise ValueError("rechtsstand must not be blank")


def _integer_value(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    return value


def _optional_integer(facts: Mapping[str, object], name: str) -> int | None:
    value = facts.get(name)
    if value is None:
        return None
    return _integer_value(value, name)


def _available_input_names(facts: Mapping[str, object]) -> set[str]:
    return {name for name, value in facts.items() if value is not None}


def _validate_public_input(facts: Mapping[str, object]) -> None:
    minimums = {
        "purchase_price_cents": 0,
        "acquisition_costs_cents": 0,
        "monthly_actual_rent_cents": 0,
        "administration_cents": 0,
        "maintenance_cents": 0,
        "reserve_cents": 0,
        "vacancy_risk_cents": 0,
        "equity_cents": 0,
        "loan_cents": 0,
        "interest_bp": 0,
        "initial_repayment_bp": 0,
        "fixed_monthly_annuity_cents": 0,
        "afa_rate_bp": 0,
        "annual_full_afa_cents": 0,
    }
    for name, minimum in minimums.items():
        value = _optional_integer(facts, name)
        if value is not None and value < minimum:
            raise ValueError(f"{name} is outside the documented range")
    bounded = {
        "vacancy_bp": (0, 10_000),
        "building_share_bp": (0, 10_000),
        "marginal_tax_bp": (0, 9_999),
    }
    for name, (minimum, maximum) in bounded.items():
        value = _optional_integer(facts, name)
        if value is not None and not minimum <= value <= maximum:
            raise ValueError(f"{name} is outside the documented range")
    analysis_period = _optional_integer(facts, "analysis_period_months")
    if analysis_period is not None and analysis_period < 0:
        raise ValueError("analysis_period_months is outside the documented range")
    reference = facts.get("afa_reference")
    if reference is not None:
        if not isinstance(reference, Mapping):
            raise TypeError("afa_reference must be a mapping")
        for name in ("afa_basis_cents", "annual_full_afa_cents"):
            nested_value = _optional_integer(reference, name)
            if nested_value is not None and nested_value < 0:
                raise ValueError(f"{name} is outside the documented range")
        if any(
            reference.get(name) is not None for name in ("afa_basis_cents", "annual_full_afa_cents")
        ):
            _required_nonblank_string(reference, "source")
            _required_nonblank_string(reference, "record_version")
    if facts.get("annual_full_afa_cents") is not None:
        _required_nonblank_string(facts, "afa_record_version")
    _validate_bank_header(facts.get("bank_header"))


def _required_nonblank_string(values: Mapping[str, object], name: str) -> str:
    value = values.get(name)
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value.strip():
        raise ValueError(f"{name} must not be blank")
    return value


def _validate_bank_header(raw_header: object) -> None:
    if raw_header is None:
        return
    if not isinstance(raw_header, Mapping):
        raise TypeError("bank_header must be a mapping")
    for name in (
        "address",
        "property_type",
        "creator",
        "export_date",
        "layout_version",
    ):
        value = raw_header.get(name)
        if value is None:
            continue
        if not isinstance(value, str):
            raise TypeError(f"{name} must be a string")
        if not value.strip():
            raise ValueError(f"{name} must not be blank")
    integer_minimums = {
        "year_built": 1,
        "area_sqm_x100": 0,
        "unit_count": 0,
    }
    for name, minimum in integer_minimums.items():
        value = raw_header.get(name)
        if value is None:
            continue
        number = _integer_value(value, name)
        if number < minimum:
            raise ValueError(f"{name} is outside the documented range")


def _validate_complete_input(facts: Mapping[str, object]) -> None:
    _net_required, financing_required = _requirements(facts)
    if financing_required - _available_input_names(facts):
        return
    purchase = _optional_integer(facts, "purchase_price_cents")
    if purchase == 0:
        raise ValueError("purchase_price_cents is outside the documented range")


def _validate_sensitivity_ranges(
    facts: Mapping[str, object],
    rules: InvestmentRuleBundle,
) -> None:
    base_interest = _optional_integer(facts, "interest_bp")
    loan = _optional_integer(facts, "loan_cents")
    if (
        loan is not None
        and loan > 0
        and base_interest is not None
        and any(base_interest + offset < 0 for offset in rules.interest_sensitivity_offsets_bp)
    ):
        raise ValueError("interest_sensitivity_offsets_bp is outside the documented range")


def _half_up(numerator: int, denominator: int) -> int:
    if denominator == 0:
        raise ZeroDivisionError("rounding denominator must not be zero")
    return int(
        (Decimal(numerator) / Decimal(denominator)).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    )


def _annuity(
    *,
    loan_cents: int,
    interest_bp: int,
    initial_repayment_bp: int | None,
    fixed_monthly_annuity_cents: int | None,
) -> _Annuity | RepaymentControlResult:
    if loan_cents == 0:
        schedule = tuple((0, 0, 0, 0) for _ in range(12))
        return _Annuity(0, schedule, 0, 0, 0, 0)
    monthly = fixed_monthly_annuity_cents
    if monthly is None:
        if initial_repayment_bp is None:
            raise ValueError("initial repayment or fixed monthly annuity is required")
        monthly = _half_up(loan_cents * (interest_bp + initial_repayment_bp), 120_000)
    balance = loan_cents
    rows: list[tuple[int, int, int, int]] = []
    for _month in range(12):
        opening = balance
        interest = _half_up(opening * interest_bp, 120_000)
        repayment = monthly - interest
        if repayment <= 0:
            return RepaymentControlResult(
                requested_monthly_annuity_cents=monthly,
                first_interest_cents=interest,
                applied_monthly_annuity_cents=interest + 1,
                clamped=True,
                guard_text="Die Rate wurde angehoben, damit die Tilgung positiv bleibt.",
            )
        balance = opening - repayment
        rows.append((opening, interest, repayment, balance))
    annual_interest = sum(row[1] for row in rows)
    annual_repayment = sum(row[2] for row in rows)
    annual_debt_service = monthly * 12
    if annual_interest + annual_repayment != annual_debt_service:
        raise ArithmeticError("annuity schedule does not reconcile")
    return _Annuity(
        monthly,
        tuple(rows),
        annual_interest,
        annual_repayment,
        annual_debt_service,
        balance,
    )


def clamp_repayment_control(
    *,
    loan_cents: int,
    interest_bp: int,
    requested_monthly_annuity_cents: int,
    rules: InvestmentRuleBundle | _RulesLike | Mapping[str, object],
) -> RepaymentControlResult:
    """Clamp an interactive annuity control at the positive-repayment boundary."""

    _rules(rules)
    loan = _integer_value(loan_cents, "loan_cents")
    interest_rate = _integer_value(interest_bp, "interest_bp")
    requested = _integer_value(requested_monthly_annuity_cents, "requested_monthly_annuity_cents")
    for name, value in (
        ("loan_cents", loan),
        ("interest_bp", interest_rate),
        ("requested_monthly_annuity_cents", requested),
    ):
        if value < 0:
            raise ValueError(f"{name} is outside the documented range")
    first_interest = _half_up(loan * interest_rate, 120_000)
    applied = max(requested, first_interest + 1)
    clamped = applied != requested
    return RepaymentControlResult(
        requested_monthly_annuity_cents=requested,
        first_interest_cents=first_interest,
        applied_monthly_annuity_cents=applied,
        clamped=clamped,
        guard_text=(
            "Die Rate wurde angehoben, damit die Tilgung positiv bleibt."
            if clamped
            else "Die gewählte Rate enthält eine positive Tilgung."
        ),
    )


def _missing_slot(*missing: str) -> dict[str, object]:
    return {
        "status": "unavailable",
        "value": DASH,
        "badge": INCOMPLETE_BADGE,
        "missing_inputs": tuple(missing) or ("required_input",),
    }


def _liquidity_color(value: int, amber: int, green: int) -> str:
    if value < amber:
        return "red"
    if value < green:
        return "amber"
    return "green"


def _afa(
    facts: Mapping[str, object],
    rules: InvestmentRuleBundle,
    total_investment_cents: int,
) -> tuple[int, int, dict[str, object]]:
    reference = facts.get("afa_reference")
    default_share = facts.get("building_share_bp") is None
    default_rate = facts.get("afa_rate_bp") is None
    share = _optional_integer(facts, "building_share_bp")
    rate = _optional_integer(facts, "afa_rate_bp")
    building_share_bp = rules.default_building_share_bp if share is None else share
    afa_rate_bp = rules.default_afa_rate_bp if rate is None else rate
    basis = _half_up(total_investment_cents * building_share_bp, 10_000)
    basis_provenance: dict[str, object] = {
        "source": "acquisition_assumption",
        "record_version": rules.rechtsstand,
        "assumption": True,
        "value_cents": basis,
    }
    if isinstance(reference, Mapping):
        reference_basis = reference.get("afa_basis_cents")
        reference_annual = reference.get("annual_full_afa_cents")
        uses_reference = reference_basis is not None or reference_annual is not None
        source = _required_nonblank_string(reference, "source") if uses_reference else ""
        record_version = (
            _required_nonblank_string(reference, "record_version") if uses_reference else ""
        )
        if reference_basis is not None:
            basis = _integer_value(reference_basis, "afa_basis_cents")
            basis_provenance = {
                "source": source,
                "record_version": record_version,
                "assumption": False,
                "value_cents": basis,
            }
        if reference_annual is not None:
            annual = _integer_value(reference_annual, "annual_full_afa_cents")
            badge = "AfA aus Wizard"
            provenance = {
                "source": source,
                "record_version": record_version,
                "badge": badge,
                "assumption": False,
                "building_share_bp": building_share_bp,
                "afa_rate_bp": afa_rate_bp,
                "basis": basis_provenance,
                "annual_afa": {
                    "source": source,
                    "record_version": record_version,
                    "assumption": False,
                    "value_cents": annual,
                },
            }
            return basis, annual, provenance
    explicit_annual = _optional_integer(facts, "annual_full_afa_cents")
    if explicit_annual is not None:
        record_version = _required_nonblank_string(facts, "afa_record_version")
        provenance = {
            "source": "wizard_input",
            "record_version": record_version,
            "badge": "AfA aus Wizard",
            "assumption": False,
            "building_share_bp": building_share_bp,
            "afa_rate_bp": afa_rate_bp,
            "basis": basis_provenance,
            "annual_afa": {
                "source": "wizard_input",
                "record_version": record_version,
                "assumption": False,
                "value_cents": explicit_annual,
            },
        }
        return basis, explicit_annual, provenance
    annual = _half_up(basis * afa_rate_bp, 10_000)
    return (
        basis,
        annual,
        {
            "source": "acquisition_assumption",
            "record_version": rules.rechtsstand,
            "badge": "AfA-Annahme",
            "assumption": True,
            "uses_runtime_default": default_share or default_rate,
            "building_share_bp": building_share_bp,
            "afa_rate_bp": afa_rate_bp,
            "basis": basis_provenance,
            "annual_afa": {
                "source": "acquisition_assumption",
                "record_version": rules.rechtsstand,
                "assumption": True,
                "value_cents": annual,
            },
        },
    )


def _financing_provenance(facts: Mapping[str, object]) -> dict[str, object]:
    source = str(facts.get("financing_provenance", "annahme"))
    badges = {
        "annahme": "Finanzierung: Annahme",
        "indikativ": "Finanzierung: Indikation",
        "angebot": "Finanzierung: Angebot",
    }
    if source not in badges:
        raise ValueError("unsupported financing provenance")
    return {"source": source, "badge": badges[source]}


def _calculate_complete(
    facts: Mapping[str, object],
    rules: InvestmentRuleBundle,
    *,
    interest_override_bp: int | None = None,
    repayment_override_bp: int | None = None,
) -> tuple[dict[str, object], dict[str, object]] | RepaymentControlResult:
    purchase = _integer_value(facts["purchase_price_cents"], "purchase_price_cents")
    acquisition = _integer_value(facts["acquisition_costs_cents"], "acquisition_costs_cents")
    monthly_rent = _integer_value(facts["monthly_actual_rent_cents"], "monthly_actual_rent_cents")
    vacancy_bp = _integer_value(facts["vacancy_bp"], "vacancy_bp")
    administration = _integer_value(facts["administration_cents"], "administration_cents")
    maintenance = _integer_value(facts["maintenance_cents"], "maintenance_cents")
    reserve = _integer_value(facts["reserve_cents"], "reserve_cents")
    vacancy_risk = _integer_value(facts["vacancy_risk_cents"], "vacancy_risk_cents")
    equity = _optional_integer(facts, "equity_cents")
    loan = _integer_value(facts["loan_cents"], "loan_cents")
    base_interest = _integer_value(facts["interest_bp"], "interest_bp")
    interest_bp = base_interest if interest_override_bp is None else interest_override_bp
    initial_repayment = _optional_integer(facts, "initial_repayment_bp")
    if repayment_override_bp is not None:
        initial_repayment = repayment_override_bp
    fixed_annuity = _optional_integer(facts, "fixed_monthly_annuity_cents")
    if repayment_override_bp is not None:
        fixed_annuity = None
    total_investment = purchase + acquisition
    annual_actual = monthly_rent * 12
    effective = _half_up(annual_actual * (10_000 - vacancy_bp), 10_000)
    cash_costs = administration + maintenance + reserve + vacancy_risk
    deductible_costs = administration + maintenance
    noi = effective - cash_costs
    annuity = _annuity(
        loan_cents=loan,
        interest_bp=interest_bp,
        initial_repayment_bp=initial_repayment,
        fixed_monthly_annuity_cents=fixed_annuity,
    )
    if isinstance(annuity, RepaymentControlResult):
        return annuity
    afa_basis, annual_afa, afa_provenance = _afa(facts, rules, total_investment)
    marginal_value = _optional_integer(facts, "marginal_tax_bp")
    marginal_tax_bp = rules.default_marginal_tax_bp if marginal_value is None else marginal_value
    tax_base = effective - deductible_costs - annuity.annual_interest_cents - annual_afa
    tax = _half_up(tax_base * marginal_tax_bp, 10_000)
    cashflow_before_year = effective - cash_costs - annuity.annual_debt_service_cents
    cashflow_after_year = cashflow_before_year - tax
    cashflow_before_month = _half_up(cashflow_before_year, 12)
    cashflow_after_month = _half_up(cashflow_after_year, 12)
    factor = _half_up(purchase * 100, annual_actual)
    gross = _half_up(annual_actual * 10_000, purchase)
    net = _half_up(noi * 10_000, total_investment)
    dscr = (
        _half_up(noi * 100, annuity.annual_debt_service_cents)
        if annuity.annual_debt_service_cents != 0
        else None
    )
    break_even_before_year = cash_costs + annuity.annual_debt_service_cents
    deductible_relief = _half_up(
        marginal_tax_bp * (deductible_costs + annuity.annual_interest_cents + annual_afa),
        10_000,
    )
    break_even_after_year = _half_up(
        (cash_costs + annuity.annual_debt_service_cents - deductible_relief) * 10_000,
        10_000 - marginal_tax_bp,
    )
    values: dict[str, object] = {
        "total_investment_cents": total_investment,
        "annual_actual_rent_cents": annual_actual,
        "effective_rent_cents": effective,
        "cash_costs_cents": cash_costs,
        "deductible_costs_cents": deductible_costs,
        "noi_cents": noi,
        "monthly_annuity_cents": annuity.monthly_cents,
        "schedule": annuity.schedule,
        "annual_interest_cents": annuity.annual_interest_cents,
        "annual_repayment_cents": annuity.annual_repayment_cents,
        "annual_debt_service_cents": annuity.annual_debt_service_cents,
        "closing_balance_cents": annuity.closing_balance_cents,
        "afa_basis_cents": afa_basis,
        "annual_afa_cents": annual_afa,
        "tax_base_cents": tax_base,
        "tax_cents": tax,
        "cashflow_before_year_cents": cashflow_before_year,
        "cashflow_after_year_cents": cashflow_after_year,
        "cashflow_before_month_cents": cashflow_before_month,
        "cashflow_after_month_cents": cashflow_after_month,
        "factor_hundredths": factor,
        "gross_yield_bp": gross,
        "net_yield_bp": net,
        "dscr_hundredths": dscr,
        "break_even_before_year_cents": break_even_before_year,
        "break_even_after_year_cents": break_even_after_year,
        "break_even_before_month_cents": _half_up(break_even_before_year, 12),
        "break_even_after_month_cents": _half_up(break_even_after_year, 12),
        "ltv_purchase_bp": _half_up(loan * 10_000, purchase),
        "ltv_total_bp": _half_up(loan * 10_000, total_investment),
        "normalized_period_months": 12,
        "interest_bp": interest_bp,
        "initial_repayment_bp": initial_repayment,
    }
    if equity is not None and equity != 0:
        values["equity_return_before_bp"] = _half_up(
            (cashflow_before_year + annuity.annual_repayment_cents) * 10_000,
            equity,
        )
        values["equity_return_after_bp"] = _half_up(
            (cashflow_after_year + annuity.annual_repayment_cents) * 10_000,
            equity,
        )
        values["cash_on_cash_after_bp"] = _half_up(
            cashflow_after_year * 10_000,
            equity,
        )
    tax_provenance = {
        "source": "flat_rate_scenario",
        "assumption": True,
        "uses_runtime_default": marginal_value is None,
        "marginal_tax_bp": marginal_tax_bp,
    }
    return values, {"afa": afa_provenance, "tax": tax_provenance}


def _base_values(facts: Mapping[str, object]) -> dict[str, object]:
    values: dict[str, object] = {"normalized_period_months": 12}
    purchase = _optional_integer(facts, "purchase_price_cents")
    monthly_rent = _optional_integer(facts, "monthly_actual_rent_cents")
    acquisition = _optional_integer(facts, "acquisition_costs_cents")
    if purchase is not None and acquisition is not None:
        values["total_investment_cents"] = purchase + acquisition
    if monthly_rent is not None:
        annual = monthly_rent * 12
        values["annual_actual_rent_cents"] = annual
        vacancy = _optional_integer(facts, "vacancy_bp")
        if vacancy is not None:
            values["effective_rent_cents"] = _half_up(annual * (10_000 - vacancy), 10_000)
    if purchase is not None and purchase > 0 and monthly_rent is not None and monthly_rent > 0:
        annual = monthly_rent * 12
        values["factor_hundredths"] = _half_up(purchase * 100, annual)
        values["gross_yield_bp"] = _half_up(annual * 10_000, purchase)
    net_required, _financing_required = _requirements(facts)
    if (
        not (net_required - _available_input_names(facts))
        and purchase is not None
        and acquisition is not None
        and monthly_rent is not None
    ):
        annual = monthly_rent * 12
        vacancy = _integer_value(facts["vacancy_bp"], "vacancy_bp")
        effective = _half_up(annual * (10_000 - vacancy), 10_000)
        cash_costs = sum(
            _integer_value(facts[name], name)
            for name in (
                "administration_cents",
                "maintenance_cents",
                "reserve_cents",
                "vacancy_risk_cents",
            )
        )
        deductible_costs = _integer_value(
            facts["administration_cents"], "administration_cents"
        ) + _integer_value(facts["maintenance_cents"], "maintenance_cents")
        total = purchase + acquisition
        noi = effective - cash_costs
        values.update(
            effective_rent_cents=effective,
            cash_costs_cents=cash_costs,
            deductible_costs_cents=deductible_costs,
            noi_cents=noi,
        )
        if total != 0:
            values["net_yield_bp"] = _half_up(noi * 10_000, total)
    return values


def _requirements(facts: Mapping[str, object]) -> tuple[set[str], set[str]]:
    rent_required = {"purchase_price_cents", "monthly_actual_rent_cents"}
    net_required = rent_required | {
        "acquisition_costs_cents",
        "vacancy_bp",
        "administration_cents",
        "maintenance_cents",
        "reserve_cents",
        "vacancy_risk_cents",
    }
    financing_required = net_required | {"loan_cents", "interest_bp"}
    if facts.get("fixed_monthly_annuity_cents") is None:
        financing_required.add("initial_repayment_bp")
    return net_required, financing_required


def _kpi_slots(
    facts: Mapping[str, object],
    values: Mapping[str, object],
    rules: InvestmentRuleBundle,
) -> dict[str, dict[str, object]]:
    purchase = _optional_integer(facts, "purchase_price_cents")
    rent = _optional_integer(facts, "monthly_actual_rent_cents")
    factor_ready = purchase is not None and purchase > 0 and rent is not None and rent > 0
    net_required, financing_required = _requirements(facts)
    available_inputs = _available_input_names(facts)
    missing_net = tuple(sorted(net_required - available_inputs))
    net_ready = factor_ready and not missing_net
    missing_financing = tuple(sorted(financing_required - available_inputs))
    financing_ready = net_ready and not missing_financing
    equity = _optional_integer(facts, "equity_cents")
    missing_equity = missing_financing + (
        () if equity is not None and equity != 0 else ("equity_cents",)
    )
    slots: dict[str, dict[str, object]] = {}
    if factor_ready:
        slots["factor"] = {"status": "available", "value": values["factor_hundredths"]}
        slots["gross_yield"] = {"status": "available", "value": values["gross_yield_bp"]}
    else:
        missing_rent = tuple(
            name
            for name, ready in (
                ("purchase_price_cents", purchase is not None and purchase > 0),
                ("monthly_actual_rent_cents", rent is not None and rent > 0),
            )
            if not ready
        )
        slots["factor"] = _missing_slot(*missing_rent)
        slots["gross_yield"] = _missing_slot(*missing_rent)
    slots["net_yield"] = (
        {"status": "available", "value": values["net_yield_bp"]}
        if net_ready and "net_yield_bp" in values
        else _missing_slot(*(missing_net or ("valid_price_and_rent",)))
    )
    loan = _optional_integer(facts, "loan_cents")
    if financing_ready and loan == 0:
        slots["dscr"] = {"status": "not_applicable", "value": NOT_APPLICABLE_DSCR}
    elif financing_ready and "dscr_hundredths" in values:
        dscr = _integer_value(values["dscr_hundredths"], "dscr_hundredths")
        slots["dscr"] = {
            "status": "available",
            "value": dscr,
            "color": _liquidity_color(
                dscr,
                rules.dscr_amber_hundredths,
                rules.dscr_green_hundredths,
            ),
        }
    else:
        slots["dscr"] = _missing_slot(*(missing_financing or ("valid_net_inputs",)))
    if financing_ready and not missing_equity and "equity_return_after_bp" in values:
        slots["equity_return"] = {
            "status": "available",
            "value": values["equity_return_after_bp"],
            "before_tax": values["equity_return_before_bp"],
            "after_tax": values["equity_return_after_bp"],
            "display_columns": (
                "before_tax_including_repayment",
                "after_tax_including_repayment",
            ),
            "tooltip": "after_tax_excluding_repayment",
        }
    else:
        slots["equity_return"] = _missing_slot(*missing_equity)
    if financing_ready and "cashflow_after_month_cents" in values:
        after_cashflow = _integer_value(
            values["cashflow_after_month_cents"], "cashflow_after_month_cents"
        )
        slots["cashflow"] = {
            "status": "available",
            "value": after_cashflow,
            "before_tax": values["cashflow_before_month_cents"],
            "after_tax": after_cashflow,
            "color": _liquidity_color(
                after_cashflow,
                rules.cashflow_amber_cents,
                rules.cashflow_green_cents,
            ),
        }
        slots["break_even"] = {
            "status": "available",
            "value": values["break_even_after_month_cents"],
            "before_tax": values["break_even_before_month_cents"],
            "after_tax": values["break_even_after_month_cents"],
        }
    else:
        slots["cashflow"] = _missing_slot(*(missing_financing or ("valid_net_inputs",)))
        slots["break_even"] = _missing_slot(*(missing_financing or ("valid_net_inputs",)))
    return slots


def _bank_view(
    facts: Mapping[str, object],
    values: Mapping[str, object],
    slots: Mapping[str, Mapping[str, object]],
    financing: Mapping[str, object],
    afa: Mapping[str, object],
    tax: Mapping[str, object],
    interest_sensitivity: tuple[dict[str, object], ...],
    repayment_sensitivity: tuple[dict[str, object], ...],
    rules: InvestmentRuleBundle,
) -> dict[str, object]:
    raw_header = facts.get("bank_header")
    header: dict[str, object] = {}
    layout_version: object | None = None
    if isinstance(raw_header, Mapping):
        approved_keys = (
            "address",
            "property_type",
            "year_built",
            "area_sqm_x100",
            "unit_count",
            "creator",
            "export_date",
            "layout_version",
        )
        header = {key: raw_header[key] for key in approved_keys if raw_header.get(key) is not None}
        layout_version = header.get("layout_version")
    loan = _optional_integer(facts, "loan_cents")
    has_debt = loan is not None and loan > 0
    ltv_purchase: object = values.get("ltv_purchase_bp", DASH) if has_debt else DASH
    ltv_total: object = values.get("ltv_total_bp", DASH) if has_debt else DASH
    ltv_note = (
        "Berechnung zum Kaufpreis, nicht zum Beleihungswert."
        if has_debt
        else "Kein Fremdkapital; der Auslauf ist nicht anwendbar."
    )
    investment = {
        "purchase_price_cents": facts.get("purchase_price_cents", DASH),
        "acquisition_costs_cents": facts.get("acquisition_costs_cents", DASH),
        "total_investment_cents": values.get("total_investment_cents", DASH),
    }
    financing_ltv = {
        "equity_cents": facts.get("equity_cents", DASH),
        "loan_cents": facts.get("loan_cents", DASH),
        "interest_bp": facts.get("interest_bp", DASH),
        "initial_repayment_bp": facts.get("initial_repayment_bp", DASH),
        "fixed_monthly_annuity_cents": facts.get("fixed_monthly_annuity_cents", DASH),
        "monthly_annuity_cents": values.get("monthly_annuity_cents", DASH),
        "ltv_purchase_bp": ltv_purchase,
        "ltv_total_bp": ltv_total,
        "ltv_label": "Auslauf zum Kaufpreis, nicht zum Beleihungswert",
        "ltv_note": ltv_note,
        "provenance": dict(financing),
    }
    rent_and_costs = {
        "monthly_actual_rent_cents": facts.get("monthly_actual_rent_cents", DASH),
        "vacancy_bp": facts.get("vacancy_bp", DASH),
        "administration_cents": facts.get("administration_cents", DASH),
        "maintenance_cents": facts.get("maintenance_cents", DASH),
        "reserve_cents": facts.get("reserve_cents", DASH),
        "vacancy_risk_cents": facts.get("vacancy_risk_cents", DASH),
        "annual_actual_rent_cents": values.get("annual_actual_rent_cents", DASH),
        "effective_rent_cents": values.get("effective_rent_cents", DASH),
        "cash_costs_cents": values.get("cash_costs_cents", DASH),
        "deductible_costs_cents": values.get("deductible_costs_cents", DASH),
    }
    assumptions_method = {
        "convention_definitions": dict(_METHOD_DEFINITIONS),
        "afa_provenance": dict(afa),
        "financing_provenance": dict(financing),
        "tax_provenance": dict(tax),
        "source_evidence": tuple(sorted(rules.source_evidence, key=str)),
        "rechtsstand": rules.rechtsstand,
        "production_blocked": rules.production_blocked,
    }
    header_disclosure = {
        "header": header,
        "product_disclaimer": _PRODUCT_DISCLAIMER,
        "artifact_disclosure": _DISCLOSURE,
    }
    result = {
        "renderable": True,
        "recalculated": False,
        "blocks": _BANK_BLOCKS,
        "header": header,
        "header_disclosure": header_disclosure,
        "investment": investment,
        "financing_ltv": financing_ltv,
        "rent_and_planning_costs": rent_and_costs,
        "sensitivity": {
            "interest": interest_sensitivity,
            "repayment": repayment_sensitivity,
        },
        "twelve_month_schedule": values.get("schedule", DASH),
        "assumptions_method": assumptions_method,
        "ltv_label": "Auslauf zum Kaufpreis, nicht zum Beleihungswert",
        "ltv_purchase_bp": ltv_purchase,
        "ltv_total_bp": ltv_total,
        "ltv_note": ltv_note,
        "seven_kpis": {name: dict(slot) for name, slot in slots.items()},
        "financing_provenance": dict(financing),
        "afa_provenance": dict(afa),
        "tax_provenance": dict(tax),
        "renter_names_included": False,
        "product_disclaimer": _PRODUCT_DISCLAIMER,
        "disclosure": _DISCLOSURE,
    }
    if layout_version is not None:
        result["layout_version"] = layout_version
    return result


def _interest_sensitivity(
    facts: Mapping[str, object],
    rules: InvestmentRuleBundle,
) -> tuple[dict[str, object], ...]:
    base_interest = _integer_value(facts["interest_bp"], "interest_bp")
    rows: list[dict[str, object]] = []
    for offset in rules.interest_sensitivity_offsets_bp:
        interest = base_interest + offset
        outcome = _calculate_complete(facts, rules, interest_override_bp=interest)
        if isinstance(outcome, RepaymentControlResult):
            rows.append(
                {
                    "interest_bp": interest,
                    "is_base": offset == 0,
                    "outcome": "hard_block",
                    "guard": {
                        "first_interest_cents": outcome.first_interest_cents,
                        "first_repayment_cents": (
                            outcome.requested_monthly_annuity_cents - outcome.first_interest_cents
                        ),
                        "guard_text": outcome.guard_text,
                    },
                }
            )
            continue
        values, _provenance = outcome
        dscr = _integer_value(values["dscr_hundredths"], "dscr_hundredths")
        cashflow = _integer_value(
            values["cashflow_after_month_cents"], "cashflow_after_month_cents"
        )
        rows.append(
            {
                "interest_bp": interest,
                "is_base": offset == 0,
                **values,
                "dscr_color": _liquidity_color(
                    dscr,
                    rules.dscr_amber_hundredths,
                    rules.dscr_green_hundredths,
                ),
                "cashflow_color": _liquidity_color(
                    cashflow,
                    rules.cashflow_amber_cents,
                    rules.cashflow_green_cents,
                ),
            }
        )
    return tuple(rows)


def _repayment_sensitivity(
    facts: Mapping[str, object],
    rules: InvestmentRuleBundle,
) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for repayment in rules.repayment_sensitivity_steps_bp:
        outcome = _calculate_complete(facts, rules, repayment_override_bp=repayment)
        if isinstance(outcome, RepaymentControlResult):
            rows.append(
                {
                    "initial_repayment_bp": repayment,
                    "outcome": "hard_block",
                    "guard": {
                        "first_interest_cents": outcome.first_interest_cents,
                        "first_repayment_cents": (
                            outcome.requested_monthly_annuity_cents - outcome.first_interest_cents
                        ),
                        "guard_text": outcome.guard_text,
                    },
                }
            )
            continue
        values, _provenance = outcome
        dscr = _integer_value(values["dscr_hundredths"], "dscr_hundredths")
        cashflow = _integer_value(
            values["cashflow_after_month_cents"], "cashflow_after_month_cents"
        )
        rows.append(
            {
                **values,
                "initial_repayment_bp": repayment,
                "dscr_color": _liquidity_color(
                    dscr,
                    rules.dscr_amber_hundredths,
                    rules.dscr_green_hundredths,
                ),
                "cashflow_color": _liquidity_color(
                    cashflow,
                    rules.cashflow_amber_cents,
                    rules.cashflow_green_cents,
                ),
            }
        )
    return tuple(rows)


def calculate_investment_snapshot(
    investment_input: InvestmentInput | _InputLike | Mapping[str, object],
    rules: InvestmentRuleBundle | _RulesLike | Mapping[str, object],
) -> InvestmentResult:
    """Calculate a full-year planning snapshot from normalized caller facts."""

    facts = _field(investment_input, "facts")
    if not isinstance(facts, Mapping):
        raise TypeError("facts must be a mapping")
    _validate_public_input(facts)
    rule_values = _rules(rules)
    _validate_complete_input(facts)
    _validate_sensitivity_ranges(facts, rule_values)
    evidence = tuple(sorted(rule_values.source_evidence, key=str))
    financing = _financing_provenance(facts)
    analysis_period = facts.get("analysis_period_months")
    findings = (
        ("non_12_month_period_inapplicable",)
        if (12 if analysis_period is None else analysis_period) != 12
        else ()
    )
    purchase = _optional_integer(facts, "purchase_price_cents")
    acquisition = _optional_integer(facts, "acquisition_costs_cents")
    warnings = (
        ("unrealistic_acquisition_costs",)
        if purchase is not None and acquisition is not None and acquisition > purchase
        else ()
    )
    _net_required, financing_required = _requirements(facts)
    factor_values = _base_values(facts)
    complete = not (financing_required - _available_input_names(facts))
    full_outcome: tuple[dict[str, object], dict[str, object]] | RepaymentControlResult | None = None
    loan_value = _optional_integer(facts, "loan_cents")
    interest_value = _optional_integer(facts, "interest_bp")
    has_annuity_input = (
        facts.get("fixed_monthly_annuity_cents") is not None
        or facts.get("initial_repayment_bp") is not None
    )
    if loan_value is not None and interest_value is not None and has_annuity_input:
        preflight = _annuity(
            loan_cents=loan_value,
            interest_bp=interest_value,
            initial_repayment_bp=_optional_integer(facts, "initial_repayment_bp"),
            fixed_monthly_annuity_cents=_optional_integer(facts, "fixed_monthly_annuity_cents"),
        )
        if isinstance(preflight, RepaymentControlResult):
            full_outcome = preflight
    if complete and not isinstance(full_outcome, RepaymentControlResult):
        purchase_value = _optional_integer(facts, "purchase_price_cents")
        rent_value = _optional_integer(facts, "monthly_actual_rent_cents")
        if (
            purchase_value is not None
            and purchase_value > 0
            and rent_value is not None
            and rent_value > 0
        ):
            full_outcome = _calculate_complete(facts, rule_values)
    if isinstance(full_outcome, RepaymentControlResult):
        guard = {
            "first_interest_cents": full_outcome.first_interest_cents,
            "first_repayment_cents": (
                full_outcome.requested_monthly_annuity_cents - full_outcome.first_interest_cents
            ),
            "guard_text": full_outcome.guard_text,
        }
        return InvestmentResult(
            outcome="hard_block",
            calculated_values={},
            kpi_slots={},
            source_evidence=evidence,
            rechtsstand=rule_values.rechtsstand,
            production_blocked=rule_values.production_blocked,
            applied_conventions=_CONVENTION_IDS,
            financing_provenance=financing,
            afa_provenance={},
            tax_provenance={},
            bank_view={},
            interest_sensitivity=(),
            repayment_sensitivity=(),
            repayment_axis_meaning="structure_not_stress",
            tax_scenario_label="flat_rate_scenario_only",
            findings=findings,
            warnings=warnings,
            guard=guard,
        )
    if full_outcome is None:
        values = factor_values
        afa_provenance: dict[str, object] = {}
        tax_provenance: dict[str, object] = {}
    else:
        values, provenance = full_outcome
        afa_provenance = dict(cast(Mapping[str, object], provenance["afa"]))
        tax_provenance = dict(cast(Mapping[str, object], provenance["tax"]))
    slots = _kpi_slots(facts, values, rule_values)
    sensitivities_ready = full_outcome is not None and loan_value is not None and loan_value > 0
    interest_rows = _interest_sensitivity(facts, rule_values) if sensitivities_ready else ()
    repayment_rows = _repayment_sensitivity(facts, rule_values) if sensitivities_ready else ()
    bank = _bank_view(
        facts,
        values,
        slots,
        financing,
        afa_provenance,
        tax_provenance,
        interest_rows,
        repayment_rows,
        rule_values,
    )
    return InvestmentResult(
        outcome="calculated",
        calculated_values=values,
        kpi_slots=slots,
        source_evidence=evidence,
        rechtsstand=rule_values.rechtsstand,
        production_blocked=rule_values.production_blocked,
        applied_conventions=_CONVENTION_IDS,
        financing_provenance=financing,
        afa_provenance=afa_provenance,
        tax_provenance=tax_provenance,
        bank_view=bank,
        interest_sensitivity=interest_rows,
        repayment_sensitivity=repayment_rows,
        repayment_axis_meaning="structure_not_stress",
        tax_scenario_label="flat_rate_scenario_only",
        findings=findings,
        warnings=warnings,
        guard={},
    )


__all__ = [
    "InvestmentInput",
    "InvestmentResult",
    "InvestmentRuleBundle",
    "RepaymentControlResult",
    "calculate_investment_snapshot",
    "clamp_repayment_control",
]
