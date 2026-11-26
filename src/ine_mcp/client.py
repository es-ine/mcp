# -*- coding: utf-8 -*-
# ------------------------------------------------------------------------------ 
# Copyright (C) [2025] Instituto Nacional de Estadística 
# 
# Este archivo forma parte del proyecto INE MCP. 
# 
# Licenciado bajo la Licencia Pública de la Unión Europea (EUPL) v.1.2. 
# Puede obtener una copia de la licencia en la raiz de este proyecto o en: 
# https://eupl.eu/1.2/es/ 
# 
# A menos que se indique lo contrario, este software se distribuye 
# "TAL CUAL", SIN GARANTÍAS NI CONDICIONES DE NINGÚN TIPO. 
# Consulte la licencia para conocer los términos específicos. 
# ------------------------------------------------------------------------------ 
# Copyright (C) [2025] National Institute of Statistics 
# 
# This file is part of the INE MCP project. 
# 
# Licensed under the European Union Public License (EUPL) v.1.2. 
# You can obtain a copy of the license at the root of this project or at: 
# https://eupl.eu/1.2/es/ 
# 
# Unless otherwise indicated, this software is distributed 
# "AS IS", WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND. 
# See the license for specific terms. 
# ------------------------------------------------------------------------------ 

"""HTTP Client for the INE (National Statistics Institute) JSON API."""

import asyncio
import json
from typing import Any, Optional, Sequence, Union

import httpx

from .cache import TTLCache

# INE API Base URL
INE_API_BASE = "https://servicios.ine.es/wstempus/js/ES"

# Default timeout for requests. Differentiated timeouts are used:
# short 'connect' (fail fast if there's no network) and more generous 'read', because
# some endpoints (e.g. DATOS_TABLA or TABLAS_OPERACION with det=2 on
# large operations/tables) can take quite a while to respond.
DEFAULT_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=10.0)

# Maximum items per page in the INE API (for endpoints that
# DO support real pagination, see INE_ENDPOINTS_NON_PAGINATED).
INE_PAGE_SIZE = 500

# Endpoint prefixes for which the INE API does NOT implement real pagination
# via the 'page' parameter: the API ALWAYS returns the complete list
# of results, regardless of the 'page' value sent.
# Source: official documentation of the INE JSON API (API Reference /
# Other use cases), where SERIES_TABLA is always documented and exemplified
# WITHOUT 'page' (unlike SERIES_OPERACION/OPERACIONES_DISPONIBLES, which do
# show examples with ?page=1, ?page=2...).
# If this is ignored and you paginate "blindly" over these endpoints, a loop
# like `while True: request page N` never detects the end (the response is
# never shortened) and hangs until the connection timeout is reached.
INE_ENDPOINTS_NON_PAGINATED = ("SERIES_TABLA",)

# Maximum number of simultaneous requests: tools launch up to 20 requests in
# parallel with asyncio.gather and without this limit it is easy to receive
# a 429 from INE.
_MAX_CONCURRENCY = 8

# Transient HTTP status codes worth retrying.
_RETRYABLE_STATUSES = (429, 502, 503, 504)

ParamsType = Union[dict[str, Any], Sequence[tuple[str, Any]], None]


def endpoint_supports_pagination(endpoint: str) -> bool:
    """Indicates whether an INE API endpoint supports real pagination."""
    return not endpoint.startswith(INE_ENDPOINTS_NON_PAGINATED)


class INEClient:
    """Asynchronous client for the INE JSON API.

    Owns a single shared HTTP connection pool, limits the number of
    simultaneous requests, retries transient failures with exponential
    backoff, and caches complete multi-page results in memory.
    """

    def __init__(
        self,
        base_url: str = INE_API_BASE,
        max_concurrency: int = _MAX_CONCURRENCY,
        backoff_base: float = 1.0,
    ) -> None:
        """Creates the client (no connection is opened until the first request).

        Args:
            base_url: Base URL of the INE API.
            max_concurrency: Maximum number of simultaneous requests.
            backoff_base: Seconds of the first retry delay; it doubles on
                every further attempt (tests set it to 0 to avoid waiting).
        """
        self._base_url = base_url
        self._backoff_base = backoff_base
        self._sem = asyncio.Semaphore(max_concurrency)
        self._http: Optional[httpx.AsyncClient] = None
        self._cache = TTLCache()

    def _get_http_client(self) -> httpx.AsyncClient:
        """Returns the shared httpx client, creating it if needed or closed."""
        if self._http is None or self._http.is_closed:
            self._http = httpx.AsyncClient(
                timeout=DEFAULT_TIMEOUT,
                follow_redirects=True,
                limits=httpx.Limits(max_connections=16),
            )
        return self._http

    async def get(self, endpoint: str, params: ParamsType = None, retries: int = 3) -> Any:
        """
        Performs a GET request to the INE API (shared client, limited
        concurrency, and retries with exponential backoff on transient failures).

        Args:
            endpoint: Relative endpoint (e.g. 'OPERACIONES_DISPONIBLES')
            params: Optional query string parameters (dict or list of tuples)
            retries: Maximum number of attempts for 429/502/503/504, timeouts, and
                connection errors

        Returns:
            JSON response from the API (list or dict)

        Raises:
            httpx.HTTPStatusError: If the API returns an HTTP error (after retrying)
            httpx.TimeoutException: If the request times out across all attempts
            ValueError: If the response is not valid JSON
        """
        url = f"{self._base_url}/{endpoint}"
        retries = max(1, retries)
        for attempt in range(retries):
            last_attempt = attempt == retries - 1
            try:
                async with self._sem:
                    resp = await self._get_http_client().get(url, params=params or None)
                if resp.status_code in _RETRYABLE_STATUSES and not last_attempt:
                    await asyncio.sleep(self._backoff_base * 2 ** attempt)
                    continue
                resp.raise_for_status()
                return resp.json()
            except (httpx.TimeoutException, httpx.ConnectError):
                if last_attempt:
                    raise
                await asyncio.sleep(self._backoff_base * 2 ** attempt)
        raise RuntimeError("INEClient.get: retry loop finished without result")  # unreachable

    async def _get_all_pages_without_cache(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        max_pages: int = 50,
    ) -> list:
        """
        Downloads all results from an INE API endpoint, concatenating pages
        until the API stops returning new results.

        Centralizes the pagination logic used by several tools
        (ine_select_operation, ine_select_multiple_tables)
        to prevent infinite loops:

        - If the endpoint does not truly paginate (see
          INE_ENDPOINTS_NON_PAGINATED, e.g. SERIES_TABLA), a SINGLE request
          is made without sending 'page' and the result is returned as is.
        - If the endpoint does paginate, it advances page by page with two
          safeguards to never hang, even if the API behaves unexpectedly:
            1. Hard page limit (max_pages).
            2. "No progress" detection: if two consecutive pages are
               identical (the API is ignoring 'page'), the loop breaks.

        Args:
            endpoint: Relative endpoint, e.g. 'SERIES_TABLA/27153'
            params: Additional query parameters (excluding 'page')
            max_pages: Maximum number of pages to request as a safeguard

        Returns:
            List containing all accumulated elements from all pages.
        """
        base_params = dict(params or {})

        if not endpoint_supports_pagination(endpoint):
            # SERIES_TABLA type endpoint: the API returns everything in a single
            # response and does not support real pagination, so 'page' is not sent.
            resp = await self.get(endpoint, base_params)
            return resp if isinstance(resp, list) else []

        accumulated: list = []
        previous: list | None = None
        page = 1

        while page <= max_pages:
            resp = await self.get(endpoint, {**base_params, "page": page})

            if not isinstance(resp, list) or not resp:
                break

            # Safeguard: if the API returns the exact same page as the previous
            # one (e.g. because it practically ignores 'page' for this specific
            # endpoint), we stop downloading to avoid repeating data or looping indefinitely.
            if resp == previous:
                break

            accumulated.extend(resp)
            previous = resp

            if len(resp) < INE_PAGE_SIZE:
                break

            page += 1

        return accumulated

    async def get_all_pages(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        max_pages: int = 50,
        ttl: int = 0,
    ) -> list:
        """
        Same as _get_all_pages_without_cache, with optional caching.

        Args:
            ttl: Seconds to cache the complete result (0 = no cache). Only NON-empty
                results are cached, to avoid pinning a transient failure.
        """
        if ttl <= 0:
            return await self._get_all_pages_without_cache(endpoint, params, max_pages)

        key = (endpoint, tuple(sorted((params or {}).items())))
        cached = self._cache.get(key, ttl)
        if cached is not None:
            return list(cached)

        result = await self._get_all_pages_without_cache(endpoint, params, max_pages)
        if result:
            self._cache.set(key, result)
        return list(result)


# Process-wide client shared by all tools (single connection pool and cache).
_default_client = INEClient()


async def ine_get(endpoint: str, params: ParamsType = None, retries: int = 3) -> Any:
    """Module-level shortcut for INEClient.get using the shared default client."""
    return await _default_client.get(endpoint, params, retries)


async def ine_get_all_pages(
    endpoint: str,
    params: dict[str, Any] | None = None,
    max_pages: int = 50,
    ttl: int = 0,
) -> list:
    """Module-level shortcut for INEClient.get_all_pages using the shared default client."""
    return await _default_client.get_all_pages(endpoint, params, max_pages, ttl)


def handle_api_error(e: Exception) -> str:
    """
    Converts API exceptions into clear, actionable error messages.

    Args:
        e: Caught exception

    Returns:
        Error message formatted as a string
    """
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        if status == 404:
            return (
                "Error 404: Resource not found. "
                "Check that the operation or table identifier is correct. "
                "Use 'ine_select_operation' to view available operations."
            )
        if status == 400:
            return (
                "Error 400: Bad request. "
                "Review the sent parameters (identifiers, filters, etc.)."
            )
        if status == 429:
            return "Error 429: Too many requests. Wait a few seconds before retrying."
        if status >= 500:
            return (
                f"Error {status}: Internal failure in INE servers. "
                "Please try again later."
            )
        return f"HTTP Error {status}: {e.response.text[:200]}"

    if isinstance(e, httpx.TimeoutException):
        return (
            "Error: Timeout. The INE API took too long to respond. "
            "Please try again or reduce the number of requested results."
        )

    if isinstance(e, httpx.ConnectError):
        return (
            "Connection error: Cannot reach the INE API. "
            "Check your internet connection."
        )

    if isinstance(e, json.JSONDecodeError):
        return (
            "Error: The INE API returned a response that is not valid JSON "
            "(possibly an unexpected redirect or error page). "
            "Please try again; if it persists, check the identifier used."
        )

    return f"Unexpected error ({type(e).__name__}): {str(e)}"
