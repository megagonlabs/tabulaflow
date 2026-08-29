import json
from pathlib import Path

import pytest

from tabulaflow.research.benchmarks.beaver import BeaverDatasetLoader
from tabulaflow.research.benchmarks.ambrosia_s import AMBROSIA_DATASET_INSTRUCTIONS, AmbrosiaSDatasetLoader
from tabulaflow.research.benchmarks.bird_sql import BirdSQLDatasetLoader
from tabulaflow.research.benchmarks.registry import select_tasks, selected_databases
from tabulaflow.research.benchmarks.spider2_snow import Spider2SnowDatasetLoader
from tabulaflow.research.types import GoldQuery, SimpleNL2QTask


def _task(qid: str, db: str = "db") -> SimpleNL2QTask:
    return SimpleNL2QTask(qid=qid, db=db, question=qid, gold_query=GoldQuery(query="SELECT 1"))


def test_first_split_is_the_default() -> None:
    assert BirdSQLDatasetLoader.splits[0] == "dev"


def test_task_selection_filters_before_sampling() -> None:
    tasks = [_task("q1"), _task("q2"), _task("q3")]

    assert select_tasks(tasks, qids=["q2"], subsample_size=1) == [tasks[1]]


def test_task_selection_rejects_invalid_requests() -> None:
    tasks = [_task("q1")]

    with pytest.raises(ValueError, match="Unknown QIDs"):
        select_tasks(tasks, qids=["missing"])
    with pytest.raises(ValueError, match="Cannot sample"):
        select_tasks(tasks, subsample_size=2)


def test_selected_databases_preserves_first_seen_order() -> None:
    assert selected_databases([_task("q1", "b"), _task("q2", "a"), _task("q3", "b")]) == ["b", "a"]


@pytest.mark.asyncio
async def test_beaver_qids_include_the_source_file(tmp_path: Path) -> None:
    item = {"db_id": "dw", "question": "Question", "sql": "SELECT 1"}
    for name in ("dev_dw.json", "dev_nw.json"):
        (tmp_path / name).write_text(json.dumps([item]))

    tasks = await BeaverDatasetLoader(directory=str(tmp_path)).get_tasks_async("test")

    assert [task.qid for task in tasks] == ["beaver_test_dev_dw_0", "beaver_test_dev_nw_0"]


@pytest.mark.asyncio
async def test_ambrosia_tasks_always_include_dataset_instructions(tmp_path: Path) -> None:
    (tmp_path / "db_list.txt").write_text("db\n")
    task = {
        "qid": "q1",
        "has_intended_resolution": True,
        "db": "db",
        "question": "Which value?",
        "gold_ambiguity_points": [
            {
                "id": "A",
                "phrase": "value",
                "type": "finite",
                "ambiguity_type": "semantic_value",
                "interpretations": ["first"],
                "intended_interpretation_idx": 0,
            }
        ],
        "gold_queries": [{"id": "GQRY-A.0", "query": "SELECT 1"}],
        "gold_intended_query_id": "GQRY-A.0",
    }
    (tmp_path / "ambrosia_test_processed.json").write_text(json.dumps([task]))

    tasks = await AmbrosiaSDatasetLoader(directory=str(tmp_path)).get_tasks_async("test")

    assert tasks[0].dataset_instructions == AMBROSIA_DATASET_INSTRUCTIONS


@pytest.mark.asyncio
async def test_spider2_snow_requires_a_gold_execution_result(tmp_path: Path) -> None:
    gold_dir = tmp_path / "evaluation_suite" / "gold"
    (gold_dir / "exec_result").mkdir(parents=True)
    (gold_dir / "spider2snow_eval.jsonl").write_text("")
    item = {"instance_id": "q1", "db_id": "DB", "instruction": "Question", "external_knowledge": None}
    (tmp_path / "spider2-snow.jsonl").write_text(json.dumps(item) + "\n")

    loader = Spider2SnowDatasetLoader(directory=str(tmp_path))
    with pytest.raises(FileNotFoundError, match="No gold execution result found for q1"):
        await loader.get_tasks_async("test", databases=["DB"])
