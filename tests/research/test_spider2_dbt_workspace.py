import json
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock

import pytest

from tabulaflow.data import SQLConnector
from tabulaflow.research.benchmarks.spider2_dbt import Spider2DbtDatasetLoader
from tabulaflow.research.types import DbtTask


@pytest.mark.asyncio
async def test_dbt_loader_prepares_isolated_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    data_dir = tmp_path / "data"
    project_dir = data_dir / "examples" / "q1"
    project_dir.mkdir(parents=True)
    (project_dir / "source.duckdb").touch()
    (project_dir / "dbt_project.yml").write_text("name: example")
    (data_dir / "examples" / "spider2-dbt.jsonl").write_text(
        json.dumps({"instance_id": "q1", "instruction": "Build a model"}) + "\n"
    )
    gold_dir = data_dir / "evaluation_suite" / "gold"
    (gold_dir / "q1").mkdir(parents=True)
    (gold_dir / "q1" / "gold.duckdb").touch()
    (gold_dir / "spider2_eval.jsonl").write_text(
        json.dumps(
            {
                "instance_id": "q1",
                "evaluation": {
                    "parameters": {
                        "gold": "gold.duckdb",
                        "condition_tabs": [],
                    }
                },
            }
        )
        + "\n"
    )

    connector = SimpleNamespace()
    create_connector = AsyncMock(return_value=connector)
    monkeypatch.setattr(SQLConnector, "from_url_async", create_connector)
    workspace = tmp_path / "workspace"
    loader = Spider2DbtDatasetLoader(directory=str(data_dir), workspace_dir=workspace)

    dataset = await loader.get_split_async("test", qids=["q1"])

    working_dir = workspace / "q1"
    task = cast(DbtTask, dataset.tasks[0])
    assert task.working_dir == str(working_dir)
    assert (working_dir / "dbt_project.yml").read_text() == "name: example"
    assert dataset.db_connectors["q1"] is connector
    call = create_connector.await_args
    assert call is not None
    assert call.kwargs["url"] == f"duckdb:///{working_dir / 'source.duckdb'}"


@pytest.mark.asyncio
async def test_dbt_loader_does_not_overwrite_existing_workspace(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    project_dir = data_dir / "examples" / "q1"
    project_dir.mkdir(parents=True)
    (project_dir / "source.duckdb").touch()
    workspace = tmp_path / "workspace"
    (workspace / "q1").mkdir(parents=True)
    loader = Spider2DbtDatasetLoader(directory=str(data_dir), workspace_dir=workspace)

    with pytest.raises(FileExistsError, match="dbt working directory already exists"):
        await loader.get_db_connectors_async("test", ["q1"])
