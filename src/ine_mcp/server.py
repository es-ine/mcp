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

"""MCP Server for the Spanish National Statistics Institute (INE) JSON API.

Entry point of the package. The server logic is split into modules:
- config.py: environment configuration and instruction text.
- client.py / cache.py: HTTP client for the INE API and TTL cache.
- utils.py: tolerant literal filtering of API responses.
- models.py: Pydantic input models of the tools.
- state.py: flow state, session store and validation of the 5-step flow.
- tools.py: the MCP server instance and the five tools.

Available tools (mandatory flow order):
1. ine_select_operation: List or search available statistical operations
   (matches against operation names AND descriptions).
2. ine_select_multiple_tables: Search statistical tables in parallel for multiple operations.
3. ine_select_multiple_table_groups: Get variables/groups for one or multiple tables.
4. ine_select_multiple_values: Get values for multiple groups in parallel.
5. ine_select_multiple_table_data: Extract data observations applying 'tv' filters (FK_Variable:Id).

This server ENFORCES instructions via code (not just stating them):
- Flow order: Each step is blocked if preceding steps have not been completed.
- 'tv' Filters: Format and existence verified against values actually queried in session.
- Period: Default applies latest available data automatically (nult=1) if omitted.
- Source: Every returned result includes the 'source' object (operation, table with public URL, applied filters).
- Missing data: Errors/empty responses include procedure to follow ('next_step').

Strict mode is ALWAYS active and cannot be disabled.
"""

from .config import HTTP_HOST, HTTP_PORT_RAW, MCP_TRANSPORT
from .tools import mcp  # Importing the tools module registers the five tools on 'mcp'.

__all__ = ["mcp", "main"]

# Accepted values of MCP_TRANSPORT -> transport name expected by the MCP SDK.
_TRANSPORTS = {"stdio": "stdio", "http": "streamable-http", "streamable-http": "streamable-http"}


def main() -> None:
    """Starts the MCP server with the transport set in MCP_TRANSPORT."""
    transport = _TRANSPORTS.get(MCP_TRANSPORT.strip().lower())
    if transport is None:
        raise SystemExit(f"MCP_TRANSPORT='{MCP_TRANSPORT}' is not valid: use 'stdio' or 'http'.")
    if transport == "stdio":
        mcp.run(transport="stdio")
        return
    try:
        port = int(HTTP_PORT_RAW)
    except ValueError:
        raise SystemExit(f"MCP_PORT='{HTTP_PORT_RAW}' is not valid: use a port number.") from None
    mcp.run(transport="streamable-http", host=HTTP_HOST, port=port)


if __name__ == "__main__":
    main()
