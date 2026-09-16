"""DataFrame enrichment contracts using real structured output and an offline model."""

import asyncio
from datetime import date, datetime
from enum import Enum
from typing import Annotated, Any, Literal

import pandas as pd
import pytest
from pydantic import BaseModel, Field, RootModel, create_model, field_serializer, field_validator
from pandas.testing import assert_frame_equal, assert_index_equal
from pydantic_ai.messages import ModelMessage, ModelResponse, RetryPromptPart, ToolCallPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from tabulaflow.agents.enrichment import DataFrameEnricher


class Label(BaseModel):
    label: str


class Count(BaseModel):
    count: int


class Value(BaseModel):
    value: int


class Mode(BaseModel):
    mode: Literal["remote", "onsite"]


def _prompt(messages: list[ModelMessage]) -> str:
    content = next(part.content for message in messages for part in message.parts if isinstance(part, UserPromptPart))
    assert isinstance(content, str)
    return content


def _answer(values: dict[str, Any]) -> ModelResponse:
    return ModelResponse(parts=[ToolCallPart("submit_answer", values)])


@pytest.mark.parametrize("multi_index", [False, True])
async def test_preserves_rows_index_and_other_columns_when_results_finish_out_of_order(multi_index: bool) -> None:
    index = pd.MultiIndex.from_tuples([("a", 2), ("a", 2), ("b", 1)]) if multi_index else pd.Index([7, 7, 2])
    original = pd.DataFrame({"id": [0, 1, 2], "label": ["old"] * 3, "keep": ["a", "b", "c"]}, index=index)
    before = original.copy()
    second_finished = asyncio.Event()
    completion_order: list[int] = []

    async def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        position = int(_prompt(messages))
        if position == 0:
            await second_finished.wait()
        completion_order.append(position)
        if position == 1:
            second_finished.set()
        return _answer({"label": position * 10, "new": str(position)})

    class Result(BaseModel):
        label: int
        new: str

    enricher = DataFrameEnricher(llm=FunctionModel(respond), max_concurrency=2)
    result = await enricher.enrich(original, record_type=Result, instruction="{{ id }}")

    assert completion_order[0] == 1
    assert result["label"].tolist() == [0, 10, 20]
    assert result["new"].tolist() == ["0", "1", "2"]
    assert_index_equal(result.index, before.index)
    assert_frame_equal(result[["id", "keep"]], before[["id", "keep"]])
    assert_frame_equal(original, before)
    assert list(result.columns) == ["id", "label", "keep", "new"]


@pytest.mark.parametrize("empty", [False, True])
async def test_typed_nullable_columns_and_empty_input(empty: bool) -> None:
    values: dict[str, Any] = {
        "text": "hello",
        "count": 2,
        "score": 1.5,
        "flag": True,
        "day": "2026-09-15",
        "at": "2026-09-15T12:30:00+00:00",
        "category": "a",
    }
    calls = 0

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        return _answer(values if _prompt(messages) == "0" else {})

    frame = pd.DataFrame({"row": [] if empty else [0, 1]})

    class Result(BaseModel):
        text: str | None = None
        count: int | None = None
        score: float | None = None
        flag: bool | None = None
        day: date | None = None
        at: datetime | None = None
        category: Literal["a", "b"] | None = None

    result = await DataFrameEnricher(llm=FunctionModel(respond)).enrich(
        frame, record_type=Result, instruction="{{ row }}"
    )

    assert calls == len(frame)
    assert result["count"].dtype == pd.Int64Dtype()
    assert result["score"].dtype == pd.Float64Dtype()
    assert result["flag"].dtype == pd.BooleanDtype()
    assert isinstance(result["text"].dtype, pd.StringDtype)
    assert result["day"].dtype == object and result["at"].dtype == object
    assert result["category"].cat.categories.tolist() == ["a", "b"]
    if not empty:
        assert result.iloc[1][list(Result.model_fields)].isna().all()
        assert result["day"].iloc[0] == date(2026, 9, 15)
        assert result["at"].iloc[0] == datetime.fromisoformat(values["at"])
        assert result["category"].iloc[0] == "a"


@pytest.mark.parametrize(
    "record_type",
    [
        {"x": str},
        BaseModel,
        RootModel[int],
        create_model("Nested", x=(Label, ...)),
        create_model("Array", x=(list[str], ...)),
        create_model("UnionColumn", x=(int | str, ...)),
    ],
)
async def test_rejects_unsupported_schemas_before_model_calls(record_type: Any) -> None:
    with pytest.raises((TypeError, ValueError)):
        await DataFrameEnricher(llm="test").enrich(
            pd.DataFrame({"text": ["hello"]}), record_type=record_type, instruction="read"
        )


@pytest.mark.parametrize("concurrency", [0, -1])
def test_rejects_nonpositive_concurrency(concurrency: int) -> None:
    with pytest.raises(ValueError, match="max_concurrency"):
        DataFrameEnricher(llm="test", max_concurrency=concurrency)


@pytest.mark.parametrize(
    "frame,instruction",
    [
        (pd.DataFrame([[1, 2]], columns=["x", "x"]), "task"),
        (pd.DataFrame({1: ["value"]}), "task"),
        (pd.DataFrame({"x": ["value"]}), "{{ missing | default('') }}"),
        (pd.DataFrame({"x": ["value"]}), "{{ broken"),
        (pd.DataFrame({"x": [{"name": "a"}, {}]}), "{{ x.name }}"),
    ],
)
async def test_invalid_input_fails_before_any_model_call(frame: pd.DataFrame, instruction: str) -> None:
    calls = 0

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        return _answer({"label": "unused"})

    enricher = DataFrameEnricher(llm=FunctionModel(respond))
    with pytest.raises(ValueError):
        await enricher.enrich(frame, record_type=Label, instruction=instruction)
    assert calls == 0


async def test_literal_validation_retries_before_returning_a_category() -> None:
    calls = 0

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        if calls > 1:
            assert any(isinstance(part, RetryPromptPart) for message in messages for part in message.parts)
        return _answer({"mode": "invalid" if calls == 1 else "remote"})

    enricher = DataFrameEnricher(llm=FunctionModel(respond))
    result = await enricher.enrich(
        pd.DataFrame({"text": ["Work from home"]}), record_type=Mode, instruction="{{ text }}"
    )
    assert result["mode"].tolist() == ["remote"]
    assert calls == 2


@pytest.mark.parametrize("abort", [False, True])
async def test_abort_and_exhausted_validation_raise_instead_of_returning_null(abort: bool) -> None:
    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if abort:
            return ModelResponse(parts=[ToolCallPart("abort_task", {"message": "missing source"})])
        return _answer({"count": "not an integer"})

    frame = pd.DataFrame({"text": ["example"]})
    enricher = DataFrameEnricher(llm=FunctionModel(respond))
    with pytest.raises(RuntimeError, match="row 1: .*" + ("missing source" if abort else "retries")):
        await enricher.enrich(frame, record_type=Count, instruction="{{ text }}")
    assert list(frame.columns) == ["text"]


@pytest.mark.parametrize("cancel", [False, True])
async def test_failure_and_cancellation_drain_workers_without_starting_remaining_rows(cancel: bool) -> None:
    started: list[int] = []
    finished: list[int] = []
    ready = asyncio.Event()
    never = asyncio.Event()

    async def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        row = int(_prompt(messages))
        started.append(row)
        if len(started) == 3:
            ready.set()
        try:
            await ready.wait()
            if row == 0 and not cancel:
                raise ValueError("model unavailable")
            await never.wait()
            return _answer({"value": row})
        finally:
            finished.append(row)

    frame = pd.DataFrame({"row": range(8)})
    before = frame.copy()
    enricher = DataFrameEnricher(llm=FunctionModel(respond), max_concurrency=3)
    async with asyncio.timeout(5):
        task = asyncio.create_task(enricher.enrich(frame, record_type=Value, instruction="{{ row }}"))
        if cancel:
            await ready.wait()
            task.cancel()
        with pytest.raises(asyncio.CancelledError if cancel else RuntimeError):
            await task
    assert sorted(started) == [0, 1, 2]
    assert sorted(finished) == [0, 1, 2]
    assert_frame_equal(frame, before)


async def test_concurrent_calls_share_limit_and_keep_results_separate() -> None:
    active = 0
    peak = 0
    ready = asyncio.Event()
    release = asyncio.Event()

    async def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal active, peak
        active += 1
        peak = max(active, peak)
        if active == 2:
            ready.set()
        try:
            await release.wait()
            field = next(iter(info.output_tools[0].parameters_json_schema["properties"]))
            value = int(_prompt(messages)) if field == "value" else _prompt(messages)
            return _answer({field: value})
        finally:
            active -= 1

    enricher = DataFrameEnricher(llm=FunctionModel(respond), max_concurrency=2)
    requests: list[tuple[int, type[BaseModel]]] = [(1, Value), (2, Label)]
    async with asyncio.timeout(5):
        tasks = [
            asyncio.create_task(
                enricher.enrich(pd.DataFrame({"row": [i] * 4}), record_type=record_type, instruction="{{ row }}")
            )
            for i, record_type in requests
        ]
        await ready.wait()
        release.set()
        first, second = await asyncio.gather(*tasks)
    assert peak == 2 and active == 0
    assert first["value"].tolist() == [1] * 4
    assert second["label"].tolist() == ["2"] * 4


async def test_constant_instruction_preserves_rows_without_input_columns() -> None:
    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return _answer({"value": 1})

    frame = pd.DataFrame(index=[4, 4])
    result = await DataFrameEnricher(llm=FunctionModel(respond)).enrich(
        frame, record_type=Value, instruction="Return 1"
    )
    assert result["value"].tolist() == [1, 1]
    assert_index_equal(result.index, frame.index)


async def test_schema_constraints_defaults_aliases_and_validators_are_preserved() -> None:
    class Job(BaseModel):
        years: int = Field(ge=0, alias="experience", description="Minimum years of experience")
        label: str = Field(default="default", exclude=True)
        note: str | None = None

        @field_validator("years")
        @classmethod
        def reject_unrealistic_experience(cls, value: int) -> int:
            if value > 80:
                raise ValueError("unrealistic experience")
            return value

        @field_serializer("years")
        def format_years(self, value: int) -> str:
            return f"{value} years"

    answers: list[dict[str, Any]] = [
        {},
        {"experience": None},
        {"experience": -1},
        {"experience": 100},
        {"experience": 2},
    ]
    calls = 0

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        schema = info.output_tools[0].parameters_json_schema
        assert schema["required"] == ["experience"]
        assert schema["properties"]["experience"]["description"] == "Minimum years of experience"
        # One invalid response per input row stays within the model's retry limit.
        row = int(_prompt(messages))
        retrying = any(isinstance(part, RetryPromptPart) for message in messages for part in message.parts)
        calls += 1
        return _answer(answers[-1] if retrying else answers[row])

    result = await DataFrameEnricher(llm=FunctionModel(respond)).enrich(
        pd.DataFrame({"row": range(4)}), record_type=Job, instruction="{{ row }}"
    )
    assert calls == 8
    assert result["years"].tolist() == [2] * 4
    assert result["label"].tolist() == ["default"] * 4
    assert result["note"].isna().all()
    assert "experience" not in result.columns


async def test_nullable_annotated_columns_and_enum_values() -> None:
    class WorkMode(Enum):
        REMOTE = "remote"
        ONSITE = "onsite"

    class Job(BaseModel):
        years: Annotated[int, Field(ge=0)] | None = None
        mode: WorkMode | None = None
        priority: Literal[1, 2] = 1

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        return _answer({"years": 2, "mode": "remote"})

    result = await DataFrameEnricher(llm=FunctionModel(respond)).enrich(
        pd.DataFrame(index=[0]), record_type=Job, instruction="Return a remote job"
    )
    assert result["years"].tolist() == [2]
    assert result["mode"].tolist() == ["remote"]
    assert result["mode"].cat.categories.tolist() == ["remote", "onsite"]
    assert result["priority"].tolist() == [1]
