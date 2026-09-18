"""Tests for standalone document extraction."""

import asyncio
from datetime import date
import io
from typing import Literal, assert_type

from PIL import Image
import pytest
from pydantic import BaseModel, Field, field_validator
from pydantic_ai import AgentRunResult
from pydantic_ai.messages import (
    BinaryContent,
    UserContent,
    UserPromptPart,
    ModelMessage,
    ModelResponse,
    ToolCallPart,
    RetryPromptPart,
)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pypdf import PdfWriter

from tabulaflow.agents.extraction import EntityExtractor
from tabulaflow.agents.extraction.extractor import _media_prompts
from tabulaflow.agents.media import select_pdf_pages


def _png() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (1, 1), "red").save(output, format="PNG")
    return output.getvalue()


def _pdf(pages: int) -> bytes:
    output = io.BytesIO()
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=10, height=10)
    writer.write(output)
    return output.getvalue()


class NamedRecord(BaseModel):
    name: str


async def test_entity_extractor_preserves_schema_validation_and_returns_models() -> None:
    class Product(BaseModel):
        name: str
        qty: int = Field(ge=1, description="Units available")
        launched: date | None = None
        category: Literal["food", "other"] = "other"

        @field_validator("name")
        @classmethod
        def uppercase(cls, value: str) -> str:
            return value.upper()

    calls = 0

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        tool = info.output_tools[0]
        schema = tool.parameters_json_schema["$defs"]["Product"]
        assert schema["required"] == ["name", "qty"]
        assert schema["properties"]["qty"]["description"] == "Units available"
        if calls == 2:
            assert any(isinstance(part, RetryPromptPart) for message in messages for part in message.parts)
        records = [
            {"name": "apple", "qty": 0 if calls == 1 else 2},
            {"name": "pear", "qty": 3, "launched": "2026-09-15"},
        ]
        return ModelResponse(parts=[ToolCallPart(tool.name, {"response": records})])

    extractor = EntityExtractor(llm=FunctionModel(respond))
    records = await extractor.extract(
        "Two apples and three pears.", record_type=Product, instruction="Extract products"
    )
    assert_type(records, list[Product])
    assert all(isinstance(record, Product) for record in records)
    assert records == [Product(name="apple", qty=2), Product(name="pear", qty=3, launched=date(2026, 9, 15))]
    assert records[0].name == "APPLE" and records[0].category == "other"
    assert calls == 2


async def test_entity_extractor_rejects_non_model_schema() -> None:
    with pytest.raises(TypeError, match="Pydantic model class"):
        await EntityExtractor(llm="test").extract("text", record_type={"name": str}, instruction="read")  # type: ignore[arg-type]


@pytest.mark.parametrize("content", ["   ", []])
async def test_empty_document_needs_no_model_request(content: str | list[BinaryContent]) -> None:
    assert await EntityExtractor().extract(content, record_type=NamedRecord, instruction="Extract names") == []


async def test_extractor_concurrent_schemas_share_limit_without_mixing_results() -> None:
    class CountRecord(BaseModel):
        count: int

    active = 0
    peak = 0
    ready = asyncio.Event()
    release = asyncio.Event()

    async def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal active, peak
        active += 1
        peak = max(peak, active)
        if active == 2:
            ready.set()
        try:
            await release.wait()
            tool = info.output_tools[0]
            records: list[dict[str, object]] = (
                [{"name": "Alice"}] if "NamedRecord" in tool.parameters_json_schema["$defs"] else [{"count": 1}]
            )
            return ModelResponse(parts=[ToolCallPart(tool.name, {"response": records})])
        finally:
            active -= 1

    extractor = EntityExtractor(llm=FunctionModel(respond), max_concurrency=2, chunk_target=20, chunk_max=40)
    content = "# First\n\nAlice appears here.\n\n# Second\n\nBob appears here."
    async with asyncio.timeout(5):
        names_task = asyncio.create_task(extractor.extract(content, record_type=NamedRecord, instruction="Read names"))
        counts_task = asyncio.create_task(
            extractor.extract(content, record_type=CountRecord, instruction="Count names")
        )
        await ready.wait()
        release.set()
        names, counts = await asyncio.gather(names_task, counts_task)
    assert peak == 2 and active == 0
    assert len(names) > 1 and len(counts) > 1
    assert all(isinstance(record, NamedRecord) and record.name == "Alice" for record in names)
    assert all(isinstance(record, CountRecord) and record.count == 1 for record in counts)


async def test_chunk_callback_exposes_typed_results_in_completion_order() -> None:
    release_first = asyncio.Event()
    completed: list[tuple[int, AgentRunResult[list[NamedRecord]]]] = []

    async def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        prompt = next(
            part.content for message in messages for part in message.parts if isinstance(part, UserPromptPart)
        )
        assert isinstance(prompt, str)
        records = []
        if "Alice appears here." in prompt:
            await release_first.wait()
            records = [{"name": "Alice"}]
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"response": records})])

    def on_chunk_complete(index: int, result: AgentRunResult[list[NamedRecord]]) -> None:
        completed.append((index, result))
        if index == 2:
            release_first.set()

    extractor = EntityExtractor(llm=FunctionModel(respond), chunk_target=20, chunk_max=40)
    async with asyncio.timeout(5):
        records = await extractor.extract(
            "# First\n\nAlice appears here.\n\n# Second\n\nNobody appears here.",
            record_type=NamedRecord,
            instruction="Read names",
            on_chunk_complete=on_chunk_complete,
        )

    assert [index for index, _ in completed] == [2, 1]
    assert completed[0][1].output == []
    assert records == [NamedRecord(name="Alice")]
    assert records[0] is completed[1][1].output[0]
    assert all(result.all_messages() and result.usage.requests == 1 for _, result in completed)


@pytest.mark.parametrize("failure", ["model", "callback", "cancel"])
async def test_extractor_failure_and_cancellation_drain_active_chunks(failure: str) -> None:
    ready = asyncio.Event()
    never = asyncio.Event()
    active = 0
    calls = 0

    async def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal active, calls
        calls += 1
        first = calls == 1
        active += 1
        if active == 2:
            ready.set()
        try:
            await ready.wait()
            if first and failure == "model":
                raise RuntimeError("source unavailable")
            if first and failure == "callback":
                return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"response": []})])
            await never.wait()
            raise AssertionError("cancelled request resumed")
        finally:
            active -= 1

    extractor = EntityExtractor(llm=FunctionModel(respond), max_concurrency=2, chunk_target=20, chunk_max=40)
    content = "# First\n\nAlice appears here.\n\n# Second\n\nBob appears here."

    def on_chunk_complete(index: int, result: AgentRunResult[list[NamedRecord]]) -> None:
        raise RuntimeError("callback failed")

    async with asyncio.timeout(5):
        task = asyncio.create_task(
            extractor.extract(
                content, record_type=NamedRecord, instruction="Read names", on_chunk_complete=on_chunk_complete
            )
        )
        if failure == "cancel":
            await ready.wait()
            task.cancel()
        with pytest.raises(asyncio.CancelledError if failure == "cancel" else RuntimeError):
            await task
    assert calls == 2 and active == 0


def test_entity_extractor_splits_pdfs_into_page_batches() -> None:
    prompts = _media_prompts(
        BinaryContent(data=_pdf(41), media_type="application/pdf"),
        "Extract every name.",
        None,
    )

    assert len(prompts) == 3
    media = [prompt[1] for prompt in prompts]
    assert all(isinstance(item, BinaryContent) for item in media)
    assert [select_pdf_pages(item.data).total_pages for item in media if isinstance(item, BinaryContent)] == [20, 20, 1]
    assert "PDF pages 1-20 of 41" in str(prompts[0][0])
    assert "PDF pages 41-41 of 41" in str(prompts[2][0])


async def test_entity_extractor_processes_ordered_mixed_media_collection() -> None:
    prompts: list[list[UserContent]] = []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        prompt = next(
            part.content for message in messages for part in message.parts if isinstance(part, UserPromptPart)
        )
        assert not isinstance(prompt, str)
        prompts.append(list(prompt))
        name = "image" if "Media item 1 of 2" in str(prompt[0]) else "pdf"
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"response": [{"name": name}]})])

    extractor = EntityExtractor(llm=FunctionModel(respond))

    records = await extractor.extract(
        [
            BinaryContent(data=_png(), media_type="image/png"),
            BinaryContent(data=_pdf(1), media_type="application/pdf"),
        ],
        record_type=NamedRecord,
        instruction="Extract every name.",
    )

    assert len(prompts) == 2
    assert {
        (item, prompt[1].media_type)
        for prompt in prompts
        if isinstance(prompt[1], BinaryContent)
        for item in ("Media item 1 of 2", "Media item 2 of 2")
        if item in str(prompt[0])
    } == {
        ("Media item 1 of 2", "image/png"),
        ("Media item 2 of 2", "application/pdf"),
    }
    assert records == [NamedRecord(name="image"), NamedRecord(name="pdf")]
