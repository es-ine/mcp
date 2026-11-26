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

"""Unit tests for ine_mcp.client (pagination, retries, caching and error messages).

No real network is used: the HTTP layer is replaced by small fakes.
"""

import asyncio
import json

import httpx
import pytest

from ine_mcp.client import (
    INE_PAGE_SIZE,
    INEClient,
    endpoint_supports_pagination,
    handle_api_error,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class PagedClient(INEClient):
    """INEClient whose 'get' serves canned pages instead of calling the API."""

    def __init__(self, pages):
        super().__init__(backoff_base=0)
        self.pages = pages          # page number -> list returned for that page
        self.calls = []             # (endpoint, params) of every request

    async def get(self, endpoint, params=None, retries=3):
        self.calls.append((endpoint, params))
        return self.pages.get((params or {}).get("page", 1), [])


class FakeResponse:
    """Minimal stand-in for httpx.Response."""

    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self.payload = payload

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://example.org")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError("error", request=request, response=response)

    def json(self):
        return self.payload


class FakeHttp:
    """Minimal stand-in for httpx.AsyncClient returning queued responses/exceptions."""

    is_closed = False

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    async def get(self, url, params=None):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def make_client(outcomes):
    """Builds an INEClient wired to a FakeHttp with no retry delay."""
    client = INEClient(backoff_base=0)
    client._http = FakeHttp(outcomes)
    return client


def full_page(start=0):
    """A page with exactly INE_PAGE_SIZE items (means 'there may be more')."""
    return [{"Id": start + i} for i in range(INE_PAGE_SIZE)]


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

def test_endpoint_supports_pagination():
    assert endpoint_supports_pagination("OPERACIONES_DISPONIBLES") is True
    assert endpoint_supports_pagination("SERIES_TABLA/27153") is False


def test_non_paginated_endpoint_makes_a_single_request_without_page():
    client = PagedClient({1: [{"Id": 1}]})
    result = asyncio.run(client.get_all_pages("SERIES_TABLA/27153"))
    assert result == [{"Id": 1}]
    assert client.calls == [("SERIES_TABLA/27153", {})]


def test_pagination_stops_at_first_short_page():
    client = PagedClient({1: full_page(0), 2: [{"Id": 999}]})
    result = asyncio.run(client.get_all_pages("OPERACIONES_DISPONIBLES"))
    assert len(result) == INE_PAGE_SIZE + 1
    assert len(client.calls) == 2


def test_pagination_stops_when_api_ignores_page_parameter():
    same = full_page(0)
    client = PagedClient({n: same for n in range(1, 60)})
    result = asyncio.run(client.get_all_pages("OPERACIONES_DISPONIBLES"))
    assert result == same                   # no duplicated data
    assert len(client.calls) == 2           # stopped as soon as a page repeated


def test_pagination_respects_max_pages():
    client = PagedClient({n: full_page(n * 1000) for n in range(1, 60)})
    result = asyncio.run(client.get_all_pages("OPERACIONES_DISPONIBLES", max_pages=3))
    assert len(client.calls) == 3
    assert len(result) == 3 * INE_PAGE_SIZE


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------

def test_result_is_cached_when_ttl_is_given():
    client = PagedClient({1: [{"Id": 1}]})
    first = asyncio.run(client.get_all_pages("OPERACIONES_DISPONIBLES", ttl=60))
    second = asyncio.run(client.get_all_pages("OPERACIONES_DISPONIBLES", ttl=60))
    assert first == second == [{"Id": 1}]
    assert len(client.calls) == 1


def test_empty_results_are_not_cached():
    client = PagedClient({})
    asyncio.run(client.get_all_pages("OPERACIONES_DISPONIBLES", ttl=60))
    asyncio.run(client.get_all_pages("OPERACIONES_DISPONIBLES", ttl=60))
    assert len(client.calls) == 2


def test_no_cache_when_ttl_is_zero():
    client = PagedClient({1: [{"Id": 1}]})
    asyncio.run(client.get_all_pages("OPERACIONES_DISPONIBLES"))
    asyncio.run(client.get_all_pages("OPERACIONES_DISPONIBLES"))
    assert len(client.calls) == 2


# ---------------------------------------------------------------------------
# Retries
# ---------------------------------------------------------------------------

def test_get_returns_json_on_success():
    client = make_client([FakeResponse(200, {"ok": True})])
    assert asyncio.run(client.get("X")) == {"ok": True}


def test_get_retries_transient_status_then_succeeds():
    client = make_client([FakeResponse(503), FakeResponse(200, [1])])
    assert asyncio.run(client.get("X")) == [1]
    assert client._http.calls == 2


def test_get_does_not_retry_non_transient_errors():
    client = make_client([FakeResponse(404)])
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(client.get("X"))
    assert client._http.calls == 1


def test_get_raises_after_exhausting_retries():
    client = make_client([FakeResponse(503), FakeResponse(503)])
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(client.get("X", retries=2))
    assert client._http.calls == 2


def test_get_retries_timeouts():
    client = make_client([httpx.ReadTimeout("slow"), FakeResponse(200, [1])])
    assert asyncio.run(client.get("X")) == [1]


# ---------------------------------------------------------------------------
# Error messages
# ---------------------------------------------------------------------------

def _status_error(code):
    request = httpx.Request("GET", "https://example.org")
    response = httpx.Response(code, request=request)
    return httpx.HTTPStatusError("error", request=request, response=response)


def test_handle_api_error_for_http_statuses():
    assert handle_api_error(_status_error(404)).startswith("Error 404")
    assert handle_api_error(_status_error(400)).startswith("Error 400")
    assert handle_api_error(_status_error(429)).startswith("Error 429")
    assert "INE servers" in handle_api_error(_status_error(502))


def test_handle_api_error_for_network_and_parsing_problems():
    assert "Timeout" in handle_api_error(httpx.ReadTimeout("x"))
    assert "Connection error" in handle_api_error(httpx.ConnectError("x"))
    assert "not valid JSON" in handle_api_error(json.JSONDecodeError("x", "doc", 0))
    assert "Unexpected error (KeyError)" in handle_api_error(KeyError("k"))
