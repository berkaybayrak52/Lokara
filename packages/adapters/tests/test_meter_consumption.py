"""The reading fold: how point-in-time registers become period consumption.

This is the seam where "corrections are new rows, never UPDATE" either works or
silently mis-bills, so it is tested on its own — independently of the DB, the
API and both engines.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

from lokara_adapters import (
    MeasurementUnit,
    MeterKind,
    MeterReading,
    ReadingReason,
    ReadingSource,
    StubMeterGateway,
    consumption_by_meter,
    device_reading_segments,
)

JAN = date(2025, 1, 1)
DEC = date(2025, 12, 31)


def reading(
    meter_id: str,
    read_at: date,
    value: str,
    *,
    recorded_at: datetime = datetime(2026, 1, 5, 9, 0, tzinfo=UTC),
    reason: ReadingReason = ReadingReason.PERIODIC,
    unit_id: str | None = "unit-a",
) -> MeterReading:
    return MeterReading(
        meter_id=meter_id,
        unit_id=unit_id,
        kind=MeterKind.HEAT,
        measurement_unit=MeasurementUnit.HKV_UNITS,
        read_at=read_at,
        value=Decimal(value),
        reason=reason,
        source=ReadingSource.MANUAL,
        recorded_at=recorded_at,
    )


class TestConsumptionFold:
    def test_closing_minus_opening(self) -> None:
        result = consumption_by_meter([reading("m1", JAN, "1200"), reading("m1", DEC, "1800")])
        assert result["m1"].value == Decimal(600)
        assert result["m1"].opening.read_at == JAN
        assert result["m1"].closing.read_at == DEC

    def test_a_single_reading_yields_nothing(self) -> None:
        """One register value is not a consumption — the caller must see a
        MISSING reading (→ § 9a estimate), not a zero."""
        assert consumption_by_meter([reading("m1", JAN, "1200")]) == {}

    def test_backwards_register_is_dropped_not_negated(self) -> None:
        """Rollover or a swapped device: refuse rather than bill a negative."""
        assert consumption_by_meter([reading("m1", JAN, "1800"), reading("m1", DEC, "40")]) == {}

    def test_interim_readings_do_not_change_the_period_total(self) -> None:
        """Only the outermost dates bound the period; a Zwischenablesung is
        evidence, not an extra consumption."""
        result = consumption_by_meter(
            [
                reading("m1", JAN, "1200"),
                reading("m1", date(2025, 6, 30), "1500", reason=ReadingReason.INTERIM),
                reading("m1", DEC, "1800"),
            ]
        )
        assert result["m1"].value == Decimal(600)

    def test_meters_are_folded_independently(self) -> None:
        result = consumption_by_meter(
            [
                reading("m1", JAN, "1200"),
                reading("m1", DEC, "1800"),
                reading("m2", JAN, "3400"),
                reading("m2", DEC, "3650"),
            ]
        )
        assert {k: v.value for k, v in result.items()} == {
            "m1": Decimal(600),
            "m2": Decimal(250),
        }


class TestCorrectionSupersedes:
    def test_later_recorded_reading_wins_for_the_same_date(self) -> None:
        """A typo (18000 instead of 1800) is fixed by APPENDING a correction —
        the wrong row survives for the audit trail and stops counting."""
        typo = reading("m1", DEC, "18000", recorded_at=datetime(2026, 1, 5, 9, 0, tzinfo=UTC))
        fix = reading(
            "m1",
            DEC,
            "1800",
            recorded_at=datetime(2026, 1, 6, 8, 30, tzinfo=UTC),
            reason=ReadingReason.CORRECTION,
        )
        result = consumption_by_meter([reading("m1", JAN, "1200"), typo, fix])
        assert result["m1"].value == Decimal(600)
        assert result["m1"].closing.reason is ReadingReason.CORRECTION

    def test_input_order_does_not_decide_the_winner(self) -> None:
        """recorded_at decides, not the order rows happen to arrive in."""
        typo = reading("m1", DEC, "18000", recorded_at=datetime(2026, 1, 5, 9, 0, tzinfo=UTC))
        fix = reading(
            "m1",
            DEC,
            "1800",
            recorded_at=datetime(2026, 1, 6, 8, 30, tzinfo=UTC),
            reason=ReadingReason.CORRECTION,
        )
        forwards = consumption_by_meter([reading("m1", JAN, "1200"), typo, fix])
        backwards = consumption_by_meter([fix, typo, reading("m1", JAN, "1200")])
        assert forwards["m1"].value == backwards["m1"].value == Decimal(600)


class TestStubFixtureReproducesTheGoldens:
    def test_stub_readings_fold_to_the_heating_fixture(self) -> None:
        """The Phase D stub and the seeded DB must agree on every number the
        heating engine consumes — this pins the stub half."""
        readings = StubMeterGateway().list_readings("bld", JAN, DEC)
        folded = {c.meter_id: c.value for c in consumption_by_meter(readings).values()}
        assert folded == {
            "met_heat_main": Decimal(20000),  # kWh, the § 9 denominator
            "met_ww_main": Decimal(40),  # m³ central warm water
            "met_heat_a": Decimal(600),
            "met_heat_b": Decimal(250),
            "met_heat_c": Decimal(150),
            "met_ww_a": Decimal(20),
            "met_ww_b": Decimal(12),
            "met_ww_c": Decimal(8),
        }

    def test_building_meters_carry_no_unit(self) -> None:
        readings = StubMeterGateway().list_readings("bld", JAN, DEC)
        by_meter = consumption_by_meter(readings)
        assert by_meter["met_heat_main"].unit_id is None
        assert by_meter["met_heat_main"].measurement_unit is MeasurementUnit.KWH
        assert by_meter["met_heat_a"].unit_id == "unit_demo_a"
        # Both are HEAT — only the measurement unit separates the building's
        # kWh meter from the flats' dimensionless allocators.
        assert by_meter["met_heat_a"].measurement_unit is MeasurementUnit.HKV_UNITS


class TestDeviceSegments:
    def test_correction_tenant_change_estimate_and_replacement_keep_evidence(self) -> None:
        recorded = datetime(2026, 1, 5, 9, 0, tzinfo=UTC)

        def enriched(
            meter_id: str,
            read_at: date,
            value: str,
            *,
            tenancy_id: str | None,
            reason: ReadingReason,
            recorded_at: datetime = recorded,
            estimated: str | None = None,
            provenance: str | None = None,
        ) -> MeterReading:
            return MeterReading(
                meter_id=meter_id,
                unit_id="WE-02",
                kind=MeterKind.HEAT,
                measurement_unit=MeasurementUnit.HKV_UNITS,
                read_at=read_at,
                value=Decimal(value),
                reason=reason,
                source=ReadingSource.MDL,
                recorded_at=recorded_at,
                meter_serial=meter_id,
                room="Wohnzimmer",
                valuation_factor=Decimal("1.800"),
                tenancy_id=tenancy_id,
                estimated_consumption=None if estimated is None else Decimal(estimated),
                estimation_basis="Vorjahreswert" if estimated is not None else None,
                provenance_ref=provenance,
            )

        typo = enriched(
            "old",
            date(2025, 7, 31),
            "900",
            tenancy_id="Schneider",
            reason=ReadingReason.TENANT_CHANGE,
        )
        correction = enriched(
            "old",
            date(2025, 7, 31),
            "820",
            tenancy_id="Schneider",
            reason=ReadingReason.CORRECTION,
            recorded_at=datetime(2026, 1, 6, 9, 0, tzinfo=UTC),
            provenance="mdl://correction/42",
        )
        readings = (
            enriched("old", JAN, "0", tenancy_id="Schneider", reason=ReadingReason.PERIODIC),
            typo,
            correction,
            enriched(
                "new",
                date(2025, 9, 1),
                "0",
                tenancy_id="Weber",
                reason=ReadingReason.DEVICE_CHANGE,
            ),
            enriched(
                "new",
                DEC,
                "0",
                tenancy_id="Weber",
                reason=ReadingReason.PERIODIC,
                estimated="280",
                provenance="estimate://prior/2024",
            ),
        )

        result = device_reading_segments(readings)

        assert [device.device_id for device in result.devices] == ["old", "new"]
        assert result.devices[0].valuation_factor == Decimal("1.800")
        assert result.spans[0].target_id == "Schneider"
        assert result.spans[0].closing == Decimal("820")
        assert result.spans[0].provenance_refs == ("mdl://correction/42",)
        assert result.spans[1].target_id == "Weber"
        assert result.spans[1].previous_period_units == Decimal("280")
        assert result.spans[1].estimation_basis == "Vorjahreswert"
        assert result.spans[1].reading_reasons == (
            ReadingReason.DEVICE_CHANGE,
            ReadingReason.PERIODIC,
        )
