"""Typed, concurrent enrichment of DataFrame rows without a database."""

from __future__ import annotations

import asyncio
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
from pydantic_ai import Agent, AgentRunResult, NativeOutput, PromptedOutput, Tool, ToolOutput
from pydantic_ai.capabilities.abstract import AbstractCapability
from pydantic_ai.messages import UserContent
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings

from tabulaflow.agents.llm import make_agent
from tabulaflow.agents.media import inspect_inline_media, materialize_inline_media

_MAX_MEDIA_ITEMS_PER_ROW = 10
_MAX_MEDIA_BYTES_PER_ROW = 25 * 1024 * 1024
_JINJA_ENV = jinja2.Environment(undefined=jinja2.StrictUndefined)


@dataclass(frozen=True)
class _TaskRow:
    values: dict[str, object]
    prompt: str | list[UserContent]


def _prepare_task_row(row_idx: int, row: dict[str, object], template: jinja2.Template) -> _TaskRow:
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
    return _TaskRow(values=row, prompt=[prompt, *media] if media else prompt)


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


def _prepare_rows(df: pd.DataFrame, instruction: str) -> list[_TaskRow]:
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
class _RowResult:
    values: dict[str, Any] | None
    error: str | None
    run_result: AgentRunResult[Any] | None


class _RowRunner:
    """Run typed row tasks; consumers own persistence and failure policy."""

    def __init__(
        self,
        *,
        llm: str | Model,
        model_settings: ModelSettings | None,
        max_concurrency: int,
    ) -> None:
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be greater than 0")
        self._llm = llm
        self._model_settings = model_settings
        self._max_concurrency = max_concurrency
        self._semaphore = asyncio.Semaphore(max_concurrency)

    def create_agent(
        self,
        record_type: type[BaseModel],
        *,
        tools: Sequence[Tool] = (),
        capabilities: Sequence[AbstractCapability[Any]] = (),
    ) -> Agent[Any, Any]:
        return make_agent(
            self._llm,
            tools=tools,
            capabilities=capabilities or None,
            output_type=_terminal_output_type(self._llm, record_type),
            model_settings=self._model_settings,
        )

    async def run(
        self,
        rows: list[_TaskRow],
        *,
        record_type: type[BaseModel],
        on_result: Callable[[int, _RowResult], Awaitable[None]],
        run_agent: Callable[[int, str | list[UserContent]], Awaitable[AgentRunResult[Any]]] | None = None,
    ) -> None:
        if not rows:
            return
        agent = self.create_agent(record_type) if run_agent is None else None
        pending = iter(enumerate(rows))

        async def worker() -> None:
            for position, row in pending:
                async with self._semaphore:
                    try:
                        if run_agent is not None:
                            result = await run_agent(position, row.prompt)
                        else:
                            assert agent is not None
                            result = await agent.run(row.prompt)
                        if isinstance(result.output, AbortTask):
                            outcome = _RowResult(None, f"AbortTask: {result.output.message}", result)
                        else:
                            values = {name: getattr(result.output, name) for name in record_type.model_fields}
                            outcome = _RowResult(values, None, result)
                    except Exception as exc:
                        outcome = _RowResult(None, f"{type(exc).__name__}: {exc}", None)
                    await on_result(position, outcome)

        workers = [asyncio.create_task(worker()) for _ in range(min(len(rows), self._max_concurrency))]
        try:
            await asyncio.gather(*workers)
        finally:
            for task in workers:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*workers, return_exceptions=True)


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
    """Enrich DataFrame rows using a Pydantic model and an LLM.

    Each row produces a validated record. Required fields, defaults, constraints,
    and nullability come from the supplied model. No database or row key is needed.
    """

    def __init__(
        self,
        *,
        llm: str | Model = "openai-responses:gpt-5-mini",
        model_settings: ModelSettings | None = None,
        max_concurrency: int = 200,
    ) -> None:
        """Initialize the enricher.

        Args:
            llm: LLM identifier or model object used for row enrichment.
            model_settings: Optional settings passed to each agent.
            max_concurrency: Maximum concurrent row tasks across all calls
                on this instance.

        Raises:
            ValueError: If concurrency is not positive.
        """
        self._runner = _RowRunner(llm=llm, model_settings=model_settings, max_concurrency=max_concurrency)

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
        rows = _prepare_rows(enriched, instruction)
        outputs: list[dict[str, Any]] = [{} for _ in rows]

        async def collect(position: int, result: _RowResult) -> None:
            if result.error is not None:
                raise RuntimeError(f"row {position + 1}: {result.error}")
            assert result.values is not None
            outputs[position] = result.values

        await self._runner.run(rows, record_type=record_type, on_result=collect)
        for name, dtype in dtypes.items():
            values = [output[name] for output in outputs]
            values = [value.value if isinstance(value, Enum) else value for value in values]
            enriched[name] = pd.Series(values, index=enriched.index, dtype=dtype)
        return enriched
