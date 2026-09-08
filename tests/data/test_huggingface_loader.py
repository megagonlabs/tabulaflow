from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import tabulaflow.data.loaders.huggingface as huggingface
import tabulaflow.data.sql as sql


async def test_loader_uses_provenance_without_fetching_readme(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def fake_load(*_args: Any, **_kwargs: Any) -> tuple[str, list[str]]:
        return str(tmp_path / "dataset.duckdb"), []

    class FakeSQLConnector:
        @classmethod
        async def from_url_async(cls, **kwargs: Any) -> Any:
            captured.update(kwargs)
            return SimpleNamespace(schema=SimpleNamespace(tables=[]))

    monkeypatch.setattr(huggingface, "_load_hf_into_duckdb", fake_load)
    monkeypatch.setattr(sql, "SQLConnector", FakeSQLConnector)

    dataset_url = "https://huggingface.co/datasets/owner/dataset"
    await huggingface.load_hf_dataset(dataset_url)

    assert captured["description"] == f"Source: Hugging Face dataset {dataset_url}"
