import json
from typing import Any

import pandas as pd
from tabulate import tabulate


def flatten_multiline(val: str) -> str:
    """Collapse a multi-line string into a single line.

    For valid JSON, parse and re-dump compactly. For other strings, replace
    newlines with the literal ``\\n`` escape sequence.
    """
    if "\n" not in val and "\r" not in val:
        return val
    try:
        parsed = json.loads(val)
        return json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
    except (json.JSONDecodeError, ValueError):
        return val.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n")


def format_df(
    df: pd.DataFrame,
    *,
    max_visible_rows: int = 20,
    max_cell_width: int = 200,
    tablefmt: str = "github",
    floatfmt: str = ".8g",
    add_bottom_ellipsis_row: bool = False,
) -> str:
    def truncate_cell(val: object) -> object:
        if pd.isna(val):
            return "[NULL]"  # Convert all nulls to string (pandas coerces None back to nan/NaT)
        if isinstance(val, str):
            # Collapse multi-line values into a single line to preserve table layout
            val = flatten_multiline(val)
            if len(val) > max_cell_width:
                half = max_cell_width // 2
                return val[:half] + "..." + val[-half:]
        return val

    # Apply truncation first to preserve numeric types (nulls stay as None for tabulate)
    display_df = df.map(truncate_cell)

    n = len(display_df)
    if n > max_visible_rows:
        first_n = (max_visible_rows + 1) // 2
        last_n = max_visible_rows - first_n
        head_df = display_df.head(first_n)
        tail_df = display_df.tail(last_n)
        ellipsis_row = pd.DataFrame([["..."] * len(df.columns)], columns=df.columns)
        display_df = pd.concat([head_df, ellipsis_row, tail_df], ignore_index=True)

    if add_bottom_ellipsis_row:
        ellipsis_row = pd.DataFrame([["..."] * len(df.columns)], columns=df.columns)
        display_df = pd.concat([display_df, ellipsis_row], ignore_index=True)

    # showindex=False hides the automatic row numbers
    return tabulate(
        display_df, headers="keys", tablefmt=tablefmt, showindex=False, missingval="[NULL]", floatfmt=floatfmt
    )


def format_json_schema(
    schema: dict[str, Any],
    *,
    max_depth: int | None = 2,
    _depth: int = 0,
) -> str:
    """Format a JSON Schema dict as a compact TypeScript-style type annotation.

    Produces a human-readable one-liner such as
    ``{id: integer, name: string, tags: string[]}``.  Optional fields (not in
    ``required``, or nullable via ``anyOf`` with ``null``) are suffixed with
    ``?``.  Object nesting beyond *max_depth* is truncated to ``{...}``.

    Args:
        schema: A JSON Schema dictionary (as produced by ``infer_json_schema``).
        max_depth: Maximum nesting depth for objects.  Objects at or beyond this
            depth are shown as ``{...}``.  ``None`` disables the limit.
        _depth: Current nesting depth (internal recursion parameter).

    Returns:
        A compact type-annotation string.
    """
    # Handle anyOf (union types, including nullable)
    if "anyOf" in schema:
        subtypes: list[dict[str, Any]] = schema["anyOf"]
        non_null = [s for s in subtypes if s.get("type") != "null"]
        if not non_null:
            return "null"
        if len(non_null) == 1:
            return format_json_schema(non_null[0], max_depth=max_depth, _depth=_depth)
        parts = [format_json_schema(s, max_depth=max_depth, _depth=_depth) for s in non_null]
        return " | ".join(parts)

    t = schema.get("type")

    if t == "object":
        props: dict[str, Any] = schema.get("properties", {})
        if not props:
            return "object"
        if max_depth is not None and _depth >= max_depth:
            return "{...}"
        required = set(schema.get("required", []))
        field_parts: list[str] = []
        for key, val_schema in props.items():
            is_optional = key not in required
            # Also treat nullable values (anyOf containing null) as optional
            if not is_optional and isinstance(val_schema, dict) and "anyOf" in val_schema:
                is_optional = any(s.get("type") == "null" for s in val_schema["anyOf"])
            suffix = "?" if is_optional else ""
            formatted = format_json_schema(val_schema, max_depth=max_depth, _depth=_depth + 1)
            field_parts.append(f"{key}{suffix}: {formatted}")
        return "{" + ", ".join(field_parts) + "}"

    if t == "array":
        items_schema = schema.get("items")
        if items_schema:
            inner = format_json_schema(items_schema, max_depth=max_depth, _depth=_depth)
            # Wrap object-typed items as [{...}] for readability
            if inner.startswith("{"):
                return f"[{inner}]"
            return f"{inner}[]"
        return "array"

    if t in ("string", "integer", "number", "boolean", "null"):
        return t

    # Fallback for empty or unrecognized schemas
    return "any"
