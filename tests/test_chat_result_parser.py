import pandas as pd
import pytest
from pydantic_ai.messages import ToolReturnPart

from tabulaflow.chat.agent import _build_chat_result, _declared_bundle, _TextStreamRouter, _strip_answer_marker
from tabulaflow.core.types import ExecResult, PredQuery
from tabulaflow.toolhub import Artifact, ArtifactBundle, QueryHistory


def test_strip_answer_marker_removes_the_marker() -> None:
    assert _strip_answer_marker("<answer>\nThere are 3 rows.") == "There are 3 rows."


def test_strip_answer_marker_leaves_unmarked_text_alone() -> None:
    text = "I'm tabulaflow, an interactive data assistant.\n\n---\nAsk me anything about your data."

    assert _strip_answer_marker(text) == text


def test_text_stream_router_waits_for_the_answer_marker() -> None:
    router = _TextStreamRouter()

    assert router.feed("<ans") == ""
    assert router.feed("wer>") == ""
    assert router.feed("\nThere") == "There"
    assert router.is_answer
    assert router.feed(" are 3 rows.") == " are 3 rows."


def test_text_stream_router_routes_plain_prose_as_narration() -> None:
    router = _TextStreamRouter()

    assert router.feed("Thinking out loud.") == "Thinking out loud."
    assert not router.is_answer


def test_text_stream_router_resets_between_runs() -> None:
    router = _TextStreamRouter()

    assert router.feed("Looking at the schema.") == "Looking at the schema."
    assert not router.is_answer
    router.reset()
    assert router.feed("<answer>Done.") == "Done."
    assert router.is_answer


def _show_artifacts_part(call_id: str, bundle: ArtifactBundle | None) -> ToolReturnPart:
    return ToolReturnPart(
        tool_name="show_artifacts",
        content="showing" if bundle is not None else "(error: unknown artifact id 'Q9')",
        tool_call_id=call_id,
        metadata=bundle,
    )


def test_declared_bundle_skips_failed_calls_and_takes_the_last() -> None:
    first = ArtifactBundle(artifacts=(Artifact(id="Q1", label="first"),))
    second = ArtifactBundle(artifacts=(Artifact(id="Q1", label="second"),))
    completed = {
        "a": _show_artifacts_part("a", first),
        "b": ToolReturnPart(tool_name="run_query", content="1 row", tool_call_id="b"),
        "c": _show_artifacts_part("c", second),
        "d": _show_artifacts_part("d", None),  # a later call that errored
    }

    assert _declared_bundle(completed) is second
    assert _declared_bundle({"b": completed["b"]}) is None


@pytest.mark.asyncio
async def test_build_chat_result_resolves_the_declared_bundle() -> None:
    history = QueryHistory()
    await history.add(
        "workspace", "sql", PredQuery(query="SELECT 1", exec_result=ExecResult(df=pd.DataFrame({"a": [1]})))
    )
    bundle = ArtifactBundle(artifacts=(Artifact(id="Q1", label="row count"),))

    result = await _build_chat_result("<answer>\nThere is 1 row.", bundle, history)

    assert result.text == "There is 1 row."
    assert [(artifact.record_id, artifact.label) for artifact in result.artifacts] == [("Q1", "row count")]
    assert result.primary_artifact_index == 0

    without = await _build_chat_result("<answer>\nNothing to show.", None, history)
    assert without.artifacts == []
    assert without.primary_artifact_index is None
