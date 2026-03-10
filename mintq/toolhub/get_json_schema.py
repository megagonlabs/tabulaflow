import json
from typing import Any, ClassVar

from pydantic import BaseModel
from pydantic_ai import Tool

from mintq.formatters.utils import format_json_schema
from mintq.schema import SQLSchema
from mintq.toolhub.utils import equals_ci

_DEFAULT_MAX_EXAMPLE_CHARS = 1000
_DEFAULT_OVERVIEW_MAX_FIELDS = 30


def _resolve_json_schema_path(schema: dict[str, Any], path: str) -> dict[str, Any] | None:
    """Navigate into a JSON Schema dict following a dot-separated path.

    At each segment the resolver:
    - Unwraps ``anyOf`` by trying each non-null variant until one succeeds.
    - Dereferences ``type: "array"`` by stepping into ``items``.
    - Looks up the segment in ``properties`` of an object node.

    Args:
        schema: A JSON Schema dictionary.
        path: Dot-separated path (e.g. ``"product.v2ProductName"``).

    Returns:
        The sub-schema at the given path, or ``None`` if the path does not
        resolve.
    """
    return _resolve_segments(schema, path.split("."))


def _resolve_segments(schema: dict[str, Any], segments: list[str]) -> dict[str, Any] | None:
    """Recursively resolve path segments against a JSON Schema node."""
    if not segments:
        return schema

    # Handle anyOf — try each non-null variant
    if "anyOf" in schema:
        non_null = [s for s in schema["anyOf"] if s.get("type") != "null"]
        for variant in non_null:
            result = _resolve_segments(variant, segments)
            if result is not None:
                return result
        return None

    # Dereference arrays — step into items
    if schema.get("type") == "array":
        if "items" in schema:
            return _resolve_segments(schema["items"], segments)
        return None

    # Look up segment in object properties
    if schema.get("type") == "object" and "properties" in schema:
        props = schema["properties"]
        segment = segments[0]
        # Case-insensitive lookup
        matched_key = None
        for key in props:
            if key.lower() == segment.lower():
                matched_key = key
                break
        if matched_key is not None:
            return _resolve_segments(props[matched_key], segments[1:])

    return None


def _format_examples(examples: list[Any], max_chars: int) -> str:
    """Format example values, including at least one and stopping when *max_chars* is reached."""
    if not examples or max_chars < 0:
        return ""
    parts: list[str] = []
    total = 0
    for ex in examples:
        formatted = json.dumps(ex, ensure_ascii=False) if isinstance(ex, (dict, list)) else str(ex)
        total += len(formatted)
        parts.append(formatted)
        # Always include at least one example; stop after that if budget exceeded
        if total >= max_chars and len(parts) >= 1:
            break
    parts = list(dict.fromkeys(parts))  # Remove duplicates
    return "\n\nExamples:\n" + "\n".join(parts)


class GetColumnJsonSchemaToolMetrics(BaseModel):
    num_calls: int = 0
    error_table_not_found: int = 0
    error_column_not_found: int = 0
    error_no_json_schema: int = 0
    error_path_not_found: int = 0


class GetColumnJsonSchemaTool:
    """Tool that retrieves the JSON schema of a specific column.

    Looks up a column by schema name, table name, and column name, then
    returns its full JSON schema if available. This is useful for exploring
    the internal structure of JSON/VARIANT columns that contain nested
    objects, arrays, etc.

    Attributes:
        schema: The SQL schema containing all available tables. Can be a
            compressed schema produced by SchemaCompressor.
        include_examples: Whether to include example values in the output.
        max_example_chars: Character budget for example values appended to
            the output.  At least one example is always included.
    """

    name: ClassVar = "get_column_json_schema"

    def __init__(
        self, schema: SQLSchema, include_examples: bool = True, max_example_chars: int = _DEFAULT_MAX_EXAMPLE_CHARS
    ):
        self.schema = schema
        self.include_examples = include_examples
        self.max_example_chars = max_example_chars
        self._metrics = GetColumnJsonSchemaToolMetrics()

    async def __call__(
        self, schema_name: str | None, table_name: str, column_name: str, path: str | None = None
    ) -> str:
        """Get the JSON schema of a column, describing its internal structure (nested objects, arrays, etc.).

        Useful for semi-structured column types such as VARIANT, OBJECT, ARRAY,
        JSON, and JSONB that store nested or complex data.

        When called without a path, returns a shallow overview of the schema
        (top-level fields and one level of nesting). To drill into a specific
        sub-structure, provide a dot-separated path (e.g. "product",
        "transaction.currencyCode"). Arrays are traversed automatically.

        Args:
            schema_name: The name of the schema, or None if schema is not applicable.
            table_name: The name of the table.
            column_name: The name of the column.
            path: Optional dot-separated path to a nested sub-schema. When
                provided, returns the full details of that sub-path instead of
                a shallow overview of the entire schema.
        """
        self._metrics.num_calls += 1

        # If there is only a single schema, use it regardless of what the agent specified
        all_schema_names = [t.schema_name for t in self.schema.tables]
        if len(set(all_schema_names)) == 1:
            schema_name = all_schema_names[0]

        # Remove the quote characters from the column name if they exist
        for quote_char in '"`':
            if column_name.startswith(quote_char) and column_name.endswith(quote_char):
                column_name = column_name[1:-1]
                break

        table = None
        for t in self.schema.tables:
            if (schema_name is None or equals_ci(t.schema_name, schema_name)) and (
                t.name.lower() == table_name.lower()
                or any(s.lower() == table_name.lower() for pattern in t.name_patterns for s in pattern.original_names)
            ):
                table = t
                break

        if table is None:
            self._metrics.error_table_not_found += 1
            return f"(table {table_name} in schema {schema_name} not found)"

        column = None
        for c in table.columns:
            if c.name.lower() == column_name.lower():
                column = c
                break

        if column is None:
            self._metrics.error_column_not_found += 1
            return f"(column {column_name} not found in table {table_name} in schema {schema_name})"

        if not column.json_schema:
            self._metrics.error_no_json_schema += 1
            return f"(column {column_name} in table {table_name} in schema {schema_name} has no JSON schema)"

        if path:
            target_schema = _resolve_json_schema_path(column.json_schema, path)
            if target_schema is None:
                self._metrics.error_path_not_found += 1
                return f"(path '{path}' not found in JSON schema of column {column_name})"
            return format_json_schema(target_schema, max_depth=None, max_fields=None)
        else:
            result = format_json_schema(column.json_schema, max_fields=_DEFAULT_OVERVIEW_MAX_FIELDS)
            if self.include_examples:
                result += _format_examples(column.examples, self.max_example_chars)
            return result

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)

    def metrics(self) -> GetColumnJsonSchemaToolMetrics:
        return self._metrics
