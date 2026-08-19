import json
from typing import Any

import pandas as pd
from tabulate import tabulate

from tabulaflow.core import ExecResult
from tabulaflow.data.base import DataConnector


def format_connector_summary(connector: DataConnector) -> str:
    """Format a concise summary of a live data connector.

    Args:
        connector: Connector to summarize.

    Returns:
        Human-readable backend, language, and schema-size information.
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


def format_dataframe(
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


def _is_union_schema(schema: dict[str, Any]) -> bool:
    """Whether ``schema`` renders with a top-level ``|`` via :func:`format_json_schema_type`.

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


def format_json_schema_type(
    schema: dict[str, Any],
    *,
    max_depth: int | None = None,
    max_fields: int | None = 20,
    always_expand_top_level: bool = True,
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

    Returns:
        A compact type-annotation string.
    """
    return _format_json_schema_type(
        schema,
        max_depth=max_depth,
        always_expand_top_level=always_expand_top_level,
        depth=0,
        budget=float(max_fields) if max_fields is not None else None,
    )


def _format_json_schema_type(
    schema: dict[str, Any],
    *,
    max_depth: int | None,
    always_expand_top_level: bool,
    depth: int,
    budget: float | None,
) -> str:
    kw: dict[str, Any] = dict(max_depth=max_depth, always_expand_top_level=always_expand_top_level)

    # Handle anyOf (union types, including nullable)
    if "anyOf" in schema:
        subtypes: list[dict[str, Any]] = schema["anyOf"]
        non_null = [s for s in subtypes if s.get("type") != "null"]
        has_null = len(non_null) < len(subtypes)
        if not non_null:
            return "null"
        if len(non_null) == 1:
            inner = _format_json_schema_type(non_null[0], **kw, depth=depth, budget=budget)
        else:
            parts = [_format_json_schema_type(s, **kw, depth=depth, budget=budget) for s in non_null]
            inner = " | ".join(parts)
        return f"{inner} | null" if has_null else inner

    t = schema.get("type")

    if t == "object":
        props: dict[str, Any] = schema.get("properties", {})
        if not props:
            return "object"
        if max_depth is not None and depth >= max_depth:
            return "{...}"
        child_budget: float | None
        if budget is not None and budget < len(props):
            if always_expand_top_level and depth == 0:
                child_budget = 0.0
            else:
                return "{...}"
        else:
            child_budget = budget / len(props) - 1 if budget is not None else None
        required = set[Any](schema.get("required", []))
        field_parts: list[str] = []
        for key, val_schema in props.items():
            suffix = "?" if key not in required else ""
            formatted = _format_json_schema_type(val_schema, **kw, depth=depth + 1, budget=child_budget)
            field_parts.append(f"{key}{suffix}: {formatted}")
        return "{" + ", ".join(field_parts) + "}"

    if t == "array":
        items_schema = schema.get("items")
        if items_schema:
            inner = _format_json_schema_type(items_schema, **kw, depth=depth, budget=budget)
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
    rendered = format_dataframe(result.df)
    count = len(result.df)
    suffix = f"*... truncated ({count} rows total)*" if count > 20 else f"*{count} rows*"
    return f"{rendered}\n\n{suffix}"
