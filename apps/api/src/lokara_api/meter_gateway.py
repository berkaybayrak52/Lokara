"""The DB-backed implementation of the Phase D ``MeterGateway`` port.

This is what the port was for. ``StubMeterGateway`` serves fixture data and
this one serves entered rows, and **the statement cannot tell them apart** —
same Protocol, same ``MeterReading``. A hand-typed reading and a HeiWaKo MDL
delivery converge here into one shape; only where the row came from differs
(``source``), and nothing downstream branches on it.
"""

from datetime import date
from decimal import Decimal

from lokara_adapters import MeterReading
from lokara_db import Meter
from lokara_db import MeterReading as MeterReadingRow
from sqlalchemy import select
from sqlalchemy.orm import Session

# Register values are stored as integers × 1000 (never floats). Dividing a
# Decimal keeps the value exact: 241500/1000 → 241.5, 600000/1000 → 600.
VALUE_SCALE = Decimal(1000)


def to_normalized(row: MeterReadingRow, meter: Meter) -> MeterReading:
    return MeterReading(
        meter_id=meter.id,
        unit_id=meter.unit_id,
        kind=meter.kind,
        measurement_unit=meter.measurement_unit,
        read_at=row.read_at,
        value=Decimal(row.value_x1000) / VALUE_SCALE,
        reason=row.reason,
        source=row.source,
        recorded_at=row.recorded_at,
    )


class DbMeterGateway:
    """Serves one building's entered readings through the Phase D port.

    The session is already RLS-scoped by the caller's dependency, so the
    account boundary is enforced underneath this query too.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_readings(
        self, building_id: str, window_from: date, window_to: date
    ) -> tuple[MeterReading, ...]:
        rows = self._session.execute(
            select(MeterReadingRow, Meter)
            .join(Meter, Meter.id == MeterReadingRow.meter_id)
            .where(
                Meter.building_id == building_id,
                MeterReadingRow.read_at >= window_from,
                MeterReadingRow.read_at <= window_to,
            )
            # (recorded_at, id) makes supersession a total order, so a
            # correction recorded in the same instant still resolves the same
            # way on every run.
            .order_by(MeterReadingRow.recorded_at, MeterReadingRow.id)
        ).all()
        return tuple(to_normalized(row, meter) for row, meter in rows)
