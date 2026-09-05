"""Shared API-test fixtures."""

from collections.abc import Iterator

import pytest
from lokara_api.routers import buildings as buildings_router


class _NoNetworkGeocodingGateway:
    def __init__(
        self,
        *,
        endpoint: str,
        contact_email: str,
        timeout_seconds: float,
    ) -> None:
        del endpoint, contact_email, timeout_seconds

    def geocode(self, address: str) -> None:
        del address
        return None


@pytest.fixture(autouse=True)
def _no_network_geocoding(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Geocoding (O5) is best-effort over the network; keep tests offline and fast
    by making it return no coordinates, exactly as a blocked/failed lookup would."""
    buildings_router.get_geocoding_gateway.cache_clear()
    monkeypatch.setattr(
        buildings_router,
        "NominatimGeocodingGateway",
        _NoNetworkGeocodingGateway,
    )
    yield
    buildings_router.get_geocoding_gateway.cache_clear()
