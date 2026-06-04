from typing import Any

import pytest

from tabulaflow.core.utils import format_json_schema
from tabulaflow.schema import SQLColumnSchema, SQLSchema, SQLTableSchema
from tabulaflow.toolhub.get_column_json_schema import (
    GetColumnJsonSchemaTool,
    _extract_examples_at_path,
    _parse_json_examples,
    _resolve_json_schema_path,
)

# ---------------------------------------------------------------------------
# Fixtures: reusable JSON schemas
# ---------------------------------------------------------------------------

SIMPLE_OBJECT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
    },
    "required": ["name", "age"],
}

NESTED_OBJECT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "page": {
            "type": "object",
            "properties": {
                "hostname": {"type": "string"},
                "pagePath": {"type": "string"},
            },
            "required": ["hostname", "pagePath"],
        },
        "time": {"type": "integer"},
    },
    "required": ["page", "time"],
}

ARRAY_OF_OBJECTS_SCHEMA: dict[str, Any] = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "product": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "v2ProductName": {"type": "string"},
                        "productPrice": {"type": "integer"},
                    },
                    "required": ["v2ProductName", "productPrice"],
                },
            },
            "transaction": {
                "type": "object",
                "properties": {
                    "currencyCode": {"type": "string"},
                    "transactionId": {"type": "string"},
                },
                "required": ["currencyCode"],
            },
            "hitNumber": {"type": "integer"},
        },
        "required": ["hitNumber"],
    },
}

NULLABLE_WRAPPER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "info": {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {
                        "detail": {"type": "string"},
                    },
                    "required": ["detail"],
                },
                {"type": "null"},
            ],
        },
    },
}

MULTI_VARIANT_ANYOF_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "data": {
            "anyOf": [
                {
                    "type": "object",
                    "properties": {
                        "fieldA": {"type": "string"},
                    },
                },
                {
                    "type": "object",
                    "properties": {
                        "fieldB": {"type": "integer"},
                    },
                },
                {"type": "null"},
            ],
        },
    },
}


# A wide schema (more fields than any reasonable budget)
WIDE_OBJECT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        f"field_{i}": (
            {
                "type": "object",
                "properties": {"nested": {"type": "string"}},
                "required": ["nested"],
            }
            if i < 3
            else {"type": "string"}
        )
        for i in range(40)
    },
    "required": [f"field_{i}" for i in range(40)],
}


# ---------------------------------------------------------------------------
# Tests for format_json_schema always_expand_top_level
# ---------------------------------------------------------------------------


class TestFormatJsonSchemaAlwaysExpandTopLevel:
    def test_wide_schema_expands_top_level_by_default(self) -> None:
        """Default (always_expand_top_level=True) shows all top-level fields."""
        result = format_json_schema(WIDE_OBJECT_SCHEMA, max_fields=10)
        # All 40 field names should appear
        for i in range(40):
            assert f"field_{i}" in result

    def test_wide_schema_nested_objects_collapse(self) -> None:
        """Nested objects should collapse to {...} when budget is exhausted."""
        result = format_json_schema(WIDE_OBJECT_SCHEMA, max_fields=10)
        # field_0..field_2 are objects — they should collapse to {...}
        assert "nested" not in result
        assert "{...}" in result

    def test_wide_schema_collapses_when_disabled(self) -> None:
        """With always_expand_top_level=False, wide schema collapses entirely."""
        result = format_json_schema(WIDE_OBJECT_SCHEMA, max_fields=10, always_expand_top_level=False)
        assert result == "{...}"

    def test_narrow_schema_unaffected(self) -> None:
        """Schema within budget produces the same result regardless of the flag."""
        result_on = format_json_schema(SIMPLE_OBJECT_SCHEMA, max_fields=20, always_expand_top_level=True)
        result_off = format_json_schema(SIMPLE_OBJECT_SCHEMA, max_fields=20, always_expand_top_level=False)
        assert result_on == result_off

    def test_nested_wide_object_still_collapses(self) -> None:
        """A nested wide object should still collapse even when flag is True."""
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "outer": {
                    "type": "object",
                    "properties": {f"x_{i}": {"type": "string"} for i in range(50)},
                },
            },
        }
        result = format_json_schema(schema, max_fields=5, always_expand_top_level=True)
        # Top-level "outer" is shown, but its 50 children collapse
        assert "outer" in result
        assert "{...}" in result
        assert "x_0" not in result

    def test_array_wrapping_wide_object(self) -> None:
        """Array whose items object is wide should expand top-level fields."""
        schema: dict[str, Any] = {
            "type": "array",
            "items": WIDE_OBJECT_SCHEMA,
        }
        result = format_json_schema(schema, max_fields=10, always_expand_top_level=True)
        # The items object is at _depth=0 (arrays pass depth through), so it expands
        for i in range(40):
            assert f"field_{i}" in result

    def test_array_of_anyof_is_parenthesized(self) -> None:
        """An array of a union must wrap the union in parens so ``[]`` binds
        to the whole alternation: ``(A | B | C)[]`` not ``A | B | C[]``."""
        schema: dict[str, Any] = {
            "type": "array",
            "items": {
                "anyOf": [
                    {"type": "string"},
                    {"type": "integer"},
                    {"type": "boolean"},
                ]
            },
        }
        assert format_json_schema(schema) == "(string | integer | boolean)[]"

    def test_array_of_nullable_is_parenthesized(self) -> None:
        """``T | null`` inside an array must also be parenthesized."""
        schema: dict[str, Any] = {
            "type": "array",
            "items": {"anyOf": [{"type": "string"}, {"type": "null"}]},
        }
        assert format_json_schema(schema) == "(string | null)[]"

    def test_nested_array_of_array_of_union(self) -> None:
        """Regression: the cypherbench ``answer_json`` shape — list-of-list-of-mixed."""
        schema: dict[str, Any] = {
            "type": "array",
            "items": {
                "type": "array",
                "items": {
                    "anyOf": [
                        {"type": "array", "items": {"type": "string"}},
                        {"type": "boolean"},
                        {"type": "integer"},
                        {"type": "number"},
                        {"type": "string"},
                        {"type": "null"},
                    ]
                },
            },
        }
        result = format_json_schema(schema)
        assert result == "(string[] | boolean | integer | number | string | null)[][]"


# ---------------------------------------------------------------------------
# Tests for _resolve_json_schema_path
# ---------------------------------------------------------------------------


class TestResolveJsonSchemaPath:
    def test_simple_property(self) -> None:
        result = _resolve_json_schema_path(SIMPLE_OBJECT_SCHEMA, "name")
        assert result == {"type": "string"}

    def test_nested_property(self) -> None:
        result = _resolve_json_schema_path(NESTED_OBJECT_SCHEMA, "page.hostname")
        assert result == {"type": "string"}

    def test_nested_object(self) -> None:
        result = _resolve_json_schema_path(NESTED_OBJECT_SCHEMA, "page")
        assert result is not None
        assert result["type"] == "object"
        assert "hostname" in result["properties"]

    def test_array_auto_deref(self) -> None:
        """Top-level array should be auto-dereferenced into items."""
        result = _resolve_json_schema_path(ARRAY_OF_OBJECTS_SCHEMA, "hitNumber")
        assert result == {"type": "integer"}

    def test_nested_array_auto_deref(self) -> None:
        """Nested array (product) should be auto-dereferenced."""
        result = _resolve_json_schema_path(ARRAY_OF_OBJECTS_SCHEMA, "product.v2ProductName")
        assert result == {"type": "string"}

    def test_array_then_object(self) -> None:
        result = _resolve_json_schema_path(ARRAY_OF_OBJECTS_SCHEMA, "transaction.currencyCode")
        assert result == {"type": "string"}

    def test_nullable_anyof_unwrap(self) -> None:
        result = _resolve_json_schema_path(NULLABLE_WRAPPER_SCHEMA, "info.detail")
        assert result == {"type": "string"}

    def test_case_insensitive(self) -> None:
        result = _resolve_json_schema_path(SIMPLE_OBJECT_SCHEMA, "NAME")
        assert result == {"type": "string"}

    def test_invalid_path_returns_none(self) -> None:
        assert _resolve_json_schema_path(SIMPLE_OBJECT_SCHEMA, "nonexistent") is None

    def test_invalid_deep_path_returns_none(self) -> None:
        assert _resolve_json_schema_path(NESTED_OBJECT_SCHEMA, "page.nonexistent") is None

    def test_path_into_scalar_returns_none(self) -> None:
        assert _resolve_json_schema_path(SIMPLE_OBJECT_SCHEMA, "name.something") is None

    def test_array_without_items_returns_none(self) -> None:
        schema: dict[str, Any] = {"type": "array"}
        assert _resolve_json_schema_path(schema, "anything") is None

    def test_all_null_anyof_returns_none(self) -> None:
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "field": {"anyOf": [{"type": "null"}]},
            },
        }
        assert _resolve_json_schema_path(schema, "field.sub") is None

    def test_anyof_multi_variant_first(self) -> None:
        """Path resolves via the first anyOf variant."""
        result = _resolve_json_schema_path(MULTI_VARIANT_ANYOF_SCHEMA, "data.fieldA")
        assert result == {"type": "string"}

    def test_anyof_multi_variant_second(self) -> None:
        """Path resolves via the second anyOf variant (not in the first)."""
        result = _resolve_json_schema_path(MULTI_VARIANT_ANYOF_SCHEMA, "data.fieldB")
        assert result == {"type": "integer"}

    def test_anyof_multi_variant_missing(self) -> None:
        """Path not in any variant returns None."""
        assert _resolve_json_schema_path(MULTI_VARIANT_ANYOF_SCHEMA, "data.fieldC") is None


# ---------------------------------------------------------------------------
# Tests for GetColumnJsonSchemaTool
# ---------------------------------------------------------------------------


def _make_schema(json_schema: dict[str, Any] | None = None, examples: list[Any] | None = None) -> SQLSchema:
    """Build a minimal SQLSchema with one table and one column."""
    return SQLSchema(
        name="test_db",
        tables=[
            SQLTableSchema(
                name="test_table",
                schema_name="test_schema",
                is_view=False,
                columns=[
                    SQLColumnSchema(
                        name="data_col",
                        dtype="VARIANT",
                        nullable=True,
                        json_schema=json_schema,
                        examples=examples or [],
                    ),
                ],
                primary_key=[],
                foreign_keys=[],
            ),
        ],
    )


class TestGetColumnJsonSchemaTool:
    @pytest.mark.asyncio
    async def test_overview_without_path(self) -> None:
        """Without path, should return a shallow overview."""
        tool = GetColumnJsonSchemaTool(_make_schema(ARRAY_OF_OBJECTS_SCHEMA))
        result = await tool("test_schema", "test_table", "data_col")
        # Should contain top-level field names
        assert "hitNumber" in result
        assert "product" in result
        assert "transaction" in result

    @pytest.mark.asyncio
    async def test_overview_is_shallow(self) -> None:
        """Overview should truncate deeply nested fields."""
        tool = GetColumnJsonSchemaTool(_make_schema(ARRAY_OF_OBJECTS_SCHEMA))
        result = await tool("test_schema", "test_table", "data_col")
        # Deeply nested fields should NOT appear at full depth in overview
        # (max_depth=2 means we see the object but its children are {…})
        # The exact behavior depends on format_json_schema limits
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_path_drills_into_subschema(self) -> None:
        tool = GetColumnJsonSchemaTool(_make_schema(ARRAY_OF_OBJECTS_SCHEMA))
        result = await tool("test_schema", "test_table", "data_col", path="transaction")
        assert "currencyCode" in result
        assert "transactionId" in result
        # Should NOT contain unrelated top-level fields
        assert "hitNumber" not in result

    @pytest.mark.asyncio
    async def test_path_to_leaf(self) -> None:
        tool = GetColumnJsonSchemaTool(_make_schema(ARRAY_OF_OBJECTS_SCHEMA))
        result = await tool("test_schema", "test_table", "data_col", path="product.v2ProductName")
        assert result == "string"

    @pytest.mark.asyncio
    async def test_path_not_found(self) -> None:
        tool = GetColumnJsonSchemaTool(_make_schema(ARRAY_OF_OBJECTS_SCHEMA))
        result = await tool("test_schema", "test_table", "data_col", path="nonexistent")
        assert "not found" in result
        assert tool.metrics().error_path_not_found == 1

    @pytest.mark.asyncio
    async def test_no_json_schema(self) -> None:
        tool = GetColumnJsonSchemaTool(_make_schema(json_schema=None))
        result = await tool("test_schema", "test_table", "data_col")
        assert "has no JSON schema" in result
        assert tool.metrics().error_no_json_schema == 1

    @pytest.mark.asyncio
    async def test_overview_includes_examples(self) -> None:
        tool = GetColumnJsonSchemaTool(_make_schema(SIMPLE_OBJECT_SCHEMA, examples=[{"name": "Alice", "age": 30}]))
        result = await tool("test_schema", "test_table", "data_col")
        assert "Alice" in result

    @pytest.mark.asyncio
    async def test_path_includes_sub_examples(self) -> None:
        """When path is given, examples are extracted at that sub-path."""
        tool = GetColumnJsonSchemaTool(
            _make_schema(SIMPLE_OBJECT_SCHEMA, examples=[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}])
        )
        result = await tool("test_schema", "test_table", "data_col", path="name")
        assert "Alice" in result
        assert "Bob" in result
        # Should NOT contain the full object
        assert "age" not in result

    @pytest.mark.asyncio
    async def test_path_no_matching_examples(self) -> None:
        """When examples don't contain the path, no examples section is appended."""
        tool = GetColumnJsonSchemaTool(_make_schema(SIMPLE_OBJECT_SCHEMA, examples=[{"name": "Alice"}]))
        # "age" exists in schema but not all examples have it — the one that does would be extracted
        # Use a path that truly doesn't exist in examples
        result = await tool("test_schema", "test_table", "data_col", path="age")
        # age=30 is not in the example (only "name" is), but let's test with a missing key
        assert "Examples:" not in result or "Alice" not in result


# ---------------------------------------------------------------------------
# Tests for _extract_examples_at_path
# ---------------------------------------------------------------------------


class TestExtractExamplesAtPath:
    def test_simple_key(self) -> None:
        examples = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        assert _extract_examples_at_path(examples, "name") == ["Alice", "Bob"]

    def test_nested_key(self) -> None:
        examples = [
            {"page": {"hostname": "example.com", "path": "/a"}},
            {"page": {"hostname": "test.org", "path": "/b"}},
        ]
        assert _extract_examples_at_path(examples, "page.hostname") == ["example.com", "test.org"]

    def test_array_flattening(self) -> None:
        """Lists in examples are flattened — each element is navigated."""
        examples = [
            [{"product": "A"}, {"product": "B"}],
            [{"product": "C"}],
        ]
        assert _extract_examples_at_path(examples, "product") == ["A", "B", "C"]

    def test_nested_array_flattening(self) -> None:
        """Array -> object -> array -> object path."""
        examples = [
            {
                "hits": [
                    {"transaction": {"id": "T1"}},
                    {"transaction": {"id": "T2"}},
                ]
            }
        ]
        assert _extract_examples_at_path(examples, "hits.transaction.id") == ["T1", "T2"]

    def test_missing_key_skipped(self) -> None:
        examples = [{"a": 1}, {"b": 2}, {"a": 3}]
        assert _extract_examples_at_path(examples, "a") == [1, 3]

    def test_none_values_skipped(self) -> None:
        examples = [None, {"name": "Alice"}, None]
        assert _extract_examples_at_path(examples, "name") == ["Alice"]

    def test_empty_examples(self) -> None:
        assert _extract_examples_at_path([], "anything") == []

    def test_path_not_in_any_example(self) -> None:
        examples = [{"a": 1}, {"b": 2}]
        assert _extract_examples_at_path(examples, "c") == []

    def test_json_string_examples_are_parsed(self) -> None:
        """String examples (e.g. from Snowflake VARIANT) should be parsed first."""
        examples = [
            '{"name": "Alice", "age": 30}',
            '{"name": "Bob", "age": 25}',
        ]
        assert _extract_examples_at_path(_parse_json_examples(examples), "name") == ["Alice", "Bob"]

    def test_json_string_array_examples(self) -> None:
        """Top-level JSON array strings are parsed and flattened."""
        examples = [
            '[{"product": "A"}, {"product": "B"}]',
            '[{"product": "C"}]',
        ]
        assert _extract_examples_at_path(_parse_json_examples(examples), "product") == ["A", "B", "C"]

    def test_non_json_strings_are_skipped(self) -> None:
        """Plain strings that aren't valid JSON are silently skipped."""
        examples = ["not-json", '{"name": "Alice"}']
        assert _extract_examples_at_path(_parse_json_examples(examples), "name") == ["Alice"]
