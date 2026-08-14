import json
from typing import Any

import pandas as pd
from tabulate import tabulate

from tabulaflow.core import ExecResult, SQLColumnSchema


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


def format_ratio_as_percent(
    ratio: float,
    *,
    decimals: int = 0,
    min_nonzero_percent: float | None = 1.0,
) -> str:
    """Format a ratio in [0, 1] as a percentage string.

    Args:
        ratio: Ratio value where 0.0 means 0% and 1.0 means 100%.
        decimals: Number of decimal places for standard percentage formatting.
        min_nonzero_percent: If set, non-zero ratios below this threshold are
            shown as ``less than X%`` (e.g., ``less than 1%``) to avoid
            displaying misleading ``0%`` values due to rounding. Set to
            ``None`` to disable.

    Returns:
        A human-readable percentage string.
    """
    if ratio <= 0:
        return "0%"

    if min_nonzero_percent is not None and ratio * 100 < min_nonzero_percent:
        threshold = f"{min_nonzero_percent:g}%"
        return f"less than {threshold}"

    return f"{ratio:.{decimals}%}"


def format_df(
    df: pd.DataFrame,
    *,
    max_visible_rows: int = 20,
    max_cell_width: int = 200,
    tablefmt: str = "github",
    floatfmt: str = ".8g",
    add_bottom_ellipsis_row: bool = False,
) -> str:
    def _truncate_str(s: str) -> str:
        s = flatten_multiline(s)
        if len(s) > max_cell_width:
            half = max_cell_width // 2
            return s[:half] + "..." + s[-half:]
        return s

    def truncate_cell(val: object) -> object:
        try:
            if pd.isna(val):
                return "[NULL]"  # Convert all nulls to string (pandas coerces None back to nan/NaT)
        except (ValueError, TypeError):
            pass  # Container types (list, dict, ndarray) make pd.isna return non-scalar
        if isinstance(val, str):
            return _truncate_str(val)
        if isinstance(val, (int, float)):
            return val  # Preserve numeric types for tabulate formatting (floatfmt, alignment)
        # Convert other types (bytes, list, dict, Decimal, datetime, etc.) to str and truncate
        return _truncate_str(str(val))

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


def render_column_dtype(column: SQLColumnSchema, max_native_dtype_chars: int = 80) -> str:
    """Render a column's type for display to an LLM.

    Prefers ``native_dtype`` when it's short — it carries scalar parameters
    (``VARCHAR(100)``, ``DECIMAL(18, 2)``) the canonical ``dtype`` token
    discards. Falls back to ``dtype`` for unset or overly long native
    strings (e.g. deeply nested BigQuery RECORDs or DuckDB STRUCTs whose
    shape is better conveyed via ``json_schema``).
    """
    if column.native_dtype and len(column.native_dtype) <= max_native_dtype_chars:
        return column.native_dtype
    return column.dtype


def _is_union_schema(schema: dict[str, Any]) -> bool:
    """Whether ``schema`` renders with a top-level ``|`` via :func:`format_json_schema`.

    True when the schema has ``anyOf`` with more than one branch after
    collapsing duplicate ``null`` entries — i.e. the rendered form is
    ``A | B`` or ``A | null``. False for single-branch ``anyOf`` (renders
    as a bare type) and for non-``anyOf`` schemas.
    """
    if "anyOf" not in schema:
        return False
    subtypes = schema["anyOf"]
    non_null = [s for s in subtypes if s.get("type") != "null"]
    has_null = len(non_null) < len(subtypes)
    return len(non_null) >= 2 or (len(non_null) == 1 and has_null)


def format_json_schema(
    schema: dict[str, Any],
    *,
    max_depth: int | None = None,
    max_fields: int | None = 20,
    always_expand_top_level: bool = True,
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
            split equally among properties; each field consumes 1 unit for its
            name and type, with the remainder available for nested expansion.
            An object is truncated to ``{...}`` when the budget cannot cover
            all its fields.  ``None`` disables the adaptive limit.
        always_expand_top_level: When ``True``, the top-level object always
            lists its fields even if the budget is insufficient.  Nested
            objects that exceed the budget still collapse to ``{...}``.
        _depth: Current nesting depth (internal recursion parameter).
        _budget: Remaining field budget (internal recursion parameter).

    Returns:
        A compact type-annotation string.
    """
    if _budget is None and max_fields is not None:
        _budget = float(max_fields)

    kw: dict[str, Any] = dict(
        max_depth=max_depth, max_fields=max_fields, always_expand_top_level=always_expand_top_level
    )

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
        child_budget: float | None
        if _budget is not None and _budget < len(props):
            if always_expand_top_level and _depth == 0:
                child_budget = 0.0
            else:
                return "{...}"
        else:
            child_budget = _budget / len(props) - 1 if _budget is not None else None
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
            if inner.startswith("{"):
                return f"[{inner}]"
            # Parenthesize unions so ``[]`` binds to the whole alternation,
            # not just the last branch: ``(A | B)[]`` rather than ``A | B[]``.
            # Check the schema (not the rendered string) so already-parenthesized
            # inner forms like ``(A | B)[]`` don't get double-wrapped.
            if _is_union_schema(items_schema):
                return f"({inner})[]"
            return f"{inner}[]"
        return "array"

    if t in ("string", "integer", "number", "boolean", "null"):
        return t  # type: ignore

    return "any"


def format_exec_result_markdown(result: ExecResult) -> str:
    if result.error is not None:
        return f"**Error:** {result.error.exc_type}: {result.error.message}"
    if result.df is None:
        if result.affected_rows is not None:
            return f"*Statement executed successfully ({result.affected_rows} rows affected).*"
        return "*Statement executed successfully.*"
    rendered = format_df(result.df)
    count = len(result.df)
    suffix = f"*... truncated ({count} rows total)*" if count > 10 else f"*{count} rows*"
    return f"{rendered}\n\n{suffix}"
