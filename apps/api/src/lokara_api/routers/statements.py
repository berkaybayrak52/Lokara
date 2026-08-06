"""NK statement calculation — the Phase E DoD endpoint.

Pure computation: Pydantic body in → engine dataclasses → cent-exact shares
out. No DB access; auth is still required (the numbers are domain output).
The M3 slice adds the DB-backed variant that loads a building's real data.
"""

from fastapi import APIRouter, HTTPException
from lokara_domain import Occupancy, Period, cents, format_eur
from lokara_nk_engine import (
    ConsumptionValue,
    CostItem,
    NkInput,
    NkInputError,
    PersonCountPeriod,
    UnitBasis,
    calculate_nk_statement,
)

from ..auth import RequireAuth
from ..schemas import NkCalcRequest, NkCalcResponse, NkShareLineOut, PeriodIn

router = APIRouter(prefix="/calc")


def _period(p: PeriodIn) -> Period:
    return Period(valid_from=p.valid_from, valid_to=p.valid_to)


@router.post("/nk")
def calculate_nk(body: NkCalcRequest, _auth: RequireAuth) -> NkCalcResponse:
    nk_input = NkInput(
        billing_period=_period(body.billing_period),
        units=tuple(
            UnitBasis(unit_id=u.unit_id, area_sqm_x100=u.area_sqm_x100, mea_x10000=u.mea_x10000)
            for u in body.units
        ),
        occupancies=tuple(
            Occupancy(unit_id=o.unit_id, tenancy_id=o.tenancy_id, period=_period(o.period))
            for o in body.occupancies
        ),
        costs=tuple(
            CostItem(
                cost_id=c.cost_id,
                label=c.label,
                amount=cents(c.amount_cents),
                key=c.key,
                direct_unit_id=c.direct_unit_id,
                direct_tenancy_id=c.direct_tenancy_id,
            )
            for c in body.costs
        ),
        person_counts=tuple(
            PersonCountPeriod(tenancy_id=p.tenancy_id, count=p.count, period=_period(p.period))
            for p in body.person_counts
        ),
        consumptions=tuple(
            ConsumptionValue(
                unit_id=v.unit_id,
                tenancy_id=v.tenancy_id,
                value=v.value,
                measurement_unit=v.measurement_unit,
            )
            for v in body.consumptions
        ),
    )
    try:
        result = calculate_nk_statement(nk_input)
    except NkInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return NkCalcResponse(
        lines=[
            NkShareLineOut(
                cost_id=line.cost_id,
                unit_id=line.unit_id,
                tenancy_id=line.tenancy_id,
                amount_cents=int(line.amount),
                amount_eur=format_eur(line.amount),
            )
            for line in result.lines
        ],
        total_cents=int(result.total),
        total_eur=format_eur(result.total),
    )
