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

"""Unit tests for ine_mcp.models (input validation rules of the tools)."""

import pytest
from pydantic import ValidationError

from ine_mcp.models import (
    SelectMultipleTableDataInput,
    SelectOperationInput,
    SelectTableInput,
    TableDataFilterItem,
)


def test_queries_are_optional_and_limited_to_15_terms():
    assert SelectOperationInput().queries is None
    with pytest.raises(ValidationError):
        SelectOperationInput(queries=["x"] * 16)


def test_extra_fields_are_forbidden():
    with pytest.raises(ValidationError):
        SelectOperationInput(unknown="value")


def test_select_table_input_requires_at_least_one_operation():
    with pytest.raises(ValidationError):
        SelectTableInput(operations=[])


def test_select_table_input_has_expected_defaults():
    params = SelectTableInput(operations=[{"operation_id": "IPC"}])
    assert params.top_n == 100 and params.det == 0 and params.geo is None


def test_date_pattern_accepts_ranges_and_rejects_garbage():
    assert TableDataFilterItem(table_id="1", tv=["1:2"], date="20240101:20241231").date
    with pytest.raises(ValidationError):
        TableDataFilterItem(table_id="1", tv=["1:2"], date="2024-01-01")


def test_nult_must_be_positive():
    with pytest.raises(ValidationError):
        TableDataFilterItem(table_id="1", tv=["1:2"], nult=0)


def test_tip_only_accepts_a_am_or_m():
    request = {"table_id": "1", "tv": ["1:2"]}
    assert SelectMultipleTableDataInput(requests=[request], tip="AM").tip == "AM"
    with pytest.raises(ValidationError):
        SelectMultipleTableDataInput(requests=[request], tip="X")
