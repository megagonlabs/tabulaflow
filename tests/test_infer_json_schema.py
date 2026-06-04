from tabulaflow.core.db_connector.utils import infer_json_schema, looks_like_json


def test_all_null_returns_none() -> None:
    assert infer_json_schema([None, None]) is None


def test_empty_list_returns_none() -> None:
    assert infer_json_schema([]) is None


def test_simple_object() -> None:
    schema = infer_json_schema(
        [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
    )
    assert schema == {
        "type": "object",
        "properties": {
            "age": {"type": "integer"},
            "name": {"type": "string"},
        },
        "required": ["name", "age"],
    }


def test_optional_keys() -> None:
    """Keys not present in every sample should not be in 'required'."""
    schema = infer_json_schema(
        [
            {"name": "Alice", "age": 30},
            {"name": "Bob"},
        ]
    )
    assert schema is not None
    assert schema["required"] == ["name"]
    assert "age" in schema["properties"]


def test_nested_object() -> None:
    schema = infer_json_schema(
        [
            {"address": {"city": "NYC", "zip": "10001"}},
            {"address": {"city": "SF"}},
        ]
    )
    assert schema is not None
    addr = schema["properties"]["address"]
    assert addr["type"] == "object"
    assert addr["properties"]["city"] == {"type": "string"}
    assert addr["properties"]["zip"] == {"type": "string"}
    assert addr["required"] == ["city"]


def test_simple_array() -> None:
    schema = infer_json_schema(
        [
            ["a", "b"],
            ["c"],
        ]
    )
    assert schema == {
        "type": "array",
        "items": {"type": "string"},
    }


def test_array_of_objects() -> None:
    schema = infer_json_schema(
        [
            [{"id": 1}, {"id": 2}],
            [{"id": 3, "label": "x"}],
        ]
    )
    assert schema is not None
    assert schema["type"] == "array"
    items = schema["items"]
    assert items["type"] == "object"
    assert "id" in items["properties"]
    assert "label" in items["properties"]
    assert items["required"] == ["id"]


def test_object_with_array_field() -> None:
    schema = infer_json_schema(
        [
            {"tags": ["a", "b"]},
            {"tags": ["c"]},
        ]
    )
    assert schema is not None
    assert schema["properties"]["tags"] == {
        "type": "array",
        "items": {"type": "string"},
    }


def test_mixed_types() -> None:
    """When a field has different types across samples, produce anyOf."""
    schema = infer_json_schema(
        [
            {"val": 42},
            {"val": "hello"},
        ]
    )
    assert schema is not None
    val_schema = schema["properties"]["val"]
    assert val_schema == {"anyOf": [{"type": "integer"}, {"type": "string"}]}


def test_nullable_field() -> None:
    """Null values should appear as anyOf with null."""
    schema = infer_json_schema(
        [
            {"x": 1},
            {"x": None},
        ]
    )
    assert schema is not None
    x_schema = schema["properties"]["x"]
    assert x_schema == {"anyOf": [{"type": "integer"}, {"type": "null"}]}


def test_nullable_top_level() -> None:
    """Mix of null and non-null top-level values."""
    schema = infer_json_schema(
        [
            None,
            {"a": 1},
        ]
    )
    assert schema is not None
    assert schema == {
        "anyOf": [
            {"type": "object", "properties": {"a": {"type": "integer"}}, "required": ["a"]},
            {"type": "null"},
        ]
    }


def test_json_string_auto_parse() -> None:
    """String values that are valid JSON should be parsed automatically."""
    schema = infer_json_schema(
        [
            '{"name": "Alice", "age": 30}',
            '{"name": "Bob", "age": 25}',
        ]
    )
    assert schema is not None
    assert schema["type"] == "object"
    assert "name" in schema["properties"]
    assert "age" in schema["properties"]


def test_plain_string_not_parsed() -> None:
    """Non-JSON strings should remain as strings."""
    schema = infer_json_schema(["hello", "world"])
    assert schema == {"type": "string"}


def test_json_encoded_objects_nested_in_arrays_get_parsed() -> None:
    """Arrays whose items are JSON-encoded objects (the DuckDB ``JSON[]`` case)
    should infer object items, not string items."""
    schema = infer_json_schema(
        [
            ['{"id": "A", "phrase": "foo"}', '{"id": "B", "phrase": "bar"}'],
            ['{"id": "C", "phrase": "baz"}'],
        ]
    )
    assert schema is not None
    assert schema["type"] == "array"
    items = schema["items"]
    assert items["type"] == "object"
    assert items["properties"]["id"] == {"type": "string"}
    assert items["properties"]["phrase"] == {"type": "string"}


def test_json_encoded_objects_nested_in_struct_fields_get_parsed() -> None:
    """Object property values that are JSON-encoded objects should unwrap too."""
    schema = infer_json_schema(
        [
            {"meta": '{"version": 1, "author": "alice"}'},
            {"meta": '{"version": 2, "author": "bob"}'},
        ]
    )
    assert schema is not None
    meta = schema["properties"]["meta"]
    assert meta["type"] == "object"
    assert meta["properties"]["version"] == {"type": "integer"}


def test_scalar_looking_strings_inside_objects_stay_strings() -> None:
    """A property value like ``"10001"`` (ZIP code) is valid JSON for an integer,
    but the caller stored it as a string; nested inference must not reinterpret."""
    schema = infer_json_schema(
        [
            {"zip": "10001", "count": "5"},
            {"zip": "94016", "count": "12"},
        ]
    )
    assert schema is not None
    assert schema["properties"]["zip"] == {"type": "string"}
    assert schema["properties"]["count"] == {"type": "string"}


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
    schema = infer_json_schema(
        [
            '{"key": "val"}',
            None,
            '{"key": "other", "extra": 1}',
        ]
    )
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


# ── looks_like_json tests ──────────────────────────────────────────────


def test_looks_like_json_objects() -> None:
    assert looks_like_json(['{"a": 1}', '{"b": 2}', '{"c": 3}']) is True


def test_looks_like_json_arrays() -> None:
    assert looks_like_json(["[1, 2]", "[3]", "[]"]) is True


def test_looks_like_json_plain_strings() -> None:
    assert looks_like_json(["hello", "world", "foo"]) is False


def test_looks_like_json_scalars_not_counted() -> None:
    """JSON scalars like '42' or '"hello"' should not count as JSON."""
    assert looks_like_json(["42", '"hello"', "true"]) is False


def test_looks_like_json_mixed_below_threshold() -> None:
    """If less than 80% are JSON, return False."""
    assert looks_like_json(['{"a": 1}', "plain", "text", "hello", "world"]) is False


def test_looks_like_json_mixed_above_threshold() -> None:
    """If >= 80% are JSON, return True."""
    assert looks_like_json(['{"a": 1}', '{"b": 2}', '{"c": 3}', '{"d": 4}', "plain"]) is True


def test_looks_like_json_empty_list() -> None:
    assert looks_like_json([]) is False


def test_looks_like_json_all_none() -> None:
    assert looks_like_json([None, None]) is False


def test_looks_like_json_custom_threshold() -> None:
    values = ['{"a": 1}', "plain"]  # 50% JSON
    assert looks_like_json(values, threshold=0.5) is True
    assert looks_like_json(values, threshold=0.8) is False


def test_looks_like_json_whitespace_strings() -> None:
    """Empty/whitespace strings should be ignored."""
    assert looks_like_json(["", "  ", '{"a": 1}']) is True
