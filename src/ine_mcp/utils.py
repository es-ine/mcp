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

"""Lightweight utilities for the INE API.

No embeddings, no local models, and no scoring functions: the server only
compacts responses and applies a tolerant LITERAL FILTER (accent-insensitive,
tolerant to plurals and root variants). The decision of which operation / table /
variable / value to choose is made by the LLM by reading the names (and, for
operations, the descriptions).
"""

import html
import re
import unicodedata
from typing import Any

# Stop words that do not contribute when filtering.
_STOP = {
    "los", "las", "del", "por", "con", "una", "uno", "para", "que", "sus",
    "segun", "entre", "sobre", "como", "este", "esta", "cual", "cuales",
    "the", "and", "for", "with", "from", "that", "this",
}


def _normalize(text: str) -> str:
    """Lowercase and strip accents/diacritics."""
    if not text:
        return ""
    return unicodedata.normalize("NFD", text.lower()).encode("ascii", "ignore").decode()


def _words(text: str) -> list[str]:
    """Normalized words (letters and digits only)."""
    return re.findall(r"[a-z0-9]+", _normalize(text))


def _root(w: str) -> str:
    """
    Approximate root to match variants without a stemmer:
    poblacion / poblaciones / poblacional -> 'pobla'; viviendas -> 'vivie'; precios -> 'preci'.
    Short words (acronyms like IPC, EPA, PIB) are compared in full.
    """
    if len(w) >= 6:
        return w[:5]
    if len(w) > 3 and w.endswith("s"):
        return w[:-1]
    return w


def _roots(phrase: str) -> list[tuple[str, str]]:
    """(word, root) pairs of a search phrase, excluding stop words."""
    return [
        (w, _root(w))
        for w in _words(phrase)
        if (len(w) > 2 or w.isdigit()) and w not in _STOP
    ]


def _item_words(item: dict[str, Any]) -> list[str]:
    """Words of the item: name, codes/ids, and names of nested objects."""
    parts = [str(item.get(k) or "") for k in ("Nombre", "Codigo", "Cod_IOE", "Id")]
    for v in item.values():
        if isinstance(v, dict) and v.get("Nombre"):
            parts.append(str(v["Nombre"]))
    return _words(" ".join(parts))


def _desc_words(item: dict[str, Any]) -> list[str]:
    """Unique words of the item's description (decodes HTML entities such as &ordm;)."""
    desc = html.unescape(str(item.get("Descripcion") or ""))
    return sorted(set(_words(desc)))


def _matches(words: list[str], root: str) -> bool:
    """True if any word of the item starts with the root."""
    return any(w.startswith(root) for w in words)


def compact(item: dict[str, Any]) -> dict[str, Any]:
    """Removes empty fields and flattens nested objects (Periodicidad, Publicacion...) to their name."""
    out: dict[str, Any] = {}
    for k, v in item.items():
        if v in (None, "", [], {}):
            continue
        if isinstance(v, dict):
            if v.get("Nombre"):
                out[k] = v["Nombre"]
            continue
        out[k] = v
    return out


def filter_items(
    items: list[dict[str, Any]],
    query: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """
    Literal filter for ONE query (does NOT score or reorder; keeps API order).

    1. No query -> returns everything (up to 'limit').
    2. With query -> items containing ALL words (or variants of their root).
    3. If none -> items containing ANY word.
    4. If still none -> returns everything, so the LLM can decide by reading the list.
    """
    total = len(items)
    selected, mode = items, "no_filter"
    roots = [r for _, r in _roots(query)] if query else []

    if roots:
        texts = [(it, _item_words(it)) for it in items]
        all_match = [it for it, ws in texts if all(_matches(ws, r) for r in roots)]
        if all_match:
            selected, mode = all_match, "all_words"
        else:
            any_match = [it for it, ws in texts if any(_matches(ws, r) for r in roots)]
            if any_match:
                selected, mode = any_match, "any_word"
            else:
                mode = "no_matches_returning_all"

    return {
        "total_catalog": total,
        "matches": len(selected),
        "filter_mode": mode,
        "truncated": len(selected) > limit,
        "items": [compact(i) for i in selected[:limit]],
    }


def search_multiple(
    items: list[dict[str, Any]],
    phrases: list[str],
    limit: int = 100,
    use_description: bool = False,
) -> dict[str, Any]:
    """
    Search with a rich list of terms (synonyms, acronyms, official names...).

    - Each phrase matches if ALL its words appear (tolerating plurals and variants).
    - With use_description=True, a phrase also matches when its words are spread
      across the item's name AND its description.
    - The result is the UNION of all phrases, without duplicates, in a single list.
    - Ordering: items with the most matched phrases first, counting name and
      description matches equally. Ties keep the API order. There is no scoring.
    - If no phrase matches completely, it tries with any single word.
    - If still none, the complete catalog is returned for the LLM to decide.
    - Each item reports 'matched_terms' (all matched phrases) and, when
      use_description=True, also 'matched_in_name' (matched in the name) and
      'matched_only_in_description' (matched only thanks to the description).
    """
    total = len(items)
    parsed = [(f, _roots(f)) for f in phrases]
    parsed = [(f, rs) for f, rs in parsed if rs]
    name_ws = [_item_words(it) for it in items]
    desc_ws = [_desc_words(it) if use_description else [] for it in items]

    found: list[tuple[dict[str, Any], list[str], list[str]]] = []
    for it, nw, dw in zip(items, name_ws, desc_ws):
        hits_name: list[str] = []
        hits_desc: list[str] = []
        for f, rs in parsed:
            if all(_matches(nw, r) for _, r in rs):
                hits_name.append(f)
            elif dw and all(_matches(nw, r) or _matches(dw, r) for _, r in rs):
                hits_desc.append(f)
        if hits_name or hits_desc:
            found.append((it, hits_name, hits_desc))
    mode = "union_of_phrases" + ("+description" if use_description else "")

    if not found:
        mode = "any_word" + ("+description" if use_description else "")
        for it, nw, dw in zip(items, name_ws, desc_ws):
            hits_name = sorted({p for _, rs in parsed for p, r in rs if _matches(nw, r)})
            hits_desc = sorted(
                {p for _, rs in parsed for p, r in rs if dw and _matches(dw, r)}
                - set(hits_name)
            )
            if hits_name or hits_desc:
                found.append((it, hits_name, hits_desc))

    if not found:
        return {
            "total_catalog": total,
            "matches": total,
            "filter_mode": "no_matches_returning_all",
            "truncated": total > limit,
            "items": [compact(i) for i in items[:limit]],
        }

    # Stable sort: name and description matches weigh the same; ties keep the API order.
    found.sort(key=lambda x: -(len(x[1]) + len(x[2])))

    out = []
    for it, hits_name, hits_desc in found[:limit]:
        entry = {**compact(it), "matched_terms": hits_name + hits_desc}
        if use_description:
            entry["matched_in_name"] = hits_name
            entry["matched_only_in_description"] = hits_desc
        out.append(entry)

    return {
        "total_catalog": total,
        "matches": len(found),
        "filter_mode": mode,
        "truncated": len(found) > limit,
        "items": out,
    }


def search(
    items: list[dict[str, Any]],
    queries: list[str] | None,
    limit: int = 50,
    use_description: bool = False,
) -> dict[str, Any]:
    """Without queries returns everything (up to 'limit'); with queries uses the union of terms."""
    if not queries:
        return filter_items(items, None, limit)
    return search_multiple(items, queries, limit, use_description=use_description)