"""The URL-scoped Vermieter portal (docs/04): /a/{account_id}/…

Context lives in the URL, never the session — `PathAccountSession` verifies
the caller's Membership in the account named in the path AND sets the RLS
context to it, on every request (enforced twice, CLAUDE.md rule 3).
"""

from fastapi import APIRouter, HTTPException, Response
from lokara_db import Account, Person
from lokara_domain import cents, format_eur
from lokara_pdf import (
    DISCLAIMER,
    OWNER_LABEL,
    format_number_de,
    render_html_to_pdf,
    statement_html,
)

from ..auth import RequireAuth
from ..deps import PathAccountSession
from ..schemas import (
    DemoStatementResponse,
    DemoSummaryResponse,
    StatementCo2,
    StatementHeatingLine,
    StatementNkCost,
    StatementNkLine,
)
from ..statement_service import (
    ALLOCATION_KEY_LABELS,
    PERIOD_LABEL,
    WEIGHT_DISPLAY_DIVISORS,
    NoDemoDataError,
    StatementBundle,
    compute_statement,
    input_total,
    to_pdf_data,
)
from .demo import summary_response

router = APIRouter(prefix="/a/{account_id}")

_NO_DATA = 'Keine Daten im Konto — erst "Demo-Szenario laden" ausführen.'


@router.get("/summary")
def summary(account_id: str, session: PathAccountSession) -> DemoSummaryResponse:
    return summary_response(session, session.get(Account, account_id))


def _bundle(session: PathAccountSession) -> StatementBundle:
    try:
        return compute_statement(session)
    except NoDemoDataError as exc:
        raise HTTPException(status_code=404, detail=_NO_DATA) from exc


@router.get("/statements/demo")
def demo_statement(account_id: str, session: PathAccountSession) -> DemoStatementResponse:
    del account_id  # scoping happened in the dependency
    bundle = _bundle(session)
    nk = bundle.nk_result
    heating = bundle.heating_result

    nk_costs: list[StatementNkCost] = []
    for cost in bundle.nk_costs:
        divisor = WEIGHT_DISPLAY_DIVISORS.get(cost.key, None)
        lines = [
            StatementNkLine(
                party_label=bundle.party_labels.get(
                    (line.unit_id, line.tenancy_id), f"{line.unit_id}"
                ),
                is_landlord=line.tenancy_id is None,
                weight_display=format_number_de(
                    line.weight / divisor if divisor is not None else line.weight
                ),
                amount_cents=int(line.amount),
                amount_eur=format_eur(line.amount),
            )
            for line in nk.lines
            if line.cost_id == cost.cost_id
        ]
        nk_costs.append(
            StatementNkCost(
                label=cost.label,
                key_label=ALLOCATION_KEY_LABELS[cost.key],
                amount_cents=int(cost.amount),
                amount_eur=format_eur(cost.amount),
                lines=lines,
            )
        )

    # heating is None when the meter/invoice inputs are incomplete: the NK part
    # still stands on its own, and the response carries the German reason
    # instead of a table of invented numbers.
    # Since 14.08.2026 `heating.lines` carries **Mietverhältnisse only** — the
    # Eigentümeranteil is a residual line per Liegenschaft, not a party derived
    # from occupancy (`docs/02`, Berkay Seite 01 D12). So `is_landlord` is
    # constant here rather than a test on `tenancy_id`, and the owner row is
    # appended once from `owner_residual` instead of falling out of the loop.
    # It is appended **unconditionally**: the row exists at `0,00 €` too
    # (`docs/08` → "Die Eigentümerzeile"), and `owner_residual` is non-optional
    # precisely so no renderer can write `if ...:` and drop it.
    heating_lines = [
        StatementHeatingLine(
            party_label=bundle.party_labels.get((line.unit_id, line.tenancy_id), f"{line.unit_id}"),
            is_landlord=False,
            heating_base_eur=format_eur(line.heating_base),
            heating_consumption_eur=format_eur(line.heating_consumption),
            ww_base_eur=format_eur(line.ww_base),
            ww_consumption_eur=format_eur(line.ww_consumption),
            total_cents=int(line.total),
            total_eur=format_eur(line.total),
        )
        for line in (heating.lines if heating is not None else ())
    ]
    if heating is not None:
        residual = heating.owner_residual
        heating_lines.append(
            StatementHeatingLine(
                # One label for one thing, matching the PDF's `OWNER_LABEL` and
                # Berkay's own annex wording ("Eigentümeranteil gesamt").
                party_label=OWNER_LABEL,
                is_landlord=True,
                heating_base_eur=format_eur(residual.heating_base),
                heating_consumption_eur=format_eur(residual.heating_consumption),
                ww_base_eur=format_eur(residual.ww_base),
                ww_consumption_eur=format_eur(residual.ww_consumption),
                total_cents=int(residual.total),
                total_eur=format_eur(residual.total),
            )
        )

    co2 = heating.co2 if heating is not None else None
    co2_out = (
        StatementCo2(
            intensity_display=format_number_de(co2.intensity_kg_per_sqm),
            landlord_share_percent=co2.landlord_share_percent,
            landlord_amount_eur=format_eur(co2.landlord_amount),
            renter_amount_eur=format_eur(co2.renter_amount),
            rechtsstand=co2.rechtsstand,
        )
        if co2 is not None
        else None
    )
    heating_total = heating.total if heating is not None else cents(0)

    building = bundle.building
    return DemoStatementResponse(
        building_name=building.name,
        building_address=f"{building.street}, {building.postal_code} {building.city}",
        period_label=PERIOD_LABEL,
        nk_costs=nk_costs,
        nk_total_cents=int(nk.total),
        nk_total_eur=format_eur(nk.total),
        nk_input_total_cents=int(input_total(bundle.nk_costs)),
        heating_lines=heating_lines,
        heating_total_cents=int(heating_total),
        heating_total_eur=format_eur(heating_total),
        heating_input_total_cents=int(bundle.heating_input_total),
        heating_missing_reason=bundle.heating_missing_reason,
        co2=co2_out,
        rechtsstaende=list(bundle.rechtsstaende),
        disclaimer=DISCLAIMER,
    )


@router.get("/statements/demo/pdf")
def demo_statement_pdf(account_id: str, auth: RequireAuth, session: PathAccountSession) -> Response:
    del account_id
    bundle = _bundle(session)
    landlord = bundle.building.landlord
    if landlord is not None:
        landlord_name = landlord.legal_name
    else:
        person = session.get(Person, auth.person_id)
        landlord_name = (person.name if person and person.name else None) or "Vermieter"

    pdf = render_html_to_pdf(statement_html(to_pdf_data(bundle, landlord_name)))
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="abrechnung-2025.pdf"',
        },
    )
