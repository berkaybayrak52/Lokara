"""Red M9 email-port contract: immutable, one-recipient delivery evidence."""

from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime
from hashlib import sha256

import lokara_adapters.email as email_port
import pytest


def test_delivery_status_has_the_complete_append_only_event_vocabulary() -> None:
    status = email_port.DeliveryStatus
    assert {item.value for item in status} == {
        "QUEUED",
        "DELIVERED",
        "BOUNCED",
        "COMPLAINED",
        "FAILED",
    }


def test_attachment_owns_immutable_exact_bytes_and_matching_sha256() -> None:
    attachment_type = email_port.EmailAttachment
    content = b"%PDF-1.7\nexact archived bytes\n"
    digest = sha256(content).hexdigest()
    attachment = attachment_type(
        filename="abrechnung-2025.pdf",
        mime_type="application/pdf",
        content_bytes=content,
        sha256=digest,
    )
    assert attachment.content_bytes is content
    assert attachment.sha256 == digest
    with pytest.raises(FrozenInstanceError):
        attachment.sha256 = "0" * 64  # type: ignore[misc]
    with pytest.raises(ValueError, match=r"hash|sha256"):
        attachment_type(
            filename="falsch.pdf",
            mime_type="application/pdf",
            content_bytes=content,
            sha256="0" * 64,
        )


def test_outgoing_message_has_one_recipient_no_cc_and_an_idempotency_key() -> None:
    outgoing_type = email_port.OutgoingEmail
    names = {field.name for field in fields(outgoing_type)}
    assert {"to", "from_name", "subject", "html_body", "attachments", "idempotency_key"} <= names
    assert {"cc", "bcc"}.isdisjoint(names)


def test_stub_uses_configured_lokara_sender_and_keeps_landlord_from_name() -> None:
    attachment_type = email_port.EmailAttachment
    frozen = datetime(2026, 8, 25, 8, 0, tzinfo=UTC)
    content = b"document-a"
    attachment = attachment_type(
        filename="a.pdf",
        mime_type="application/pdf",
        content_bytes=content,
        sha256=sha256(content).hexdigest(),
    )
    stub = email_port.StubEmailGateway(sender_address="zustellung@lokara.de", clock=lambda: frozen)
    message = email_port.OutgoingEmail(
        to="anna@example.de",
        from_name="Hausverwaltung Beispiel",
        subject="Ihre Abrechnung",
        html_body="<p>Dokument im Anhang.</p>",
        attachments=(attachment,),
        idempotency_key="delivery:artifact-a:anna",
    )
    receipt = stub.send(message)
    assert receipt.status is email_port.DeliveryStatus.QUEUED
    assert stub.sent[0].sender_address == "zustellung@lokara.de"
    assert stub.sent[0].email.from_name == "Hausverwaltung Beispiel"
    assert stub.sent[0].email.attachments[0].content_bytes is content


def test_stub_never_combines_renters_and_deduplicates_by_idempotency_key() -> None:
    attachment_type = email_port.EmailAttachment
    content = b"same frozen artifact"
    attachment = attachment_type(
        filename="a.pdf",
        mime_type="application/pdf",
        content_bytes=content,
        sha256=sha256(content).hexdigest(),
    )
    stub = email_port.StubEmailGateway(sender_address="post@lokara.de")

    def message(to: str, key: str) -> email_port.OutgoingEmail:
        return email_port.OutgoingEmail(
            to=to,
            from_name="Vermieter",
            subject="Dokument",
            html_body="",
            attachments=(attachment,),
            idempotency_key=key,
        )

    first = stub.send(message("a@example.de", "artifact:a"))
    replay = stub.send(message("a@example.de", "artifact:a"))
    second = stub.send(message("b@example.de", "artifact:b"))
    assert replay is first
    assert stub.provider_idempotency_enforced is True
    assert second.message_id != first.message_id
    assert [sent.email.to for sent in stub.sent] == ["a@example.de", "b@example.de"]


def test_gateway_contract_explicitly_guarantees_provider_idempotency() -> None:
    gateway_type = email_port.EmailGateway
    assert "provider_idempotency_enforced" in gateway_type.__annotations__


def test_provider_replay_is_safe_after_local_transaction_rollback() -> None:
    """The provider key, not an uncommitted DB flush, closes the send ambiguity."""
    frozen = datetime(2026, 8, 25, 8, 0, tzinfo=UTC)
    stub = email_port.StubEmailGateway(sender_address="zustellung@lokara.de", clock=lambda: frozen)
    content = b"same immutable statement after rollback"
    message = email_port.OutgoingEmail(
        to="anna@example.de",
        from_name="Vermieter",
        subject="Ihre Abrechnung",
        html_body="Dokument im Anhang.",
        attachments=(
            email_port.EmailAttachment(
                filename="abrechnung.pdf",
                mime_type="application/pdf",
                content_bytes=content,
                sha256=sha256(content).hexdigest(),
            ),
        ),
        idempotency_key="delivery:statement:2025:anna",
    )

    before_rollback = stub.send(message)
    after_rollback_retry = stub.send(message)

    assert after_rollback_retry is before_rollback
    assert len(stub.sent) == 1
