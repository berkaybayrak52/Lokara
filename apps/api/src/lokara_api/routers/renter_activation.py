"""M10-R1 owner issuance and authenticated renter activation."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from lokara_db import Membership, Role
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..auth import RequireAuth
from ..authorization import require_owner
from ..deps import PathAccountSession, activation_account_session
from ..renter_activation_service import (
    ActivationRefusal,
    ActivationTargetNotFoundError,
    RefusedActivation,
    activation_code_hash,
    issue_activation_code,
    record_activation_refusal,
    redeem_activation_code,
)
from ..schemas import (
    RenterActivationCodeOut,
    RenterActivationRedeemIn,
    RenterActivationRedeemOut,
)
from .me import resolve_bootstrap_subject

router = APIRouter()
logger = logging.getLogger(__name__)

_PUBLIC_REFUSAL = (
    "Die Aktivierung war nicht möglich. Bitte prüfen Sie den Code oder wenden Sie sich an Ihre "
    "Vermieterin oder Ihren Vermieter."
)
_MINIMUM_REDEMPTION_SECONDS = 0.02


def _account_locator(raw_code: str) -> str | None:
    locator, separator, _secret = raw_code.partition(".")
    return locator if separator and locator else None


def _finish_minimum_duration(started_at: float) -> None:
    remaining = _MINIMUM_REDEMPTION_SECONDS - (time.monotonic() - started_at)
    if remaining > 0:
        time.sleep(remaining)


def _log_refusal(refusal: RefusedActivation, raw_hash: str) -> None:
    logger.info(
        "renter activation refused outcome=%s code_id=%s code_digest=%s",
        refusal.outcome.value,
        refusal.code_id or "unknown",
        raw_hash[:12],
    )


def _persist_refusal(
    *,
    account_id: str,
    tenancy_id: str,
    person_id: str,
    refusal: RefusedActivation,
    code_digest: str,
) -> None:
    """Append evidence when the locator names a real account, without revealing that fact."""
    try:
        with activation_account_session(account_id) as session:
            record_activation_refusal(
                session,
                account_id=account_id,
                tenancy_id=tenancy_id,
                person_id=person_id,
                refusal=refusal,
                code_digest=code_digest,
                now=datetime.now(UTC),
            )
    except IntegrityError:
        # A nonexistent locator has no owner to whom evidence can be attributed.
        # Its public response and structured operational log remain identical.
        return


@router.post(
    "/a/{account_id}/tenancies/{tenancy_id}/renters/{renter_id}/activation-codes",
    response_model=RenterActivationCodeOut,
    status_code=status.HTTP_201_CREATED,
)
def create_renter_activation_code(
    account_id: str,
    tenancy_id: str,
    renter_id: str,
    auth: RequireAuth,
    session: PathAccountSession,
) -> RenterActivationCodeOut:
    require_owner(session)
    membership = session.scalar(
        select(Membership).where(
            Membership.account_id == account_id,
            Membership.person_id == auth.person_id,
            Membership.role == Role.OWNER,
            Membership.accepted_at.is_not(None),
            Membership.revoked_at.is_(None),
        )
    )
    if membership is None:
        raise HTTPException(status_code=403, detail="Only owners may issue activation codes")
    try:
        issued = issue_activation_code(
            session,
            account_id=account_id,
            tenancy_id=tenancy_id,
            renter_id=renter_id,
            issued_by=membership,
            now=datetime.now(UTC),
        )
    except ActivationTargetNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Tenancy party not found") from exc
    return RenterActivationCodeOut(
        activation_code_id=issued.id,
        activation_code=issued.raw_code,
        expires_at=issued.expires_at,
    )


@router.post(
    "/renter/{tenancy_id}/activation",
    response_model=RenterActivationRedeemOut,
)
def redeem_renter_activation_code(
    tenancy_id: str,
    body: RenterActivationRedeemIn,
    auth: RequireAuth,
) -> RenterActivationRedeemOut:
    started_at = time.monotonic()
    submitted_code = body.activation_code
    raw_code = submitted_code if isinstance(submitted_code, str) else None
    raw_hash = activation_code_hash(raw_code or "")
    locator = _account_locator(raw_code) if raw_code is not None else None
    subject_rows = resolve_bootstrap_subject(auth)
    person_known = bool(subject_rows)
    refusal: RefusedActivation | None = None
    result: RenterActivationRedeemOut | None = None
    try:
        if locator is None:
            refusal = RefusedActivation(ActivationRefusal.CODE_UNKNOWN)
        else:
            assert raw_code is not None
            try:
                with activation_account_session(locator) as session:
                    redemption = redeem_activation_code(
                        session,
                        account_id=locator,
                        tenancy_id=tenancy_id,
                        raw_code=raw_code,
                        person_id=auth.person_id,
                        person_known=person_known,
                        now=datetime.now(UTC),
                    )
                    if isinstance(redemption, RefusedActivation):
                        refusal = redemption
                    else:
                        result = RenterActivationRedeemOut(
                            ok=True,
                            tenancy_id=redemption.tenancy_id,
                            renter_id=redemption.renter_id,
                        )
            except IntegrityError:
                # Database uniqueness is the final arbiter when two callers race.
                refusal = RefusedActivation(ActivationRefusal.CODE_SPENT)
        if refusal is not None and locator is not None:
            _persist_refusal(
                account_id=locator,
                tenancy_id=tenancy_id,
                person_id=auth.person_id,
                refusal=refusal,
                code_digest=raw_hash,
            )
    finally:
        _finish_minimum_duration(started_at)

    if refusal is not None:
        _log_refusal(refusal, raw_hash)
        raise HTTPException(status_code=400, detail=_PUBLIC_REFUSAL)
    if result is None:
        raise RuntimeError("activation redemption produced no result")
    return result
