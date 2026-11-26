"""End-to-end tests of the five-step flow through the real tool functions.

No network is used: ``ine_get`` and ``ine_get_all_pages`` (as imported by
``ine_mcp.tools``) are replaced by a fake INE API serving small canned data.
Module-level state (operations catalog, sessions, empty-operations registry)
is replaced with fresh instances for every test.
"""

import asyncio
import json

import pytest

from ine_mcp import tools
from ine_mcp.models import (
    SelectMultipleTableDataInput,
    SelectMultipleTableGroupsInput,
    SelectMultipleValuesInput,
    SelectOperationInput,
    SelectTableInput,
)
from ine_mcp.state import EmptyOperationsRegistry, OperationsCatalog, SessionStore

OPERATIONS = [
    {"Id": 293, "Codigo": "EPA", "Nombre": "Encuesta de Población Activa (EPA)",
     "Descripcion": "Unemployment and employment by sex and province"},
    {"Id": 25, "Codigo": "IPC", "Nombre": "Índice de Precios de Consumo (IPC)",
     "Descripcion": "Consumer prices"},
]
TABLES = {"293": [{"Id": 4247, "Nombre": "Tasa de paro por sexo y comunidad autónoma"}]}
GROUPS = {"4247": [{"Id": 70, "Nombre": "Sexo"}, {"Id": 115, "Nombre": "Comunidades autónomas"}]}
VALUES = {
    ("4247", "70"): [{"Id": 1, "FK_Variable": 3, "Nombre": "Hombres"},
                     {"Id": 2, "FK_Variable": 3, "Nombre": "Mujeres"}],
    ("4247", "115"): [{"Id": 31, "FK_Variable": 115, "Nombre": "Murcia, Región de"}],
}
DATA = {"Data": [{"Fecha": 1700000000000, "Valor": 12.3}]}


class FakeIne:
    """Fake INE API: records every call and serves the canned data above."""

    def __init__(self):
        self.calls = []

    async def get_all_pages(self, endpoint, params=None, ttl=None):
        self.calls.append((endpoint, params))
        if endpoint == "OPERACIONES_DISPONIBLES":
            return OPERATIONS
        if endpoint.startswith("TABLAS_OPERACION/"):
            return TABLES.get(endpoint.split("/")[1], [])
        raise AssertionError(f"unexpected endpoint {endpoint}")

    async def get(self, endpoint, params=None, retries=3):
        self.calls.append((endpoint, params))
        parts = endpoint.split("/")
        if parts[0] == "GRUPOS_TABLA":
            return GROUPS[parts[1]]
        if parts[0] == "VALORES_GRUPOSTABLA":
            return VALUES[(parts[1], parts[2])]
        if parts[0] == "DATOS_TABLA":
            return DATA
        raise AssertionError(f"unexpected endpoint {endpoint}")

    def endpoints(self):
        return [c[0] for c in self.calls]


@pytest.fixture
def ine(monkeypatch):
    fake = FakeIne()
    monkeypatch.setattr(tools, "ine_get", fake.get)
    monkeypatch.setattr(tools, "ine_get_all_pages", fake.get_all_pages)
    monkeypatch.setattr(tools, "OPERATIONS", OperationsCatalog())
    monkeypatch.setattr(tools, "SESSIONS", SessionStore())
    monkeypatch.setattr(tools, "EMPTY_OPERATIONS", EmptyOperationsRegistry())
    return fake


def run(coro):
    return json.loads(asyncio.run(coro))


def step1(queries=("paro", "unemployment")):
    return run(tools.ine_select_operation(SelectOperationInput(queries=list(queries))))


def step2(op="293"):
    return run(tools.ine_select_multiple_tables(
        SelectTableInput(operations=[{"operation_id": op}])))


def step3(table="4247"):
    return run(tools.ine_select_multiple_table_groups(
        SelectMultipleTableGroupsInput(requests=[{"table_id": table}])))


def step4(table="4247", group="70"):
    return run(tools.ine_select_multiple_values(
        SelectMultipleValuesInput(requests=[{"table_id": table, "group_id": group}])))


def step5(tv, table="4247", **period):
    return run(tools.ine_select_multiple_table_data(
        SelectMultipleTableDataInput(requests=[{"table_id": table, "tv": tv, **period}])))


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_full_flow_returns_data_with_source(ine):
    ops = step1()
    assert [o["Id"] for o in ops["operations"]] == [293]
    assert "Step 2" in ops["next_step"]

    tables = step2()["results_by_operation"][0]
    assert tables["tables"][0]["Id"] == 4247

    assert [v["Id"] for v in step3()["results_by_table"][0]["selected_variables"]] == [70, 115]

    values = step4()["results"][0]["selected_values"]
    assert {(v["FK_Variable"], v["Id"]) for v in values} == {(3, 1), (3, 2)}

    result = step5(["3:1"])["results"][0]
    assert result["results"] == DATA
    assert result["total_observations"] == 1
    source = result["source"]
    assert source["operation"] == {"id": "293", "name": "Encuesta de Población Activa (EPA)"}
    assert source["table"]["url"] == "https://www.ine.es/jaxiT3/Tabla.htm?t=4247"
    assert source["applied_filters"] == ["3:1"]


def test_operation_can_be_resolved_by_code_in_step_2(ine):
    step1()
    result = step2(op="epa")["results_by_operation"][0]
    assert result["operation_id"] == "293"


def test_default_period_is_latest_observation(ine):
    step1(); step2(); step3(); step4()
    result = step5(["3:1"])["results"][0]
    assert "nult=1" in result["applied_period"]
    data_call = [c for c in ine.calls if c[0].startswith("DATOS_TABLA")][-1]
    assert ("nult", "1") in data_call[1] and ("tv", "3:1") in data_call[1]


def test_nult_wins_over_date_and_a_notice_is_returned(ine):
    step1(); step2(); step3(); step4()
    result = step5(["3:1"], nult=4, date="20240101:20241231")["results"][0]
    assert result["applied_period"].startswith("latest 4")
    assert "ignored" in result["notice"]


# ---------------------------------------------------------------------------
# Enforced order
# ---------------------------------------------------------------------------

def test_step_2_blocks_unknown_operation(ine):
    result = step2(op="9999")
    blocked = result["results_by_operation"][0]
    assert blocked["error"].startswith("BLOCKED")
    assert blocked["required_step"] == 1


def test_step_3_blocks_without_step_2(ine):
    result = step3()["results_by_table"][0]
    assert result["error"].startswith("BLOCKED")
    assert result["required_step"] == 2
    assert not any(e.startswith("GRUPOS_TABLA") for e in ine.endpoints())


def test_step_4_blocks_without_step_3(ine):
    step1(); step2()
    result = step4()["results"][0]
    assert result["error"].startswith("BLOCKED")
    assert result["required_step"] == 3


def test_step_4_blocks_group_that_step_3_did_not_return(ine):
    step1(); step2(); step3()
    result = step4(group="999")["results"][0]
    assert result["error"].startswith("BLOCKED")
    assert not any(e.startswith("VALORES_GRUPOSTABLA") for e in ine.endpoints())


def test_step_5_blocks_without_step_4_and_never_calls_the_api(ine):
    step1(); step2(); step3()
    result = step5(["3:1"])["results"][0]
    assert result["error"].startswith("BLOCKED")
    assert result["required_step"] == 4
    assert not any(e.startswith("DATOS_TABLA") for e in ine.endpoints())


# ---------------------------------------------------------------------------
# tv filters
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_tv", ["70:1", "3:99", "9:1", "not-a-filter"])
def test_step_5_rejects_invalid_filters_without_calling_the_api(ine, bad_tv):
    step1(); step2(); step3(); step4()
    result = step5([bad_tv])["results"][0]
    assert result["error"].startswith("BLOCKED")
    assert not any(e.startswith("DATOS_TABLA") for e in ine.endpoints())


def test_sessions_do_not_share_progress(ine, monkeypatch):
    """What one client queried must not unlock steps for another session."""
    step1(); step2()
    monkeypatch.setattr(tools, "SESSIONS", SessionStore())  # a brand-new client
    result = step3()["results_by_table"][0]
    assert result["error"].startswith("BLOCKED")
