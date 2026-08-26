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
from hashlib import sha256 as calculate_sha256
from typing import Protocol


class DeliveryStatus(StrEnum):
    QUEUED = "QUEUED"
    DELIVERED = "DELIVERED"
    BOUNCED = "BOUNCED"
    COMPLAINED = "COMPLAINED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class EmailAttachment:
    """Exact immutable bytes handed to the delivery provider."""

    filename: str
    mime_type: str
    content_bytes: bytes
    sha256: str

    def __post_init__(self) -> None:
        if not self.filename.strip():
            raise ValueError("attachment filename must not be blank")
        if not self.mime_type.strip():
            raise ValueError("attachment MIME type must not be blank")
        digest = calculate_sha256(self.content_bytes).hexdigest()
        if self.sha256 != digest:
            raise ValueError("attachment sha256 hash does not match its exact bytes")


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    from_name: str
    subject: str
    html_body: str
    attachments: tuple[EmailAttachment, ...] = ()
    idempotency_key: str = ""

    def __post_init__(self) -> None:
        if not self.to.strip() or "," in self.to or ";" in self.to:
            raise ValueError("email requires exactly one recipient")
        if not self.from_name.strip():
            raise ValueError("landlord From-name must not be blank")


@dataclass(frozen=True)
class EmailDeliveryReceipt:
    """One immutable delivery record; ``message_id`` is the provider's handle
    for later status webhooks (QUEUED → DELIVERED/BOUNCED)."""

    message_id: str
    status: DeliveryStatus
    accepted_at: datetime


class EmailGateway(Protocol):
    """Port whose provider enforces the supplied idempotency key.

    This capability is required because a provider enqueue can succeed before
    the caller's local transaction commits. Retrying after a rollback must
    return the original receipt without sending a second message.
    """

    provider_idempotency_enforced: bool

    def send(self, email: OutgoingEmail) -> EmailDeliveryReceipt: ...


@dataclass(frozen=True)
class SentEmail:
    email: OutgoingEmail
    receipt: EmailDeliveryReceipt
    sender_address: str


def _utc_now() -> datetime:
    return datetime.now(UTC)


class StubEmailGateway:
    """Dev/test stub: records sends in memory instead of delivering anything.

    The clock is injectable so tests assert exact timestamps instead of
    tolerating wall-clock drift. TODO(provider): real EU adapter at M9.
    """

    provider_idempotency_enforced: bool = True

    def __init__(
        self,
        sender_address: str = "zustellung@lokara.de",
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        normalized_sender = sender_address.strip().lower()
        if not normalized_sender.endswith("@lokara.de"):
            raise ValueError("sender address must use the configured Lokara domain")
        self._sender_address = normalized_sender
        self._clock = clock
        self._sent: list[SentEmail] = []
        self._receipts_by_key: dict[str, EmailDeliveryReceipt] = {}

    @property
    def sent(self) -> tuple[SentEmail, ...]:
        return tuple(self._sent)

    def send(self, email: OutgoingEmail) -> EmailDeliveryReceipt:
        if email.idempotency_key:
            existing = self._receipts_by_key.get(email.idempotency_key)
            if existing is not None:
                return existing
        receipt = EmailDeliveryReceipt(
            message_id=f"stub-msg-{len(self._sent) + 1}",
            status=DeliveryStatus.QUEUED,
            accepted_at=self._clock(),
        )
        self._sent.append(
            SentEmail(email=email, receipt=receipt, sender_address=self._sender_address)
        )
        if email.idempotency_key:
            self._receipts_by_key[email.idempotency_key] = receipt
        return receipt
