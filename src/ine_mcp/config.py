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

"""Configuration and shared constants for the INE MCP server."""

import importlib.resources
import os
from pathlib import Path

# Transport: "stdio" or "http" (streamable-http). Can be overridden with the MCP_TRANSPORT env var.
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")
# HTTP bind address and port. Can be overridden with the MCP_HOST / MCP_PORT env vars.
HTTP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
HTTP_PORT_RAW = os.getenv("MCP_PORT", "8000")

# Public URL template of an INE table (used to build the 'source' object).
INE_TABLE_URL = "https://www.ine.es/jaxiT3/Tabla.htm?t={table_id}"

# Seconds the operations/tables catalogs are cached in memory.
CATALOG_TTL = 6 * 3600

# Seconds an operation that returned no tables is remembered (avoids retry loops).
EMPTY_OPERATION_TTL = 15 * 60

# Maximum number of MCP sessions kept in memory (least recently used are evicted).
MAX_SESSIONS = 1000
# HTTP header that carries the MCP session id over Streamable HTTP.
SESSION_ID_HEADER = "mcp-session-id"
# Session key used when the transport carries no session id (e.g. stdio).
DEFAULT_SESSION_KEY = "default"

_FALLBACK_INSTRUCTIONS = "Use official INE tools to query statistical data."


def load_instructions() -> str:
    """Loads the instruction manual shown to the MCP client.

    Tries, in order: the Markdown resource embedded in the installed package,
    the same file in the project root (local development), and finally a
    one-line fallback text.
    """
    try:
        return (
            importlib.resources.files("ine_mcp")
            .joinpath("Resources", "ine_mcp_instructions.md")
            .read_text(encoding="utf-8")
        )
    except Exception:
        # Local development: navigate up from src/ine_mcp/ to the root /Resources.
        try:
            project_root = Path(__file__).resolve().parents[2]
            path = project_root / "Resources" / "ine_mcp_instructions.md"
            return path.read_text(encoding="utf-8")
        except Exception:
            return _FALLBACK_INSTRUCTIONS


instruction_text = load_instructions()
