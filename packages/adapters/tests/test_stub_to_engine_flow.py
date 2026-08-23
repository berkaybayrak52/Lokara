"""End-to-end Phase D DoD: a stubbed extraction flows adapter → engine.

The M4 pitch flow in miniature: the vision stub "reads" the garbage invoice,
the caller turns the normalized fields into a CostItem, and the NK engine
reproduces the canonical €1,200 allocation byte-exact. The engine never sees
the adapter — only normalized domain/engine inputs (docs/03 contract).
"""

from lokara_adapters import SourceDocument, StubVisionGateway, VisionGateway
from lokara_domain import AllocationKey, Occupancy, period
from lokara_nk_engine import CostItem, NkInput, UnitBasis, calculate_nk_statement


def test_extracted_invoice_reproduces_the_canonical_1200_allocation() -> None:
    gateway: VisionGateway = StubVisionGateway()
    fields = gateway.extract_invoice(SourceDocument(file_name="rechnung.pdf", content=b"%PDF"))

    result = calculate_nk_statement(
        NkInput(
            billing_period=period("2025-01-01", "2026-01-01"),
            units=(
                UnitBasis(unit_id="unit-a", area_sqm_x100=5000),
                UnitBasis(unit_id="unit-b", area_sqm_x100=3000),
                UnitBasis(unit_id="unit-c", area_sqm_x100=2000),
            ),
            occupancies=(
                Occupancy("unit-a", "ten-a", period("2025-01-01")),
                Occupancy("unit-b", "ten-b", period("2024-08-01", "2025-07-01")),
                Occupancy("unit-c", "ten-c", period("2023-01-01")),
            ),
            costs=(
                CostItem(
                    cost_id="cost-from-beleg",
                    label=fields.cost_category,
                    amount=fields.total_amount,
                    key=AllocationKey.AREA,
                ),
            ),
        )
    )

    assert [(line.unit_id, line.tenancy_id, int(line.amount)) for line in result.lines] == [
        ("unit-a", "ten-a", 60000),
        ("unit-b", "ten-b", 17852),
        ("unit-c", "ten-c", 24000),
        (None, None, 18148),
    ]
    assert result.total == fields.total_amount
