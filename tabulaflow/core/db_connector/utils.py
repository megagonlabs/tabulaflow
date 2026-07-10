import json
from typing import Any

from tabulaflow.core.db_connector.base import NL2QDBConnector


def connector_info(connector: NL2QDBConnector) -> str:
    """Return a concise human-readable connector summary.

    Args:
        connector: Database connector to summarize.

    Returns:
        A short summary suitable for connection confirmations and agent events.
    """
    if connector.connector_type == "property_graph":
        n_labels = len(connector.schema.nodes)
        n_relationships = len(connector.schema.relationships)
        language = connector.language or "graph"
        return (
            f"{connector.backend}, {language}, {n_labels} label{'s' if n_labels != 1 else ''}, "
            f"{n_relationships} relationship type{'s' if n_relationships != 1 else ''}"
        )

    schema = connector.schema
    n_tables = len(schema.tables)
    dialect = connector.language or schema.dialect or "unknown"
    return f"{dialect}, {n_tables} table{'s' if n_tables != 1 else ''}"


def infer_json_schema(values: list[Any], *, max_depth: int = 10) -> dict[str, Any] | None:
    """Infer a JSON Schema from a list of sample values.

    Handles nested objects, arrays, mixed types, and null values.
    Returns None if no non-null values are provided.

    Args:
        values: Sample values (dicts, lists, scalars, or None). String values
            that look like JSON will be parsed automatically.
        max_depth: Maximum nesting depth to prevent runaway recursion.

    Returns:
        A JSON Schema dict, or None if all values are null/empty.
    """
    parsed = [_parse_value(v) for v in values]
    non_null = [v for v in parsed if v is not None]
    if not non_null:
        return None
    return _infer_schema(parsed, max_depth=max_depth, _depth=0)


def looks_like_json(values: list[Any], *, threshold: float = 0.8) -> bool:
    """Check if a list of values looks like JSON objects or arrays.

    Returns True if at least ``threshold`` fraction of non-null string values
    parse as JSON objects or arrays (not scalars like ``"hello"`` or ``123``).

    Args:
        values: Sample values to check.
        threshold: Minimum fraction of values that must be JSON objects/arrays.
    """
    non_null_strings = [v for v in values if isinstance(v, str) and v.strip()]
    if not non_null_strings:
        return False
    json_count = 0
    for v in non_null_strings:
        try:
            parsed = json.loads(v)
            if isinstance(parsed, (dict, list)):
                json_count += 1
        except (json.JSONDecodeError, ValueError):
            pass
    return json_count / len(non_null_strings) >= threshold


def _parse_value(v: Any) -> Any:
    """Try to parse string values as JSON; return as-is otherwise."""
    if isinstance(v, str):
        try:
            return json.loads(v)
        except (json.JSONDecodeError, ValueError):
            return v
    return v


def _parse_nested_value(v: Any) -> Any:
    """Like :func:`_parse_value` but only unwraps JSON-encoded *containers*.

    At a nested level we cannot assume a string is JSON-encoded: a property
    value like ``"10001"`` (e.g. a ZIP code) is valid JSON for integer ``10001``,
    but the caller stored it as a string and the inference should respect that.
    Only unwrap when the parse result is a ``dict`` or ``list`` — i.e. the
    string clearly carries embedded JSON structure, as happens with DuckDB
    ``JSON[]`` columns whose items come back as JSON text.
    """
    if not isinstance(v, str):
        return v
    s = v.lstrip()
    if not s.startswith(("{", "[")):
        return v
    try:
        parsed = json.loads(v)
    except (json.JSONDecodeError, ValueError):
        return v
    if isinstance(parsed, (dict, list)):
        return parsed
    return v


def _infer_schema(values: list[Any], *, max_depth: int, _depth: int) -> dict[str, Any]:
    """Recursively infer a JSON Schema from a list of sample values."""
    if _depth >= max_depth:
        return {}

    # Unwrap JSON-encoded composites at every nested level. DuckDB ``JSON[]``
    # columns return arrays whose items are raw JSON text, and nested struct
    # fields can similarly carry JSON-encoded objects. Scalar-looking strings
    # are left alone — see :func:`_parse_nested_value`.
    values = [_parse_nested_value(v) for v in values]

    types: set[str] = set()
    # For objects: key -> list of values seen for that key
    obj_key_values: dict[str, list[Any]] = {}
    obj_key_counts: dict[str, int] = {}
    num_objects = 0
    # For arrays: all element values collected across samples
    arr_items: list[Any] = []

    for v in values:
        if v is None:
            types.add("null")
        elif isinstance(v, bool):
            # Must check bool before int (bool is a subclass of int in Python)
            types.add("boolean")
        elif isinstance(v, int):
            types.add("integer")
        elif isinstance(v, float):
            types.add("number")
        elif isinstance(v, str):
            types.add("string")
        elif isinstance(v, dict):
            types.add("object")
            num_objects += 1
            for k, child in v.items():
                obj_key_values.setdefault(k, []).append(child)
                obj_key_counts[k] = obj_key_counts.get(k, 0) + 1
        elif isinstance(v, list):
            types.add("array")
            arr_items.extend(v)

    # Build a schema for each observed type
    non_null_types = sorted(types - {"null"})
    has_null = "null" in types

    type_schemas: list[dict[str, Any]] = []
    for t in non_null_types:
        s: dict[str, Any] = {"type": t}

        if t == "object" and obj_key_values:
            properties: dict[str, Any] = {}
            for k in obj_key_values:
                properties[k] = _infer_schema(obj_key_values[k], max_depth=max_depth, _depth=_depth + 1)
            s["properties"] = properties
            # A key is required only if it appeared in every object sample
            # Preserve the insertion order (first-seen order from the data)
            required = [k for k in obj_key_values if obj_key_counts[k] == num_objects]
            if required:
                s["required"] = required

        if t == "array" and arr_items:
            s["items"] = _infer_schema(arr_items, max_depth=max_depth, _depth=_depth + 1)

        type_schemas.append(s)

    if has_null:
        type_schemas.append({"type": "null"})

    # Flatten: single type needs no anyOf wrapper
    if not type_schemas:
        return {"type": "null"}
    elif len(type_schemas) == 1:
        return type_schemas[0]
    else:
        return {"anyOf": type_schemas}
