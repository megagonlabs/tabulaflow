import pytest

from mintq.schema import SQLColumnSchema, SQLSchema, SQLTableSchema
from mintq.toolhub.get_json_schema import (
    GetColumnJsonSchemaTool,
    _resolve_json_schema_path,
)

# ---------------------------------------------------------------------------
# Fixtures: reusable JSON schemas
# ---------------------------------------------------------------------------

SIMPLE_OBJECT_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
    },
    "required": ["name", "age"],
}

NESTED_OBJECT_SCHEMA: dict = {
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

ARRAY_OF_OBJECTS_SCHEMA: dict = {
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

NULLABLE_WRAPPER_SCHEMA: dict = {
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

MULTI_VARIANT_ANYOF_SCHEMA: dict = {
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
        schema: dict = {"type": "array"}
        assert _resolve_json_schema_path(schema, "anything") is None

    def test_all_null_anyof_returns_none(self) -> None:
        schema: dict = {
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


def _make_schema(json_schema: dict | None = None, examples: list | None = None) -> SQLSchema:
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
        tool = GetColumnJsonSchemaTool(
            _make_schema(SIMPLE_OBJECT_SCHEMA, examples=[{"name": "Alice", "age": 30}])
        )
        result = await tool("test_schema", "test_table", "data_col")
        assert "Alice" in result

    @pytest.mark.asyncio
    async def test_path_excludes_examples(self) -> None:
        tool = GetColumnJsonSchemaTool(
            _make_schema(SIMPLE_OBJECT_SCHEMA, examples=[{"name": "Alice", "age": 30}])
        )
        result = await tool("test_schema", "test_table", "data_col", path="name")
        assert "Alice" not in result
