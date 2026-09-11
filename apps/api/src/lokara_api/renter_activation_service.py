"""M10-R1 tenancy-bound activation issuance and atomic redemption."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from hashlib import sha256
from secrets import token_urlsafe

from lokara_db import (
    Membership,
    Renter,
    RenterActivationAttempt,
    RenterActivationCode,
    RenterActivationRedemption,
    Tenancy,
    TenancyParty,
    new_id,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

ACTIVATION_CODE_TTL = timedelta(days=7)


class ActivationRefusal(StrEnum):
    CODE_SPENT = "ACTIVATION_CODE_SPENT"
    CODE_EXPIRED = "ACTIVATION_CODE_EXPIRED"
    TENANCY_MISMATCH = "ACTIVATION_TENANCY_MISMATCH"
    ACCOUNT_MISMATCH = "ACTIVATION_ACCOUNT_MISMATCH"
    RENTER_ALREADY_LINKED = "RENTER_ALREADY_LINKED"
    PERSON_UNKNOWN = "ACTIVATION_PERSON_UNKNOWN"
    CODE_UNKNOWN = "ACTIVATION_CODE_UNKNOWN"


@dataclass(frozen=True, slots=True)
class IssuedActivationCode:
    id: str
    raw_code: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ActivationRedemption:
    tenancy_id: str
    renter_id: str


@dataclass(frozen=True, slots=True)
class RefusedActivation:
    outcome: ActivationRefusal
    code_id: str | None = None


class ActivationTargetNotFoundError(LookupError):
    """The owner issuance URL does not name one exact tenancy party."""


def activation_code_hash(raw_code: str) -> str:
    return sha256(raw_code.encode("utf-8")).hexdigest()


def record_activation_refusal(
    session: Session,
    *,
    account_id: str,
    tenancy_id: str,
    person_id: str,
    refusal: RefusedActivation,
    code_digest: str,
    now: datetime,
) -> None:
    """Append owner-visible evidence after a safely attributable refusal."""
    session.add(
        RenterActivationAttempt(
            id=new_id(),
            account_id=account_id,
            activation_code_id=refusal.code_id,
            requested_tenancy_id=tenancy_id,
            subject_id=person_id,
            outcome=refusal.outcome.value,
            code_digest=code_digest,
            attempted_at=now,
        )
    )
    session.flush()


def issue_activation_code(
    session: Session,
    *,
    account_id: str,
    tenancy_id: str,
    renter_id: str,
    issued_by: Membership,
    now: datetime,
) -> IssuedActivationCode:
    tenancy_exists = session.scalar(
        select(Tenancy.id).where(
            Tenancy.account_id == account_id,
            Tenancy.id == tenancy_id,
        )
    )
    party_exists = session.scalar(
        select(TenancyParty.id).where(
            TenancyParty.account_id == account_id,
            TenancyParty.tenancy_id == tenancy_id,
            TenancyParty.renter_id == renter_id,
        )
    )
    if tenancy_exists is None or party_exists is None:
        raise ActivationTargetNotFoundError

    raw_code = f"{account_id}.{token_urlsafe(32)}"
    expires_at = now + ACTIVATION_CODE_TTL
    row = RenterActivationCode(
        id=new_id(),
        account_id=account_id,
        renter_id=renter_id,
        tenancy_id=tenancy_id,
        code_hash=activation_code_hash(raw_code),
        expires_at=expires_at,
        issued_by_membership_id=issued_by.id,
        issued_at=now,
    )
    session.add(row)
    session.flush()
    return IssuedActivationCode(id=row.id, raw_code=raw_code, expires_at=expires_at)


def redeem_activation_code(
    session: Session,
    *,
    account_id: str,
    tenancy_id: str,
    raw_code: str,
    person_id: str,
    person_known: bool,
    now: datetime,
) -> ActivationRedemption | RefusedActivation:
    """Redeem one code; the caller owns the surrounding atomic transaction."""
    tenancy_exists = session.scalar(
        select(Tenancy.id).where(
            Tenancy.account_id == account_id,
            Tenancy.id == tenancy_id,
        )
    )
    if tenancy_exists is None:
        return RefusedActivation(ActivationRefusal.CODE_UNKNOWN)

    code = session.scalar(
        select(RenterActivationCode)
        .where(
            RenterActivationCode.account_id == account_id,
            RenterActivationCode.code_hash == activation_code_hash(raw_code),
        )
        .with_for_update()
    )
    if code is None:
        return RefusedActivation(ActivationRefusal.CODE_UNKNOWN)

    spend_exists = session.scalar(
        select(RenterActivationRedemption.id).where(
            RenterActivationRedemption.activation_code_id == code.id
        )
    )
    if spend_exists is not None:
        return RefusedActivation(ActivationRefusal.CODE_SPENT, code.id)
    if now >= code.expires_at:
        return RefusedActivation(ActivationRefusal.CODE_EXPIRED, code.id)
    if code.tenancy_id != tenancy_id:
        return RefusedActivation(ActivationRefusal.TENANCY_MISMATCH, code.id)

    party_exists = session.scalar(
        select(TenancyParty.id).where(
            TenancyParty.account_id == account_id,
            TenancyParty.tenancy_id == tenancy_id,
            TenancyParty.renter_id == code.renter_id,
        )
    )
    if party_exists is None:
        return RefusedActivation(ActivationRefusal.TENANCY_MISMATCH, code.id)

    renter = session.scalar(
        select(Renter)
        .where(
            Renter.account_id == account_id,
            Renter.id == code.renter_id,
        )
        .with_for_update()
    )
    if renter is None:
        return RefusedActivation(ActivationRefusal.TENANCY_MISMATCH, code.id)
    if not person_known:
        return RefusedActivation(ActivationRefusal.PERSON_UNKNOWN, code.id)
    if renter.person_id is not None:
        return RefusedActivation(ActivationRefusal.RENTER_ALREADY_LINKED, code.id)

    session.add(
        RenterActivationRedemption(
            id=new_id(),
            account_id=account_id,
            activation_code_id=code.id,
            renter_id=renter.id,
            tenancy_id=tenancy_id,
            person_id=person_id,
            redeemed_at=now,
        )
    )
    # The database trigger requires immutable spend evidence to exist before
    # the sole permitted NULL -> Person link is written.
    session.flush()
    renter.person_id = person_id
    session.flush()
    return ActivationRedemption(tenancy_id=tenancy_id, renter_id=renter.id)
