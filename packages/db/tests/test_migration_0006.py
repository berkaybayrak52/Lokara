"""Executable contract for the Page 01b metadata migration."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any


class RecordingOperations:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def __getattr__(self, name: str) -> Any:
        def record(*args: Any, **kwargs: Any) -> None:
            self.calls.append((name, args, kwargs))

        return record


def test_heat_factor_is_backfilled_before_the_constraint(monkeypatch: Any) -> None:
    path = Path(__file__).parents[1] / "alembic/versions/0006_page01b_device_metadata.py"
    spec = spec_from_file_location("migration_0006", path)
    assert spec is not None and spec.loader is not None
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    operations = RecordingOperations()
    monkeypatch.setattr(migration, "op", operations)

    migration.upgrade()

    call_names = [name for name, _, _ in operations.calls]
    backfill_index = next(
        index
        for index, (name, args, _) in enumerate(operations.calls)
        if name == "execute"
        and args == ("UPDATE meter SET valuation_factor_x1000 = 1000 WHERE kind = 'HEAT'",)
    )
    constraint_index = next(
        index
        for index, (name, args, _) in enumerate(operations.calls)
        if name == "create_check_constraint" and args[0] == "ck_meter_heat_valuation_factor"
    )

    assert migration.down_revision == "0005"
    assert call_names.count("add_column") == 5
    assert backfill_index < constraint_index
