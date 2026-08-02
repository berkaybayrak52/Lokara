"""Email port — compliance-grade transactional delivery.

Modell A: we send from our own domain with the landlord as From-name. Delivery
states feed the **append-only** EmailDelivery ledger and the 3-colour
Zustell-Ampel (§ 556 proof of receipt, M9) — a receipt is evidence, not a log
line, so the caller must persist it.

TODO(provider): EU provider (SES Frankfurt / Postmark / Brevo) chosen at M9,
with SPF/DKIM/DMARC on the sending domain.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol


class DeliveryStatus(StrEnum):
    QUEUED = "QUEUED"
    DELIVERED = "DELIVERED"
    BOUNCED = "BOUNCED"


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    from_name: str
    subject: str
    html_body: str


@dataclass(frozen=True)
class EmailDeliveryReceipt:
    """One immutable delivery record; ``message_id`` is the provider's handle
    for later status webhooks (QUEUED → DELIVERED/BOUNCED)."""

    message_id: str
    status: DeliveryStatus
    accepted_at: datetime


class EmailGateway(Protocol):
    """Port: hand one message to the provider and get its receipt."""

    def send(self, email: OutgoingEmail) -> EmailDeliveryReceipt: ...


@dataclass(frozen=True)
class SentEmail:
    email: OutgoingEmail
    receipt: EmailDeliveryReceipt


def _utc_now() -> datetime:
    return datetime.now(UTC)


class StubEmailGateway:
    """Dev/test stub: records sends in memory instead of delivering anything.

    The clock is injectable so tests assert exact timestamps instead of
    tolerating wall-clock drift. TODO(provider): real EU adapter at M9.
    """

    def __init__(self, clock: Callable[[], datetime] = _utc_now) -> None:
        self._clock = clock
        self._sent: list[SentEmail] = []

    @property
    def sent(self) -> tuple[SentEmail, ...]:
        return tuple(self._sent)

    def send(self, email: OutgoingEmail) -> EmailDeliveryReceipt:
        receipt = EmailDeliveryReceipt(
            message_id=f"stub-msg-{len(self._sent) + 1}",
            status=DeliveryStatus.QUEUED,
            accepted_at=self._clock(),
        )
        self._sent.append(SentEmail(email=email, receipt=receipt))
        return receipt
