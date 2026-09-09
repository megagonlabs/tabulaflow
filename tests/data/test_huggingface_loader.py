from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import tabulaflow.data.loaders.huggingface as huggingface
import tabulaflow.data.sql as sql


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
