import datetime
from pathlib import Path

import pandas as pd
import pytest
from pydantic import ValidationError

from tabulaflow.research.reporting import dict_to_df
from tabulaflow.research.types import (
    ARCSAmbiguityType,
    AmbigNL2QTask,
    DbtTask,
    GoldAmbiguityPointFinite,
    GoldQuery,
    NL2QRunResult,
    PredQuery,
    SimpleNL2QTaskOutput,
)


def test_query_markdown_delegates_to_reporting() -> None:
    predicted = PredQuery(query="SELECT 1")
    gold = GoldQuery(query="SELECT 1")

    assert predicted.to_markdown() == "## Pred Query\n\n```sql\nSELECT 1\n```"
    assert gold.to_markdown() == "## Gold Query\n\n```sql\nSELECT 1\n```"


def test_run_result_directory_layout(tmp_path: Path) -> None:
    task = SimpleNL2QTaskOutput(
        qid="q1",
        db="db",
        question="Return one.",
        gold_query=GoldQuery(query="SELECT 1"),
        pred_query=PredQuery(query="SELECT 1"),
        eval_metrics={"accuracy": 1},
    )
    result = NL2QRunResult(
        start_time=datetime.datetime(2026, 1, 1),
        end_time=datetime.datetime(2026, 1, 1),
        dataset="test",
        split="test",
        databases=["db"],
        subsample_size=None,
        agent="test",
        agent_config={},
        tasks=[task],
    )

    result.to_directory(str(tmp_path), eval_metrics_in_summary=["accuracy"])

    assert (tmp_path / "result.json").is_file()
    assert (tmp_path / "readable" / "q1" / "task_readable.md").is_file()
    summary = pd.read_csv(tmp_path / "result_summary.csv")
    assert summary.loc[0, "qid"] == "q1"
    assert summary.loc[0, "accuracy"] == 1


def test_empty_run_writes_summary_headers(tmp_path: Path) -> None:
    result = NL2QRunResult(
        start_time=datetime.datetime(2026, 1, 1),
        end_time=datetime.datetime(2026, 1, 1),
        dataset="test",
        split="test",
        databases=[],
        subsample_size=None,
        agent="test",
        agent_config={},
        tasks=[],
    )

    result.to_csv(str(tmp_path / "summary.csv"), eval_metrics=["accuracy"])

    assert list(pd.read_csv(tmp_path / "summary.csv").columns) == [
        "qid",
        "db",
        "question",
        "question_instructions",
        "gold_query",
        "pred_query",
        "gold_exec_result",
        "pred_exec_result",
        "accuracy",
    ]


def test_dict_to_df_handles_empty_input_and_forwards_total_column_only() -> None:
    assert dict_to_df({}).empty

    result = dict_to_df(
        {"first": {"a": 1, "b": 2}, "second": {"a": 3, "b": 4}},
        column_level="inner",
        total_column_only=True,
    )

    assert list(result.columns) == ["Total"]


def test_dbt_markdown_delegates_to_reporting() -> None:
    task = DbtTask(qid="q1", db="project", question="Build a model.", project_dir="project", gold_tables=[])

    markdown = task.to_markdown()

    assert "# Task: q1" in markdown
    assert "**Project:** project" in markdown
    assert "## Instruction\nBuild a model." in markdown


def test_ambiguous_task_validation_uses_explicit_errors() -> None:
    point = GoldAmbiguityPointFinite(
        id="A",
        phrase="value",
        ambiguity_type=ARCSAmbiguityType.semantic_value,
        interpretations=["first", "second"],
        intended_interpretation_idx=0,
    )

    with pytest.raises(ValidationError, match="gold_intended_query_id is required"):
        AmbigNL2QTask(
            qid="q1",
            has_intended_resolution=True,
            db="db",
            question="value",
            gold_ambiguity_points=[point],
            gold_queries=[GoldQuery(id="GQRY-A.0", query="SELECT 1"), GoldQuery(id="GQRY-A.1", query="SELECT 2")],
            gold_intended_query_id=None,
        )
