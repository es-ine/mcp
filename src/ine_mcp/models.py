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

"""Input models (Pydantic v2) for the INE MCP tools.

Strict constraints (max lengths, patterns, forbidden extra fields) keep the
inputs safe against malformed data and ReDoS.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SelectOperationInput(BaseModel):
    """Parameters for listing INE statistical operations."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    queries: Optional[list[str]] = Field(
        default=None,
        description=(
            "RICH list of search terms derived from the user's query (up to 15). "
            "Includes: full words (NEVER truncated fragments), synonyms, official acronyms "
            "(IPC, EPA, PIB...), official operation names, descriptive terms about the content "
            "(e.g. 'hogares tamaño', 'número de miembros', 'por provincia') and 2-3 word combinations. "
            "Terms are matched against the operation NAME and also its DESCRIPTION. "
            "ALWAYS include each keyword separately in addition to the combinations. "
            "E.g., for 'how many people live in Murcia': ['population', 'register', 'census', 'inhabitants', 'demography', "
            "'population figures', 'population estimates', 'municipal register']. "
            "Each term matches if ALL its words are in the operation (plurals, accents, and variants are tolerated); "
            "the result is the union of all of them. If omitted, the complete catalog is returned."
        ),
        max_length=15,
    )


class OperationTableFilter(BaseModel):
    """Filter for searching tables in a specific operation."""

    operation_id: str = Field(
        ...,
        description="Operation ID (e.g. '25' or 'IPC').",
        min_length=1,
        max_length=50,
    )
    queries: Optional[list[str]] = Field(
        default=None,
        description=(
            "OPTIONAL. Rich list of terms to locate tables by name/code/periodicity: "
            "full words (never truncated), synonyms and combinations, PLUS each individual keyword "
            "(e.g., ['unemployment', 'unemployment rate', 'joblessness', 'province', 'sex']). Each term matches if "
            "ALL its words are in the table (plurals, accents, and variants are tolerated); the result is "
            "the union, with match info in each table. If omitted, the tables of the operation are returned."
        ),
        max_length=15,
    )


class SelectTableInput(BaseModel):
    """Parameters for searching candidate statistical tables across operations."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    operations: list[OperationTableFilter] = Field(
        ...,
        description=(
            "List of statistical operations and queries to search tables in parallel. "
            "CRITICAL WARNING: Mandatory list where you MUST GROUP ALL candidate operations "
            "(e.g. IDs 22, 21, 72, 450) into a SINGLE simultaneous call. "
            "CONSECUTIVE OR SEPARATE CALLS ARE PROHIBITED."
        ),
        min_length=1,
        max_length=10,
    )

    top_n: int = Field(
        default=100,
        description=(
            "Maximum number of tables to return per operation (between 1 and 500). "
            "If response indicates 'truncated': true, repeat with a more specific query or larger top_n."
        ),
        ge=1,
        le=500,
    )

    geo: Optional[int] = Field(
        default=None,
        description=(
            "Geographical filter: 1 = Regions/provinces, 0 = national, None = all. "
            "DO NOT USE unless strictly necessary: INE catalog geographical tagging "
            "can be unreliable and exclude valid tables."
        ),
        ge=0,
        le=1,
    )

    det: Optional[int] = Field(
        default=0,
        description="Detail level: 2 = maximum, 1 = medium, 0 = basic, None = unfiltered.",
        ge=0,
        le=2,
    )


class TableGroupFilterItem(BaseModel):
    """Parameters for selecting table variables/groups to filter by."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    table_id: str = Field(..., description="Table code (e.g. '50913').")
    query_filter: Optional[str] = Field(
        default=None,
        description=(
            "OPTIONAL. Literal text filter on variable names (e.g., 'region'). "
            "Normally omitted: tables have few variables and all are returned."
        ),
    )

    top_n: Optional[int] = Field(
        default=50,
        description="Maximum number of variables to return.",
        ge=1,
        le=50,
    )


class SelectMultipleTableGroupsInput(BaseModel):
    """Parameters for retrieving variables/groups across multiple tables concurrently."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    requests: list[TableGroupFilterItem] = Field(
        ...,
        description="List of table and variable filtering requests to resolve in parallel.",
        min_length=1,
    )


class TableValueFilterItem(BaseModel):
    """Parameters for retrieving values inside a specific group/variable of a table."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    table_id: str = Field(..., description="Table code (e.g. '59583').")
    group_id: str = Field(..., description="Group or variable ID of the table (e.g. '70').")
    queries: Optional[list[str]] = Field(
        default=None,
        description=(
            "OPTIONAL. Search terms to locate values by name (e.g., ['murcia', 'madrid'] or "
            "['total', 'both sexes']). Matches if ALL words are present. Omit for all values."
        ),
        max_length=15,
    )
    top_n: Optional[int] = Field(
        default=50,
        description="Maximum number of values to return per group (1-300).",
        ge=1,
        le=300,
    )


class SelectMultipleValuesInput(BaseModel):
    """Parameters for retrieving group values across MULTIPLE tables concurrently."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    requests: list[TableValueFilterItem] = Field(
        ...,
        description="List of combined table, group, and value requests to resolve in parallel.",
        min_length=1,
        max_length=20,
    )
    det: Optional[int] = Field(
        default=0,
        description="INE API detail level (default 0).",
        ge=0,
        le=2,
    )


class TableDataFilterItem(BaseModel):
    """Parameters for extracting observations from a specific table using filters."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    table_id: str = Field(
        ...,
        description="Table identification code (e.g. '76150').",
        min_length=1,
        max_length=100,
    )
    tv: list[str] = Field(
        ...,
        description=(
            "List of filters in 'FK_Variable:Id' format (e.g. ['70:9009', '70:9005', '3:74']). "
            "Include all necessary filters derived from the query."
        )
    )
    nult: Optional[int] = Field(
        default=None,
        description="Number of latest periods to retrieve (e.g. 17).",
        ge=1,
        le=100,
    )
    date: Optional[str] = Field(
        default=None,
        description="Specific date range in 'YYYYMMDD:YYYYMMDD' format.",
        max_length=50,
        pattern=r"^\d{8}(:(\d{8})?)?(,\d{8}(:(\d{8})?)?)*$",
    )


class SelectMultipleTableDataInput(BaseModel):
    """Parameters for extracting data from MULTIPLE tables concurrently with filters."""

    model_config = ConfigDict(str_strip_whitespace=True, validate_assignment=True, extra="forbid")

    requests: list[TableDataFilterItem] = Field(
        ...,
        description="List of combined table and 'tv' filter requests to resolve in parallel.",
        min_length=1,
        max_length=20,
    )
    det: Optional[int] = Field(
        default=2,
        description="Global detail level (0, 1, 2; default 2).",
        ge=0,
        le=2,
    )
    tip: Optional[str] = Field(
        default="A",
        description="Global result type: 'A' (friendly), 'M' (metadata), 'AM' (both).",
        pattern=r"^(A|M|AM)$",
    )
