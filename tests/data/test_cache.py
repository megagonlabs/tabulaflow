from pathlib import Path

import pytest

from tabulaflow.core import SQLSchema
from tabulaflow.data._cache import (
    cache_lock,
    query_cache_key,
    query_cache_path,
    read_cached_model,
    schema_cache_path,
    write_cached_model,
)


def test_schema_cache_path_is_flat_versioned_and_filename_safe(tmp_path: Path) -> None:
    path = schema_cache_path(tmp_path, "neo4j+movies", variant="fast")

    assert path.parent == tmp_path / "schemas"
    assert path.name == "v3@fast@neo4j+movies.json"

    with pytest.raises(ValueError, match="Invalid schema cache variant"):
        schema_cache_path(tmp_path, "neo4j+movies", variant="../fast")

    with pytest.raises(ValueError, match="global_id must be"):
        schema_cache_path(tmp_path, "../neo4j/movies")


def test_query_cache_key_includes_positional_and_named_parameters() -> None:
    positional_a = query_cache_key("SELECT ?", [1], 30, 100)
    positional_b = query_cache_key("SELECT ?", [2], 30, 100)
    named_a = query_cache_key("SELECT :value", {"value": 1}, 30, 100)
    named_b = query_cache_key("SELECT :value", {"value": 2}, 30, 100)

    assert positional_a != positional_b
    assert named_a != named_b
    assert query_cache_key("SELECT :value", {"value": 1}, 30, 100) == named_a


def test_query_cache_path_is_flat_and_versioned(tmp_path: Path) -> None:
    key = query_cache_key("SELECT 1", [], 30, 100)

    assert query_cache_path(tmp_path, "sql+shop", key) == tmp_path / "query_results" / f"v2@sql+shop@{key}.json"


async def test_schema_cache_roundtrip(tmp_path: Path) -> None:
    path = schema_cache_path(tmp_path, "sql+shop")
    schema = SQLSchema(display_name="shop", dialect="sqlite", tables=[])

    await write_cached_model(path, schema)

    assert await read_cached_model(path, SQLSchema) == schema


async def test_cache_lock_is_scoped_to_resolved_path(tmp_path: Path) -> None:
    path = schema_cache_path(tmp_path, "sql+shop")

    assert cache_lock(path) is cache_lock(path)
    assert cache_lock(path) is not cache_lock(schema_cache_path(tmp_path, "sql+other"))


async def test_failed_atomic_replace_preserves_existing_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = schema_cache_path(tmp_path, "sql+shop")
    original = SQLSchema(display_name="original", dialect="sqlite", tables=[])
    await write_cached_model(path, original)

    def fail_replace(_source: Path, _target: Path) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr("tabulaflow.core._cache.os.replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        await write_cached_model(path, SQLSchema(display_name="replacement", dialect="sqlite", tables=[]))

    assert await read_cached_model(path, SQLSchema) == original
    assert not list(path.parent.glob(f".{path.name}.*.tmp"))
