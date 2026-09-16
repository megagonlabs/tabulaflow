"""Typed, concurrent row enrichment for DataFrames and SQL tools."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from types import UnionType
from typing import Annotated, Any, Literal, Union, get_args, get_origin

import jinja2
import jinja2.meta
import pandas as pd
from pydantic import BaseModel, Field
from pydantic_ai import AgentRunResult, NativeOutput, PromptedOutput, Tool, ToolOutput
from pydantic_ai.capabilities.abstract import AbstractCapability
from pydantic_ai.messages import UserContent
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings

from tabulaflow.agents.llm import make_agent
from tabulaflow.agents.media import inspect_inline_media, materialize_inline_media
from tabulaflow.agents.message_store import (
    MESSAGE_THRESHOLD_CHARS,
    MessageStore,
    MessageStoreCapability,
    ScopedMessageStore,
    make_snippet,
)
from tabulaflow.agents.tools.browser.tool import (
    BROWSER_TOOL_NAMES,
    SNAPSHOT_SNIPPET_THRESHOLD_CHARS,
    ReleaseBrowserBeforeFanout,
    WebBrowserTool,
    snapshot_snippet,
)
from tabulaflow.agents.tools.registry.run_query import RegistryRunQueryTool
from tabulaflow.data.registry import DataConnectorRegistry

_MAX_MEDIA_ITEMS_PER_ROW = 10
_MAX_MEDIA_BYTES_PER_ROW = 25 * 1024 * 1024
_JINJA_ENV = jinja2.Environment(undefined=jinja2.StrictUndefined)


@dataclass(frozen=True)
class TaskRow:
    values: dict[str, object]
    prompt: str | list[UserContent]


def _prepare_task_row(row_idx: int, row: dict[str, object], template: jinja2.Template) -> TaskRow:
    prompt_values = dict(row)
    media: list[UserContent] = []
    attached = 0
    total_bytes = 0
    for column, value in row.items():
        try:
            items = inspect_inline_media(value)
        except ValueError as exc:
            raise ValueError(
                f"input contains an invalid media collection in row {row_idx}, column {column!r}: {exc}"
            ) from exc
        if items is None:
            continue
        if attached + len(items) > _MAX_MEDIA_ITEMS_PER_ROW:
            raise ValueError(f"input contains more than {_MAX_MEDIA_ITEMS_PER_ROW} media items in row {row_idx}")
        descriptors: list[str] = []
        for item in items:
            try:
                content = materialize_inline_media(item.candidate, max_bytes=_MAX_MEDIA_BYTES_PER_ROW)
            except ValueError as exc:
                source = column if item.index is None else f"{column}[{item.index}]"
                raise ValueError(
                    f"input contains unusable binary data in row {row_idx}, column {source!r}: {exc}; "
                    "provide valid inline image/PDF bytes or omit the column"
                ) from exc
            if total_bytes + len(content.data) > _MAX_MEDIA_BYTES_PER_ROW:
                raise ValueError(
                    f"media in row {row_idx} exceeds the {_MAX_MEDIA_BYTES_PER_ROW}-byte total per-row limit"
                )
            attached += 1
            total_bytes += len(content.data)
            descriptors.append(f"[Media #{attached}: {content.media_type}, {len(content.data)} bytes]")
            source = column if item.index is None else f"{column}[{item.index}]"
            media.extend((f"Media #{attached} from column {source}:", content))
        prompt_values[column] = descriptors[0] if len(descriptors) == 1 else "[" + ", ".join(descriptors) + "]"
    try:
        prompt = template.render(prompt_values)
    except jinja2.TemplateError as exc:
        raise ValueError(f"cannot render instruction for row {row_idx}: {exc}") from exc
    return TaskRow(values=row, prompt=[prompt, *media] if media else prompt)


class AbortTask(BaseModel):
    """Terminal output indicating the task could not be completed."""

    message: str = Field(
        description="Reason the task cannot be completed. Be specific about the reason and what you need in order to complete the task."
    )


def _terminal_output_type(llm: str | Model, answer_model: type[BaseModel]) -> Any:
    """Build the provider-compatible success/abort output contract."""
    if isinstance(llm, str):
        is_anthropic = llm.startswith("anthropic:") or llm.startswith("google-cloud:claude")
        supports_native = False
        if is_anthropic:
            from pydantic_ai.profiles.anthropic import anthropic_model_profile

            profile = anthropic_model_profile(llm.split(":", 1)[1])
            supports_native = bool(profile and profile.get("supports_json_schema_output", False))
    else:
        is_anthropic = llm.system == "anthropic"
        supports_native = bool(llm.profile and llm.profile.get("supports_json_schema_output", False))

    outputs: list[Any] = [answer_model, AbortTask]
    if is_anthropic:
        output_cls: Any = NativeOutput if supports_native else PromptedOutput
        return output_cls(
            outputs,
            name="task_result",
            description="Return the requested record on success or AbortTask when the task cannot be completed.",
        )
    return [
        ToolOutput(
            answer_model,
            name="submit_answer",
            description="Submit your answer for this task. Calling this tool ends the task successfully.",
        ),
        ToolOutput(
            AbortTask,
            name="abort_task",
            description="Abort the task with a human-readable reason. Calling this tool ends the task.",
        ),
    ]


def prepare_rows(df: pd.DataFrame, instruction: str) -> list[TaskRow]:
    if not df.columns.is_unique or any(not isinstance(column, str) for column in df.columns):
        raise ValueError("input columns must have unique string names")
    try:
        parsed = _JINJA_ENV.parse(instruction)
    except jinja2.TemplateSyntaxError as exc:
        raise ValueError(f"invalid Jinja2 syntax in instruction: {exc}") from exc
    unknown = sorted(jinja2.meta.find_undeclared_variables(parsed) - set(df.columns))
    if unknown:
        raise ValueError(
            f"instruction references placeholders not in the input columns: {unknown}; "
            f"available columns: {list(df.columns)}"
        )
    template = _JINJA_ENV.from_string(instruction)
    records = df.to_dict(orient="records") if len(df.columns) else [{} for _ in range(len(df))]
    return [_prepare_task_row(i, row, template) for i, row in enumerate(records, start=1)]


@dataclass(frozen=True)
class RowResult:
    run_result: AgentRunResult[BaseModel] | None
    error: str | None


class RowRunner:
    """Run typed row agents; consumers own persistence and failure policy.

    Concurrency is shared across calls on one runner. Each row owns its browser
    and message scope; additional tools are supplied by the consumer.
    """

    def __init__(
        self,
        *,
        llm: str | Model,
        model_settings: ModelSettings | None = None,
        max_concurrency: int = 200,
        enable_browser_tools: bool = False,
        enable_run_query_tool: bool = False,
        registry: DataConnectorRegistry | None = None,
        message_store: MessageStore | None = None,
        truncate_messages: bool = False,
    ) -> None:
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be greater than 0")
        if enable_run_query_tool and registry is None:
            raise ValueError("enable_run_query_tool=True requires a registry")
        if truncate_messages and (message_store is None or registry is None):
            raise ValueError("message truncation requires a message store and registry")
        self._llm = llm
        self._model_settings = model_settings
        self._max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._enable_browser_tools = enable_browser_tools
        self._enable_run_query_tool = enable_run_query_tool
        self._registry = registry
        self._message_store = message_store
        self._truncate_messages = truncate_messages

    async def run(
        self,
        rows: list[TaskRow],
        *,
        record_type: type[BaseModel],
        on_result: Callable[[int, RowResult], Awaitable[None]],
        tools: Sequence[Tool] = (),
        fanout_tool_names: frozenset[str] = frozenset(),
        call_id: str | None = None,
    ) -> None:
        """Deliver each row's outcome as it completes and drain workers on exit."""
        if not rows:
            return
        call_id = call_id or uuid.uuid4().hex[:8]
        shared_tools = list(tools)
        if self._enable_run_query_tool or self._truncate_messages:
            assert self._registry is not None
            shared_tools.append(RegistryRunQueryTool(self._registry).as_pydantic_ai_tool())
        pending = iter(enumerate(rows))

        async def worker() -> None:
            for position, row in pending:
                async with self._semaphore:
                    scope = (
                        self._message_store.scoped(f"subagent:{call_id}:{position + 1}")
                        if self._message_store is not None
                        else None
                    )
                    try:
                        result = await self._run_agent(
                            row.prompt,
                            record_type=record_type,
                            tools=shared_tools,
                            fanout_tool_names=fanout_tool_names,
                            scope=scope,
                        )
                        if isinstance(result.output, AbortTask):
                            outcome = RowResult(result, f"AbortTask: {result.output.message}")
                        else:
                            outcome = RowResult(result, None)
                    except Exception as exc:
                        outcome = RowResult(None, f"{type(exc).__name__}: {exc}")
                    await on_result(position, outcome)

        workers = [asyncio.create_task(worker()) for _ in range(min(len(rows), self._max_concurrency))]
        try:
            await asyncio.gather(*workers)
        finally:
            for task in workers:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*workers, return_exceptions=True)

    async def _run_agent(
        self,
        prompt: str | list[UserContent],
        *,
        record_type: type[BaseModel],
        tools: Sequence[Tool],
        fanout_tool_names: frozenset[str],
        scope: ScopedMessageStore | None,
    ) -> AgentRunResult[BaseModel]:
        browser: WebBrowserTool | None = None
        try:
            row_tools: list[Tool] = []
            capabilities: list[AbstractCapability[Any]] = []
            if self._enable_browser_tools:
                browser = WebBrowserTool()
                row_tools.extend(browser.as_pydantic_ai_tools())
                capabilities.append(browser.lifecycle_capability())
                if fanout_tool_names:
                    capabilities.append(ReleaseBrowserBeforeFanout(browser, fanout_tool_names))
            row_tools.extend(tools)
            if scope is not None:
                capabilities.append(
                    MessageStoreCapability(
                        store=scope,
                        tool_allowlist=BROWSER_TOOL_NAMES,
                        truncate=self._truncate_messages,
                        snippet_fn=snapshot_snippet,
                        threshold_chars=SNAPSHOT_SNIPPET_THRESHOLD_CHARS,
                    )
                )
                if self._truncate_messages:
                    text = prompt if isinstance(prompt, str) else str(prompt[0])
                    message_id = await scope.add(kind="user_prompt", content=text)
                    if message_id is not None and len(text) > MESSAGE_THRESHOLD_CHARS:
                        snippet = make_snippet(message_id, text)
                        prompt = snippet if isinstance(prompt, str) else [snippet, *prompt[1:]]
            agent = make_agent(
                self._llm,
                tools=row_tools,
                capabilities=capabilities or None,
                output_type=_terminal_output_type(self._llm, record_type),
                model_settings=self._model_settings,
            )
            return await agent.run(prompt)
        finally:
            if browser is not None:
                await browser.close()


def _pandas_dtype(annotation: Any) -> str | pd.CategoricalDtype:
    origin = get_origin(annotation)
    if origin is Annotated:
        return _pandas_dtype(get_args(annotation)[0])
    if origin in (Union, UnionType):
        types = [arg for arg in get_args(annotation) if arg is not type(None)]
        if len(types) == 1:
            return _pandas_dtype(types[0])
    if annotation in (str, int, float, bool, date, datetime):
        return {str: "string", int: "Int64", float: "Float64", bool: "boolean"}.get(annotation, "object")
    if origin is Literal or (isinstance(annotation, type) and issubclass(annotation, Enum)):
        choices = get_args(annotation) if origin is Literal else tuple(member.value for member in annotation)
        values = [value for value in choices if value is not None]
        if all(isinstance(value, (str, int, float, bool)) for value in values):
            return pd.CategoricalDtype(categories=values)
    raise TypeError(f"unsupported column type {annotation!r}; use scalar types, Literal choices, or scalar enums")


class DataFrameEnricher:
    """Enrich DataFrame rows with typed fields using an LLM.

    Rows are processed concurrently using their supplied content and optional
    browser or database tools. Each row produces a record validated by the supplied
    Pydantic model, preserving required fields, defaults, constraints, and nullability.
    """

    def __init__(
        self,
        *,
        llm: str | Model = "openai-responses:gpt-5-mini",
        model_settings: ModelSettings | None = None,
        max_concurrency: int = 200,
        enable_browser_tools: bool = False,
        enable_run_query_tool: bool = False,
        registry: DataConnectorRegistry | None = None,
    ) -> None:
        """Initialize the enricher.

        Args:
            llm: LLM identifier or model object used for row enrichment.
            model_settings: Optional settings passed to each agent.
            max_concurrency: Maximum concurrent row tasks across all calls
                on this instance.
            enable_browser_tools: Give each row agent its own browser tools.
            enable_run_query_tool: Give row agents a tool to query and modify
                registered data sources. Requires ``registry``.
            registry: Data sources available to the optional query tool.

        Raises:
            ValueError: If concurrency is not positive or query tools lack a registry.
        """
        self._runner = RowRunner(
            llm=llm,
            model_settings=model_settings,
            max_concurrency=max_concurrency,
            enable_browser_tools=enable_browser_tools,
            enable_run_query_tool=enable_run_query_tool,
            registry=registry,
        )

    async def enrich(self, df: pd.DataFrame, *, record_type: type[BaseModel], instruction: str) -> pd.DataFrame:
        """Return a copy with the model's fields added or replaced as columns.

        Input order, index (including duplicate labels), and other columns are
        preserved. Scalar outputs use nullable pandas dtypes; dates and
        datetimes remain Python objects. Literal and enum outputs are categorical.

        Args:
            df: Input rows with unique string column names. Images and PDFs
                in supported inline forms are attached to the row's prompt.
            record_type: Pydantic model class defining a non-empty, flat record.
                Fields may use str, int, float, bool, date, datetime, scalar
                Literal choices or enums, and nullable forms of those types.
                Model field names become column names, regardless of aliases.
            instruction: Jinja2 template referencing input columns, such as
                ``"Classify this job: {{ description }}"``.

        Returns:
            A new DataFrame with one output row per input row. An empty input
            returns an empty frame with the declared output columns.

        Raises:
            TypeError: If ``record_type`` is not a Pydantic model class or contains
                unsupported column types.
            ValueError: If ``record_type`` is empty or a root model, or input
                columns, the template, or inline media are invalid.
            RuntimeError: If any agent fails or aborts. Pending row tasks are
                cancelled and awaited; the input DataFrame is never modified.
        """
        if not isinstance(record_type, type) or not issubclass(record_type, BaseModel):
            raise TypeError("record_type must be a Pydantic model class")
        if not record_type.model_fields or record_type.__pydantic_root_model__:
            raise ValueError("record_type must define a non-empty record")
        dtypes = {name: _pandas_dtype(field.annotation) for name, field in record_type.model_fields.items()}
        enriched = df.copy()
        rows = prepare_rows(enriched, instruction)
        outputs: dict[int, BaseModel] = {}

        async def collect(position: int, result: RowResult) -> None:
            if result.error is not None:
                raise RuntimeError(f"row {position + 1}: {result.error}")
            assert result.run_result is not None
            outputs[position] = result.run_result.output

        await self._runner.run(rows, record_type=record_type, on_result=collect)
        for name, dtype in dtypes.items():
            values = [getattr(outputs[position], name) for position in range(len(rows))]
            values = [value.value if isinstance(value, Enum) else value for value in values]
            enriched[name] = pd.Series(values, index=enriched.index, dtype=dtype)
        return enriched
