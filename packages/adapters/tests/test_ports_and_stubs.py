"""Phase D gate: fixture data flows through each port as normalized domain types.

Every stub is consumed **through its Protocol type** — mypy strict enforces the
structural conformance these annotations claim, so a stub drifting from its
port breaks the build, not the demo.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from lokara_adapters import (
    VPI_SERIES_CODE,
    BankGateway,
    DatevExportFile,
    DatevGateway,
    DeliveryStatus,
    EmailGateway,
    FieldConfidences,
    MeterGateway,
    MeterKind,
    OutgoingEmail,
    PriceIndexGateway,
    SourceDocument,
    StubBankGateway,
    StubDatevGateway,
    StubEmailGateway,
    StubMeterGateway,
    StubPriceIndexGateway,
    StubVisionGateway,
    VisionGateway,
)
from lokara_domain import Cents

_ALL_CERTAIN = FieldConfidences(
    vendor_name=Decimal(1),
    invoice_date=Decimal(1),
    total_amount=Decimal(1),
    cost_category=Decimal(1),
)


class TestBankPort:
    """Port conformance only. The docs/15 § 3.1 normalization contract and the
    BANKMATCH-F10 conversion live in test_bank_normalization.py."""

    def test_stub_transactions_flow_through_the_port(self) -> None:
        gateway: BankGateway = StubBankGateway()
        transactions = gateway.list_transactions(
            "bank_acc_demo", date(2025, 1, 1), date(2026, 1, 1)
        )

        assert [t.provider_transaction_id for t in transactions] == [
            "tx_stub_001",
            "tx_stub_002",
            "tx_stub_003",
            "tx_stub_004",
        ]
        january = transactions[0]
        assert january.bank_booking_date == date(2025, 1, 3)  # § 11 EStG payment date
        assert january.amount_cents == 117000
        assert isinstance(january.amount_cents, int)  # integer cents, never float


class TestVisionPort:
    def test_upload_extracts_the_demo_garbage_invoice(self) -> None:
        gateway: VisionGateway = StubVisionGateway()
        fields = gateway.extract_invoice(SourceDocument(file_name="beleg.pdf", content=b"%PDF"))

        assert fields.vendor_name == "Stadtreinigung Frankfurt GmbH"
        assert fields.total_amount == 120000  # the canonical €1,200.00
        assert fields.cost_category == "Müllabfuhr"
        assert Decimal(0) <= fields.confidence <= Decimal(1)

    def test_every_field_carries_its_own_confidence(self) -> None:
        """The review UI's whole job is to point at the weak field, which a
        single document-level score cannot do."""
        fields = StubVisionGateway().extract_invoice(
            SourceDocument(file_name="beleg.pdf", content=b"%PDF")
        )
        per_field = fields.field_confidences

        for name, value in vars(per_field).items():
            assert Decimal(0) <= value <= Decimal(1), name
        # cost_category is inferred (and against a catalogue that is still a
        # pending spec), so it must read as the least certain value.
        assert per_field.cost_category < min(
            per_field.vendor_name, per_field.invoice_date, per_field.total_amount
        )

    def test_confidence_outside_unit_interval_is_rejected(self) -> None:
        from lokara_adapters import ExtractedInvoiceFields

        with pytest.raises(ValueError, match="confidence"):
            ExtractedInvoiceFields(
                vendor_name="X",
                invoice_date=date(2025, 1, 1),
                total_amount=Cents(100),
                cost_category="Sonstiges",
                confidence=Decimal("1.01"),
                field_confidences=_ALL_CERTAIN,
            )

    def test_a_per_field_confidence_outside_the_interval_is_rejected(self) -> None:
        from lokara_adapters import FieldConfidences

        with pytest.raises(ValueError, match="total_amount confidence"):
            FieldConfidences(
                vendor_name=Decimal("0.9"),
                invoice_date=Decimal("0.9"),
                total_amount=Decimal("-0.1"),
                cost_category=Decimal("0.9"),
            )


class TestEmailPort:
    def test_send_returns_a_receipt_and_records_the_send(self) -> None:
        frozen = datetime(2025, 7, 1, 12, 0, tzinfo=UTC)
        stub = StubEmailGateway(clock=lambda: frozen)
        gateway: EmailGateway = stub

        receipt = gateway.send(
            OutgoingEmail(
                to="anna.beispiel@example.de",
                from_name="Demo Vermieter",
                subject="Ihre Betriebskostenabrechnung 2025",
                html_body="<p>…</p>",
            )
        )

        assert receipt.message_id == "stub-msg-1"
        assert receipt.status is DeliveryStatus.QUEUED
        assert receipt.accepted_at == frozen
        assert len(stub.sent) == 1
        assert stub.sent[0].receipt is receipt

    def test_message_ids_are_sequential_per_gateway(self) -> None:
        stub = StubEmailGateway()
        email = OutgoingEmail(to="a@b.de", from_name="V", subject="s", html_body="")
        assert stub.send(email).message_id == "stub-msg-1"
        assert stub.send(email).message_id == "stub-msg-2"


class TestMeterPort:
    def test_register_differences_reproduce_the_heating_fixture(self) -> None:
        gateway: MeterGateway = StubMeterGateway()
        readings = gateway.list_readings("bld_demo_muster12", date(2025, 1, 1), date(2025, 12, 31))

        def consumption(unit_id: str, kind: MeterKind) -> Decimal:
            values = sorted(r.value for r in readings if r.unit_id == unit_id and r.kind == kind)
            assert len(values) == 2, f"expected opening+closing for {unit_id}/{kind}"
            return values[1] - values[0]

        # The heating golden fixture: heat 600/250/150 units, warm water 20/12/8 m³.
        assert consumption("unit_demo_a", MeterKind.HEAT) == Decimal(600)
        assert consumption("unit_demo_b", MeterKind.HEAT) == Decimal(250)
        assert consumption("unit_demo_c", MeterKind.HEAT) == Decimal(150)
        assert consumption("unit_demo_a", MeterKind.WARM_WATER) == Decimal(20)
        assert consumption("unit_demo_b", MeterKind.WARM_WATER) == Decimal(12)
        assert consumption("unit_demo_c", MeterKind.WARM_WATER) == Decimal(8)

    def test_window_is_closed_both_ends(self) -> None:
        gateway: MeterGateway = StubMeterGateway()
        only_openings = gateway.list_readings("bld", date(2025, 1, 1), date(2025, 6, 30))
        assert {r.read_at for r in only_openings} == {date(2025, 1, 1)}


class TestDestatisPort:
    def test_vpi_values_are_monthly_and_windowed(self) -> None:
        gateway: PriceIndexGateway = StubPriceIndexGateway()
        values = gateway.list_index_values(VPI_SERIES_CODE, date(2024, 12, 1), date(2025, 3, 1))

        assert [(v.month, v.value) for v in values] == [
            (date(2024, 12, 1), Decimal("119.6")),
            (date(2025, 1, 1), Decimal("119.4")),
            (date(2025, 2, 1), Decimal("119.9")),
        ]
        assert all(v.base_year == 2020 for v in values)

    def test_unknown_series_yields_nothing(self) -> None:
        gateway: PriceIndexGateway = StubPriceIndexGateway()
        assert gateway.list_index_values("00000-0000", date(2024, 1, 1), date(2026, 1, 1)) == ()


class TestDatevPort:
    def test_delivery_returns_an_immutable_reference(self) -> None:
        frozen = datetime(2026, 1, 15, 9, 30, tzinfo=UTC)
        stub = StubDatevGateway(clock=lambda: frozen)
        gateway: DatevGateway = stub

        export = DatevExportFile(file_name="EXTF_Buchungsstapel_2025.csv", content=b";;\r\n")
        reference = gateway.deliver(export)

        assert reference.delivery_id == "stub-datev-1"
        assert reference.delivered_at == frozen
        assert stub.delivered[0].export_file is export
