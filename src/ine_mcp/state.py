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

"""Flow state tracking and validation for the 5-step INE workflow.

The server ENFORCES the order of the steps in code: each step is blocked if
the preceding ones were not completed for the same table in the same MCP
session. This module holds the classes that remember what each client has
queried and that verify it.
"""

import re
import time
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Callable, Hashable, Optional

from .cache import TTLCache
from .config import (
    DEFAULT_SESSION_KEY,
    EMPTY_OPERATION_TTL,
    INE_TABLE_URL,
    MAX_SESSIONS,
    SESSION_ID_HEADER,
)

if TYPE_CHECKING:  # Only needed for type hints; avoids requiring 'mcp' at runtime.
    from mcp.server.mcpserver import Context

# Format of a 'tv' filter: 'FK_Variable:Id', or 'FK_Variable:' for all values.
TV_PATTERN = re.compile(r"^\d+:\d*$")


class OperationsCatalog:
    """Registry of the INE statistical operations seen so far.

    The catalog is public data, identical for every client, so a single
    instance is shared by all sessions. Operations can be resolved either by
    numeric id or by (case-insensitive) code, e.g. '25' or 'IPC'.
    """

    def __init__(self) -> None:
        """Creates an empty catalog."""
        self._by_id: dict[str, dict] = {}      # id -> {"id", "code", "name"}
        self._aliases: dict[str, str] = {}     # uppercase code -> id

    def register(self, items: Optional[list]) -> None:
        """Adds API operation objects (with 'Id', 'Codigo', 'Nombre') to the catalog."""
        for it in items or []:
            if not isinstance(it, dict) or it.get("Id") is None:
                continue
            oid = str(it["Id"])
            self._by_id[oid] = {"id": oid, "code": it.get("Codigo"), "name": it.get("Nombre")}
            if it.get("Codigo"):
                self._aliases[str(it["Codigo"]).upper()] = oid

    def resolve(self, operation_id: str) -> Optional[dict]:
        """Returns the operation matching an id or code, or None if unknown."""
        key = str(operation_id).strip()
        if key in self._by_id:
            return self._by_id[key]
        oid = self._aliases.get(key.upper())
        return self._by_id.get(oid) if oid else None

    def get(self, operation_id: Any) -> dict:
        """Returns the operation with exactly this id, or an empty dict."""
        return self._by_id.get(str(operation_id), {})


class FlowState:
    """Entities one client has queried, used to verify adherence to the 5-step flow.

    There is one instance per MCP session (see SessionStore), so what one
    client queries never unlocks steps for another.
    """

    def __init__(self) -> None:
        """Creates an empty state (nothing queried yet)."""
        self.tables: dict[str, dict] = {}   # table_id -> {"name", "operation_id"}
        self.groups: dict[str, set] = {}    # table_id -> {group/variable ids}
        self.values: dict[str, dict] = {}   # table_id -> {"fks": set, "pairs": set}

    # -- Registration (called as the steps are completed) ---------------

    def register_tables(self, operation_id: str, items: Optional[list]) -> None:
        """Records the tables returned by Step 2 for an operation."""
        for it in items or []:
            if not isinstance(it, dict) or it.get("Id") is None:
                continue
            self.tables[str(it["Id"])] = {"name": it.get("Nombre"), "operation_id": operation_id}

    def register_groups(self, table_id: str, items: Optional[list]) -> None:
        """Records the variable/group ids returned by Step 3 for a table."""
        ids = self.groups.setdefault(table_id, set())
        for it in items or []:
            if isinstance(it, dict) and it.get("Id") is not None:
                ids.add(str(it["Id"]))

    def register_values(self, table_id: str, items: Optional[list]) -> None:
        """Records the (FK_Variable, Id) pairs returned by Step 4 for a table."""
        reg = self.values.setdefault(table_id, {"fks": set(), "pairs": set()})
        for it in items or []:
            if isinstance(it, dict) and it.get("Id") is not None and it.get("FK_Variable") is not None:
                fk, vid = str(it["FK_Variable"]), str(it["Id"])
                reg["fks"].add(fk)
                reg["pairs"].add((fk, vid))

    def has_group(self, table_id: str, group_id: str) -> bool:
        """True if 'group_id' was returned by Step 3 for 'table_id'."""
        return group_id in self.groups.get(table_id, set())

    # -- Verification ---------------------------------------------------

    def verify_flow(self, table_id: str, current_step: int) -> Optional[dict]:
        """Returns a BLOCKED error if any step before 'current_step' is missing for the table.

        Returns None when every required previous step has been completed.
        """
        checks = [
            (2, table_id not in self.tables, "ine_select_multiple_tables",
             "table does not originate from any table search in this session",
             'Step 2: Call ine_select_multiple_tables with candidate operation IDs (all in a SINGLE call) and choose the most suitable table by reading their names.'),
            (3, table_id not in self.groups, "ine_select_multiple_table_groups",
             "variables/groups for this table have not been queried",
             'Step 3: Call ine_select_multiple_table_groups with the selected table ID to identify variables/groups to filter by.'),
            (4, table_id not in self.values, "ine_select_multiple_values",
             "values for variables in this table have not been queried",
             "Step 4: Call ine_select_multiple_values (SINGLE call, all groups) using the 'Id' of each variable as 'group_id'."),
        ]
        for step, missing, tool, reason, next_step_desc in checks:
            if step < current_step and missing:
                return {
                    "table_id": table_id,
                    "error": (f"BLOCKED: Cannot execute step {current_step} without completing "
                              f"step {step} ({tool}) for table '{table_id}': {reason}."),
                    "required_step": step,
                    "next_step": next_step_desc,
                }
        return None

    def validate_tv(self, table_id: str, tv: list[str]) -> Optional[str]:
        """Validates 'tv' filters for format and, if values were fetched, for existence.

        Returns an error message, or None if every filter is valid.
        """
        reg = self.values.get(table_id)
        groups = self.groups.get(table_id, set())
        for raw in tv:
            f = raw.strip()
            if not TV_PATTERN.match(f):
                return (f"Filter '{raw}' does not match format 'FK_Variable:Id' (e.g., '115:31', or '18:' "
                        f"for all values of variable 18).")
            if not reg:
                continue
            fk, _, vid = f.partition(":")

            # A group Id is only a mistake when it is not ALSO a real FK_Variable of
            # the queried values: both numbering spaces can overlap.
            if fk in groups and fk not in reg["fks"]:
                return (
                    f"FATAL ERROR IN FILTER '{f}': You used the Group ID ('{fk}') instead of the 'FK_Variable'. "
                    f"The INE API strictly requires the 'FK_Variable' field returned inside the value objects "
                    f"of 'ine_select_multiple_values' (Step 4), NOT the group or variable ID. "
                    f"Please look back at Step 4 results, extract the correct 'FK_Variable' (e.g. 115), and retry with 'FK_Variable:Id'."
                )

            if fk not in reg["fks"]:
                return (
                    f"In filter '{f}', variable/FK '{fk}' was not found in queried values for table {table_id}. "
                    f"Ensure you are using the exact 'FK_Variable' property from Step 4 response."
                )

            if vid and (fk, vid) not in reg["pairs"]:
                return (f"In filter '{f}', value '{vid}' does not exist for variable '{fk}' in table "
                        f"{table_id}. Use an 'Id' returned by ine_select_multiple_values.")
        return None

    # -- Output ---------------------------------------------------------

    def build_source(
        self, table_id: str, tv: list[str], period: str, catalog: OperationsCatalog
    ) -> dict:
        """Builds the 'source' object (operation, table with public URL, filters, period).

        Args:
            table_id: Table the data comes from.
            tv: Filters applied to the query.
            period: Human-readable description of the applied period.
            catalog: Operations catalog used to look up the operation name.
        """
        table = self.tables.get(table_id, {})
        op_id = table.get("operation_id")
        op = catalog.get(op_id) if op_id is not None else {}
        return {
            "operation": {"id": op.get("id", op_id), "name": op.get("name")},
            "table": {
                "id": table_id,
                "name": table.get("name"),
                "url": INE_TABLE_URL.format(table_id=table_id),
            },
            "applied_filters": tv,
            "period": period,
        }


class SessionStore:
    """Keeps one FlowState per MCP session, evicting the least recently used.

    Bounded so a long-running HTTP server does not grow without limit.
    """

    def __init__(
        self,
        max_sessions: int = MAX_SESSIONS,
        header_name: str = SESSION_ID_HEADER,
    ) -> None:
        """Creates an empty store.

        Args:
            max_sessions: Maximum number of sessions kept in memory.
            header_name: HTTP header that carries the session id.
        """
        self._max_sessions = max_sessions
        self._header_name = header_name
        self._sessions: "OrderedDict[str, FlowState]" = OrderedDict()  # LRU first

    def _session_key(self, ctx: Optional["Context"]) -> str:
        """Returns the session id of the request, or the default key if none."""
        if ctx is None:
            return DEFAULT_SESSION_KEY
        try:
            headers = ctx.headers
        except Exception:
            return DEFAULT_SESSION_KEY
        if not headers:
            return DEFAULT_SESSION_KEY
        return headers.get(self._header_name) or DEFAULT_SESSION_KEY

    def get_state(self, ctx: Optional["Context"]) -> FlowState:
        """Returns the flow state of the session that issued the current request.

        Over Streamable HTTP the session is identified by the 'mcp-session-id'
        header. Over stdio (one client per process), or when the transport
        carries no session id, a single default state is used.
        """
        key = self._session_key(ctx)
        state = self._sessions.get(key)
        if state is None:
            state = self._sessions[key] = FlowState()
            while len(self._sessions) > self._max_sessions:
                self._sessions.popitem(last=False)
        else:
            self._sessions.move_to_end(key)
        return state


class EmptyOperationsRegistry:
    """Remembers, for a while, operations that returned no tables.

    Entries expire, so a transient empty response from INE does not rule an
    operation out for the lifetime of the process.
    """

    def __init__(
        self,
        ttl: float = EMPTY_OPERATION_TTL,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Creates an empty registry.

        Args:
            ttl: Seconds an entry stays valid.
            clock: Time source (injectable for tests).
        """
        self._ttl = ttl
        self._cache = TTLCache(clock)

    def mark(self, key: Hashable) -> None:
        """Remembers that the operation identified by 'key' returned no tables."""
        self._cache.set(key, True)

    def is_known_empty(self, key: Hashable) -> bool:
        """True if 'key' was marked as empty and the entry has not expired."""
        return self._cache.get(key, self._ttl) is not None
