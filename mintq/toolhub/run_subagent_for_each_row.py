"""Run a row-wise subagent over a table in a single database."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable
from typing import Any, ClassVar

import jinja2
import sqlalchemy
from pydantic_ai import Agent, Tool
from pydantic_ai.capabilities.abstract import AbstractCapability
from pydantic_ai.settings import ModelSettings

from mintq.db_connector.base import BaseSQLDBConnector
from mintq.db_connector.db_registry import DBRegistry
from mintq.schema import SQLDialect, Trajectory
from mintq.toolhub.message_store import (
    MESSAGE_THRESHOLD_CHARS,
    MessageStore,
    MessageStoreCapability,
    make_snippet,
)
from mintq.toolhub.registry_run_query import RegistryRunQueryTool
from mintq.toolhub.web_browser import BROWSER_TOOL_NAMES, WebBrowserTool


_COL_EXCEPTION = "_subagent_exception"
_COL_TRAJECTORY = "_subagent_trajectory"
_INTERNAL_COLUMNS = [_COL_EXCEPTION, _COL_TRAJECTORY]

# Dialects that support a native JSON column type and the SQL type name to use.
_JSON_TYPE_FOR_DIALECT: dict[SQLDialect, str] = {
    "snowflake": "VARIANT",
    "postgres": "JSONB",
    "mysql": "JSON",
    "duckdb": "JSON",
    "bigquery": "JSON",
    "clickhouse": "String",  # no native JSON; fall back to String (≈TEXT)
}


# Dialects that require PARSE_JSON() to store a JSON string into a native column.
_DIALECTS_WITH_PARSE_JSON: set[SQLDialect] = {"snowflake"}

_JINJA_ENV = jinja2.Environment(undefined=jinja2.StrictUndefined)


def _key_where_clause(key_columns: list[str], key_payload: dict[str, object]) -> sqlalchemy.ColumnElement[bool]:
    """Build a SQLAlchemy WHERE clause from key columns."""
    conditions: list[sqlalchemy.ColumnElement[bool]] = []
    for col_name in key_columns:
        val = key_payload[col_name]
        col: sqlalchemy.ColumnClause[object] = sqlalchemy.column(col_name)
        conditions.append(col.is_(None) if val is None else col == val)
    return sqlalchemy.and_(*conditions)


class RunSubagentForEachRowTool:
    """Run an LLM subagent for each row of a table and write its text output back.

    The per-row subagent has no database tools; it produces a single text value
    that this tool writes to the configured output column. Optional capabilities
    (``enable_browser_tools``, ``enable_nested_subagents``) extend the subagent's
    reach without changing the output contract.
    """

    name: ClassVar[str] = "run_subagent_for_each_row"

    def __init__(
        self,
        db_connector: BaseSQLDBConnector,
        *,
        registry: DBRegistry | None = None,
        message_store: MessageStore | None = None,
        subagent_llm: str = "openai-responses:gpt-5-mini",
        model_settings: ModelSettings | None = None,
        max_concurrency: int = 200,
        store_metadata: bool = False,
    ) -> None:
        """Initialize the tool.

        Args:
            db_connector: SQL connector for the table being updated (used for
                per-row write-back).
            registry: Optional database registry. Required only when callers
                pass ``enable_run_query_tool=True`` so the per-row subagent
                can query any registered database. If omitted, that flag is
                unavailable.
            message_store: Optional workspace-backed message store. When
                provided (together with ``registry``), non-leaf subagents
                (``enable_nested_subagents=True``) get offload-truncation: long
                prompts and tool returns are mirrored here and replaced with
                snippets, and the subagent gets a registry-backed ``run_query``
                tool to read the full content back from
                ``workspace._internal.messages``. Without both, non-leaf
                subagents run untruncated.
            subagent_llm: LLM identifier used by per-row subagent runs.
            model_settings: Optional pydantic-ai model settings passed to
                each subagent run (e.g. ``openai_service_tier``).
            max_concurrency: Maximum number of row subagents to run
                concurrently.
            store_metadata: If True, write ``_subagent_exception`` and
                ``_subagent_trajectory`` columns back to the target table
                after each row. ``_subagent_exception`` is NULL on success
                and a ``"<ExceptionType>: <message>"`` string on failure.
        """
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be greater than 0")
        self.db_connector = db_connector
        self.registry = registry
        self.message_store = message_store
        self.subagent_llm = subagent_llm
        self.model_settings = model_settings
        self.max_concurrency = max_concurrency
        self.store_metadata = store_metadata
        self.on_row_complete: Callable[[int, int], None] | None = None

    async def __call__(
        self,
        table_name: str,
        *,
        task_query: str,
        task_instruction: str,
        key_columns: list[str],
        output_columns: list[str],
        enable_browser_tools: bool = False,
        enable_nested_subagents: bool = False,
        enable_run_query_tool: bool = False,
    ) -> str:
        """Run an LLM subagent on each row, concurrently.

        Use this tool to process many similar, independent sub-tasks in parallel:
        lay the sub-tasks out as rows of a table and each row gets its own subagent.
        ``task_query`` and ``task_instruction`` serve two roles. Row selection:
        ``task_query`` is a free-form SELECT whose result rows become the tasks (one
        subagent per row). Prompt construction: each subagent's prompt is
        ``task_instruction`` rendered with that row's ``task_query`` columns — which
        may include joined or computed columns, not just the table's own.

        By default the subagent has no tools: it reads its prompt, returns one text
        value, and this tool writes that value to ``output_columns[0]``. Set
        ``enable_browser_tools=True`` to grant web-browsing tools, or
        ``enable_run_query_tool=True`` to grant a ``run_query`` tool that can query
        and modify any registered database. Set ``enable_nested_subagents=True`` to
        give the subagent this same tool so it can fan out its own row-wise sub-tasks;
        this does not propagate — each deeper level must set the flag again to nest
        further.

        This is also the execution primitive for semantic operators beyond standard
        SQL — tasks where the predicate, join condition, or transformation requires
        natural-language understanding rather than exact SQL expressions. Prefer this
        tool over fuzzy regex matching or LIKE-based SQL for these tasks. Common
        patterns:
        - **Semantic filter**: Classify a free-text column against a natural-language
          predicate (e.g., "is this review positive or negative?").
        - **Semantic extraction**: Extract structured values from unstructured text
          (e.g., extract sentiment, topic, or named entities from a comment).
        - **Semantic join**: Match rows across tables where there is no shared key
          and no syntactic overlap between join columns (e.g., abbreviations to
          full names, or matching product names across different naming conventions).
          Two approaches:
          (a) (preferred when the lookup space is large) Add a foreign-key column
              to one table and have the subagent resolve the match against the
              other table at runtime via ``run_query`` — set
              ``enable_run_query_tool=True``. Avoid embedding a large vocabulary
              in the task instruction.
          (b) Add a standardized column to both tables and have the subagent
              normalize each side to a canonical form (e.g., IATA airport code)
              independently. No ``run_query`` access needed.
          After the tool completes, a standard SQL JOIN on the new column(s)
          produces the final result.

        Args:
            table_name: Target table name. Can be qualified (e.g. schema.table).
                Used as the write-back target; per-row updates locate rows here
                via ``key_columns``.
            task_query: SELECT query producing one row per subagent task. Free-form:
                may join tables, compute new columns, etc. The result columns
                become the variables available to ``task_instruction``. Must
                include all ``key_columns``. Pass ``SELECT * FROM <table_name>``
                as a default. Example::

                    SELECT r.review_id,
                           r.product_name,
                           m.content AS review_text
                    FROM reviews r
                    JOIN _internal.messages m ON r.msg_ref = m.message_id
                    WHERE r.sentiment IS NULL
            task_instruction: A Jinja2 template rendered per-row as the subagent
                prompt. Use ``{{ column_name }}`` to interpolate values from the
                ``task_query`` result; standard Jinja control flow
                (``{% for %}``, ``{% if %}``) is available. For JSON columns,
                extract the field or cast to an array in ``task_query`` using
                the dialect's JSON functions rather than relying on the
                template — driver materialization varies (string vs structure)
                and only structured projections iterate reliably. Example:
                ``"Classify the sentiment of: {{ review_text }}"``.
            key_columns: Columns used in the WHERE clause to locate each row in
                ``table_name`` for write-back. Must appear in the ``task_query``
                result.
            output_columns: Columns to update on ``table_name``. Must be exactly
                one column; it must already exist on the target table (does not
                need to appear in the ``task_query`` projection).
            enable_browser_tools: If True, the per-row subagent additionally
                receives web-browsing tools (navigate, click, type, scroll,
                etc.). Use for tasks that require fetching information from the
                web.
            enable_nested_subagents: If True, each per-row subagent additionally
                receives this ``run_subagent_for_each_row`` tool, allowing it
                to fan out further row-wise tasks of its own. The flag does not
                propagate automatically — each nested level must opt in
                explicitly.
            enable_run_query_tool: If True, the per-row subagent additionally
                receives a registry-backed ``run_query`` tool that can query
                and modify any registered database (the subagent specifies
                ``db_alias`` per call). Enable it for tasks where row-local
                context isn't enough:

                - **Computing the output via SQL.** The subagent builds the
                  value with ``run_query`` and writes ``output_columns[0]``
                  itself via an ``UPDATE``. Useful when the value is large.
                  When the subagent needs to use ``UPDATE`` to write back to
                  the row, the ``task_instruction`` must mention the
                  ``db_alias`` and ``table_name``, and include the key
                  columns for the WHERE clause.
                - **Reads or writes beyond the row.** The subagent reads
                  auxiliary tables for context, or writes outside the row's
                  output column (other tables, INSERTs, DDL).
        """
        if not output_columns or len(output_columns) != 1:
            return "(error: output_columns must be exactly one column)"
        output_col = output_columns[0]

        select_result = await self.db_connector.run_query_async(task_query)
        if select_result.error is not None or select_result.df is None:
            detail = select_result.error.message if select_result.error is not None else "no dataframe returned"
            return f"(error: failed to evaluate task_query: {detail})"

        df = select_result.df
        all_columns = [str(c) for c in df.columns]
        if not all_columns:
            return "(error: task_query returned no columns)"

        missing_id = [c for c in key_columns if c not in all_columns]
        if missing_id:
            return f"(error: key_columns not found in task_query result: {missing_id})"

        # Look up the target table's actual columns to validate output_columns and
        # decide whether to ALTER for _subagent_* columns. task_query may project
        # arbitrary computed/joined columns that don't correspond to table_name.
        table_columns_result = await self.db_connector.run_query_async(f"SELECT * FROM {table_name} LIMIT 0")
        if table_columns_result.error is not None or table_columns_result.df is None:
            detail = (
                table_columns_result.error.message
                if table_columns_result.error is not None
                else "no dataframe returned"
            )
            return f"(error: failed to inspect target table {table_name!r}: {detail})"
        table_columns = [str(c) for c in table_columns_result.df.columns]

        if output_col not in table_columns:
            return f"(error: output_columns not found in table {table_name!r}: [{output_col!r}])"

        # Compile the task instruction as a Jinja2 template.
        try:
            task_template = _JINJA_ENV.from_string(task_instruction)
        except jinja2.TemplateSyntaxError as e:
            return f"(error: invalid Jinja2 syntax in task_instruction: {e})"

        # Ensure _subagent_* columns exist on the target table.
        dialect = self.db_connector.language
        trajectory_dtype = _JSON_TYPE_FOR_DIALECT.get(dialect, "TEXT")
        if self.store_metadata:
            for col in _INTERNAL_COLUMNS:
                if col not in table_columns:
                    dtype = trajectory_dtype if col == _COL_TRAJECTORY else "TEXT"
                    await self.db_connector.run_query_async(f"ALTER TABLE {table_name} ADD COLUMN {col} {dtype}")

        # If nesting is enabled, construct one fresh tool instance to share across
        # all rows. Fresh (not ``self``) so its ``on_row_complete`` stays None and
        # nested progress doesn't bleed into the parent's TUI callback. One per
        # outer ``__call__`` (not per row) — per-call state lives in the frame.
        nested_pa_tool: Tool | None = None
        if enable_nested_subagents:
            nested_tool = RunSubagentForEachRowTool(
                self.db_connector,
                registry=self.registry,
                message_store=self.message_store,
                subagent_llm=self.subagent_llm,
                model_settings=self.model_settings,
                max_concurrency=self.max_concurrency,
                store_metadata=self.store_metadata,
            )
            nested_pa_tool = nested_tool.as_pydantic_ai_tool()

        if enable_run_query_tool and self.registry is None:
            return "(error: enable_run_query_tool=True but no registry was provided to RunSubagentForEachRowTool)"

        # Offload-truncation applies only to non-leaf subagents (those that can
        # spawn nested subagents), and only when a workspace message store and a
        # registry are wired. Long prompts and tool returns (browser snapshots,
        # nested-subagent summaries) are mirrored to the store and shown as
        # snippets; the subagent dereferences them by reading
        # ``workspace._internal.messages`` with ``run_query`` — so offload
        # implies the run_query tool.
        offload_enabled = enable_nested_subagents and self.message_store is not None and self.registry is not None
        call_id = uuid.uuid4().hex[:8]

        run_query_pa_tool: Tool | None = None
        if enable_run_query_tool or offload_enabled:
            assert self.registry is not None
            run_query_pa_tool = RegistryRunQueryTool(self.registry).as_pydantic_ai_tool()

        completed = 0

        # Build a SQLAlchemy table with all columns referenced in SET clauses.
        sa_col_names: set[str] = set(key_columns) | {output_col}
        if self.store_metadata:
            sa_col_names.update(_INTERNAL_COLUMNS)
        sa_table = sqlalchemy.table(table_name, *[sqlalchemy.column(c) for c in sa_col_names])

        async def _save_row_metadata(
            key_payload: dict[str, object],
            exception: str | None,
            trajectory: str | None,
        ) -> None:
            """Write subagent metadata columns for one row."""
            traj_val: object | None = None
            if trajectory is not None:
                traj_val = (
                    sqlalchemy.func.parse_json(trajectory) if dialect in _DIALECTS_WITH_PARSE_JSON else trajectory
                )
            stmt = (
                sqlalchemy.update(sa_table)
                .where(_key_where_clause(key_columns, key_payload))
                .values(
                    {
                        sa_table.c[_COL_EXCEPTION]: exception,
                        sa_table.c[_COL_TRAJECTORY]: traj_val,
                    }
                )
            )
            await self.db_connector.run_query_async(stmt)

        async def _write_row_output(key_payload: dict[str, object], value: object) -> None:
            """Write the subagent's text output to the target row."""
            stmt = (
                sqlalchemy.update(sa_table)
                .where(_key_where_clause(key_columns, key_payload))
                .values({sa_table.c[output_col]: value})
            )
            await self.db_connector.run_query_async(stmt)

        async def _process_one_row(row_idx: int, row: dict[str, object]) -> str | None:
            nonlocal completed
            tools: list[Tool] = []
            browser_tool: WebBrowserTool | None = None
            if enable_browser_tools:
                browser_tool = WebBrowserTool()
                tools.extend(browser_tool.as_pydantic_ai_tools())
            if nested_pa_tool is not None:
                tools.append(nested_pa_tool)
            if run_query_pa_tool is not None:
                tools.append(run_query_pa_tool)

            capabilities: list[AbstractCapability[Any]] = []
            if browser_tool is not None:
                capabilities.append(browser_tool.lifecycle_capability())
            subagent_scope = None
            if offload_enabled:
                assert self.message_store is not None
                subagent_scope = self.message_store.scoped(f"subagent:{call_id}:{row_idx}")
                capabilities.append(
                    MessageStoreCapability(store=subagent_scope, tool_allowlist=BROWSER_TOOL_NAMES)
                )

            subagent = Agent(
                model=self.subagent_llm,
                tools=tools,
                capabilities=capabilities or None,
                output_type=str,
                model_settings=self.model_settings,
            )
            key_payload = {col: row.get(col) for col in key_columns}
            error_msg: str | None = None
            metadata: tuple[str | None, str | None] | None = None
            try:
                prompt = task_template.render(row)
                if subagent_scope is not None:
                    message_id = await subagent_scope.add(kind="user_prompt", content=prompt)
                    if len(prompt) > MESSAGE_THRESHOLD_CHARS:
                        prompt = make_snippet(message_id, prompt)
                result = await subagent.run(prompt)
                await _write_row_output(key_payload, result.output)
                traj = Trajectory.from_pydantic_ai_messages(result.all_messages())
                metadata = (None, traj.model_dump_json())
            except Exception as e:
                exception_msg = f"{type(e).__name__}: {e}"
                error_msg = f"row {row_idx}: {exception_msg}"
                metadata = (exception_msg, None)
            finally:
                if browser_tool is not None:
                    await browser_tool.close()
                if self.store_metadata and metadata is not None:
                    await _save_row_metadata(key_payload, *metadata)
                completed += 1
                if self.on_row_complete is not None:
                    self.on_row_complete(completed, total)
                    await asyncio.sleep(0)
            return error_msg

        rows = df.to_dict(orient="records")
        total = len(rows)
        semaphore = asyncio.Semaphore(self.max_concurrency)

        async def _throttled(row_idx: int, row: dict[str, object]) -> str | None:
            async with semaphore:
                return await _process_one_row(row_idx, row)

        errors = await asyncio.gather(*(_throttled(row_idx, row) for row_idx, row in enumerate(rows, start=1)))
        await self.db_connector.refresh_schema_async()

        error_messages = [e for e in errors if e is not None]
        failed = len(error_messages)
        updated = total - failed
        summary = (
            f"Processed {total} rows from {table_name}; "
            f"subagent updates succeeded for {updated} rows, failed for {failed} rows."
        )
        if error_messages:
            summary += "\nSample errors:\n" + "\n".join(f"- {e}" for e in error_messages[:5])
        if self.store_metadata:
            summary += f"\nMetadata stored in columns {_COL_EXCEPTION}, {_COL_TRAJECTORY} of {table_name}."
        return summary

    def as_pydantic_ai_tool(self) -> Tool:
        """Return pydantic-ai Tool wrapper."""
        return Tool(self.__call__, name=self.name)
