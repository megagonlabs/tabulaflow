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
    max_depth: int | None = None,
    max_fields: int | None = 20,
    _depth: int = 0,
    _budget: float | None = None,
) -> str:
    """Format a JSON Schema dict as a compact TypeScript-style type annotation.

    Produces a human-readable one-liner such as
    ``{id: integer, name: string, tags: string[]}``.  Follows TypeScript
    conventions: optional fields (not in ``required``) are suffixed with
    ``?``, and nullable fields use ``| null``.  Object nesting is controlled by two independent mechanisms:

    * *max_depth* - hard ceiling on nesting depth.
    * *max_fields* - adaptive budget that distributes across sibling
      properties so that narrow schemas expand deeper and wide schemas
      truncate earlier, keeping total output size roughly constant.

    Truncation occurs when *either* limit is reached.

    Args:
        schema: A JSON Schema dictionary (as produced by ``infer_json_schema``).
        max_depth: Maximum nesting depth for objects.  Objects at or beyond this
            depth are shown as ``{...}``.  ``None`` disables the limit.
        max_fields: Adaptive field budget.  At each object node the budget is
            divided equally among its properties; when a child's share drops
            below 1 the sub-tree is truncated to ``{...}``.  ``None`` disables
            the adaptive limit.
        _depth: Current nesting depth (internal recursion parameter).
        _budget: Remaining field budget (internal recursion parameter).

    Returns:
        A compact type-annotation string.
    """
    if _budget is None and max_fields is not None:
        _budget = float(max_fields)

    kw = dict(max_depth=max_depth, max_fields=max_fields)

    # Handle anyOf (union types, including nullable)
    if "anyOf" in schema:
        subtypes: list[dict[str, Any]] = schema["anyOf"]
        non_null = [s for s in subtypes if s.get("type") != "null"]
        has_null = len(non_null) < len(subtypes)
        if not non_null:
            return "null"
        if len(non_null) == 1:
            inner = format_json_schema(non_null[0], **kw, _depth=_depth, _budget=_budget)
        else:
            parts = [format_json_schema(s, **kw, _depth=_depth, _budget=_budget) for s in non_null]
            inner = " | ".join(parts)
        return f"{inner} | null" if has_null else inner

    t = schema.get("type")

    if t == "object":
        props: dict[str, Any] = schema.get("properties", {})
        if not props:
            return "object"
        if max_depth is not None and _depth >= max_depth:
            return "{...}"
        if _budget is not None and _budget < 1:
            return "{...}"
        child_budget = (_budget - 1) / len(props) if _budget is not None else None
        required = set[Any](schema.get("required", []))
        field_parts: list[str] = []
        for key, val_schema in props.items():
            suffix = "?" if key not in required else ""
            formatted = format_json_schema(val_schema, **kw, _depth=_depth + 1, _budget=child_budget)
            field_parts.append(f"{key}{suffix}: {formatted}")
        return "{" + ", ".join(field_parts) + "}"

    if t == "array":
        items_schema = schema.get("items")
        if items_schema:
            inner = format_json_schema(items_schema, **kw, _depth=_depth, _budget=_budget)
            # Wrap object-typed items as [{...}] for readability
            if inner.startswith("{"):
                return f"[{inner}]"
            return f"{inner}[]"
        return "array"

    if t in ("string", "integer", "number", "boolean", "null"):
        return t

    # Fallback for empty or unrecognized schemas
    return "any"
