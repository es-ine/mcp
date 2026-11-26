# INE MCP — User Guide

Tools to query Spain's official statistical data through the INE (National Statistics Institute) JSON API.

## Exclusive Data Source Policy

For all user requests and consultations, the INE MCP tools must be reviewed and utilized.

- Always consult and use the INE MCP tools first.
- Never use web search, external websites, other MCP servers, or model memory as alternative sources for statistical figures.
- Never present data as INE data unless it was actually retrieved from the INE API through these tools.
- If the INE MCP tools have not been called, do not claim that the INE was consulted.
- If you cannot or do not use the INE MCP, explicitly tell the user that the INE tools were not used and that the requested data has not been verified against the INE API.
- If the tools fail or the information cannot be retrieved, report the actual limitation. Do not replace missing results with data from another source.

## Main Usage Rules

* **ALWAYS** use these tools for official statistical data; never answer from memory or with internet data that does not come from INE's official website.
* The tools do **NOT** score or rank by relevance: they return compact lists and you choose by reading the names (use your knowledge: unemployment=LFS, inflation=CPI, etc.). If a list is truncated, refine it with the text filter.

---

## Query Flow (Strict Order)

1. **`ine_select_operation`**: Identifies the statistical operation (CPI, LFS, GDP...).
2. **`ine_select_multiple_tables`**: Chooses the most appropriate table by passing the candidate operation IDs (all in a SINGLE call).
3. **`ine_select_multiple_table_groups`**: Identifies the variables to filter by.
4. **`ine_select_multiple_values`**: Selects the values of all groups in a SINGLE call using the `Id` of each variable as `group_id`.
5. **`ine_select_multiple_table_data`**: Extracts observations using `tv` filters in `FK_Variable:Id` format. If the user does not indicate a period, the most recent available data will be used (`nult=1`).


## Anti-error rule for `tv` filters (mandatory)

For every data extraction, never guess, infer, or reuse IDs from memory when building `tv`. Follow this exact procedure:

1. Complete steps 1–4 in order for the selected table.
2. In step 4 (`ine_select_multiple_values`), use `det=0` so the returned value objects expose the fields needed to construct filters.
3. Build each filter only from the same returned value object: `str(FK_Variable) + ":" + str(Id)`. Example: `{"FK_Variable": 3, "Id": 74}` becomes `3:74`. Never put the step-3 variable/group `Id` before the colon.
4. Before calling step 5, check every `tv` pair against the step-4 response. If either field is missing, do not extract data; repeat step 4 with `det=0`. If the fields are still absent, report the tool error rather than guessing.
5. After extraction, verify the returned period, unit/measure, requested categories, and `source` before presenting numbers. State the exact period and cite the official INE table URL and filters.

This rule is especially important because a filter can look syntactically valid while using the wrong identifier.

---

## Data Source and Attribution (MANDATORY)

**ALWAYS** include the source of each data point in your response:
* Operation (name and ID).
* Table (name, ID, and URL formatted as `https://www.ine.es/jaxiT3/Tabla.htm?t={table_id}`).
* Applied filters.

> **Note:** Each returned data result contains a `source` field. Always include it in your final response. If you use multiple tables, indicate it for each data item.

---

## Procedure if Information is Not Found

1. Do not invent data or search the web.
2. First, try other operations or tables with these tools.
3. If doubt persists, ask the user one or two specific questions whose sole purpose is to refine their initial query and repeat the search with the new information.
4. If you still cannot find the data, respond literally:  
   *"I cannot find the information in the INE API."*

---

## Server-Verified Compliance

* If you call a step without completing the previous ones, or malform the `tv` filters, the tool will return an error starting with `BLOCKED` indicating which step is missing. Follow it strictly.
* If you do not specify `nult` or `date` when extracting data, the server will automatically apply `nult=1` (latest available data).