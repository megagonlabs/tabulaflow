import json
from typing import Any


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


def _infer_schema(values: list[Any], *, max_depth: int, _depth: int) -> dict[str, Any]:
    """Recursively infer a JSON Schema from a list of sample values."""
    if _depth >= max_depth:
        return {}

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
            for k in sorted(obj_key_values.keys()):
                child_values = obj_key_values[k]
                properties[k] = _infer_schema(child_values, max_depth=max_depth, _depth=_depth + 1)
            s["properties"] = properties
            # A key is required only if it appeared in every object sample
            required = sorted(k for k, count in obj_key_counts.items() if count == num_objects)
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
