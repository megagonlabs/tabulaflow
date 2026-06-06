import copy
from decimal import Decimal
import json
import os
from pydantic import BaseModel, Field, field_serializer, model_validator, ConfigDict, field_validator
from typing import TYPE_CHECKING, Any, Literal, Annotated, TypeAlias, Union
import pandas as pd
import logging
from tabulaflow.core.config import tabulaflow_config
from tabulaflow.core.dataframe import _deserialize_dataframe, _sanitize_df, _serialize_dataframe

# litellm (~1.5s) and pydantic_ai (~0.9s) are heavy imports needed only by a few
# conversion helpers below. Import them lazily (in those functions) so that the 66
# modules importing core.types — including the TUI's UI shell — don't pay for them
# at startup.
if TYPE_CHECKING:
    import pydantic_ai

logger = logging.getLogger(__name__)


NumericOrNull: TypeAlias = Union[float, int, None]

SQLDialect: TypeAlias = Literal[
    "athena",
    "bigquery",
    "clickhouse",
    "databricks",
    "doris",
    "duckdb",
    "hive",
    "mysql",
    "oracle",
    "postgres",
    "presto",
    "redshift",
    "snowflake",
    "spark",
    "sqlite",
    "starrocks",
    "teradata",
    "trino",
    "tsql",
]

NonSQLLanguage: TypeAlias = Literal["cypher", "mongo"]


# ---------------------------------------------------------------------------
# Property-graph schema (Neo4j, Neptune, etc.)
# ---------------------------------------------------------------------------


class GraphPropertySchema(BaseModel):
    """A single property on a node type or relationship type."""

    name: str
    dtype: str
    """Database-reported type string (e.g. ``"STRING"``, ``"INTEGER"``, ``"LIST OF STRING"``)."""
    description: str | None = None


class NodeSchema(BaseModel):
    """Schema for one node label."""

    label: str
    description: str | None = None
    properties: list[GraphPropertySchema] = Field(default_factory=list)


class RelationshipSchema(BaseModel):
    """Schema for one (label, source, target) relationship pattern."""

    label: str
    source_label: str
    target_label: str
    description: str | None = None
    properties: list[GraphPropertySchema] = Field(default_factory=list)


class PropertyGraphSchema(BaseModel):
    """Property-graph schema usable with any graph database."""

    name: str
    description: str | None = None
    nodes: list[NodeSchema] = Field(default_factory=list)
    relationships: list[RelationshipSchema] = Field(default_factory=list)

    def get_node(self, label: str) -> NodeSchema:
        for n in self.nodes:
            if n.label == label:
                return n
        raise ValueError(f"Node type {label!r} not found.")

    def get_relationships(
        self,
        label: str | None = None,
        source_label: str | None = None,
        target_label: str | None = None,
    ) -> list[RelationshipSchema]:
        """Return relationship types matching the given filters (all optional)."""
        results: list[RelationshipSchema] = []
        for rt in self.relationships:
            if label is not None and rt.label != label:
                continue
            if source_label is not None and rt.source_label != source_label:
                continue
            if target_label is not None and rt.target_label != target_label:
                continue
            results.append(rt)
        return results


# ---------------------------------------------------------------------------
# SQL schema (MySQL, PostgreSQL, Snowflake, BigQuery, etc.)
# ---------------------------------------------------------------------------


class ForeignKeySchema(BaseModel):
    columns: list[str]
    foreign_schema_name: str | None = None
    foreign_table: str
    foreign_columns: list[str]


class SQLColumnSchema(BaseModel):
    name: str
    dtype: str
    """Canonical atomic type token (e.g. ``VARCHAR``, ``BIGINT``, ``ARRAY``, ``STRUCT``).
    Used for categorical type-class checks. See ``native_dtype`` for the dialect-native string."""
    native_dtype: str | None = None
    """Dialect-native type string preserving parameters/nested shape
    (e.g. ``VARCHAR(100)`` on Postgres, ``STRUCT(a INT, b VARCHAR)`` on DuckDB,
    ``ARRAY<STRING>`` on BigQuery). Best-effort: ``None`` when neither SQLAlchemy
    nor the dialect catalog could resolve it."""
    description: str | None = None
    """Concise description of the column"""
    detailed_description_markdown: str | None = None
    """Markdown-formatted detailed description of the column"""
    json_schema: dict[str, Any] | None = None
    """JSON Schema describing the internal structure of JSON/VARIANT columns (nested objects, arrays, etc.)"""
    not_used: bool = False
    """Indicates that the column contains no valid data or has been explicitly marked as not useful"""
    nullable: bool
    null_ratio: float | None = None
    num_unique: int | None = None  # Only for text or integer columns
    unique_ratio: float | None = None  # Only for text or integer columns
    examples: list[Any]
    primary_key_type: Literal["single", "composite"] | None = None
    foreign_keys: list[ForeignKeySchema] = Field(default_factory=list)  # Includes composite foreign keys


class NamePattern(BaseModel):
    pattern: str
    """(e.g. "events_{YYYYMMDD}")"""
    comment: str | None = None
    """(e.g. "YYYYMMDD from 20200101 to 20200102")"""
    original_names: list[str] = Field(default_factory=list)
    """The original table names in the compressed schema (e.g. ["events_20200101", "events_20200102"])"""


class SQLTableSchema(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    name_patterns: list[NamePattern] = Field(default_factory=list)
    """All variations of the table name in the compressed schema."""
    schema_name: str | None = None
    """null for DBMS that does not support schemas such as SQLite"""
    description: str | None = None
    is_view: bool
    columns: list[SQLColumnSchema]
    primary_key: list[str]
    num_rows: int | None = None
    foreign_keys: list[ForeignKeySchema]
    sampled_df: pd.DataFrame | None = None

    @field_serializer("sampled_df", when_used="always")
    def serialize_df(self, df: pd.DataFrame | None) -> dict[str, Any] | None:
        return _serialize_dataframe(df)

    @field_validator("sampled_df", mode="before")
    @classmethod
    def deserialize_df(cls, v: dict[str, Any] | pd.DataFrame | None) -> pd.DataFrame | None:
        return _deserialize_dataframe(v)

    @model_validator(mode="after")
    def sanitize_sampled_df(self) -> "SQLTableSchema":
        if self.sampled_df is not None:
            self.sampled_df = _sanitize_df(self.sampled_df)
        return self

    def trim(
        self,
        column_names: list[str],
        case_insensitive: bool = True,
        keep_pk: bool = True,
    ) -> "SQLTableSchema | None":
        """Return a trimmed copy keeping only the specified columns.

        Args:
            column_names: Column names to retain.
            case_insensitive: If True, column name matching ignores case.
            keep_pk: If True, primary-key columns are always retained.

        Returns:
            A deep-copied ``SQLTableSchema`` with only the matched columns,
            or ``None`` if no columns remain after trimming.
        """

        def normalize(s: str) -> str:
            return s.lower() if case_insensitive else s

        normalized_names = {normalize(n) for n in column_names}

        new_columns = [
            col for col in self.columns if normalize(col.name) in normalized_names or (keep_pk and col.primary_key_type)
        ]
        if not new_columns:
            return None

        table = copy.deepcopy(self)
        table.columns = new_columns

        if table.sampled_df is not None:
            remaining_col_names = [col.name for col in table.columns]
            cols_to_keep = [c for c in remaining_col_names if c in table.sampled_df.columns]
            table.sampled_df = table.sampled_df[cols_to_keep] if cols_to_keep else pd.DataFrame()

        return table


class ColumnRef(BaseModel):
    schema_name: str | None = None
    table_name: str
    column_name: str


class TableRef(BaseModel):
    schema_name: str | None = None
    table_name: str


class SQLSchema(BaseModel):
    name: str
    """Database name, or project name for BigQuery."""
    dialect: SQLDialect | None = None
    description: str | None = None
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
        def normalize(s: str | None) -> str | None:
            return s.lower() if case_insensitive and s is not None else s

        # Group column names by (schema_name, table_name)
        columns_by_table: dict[tuple[str | None, str], set[str]] = {}
        for ref in column_refs:
            key = (normalize(ref.schema_name), normalize(ref.table_name))
            columns_by_table.setdefault(key, set()).add(ref.column_name)  # type: ignore[arg-type]

        new_tables: list[SQLTableSchema] = []
        for table in self.tables:
            table_key = (normalize(table.schema_name), normalize(table.name))
            col_names = columns_by_table.get(table_key)  # type: ignore[arg-type]
            if col_names is None:
                continue
            trimmed = table.trim(list(col_names), case_insensitive=case_insensitive, keep_pk=keep_pk)
            if trimmed is not None:
                new_tables.append(trimmed)

        schema = self.model_copy(deep=False)
        schema.tables = new_tables
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
        cls, messages: "list[pydantic_ai.messages.ModelMessage]", id: str = "TRJY"
    ) -> "Trajectory":
        trajectory = cls(messages=[], id=id)
        if not messages:
            return trajectory

        for msg in reversed(messages):
            if (
                msg.kind == "request"
                and msg.instructions is not None
                and any(part.part_kind == "user-prompt" for part in msg.parts)
            ):
                trajectory.messages.append(SystemMessage(content=msg.instructions))
                break

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
                lines.append(f"``````\n{msg.content}\n``````")
            elif msg.role == "user":
                lines.append(f'\n<a id="{anchor}"></a>\n\n**[{i}] User:**\n')
                lines.append(f"``````\n{msg.content}\n``````")
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
                lines.append(f"``````\n{s.strip()}\n``````")
            elif msg.role == "tool":
                lines.append(f'\n<a id="{anchor}"></a>\n\n**[{i}] Tool:**\n')
                lines.append(f"``````\n{msg.response}\n``````")
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
    import litellm

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
        input_cost, output_cost = litellm.cost_per_token(
            model=pydantic_ai_model_to_litellm_model(llm),
            prompt_tokens=input_tokens,
            completion_tokens=output_tokens,
        )
        return Decimal(round(input_cost + output_cost, 8))
    except Exception:
        pass

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
            if api_requests == 0:
                api_cost_usd = Decimal(0)
            else:
                assert llm is not None, "llm is required to when api_requests > 0"
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
        cls, usage: "pydantic_ai.usage.RunUsage | pydantic_ai.usage.RequestUsage", llm: str
    ) -> "Usage":
        import pydantic_ai

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

    df: pd.DataFrame | None = None
    df_is_truncated: bool = False
    """True if the df is truncated, e.g. when the result is too large"""
    error: ErrorInfo | None = None
    latency_seconds: float | None = None

    @field_serializer("df", when_used="always")
    def serialize_df(self, df: pd.DataFrame | None) -> dict[str, Any] | None:
        return _serialize_dataframe(df)

    @field_validator("df", mode="before")
    @classmethod
    def deserialize_df(cls, v: dict[str, Any] | pd.DataFrame | None) -> pd.DataFrame | None:
        return _deserialize_dataframe(v)

    @model_validator(mode="after")
    def truncate_df(self) -> "ExecResult":
        if tabulaflow_config.df_max_rows and self.df is not None and len(self.df) > tabulaflow_config.df_max_rows:
            logger.warning(f"Truncated df from {len(self.df)} to {tabulaflow_config.df_max_rows} rows")
            self.df = self.df.head(tabulaflow_config.df_max_rows)
            self.df_is_truncated = True
        return self

    @model_validator(mode="after")
    def sanitize_df(self) -> "ExecResult":
        if self.df is not None:
            self.df = _sanitize_df(self.df)
        return self

    @model_validator(mode="after")
    def validate_df_or_error(self) -> "ExecResult":
        if self.df is None and self.error is None or self.df is not None and self.error is not None:
            raise ValueError("ExecResult must have either df or error, but not both")
        return self

    def to_markdown(self) -> str:
        if self.df is None:
            return f"**Error:** {self.error.exc_type}: {self.error.message}" if self.error else "**Error:** Unknown"
        from tabulaflow.core.utils import format_df

        result = format_df(self.df)
        n = len(self.df)
        if n > 10:
            result += f"\n\n*... truncated ({n} rows total)*"
        else:
            result += f"\n\n*{n} rows*"
        return result


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
