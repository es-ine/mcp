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

"""Small in-memory cache with time-to-live (TTL) expiry."""

import time
from typing import Any, Callable, Hashable, Optional


class TTLCache:
    """In-memory key/value cache whose entries expire after a given TTL.

    The TTL is supplied at read time (``get``), so the same cache can serve
    callers that need different lifetimes. The clock is injectable so tests
    can simulate the passage of time without sleeping.
    """

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        """Creates an empty cache.

        Args:
            clock: Function returning the current time in seconds
                (monotonic by default).
        """
        self._clock = clock
        self._store: dict[Hashable, tuple[float, Any]] = {}

    def get(self, key: Hashable, ttl: float) -> Optional[Any]:
        """Returns the cached value for 'key', or None if missing or expired.

        Expired entries are removed when they are found.

        Args:
            key: Cache key.
            ttl: Maximum age (seconds) the entry may have to still be valid.
        """
        entry = self._store.get(key)
        if entry is None:
            return None
        stamp, value = entry
        if self._clock() - stamp >= ttl:
            del self._store[key]
            return None
        return value

    def set(self, key: Hashable, value: Any) -> None:
        """Stores 'value' under 'key', stamping it with the current time."""
        self._store[key] = (self._clock(), value)

    def clear(self) -> None:
        """Removes every entry from the cache."""
        self._store.clear()
