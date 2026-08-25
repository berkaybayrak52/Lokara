"""UI-03 Nominatim adapter contract without network access."""

import json
from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request

import pytest
from lokara_adapters import geocoding
from lokara_adapters.geocoding import DisabledGeocodingGateway, NominatimGeocodingGateway


class _Response:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, _limit: int) -> bytes:
        return self._body


def _json_response(payload: object) -> _Response:
    return _Response(json.dumps(payload).encode())


def test_nominatim_request_is_identified_bounded_and_parses_first_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Request, float]] = []

    def fake_urlopen(request: Request, *, timeout: float) -> _Response:
        calls.append((request, timeout))
        return _json_response(
            [
                {"lat": "50.110924", "lon": "8.682127"},
                {"lat": "1", "lon": "2"},
            ]
        )

    monkeypatch.setattr(geocoding, "urlopen", fake_urlopen)
    gateway = NominatimGeocodingGateway(
        contact_email="geo@lokara.de",
        timeout_seconds=2.75,
    )

    result = gateway.geocode("  Musterstraße   12,  60311 Frankfurt am Main, Deutschland  ")

    assert result is not None
    assert result.latitude == pytest.approx(50.110924)
    assert result.longitude == pytest.approx(8.682127)
    [(request, timeout)] = calls
    parsed = urlsplit(request.full_url)
    assert f"{parsed.scheme}://{parsed.netloc}{parsed.path}" == (
        "https://nominatim.openstreetmap.org/search"
    )
    assert parse_qs(parsed.query) == {
        "q": ["Musterstraße 12, 60311 Frankfurt am Main, Deutschland"],
        "format": ["jsonv2"],
        "limit": ["1"],
    }
    assert request.get_header("User-agent") == "Lokara/1.0 (geo@lokara.de)"
    assert timeout == 2.75


def test_equivalent_normalized_casefold_addresses_share_one_cached_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = 0

    def fake_urlopen(_request: Request, *, timeout: float) -> _Response:
        nonlocal call_count
        assert timeout == 3.0
        call_count += 1
        return _json_response([{"lat": "50.1", "lon": "8.6"}])

    monkeypatch.setattr(geocoding, "urlopen", fake_urlopen)
    gateway = NominatimGeocodingGateway()

    first = gateway.geocode("Musterstraße 12, 60311 Frankfurt")
    second = gateway.geocode("  MUSTERSTRASSE   12,  60311  FRANKFURT ")

    assert first == second
    assert call_count == 1


def test_public_provider_rate_limit_is_shared_across_gateway_instances(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = 100.0
    starts: list[float] = []
    sleeps: list[float] = []

    def clock() -> float:
        return now

    def sleep(seconds: float) -> None:
        nonlocal now
        sleeps.append(seconds)
        now += seconds

    def fake_urlopen(_request: Request, *, timeout: float) -> _Response:
        assert timeout == 3.0
        starts.append(clock())
        return _json_response([{"lat": "50.1", "lon": "8.6"}])

    monkeypatch.setattr(geocoding, "urlopen", fake_urlopen)
    first = NominatimGeocodingGateway(clock=clock, sleep=sleep)
    second = NominatimGeocodingGateway(
        endpoint="https://nominatim.openstreetmap.org./search",
        clock=clock,
        sleep=sleep,
    )

    assert first.geocode("Adresse Eins") is not None
    assert first.geocode("  ADRESSE   EINS ") is not None  # cache hit: no provider budget
    assert second.geocode("Adresse Zwei") is not None

    assert starts == [100.0, 101.0]
    assert sleeps == [1.0]


@pytest.mark.parametrize(
    "body",
    [
        json.dumps([]).encode(),
        json.dumps({}).encode(),
        json.dumps([None]).encode(),
        json.dumps([{"lat": "ungueltig", "lon": "8.6"}]).encode(),
        json.dumps([{"lat": "nan", "lon": "8.6"}]).encode(),
        json.dumps([{"lat": "50.1", "lon": "inf"}]).encode(),
        b"not-json",
    ],
)
def test_empty_malformed_and_nonfinite_results_return_none(
    monkeypatch: pytest.MonkeyPatch, body: bytes
) -> None:
    monkeypatch.setattr(geocoding, "urlopen", lambda *_args, **_kwargs: _Response(body))
    assert NominatimGeocodingGateway().geocode("Musterstraße 12, Frankfurt") is None


@pytest.mark.parametrize(
    ("latitude", "longitude"),
    [
        ("90.000001", "8.6"),
        ("-90.000001", "8.6"),
        ("50.1", "180.000001"),
        ("50.1", "-180.000001"),
    ],
)
def test_coordinates_outside_world_bounds_return_none(
    monkeypatch: pytest.MonkeyPatch, latitude: str, longitude: str
) -> None:
    monkeypatch.setattr(
        geocoding,
        "urlopen",
        lambda *_args, **_kwargs: _json_response([{"lat": latitude, "lon": longitude}]),
    )
    assert NominatimGeocodingGateway().geocode("Musterstraße 12, Frankfurt") is None


@pytest.mark.parametrize("error_factory", [OSError, ValueError, TypeError])
def test_network_edge_failures_and_empty_addresses_return_none(
    monkeypatch: pytest.MonkeyPatch,
    error_factory: Callable[[], Exception],
) -> None:
    call_count = 0

    def failing_urlopen(*_args: Any, **_kwargs: Any) -> _Response:
        nonlocal call_count
        call_count += 1
        raise error_factory()

    monkeypatch.setattr(geocoding, "urlopen", failing_urlopen)
    gateway = NominatimGeocodingGateway()

    assert gateway.geocode("Musterstraße 12, Frankfurt") is None
    assert gateway.geocode("   ") is None
    assert call_count == 1


def test_disabled_gateway_never_geocodes() -> None:
    assert DisabledGeocodingGateway().geocode("Musterstraße 12, Frankfurt") is None
