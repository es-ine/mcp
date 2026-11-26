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

"""MCP tools of the INE server (the 5-step workflow).

Defines the MCP server instance, the instructions resource and the five tools:
1. ine_select_operation
2. ine_select_multiple_tables
3. ine_select_multiple_table_groups
4. ine_select_multiple_values
5. ine_select_multiple_table_data

The order of the steps is enforced through FlowState (see state.py).
"""

import asyncio
import json
from typing import Optional

# Fully compatible with mcp[cli] >= 2.1.1 using MCPServer interface
from mcp.server.mcpserver import Context, MCPServer

from .client import handle_api_error, ine_get, ine_get_all_pages
from .config import CATALOG_TTL, instruction_text
from .models import (
    OperationTableFilter,
    SelectMultipleTableDataInput,
    SelectMultipleTableGroupsInput,
    SelectMultipleValuesInput,
    SelectOperationInput,
    SelectTableInput,
    TableDataFilterItem,
    TableGroupFilterItem,
    TableValueFilterItem,
)
from .state import EmptyOperationsRegistry, OperationsCatalog, SessionStore
from .utils import filter_items, search, search_multiple

# ---------------------------------------------------------------------------
# Server instance and shared state
# ---------------------------------------------------------------------------

mcp = MCPServer(
    "ine_mcp",
    instructions=instruction_text,
)

# Operations catalog: public data, identical for every client, so it is shared.
OPERATIONS = OperationsCatalog()
# Flow state per MCP session (what each client has already queried).
SESSIONS = SessionStore()
# Operations that recently returned no tables (avoids pointless retries).
EMPTY_OPERATIONS = EmptyOperationsRegistry()


@mcp.resource("ine://instructions")
def get_instructions() -> str:
    """Return the instruction manual for the INE MCP server."""
    return instruction_text


async def _load_operations_catalog() -> list:
    """Fetches (with cache) the operations catalog and registers its items."""
    catalog = await ine_get_all_pages("OPERACIONES_DISPONIBLES", ttl=CATALOG_TTL)
    OPERATIONS.register(catalog)
    return catalog


# ---------------------------------------------------------------------------
# Tool 1: Statistical Operations (OPERACIONES_DISPONIBLES)
# ---------------------------------------------------------------------------


@mcp.tool(
    name="ine_select_operation",
    annotations={
        "title": "List INE statistical operations",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ine_select_operation(params: SelectOperationInput) -> str:
    """
    Use this tool FIRST whenever the user asks for any figure or statistic about Spain:
    population, households, unemployment, employment, prices and inflation (CPI/IPC), GDP,
    wages, housing, tourism, births, deaths, companies... for the whole country, a region
    (comunidad autónoma), a province or a municipality, even if the user does not mention INE.
    It is the entry point to Spain's official statistics (INE, Instituto Nacional de Estadística).
    Never answer such questions from memory or from a web search: call this tool.

    STEP 1 of the flow.

    WHEN TO USE IT:
    This is the mandatory STEP 1 of the workflow for any official INE statistical query.
    It identifies the statistical operation before table selection or data extraction.

    INPUT PARAMETERS (What it receives):
    - params.queries (optional, list[str], max. 15 terms): Rich list of search terms derived from
      the user's query. Includes: full words (never truncated fragments), synonyms, official
      acronyms (IPC, EPA, PIB...), official operation names, descriptive terms about the content
      and 2-3 word combinations. Terms are matched against the operation NAME and also its
      DESCRIPTION. Always include each keyword separately in addition to the combinations.
      If omitted, the tool returns the complete catalog of available operations.

    WHAT IT RETURNS:
    A JSON string containing the following main fields:
    - usage_rules: The server's usage guide (same text as the 'ine://instructions' resource).
      Read it and follow it for the rest of the flow.
    - total_operations: Total number of INE catalog operations analyzed or matching.
    - queries: List of search terms used (if provided).
    - matches / filter_mode / truncated: Informative metadata about the text matching process.
    - operations: List of matching operation objects. Each element includes 'Id', 'Codigo',
      'Nombre', 'Descripcion' and the match details. If no queries, returns the full catalog.
    - Each operation also includes 'matched_terms' (all terms that matched),
      'matched_in_name' (terms found in the operation name) and 'matched_only_in_description'
      (terms found only thanks to the description). Name and description matches weigh the same.
      READ 'Descripcion' to decide which operation actually contains the requested breakdown
      (e.g. households by size by province) before moving to Step 2.
    - next_step: Guide or textual instruction with the mandatory next step (Step 2: ine_select_multiple_tables).

    SPECIAL RULE FOR POPULATION AND HOUSEHOLDS:
    - When the user's query is related to population or households data, search by default
      in the **Continuous Population Survey (ECP)** (note: housing is excluded from this default rule).
    - However, if there are doubts or ambiguities about which source best fits the request, present
      the most recent available alternatives to the user (such as the Municipal Register or Censuses) and let them decide
      what suits them best.

    OPERATING NOTES AND RESTRICTIONS:
    - The tools do not score or rank natively by complex relevance: read the returned names and
      descriptions and choose the relevant operations yourself (e.g., unemployment=LFS/EPA,
      inflation=CPI/IPC, population=ECP, etc.).
    - The server enforces a strict order: the operation IDs and codes you use in subsequent
      steps (Step 2) must obligatorily come from this catalog."""

    try:
        all_operations = await _load_operations_catalog()

        if not all_operations:
            return json.dumps({
                "error": "Could not retrieve INE statistical operations.",
                "next_step": 'Do not invent data or search the web. First, try other operations or tables using these tools. If doubt persists, ask the user one or two specific questions whose sole purpose is to refine their initial query, then repeat the search with the new information. If you still cannot find the data, respond literally: I cannot find the information in the INE API.',
            }, ensure_ascii=False)

        OPERATIONS.register(all_operations)

        if not params.queries:
            res = filter_items(all_operations, None, limit=500)
            return json.dumps(
                {
                    "usage_rules": instruction_text,
                    "total_operations": res["total_catalog"],
                    "operations": res["items"],
                    "next_step": 'Step 2: Call ine_select_multiple_tables with candidate operation IDs (all in a SINGLE call) and choose the most suitable table by reading their names.',
                },
                ensure_ascii=False,
                indent=2,
            )

        # use_description=True: terms are also matched against the operation description.
        res = search_multiple(all_operations, params.queries, limit=100, use_description=True)
        return json.dumps(
            {
                "usage_rules": instruction_text,
                "total_operations": res["total_catalog"],
                "queries": params.queries,
                "matches": res["matches"],
                "filter_mode": res["filter_mode"],
                "truncated": res["truncated"],
                "operations": res["items"],
                "next_step": 'Step 2: Call ine_select_multiple_tables with candidate operation IDs (all in a SINGLE call) and choose the most suitable table by reading their names.',
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        return handle_api_error(e)


# ---------------------------------------------------------------------------
# Tool 2: Select multiple tables per Operation in parallel
# ---------------------------------------------------------------------------

@mcp.tool(
    name="ine_select_multiple_tables",
    annotations={
        "title": "Select multiple tables across INE operations in parallel",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ine_select_multiple_tables(params: SelectTableInput, ctx: Optional[Context] = None) -> str:
    """
    STEP 2 of the flow.

    WHEN TO USE IT:
    This is the mandatory STEP 2 of the workflow. It is used after identifying candidate operations in
    Step 1 (ine_select_operation) to retrieve available tables within each operation and select the
    most suitable ones based on query requirements (geographical breakdown, thematic scope, etc.).

    INPUT PARAMETERS (What it receives):
    - params.operations (list[OperationTableFilter], required): List of requests per operation.
      CRITICAL WARNING: You MUST group ALL candidate operations found in Step 1 inside this list
      to execute them in a SINGLE parallel call. Consecutive or separate calls are strictly prohibited.
      Each item contains:
        * operation_id (str, required): ID or official code of the operation (e.g., '25' or 'IPC').
        * queries (optional, list[str]): Search terms (synonyms, combinations, and individual keywords)
          to filter tables by name/code/periodicity.
    - params.top_n (int, optional, default 100): Maximum number of tables to return per operation (1 to 500).
    - params.geo (int, optional, default None): Geographical filter (1 = Regions/provinces, 0 = national, None = all).
      Warning: Avoid using it unless strictly necessary, as INE tagging may exclude valid tables.
    - params.det (int, optional, default 0): Detail level of response (0 = basic, 1 = medium, 2 = maximum).

    WHAT IT RETURNS:
    A JSON string containing:
    - total_operations_queried: Number of operations processed simultaneously.
    - results_by_operation: List containing individual results for each queried operation:
        * operation_id: Identifier of the processed operation.
        * total_tables / matches / filter_mode / truncated: Filtering process metadata.
        * tables: List of matching table objects with their key fields ('Id', 'Nombre', etc.).
        * error: Explanatory message in case of blockage, failure, or absence of tables.
    - next_step: Guide or textual instruction with the mandatory next step
      (Step 3: ine_select_multiple_table_groups).

    OPERATING NOTES AND ADAPTIVE STRATEGY:
    - Strict requirement: Every 'operation_id' must come from 'ine_select_operation' (Step 1);
      otherwise, the call will be BLOCKED.
    - Simple queries: Select the most suitable table directly.
    - Complex or ambiguous queries: When the request crosses sources or contains tables with similar names,
      simultaneously open the top 2 or 3 candidate tables in this same call to examine and contrast their
      structural variables in Step 3.
    - If an operation returns no tables, do not retry iteratively; assume the catalog lacks them in this
      format and try other operations."""

    state = SESSIONS.get_state(ctx)
    blocked: list = []
    skipped: list = []
    unique_operations: list = []
    seen: set = set()

    for filter_item in params.operations:
        op = OPERATIONS.resolve(filter_item.operation_id)
        if op is None:
            try:
                await _load_operations_catalog()
            except Exception:
                pass
            op = OPERATIONS.resolve(filter_item.operation_id)
        if op is None:
            blocked.append({
                "operation_id": filter_item.operation_id,
                "error": (f"BLOCKED: Operation '{filter_item.operation_id}' does not originate from "
                          f"ine_select_operation catalog. Complete Step 1 first and use a returned ID/code."),
                "required_step": 1,
                "next_step": 'Step 1: Call ine_select_operation to identify the statistical operation (CPI, LFS, GDP...).',
            })
            continue
        op_id = op["id"]
        if op_id in seen:
            continue
        seen.add(op_id)
        if EMPTY_OPERATIONS.is_known_empty((op_id, params.geo, params.det)):
            skipped.append({
                "operation_id": op_id,
                "error": (f"Operation {op_id} returned no tables a moment ago and was not queried again. "
                          f"Do not retry it now; try other operations."),
            })
            continue
        unique_operations.append((op_id, filter_item))

    if not unique_operations:
        if blocked:
            return json.dumps(
                {"total_operations_queried": 0, "results_by_operation": skipped + blocked},
                ensure_ascii=False,
                indent=2,
            )
        return json.dumps({
            "error": "All provided operations returned no tables a moment ago. Do not retry them now.",
            "results_by_operation": skipped,
            "next_step": 'Do not invent data or search the web. First, try other operations or tables using these tools. If doubt persists, ask the user one or two specific questions whose sole purpose is to refine their initial query, then repeat the search with the new information. If you still cannot find the data, respond literally: I cannot find the information in the INE API.',
        }, ensure_ascii=False)

    query_params: dict = {}
    if params.geo is not None:
        query_params["geo"] = params.geo
    if params.det is not None:
        query_params["det"] = params.det

    async def _process_operation_table(op_id: str, filter_item: OperationTableFilter) -> dict:
        """Fetches and filters the tables of ONE operation; returns a result or an error dict."""
        try:
            all_tables = await ine_get_all_pages(
                f"TABLAS_OPERACION/{op_id}", query_params, ttl=CATALOG_TTL
            )

            if not all_tables:
                if params.geo is None:
                    EMPTY_OPERATIONS.mark((op_id, params.geo, params.det))
                    notice = f"No tables found for operation {op_id}. Operation discarded."
                else:
                    notice = (f"No tables found for operation {op_id} with geo={params.geo}, "
                              f"det={params.det}. Repeat query WITHOUT 'geo' before discarding.")
                return {
                    "operation_id": op_id,
                    "error": notice,
                    "next_step": 'Do not invent data or search the web. First, try other operations or tables using these tools. If doubt persists, ask the user one or two specific questions whose sole purpose is to refine their initial query, then repeat the search with the new information. If you still cannot find the data, respond literally: I cannot find the information in the INE API.',
                }

            state.register_tables(op_id, all_tables)
            res = search(all_tables, filter_item.queries, limit=params.top_n)

            return {
                "operation_id": op_id,
                "queries": filter_item.queries,
                "total_tables": res["total_catalog"],
                "matches": res["matches"],
                "filter_mode": res["filter_mode"],
                "truncated": res["truncated"],
                "tables": res["items"],
            }
        except Exception as e:
            return {
                "operation_id": op_id,
                "error": handle_api_error(e),
            }

    try:
        tasks = [_process_operation_table(op_id, filter_item) for op_id, filter_item in unique_operations]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        clean_results = []
        for res in results:
            if isinstance(res, Exception):
                clean_results.append({"error": handle_api_error(res)})
            else:
                clean_results.append(res)
        clean_results.extend(skipped)
        clean_results.extend(blocked)

        return json.dumps(
            {
                "total_operations_queried": len(unique_operations),
                "results_by_operation": clean_results,
                "next_step": 'Step 3: Call ine_select_multiple_table_groups with the selected table ID to identify variables/groups to filter by.',
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        return handle_api_error(e)


# ---------------------------------------------------------------------------
# Tool 3: Groups / Variables of a Table (GRUPOS_TABLA)
# ---------------------------------------------------------------------------


@mcp.tool(
    name="ine_select_multiple_table_groups",
    annotations={
        "title": "List or select groups/variables from an INE table",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ine_select_multiple_table_groups(
    params: SelectMultipleTableGroupsInput, ctx: Optional[Context] = None
) -> str:
    """
    STEP 3 of the flow.

    WHEN TO USE IT:
    This is the mandatory STEP 3 of the workflow. It is used to concurrently retrieve and filter the
    variables or groups from multiple tables, determining which structural variables will act as filters
    based on the user's request.

    INPUT PARAMETERS (What it receives):
    - params.requests (list[TableGroupFilterItem], required): List of combinations of tables and variable
      filtering queries to be resolved in parallel. Each item contains:
        * table_id (str, required): Code of the table (e.g., '50913'). Must originate from Step 2.
        * query_filter (str, optional): Literal text filter on the variable names (e.g., 'region').
          Normally omitted since tables have few variables and all are returned.
        * top_n (int, optional, default 50): Maximum number of variables to return (1 to 50).

    WHAT IT RETURNS:
    A JSON string containing:
    - total_requests: Total number of requests processed.
    - results_by_table: List containing individual results for each queried table:
        * table_id: Code of the processed table.
        * query_filter: The applied text filter query.
        * total_variables / truncated: Metadata of the variables catalog.
        * selected_variables: List of selected variable objects (each variable's 'Id' serves as the 'group_id' for Step 4).
        * error: Explanatory message in case of blockage (e.g., if Step 2 was skipped) or failure.
    - next_step: Guide or textual instruction with the mandatory next step
      (Step 4: ine_select_multiple_values).

    OPERATING NOTES AND RESTRICTIONS:
    - Strict requirement: Every 'table_id' must come from 'ine_select_multiple_tables' (Step 2);
      otherwise, that specific request is BLOCKED.
    - The 'Id' field of each returned variable is the 'group_id' required in Step 4."""

    state = SESSIONS.get_state(ctx)

    async def _process_group_item(item: TableGroupFilterItem) -> dict:
        """Retrieves the variables/groups of ONE table (Step 3); returns a result or a BLOCKED/error dict."""
        blockage = state.verify_flow(item.table_id, 3)
        if blockage:
            return blockage
        try:
            url_path = f"GRUPOS_TABLA/{item.table_id}"
            resp = await ine_get(url_path)

            if not resp or not isinstance(resp, list):
                return {
                    "table_id": item.table_id,
                    "error": f"Could not retrieve variables for table '{item.table_id}'.",
                    "next_step": 'Do not invent data or search the web. First, try other operations or tables using these tools. If doubt persists, ask the user one or two specific questions whose sole purpose is to refine their initial query, then repeat the search with the new information. If you still cannot find the data, respond literally: I cannot find the information in the INE API.',
                }

            state.register_groups(item.table_id, resp)
            res = filter_items(resp, item.query_filter, limit=item.top_n or 50)

            return {
                "table_id": item.table_id,
                "query_filter": item.query_filter,
                "total_variables": res["total_catalog"],
                "truncated": res["truncated"],
                "selected_variables": res["items"],
            }
        except Exception as e:
            return {
                "table_id": item.table_id,
                "error": handle_api_error(e),
            }

    try:
        tasks = [_process_group_item(item) for item in params.requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        clean_results = [
            res if not isinstance(res, Exception) else {"error": handle_api_error(res)}
            for res in results
        ]

        return json.dumps(
            {
                "total_requests": len(params.requests),
                "results_by_table": clean_results,
                "next_step": "Step 4: Call ine_select_multiple_values (SINGLE call, all groups) using the 'Id' of each variable as 'group_id'.",
            },
            ensure_ascii=False,
            indent=2,
        )
    except Exception as e:
        return handle_api_error(e)


# ---------------------------------------------------------------------------
# Tool 4: Extract values for multiple groups in parallel
# ---------------------------------------------------------------------------


@mcp.tool(
    name="ine_select_multiple_values",
    annotations={
        "title": "Select values for multiple variables simultaneously",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def ine_select_multiple_values(
    params: SelectMultipleValuesInput, ctx: Optional[Context] = None
) -> str:
    """
    STEP 4 of the flow.

    WHEN TO USE IT:
    This is the mandatory STEP 4 of the workflow. It is used to retrieve the values of multiple groups/variables
    across multiple tables in parallel (without scoring: you choose by reading the names).

    INPUT PARAMETERS (What it receives):
    - params.requests (list[TableValueFilterItem], required): List of combined requests for table, group,
      and value query to be resolved simultaneously in parallel (max 20 items). Each item contains:
        * table_id (str, required): Code of the table (e.g., '59583'). Must come from previous steps.
        * group_id (str, required): ID of the table group or variable (e.g., '70'). Must originate from Step 3.
        * queries (optional, list[str]): Terms to locate values by name (e.g., ['murcia', 'madrid'] or ['total', 'both sexes']).
          If the group has few values, omit it and choose yourself. Omit for all values.
        * top_n (int, optional, default 50): Maximum number of values to return per group (1 to 300).
    - params.det (int, optional): Accepted for compatibility, but the server ALWAYS requests det=0 here so value objects include the fields needed for safe tv construction (FK_Variable and Id).

    WHAT IT RETURNS:
    A JSON string containing:
    - total_requests_processed: Total number of requests processed.
    - results: List containing individual results for each queried table and group:
        * table_id / group_id / queries: Request context.
        * total_values / filter_mode / truncated: Catalog metadata.
        * selected_values: List of matching value objects. Each object contains 'Id' and 'FK_Variable'.
        * error: Explanatory message in case of blockage (e.g., if Step 3 was skipped) or failure.
    - next_step: Guide or textual instruction with the mandatory next step
      (Step 5: ine_select_multiple_table_data).

    OPERATING NOTES AND CRITICAL WARNINGS FOR 'tv' FILTERS:
    - Strict requirement: Every 'group_id' must come from 'ine_select_multiple_table_groups' (Step 3);
      otherwise, that request is BLOCKED.
    - Use 'ine_select_multiple_values' in a SINGLE CALL passing the list of requests.
    - CRITICAL WARNING WHEN BUILDING 'tv' FILTERS: Each value returned in 'selected_values' must contain
      the fields 'FK_Variable' and 'Id'. The server requests det=0 and refuses to return a usable selection if either field is absent.
    - The MANDATORY format for the 'tv' filter pair is 'FK_Variable:Id' (using the 'FK_Variable' returned
      inside the value object, NEVER the 'group_id'). Step 5 will reject malformed filters or those not originating from these values.
      Examples of correct 'tv' pairs (FK_Variable:Id):
        * If for Murcia you get {"Id": 31, "FK_Variable": 115} -> The 'tv' pair is '115:31' (NOT '87779:31').
        * If for Men you get {"Id": 452, "FK_Variable": 18} -> The 'tv' pair is '18:452'.
        * If you want all values of variable 18 unfiltered -> '18:'"""

    state = SESSIONS.get_state(ctx)

    async def _process_global_request(item: TableValueFilterItem):
        """Retrieves the values of ONE group of ONE table (Step 4); returns a result or a BLOCKED/error dict."""
        blockage = state.verify_flow(item.table_id, 4)
        if blockage:
            blockage["group_id"] = item.group_id
            return blockage
        if not state.has_group(item.table_id, item.group_id):
            return {
                "table_id": item.table_id,
                "group_id": item.group_id,
                "error": (f"BLOCKED: group_id '{item.group_id}' is not a variable of table "
                          f"'{item.table_id}'. Use 'Id' field of variables returned by "
                          f"ine_select_multiple_table_groups."),
                "required_step": 3,
                "next_step": 'Step 3: Call ine_select_multiple_table_groups with the selected table ID to identify variables/groups to filter by.',
            }

        query_params: list[tuple[str, str]] = [("det", "0")]
        url_path = f"VALORES_GRUPOSTABLA/{item.table_id}/{item.group_id}"
        try:
            resp = await ine_get(url_path, query_params)
        except Exception as e:
            return {
                "table_id": item.table_id,
                "group_id": item.group_id,
                "error": handle_api_error(e),
            }

        if not resp or not isinstance(resp, list):
            return {
                "table_id": item.table_id,
                "group_id": item.group_id,
                "error": f"Could not retrieve values for table '{item.table_id}' and group '{item.group_id}'.",
                "selected_values": [],
                "next_step": 'Do not invent data or search the web. First, try other operations or tables using these tools. If doubt persists, ask the user one or two specific questions whose sole purpose is to refine their initial query, then repeat the search with the new information. If you still cannot find the data, respond literally: I cannot find the information in the INE API.',
            }

        invalid = [
            val for val in resp
            if not isinstance(val, dict)
            or val.get("Id") is None
            or val.get("FK_Variable") is None
        ]
        if invalid:
            return {
                "table_id": item.table_id,
                "group_id": item.group_id,
                "error": (
                    "Cannot safely construct tv filters: the INE values response is missing "
                    "Id and/or FK_Variable even with det=0. Do not guess the identifiers; "
                    "check the INE response or report that the API did not provide the required fields."
                ),
                "selected_values": [],
            }

        state.register_values(item.table_id, resp)
        res = search(resp, item.queries, limit=item.top_n or 50)

        return {
            "table_id": item.table_id,
            "group_id": item.group_id,
            "queries": item.queries,
            "total_values": res["total_catalog"],
            "filter_mode": res["filter_mode"],
            "truncated": res["truncated"],
            "selected_values": res["items"],
        }

    try:
        tasks = [_process_global_request(item) for item in params.requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        clean_results = [
            res if not isinstance(res, Exception) else {"error": handle_api_error(res)}
            for res in results
        ]

        return json.dumps(
            {
                "total_requests_processed": len(params.requests),
                "results": clean_results,
                "next_step": "Step 5: Call ine_select_multiple_table_data with 'tv' filters in 'FK_Variable:Id' format taken from returned values. If user specifies no period, latest data (nult=1) will be used.",
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        return handle_api_error(e)


# ---------------------------------------------------------------------------
# Tool 5: Extract table data with filters (DATOS_TABLA)
# ---------------------------------------------------------------------------


@mcp.tool(
    name="ine_select_multiple_table_data",
    annotations={
        "title": "Select data from multiple INE tables in parallel with filters",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def ine_select_multiple_table_data(
    params: SelectMultipleTableDataInput, ctx: Optional[Context] = None
) -> str:
    """
    STEP 5 of the flow.

    WHEN TO USE IT:
    This is the mandatory STEP 5 of the workflow. It is used to concurrently extract quantitative
    observations from multiple tables by applying 'tv' filters.

    INPUT PARAMETERS (What it receives):
    - params.requests (list[TableDataFilterItem], required): List of combined requests for table and
      'tv' filters to be resolved simultaneously in parallel (max 20 items). Each item contains:
        * table_id (str, required): Identification code of the table (e.g., '76150'). Must come from previous steps.
        * tv (list[str], required): List of filters in 'FK_Variable:Id' format (e.g., ['70:9009', '18:452']).
          Include all necessary filters derived from the query, incorporating multiple values independently if required.
        * nult (int, optional): Number of latest periods to retrieve (e.g., 17). If both 'nult' and 'date' are indicated, 'nult' prevails.
        * date (str, optional): Specific date range or concrete period in 'YYYYMMDD:YYYYMMDD' format.
    - params.det (int, optional, default 2): Global detail level (0, 1, or 2).
    - params.tip (str, optional, default "A"): Global result type: 'A' (friendly), 'M' (metadata), 'AM' (both).

    WHAT IT RETURNS:
    A JSON string containing:
    - total_requests_processed: Total number of requests processed.
    - response_reminder: Mandatory reminder to include the data source in the final response.
    - results: List containing individual results for each queried table:
        * table_id / applied_filters / applied_period: Query context and applied parameters.
        * source: Source object containing operation info (name & ID), table info (name, ID, and public URL), applied filters, and period.
        * total_observations / results: Data payload returned by the INE API.
        * error: Explanatory message if blocked (e.g., if steps 2-4 were skipped or 'tv' validation failed) or failed.

    OPERATING NOTES AND CRITICAL RULES:
    - Strict requirement: Requires having completed steps 2, 3, and 4 for each table; otherwise, that request is BLOCKED.
    - CRITICAL RULE FOR 'tv': Always use the 'FK_Variable' returned inside the selected value object (NEVER the 'group_id'). Malformed filters or those not originating from consulted values are REJECTED.
    - Period default: If neither 'nult' nor 'date' is specified, the server automatically applies nult=1 (most recent data available).
    - MANDATORY SOURCE ATTRIBUTION: Each result includes a 'source' field. ALWAYS include it in your final response; if using multiple tables, indicate it for each piece of data."""

    state = SESSIONS.get_state(ctx)

    async def _process_data_request(item: TableDataFilterItem):
        """Validates and runs the data request of ONE table (Step 5); returns a result or a BLOCKED/error dict."""
        blockage = state.verify_flow(item.table_id, 5)
        if blockage:
            return blockage

        tv_error = state.validate_tv(item.table_id, item.tv)
        if tv_error:
            return {
                "table_id": item.table_id,
                "applied_filters": item.tv,
                "error": f"BLOCKED: {tv_error}",
                "required_step": 4,
                "next_step": "Step 4: Call ine_select_multiple_values (SINGLE call, all groups) using the 'Id' of each variable as 'group_id'.",
            }

        nult, date_str, notice = item.nult, item.date, None
        if nult is not None and date_str is not None:
            notice = "Both 'nult' and 'date' specified; applied 'nult' and ignored 'date'."
            date_str = None
        if nult is None and date_str is None:
            nult = 1
            period = "latest available data (nult=1 applied automatically: no period indicated)"
        elif nult is not None:
            period = f"latest {nult} period(s) (nult={nult})"
        else:
            period = f"date={date_str}"

        query_params: list[tuple[str, str]] = []

        for filter_item in item.tv:
            query_params.append(("tv", filter_item.strip()))

        if nult is not None:
            query_params.append(("nult", str(nult)))
        else:
            query_params.append(("date", date_str))

        if params.det is not None:
            query_params.append(("det", str(params.det)))

        if params.tip is not None:
            query_params.append(("tip", params.tip))

        url_path = f"DATOS_TABLA/{item.table_id}"
        try:
            resp = await ine_get(url_path, query_params)
        except Exception as e:
            return {
                "table_id": item.table_id,
                "error": handle_api_error(e),
            }

        if not resp:
            return {
                "table_id": item.table_id,
                "applied_filters": item.tv,
                "error": f"No data obtained for table '{item.table_id}' with specified filters.",
                "next_step": 'Do not invent data or search the web. First, try other operations or tables using these tools. If doubt persists, ask the user one or two specific questions whose sole purpose is to refine their initial query, then repeat the search with the new information. If you still cannot find the data, respond literally: I cannot find the information in the INE API.',
            }

        extracted_data = resp.get("Data") if isinstance(resp, dict) else resp

        result = {
            "table_id": item.table_id,
            "source": state.build_source(item.table_id, item.tv, period, OPERATIONS),
            "applied_filters": item.tv,
            "applied_period": period,
            "total_observations": len(extracted_data) if isinstance(extracted_data, list) else 1,
            "results": resp,
        }
        if notice:
            result["notice"] = notice
        return result

    try:
        tasks = [_process_data_request(item) for item in params.requests]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        clean_results = [
            res if not isinstance(res, Exception) else {"error": handle_api_error(res)}
            for res in results
        ]

        return json.dumps(
            {
                "total_requests_processed": len(params.requests),
                "response_reminder": 'ALWAYS include the source of each data item in your response: operation (name and ID), table (name, ID, and URL), and applied filters. If you use multiple tables, indicate it for each data item.',
                "results": clean_results,
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        return handle_api_error(e)
