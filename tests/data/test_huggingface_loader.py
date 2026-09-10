import asyncio
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import duckdb
import pytest

import tabulaflow.data.loaders.huggingface as huggingface
import tabulaflow.data.sql as sql
from tabulaflow.data.config import SQLConnectorConfig


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("https://huggingface.co/datasets/owner/dataset/", ("owner/dataset", None, None)),
        (
            "https://huggingface.co/datasets/owner/dataset/viewer/config/train?row=10#preview",
            ("owner/dataset", "config", "train"),
        ),
        (
            "https://huggingface.co/datasets/owner/dataset/viewer/en%2Fus/test%20split",
            ("owner/dataset", "en/us", "test split"),
        ),
        ("https://huggingface.co/datasets/owner/dataset/tree/main?download=true", ("owner/dataset", None, None)),
    ],
)
def test_parse_hf_dataset_url_normalizes_common_urls(
    url: str,
    expected: tuple[str, str | None, str | None],
) -> None:
    assert huggingface.parse_hf_dataset_url(url) == expected
    assert huggingface.is_hf_dataset_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/datasets/owner/dataset",
        "https://huggingface.co/owner/dataset",
        "https://huggingface.co/datasets/owner/dataset/blob/main/data.csv",
        "https://huggingface.co/datasets/owner/dataset/viewer",
        "https://huggingface.co/datasets/owner/dataset/viewer/config/train/extra",
    ],
)
def test_parse_hf_dataset_url_rejects_unrelated_paths(url: str) -> None:
    with pytest.raises(ValueError):
        huggingface.parse_hf_dataset_url(url)
    assert not huggingface.is_hf_dataset_url(url)


def test_build_hf_dataset_url_encodes_viewer_segments() -> None:
    assert huggingface.build_hf_dataset_url("owner/data set", "en/us", "test split") == (
        "https://huggingface.co/datasets/owner/data%20set/viewer/en%2Fus/test%20split"
    )


async def test_resolve_config_exposes_subset_choices(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_configs(_dataset_id: str) -> list[str]:
        return ["cola", "mnli", "mrpc"]

    monkeypatch.setattr(huggingface, "_fetch_configs_from_api", fake_configs)

    with pytest.raises(huggingface.HuggingFaceSubsetRequiredError) as exc_info:
        await huggingface._resolve_config("nyu-mll/glue", None)

    assert exc_info.value.dataset_id == "nyu-mll/glue"
    assert exc_info.value.subsets == ("cola", "mnli", "mrpc")


async def test_schema_worker_releases_cache_before_parent_opens_it(tmp_path: Path) -> None:
    db_path = tmp_path / "hf_cache.duckdb"
    with duckdb.connect(str(db_path)) as conn:
        conn.execute("INSTALL httpfs")
        conn.execute("CREATE TABLE documents (id INTEGER)")
        conn.execute("INSERT INTO documents VALUES (1)")
        conn.execute("CREATE VIEW remote_documents AS SELECT * FROM documents")
    config = SQLConnectorConfig(
        cache_dir=tmp_path,
        schema_cache_mode="off",
        sql_query_cache_mode="off",
    )

    schema = await huggingface._load_hf_schema_in_subprocess(
        str(db_path),
        global_id="hf-test",
        display_name="documents",
        dataset_url="https://huggingface.co/datasets/owner/documents",
        config=config,
    )

    tables = {table.name: table for table in schema.tables}
    assert tables["documents"].sampled_df is not None
    assert tables["documents"].columns[0].examples == [1]
    assert tables["remote_documents"].sampled_df is None
    assert tables["remote_documents"].columns[0].examples == []
    connector = await sql.SQLConnector.from_url_async(
        global_id="hf-parent",
        url=f"duckdb:///{db_path}",
        display_name="documents",
        schema=schema,
        read_only=False,
        config=config,
    )
    await connector.close_async()


async def test_cancelled_schema_worker_releases_cache_before_retry(tmp_path: Path) -> None:
    db_path = tmp_path / "slow_hf_cache.duckdb"
    with duckdb.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE VIEW remote_split AS
            WITH RECURSIVE loop(x) AS (
                VALUES(0)
                UNION ALL
                SELECT (x + 1) % 2 FROM loop
            )
            SELECT COUNT(*) AS value FROM loop
            """
        )
    config = SQLConnectorConfig(
        cache_dir=tmp_path,
        schema_cache_mode="off",
        sql_query_cache_mode="off",
    )
    task = asyncio.create_task(
        huggingface._load_hf_schema_in_subprocess(
            str(db_path),
            global_id="hf-cancel",
            display_name="documents",
            dataset_url="https://huggingface.co/datasets/owner/documents",
            config=config,
        )
    )

    await asyncio.sleep(0.5)
    assert not task.done()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=5)

    with duckdb.connect(str(db_path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM duckdb_views() WHERE view_name = 'remote_split'").fetchone() == (1,)


async def test_loader_uses_provenance_without_fetching_readme(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def fake_load(*_args: Any, **_kwargs: Any) -> tuple[str, list[str]]:
        return str(tmp_path / "dataset.duckdb"), []

    async def fake_schema(*_args: Any, **_kwargs: Any) -> Any:
        return SimpleNamespace()

    class FakeSQLConnector:
        @classmethod
        async def from_url_async(cls, **kwargs: Any) -> Any:
            captured.update(kwargs)
            return SimpleNamespace(schema=SimpleNamespace(tables=[]))

    monkeypatch.setattr(huggingface, "_load_hf_into_duckdb", fake_load)
    monkeypatch.setattr(huggingface, "_load_hf_schema_in_subprocess", fake_schema)
    monkeypatch.setattr(sql, "SQLConnector", FakeSQLConnector)

    dataset_url = "https://huggingface.co/datasets/owner/dataset"
    await huggingface.load_hf_dataset(dataset_url)

    assert captured["description"] == f"Source: Hugging Face dataset {dataset_url}"
