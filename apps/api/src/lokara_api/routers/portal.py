"""The URL-scoped Vermieter portal (docs/04): /a/{account_id}/…

Context lives in the URL, never the session — `PathAccountSession` verifies
the caller's Membership in the account named in the path AND sets the RLS
context to it, on every request (enforced twice, CLAUDE.md rule 3).
"""

from datetime import date, timedelta

from fastapi import APIRouter, HTTPException, Response
from lokara_db import Account, Person
from lokara_domain import OccupancyOverlapError, Period, cents, format_eur
from lokara_heating_engine import Page01bStatementValues
from lokara_nk_engine import BillingWindowTooLongError, NkInputError
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
    StatementAnnualComparison,
    StatementCo2,
    StatementDeviceEvidence,
    StatementFinding,
    StatementHeatingLine,
    StatementNkCost,
    StatementNkLine,
    StatementProjectionCost,
    StatementProjectionParty,
    StatementProjectionResponse,
    StatementProvenance,
    StatementReductionRisk,
)
from ..statement_service import (
    ALLOCATION_KEY_LABELS,
    WEIGHT_DISPLAY_DIVISORS,
    EmptyTenancyError,
    NoDemoDataError,
    StatementAudience,
    StatementBundle,
    StatementProductionBlockedError,
    StatementProjection,
    UnknownTenancyError,
    compute_statement,
    input_total,
    period_label,
    project_statement,
    to_pdf_data,
)
from .demo import summary_response

router = APIRouter(prefix="/a/{account_id}")

_NO_DATA = 'Keine Daten im Konto — erst "Demo-Szenario laden" ausführen.'


@router.get("/summary")
def summary(account_id: str, session: PathAccountSession) -> DemoSummaryResponse:
    return summary_response(session, session.get(Account, account_id))


def _bundle(
    session: PathAccountSession,
    *,
    building_id: str | None = None,
    window: Period | None = None,
) -> StatementBundle:
    try:
        return compute_statement(session, building_id=building_id, window=window)
    except NoDemoDataError as exc:
        raise HTTPException(status_code=404, detail=_NO_DATA) from exc
    except OccupancyOverlapError as exc:
        # docs/02 § 5 blocks overlapping tenancies before calculation, and the
        # block has to carry the over-allocated Bemessung so a landlord can find
        # the days in a lease file instead of only learning that a conflict
        # exists. 422: the entered data is the defect, not the request.
        raise HTTPException(
            status_code=422,
            detail=(
                f"Überschneidende Mietverhältnisse in Einheit {exc.unit_id}: "
                f"{exc.overlap_days} Tage sind doppelt belegt "
                f"({format_number_de(exc.overallocated_weight)} von "
                f"{format_number_de(exc.available_weight)} Bemessungseinheiten). "
                "Bitte die Mietzeiträume korrigieren."
            ),
        ) from exc
    except BillingWindowTooLongError as exc:
        # docs/08 "Period boundary". Its own German sentence, and named dates:
        # the landlord's next action is to shorten the period, so the message
        # has to say what the latest permitted end actually is.
        last_permitted = exc.maximum_to - timedelta(days=1)
        raise HTTPException(
            status_code=422,
            detail=(
                "Ein Abrechnungszeitraum darf höchstens 12 Monate umfassen. "
                f"Für einen Beginn am {exc.window_from.strftime('%d.%m.%Y')} ist "
                f"spätestens der {last_permitted.strftime('%d.%m.%Y')} zulässig."
            ),
        ) from exc
    except NkInputError as exc:
        # Every other input precondition — a missing MEA share, a DIRECT target
        # that does not exist. A 500 here would read as "Lokara is broken" for
        # data the landlord can actually fix. The engine's own wording is
        # English and technical, so it is appended as the detail behind a German
        # lead rather than shown as the whole message.
        raise HTTPException(
            status_code=422,
            detail=f"Die erfassten Daten ergeben keine gültige Abrechnung: {exc}",
        ) from exc


def _window(period_from: date | None, period_to: date | None) -> Period | None:
    """The URL's inclusive `period_to` as the half-open window everything else uses.

    `None` means "the demo preset", which is what the existing screens ask for.
    Both dates or neither: half a period is a mistake, not a default, and
    guessing the missing end is how a Rumpfperiode silently becomes a year.
    """
    if period_from is None and period_to is None:
        return None
    if period_from is None or period_to is None:
        raise HTTPException(
            status_code=422,
            detail="Abrechnungszeitraum braucht Anfang und Ende.",
        )
    if period_to < period_from:
        raise HTTPException(
            status_code=422,
            detail="Das Ende des Abrechnungszeitraums liegt vor seinem Anfang.",
        )
    return Period(valid_from=period_from, valid_to=period_to + timedelta(days=1))


@router.get("/buildings/{building_id}/statement")
def statement_projection(
    account_id: str,
    building_id: str,
    session: PathAccountSession,
    audience: StatementAudience = StatementAudience.OWNER,
    tenancy_id: str | None = None,
    period_from: date | None = None,
    period_to: date | None = None,
) -> StatementProjectionResponse:
    """One calculation, projected to one audience before anything renders.

    `period_to` is **inclusive** in the URL, as a human reads a billing period,
    and half-open internally. Omitting both dates falls back to the demo preset
    so the existing screens keep working.

    A missing or foreign `tenancy_id` returns 404 and never the owner view
    (`docs/02` § 5; `CLAUDE.md` § 3.3). The path account is verified by the
    dependency, and the building/tenancy relationship carried in the URL is
    verified here — RLS is the backstop, not the authorization.
    """
    del account_id  # scoping happened in the dependency
    bundle = _bundle(session, building_id=building_id, window=_window(period_from, period_to))
    try:
        projection = project_statement(bundle, audience, tenancy_id=tenancy_id)
    except EmptyTenancyError as exc:
        raise HTTPException(
            status_code=404,
            detail=(
                "Dieses Mietverhältnis hat im Abrechnungszeitraum keine Nutzungstage; "
                "es entsteht keine Mieterabrechnung."
            ),
        ) from exc
    except UnknownTenancyError as exc:
        raise HTTPException(
            status_code=404,
            detail="Mietverhältnis nicht gefunden.",
        ) from exc
    except StatementProductionBlockedError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _projection_response(projection, bundle)


def _projection_response(
    projection: StatementProjection, bundle: StatementBundle
) -> StatementProjectionResponse:
    costs: list[StatementProjectionCost] = []
    for cost in projection.nk_costs:
        divisor = WEIGHT_DISPLAY_DIVISORS.get(cost.key, None)
        lines = [
            StatementProjectionParty(
                party_label=projection.party_labels.get(
                    (line.unit_id, line.tenancy_id), f"{line.unit_id}"
                ),
                is_landlord=line.tenancy_id is None,
                weight_display=format_number_de(
                    line.weight / divisor if divisor is not None else line.weight
                ),
                amount_cents=int(line.amount),
                amount_eur=format_eur(line.amount),
            )
            for line in projection.nk_lines
            if line.cost_id == cost.cost_id
        ]
        # A cost this audience sees no line of is omitted entirely rather than
        # rendered with an empty table: on a tenant document, a cost the renter
        # carries nothing of is not that renter's business.
        if not lines:
            continue
        costs.append(
            StatementProjectionCost(
                cost_id=cost.cost_id,
                label=cost.label,
                key_label=ALLOCATION_KEY_LABELS[cost.key],
                total_cents=int(cost.amount),
                total_eur=format_eur(cost.amount),
                lines=lines,
            )
        )

    heating_lines = [
        StatementHeatingLine(
            party_label=projection.party_labels.get(
                (line.unit_id, line.tenancy_id), f"{line.unit_id}"
            ),
            is_landlord=False,
            heating_base_eur=format_eur(line.heating_base),
            heating_consumption_eur=format_eur(line.heating_consumption),
            ww_base_eur=format_eur(line.ww_base),
            ww_consumption_eur=format_eur(line.ww_consumption),
            total_cents=int(line.total),
            total_eur=format_eur(line.total),
        )
        for line in projection.heating_lines
    ]
    residual = projection.owner_residual
    if residual is not None:
        heating_lines.append(
            StatementHeatingLine(
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

    building = projection.building
    return StatementProjectionResponse(
        audience=projection.audience.value,
        tenancy_id=projection.tenancy_id,
        building_name=building.name,
        building_address=f"{building.street}, {building.postal_code} {building.city}",
        period_label=period_label(projection.window),
        costs=costs,
        heating_lines=heating_lines,
        owner_residual_cents=(int(residual.total) if residual is not None else None),
        findings=list(projection.findings),
        rechtsstaende=list(bundle.rechtsstaende),
        disclaimer=DISCLAIMER,
    )


@router.get("/statements")
def statement(
    account_id: str,
    session: PathAccountSession,
    building_id: str | None = None,
    period_from: date | None = None,
    period_to: date | None = None,
) -> DemoStatementResponse:
    """The Vermieter-Gesamtübersicht for one selected object and period.

    `period_to` is inclusive in the URL. Omitting a parameter falls back to the
    demo preset, which is what `/statements/demo` below is.
    """
    del account_id  # scoping happened in the dependency
    return _statement_response(
        _bundle(session, building_id=building_id, window=_window(period_from, period_to))
    )


@router.get("/statements/demo")
def demo_statement(account_id: str, session: PathAccountSession) -> DemoStatementResponse:
    """The seeded demo object and 2025 period — the preset of `/statements`.

    Kept as its own path because `verify_demo_path.sh`, `DEMO-RUNBOOK.md` and
    the rehearsal all address it by name; it takes no parameters so the demo
    beat cannot be misconfigured from a URL.
    """
    del account_id  # scoping happened in the dependency
    return _statement_response(_bundle(session))


def _mdl_values(bundle: StatementBundle) -> Page01bStatementValues | None:
    """The confirmed-MDL figures of this run, or `None` on the self-billing path."""
    page = bundle.page01b_result
    if page is None or page.values is None:
        return None
    return page.values if page.values.path in ("MDL_NET", "MDL_GROSS") else None


def _mdl_heating_lines(bundle: StatementBundle) -> list[StatementHeatingLine]:
    """Party totals as the Messdienstleister document states them.

    Empty on the self-billing path, which is what lets the caller fall through
    to the §§ 7/8/9 table. The four column figures are `None` here on purpose:
    an MDL document discloses a total per party and no column split, and
    `docs/03` H7 forbids reconstructing one.

    The owner row is appended unconditionally, including at `0,00 €` — same rule
    as the self-billing path (`docs/08` "Die Eigentümerzeile").
    """
    values = _mdl_values(bundle)
    if values is None:
        return []
    unit_by_tenancy = {
        tenancy.id: unit.id for unit in bundle.building.units for tenancy in unit.tenancies
    }
    lines = [
        StatementHeatingLine(
            party_label=bundle.party_labels.get(
                (unit_by_tenancy.get(tenancy_id), tenancy_id), tenancy_id
            ),
            is_landlord=False,
            heating_base_eur=None,
            heating_consumption_eur=None,
            ww_base_eur=None,
            ww_consumption_eur=None,
            total_cents=int(total),
            total_eur=format_eur(total),
        )
        for tenancy_id, total in zip(values.renter_ids, values.renter_totals, strict=True)
    ]
    lines.append(
        StatementHeatingLine(
            party_label=OWNER_LABEL,
            is_landlord=True,
            heating_base_eur=None,
            heating_consumption_eur=None,
            ww_base_eur=None,
            ww_consumption_eur=None,
            total_cents=int(values.owner_total),
            total_eur=format_eur(values.owner_total),
        )
    )
    return lines


def _statement_response(bundle: StatementBundle) -> DemoStatementResponse:
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
    heating_lines = _mdl_heating_lines(bundle) or [
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
    mdl = _mdl_values(bundle)
    # On the MDL path the source total IS the heating total: it is the figure the
    # document states and the one the control sum was checked against. Taking
    # `heating.total` here would report 0,00 € for a statement that has figures.
    if mdl is not None:
        heating_total = mdl.source_total
    else:
        heating_total = heating.total if heating is not None else cents(0)
    page = bundle.page01b_result
    findings = (
        [
            StatementFinding(
                code=finding.code,
                message=finding.message_de,
                severity=finding.severity,
                dismissible=finding.dismissible,
            )
            for finding in page.findings
        ]
        if page is not None
        else (
            [
                StatementFinding(
                    code="heating_input_missing",
                    message=bundle.heating_missing_reason,
                    severity="BLOCKER",
                    dismissible=False,
                )
            ]
            if bundle.heating_missing_reason is not None
            else []
        )
    )
    annual = page.annual_comparison if page is not None else None

    building = bundle.building
    return DemoStatementResponse(
        building_name=building.name,
        building_address=f"{building.street}, {building.postal_code} {building.city}",
        period_label=period_label(bundle.window),
        nk_costs=nk_costs,
        nk_total_cents=int(nk.total),
        nk_total_eur=format_eur(nk.total),
        nk_input_total_cents=int(input_total(bundle.nk_costs)),
        heating_lines=heating_lines,
        heating_total_cents=int(heating_total),
        heating_total_eur=format_eur(heating_total),
        # The reconciliation the page asserts: what went in equals what came
        # out. On the MDL path both sides are the confirmed total, which is the
        # only reconciliation a passthrough can honestly claim.
        heating_input_total_cents=(
            int(mdl.source_total) if mdl is not None else int(bundle.heating_input_total)
        ),
        heating_missing_reason=bundle.heating_missing_reason,
        heating_path=(page.values.path if page is not None and page.values is not None else None),
        heating_source_note=(
            "Bestätigte Abrechnung des Messdienstleisters — die Beträge wurden geprüft und "
            "unverändert übernommen, nicht neu berechnet."
            if mdl is not None
            else None
        ),
        heating_readiness=(page.readiness if page is not None else "BLOCKED"),
        heating_findings=findings,
        heating_provenance=[
            StatementProvenance(
                code=entry.code,
                source=entry.source_ref,
                detail=entry.detail_de,
            )
            for entry in (page.provenance if page is not None else ())
        ],
        heating_device_evidence=[
            StatementDeviceEvidence(
                device_id=line.device_id,
                unit_id=line.unit_id,
                room=line.room,
                measurement_unit=line.measurement_unit,
                valuation_factor=format_number_de(line.valuation_factor),
                allocation_kind=line.allocation_kind,
                target_id=line.target_id,
                opening=(format_number_de(line.opening) if line.opening is not None else None),
                closing=(format_number_de(line.closing) if line.closing is not None else None),
                units=format_number_de(line.units),
                estimated=line.estimated,
                estimation_basis=line.estimation_basis,
                reading_reasons=list(line.reading_reasons),
                reading_sources=list(line.reading_sources),
                provenance_refs=list(line.provenance_refs),
            )
            for line in (page.device_evidence if page is not None else ())
        ],
        heating_reduction_risks=[
            StatementReductionRisk(
                code=risk.code,
                percent=format_number_de(risk.percent),
                amounts_eur=[format_eur(amount) for amount in risk.amounts],
                message=risk.message_de,
            )
            for risk in (page.risks if page is not None else ())
        ],
        annual_comparison=(
            StatementAnnualComparison(
                state=annual.state,
                current_heat=format_number_de(annual.current_heat_raw),
                previous_heat=(
                    format_number_de(annual.previous_heat_raw)
                    if annual.previous_heat_raw is not None
                    else None
                ),
                current_heat_adjusted=(
                    format_number_de(annual.current_heat_adjusted)
                    if annual.current_heat_adjusted is not None
                    else None
                ),
                previous_heat_adjusted=(
                    format_number_de(annual.previous_heat_adjusted)
                    if annual.previous_heat_adjusted is not None
                    else None
                ),
                current_warm_water=(
                    format_number_de(annual.current_warm_water)
                    if annual.current_warm_water is not None
                    else None
                ),
                previous_warm_water=(
                    format_number_de(annual.previous_warm_water)
                    if annual.previous_warm_water is not None
                    else None
                ),
                raw_change_percent=(
                    format_number_de(annual.raw_change_percent)
                    if annual.raw_change_percent is not None
                    else None
                ),
                adjusted_change_percent=(
                    format_number_de(annual.adjusted_change_percent)
                    if annual.adjusted_change_percent is not None
                    else None
                ),
                graph_required=annual.graph_required,
                note=annual.note_de,
            )
            if annual is not None
            else None
        ),
        co2=co2_out,
        rechtsstaende=list(bundle.rechtsstaende),
        disclaimer=DISCLAIMER,
    )


@router.get("/statements/pdf")
def statement_pdf(
    account_id: str,
    auth: RequireAuth,
    session: PathAccountSession,
    building_id: str | None = None,
    period_from: date | None = None,
    period_to: date | None = None,
) -> Response:
    """The same overview as `/statements`, rendered. Landlord audience only.

    There is deliberately no `audience` parameter here: a Mieter-Einzelabrechnung
    is a separate, independently rendered document (`docs/08` § 3) and belongs to
    M6 with the ledger. Adding a flag to this route is exactly the "render
    everything and hide rows" shape that section forbids.
    """
    del account_id
    return _statement_pdf(
        session,
        auth,
        _bundle(session, building_id=building_id, window=_window(period_from, period_to)),
    )


@router.get("/statements/demo/pdf")
def demo_statement_pdf(account_id: str, auth: RequireAuth, session: PathAccountSession) -> Response:
    del account_id
    return _statement_pdf(session, auth, _bundle(session))


def _statement_pdf(
    session: PathAccountSession, auth: RequireAuth, bundle: StatementBundle
) -> Response:
    landlord = bundle.building.landlord
    if landlord is not None:
        landlord_name = landlord.legal_name
    else:
        person = session.get(Person, auth.person_id)
        landlord_name = (person.name if person and person.name else None) or "Vermieter"

    pdf = render_html_to_pdf(statement_html(to_pdf_data(bundle, landlord_name)))
    # Named after the period it actually covers: two runs of one building used to
    # land in a downloads folder as the same "abrechnung-2025.pdf".
    assert bundle.window.valid_to is not None
    filename = (
        f"abrechnung-{bundle.window.valid_from.isoformat()}-"
        f"{(bundle.window.valid_to - timedelta(days=1)).isoformat()}.pdf"
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
