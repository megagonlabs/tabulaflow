import pytest
from mintq.db_connector.utils import infer_json_schema


def test_all_null_returns_none() -> None:
    assert infer_json_schema([None, None]) is None


def test_empty_list_returns_none() -> None:
    assert infer_json_schema([]) is None


def test_simple_object() -> None:
    schema = infer_json_schema([
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
    ])
    assert schema == {
        "type": "object",
        "properties": {
            "age": {"type": "integer"},
            "name": {"type": "string"},
        },
        "required": ["age", "name"],
    }


def test_optional_keys() -> None:
    """Keys not present in every sample should not be in 'required'."""
    schema = infer_json_schema([
        {"name": "Alice", "age": 30},
        {"name": "Bob"},
    ])
    assert schema is not None
    assert schema["required"] == ["name"]
    assert "age" in schema["properties"]


def test_nested_object() -> None:
    schema = infer_json_schema([
        {"address": {"city": "NYC", "zip": "10001"}},
        {"address": {"city": "SF"}},
    ])
    assert schema is not None
    addr = schema["properties"]["address"]
    assert addr["type"] == "object"
    assert addr["properties"]["city"] == {"type": "string"}
    assert addr["properties"]["zip"] == {"type": "string"}
    assert addr["required"] == ["city"]


def test_simple_array() -> None:
    schema = infer_json_schema([
        ["a", "b"],
        ["c"],
    ])
    assert schema == {
        "type": "array",
        "items": {"type": "string"},
    }


def test_array_of_objects() -> None:
    schema = infer_json_schema([
        [{"id": 1}, {"id": 2}],
        [{"id": 3, "label": "x"}],
    ])
    assert schema is not None
    assert schema["type"] == "array"
    items = schema["items"]
    assert items["type"] == "object"
    assert "id" in items["properties"]
    assert "label" in items["properties"]
    assert items["required"] == ["id"]


def test_object_with_array_field() -> None:
    schema = infer_json_schema([
        {"tags": ["a", "b"]},
        {"tags": ["c"]},
    ])
    assert schema is not None
    assert schema["properties"]["tags"] == {
        "type": "array",
        "items": {"type": "string"},
    }


def test_mixed_types() -> None:
    """When a field has different types across samples, produce anyOf."""
    schema = infer_json_schema([
        {"val": 42},
        {"val": "hello"},
    ])
    assert schema is not None
    val_schema = schema["properties"]["val"]
    assert val_schema == {"anyOf": [{"type": "integer"}, {"type": "string"}]}


def test_nullable_field() -> None:
    """Null values should appear as anyOf with null."""
    schema = infer_json_schema([
        {"x": 1},
        {"x": None},
    ])
    assert schema is not None
    x_schema = schema["properties"]["x"]
    assert x_schema == {"anyOf": [{"type": "integer"}, {"type": "null"}]}


def test_nullable_top_level() -> None:
    """Mix of null and non-null top-level values."""
    schema = infer_json_schema([
        None,
        {"a": 1},
    ])
    assert schema is not None
    assert schema == {
        "anyOf": [
            {"type": "object", "properties": {"a": {"type": "integer"}}, "required": ["a"]},
            {"type": "null"},
        ]
    }


def test_json_string_auto_parse() -> None:
    """String values that are valid JSON should be parsed automatically."""
    schema = infer_json_schema([
        '{"name": "Alice", "age": 30}',
        '{"name": "Bob", "age": 25}',
    ])
    assert schema is not None
    assert schema["type"] == "object"
    assert "name" in schema["properties"]
    assert "age" in schema["properties"]


def test_plain_string_not_parsed() -> None:
    """Non-JSON strings should remain as strings."""
    schema = infer_json_schema(["hello", "world"])
    assert schema == {"type": "string"}


def test_boolean_not_integer() -> None:
    """Booleans should be typed as 'boolean', not 'integer'."""
    schema = infer_json_schema([True, False])
    assert schema == {"type": "boolean"}


def test_boolean_field_in_object() -> None:
    schema = infer_json_schema([{"active": True}, {"active": False}])
    assert schema is not None
    assert schema["properties"]["active"] == {"type": "boolean"}


def test_float_type() -> None:
    schema = infer_json_schema([1.5, 2.7])
    assert schema == {"type": "number"}


def test_mixed_int_and_float() -> None:
    schema = infer_json_schema([1, 2.5])
    assert schema == {"anyOf": [{"type": "integer"}, {"type": "number"}]}


def test_empty_object() -> None:
    schema = infer_json_schema([{}])
    assert schema == {"type": "object"}


def test_empty_array() -> None:
    schema = infer_json_schema([[]])
    assert schema == {"type": "array"}


def test_deeply_nested() -> None:
    value = {"a": {"b": {"c": {"d": 1}}}}
    schema = infer_json_schema([value])
    assert schema is not None
    d_schema = schema["properties"]["a"]["properties"]["b"]["properties"]["c"]["properties"]["d"]
    assert d_schema == {"type": "integer"}


def test_max_depth_truncates() -> None:
    """Recursion should stop at max_depth and return empty schema."""
    value = {"a": {"b": {"c": 1}}}
    schema = infer_json_schema([value], max_depth=2)
    assert schema is not None
    # depth 0: top object, depth 1: "a" object, depth 2: truncated
    b_schema = schema["properties"]["a"]["properties"]["b"]
    assert b_schema == {}


def test_mixed_json_strings_and_nulls() -> None:
    schema = infer_json_schema([
        '{"key": "val"}',
        None,
        '{"key": "other", "extra": 1}',
    ])
    assert schema is not None
    assert schema == {
        "anyOf": [
            {
                "type": "object",
                "properties": {
                    "extra": {"type": "integer"},
                    "key": {"type": "string"},
                },
                "required": ["key"],
            },
            {"type": "null"},
        ]
    }
