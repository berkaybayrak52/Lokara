"""Shared API-test fixtures."""

import pytest
from lokara_api.routers import buildings as buildings_router


@pytest.fixture(autouse=True)
def _no_network_geocoding(monkeypatch: pytest.MonkeyPatch) -> None:
    """Geocoding (O5) is best-effort over the network; keep tests offline and fast
    by making it return no coordinates, exactly as a blocked/failed lookup would."""
    monkeypatch.setattr(buildings_router, "geocode_address", lambda *args, **kwargs: (None, None))
