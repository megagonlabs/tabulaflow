import copy
import datetime
from decimal import Decimal
from enum import Enum
import json
import os
import re
import litellm
from pydantic import BaseModel, Field, field_serializer, model_validator, AfterValidator, ConfigDict, field_validator
from pydantic.types import StringConstraints
import pydantic_ai
from typing import Any, Literal, Annotated, TypeAlias, Union, get_args
import pandas as pd
import logging
import math
import itertools
from mintq.config import config

logger = logging.getLogger(__name__)

NumericOrNull: TypeAlias = Union[float, int, None]


class ForeignKeySchema(BaseModel):
    columns: list[str]
    foreign_schema_name: str | None = None
    foreign_table: str
    foreign_columns: list[str]


class SQLColumnSchema(BaseModel):
    name: str
    dtype: str
    description: str | None = None
    """Concise description of the column"""
    detailed_description_markdown: str | None = None
    """Markdown-formatted detailed description of the column"""
    not_used: bool = False
    """Indicates that the column contains no valid data or has been explicitly marked as not useful"""
    nullable: bool
    null_ratio: float
    num_unique: int | None  # Only for text or integer columns
    unique_ratio: float | None  # Only for text or integer columns
    examples: list[Any]
    primary_key_type: Literal["single", "composite"] | None = None
    foreign_keys: list[ForeignKeySchema] = Field(default_factory=list)  # Includes composite foreign keys


class SQLTableSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    name_description: str | None = None
    """Used for describing the merged table name in the compressed schema (e.g. "YYYYMMDD from 20200101 to 20200102")"""
    original_names: list[str] | None = None
    """Used for recording the original table names in the compressed schema (e.g. "20200101, 20200102")"""
    schema_name: str | None = None
    description: str | None = None
    is_view: bool
    columns: list[SQLColumnSchema]
    primary_key: list[str]
    num_rows: int
    foreign_keys: list[ForeignKeySchema]
    sampled_df: pd.DataFrame

    @field_serializer("sampled_df", when_used="always")
    def serialize_df(self, df: pd.DataFrame | None) -> dict[str, Any] | None:
        if df is None:
            return None
        return {
            "schema": {
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            },
            "data": df.to_dict(orient="records"),
        }

    @field_validator("sampled_df", mode="before")
    @classmethod
    def deserialize_df(cls, v: dict[str, Any] | pd.DataFrame) -> pd.DataFrame:
        if isinstance(v, pd.DataFrame):
            return v
        dtypes = v["schema"]["dtypes"]
        df = pd.DataFrame(v["data"], columns=list(dtypes.keys()))
        df = df.astype(dtypes)
        return df


class ColumnRef(BaseModel):
    schema_name: str | None = None
    table_name: str
    column_name: str


class TableRef(BaseModel):
    schema_name: str | None = None
    table_name: str


class SQLSchema(BaseModel):
    name: str
    tables: list[SQLTableSchema]

    def num_total_columns(self) -> int:
        return sum(len(table.columns) for table in self.tables)

    def get_all_table_refs(self) -> list[TableRef]:
        return [TableRef(schema_name=table.schema_name, table_name=table.name) for table in self.tables]

    def get_table_by_ref(self, table_ref: TableRef) -> SQLTableSchema:
        for table in self.tables:
            if table.schema_name == table_ref.schema_name and table.name == table_ref.table_name:
                return table
        raise ValueError(f"Table {table_ref.table_name} not found.")

    def get_all_column_refs(self) -> list[ColumnRef]:
        return [
            ColumnRef(schema_name=table.schema_name, table_name=table.name, column_name=column.name)
            for table in self.tables
            for column in table.columns
        ]

    def get_column_by_ref(self, column_ref: ColumnRef) -> SQLColumnSchema:
        for table in self.tables:
            if table.schema_name == column_ref.schema_name and table.name == column_ref.table_name:
                for column in table.columns:
                    if column.name == column_ref.column_name:
                        return column
        raise ValueError(f"Column {column_ref.column_name} not found in table {column_ref.table_name}.")

    def get_pk_column_refs(self) -> list[ColumnRef]:
        return [
            ColumnRef(schema_name=table.schema_name, table_name=table.name, column_name=column.name)
            for table in self.tables
            for column in table.columns
            if column.primary_key_type is not None
        ]

    def get_fk_column_refs(self) -> list[ColumnRef]:
        """Get columns involved in foreign key relationships (both outgoing and incoming)."""
        result: list[ColumnRef] = []
        seen: set[tuple[str | None, str, str]] = set()

        for table in self.tables:
            for fk in table.foreign_keys:
                # Outgoing FK columns
                for col in fk.columns:
                    key = (table.schema_name, table.name, col)
                    if key not in seen:
                        seen.add(key)
                        result.append(ColumnRef(schema_name=table.schema_name, table_name=table.name, column_name=col))
                # Incoming FK columns
                for col in fk.foreign_columns:
                    key = (fk.foreign_schema_name, fk.foreign_table, col)
                    if key not in seen:
                        seen.add(key)
                        result.append(
                            ColumnRef(schema_name=fk.foreign_schema_name, table_name=fk.foreign_table, column_name=col)
                        )

        return result

    def trim(self, column_refs: list[ColumnRef], case_insensitive: bool = True, keep_pk: bool = True) -> "SQLSchema":
        schema = copy.deepcopy(self)

        def normalize(s: str | None) -> str | None:
            return s.lower() if s is not None and case_insensitive else s

        column_ref_set = {
            (normalize(c.schema_name), normalize(c.table_name), normalize(c.column_name)) for c in column_refs
        }
        table_ref_set = {(normalize(t.schema_name), normalize(t.table_name)) for t in column_refs}

        for table in schema.tables:
            new_columns = []
            for column in table.columns:
                if (normalize(table.schema_name), normalize(table.name), normalize(column.name)) in column_ref_set:
                    new_columns.append(column)
                elif (
                    keep_pk
                    and column.primary_key_type
                    and (normalize(table.schema_name), normalize(table.name)) in table_ref_set
                ):
                    new_columns.append(column)
            table.columns = new_columns

            # Update sampled_df to only include remaining columns
            remaining_col_names = [col.name for col in table.columns]
            cols_to_keep = [c for c in remaining_col_names if c in table.sampled_df.columns]
            if cols_to_keep:
                table.sampled_df = table.sampled_df[cols_to_keep]
            else:
                table.sampled_df = pd.DataFrame()

        schema.tables = [table for table in schema.tables if table.columns]
        return schema


class SystemMessage(BaseModel):
    role: Literal["system"] = "system"
    content: str


class UserMessage(BaseModel):
    role: Literal["user"] = "user"
    content: str


class ToolCall(BaseModel):
    tool_call_id: str
    name: str
    arguments: dict[str, Any] | None
    """arguments is None means the arguments generated by LLM is not a valid JSON string"""


class AssistantMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    thinking: str | None = None
    content: str
    tool_calls: list[ToolCall] = Field(default_factory=list)


class ToolResponse(BaseModel):
    role: Literal["tool"] = "tool"
    tool_call_id: str
    response: str
    is_retry_prompt: bool = False
    """True if the response is a automatic retry prompt from Pydantic AI"""


Message = Annotated[
    Union[AssistantMessage, ToolResponse, UserMessage, SystemMessage],
    Field(discriminator="role"),
]


class Trajectory(BaseModel):
    id: str = "TRJY"
    messages: list[Message]

    @classmethod
    def from_pydantic_ai_messages(
        cls, messages: list[pydantic_ai.messages.ModelMessage], id: str = "TRJY"
    ) -> "Trajectory":
        trajectory = cls(messages=[], id=id)
        if not messages:
            return trajectory

        if messages[0].kind == "request" and messages[0].instructions:
            trajectory.messages.append(SystemMessage(content=messages[0].instructions))
        for msg in messages:
            if msg.kind == "request":
                for part in msg.parts:
                    if part.part_kind == "system-prompt":
                        trajectory.messages.append(SystemMessage(content=part.content))
                    elif part.part_kind == "user-prompt":
                        if not isinstance(part.content, str):
                            raise ValueError(f"Only string is supported for user prompt, got {type(part.content)}")
                        trajectory.messages.append(UserMessage(content=part.content))
                    elif part.part_kind == "tool-return":
                        if not isinstance(part.content, str):
                            raise ValueError(f"Tool return is not a string: {part.content}")
                        trajectory.messages.append(ToolResponse(response=part.content, tool_call_id=part.tool_call_id))
                    elif part.part_kind == "retry-prompt":
                        trajectory.messages.append(
                            ToolResponse(
                                response=str(part.content), tool_call_id=part.tool_call_id, is_retry_prompt=True
                            )
                        )
                    else:
                        raise ValueError(f"Unknown message part type: {part.part_kind}")
            elif msg.kind == "response":
                new_msg = AssistantMessage(content="", tool_calls=[])
                for part in msg.parts:  # type: ignore
                    if part.part_kind == "text":  # type: ignore
                        new_msg.content += part.content
                    elif part.part_kind == "tool-call":  # type: ignore
                        arguments = part.args
                        if isinstance(arguments, str):
                            try:
                                arguments = json.loads(arguments)
                            except json.JSONDecodeError:
                                arguments = None
                        new_msg.tool_calls.append(
                            ToolCall(tool_call_id=part.tool_call_id, name=part.tool_name, arguments=arguments)
                        )
                    elif part.part_kind == "thinking":  # type: ignore
                        if not new_msg.thinking:
                            new_msg.thinking = part.content
                        else:
                            new_msg.thinking += "\n\n" + part.content
                    else:
                        raise ValueError(f"Unknown message part type: {part.part_kind}")
                trajectory.messages.append(new_msg)
            else:
                raise ValueError(f"Unknown message type: {msg.kind}")
        return cls.model_validate(trajectory.model_dump())

    def to_readable(self) -> str:
        formatted = []
        for msg in self.messages:
            if msg.role == "system":
                formatted.append(f'<message role="system">\n{msg.content}\n</message>')
            elif msg.role == "user":
                formatted.append(f'<message role="user">\n{msg.content}\n</message>')
            elif msg.role == "assistant":
                s = '<message role="assistant">\n'
                if msg.thinking:
                    s += f"<thinking>\n{msg.thinking}\n</thinking>\n"
                if msg.content:
                    try:
                        content = json.loads(msg.content)
                        content = json.dumps(content, indent=2)
                    except Exception:
                        content = msg.content
                    s += f"{content}\n"
                for tool_call in msg.tool_calls:
                    s += f'<function name="{tool_call.name}">\n'
                    if tool_call.arguments is None:
                        s += "ARGUMENTS IS NOT A VALID JSON STRING\n"
                    else:
                        for key, value in tool_call.arguments.items():
                            if isinstance(value, (list, dict)):
                                value = json.dumps(value, indent=2)
                            else:
                                value = str(value)
                            s += f'<arg name="{key}">'
                            s += f"\n{value}\n" if "\n" in value else value
                            s += "</arg>\n"
                        s += "</function>\n"
                s += "</message>"
                formatted.append(s)
            elif msg.role == "tool":
                formatted.append(f'<message role="tool">\n{msg.response}\n</message>')
        res = "<trajectory>\n" + "\n\n\n".join(formatted) + "\n</trajectory>"
        return f"----- START OF TRAJECTORY `{self.id}` -----\n{res}\n----- END OF TRAJECTORY -----"

    def to_markdown(self) -> str:
        lines = [f"### Trajectory `{self.id}`"]

        index_lines = ["\n**Preview:**"]
        for i, msg in enumerate(self.messages, 1):
            anchor = f"msg-{self.id}-{i}"
            if msg.role == "system":
                preview = msg.content[:50].replace("\n", " ") + ("..." if len(msg.content) > 50 else "")
                index_lines.append(f"- [{i}. System](#{anchor}): {preview}")
            elif msg.role == "user":
                preview = msg.content[:50].replace("\n", " ") + ("..." if len(msg.content) > 50 else "")
                index_lines.append(f"- [{i}. User](#{anchor}): {preview}")
            elif msg.role == "assistant":
                if msg.tool_calls:
                    tool_names = ", ".join(f"`{tc.name}`" for tc in msg.tool_calls)
                    index_lines.append(f"- [{i}. Assistant](#{anchor}): {tool_names}")
                else:
                    preview = msg.content[:50].replace("\n", " ") + ("..." if len(msg.content) > 50 else "")
                    index_lines.append(f"- [{i}. Assistant](#{anchor}): {preview}")
            elif msg.role == "tool":
                preview = msg.response[:50].replace("\n", " ") + ("..." if len(msg.response) > 50 else "")
                index_lines.append(f"- [{i}. Tool](#{anchor}): {preview}")
        lines.extend(index_lines)
        lines.append("")

        # Build message sections with anchors
        for i, msg in enumerate(self.messages, 1):
            anchor = f"msg-{self.id}-{i}"
            if msg.role == "system":
                lines.append(f'\n<a id="{anchor}"></a>\n\n**[{i}] System:**\n')
                lines.append(f"````\n{msg.content}\n````")
            elif msg.role == "user":
                lines.append(f'\n<a id="{anchor}"></a>\n\n**[{i}] User:**\n')
                lines.append(f"````\n{msg.content}\n````")
            elif msg.role == "assistant":
                lines.append(f'\n<a id="{anchor}"></a>\n\n**[{i}] Assistant:**\n')
                s = ""
                if msg.thinking:
                    s += f"<thinking>\n{msg.thinking}\n</thinking>\n"
                if msg.content:
                    try:
                        content = json.loads(msg.content)
                        content = json.dumps(content, indent=2)
                    except Exception:
                        content = msg.content
                    s += f"{content}\n"
                for tool_call in msg.tool_calls:
                    s += f'<function name="{tool_call.name}">\n'
                    if tool_call.arguments is None:
                        s += "ARGUMENTS IS NOT A VALID JSON STRING\n"
                    else:
                        for key, value in tool_call.arguments.items():
                            if isinstance(value, (list, dict)):
                                value = json.dumps(value, indent=2)
                            else:
                                value = str(value)
                            s += f'<arg name="{key}">'
                            s += f"\n{value}\n" if "\n" in value else value
                            s += "</arg>\n"
                    s += "</function>\n"
                lines.append(f"````\n{s.strip()}\n````")
            elif msg.role == "tool":
                lines.append(f'\n<a id="{anchor}"></a>\n\n**[{i}] Tool:**\n')
                lines.append(f"````\n{msg.response}\n````")
        return "\n".join(lines)


PROVIDER_MAPPINGS = {
    "openai-responses": "openai",
    "fireworks": "fireworks_ai",
    "google-vertex": "vertex_ai",
    "together": "together_ai",
}


def pydantic_ai_model_to_litellm_model(llm: str) -> str:
    provider, model = llm.split(":")
    provider = PROVIDER_MAPPINGS.get(provider, provider)
    return f"{provider}/{model}"


def compute_api_cost(llm: str, input_tokens: int, output_tokens: int, api_requests: int = 1) -> Decimal:
    # Note: We found litellm to be more accurate than genai-prices
    # try:
    #     provider, model = llm.split(":")
    #     price_data = calc_price(
    #         pydantic_ai.usage.RunUsage(
    #             requests=api_requests,
    #             input_tokens=input_tokens,
    #             output_tokens=output_tokens,
    #         ),
    #         model_ref=model,
    #         provider_id=provider,
    #     )
    #     return price_data.total_price
    # except Exception:
    #     pass

    try:
        input_cost, output_cost = litellm.cost_per_token(  # type: ignore
            model=pydantic_ai_model_to_litellm_model(llm),
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
        )
        return Decimal(round(input_cost + output_cost, 8))
    except Exception:
        pass

    logger.info(f"Unable to calculate API cost for {llm}, setting to 0.0")
    return Decimal(0)


class Usage(BaseModel):
    llm: str | Literal["MULTI"] | None
    api_requests: int
    input_tokens: int
    output_tokens: int
    api_cost_usd: Decimal

    def __add__(self, other: "Usage") -> "Usage":
        if self.llm is None:
            llm = other.llm
        elif other.llm is None:
            llm = self.llm
        elif self.llm == other.llm:
            llm = self.llm
        else:
            llm = "MULTI"

        return Usage(
            llm=llm,
            api_requests=self.api_requests + other.api_requests,
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            api_cost_usd=self.api_cost_usd + other.api_cost_usd,
        )

    @classmethod
    def create(
        cls,
        llm: str | None = None,
        api_requests: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        api_cost_usd: float | Decimal | None = None,
    ) -> "Usage":
        if api_cost_usd is None:
            api_cost_usd = compute_api_cost(llm, input_tokens, output_tokens, api_requests)

        elif isinstance(api_cost_usd, float):
            api_cost_usd = Decimal(api_cost_usd)
        return cls(
            api_requests=api_requests,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            api_cost_usd=api_cost_usd,
            llm=llm,
        )

    @classmethod
    def from_pydantic_ai_usage(
        cls, usage: pydantic_ai.usage.RunUsage | pydantic_ai.usage.RequestUsage, llm: str
    ) -> "Usage":
        if isinstance(usage, pydantic_ai.usage.RunUsage):
            return cls.create(
                llm=llm,
                api_requests=usage.requests,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
            )
        else:
            return cls.create(
                llm=llm,
                api_requests=1,
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
            )


class ErrorInfo(BaseModel):
    exc_type: str
    message: str


class ExecResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    df: pd.DataFrame | None
    df_is_truncated: bool = False
    """True if the df is truncated, e.g. when the result is too large"""
    error: ErrorInfo | None = None
    latency_seconds: float | None = None

    @field_serializer("df", when_used="always")
    def serialize_df(self, df: pd.DataFrame | None) -> dict[str, Any] | None:
        if df is None:
            return None
        return {
            "schema": {
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
            },
            "data": df.to_dict(orient="records"),
        }

    @field_validator("df", mode="before")
    @classmethod
    def deserialize_df(cls, v: dict[str, Any] | pd.DataFrame | None) -> pd.DataFrame:
        if v is None or isinstance(v, pd.DataFrame):
            return v
        dtypes = v["schema"]["dtypes"]
        df = pd.DataFrame(v["data"], columns=list(dtypes.keys()))
        df = df.astype(dtypes)
        return df

    @model_validator(mode="after")
    def truncate_df(self) -> "ExecResult":
        if config.df_max_rows and self.df is not None and len(self.df) > config.df_max_rows:
            logger.warning(f"Truncated df from {len(self.df)} to {config.df_max_rows} rows")
            self.df = self.df.head(config.df_max_rows)
            self.df_is_truncated = True
        return self

    @model_validator(mode="after")
    def validate_df_or_error(self) -> "ExecResult":
        if self.df is None and self.error is None or self.df is not None and self.error is not None:
            raise ValueError("ExecResult must have either df or error, but not both")
        return self

    def to_readable(self) -> str:
        if self.df is None:
            res = f"(query failed: {self.error})"
        else:
            df = self.df
            if len(df) > 10:
                df = pd.concat([df.head(5), df.tail(5)], ignore_index=True)
                lines = df.to_string(index=False).split("\n")
                assert len(lines) == 11
                res = "\n".join(lines[:6] + ["... TRUNCATED ..."] + lines[6:])
            else:
                res = df.to_string(index=False)
        return f"/* EXEC RESULT\n{res}\n*/"

    def to_markdown(self) -> str:
        if self.df is None:
            return f"**Error:** {self.error.exc_type}: {self.error.message}" if self.error else "**Error:** Unknown"
        df = self.df
        truncated = False
        if len(df) > 10:
            df = pd.concat([df.head(5), df.tail(5)], ignore_index=True)
            truncated = True
        result = df.to_markdown(index=False)
        if truncated:
            result += f"\n\n*... truncated ({len(self.df)} rows total)*"
        return result  # type: ignore


class GoldQuery(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = "GQRY"
    query: str | None
    """In Spider2, some gold queries are not available, so we allow it to be None"""
    parameter_names: list[str] = Field(default_factory=list)
    parameter_values: dict[str, Any] = Field(default_factory=dict)
    """If `parameter_names` is not empty and `parameter_values` is empty, the query is parameterized."""
    exec_result: ExecResult | None = None
    other_exec_results: list[ExecResult] = Field(default_factory=list)
    """Some queries have multiple exec results (usually caused by argmax with ties), which is common in Spider2"""
    required_columns: list[int] | None = None
    """Columns that must be present in the result, None means all columns must be present"""
    required_sorted: bool = False
    """True if row order matters"""
    extra_info: dict[str, Any] = Field(default_factory=dict)

    @property
    def all_exec_results(self) -> list[ExecResult]:
        return ([self.exec_result] if self.exec_result is not None else []) + self.other_exec_results

    def to_directory(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        if self.exec_result is not None and self.exec_result.df is not None:
            self.exec_result.df.to_csv(os.path.join(directory, f"{self.id}.csv"), index=False)
        for i, exec_result in enumerate(self.other_exec_results):
            if exec_result.df is not None:
                exec_result.df.to_csv(os.path.join(directory, f"{self.id}_other_{i}.csv"), index=False)

    def to_readable(self) -> str:
        header = self.model_dump_json(indent=2, exclude={"query", "exec_result", "other_exec_results"})
        res = f"/*\n{header}\n*/\n{self.query}"
        res += "".join(f"\n{exec_result.to_readable()}" for exec_result in self.all_exec_results)
        return f"----- START OF GOLD QUERY `{self.id}` -----\n{res}\n----- END OF GOLD QUERY -----"

    def to_markdown(self, heading_level: int = 2) -> str:
        h = "#" * heading_level
        lines = [f"{h} Gold Query"]
        if self.query:
            lines.append("\n```sql")
            lines.append(self.query)
            lines.append("```")
        for i, exec_result in enumerate(self.all_exec_results):
            label = "Execution Result" if i == 0 else f"Alt Execution Result {i}"
            lines.append(f"\n**{label}:**\n")
            lines.append(exec_result.to_markdown())
        return "\n".join(lines)


class PredQuery(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: str = "PQRY"
    query: str
    parameter_names: list[str] = Field(default_factory=list)
    parameter_values: dict[str, Any] = Field(default_factory=dict)
    """If `parameter_names` is not empty and `parameter_values` is empty, the query is parameterized."""
    exec_result: ExecResult | None = None

    def to_directory(self, directory: str) -> None:
        os.makedirs(directory, exist_ok=True)
        if self.exec_result is not None and self.exec_result.df is not None:
            self.exec_result.df.to_csv(os.path.join(directory, f"{self.id}.csv"), index=False)

    def to_readable(self) -> str:
        header = self.model_dump_json(indent=2, exclude={"query", "exec_result"})
        res = f"/*\n{header}\n*/\n{self.query}"
        if self.exec_result is not None:
            res += f"\n{self.exec_result.to_readable()}"
        return f"----- START OF PRED QUERY `{self.id}` -----\n{res}\n----- END OF PRED QUERY -----"

    def to_markdown(self, heading_level: int = 2) -> str:
        h = "#" * heading_level
        lines = [f"{h} Pred Query"]
        lines.append("\n```sql")
        lines.append(self.query)
        lines.append("```")
        if self.exec_result is not None:
            lines.append("\n**Execution Result:**\n")
            lines.append(self.exec_result.to_markdown())
        return "\n".join(lines)


def is_id_unique(objs: list[Any]) -> list[Any]:
    ids = [obj.id for obj in objs]
    if len(ids) != len(set(ids)):
        raise ValueError(f"IDs of {type(objs[0]).__name__} are not unique.")
    return objs


class CSVSummaryRow(BaseModel):
    qid: str
    db: str
    question: str
    question_instructions: str | None = None
    gold_query: str | None = None
    pred_query: str | None = None
    gold_exec_result: str | None = None
    pred_exec_result: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)

    def fields(self) -> list[str]:
        return list(CSVSummaryRow.model_fields.keys())[:-1] + list(self.metrics.keys())

    def data(self) -> list[Any]:
        return list(self.model_dump().values())[:-1] + list(self.metrics.values())


class SimpleNL2QTask(BaseModel):
    task_type: Literal["simple"] = "simple"
    qid: str
    language: str
    db: str
    question: str
    question_instructions: str | None = None
    """Instructions that apply to this question only."""
    dataset_instructions: str | None = None
    """Instructions (e.g. for formatting) that apply to all questions in the dataset."""
    evidence: str | None = None
    gold_query: GoldQuery
    extra_info: dict[str, Any] = {}

    def to_directory(self, directory: str) -> None:
        return _task_to_directory(self, directory)

    def to_readable(self) -> str:
        return _task_to_readable(self)

    def to_markdown(self, heading_level: int = 1) -> str:
        return _task_to_markdown(self, heading_level)


class ExtraPredInfo(BaseModel):
    linked_schema: list[ColumnRef] | None = None
    raw_pred_query: PredQuery | None = None
    """If your method includes a postprocessing step, this field can store the raw predicted query before postprocessing to analyze its impact. The raw_pred_*_ex metrics evaluate these raw predictions."""
    other: dict[str, Any] = Field(default_factory=dict)


class SimpleNL2QTaskOutput(SimpleNL2QTask):
    output_type: Literal["simple"] = "simple"
    pred_query: PredQuery | None
    trajectory: Trajectory | list[Trajectory] | None = None
    usage: Usage | None = None
    inference_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during agent prediction, e.g. latency, API costs, etc."""
    eval_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during evaluation, e.g. accuracy, etc."""
    extra_pred_info: ExtraPredInfo = Field(default_factory=ExtraPredInfo)

    def to_directory(self, directory: str) -> None:
        return _task_to_directory(self, directory)

    def to_readable(self) -> str:
        return _task_to_readable(self)

    def to_markdown(self, heading_level: int = 1) -> str:
        return _task_to_markdown(self, heading_level)

    def to_summary(self, eval_metrics: list[str] = []) -> CSVSummaryRow:
        return _task_to_summary(self, eval_metrics)


class ARCSAmbiguityType(str, Enum):
    semantic_column = "semantic_column"
    semantic_table = "semantic_table"
    semantic_value = "semantic_value"
    semantic_computation = "semantic_computation"
    syntactic_column = "syntactic_column"
    syntactic_table = "syntactic_table"
    syntactic_value = "syntactic_value"
    syntactic_computation = "syntactic_computation"


class GoldAmbiguityPointFinite(BaseModel):
    id: Annotated[str, StringConstraints(pattern=r"^[A-Z]$")]
    """A, B, C, etc."""
    phrase: str
    type: Literal["finite"] = "finite"
    ambiguity_type: ARCSAmbiguityType
    interpretations: list[str]
    intended_interpretation_idx: int | None

    @model_validator(mode="after")
    def validate_intended_interpretation_idx(self) -> "GoldAmbiguityPointFinite":
        if self.intended_interpretation_idx is not None:
            if self.intended_interpretation_idx < 0 or self.intended_interpretation_idx >= len(self.interpretations):
                raise ValueError(
                    f'phrase "{self.phrase}": intended_interpretation_idx {self.intended_interpretation_idx} is out of range.'
                )
        return self


class GoldAmbiguityPointInfinite(BaseModel):
    id: Annotated[str, StringConstraints(pattern=r"^[A-Z]+$")]
    """A, B, C, etc."""
    phrase: str
    type: Literal["infinite"] = "infinite"
    ambiguity_type: ARCSAmbiguityType
    parameter_name: str
    parameter_dtype: Literal["int", "float", "str"]
    parameter_sample_operators: list[Literal["<", ">", "<=", ">=", "=", "<>"]]
    parameter_sample_values: list[Any]
    intended_parameter_operator: Literal["<", ">", "<=", ">=", "=", "<>"]
    intended_parameter_value: Any | None


GoldAmbiguityPoint = Annotated[Union[GoldAmbiguityPointFinite, GoldAmbiguityPointInfinite], Field(discriminator="type")]


class AmbigNL2QTask(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    qid: str
    task_type: Literal["ambig"] = "ambig"
    has_intended_resolution: bool
    language: str
    db: str
    question: str
    dataset_instructions: str | None = None
    """Instructions (e.g. for formatting) that apply to all questions in the dataset"""
    gold_ambiguity_points: Annotated[list[GoldAmbiguityPoint], AfterValidator(is_id_unique)]
    gold_queries: Annotated[list[GoldQuery], AfterValidator(is_id_unique)]
    gold_intended_query_id: str | None
    """Ground-truth query intended by the user"""
    extra_info: dict[str, Any] = Field(default_factory=dict)

    @property
    def gold_intended_query(self) -> GoldQuery | None:
        if self.gold_intended_query_id is None:
            return None
        id_to_query = {gq.id: gq for gq in self.gold_queries}
        return id_to_query[self.gold_intended_query_id]

    @property
    def gold_finite_ambiguity_points(self) -> list[GoldAmbiguityPointFinite]:
        return [ap for ap in self.gold_ambiguity_points if ap.type == "finite"]

    @property
    def gold_infinite_ambiguity_points(self) -> list[GoldAmbiguityPointInfinite]:
        return [ap for ap in self.gold_ambiguity_points if ap.type == "infinite"]

    @property
    def gold_num_interpretation_comb(self) -> int:
        return math.prod(len(ap.interpretations) for ap in self.gold_finite_ambiguity_points)

    def to_directory(self, directory: str) -> None:
        return _task_to_directory(self, directory)

    def to_readable(self) -> str:
        return _task_to_readable(self)

    def to_markdown(self, heading_level: int = 1) -> str:
        return _task_to_markdown(self, heading_level)

    @model_validator(mode="after")
    def validate_gold_queries(self) -> "AmbigNL2QTask":
        # Gold query ID must match the pattern "GQRY(-[A-Z]+\.[0-9]+)*" (e.g. "GQRY-A.2-B.0")
        pattern = r"^GQRY(-[A-Z]+\.[0-9]+)*$"
        assert all(re.match(pattern, gq.id) for gq in self.gold_queries)

        finite_aps = sorted([ap for ap in self.gold_ambiguity_points if ap.type == "finite"], key=lambda x: x.id)
        required_ids = [
            "GQRY" + "".join(f"-{ap.id}.{idx}" for ap, idx in zip(finite_aps, indexes))
            for indexes in itertools.product(*[range(len(ap.interpretations)) for ap in finite_aps])
        ]
        gold_query_ids = set(gq.id for gq in self.gold_queries)
        for gq_id in gold_query_ids:
            if gq_id not in required_ids:
                raise ValueError(
                    f"qid {self.qid}: Gold query {gq_id} is not required. Only {required_ids} are required."
                )
        for required_id in required_ids:
            if required_id not in gold_query_ids:
                raise ValueError(
                    f"qid {self.qid}: Gold query {required_id} is not found. Only {gold_query_ids} are found."
                )
        assert len(self.gold_queries) == len(required_ids) == math.prod(len(ap.interpretations) for ap in finite_aps)
        return self

    @model_validator(mode="after")
    def validate_has_intended_resolution(self) -> "AmbigNL2QTask":
        if self.has_intended_resolution:
            assert self.gold_intended_query_id is not None
            assert all(
                ap.intended_interpretation_idx is not None for ap in self.gold_ambiguity_points if ap.type == "finite"
            )
            assert all(
                ap.intended_parameter_value is not None for ap in self.gold_ambiguity_points if ap.type == "infinite"
            )
        else:
            assert self.gold_intended_query_id is None
            assert all(
                ap.intended_interpretation_idx is None for ap in self.gold_ambiguity_points if ap.type == "finite"
            )
            assert all(
                ap.intended_parameter_value is None for ap in self.gold_ambiguity_points if ap.type == "infinite"
            )
        return self

    @model_validator(mode="after")
    def validate_id_reference(self) -> "AmbigNL2QTask":
        gold_query_ids = set(gq.id for gq in self.gold_queries)
        assert self.gold_intended_query_id is None or self.gold_intended_query_id in gold_query_ids
        return self


class SimpleAmbigNL2QTaskOutput(AmbigNL2QTask):
    """
    The model only predicts the final disambiguated query
    """

    output_type: Literal["ambig-simple"] = "ambig-simple"
    pred_intended_query: PredQuery | None
    trajectory: Trajectory | list[Trajectory] | None = None
    usage: Usage | None = None
    user_simulator_usage: Usage | None = None
    inference_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during agent prediction, e.g. latency, API costs, etc."""
    eval_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during evaluation, e.g. accuracy, etc."""
    extra_pred_info: ExtraPredInfo = Field(default_factory=ExtraPredInfo)

    def to_directory(self, directory: str) -> None:
        return _task_to_directory(self, directory)

    def to_readable(self) -> str:
        return _task_to_readable(self)

    def to_markdown(self, heading_level: int = 1) -> str:
        return _task_to_markdown(self, heading_level)

    def to_summary(self, eval_metrics: list[str] = []) -> CSVSummaryRow:
        return _task_to_summary(self, eval_metrics)


class PredAmbiguityPointFinite(BaseModel):
    id: Annotated[str, StringConstraints(pattern=r"^[A-Z]+$")]
    """A, B, C, etc."""
    phrase: str
    type: Literal["finite"] = "finite"
    interpretations: list[str]
    intended_interpretation_idx: int | None = None
    rejected_by_user: bool = False


class PredAmbiguityPointInfinite(BaseModel):
    id: Annotated[str, StringConstraints(pattern=r"^[A-Z]+$")]
    """A, B, C, etc."""
    phrase: str
    type: Literal["infinite"] = "infinite"
    parameter_name: str
    parameter_dtype: Literal["int", "float", "str"]
    parameter_description: str | None = None
    parameter_sample_operators: list[Literal["<", ">", "<=", ">=", "=", "<>"]]
    parameter_sample_values: list[Any] | list[list[Any]]
    intended_parameter_operator: Literal["<", ">", "<=", ">=", "=", "<>"] | None = None
    intended_parameter_value: Any | None = None
    rejected_by_user: bool = False


PredAmbiguityPoint = Annotated[Union[PredAmbiguityPointFinite, PredAmbiguityPointInfinite], Field(discriminator="type")]


class FlatAmbigNL2QTaskOutput(AmbigNL2QTask):
    """
    The model predicts a list of interpretations, the SQL for each interpretation, and the final disambiguated query
    (e.g. the "Disambiguate First Parse Later" paper https://arxiv.org/pdf/2502.18448)
    """

    output_type: Literal["ambig-flat"] = "ambig-flat"
    interpretations: list[str]
    parameters: list[PredAmbiguityPointInfinite]
    pred_queries: Annotated[list[PredQuery], AfterValidator(is_id_unique)]
    pred_intended_query_id: str | None
    trajectory: Trajectory | list[Trajectory] | None = None
    usage: Usage | None = None
    user_simulator_usage: Usage | None = None
    inference_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during agent prediction, e.g. latency, API costs, etc."""
    eval_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during evaluation, e.g. accuracy, etc."""
    extra_pred_info: ExtraPredInfo = Field(default_factory=ExtraPredInfo)

    # @model_validator(mode="after")
    # def validate_interpretations(self) -> "FlatAmbigNL2QTaskOutput":
    #     assert len(self.interpretations) == len(self.pred_queries)
    #     return self

    @property
    def pred_intended_query(self) -> PredQuery | None:
        if self.pred_intended_query_id is None:
            return None
        id_to_query = {pq.id: pq for pq in self.pred_queries}
        return id_to_query[self.pred_intended_query_id]

    def to_directory(self, directory: str) -> None:
        return _task_to_directory(self, directory)

    def to_readable(self) -> str:
        return _task_to_readable(self)

    def to_markdown(self, heading_level: int = 1) -> str:
        return _task_to_markdown(self, heading_level)

    def to_summary(self, eval_metrics: list[str] = []) -> CSVSummaryRow:
        return _task_to_summary(self, eval_metrics)


class StructuredAmbigNL2QTaskOutput(AmbigNL2QTask):
    """
    The model predicts all the ambiguity points, their interpretations, the SQL for each interpretation combination, as well as the final disambiguated query
    """

    output_type: Literal["ambig-structured"] = "ambig-structured"
    pred_ambiguity_points: Annotated[list[PredAmbiguityPoint], AfterValidator(is_id_unique)]
    pred_queries: Annotated[list[PredQuery], AfterValidator(is_id_unique)]
    pred_intended_query_id: str | None
    trajectory: Trajectory | list[Trajectory] | None = None
    usage: Usage | None = None
    user_simulator_usage: Usage | None = None
    inference_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during agent prediction, e.g. latency, API costs, etc."""
    eval_metrics: dict[str, Any] = Field(default_factory=dict)
    """Metrics produced during evaluation, e.g. accuracy, etc."""
    extra_pred_info: ExtraPredInfo = Field(default_factory=ExtraPredInfo)

    @property
    def pred_intended_query(self) -> PredQuery | None:
        if self.pred_intended_query_id is None:
            return None
        id_to_query = {pq.id: pq for pq in self.pred_queries}
        return id_to_query[self.pred_intended_query_id]

    @property
    def pred_finite_ambiguity_points(self) -> list[PredAmbiguityPointFinite]:
        return [ap for ap in self.pred_ambiguity_points if ap.type == "finite"]

    @property
    def pred_infinite_ambiguity_points(self) -> list[PredAmbiguityPointInfinite]:
        return [ap for ap in self.pred_ambiguity_points if ap.type == "infinite"]

    @property
    def pred_num_interpretation_comb(self) -> int:
        return math.prod(len(ap.interpretations) for ap in self.pred_finite_ambiguity_points)

    @model_validator(mode="after")
    def validate_pred_queries(self) -> "StructuredAmbigNL2QTaskOutput":
        # Pred query ID must match the pattern "PQRY(-[A-Z]+\.[0-9]+)*" (e.g. "PQRY-A.2-B.0")
        pattern = r"^PQRY(-[A-Z]+\.[0-9]+)*$"
        assert all(re.match(pattern, pq.id) for pq in self.pred_queries)

        if not self.pred_ambiguity_points:
            assert len(self.pred_queries) == 0 or len(self.pred_queries) == 1
            return self

        # finite_aps = sorted([ap for ap in self.pred_ambiguity_points if ap.type == "finite"], key=lambda x: x.id)
        # required_ids = [
        #     "PQRY" + "".join(f"-{ap.id}.{idx}" for ap, idx in zip(finite_aps, indexes))
        #     for indexes in itertools.product(*[range(len(ap.interpretations)) for ap in finite_aps])
        # ]
        # pred_query_ids = set(pq.id for pq in self.pred_queries)
        # for pq_id in pred_query_ids:
        #     if pq_id not in required_ids:
        #         raise ValueError(f"qid {self.qid}: Pred query {pq_id} is not required.")
        # for required_id in required_ids:
        #     if required_id not in pred_query_ids:
        #         raise ValueError(f"qid {self.qid}: Pred query {required_id} is not found.")
        # assert len(self.pred_queries) == len(required_ids) == math.prod(len(ap.interpretations) for ap in finite_aps)
        return self

    @model_validator(mode="after")
    def validate_pred_id_reference(self) -> "StructuredAmbigNL2QTaskOutput":
        pred_query_ids = set(pq.id for pq in self.pred_queries)
        assert self.pred_intended_query_id is None or self.pred_intended_query_id in pred_query_ids
        return self

    def to_directory(self, directory: str) -> None:
        return _task_to_directory(self, directory)

    def to_readable(self) -> str:
        return _task_to_readable(self)

    def to_markdown(self, heading_level: int = 1) -> str:
        return _task_to_markdown(self, heading_level)

    def to_summary(self, eval_metrics: list[str] = []) -> CSVSummaryRow:
        return _task_to_summary(self, eval_metrics)


NL2QTask = Annotated[Union[SimpleNL2QTask, AmbigNL2QTask], Field(discriminator="task_type")]
NL2QTaskOutput = Annotated[
    Union[SimpleNL2QTaskOutput, SimpleAmbigNL2QTaskOutput, FlatAmbigNL2QTaskOutput, StructuredAmbigNL2QTaskOutput],
    Field(discriminator="output_type"),
]


def _get_query_fields(task: NL2QTask | NL2QTaskOutput, t: TypeAlias) -> list[str]:
    res = []
    for key, value in type(task).model_fields.items():
        if value.annotation == t or t in get_args(value.annotation):
            res.append(key)
    return res


def _save_trajectories(trajectory: Trajectory | list[Trajectory], directory: str) -> None:
    os.makedirs(directory, exist_ok=True)
    trajectories = trajectory if isinstance(trajectory, list) else [trajectory]
    ids = [tr.id for tr in trajectories]
    if len(ids) != len(set(ids)):
        logger.warning(f"Trajectory IDs are not unique: {ids}, some trajectories will be overwritten")
    for tr in trajectories:
        with open(os.path.join(directory, f"{tr.id}.xml"), "w") as f:
            f.write(tr.to_readable())
        with open(os.path.join(directory, f"{tr.id}.md"), "w") as f:
            f.write(tr.to_markdown())


def _task_to_directory(task: NL2QTask | NL2QTaskOutput, directory: str) -> None:
    os.makedirs(directory, exist_ok=True)
    for prefix in ["gold", "pred"]:
        for field in _get_query_fields(task, GoldQuery if prefix == "gold" else PredQuery):
            queries = getattr(task, field)
            if not isinstance(queries, list):
                queries = [queries]
            for q in queries:
                if q is not None:
                    q.to_directory(os.path.join(directory, f"{prefix}_csv"))
    with open(os.path.join(directory, "task_readable.sql"), "w") as f:
        f.write(task.to_readable())
    with open(os.path.join(directory, "task_readable.md"), "w") as f:
        f.write(task.to_markdown())
    trajectory = getattr(task, "trajectory", None)
    if trajectory is not None:
        _save_trajectories(trajectory, os.path.join(directory, "trajectory"))


def _task_to_readable(task: NL2QTask | NL2QTaskOutput) -> str:
    query_fields = _get_query_fields(task, GoldQuery)
    query_fields += _get_query_fields(task, PredQuery)
    header = task.model_dump_json(indent=2, exclude=set(["evidence", "trajectory", "extra_pred_info"] + query_fields))
    res = f"/*\n{header}\n*/"
    evidence = getattr(task, "evidence", None)
    if evidence is not None:
        res += f"\n\n\n----- START OF EVIDENCE -----\n/*\n{evidence}\n*/\n----- END OF EVIDENCE -----"
    for field in query_fields:
        queries = getattr(task, field)
        if not isinstance(queries, list):
            queries = [queries]
        for q in queries:
            if q is not None:
                res += f"\n\n\n{q.to_readable()}"
    return res


def _task_to_markdown(task: NL2QTask | NL2QTaskOutput, heading_level: int = 1) -> str:
    """Convert task to a concise, human-readable markdown format.

    Args:
        task: The task to convert.
        heading_level: The base heading level (1 for #, 2 for ##, 3 for ###, etc.)
    """
    h1 = "#" * heading_level
    h2 = "#" * (heading_level + 1)
    lines = [f"{h1} Task: {task.qid}", ""]

    # Basic info
    lines.append(f"**Database:** {task.db}  ")
    lines.append(f"**Language:** {task.language}  ")
    lines.append("")

    # Question
    lines.append(f"{h2} Question")
    lines.append(task.question)

    # Question instructions
    question_instructions = getattr(task, "question_instructions", None)
    if question_instructions:
        lines.append(f"\n**Question Instructions:** {question_instructions}")

    # Evidence
    evidence = getattr(task, "evidence", None)
    if evidence:
        lines.append(f"\n{h2} Evidence")
        lines.append(evidence)

    def _quote(s: str) -> str:
        return f'"{s}"' if " " in s else s

    def _format_column_name(col: ColumnRef) -> str:
        res = f"{_quote(col.table_name)}.{_quote(col.column_name)}"
        if col.schema_name:
            res = f"{_quote(col.schema_name)}.{res}"
        return res

    if isinstance(
        task, (SimpleNL2QTaskOutput, SimpleAmbigNL2QTaskOutput, FlatAmbigNL2QTaskOutput, StructuredAmbigNL2QTaskOutput)
    ):
        # Linked schema
        linked_schema = task.extra_pred_info.linked_schema
        if linked_schema:
            lines.append(f"\n{h2} Linked Schema")
            lines.append(f"\n```\n{', '.join([_format_column_name(col) for col in linked_schema])}\n```")

        # Raw pred query
        raw_pred_query = task.extra_pred_info.raw_pred_query
        if raw_pred_query:
            lines.append(
                "\n\n"
                + raw_pred_query.to_markdown(heading_level=heading_level + 1).replace(
                    "# Pred Query", "# Raw Pred Query"
                )
            )

        # Pred queries
        pred_query = task.pred_intended_query if task.task_type == "ambig" else task.pred_query
        if pred_query is not None:
            lines.append("\n\n" + pred_query.to_markdown(heading_level=heading_level + 1))
        else:
            lines.append(f"\n\n{h2} Pred Query\n\nN/A")

    # Gold queries
    gold_query = task.gold_intended_query if task.task_type == "ambig" else task.gold_query
    if gold_query is not None:
        lines.append("\n\n" + gold_query.to_markdown(heading_level=heading_level + 1))
    else:
        lines.append(f"\n\n{h2} Gold Query\n\nN/A")

    # Metrics
    eval_metrics = getattr(task, "eval_metrics", None)
    if eval_metrics:
        lines.append(f"\n{h2} Evaluation Metrics")
        for key, value in eval_metrics.items():
            lines.append(f"- **{key}:** {value}")

    inference_metrics = getattr(task, "inference_metrics", None)
    if inference_metrics:
        lines.append(f"\n{h2} Inference Metrics")
        for key, value in inference_metrics.items():
            lines.append(f"- **{key}:** {value}")

    # Usage
    usage = getattr(task, "usage", None)
    if usage:
        lines.append(f"\n{h2} Usage")
        lines.append(f"- **API Requests:** {usage.api_requests}")
        lines.append(f"- **Input Tokens:** {usage.input_tokens}")
        lines.append(f"- **Output Tokens:** {usage.output_tokens}")
        lines.append(f"- **Cost:** ${round(float(usage.api_cost_usd), 4)}")

    return "\n".join(lines)


def _task_to_summary(task: NL2QTask | NL2QTaskOutput, eval_metrics: list[str] = []) -> CSVSummaryRow:
    gold_query_field = "gold_query" if task.task_type == "simple" else "gold_intended_query"
    gold_query = getattr(task, gold_query_field, None)
    pred_query_field = "pred_query" if task.task_type == "simple" else "pred_intended_query"
    pred_query = getattr(task, pred_query_field, None)
    return CSVSummaryRow(
        qid=task.qid,
        db=task.db,
        question=task.question,
        question_instructions=getattr(task, "question_instructions", None),
        gold_query=gold_query.query if gold_query else None,
        pred_query=pred_query.query if pred_query else None,
        gold_exec_result="\n".join([exec_result.to_readable() for exec_result in gold_query.all_exec_results])
        if gold_query
        else None,
        pred_exec_result=pred_query.exec_result.to_readable() if pred_query and pred_query.exec_result else None,
        metrics={m: getattr(task, "eval_metrics", {}).get(m) for m in eval_metrics},
    )


class NL2QDataset(BaseModel):
    name: str
    split: str
    databases: list[str] | None = None  # None means all databases
    subsample_size: int | None = None
    dataset_extra_kwargs: dict[str, Any] = Field(default_factory=dict)
    tasks: list[NL2QTask]
    db_connectors: dict[str, Any]

    @model_validator(mode="after")
    def validate_qid_uniqueness(self) -> "NL2QDataset":
        qids = [task.qid for task in self.tasks]
        if len(qids) != len(set(qids)):
            raise ValueError(f"QIDs are not unique: {qids}")
        return self


class NL2QRunResult(BaseModel):
    start_time: datetime.datetime
    end_time: datetime.datetime
    dataset: str
    split: str
    databases: list[str] | None  # None means all databases
    subsample_size: int | None
    dataset_extra_kwargs: dict[str, Any] = Field(default_factory=dict)
    agent: str
    agent_config: dict[str, Any]
    total_usage: Usage | None = None
    """Total usage of the agent, does not include user simulator usage"""
    total_user_simulator_usage: Usage | None = None
    aggregated_inference_metrics: dict[str, Any] = Field(default_factory=dict)
    aggregated_eval_metrics: dict[str, Any] = Field(default_factory=dict)
    tasks: list[NL2QTaskOutput]

    def to_directory(self, directory: str, eval_metrics_in_summary: list[str] = []) -> None:
        os.makedirs(directory, exist_ok=True)
        with open(os.path.join(directory, "result.json"), "w") as f:
            f.write(self.model_dump_json(indent=2))

        self.to_csv(os.path.join(directory, "result_summary.csv"), eval_metrics_in_summary)

        for task in self.tasks:
            task.to_directory(os.path.join(directory, "readable", task.qid))

    def to_csv(self, path: str, eval_metrics: list[str] = []) -> None:
        summaries = [task.to_summary(eval_metrics) for task in self.tasks]
        df = pd.DataFrame([summary.data() for summary in summaries], columns=summaries[0].fields())
        df.to_csv(path, index=False)
