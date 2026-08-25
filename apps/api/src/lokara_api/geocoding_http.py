"""HTTP transport for the Nominatim geocoding adapter.

`packages/adapters` owns the vendor format and stays socket-free (see
`lokara_adapters.geocoding`). This module is the only place that speaks HTTP to
the provider, and it is the only place the timeout, the one-request-per-second
policy and the response cap live.

Every failure resolves to ``None``. Geocoding is best effort: a building is
created with or without coordinates, never blocked by a provider.
"""

import threading
import time
from collections.abc import Callable
from typing import ClassVar, cast
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from lokara_adapters.geocoding import (
    NOMINATIM_DEFAULT_CONTACT,
    NOMINATIM_MAX_RESPONSE_BYTES,
    NOMINATIM_MIN_SECONDS_BETWEEN_REQUESTS,
    NOMINATIM_PUBLIC_ENDPOINT,
    NOMINATIM_PUBLIC_HOST,
    GeocodingResult,
    nominatim_query_params,
    nominatim_user_agent,
    parse_nominatim_payload,
)


class NominatimGeocodingGateway:
    """Small synchronous client for Nominatim's public search endpoint."""

    _public_provider_lock: ClassVar[threading.Lock] = threading.Lock()
    _last_public_start_by_clock: ClassVar[dict[int, tuple[Callable[[], float], float]]] = {}

    def __init__(
        self,
        *,
        endpoint: str = NOMINATIM_PUBLIC_ENDPOINT,
        contact_email: str = NOMINATIM_DEFAULT_CONTACT,
        timeout_seconds: float = 3.0,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._endpoint = endpoint
        self._timeout_seconds = timeout_seconds
        self._clock = clock
        self._sleep = sleep
        endpoint_hostname = (urlsplit(endpoint).hostname or "").casefold().rstrip(".")
        self._uses_public_provider = endpoint_hostname == NOMINATIM_PUBLIC_HOST
        self._user_agent = nominatim_user_agent(contact_email)
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
        query = urlencode(nominatim_query_params(address))
        separator = "&" if "?" in self._endpoint else "?"
        try:
            request = Request(
                f"{self._endpoint}{separator}{query}",
                headers={"User-Agent": self._user_agent},
            )
            body = self._request(request)
        except (OSError, ValueError, TypeError):
            return None
        if body is None:
            return None
        return parse_nominatim_payload(body)

    def _request(self, request: Request) -> bytes | None:
        if not self._uses_public_provider:
            return self._read_response(request)

        with self._public_provider_lock:
            clock_key = id(self._clock)
            state = self._last_public_start_by_clock.get(clock_key)
            now = self._clock()
            last_start = state[1] if state is not None and state[0] is self._clock else None
            if last_start is not None and now >= last_start:
                wait_seconds = max(0.0, NOMINATIM_MIN_SECONDS_BETWEEN_REQUESTS - (now - last_start))
                if wait_seconds >= self._timeout_seconds:
                    return None
                if wait_seconds > 0.0:
                    self._sleep(wait_seconds)

            request_start = self._clock()
            self._last_public_start_by_clock[clock_key] = (self._clock, request_start)
            return self._read_response(request)

    def _read_response(self, request: Request) -> bytes:
        with urlopen(request, timeout=self._timeout_seconds) as response:
            return cast(bytes, response.read(NOMINATIM_MAX_RESPONSE_BYTES))
