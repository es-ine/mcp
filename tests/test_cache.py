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

"""Unit tests for ine_mcp.cache.TTLCache (time is simulated, no sleeping)."""

from ine_mcp.cache import TTLCache


class FakeClock:
    """Manually advanced clock."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def test_get_returns_none_for_missing_key():
    assert TTLCache(FakeClock()).get("x", ttl=10) is None


def test_value_is_returned_before_ttl_and_dropped_after():
    clock = FakeClock()
    cache = TTLCache(clock)
    cache.set("k", [1, 2])
    clock.now = 9
    assert cache.get("k", ttl=10) == [1, 2]
    clock.now = 10
    assert cache.get("k", ttl=10) is None
    assert cache.get("k", ttl=1000) is None     # the expired entry was removed


def test_clear_removes_everything():
    cache = TTLCache(FakeClock())
    cache.set("k", 1)
    cache.clear()
    assert cache.get("k", ttl=10) is None
