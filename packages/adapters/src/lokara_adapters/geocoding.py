"""Geocoding port and best-effort Nominatim adapter."""

import json
import math
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar, Protocol, cast
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class GeocodingResult:
    latitude: float
    longitude: float


class GeocodingGateway(Protocol):
    def geocode(self, address: str) -> GeocodingResult | None:
        """Return coordinates for an address, or ``None`` when unavailable."""
        ...


class DisabledGeocodingGateway:
    """Safe default for environments where external geocoding is disabled."""

    def geocode(self, address: str) -> GeocodingResult | None:
        del address
        return None


class NominatimGeocodingGateway:
    """Small synchronous adapter for Nominatim's public search endpoint."""

    _public_provider_lock: ClassVar[threading.Lock] = threading.Lock()
    _last_public_start_by_clock: ClassVar[dict[int, tuple[Callable[[], float], float]]] = {}

    def __init__(
        self,
        *,
        endpoint: str = "https://nominatim.openstreetmap.org/search",
        contact_email: str = "kontakt@lokara.de",
        timeout_seconds: float = 3.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._endpoint = endpoint
        self._timeout_seconds = timeout_seconds
        self._clock = clock
        self._sleep = sleep
        endpoint_hostname = (urlsplit(endpoint).hostname or "").casefold().rstrip(".")
        self._uses_public_provider = endpoint_hostname == "nominatim.openstreetmap.org"
        contact = contact_email.strip() or "kontakt@lokara.de"
        self._user_agent = f"Lokara/1.0 ({contact})"
        self._cache: dict[str, GeocodingResult | None] = {}

    def geocode(self, address: str) -> GeocodingResult | None:
        normalized_address = " ".join(address.split())
        cache_key = normalized_address.casefold()
        if not cache_key:
            return None
        if cache_key in self._cache:
            return self._cache[cache_key]

        result = self._lookup(normalized_address)
        self._cache[cache_key] = result
        return result

    def _lookup(self, address: str) -> GeocodingResult | None:
        query = urlencode({"q": address, "format": "jsonv2", "limit": "1"})
        separator = "&" if "?" in self._endpoint else "?"
        try:
            request = Request(
                f"{self._endpoint}{separator}{query}",
                headers={"User-Agent": self._user_agent},
            )
            body = self._request(request)
            if body is None:
                return None
            payload = cast(object, json.loads(body))
        except (OSError, ValueError, TypeError):
            return None

        if not isinstance(payload, list) or not payload:
            return None
        first = payload[0]
        if not isinstance(first, dict):
            return None
        latitude_raw: object = first.get("lat")
        longitude_raw: object = first.get("lon")
        coordinate_types = (str, int, float)
        if (
            not isinstance(latitude_raw, coordinate_types)
            or isinstance(latitude_raw, bool)
            or not isinstance(longitude_raw, coordinate_types)
            or isinstance(longitude_raw, bool)
        ):
            return None
        try:
            latitude = float(latitude_raw)
            longitude = float(longitude_raw)
        except (TypeError, ValueError):
            return None
        if (
            not math.isfinite(latitude)
            or not math.isfinite(longitude)
            or not -90.0 <= latitude <= 90.0
            or not -180.0 <= longitude <= 180.0
        ):
            return None
        return GeocodingResult(latitude=latitude, longitude=longitude)

    def _request(self, request: Request) -> bytes | None:
        if not self._uses_public_provider:
            return self._read_response(request)

        with self._public_provider_lock:
            clock_key = id(self._clock)
            state = self._last_public_start_by_clock.get(clock_key)
            now = self._clock()
            last_start = state[1] if state is not None and state[0] is self._clock else None
            if last_start is not None and now >= last_start:
                wait_seconds = max(0.0, 1.0 - (now - last_start))
                if wait_seconds >= self._timeout_seconds:
                    return None
                if wait_seconds > 0.0:
                    self._sleep(wait_seconds)

            request_start = self._clock()
            self._last_public_start_by_clock[clock_key] = (self._clock, request_start)
            return self._read_response(request)

    def _read_response(self, request: Request) -> bytes:
        with urlopen(request, timeout=self._timeout_seconds) as response:
            return cast(bytes, response.read(65_536))
