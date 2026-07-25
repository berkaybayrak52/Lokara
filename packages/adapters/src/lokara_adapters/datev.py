"""DATEV port — handing a finished export to the tax advisor's system.

Generating the EXTF file is **not** this adapter's job: that is the pure
`export-engine` (M7) — deterministic `f(ledger, mapping, params) → file`,
Windows-1252 / semicolon / CRLF, golden-tested byte-exact. This port only
transports the finished artifact (DATEV Unternehmen Online upload or a download
handover) and returns an immutable reference for the audit trail.

TODO(provider): real DATEV connectivity chosen at M7; only this module ever
imports its SDK.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


@dataclass(frozen=True)
class DatevExportFile:
    """A finished EXTF artifact. ``content`` is already encoded by the
    export-engine — the adapter never re-encodes (encoding is the #1 footgun,
    and it belongs in exactly one place)."""

    file_name: str
    content: bytes


@dataclass(frozen=True)
class DatevDeliveryReference:
    """Immutable proof of handover — referenced by the export's audit record."""

    delivery_id: str
    delivered_at: datetime


class DatevGateway(Protocol):
    """Port: deliver one export file to the connected DATEV endpoint."""

    def deliver(self, export_file: DatevExportFile) -> DatevDeliveryReference: ...


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class DeliveredExport:
    export_file: DatevExportFile
    reference: DatevDeliveryReference


class StubDatevGateway:
    """Dev/test stub: records deliveries in memory. TODO(provider): M7."""

    def __init__(self, clock: Callable[[], datetime] = _utc_now) -> None:
        self._clock = clock
        self._delivered: list[DeliveredExport] = []

    @property
    def delivered(self) -> tuple[DeliveredExport, ...]:
        return tuple(self._delivered)

    def deliver(self, export_file: DatevExportFile) -> DatevDeliveryReference:
        reference = DatevDeliveryReference(
            delivery_id=f"stub-datev-{len(self._delivered) + 1}",
            delivered_at=self._clock(),
        )
        self._delivered.append(DeliveredExport(export_file=export_file, reference=reference))
        return reference
