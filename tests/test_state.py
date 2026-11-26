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

"""Unit tests for ine_mcp.state (flow enforcement, tv validation, sessions)."""

from ine_mcp.state import (
    EmptyOperationsRegistry,
    FlowState,
    OperationsCatalog,
    SessionStore,
)


class FakeClock:
    """Manually advanced clock."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class FakeCtx:
    """Stand-in for the MCP Context carrying HTTP headers."""

    def __init__(self, session_id=None) -> None:
        self.headers = {"mcp-session-id": session_id} if session_id else {}


class BrokenCtx:
    """Context whose 'headers' attribute raises (e.g. stdio transport)."""

    @property
    def headers(self):
        raise RuntimeError("no headers over stdio")


def prepared_state() -> FlowState:
    """A state in which steps 2, 3 and 4 were completed for table 'T'."""
    state = FlowState()
    state.register_tables("25", [{"Id": 1, "Nombre": "Some table"}, {"Id": "T", "Nombre": "Table T"}])
    state.register_groups("T", [{"Id": 70}])
    state.register_values("T", [{"Id": 31, "FK_Variable": 115}, {"Id": 452, "FK_Variable": 18}])
    return state


# ---------------------------------------------------------------------------
# OperationsCatalog
# ---------------------------------------------------------------------------

def test_catalog_resolves_by_id_and_by_code_case_insensitive():
    catalog = OperationsCatalog()
    catalog.register([{"Id": 25, "Codigo": "IPC", "Nombre": "Consumer Price Index"}])
    assert catalog.resolve("25")["name"] == "Consumer Price Index"
    assert catalog.resolve("ipc")["id"] == "25"
    assert catalog.resolve(" IPC ")["id"] == "25"


def test_catalog_returns_none_for_unknown_operation():
    catalog = OperationsCatalog()
    catalog.register([{"Id": 25, "Codigo": "IPC"}])
    assert catalog.resolve("999") is None
    assert catalog.get("999") == {}


def test_catalog_ignores_malformed_items():
    catalog = OperationsCatalog()
    catalog.register([None, "text", {"Nombre": "no id"}])
    assert catalog.resolve("anything") is None


# ---------------------------------------------------------------------------
# FlowState.verify_flow
# ---------------------------------------------------------------------------

def test_verify_flow_blocks_step_3_without_step_2():
    blocked = FlowState().verify_flow("T", 3)
    assert blocked["required_step"] == 2
    assert blocked["error"].startswith("BLOCKED")


def test_verify_flow_blocks_step_4_without_step_3():
    state = FlowState()
    state.register_tables("25", [{"Id": "T"}])
    assert state.verify_flow("T", 4)["required_step"] == 3


def test_verify_flow_blocks_step_5_without_step_4():
    state = FlowState()
    state.register_tables("25", [{"Id": "T"}])
    state.register_groups("T", [{"Id": 70}])
    assert state.verify_flow("T", 5)["required_step"] == 4


def test_verify_flow_allows_each_step_when_previous_ones_are_done():
    state = prepared_state()
    assert state.verify_flow("T", 3) is None
    assert state.verify_flow("T", 4) is None
    assert state.verify_flow("T", 5) is None


def test_has_group():
    state = prepared_state()
    assert state.has_group("T", "70") is True
    assert state.has_group("T", "71") is False
    assert state.has_group("OTHER", "70") is False


# ---------------------------------------------------------------------------
# FlowState.validate_tv
# ---------------------------------------------------------------------------

def test_validate_tv_accepts_valid_filters():
    state = prepared_state()
    assert state.validate_tv("T", ["115:31", "18:452", "18:"]) is None


def test_validate_tv_rejects_bad_format_even_without_values():
    assert "does not match format" in FlowState().validate_tv("T", ["abc"])
    assert FlowState().validate_tv("T", ["115:31"]) is None   # nothing to check against


def test_validate_tv_detects_group_id_used_instead_of_fk_variable():
    error = prepared_state().validate_tv("T", ["70:31"])
    assert error.startswith("FATAL ERROR IN FILTER")


def test_validate_tv_allows_group_id_that_is_also_a_real_fk_variable():
    state = FlowState()
    state.register_groups("T", [{"Id": 115}])
    state.register_values("T", [{"Id": 31, "FK_Variable": 115}])
    assert state.validate_tv("T", ["115:31"]) is None


def test_validate_tv_rejects_unknown_variable_and_unknown_value():
    state = prepared_state()
    assert "was not found" in state.validate_tv("T", ["999:1"])
    assert "does not exist" in state.validate_tv("T", ["115:99"])


# ---------------------------------------------------------------------------
# FlowState.build_source
# ---------------------------------------------------------------------------

def test_build_source_includes_operation_table_url_filters_and_period():
    catalog = OperationsCatalog()
    catalog.register([{"Id": 25, "Codigo": "IPC", "Nombre": "Consumer Price Index"}])
    source = prepared_state().build_source("T", ["115:31"], "latest", catalog)
    assert source["operation"] == {"id": "25", "name": "Consumer Price Index"}
    assert source["table"]["name"] == "Table T"
    assert source["table"]["url"].endswith("t=T")
    assert source["applied_filters"] == ["115:31"]
    assert source["period"] == "latest"


# ---------------------------------------------------------------------------
# SessionStore
# ---------------------------------------------------------------------------

def test_sessions_are_isolated_by_session_id():
    store = SessionStore()
    a1, a2, b = store.get_state(FakeCtx("a")), store.get_state(FakeCtx("a")), store.get_state(FakeCtx("b"))
    assert a1 is a2
    assert a1 is not b


def test_default_state_is_used_without_context_or_headers():
    store = SessionStore()
    default = store.get_state(None)
    assert store.get_state(FakeCtx()) is default
    assert store.get_state(BrokenCtx()) is default


def test_least_recently_used_session_is_evicted():
    store = SessionStore(max_sessions=2)
    first = store.get_state(FakeCtx("a"))
    store.get_state(FakeCtx("b"))
    store.get_state(FakeCtx("a"))          # 'a' becomes the most recently used
    store.get_state(FakeCtx("c"))          # evicts 'b'
    assert store.get_state(FakeCtx("a")) is first
    assert len(store._sessions) == 2


# ---------------------------------------------------------------------------
# EmptyOperationsRegistry
# ---------------------------------------------------------------------------

def test_empty_operations_expire_after_ttl():
    clock = FakeClock()
    registry = EmptyOperationsRegistry(ttl=100, clock=clock)
    key = ("25", None, 0)
    assert registry.is_known_empty(key) is False
    registry.mark(key)
    assert registry.is_known_empty(key) is True
    clock.now = 100
    assert registry.is_known_empty(key) is False
