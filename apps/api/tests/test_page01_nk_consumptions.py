"""The NK CONSUMPTION Bemessung built from cold-water meters (Slice B, B3c/B3d).

Spec: `docs/02-data-model.md` § 5 basis table — Consumption is the one key that
gets **nothing invented** for a vacant or unattributable stretch — and
`docs/08-statement-document.md` "Page 01 output contract": "No document-layer
money math. Every cost line receives engine output" and "A zero consumption
denominator gives renters 0 and leaves the cost with the owner."

These are pure unit tests of `statement_service._nk_consumptions`: no database,
no HTTP. The attribution rule it implements is the whole point of the function —
one meter yields one figure for the window, `ConsumptionValue` names one party,
so a unit whose renter changed inside the window has no honest split available
and must contribute no row at all rather than a day-weighted guess (a flat is
not used evenly, which is why consumption is metered instead of apportioned).
"""

from datetime import date
from decimal import Decimal

from lokara_adapters import MeasurementUnit
from lokara_api.statement_service import MeterFacts, _nk_consumptions
from lokara_db import Unit
from lokara_domain import Occupancy, Period

WINDOW = Period(valid_from=date(2025, 1, 1), valid_to=date(2026, 1, 1))


def _unit(unit_id: str, label: str, area_sqm_x100: int = 5000) -> Unit:
    """A detached `Unit` — `_nk_consumptions` reads only id, label and nothing else."""
    return Unit(
        id=unit_id,
        account_id="acc_test",
        building_id="bld_test",
        label=label,
        area_sqm_x100=area_sqm_x100,
    )


def _facts(
    cold_water: dict[str, Decimal],
    cold_water_units: dict[str, MeasurementUnit] | None = None,
) -> MeterFacts:
    """Only the cold-water fields matter here; the heating ones stay empty."""
    return MeterFacts(
        total_energy_kwh=None,
        warm_water_volume_m3=None,
        has_warm_water=False,
        heat_by_unit={},
        ww_by_unit={},
        cold_water_by_unit=cold_water,
        cold_water_unit_by_unit=cold_water_units or {},
        heat_unit_by_unit={},
        devices=(),
        device_spans=(),
    )


class TestOneCoveringTenancy:
    """One renter across the whole window ⇒ the figure has exactly one owner."""

    def test_the_value_is_attributed_to_that_tenancy_with_its_unit(self) -> None:
        units = [_unit("unit-a", "Wohnung A")]
        occupancies = (
            Occupancy(
                unit_id="unit-a",
                tenancy_id="ten-a",
                period=Period(valid_from=date(2024, 1, 1), valid_to=None),
            ),
        )
        values, findings = _nk_consumptions(
            units,
            occupancies,
            _facts(
                {"unit-a": Decimal("38.5")},
                {"unit-a": MeasurementUnit.CUBIC_METRE},
            ),
            WINDOW,
        )

        assert findings == ()
        [value] = values
        assert value.unit_id == "unit-a"
        assert value.tenancy_id == "ten-a"
        assert value.value == Decimal("38.5")
        # docs/08 rule 2: the Maßeinheit travels on the row that carries the value.
        assert value.measurement_unit is MeasurementUnit.CUBIC_METRE

    def test_a_recorded_zero_is_a_reading_not_a_missing_row(self) -> None:
        """`08-F12`: a renter whose meter read 0 gets a rendered 0,00 € line."""
        units = [_unit("unit-a", "Wohnung A")]
        occupancies = (
            Occupancy(
                unit_id="unit-a",
                tenancy_id="ten-a",
                period=Period(valid_from=date(2024, 1, 1), valid_to=None),
            ),
        )
        values, findings = _nk_consumptions(
            units, occupancies, _facts({"unit-a": Decimal(0)}), WINDOW
        )

        assert findings == ()
        [value] = values
        assert value.value == Decimal(0)
        # No cold-water unit could be established ⇒ the row declares none, and
        # the statement withholds the reference total rather than guessing.
        assert value.measurement_unit is None

    def test_a_unit_without_a_cold_water_meter_contributes_nothing_and_says_nothing(
        self,
    ) -> None:
        """Absent ≠ zero. No meter is not a defect worth a note on the document."""
        units = [_unit("unit-a", "Wohnung A"), _unit("unit-b", "Wohnung B")]
        occupancies = (
            Occupancy(
                unit_id="unit-a",
                tenancy_id="ten-a",
                period=Period(valid_from=date(2024, 1, 1), valid_to=None),
            ),
            Occupancy(
                unit_id="unit-b",
                tenancy_id="ten-b",
                period=Period(valid_from=date(2024, 1, 1), valid_to=None),
            ),
        )
        values, findings = _nk_consumptions(
            units, occupancies, _facts({"unit-a": Decimal(12)}), WINDOW
        )

        assert findings == ()
        assert [v.unit_id for v in values] == ["unit-a"]

    def test_a_vacant_unit_is_a_single_party_and_the_value_lands_on_the_landlord(
        self,
    ) -> None:
        """`docs/02` § 5: Consumption gets nothing invented for vacancy — but a
        real reading taken while the flat stood empty is not invented, and its
        party is the owner (`tenancy_id is None`)."""
        units = [_unit("unit-a", "Wohnung A")]
        values, findings = _nk_consumptions(units, (), _facts({"unit-a": Decimal(3)}), WINDOW)

        assert findings == ()
        [value] = values
        assert value.tenancy_id is None


def _unit_b() -> list[Unit]:
    return [_unit("unit-b", "Wohnung B (EG rechts)", 3000)]


# The demo scenario's move-out: Bernd Muster leaves unit B on 30.06.2025
# (`valid_to` exclusive), leaving vacancy for the rest of the window.
_B1_ONLY: tuple[Occupancy, ...] = (
    Occupancy(
        unit_id="unit-b",
        tenancy_id="ten-b1",
        period=Period(valid_from=date(2021, 9, 1), valid_to=date(2025, 7, 1)),
    ),
)


class TestRenterChangeWithinTheWindow:
    """Two parties, one meter figure ⇒ no row, and a German sentence saying why."""

    def test_renter_then_vacancy_contributes_no_consumption_row(self) -> None:
        values, _ = _nk_consumptions(_unit_b(), _B1_ONLY, _facts({"unit-b": Decimal(20)}), WINDOW)
        assert values == ()

    def test_the_finding_is_german_names_the_unit_and_asks_for_an_interim_reading(
        self,
    ) -> None:
        _, findings = _nk_consumptions(_unit_b(), _B1_ONLY, _facts({"unit-b": Decimal(20)}), WINDOW)
        [finding] = findings
        assert finding.startswith("Wohnung B (EG rechts): ")
        assert "Nutzerwechsel" in finding
        assert "Zwischenablesung" in finding
        # It must never claim a share was allocated anyway.
        assert "keiner Partei zugeordnet" in finding

    def test_two_consecutive_renters_are_also_unattributable(self) -> None:
        occupancies = (
            *_B1_ONLY,
            Occupancy(
                unit_id="unit-b",
                tenancy_id="ten-b2",
                period=Period(valid_from=date(2025, 7, 1), valid_to=None),
            ),
        )
        values, findings = _nk_consumptions(
            _unit_b(), occupancies, _facts({"unit-b": Decimal(20)}), WINDOW
        )
        assert values == ()
        assert len(findings) == 1

    def test_a_change_outside_the_window_still_leaves_one_party(self) -> None:
        """The clip is what decides. A move-out on 01.01.2025 means the whole
        2025 window had exactly one user, so the figure is attributable."""
        occupancies = (
            Occupancy(
                unit_id="unit-b",
                tenancy_id="ten-b1",
                period=Period(valid_from=date(2021, 9, 1), valid_to=date(2025, 1, 1)),
            ),
            Occupancy(
                unit_id="unit-b",
                tenancy_id="ten-b2",
                period=Period(valid_from=date(2025, 1, 1), valid_to=None),
            ),
        )
        values, findings = _nk_consumptions(
            _unit_b(), occupancies, _facts({"unit-b": Decimal(20)}), WINDOW
        )
        assert findings == ()
        [value] = values
        assert value.tenancy_id == "ten-b2"
