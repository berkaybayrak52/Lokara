"""Pure, cent-exact AfA calculations from normalized caller facts and rules."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Protocol


class _InputLike(Protocol):
    facts: Mapping[str, object]


class _RulesLike(Protocol):
    @property
    def linear_rates_bp(self) -> tuple[tuple[int | None, int | None, int], ...]: ...

    @property
    def guard_rate_bp(self) -> int: ...

    @property
    def market_disagio_limit_bp(self) -> int: ...

    @property
    def source_evidence(self) -> tuple[str, ...]: ...

    @property
    def rechtsstand(self) -> str: ...

    @property
    def production_blocked(self) -> bool: ...


@dataclass(frozen=True)
class AfaInput:
    facts: Mapping[str, object]


@dataclass(frozen=True)
class AfaRuleBundle:
    linear_rates_bp: tuple[tuple[int | None, int | None, int], ...]
    guard_rate_bp: int
    market_disagio_limit_bp: int
    source_evidence: tuple[str, ...]
    rechtsstand: str
    production_blocked: bool


@dataclass(frozen=True)
class AfaFinding:
    code: str
    message: str


@dataclass(frozen=True)
class AfaResult:
    calculated_values: dict[str, object]
    findings: tuple[AfaFinding, ...]
    source_evidence: tuple[str, ...]
    rechtsstand: str
    production_blocked: bool
    tax_year: int
    evidence_limit: str | None = None
    page04_handoff: dict[str, object] | None = None


def _field(value: object, name: str, default: Any = None) -> Any:
    return value.get(name, default) if isinstance(value, Mapping) else getattr(value, name, default)


def _integer(facts: Mapping[str, object], name: str) -> int:
    value = facts[name]
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    return value


def _calculated_integer(values: Mapping[str, object], name: str) -> int:
    value = values[name]
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"calculated {name} must be an integer")
    return value


def _half_up(numerator: int, denominator: int) -> int:
    return int(
        (Decimal(numerator) / Decimal(denominator)).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    )


def _iso_date(value: object) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise TypeError("date must be ISO text or a date")


def _selected_rate(rules: _RulesLike, year: int) -> int:
    for first_year, last_year, rate_bp in rules.linear_rates_bp:
        if (first_year is None or year >= first_year) and (last_year is None or year <= last_year):
            return rate_bp
    raise ValueError(f"no linear AfA rate resolved for completion year {year}")


def _annual(basis: int, rate_bp: int) -> int:
    return _half_up(basis * rate_bp, 10_000)


def _acquisition(facts: Mapping[str, object]) -> dict[str, int]:
    ancillary = sum(
        _integer(facts, key)
        for key in (
            "grunderwerbsteuer_cents",
            "notar_grundbuch_cents",
            "makler_cents",
            "sonstige_ank_cents",
        )
    )
    return {
        "ancillary": ancillary,
        "acquisition_cost": (
            _integer(facts, "kaufpreis_cents") - _integer(facts, "movable_assets_cents") + ancillary
        ),
        "excluded_financing_cost_cents": _integer(facts, "grundschuld_notar_cents"),
    }


def _bmf(facts: Mapping[str, object], acquisition: int) -> dict[str, object]:
    land_value = _integer(facts, "land_area_sqm") * _integer(facts, "land_value_cents_per_sqm")
    area_factor = 135 if facts.get("building_type") == "mfh" else 125
    bgf_x100 = _half_up(_integer(facts, "living_area_sqm_x100") * area_factor, 100)
    nhk = _integer(facts, "nhk_cents_per_sqm_bgf")
    index_bp = _integer(facts, "price_index_bp")
    indexed = _half_up(nhk * index_bp, 10_000)
    normal = _half_up(bgf_x100 * indexed, 100)
    useful_life = _integer(facts, "useful_life_years")
    age = max(0, _integer(facts, "valuation_year") - _integer(facts, "year_built"))
    residual_bp = max(
        _integer(facts, "minimum_residual_bp"),
        _half_up(max(0, useful_life - age) * 10_000, useful_life),
    )
    building_value = _half_up(normal * residual_bp, 10_000)
    property_value = building_value + land_value
    if property_value <= 0:
        return {"result": "hard_block"}
    building_cost = _half_up(acquisition * building_value, property_value)
    return {
        "land_value": land_value,
        "bgf_x100": bgf_x100,
        "nhk_cents_m2": nhk,
        "price_index_bp": index_bp,
        "indexed_nhk": indexed,
        "normal_production_value": normal,
        "age_years": age,
        "useful_life_years": useful_life,
        "building_value": building_value,
        "property_value": property_value,
        "acquisition_cost": acquisition,
        "building_cost": building_cost,
        "land_cost": acquisition - building_cost,
        "production_blocked": True,
    }


def _loan(facts: Mapping[str, object], special_at: int | None = None) -> dict[str, object]:
    nominal = _integer(facts, "nominal_cents")
    interest_bp = _integer(facts, "interest_bp")
    count = _integer(facts, "installment_count")
    annuity = _half_up(nominal * (interest_bp + _integer(facts, "initial_repayment_bp")), 120_000)
    balance = nominal
    interests: list[int] = []
    repayments: list[int] = []
    for installment in range(1, count + 1):
        if special_at == installment:
            balance -= _integer(facts, "special_repayment_cents")
        interest = _half_up(balance * interest_bp, 120_000)
        repayment = annuity - interest
        if repayment <= 0:
            return {"result": "hard_block"}
        interests.append(interest)
        repayments.append(repayment)
        balance -= repayment
    return {
        "monthly_annuity": annuity,
        "interest_schedule": tuple(interests),
        "repayment_schedule": tuple(repayments),
        "interest_year": sum(interests),
        "repayment_year": sum(repayments),
        "closing_balance": balance,
    }


def _series(facts: Mapping[str, object], rules: _RulesLike) -> dict[str, object]:
    basis = _integer(facts, "building_basis_cents")
    annual = _annual(basis, _selected_rate(rules, _integer(facts, "year_built")))
    first = _half_up(annual * (13 - _iso_date(facts["transfer_date"]).month), 12)
    full_year_count, final_residual = divmod(basis - first, annual)
    return {
        "first_year_afa": first,
        "full_year_afa": annual,
        "full_year_count": full_year_count,
        "final_year": _integer(facts, "series_start_year") + full_year_count + 1,
        "final_residual": final_residual,
        "final_book_value": 0,
    }


def _guard_reclassification(facts: Mapping[str, object], rules: _RulesLike) -> dict[str, object]:
    basis = _integer(facts, "building_basis_cents")
    raw = facts["counted_measures_by_year"]
    if not isinstance(raw, Sequence):
        raise TypeError("year measures must be a sequence")
    measures = tuple((int(item[0]), int(item[1])) for item in raw)
    running = basis
    bases: list[tuple[int, int]] = []
    new_values: list[int] = []
    old_values: list[int] = []
    rate = _integer(facts, "rate_bp")
    for index, (year, amount) in enumerate(measures):
        running += amount
        bases.append((year, running))
        new = _annual(running, rate)
        old = _annual(basis, rate)
        if index == 0:
            new, old = _half_up(new * 10, 12), _half_up(old * 10, 12)
        new_values.append(new)
        old_values.append(old)
    return {
        "threshold": _half_up(basis * rules.guard_rate_bp, 10_000),
        "cumulative": sum(amount for _, amount in measures),
        "basis_by_year": tuple(bases),
        "new_afa": tuple(new_values),
        "afa_delta": tuple(new - old for new, old in zip(new_values, old_values, strict=True)),
    }


def _measures(facts: Mapping[str, object], rules: _RulesLike) -> dict[str, object]:
    raw = facts["measures"]
    if not isinstance(raw, Sequence):
        raise TypeError("measures must be a sequence")
    items = tuple(item for item in raw if isinstance(item, Mapping))
    previous = _integer(facts, "previous_counted_cents")
    if items and "class" in items[0]:
        classes = {str(item.get("class")) for item in items}
        if classes == {"erweiterung"}:
            return {
                "countable_for_15_percent": False,
                "later_production_cost": sum(int(item["net_cents"]) for item in items),
                "cumulative": previous,
            }
        if classes == {"jaehrlichUeblich"}:
            annual_parts = tuple(int(item["net_cents"]) for item in items[:3])
            return {
                "annual_total": sum(annual_parts),
                "three_year_total": sum(int(item["net_cents"]) for item in items),
                "countable_for_15_percent": False,
                "cumulative": previous,
            }
        raise ValueError("unsupported normalized measure classes")
    transfer = _iso_date(facts["transfer_date"])
    window_end = transfer.replace(year=transfer.year + 3) - timedelta(days=1)
    amounts = [int(item["net_cents"]) for item in items]
    inside = [
        int(item["net_cents"]) for item in items if _iso_date(item["leistung_bis"]) <= window_end
    ]
    threshold = _half_up(_integer(facts, "building_basis_cents") * rules.guard_rate_bp, 10_000)
    cumulative = previous + sum(inside)
    return {
        "cumulative": cumulative,
        "buffer": threshold - cumulative,
        "counterfactual_cumulative": previous + sum(amounts),
        "required_date_field": "leistungBis",
    }


def _page04_handoff() -> dict[str, object]:
    return {
        "production_blocked": True,
        "deduplicated": False,
        "mapping_status": "unresolved",
    }


def _calculate(facts: Mapping[str, object], rules: _RulesLike) -> dict[str, object]:
    route = facts.get("allocation_route")
    if route == "gutachten" and facts.get("report_building_share_bp") is None:
        return {}
    if route == "bmf" and "land_value_cents_per_sqm" not in facts:
        return {}
    if route == "bmf" and facts.get("land_value_cents_per_sqm") is None:
        return {"result": "hard_block"}
    if "self_use_periods" in facts or facts.get("year_built", object()) is None:
        return {"result": "hard_block"}
    if "notary_date" in facts and facts.get("transfer_date") is None:
        return {"result": "hard_block"}
    if facts.get("acquisition_type") == "unentgeltlich":
        basis = _integer(facts, "predecessor_basis_cents")
        annual = _annual(basis, _integer(facts, "rate_bp"))
        opening = basis - _integer(facts, "predecessor_accumulated_afa_cents")
        predecessor = _half_up(annual * _integer(facts, "predecessor_months"), 12)
        return {
            "annual_afa": annual,
            "opening_book_value": opening,
            "predecessor_share": predecessor,
            "successor_share": annual - predecessor,
        }
    if "remaining_life_years" in facts:
        basis = _integer(facts, "building_basis_cents")
        years = _integer(facts, "remaining_life_years")
        if facts.get("report_qualification") not in {"oebuv", "zertifiziert"}:
            return {"result": "hard_block"}
        annual = _half_up(basis, years)
        return {"annual_afa": annual, "final_residual": basis - annual * years}
    if "nominal_cents" in facts and "interest_bp" in facts:
        if "special_repayment_cents" not in facts:
            return _loan(facts)
        loan_result = _loan(facts, _integer(facts, "special_repayment_before_installment"))
        baseline = _loan(facts)
        loan_result["interest_saving"] = _calculated_integer(
            baseline, "interest_year"
        ) - _calculated_integer(loan_result, "interest_year")
        loan_result["total_repayment"] = _calculated_integer(
            loan_result, "repayment_year"
        ) + _integer(facts, "special_repayment_cents")
        return loan_result
    if "market_disagio_cents" in facts:
        nominal = _integer(facts, "nominal_cents")
        market = _integer(facts, "market_disagio_cents")
        if market > _half_up(nominal * rules.market_disagio_limit_bp, 10_000):
            return {"result": "hard_block"}
        total = _integer(facts, "non_market_disagio_cents")
        years = _integer(facts, "fixed_interest_years")
        annual = _half_up(total, years)
        first = _half_up(annual * _integer(facts, "first_year_months"), 12)
        return {
            "market_first_year_deduction": market,
            "non_market_first_year": first,
            "non_market_final_residual": total - first - annual * (years - 1),
        }
    if "interest_cents" in facts:
        interest = _integer(facts, "interest_cents")
        deductible = _half_up(
            interest * _integer(facts, "rented_area_months_x100"),
            _integer(facts, "total_area_months_x100"),
        )
        return {
            "proportional_deductible": deductible,
            "proportional_non_deductible": interest - deductible,
        }
    if "counted_measures_by_year" in facts:
        return _guard_reclassification(facts, rules)
    if "measures" in facts:
        return _measures(facts, rules)
    if "counted_measure_cents" in facts:
        raw = facts["counted_measure_cents"]
        if not isinstance(raw, Sequence):
            raise TypeError("counted measures must be a sequence")
        threshold = _half_up(_integer(facts, "building_basis_cents") * rules.guard_rate_bp, 10_000)
        cumulative = sum(int(value) for value in raw)
        return {
            "threshold": threshold,
            "cumulative": cumulative,
            "buffer": threshold - cumulative,
            "status": "warning" if cumulative * 10 >= threshold * 8 else "ok",
        }
    if "later_production_cost_cents" in facts:
        later = _integer(facts, "later_production_cost_cents")
        new_basis = _integer(facts, "building_basis_cents") + later
        annual = _annual(new_basis, _integer(facts, "rate_bp"))
        return {
            "new_basis": new_basis,
            "new_annual_afa": annual,
            "closing_book_value": _integer(facts, "opening_book_value_cents") + later - annual,
        }
    if "contract_building_cents" in facts:
        rate = _selected_rate(rules, _integer(facts, "year_built"))
        contract = _integer(facts, "contract_building_cents")
        bmf = _integer(facts, "comparison_bmf_building_cents")
        return {
            "contract_building": contract,
            "contract_land": _integer(facts, "contract_land_cents"),
            "bmf_building": bmf,
            "bmf_land": _integer(facts, "comparison_bmf_land_cents"),
            "annual_afa_delta": _annual(contract, rate) - _annual(bmf, rate),
            "warning": True,
        }
    if route == "contract":
        acquisition = _integer(facts, "acquisition_cost_cents")
        building = _half_up(acquisition * _integer(facts, "contract_building_share_bp"), 10_000)
        rate = _selected_rate(rules, _integer(facts, "year_built"))
        return {
            "building_cost": building,
            "land_cost": acquisition - building,
            "annual_afa": _annual(building, rate),
            "blocking": False,
        }
    if "kaufpreis_cents" in facts:
        purchase_values = _acquisition(facts)
        if "bmf_building_value_cents" not in facts:
            purchase_result: dict[str, object] = dict(purchase_values)
            return purchase_result
        total = purchase_values["acquisition_cost"]
        numerator = _integer(facts, "bmf_building_value_cents")
        denominator = _integer(facts, "bmf_property_value_cents")
        building = _half_up(total * numerator, denominator)
        wrong_total = total + purchase_values["excluded_financing_cost_cents"]
        wrong_building = _half_up(wrong_total * numerator, denominator)
        rate = _selected_rate(rules, _integer(facts, "year_built"))
        correct_annual = _annual(building, rate)
        wrong_annual = _annual(wrong_building, rate)
        return {
            "correct_acquisition_cost": total,
            "correct_building_cost": building,
            "correct_land_cost": total - building,
            "correct_annual_afa": correct_annual,
            "immediate_financing_cost": purchase_values["excluded_financing_cost_cents"],
            "first_year_net_delta": purchase_values["excluded_financing_cost_cents"]
            - (wrong_annual - correct_annual),
        }
    if route == "bmf":
        if "purchase_price_cents" in facts:
            purchase = _integer(facts, "purchase_price_cents") - _integer(
                facts, "movable_assets_cents"
            )
            acquisition_total = purchase + _integer(facts, "ancillary_cost_cents")
            bmf_result = {"purchase_after_split": purchase, **_bmf(facts, acquisition_total)}
            bmf_result["annual_afa"] = _annual(
                _calculated_integer(bmf_result, "building_cost"),
                _selected_rate(rules, _integer(facts, "year_built")),
            )
            return bmf_result
        return _bmf(facts, _integer(facts, "acquisition_cost_cents"))
    if "series_start_year" in facts:
        return _series(facts, rules)
    if "sale_date" in facts:
        rate = _selected_rate(rules, _integer(facts, "year_built"))
        annual = _annual(_integer(facts, "building_basis_cents"), rate)
        months = _iso_date(facts["sale_date"]).month
        amount = _half_up(annual * months, 12)
        return {
            "months": months,
            "sale_year_afa": amount,
            "closing_book_value": _integer(facts, "opening_book_value_cents") - amount,
        }
    if "annual_afa_cents" in facts:
        annual = _integer(facts, "annual_afa_cents")
        deductible = _half_up(
            annual * _integer(facts, "rented_area_months_x100"),
            _integer(facts, "total_area_months_x100"),
        )
        use_result: dict[str, object] = {
            "deductible_afa": deductible,
            "non_deductible_afa": annual - deductible,
        }
        if facts.get("started_rental_month_counts_fully") is True:
            use_result["verification_flag"] = "verify-before-production"
        return use_result
    if "building_basis_cents" in facts and "year_built" in facts:
        rate = _selected_rate(rules, _integer(facts, "year_built"))
        annual = _annual(_integer(facts, "building_basis_cents"), rate)
        annual_result: dict[str, object] = {"rate_bp": rate, "annual_afa": annual}
        relevant_date = facts.get("completion_date", facts.get("transfer_date"))
        if relevant_date is not None:
            months = 13 - _iso_date(relevant_date).month
            first = _half_up(annual * months, 12)
            annual_result.update(months=months, first_year_afa=first)
            if months == 1:
                annual_result["twelve_month_product"] = first * 12
        return annual_result
    raise ValueError("unsupported normalized AfA facts")


def calculate_afa_record(
    afa_input: AfaInput | _InputLike | Mapping[str, object],
    rules: AfaRuleBundle | _RulesLike | Mapping[str, object],
    tax_year: int,
) -> AfaResult:
    facts = _field(afa_input, "facts")
    if not isinstance(facts, Mapping):
        raise TypeError("facts must be a mapping")
    rule_values = AfaRuleBundle(
        linear_rates_bp=tuple(_field(rules, "linear_rates_bp")),
        guard_rate_bp=int(_field(rules, "guard_rate_bp")),
        market_disagio_limit_bp=int(_field(rules, "market_disagio_limit_bp")),
        source_evidence=tuple(_field(rules, "source_evidence")),
        rechtsstand=str(_field(rules, "rechtsstand")),
        production_blocked=bool(_field(rules, "production_blocked")),
    )
    missing_bmf = facts.get("allocation_route") == "bmf" and (
        "land_value_cents_per_sqm" not in facts
    )
    missing_report_share = facts.get("allocation_route") == "gutachten" and (
        facts.get("report_building_share_bp") is None
    )
    findings: list[AfaFinding] = []
    evidence_limit: str | None = None
    if missing_bmf:
        evidence_limit = "approved raw inputs are incomplete"
        findings.append(AfaFinding("source_gap", "Freigegebene Rohdaten sind unvollstaendig."))
    if missing_report_share:
        evidence_limit = "approved Gutachten share is missing"
        findings.append(
            AfaFinding("gutachten_share_missing", "Der freigegebene Gutachten-Anteil fehlt.")
        )
    if rule_values.production_blocked:
        findings.append(AfaFinding("authority_unverified", "Vor Produktion pruefen."))
    handoff = (
        _page04_handoff()
        if any(
            key in facts
            for key in ("counted_measures_by_year", "market_disagio_cents", "interest_cents")
        )
        else None
    )
    return AfaResult(
        calculated_values=_calculate(facts, rule_values),
        findings=tuple(findings),
        source_evidence=tuple(sorted(rule_values.source_evidence)),
        rechtsstand=rule_values.rechtsstand,
        production_blocked=(rule_values.production_blocked or missing_bmf or missing_report_share),
        tax_year=tax_year,
        evidence_limit=evidence_limit,
        page04_handoff=handoff,
    )


__all__ = [
    "AfaFinding",
    "AfaInput",
    "AfaResult",
    "AfaRuleBundle",
    "calculate_afa_record",
]
