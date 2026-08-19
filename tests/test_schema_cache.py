from pathlib import Path

import pytest

from tabulaflow.core import SQLSchema
from tabulaflow.data.schema_cache import (
    read_schema_cache,
    schema_cache_lock,
    schema_cache_path,
    write_schema_cache,
)


def test_schema_cache_path_is_flat_versioned_and_filename_safe(tmp_path: Path) -> None:
    path = schema_cache_path(tmp_path, "neo4j+movies", variant="fast")

    assert path.parent == tmp_path / "schemas"
    assert path.name == "v1@fast@neo4j+movies.json"

    with pytest.raises(ValueError, match="Invalid schema cache variant"):
        schema_cache_path(tmp_path, "neo4j+movies", variant="../fast")

    with pytest.raises(ValueError, match="global_id must be"):
        schema_cache_path(tmp_path, "../neo4j/movies")


async def test_schema_cache_roundtrip(tmp_path: Path) -> None:
    path = schema_cache_path(tmp_path, "sql+shop")
    schema = SQLSchema(name="shop", dialect="sqlite", tables=[])

    await write_schema_cache(path, schema)

    assert await read_schema_cache(path, SQLSchema) == schema


async def test_schema_cache_lock_is_scoped_to_resolved_path(tmp_path: Path) -> None:
    path = schema_cache_path(tmp_path, "sql+shop")

    assert schema_cache_lock(path) is schema_cache_lock(path)
    assert schema_cache_lock(path) is not schema_cache_lock(schema_cache_path(tmp_path, "sql+other"))


async def test_failed_atomic_replace_preserves_existing_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = schema_cache_path(tmp_path, "sql+shop")
    original = SQLSchema(name="original", dialect="sqlite", tables=[])
    await write_schema_cache(path, original)

    def fail_replace(_source: Path, _target: Path) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr("tabulaflow.data.schema_cache.os.replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        await write_schema_cache(path, SQLSchema(name="replacement", dialect="sqlite", tables=[]))

    assert await read_schema_cache(path, SQLSchema) == original
    assert not list(path.parent.glob(f".{path.name}.*.tmp"))
