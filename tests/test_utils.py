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

"""Unit tests for ine_mcp.utils (text normalization, filtering and search)."""

from ine_mcp.utils import _normalize, _root, _roots, compact, filter_items, search, search_multiple

# Small catalog reused by several tests.
ITEMS = [
    {"Id": 1, "Codigo": "IPC", "Nombre": "Índice de Precios de Consumo",
     "Descripcion": "Mide la evolución de los precios de bienes y servicios."},
    {"Id": 2, "Codigo": "EPA", "Nombre": "Encuesta de Población Activa",
     "Descripcion": "Paro y empleo por provincias."},
    {"Id": 3, "Codigo": "ECP", "Nombre": "Estadística Continua de Población",
     "Descripcion": "Cifras de población y hogares."},
]


def test_normalize_removes_accents_and_lowercases():
    assert _normalize("Población") == "poblacion"
    assert _normalize("") == ""


def test_root_groups_variants_of_the_same_word():
    assert _root("poblaciones") == _root("poblacion") == "pobla"
    assert _root("precios") == "preci"
    assert _root("ipc") == "ipc"          # short acronyms are compared in full


def test_roots_skips_stop_words_and_short_words():
    words = [w for w, _ in _roots("el paro de los hogares")]
    assert "los" not in words and "el" not in words
    assert "paro" in words and "hogares" in words


def test_compact_removes_empty_fields_and_flattens_nested_objects():
    item = {"Id": 1, "Nombre": "X", "Vacio": "", "Lista": [], "Periodicidad": {"Nombre": "Mensual"}}
    assert compact(item) == {"Id": 1, "Nombre": "X", "Periodicidad": "Mensual"}


def test_filter_items_without_query_returns_everything():
    res = filter_items(ITEMS)
    assert res["filter_mode"] == "no_filter"
    assert res["matches"] == 3


def test_filter_items_all_words_mode():
    res = filter_items(ITEMS, "poblacion activa")
    assert res["filter_mode"] == "all_words"
    assert [i["Id"] for i in res["items"]] == [2]


def test_filter_items_falls_back_to_any_word():
    res = filter_items(ITEMS, "precios paro")     # no item has both words
    assert res["filter_mode"] == "any_word"
    assert [i["Id"] for i in res["items"]] == [1]


def test_filter_items_no_match_returns_whole_catalog():
    res = filter_items(ITEMS, "zzzzzz")
    assert res["filter_mode"] == "no_matches_returning_all"
    assert res["matches"] == 3


def test_filter_items_respects_limit_and_reports_truncation():
    res = filter_items(ITEMS, None, limit=2)
    assert len(res["items"]) == 2 and res["truncated"] is True


def test_search_multiple_matches_in_name_only_by_default():
    res = search_multiple(ITEMS, ["hogares"])      # 'hogares' is only in a description
    assert res["filter_mode"] == "no_matches_returning_all"


def test_search_multiple_can_use_the_description():
    res = search_multiple(ITEMS, ["hogares"], use_description=True)
    assert res["filter_mode"] == "union_of_phrases+description"
    assert [i["Id"] for i in res["items"]] == [3]
    assert res["items"][0]["matched_only_in_description"] == ["hogares"]


def test_search_multiple_orders_by_number_of_matched_phrases():
    # Item 3 matches all three phrases; item 2 matches only 'poblacion'.
    res = search_multiple(ITEMS, ["poblacion", "estadistica", "continua"])
    assert [i["Id"] for i in res["items"]] == [3, 2]
    assert len(res["items"][0]["matched_terms"]) == 3


def test_search_without_queries_delegates_to_filter_items():
    assert search(ITEMS, None)["filter_mode"] == "no_filter"
    assert search(ITEMS, ["ipc"])["items"][0]["Id"] == 1
