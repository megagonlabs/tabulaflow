"""Enrich database table rows using concurrent subagents."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

import sqlalchemy
from pydantic_ai import RunContext, Tool
from pydantic_ai.models import Model
from pydantic_ai.settings import ModelSettings

from tabulaflow.data.registry import DataConnectorRegistry
from tabulaflow.data.sql import SQLConnector
from tabulaflow.core.schema import SQLDialect
from tabulaflow.agents.trace import Trajectory
from tabulaflow.agents.tools.add_canonical_name import AddCanonicalNameTool
from tabulaflow.agents.tools.protocols import ToolProgressUpdate
from tabulaflow.agents.tools.extract_rows_from_documents import ExtractRowsFromDocumentsTool
from tabulaflow.agents.tools._sql import create_column_model, qualified_table, sa_table
from tabulaflow.agents.message_store import MessageStore
from tabulaflow.agents.enrichment import RowResult, RowRunner, prepare_rows


_COL_EXCEPTION = "_subagent_exception"
_COL_TRAJECTORY = "_subagent_trajectory"
_INTERNAL_COLUMNS = [_COL_EXCEPTION, _COL_TRAJECTORY]

# Dialects that support a native JSON column type and the SQL type name to use.
_JSON_TYPE_FOR_DIALECT: dict[SQLDialect, str] = {
    "snowflake": "VARIANT",
    "postgresql": "JSONB",
    "mysql": "JSON",
    "duckdb": "JSON",
    "bigquery": "JSON",
    "clickhouse": "String",  # no native JSON; fall back to String (≈TEXT)
}


# Dialects that require PARSE_JSON() to store a JSON string into a native column.
_DIALECTS_WITH_PARSE_JSON: set[SQLDialect] = {"snowflake"}

logger = logging.getLogger(__name__)


def _key_where_clause(key_columns: list[str], key_payload: dict[str, object]) -> sqlalchemy.ColumnElement[bool]:
    """Build a SQLAlchemy WHERE clause from key columns."""
    conditions: list[sqlalchemy.ColumnElement[bool]] = []
    for col_name in key_columns:
        val = key_payload[col_name]
        col: sqlalchemy.ColumnClause[object] = sqlalchemy.column(col_name)
        conditions.append(col.is_(None) if val is None else col == val)
    return sqlalchemy.and_(*conditions)


class RunSubagentForEachRowTool:
    """Enrich table rows with concurrent agents and write structured results back.

    Each agent emits one value per configured output column, with types derived
    from the target table. Agents use their supplied row content by default;
    browser, database, and nested-subagent tools can be enabled as needed.
    """

    name: ClassVar[str] = "run_subagent_for_each_row"

    def __init__(
        self,
        connector: SQLConnector,
        *,
        registry: DataConnectorRegistry | None = None,
        message_store: MessageStore | None = None,
        subagent_llm: str | Model = "openai:gpt-5.6-luna",
        model_settings: ModelSettings | None = None,
        max_concurrency: int = 200,
        store_metadata: bool = False,
        trajectory_log_dir: Path | None = None,
    ) -> None:
        """Initialize the tool.

        Args:
            connector: SQL connector for the table being updated (used for
                per-row write-back).
            registry: Optional data-source registry. Required only when callers
                pass ``enable_run_query_tool=True`` so the per-row subagent
                can query any registered data source. If omitted, that flag is
                unavailable.
            message_store: Optional workspace-backed message store. When
                provided, every browser tool return is mirrored here and tagged
                with a ``[message_id=M<n>]`` marker so the agent can reference
                it. For non-leaf subagents (``enable_nested_subagents=True``)
                that also have a ``registry``, oversized prompts and tool
                returns are additionally replaced with head+tail snippets, and
                the subagent gets a registry-backed ``run_query`` tool to read
                the full content back from ``workspace._internal.messages``.
                Without a store, browser returns are neither mirrored nor tagged.
            subagent_llm: LLM identifier or model object used by per-row subagent runs.
            model_settings: Optional pydantic-ai model settings passed to
                each subagent run.
            max_concurrency: Maximum number of row subagents to run
                concurrently.
            store_metadata: If True, write ``_subagent_exception`` and
                ``_subagent_trajectory`` columns back to the target table
                after each row. ``_subagent_exception`` is NULL on success
                and a ``"<ExceptionType>: <message>"`` string on failure.
            trajectory_log_dir: If set, each per-row subagent trajectory is
                written as ``<dir>/<call_id>/row-<N>.md`` after the row
                finishes. Nested subagent instances inherit the same directory
                so their own ``call_id``s appear alongside the parent's.
                Independent of ``store_metadata``: this is a filesystem sink
                for local debugging; ``store_metadata`` writes to the target
                table.
        """
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be greater than 0")
        self.connector = connector
        self.registry = registry
        self.message_store = message_store
        self.subagent_llm = subagent_llm
        self.model_settings = model_settings
        self.max_concurrency = max_concurrency
        self.store_metadata = store_metadata
        self.trajectory_log_dir = trajectory_log_dir
        # Emits one tick per completed row (``completed``/``total``).
        self.on_progress: Callable[[ToolProgressUpdate], None] | None = None

    def apply_llm_profile(self, *, llm: str, model_settings: ModelSettings | None) -> None:
        """Apply the LLM profile used by per-row subagents."""
        self.subagent_llm = llm
        self.model_settings = model_settings

    def apply_execution_limits(self, *, max_concurrency: int) -> None:
        """Apply the concurrency limit used by subsequent calls."""
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be greater than 0")
        self.max_concurrency = max_concurrency

    async def __call__(
        self,
        ctx: RunContext[Any],
        schema_name: str | None,
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

        By default the subagent has no tools: it reads its prompt and emits one value
        per column in ``output_columns`` (via a structured ``submit_answer`` output), and
        this tool writes them back to that row in a single UPDATE. Any field may be
        emitted as NULL — no placeholder strings like ``"N/A"`` are needed. Set
        ``enable_browser_tools=True`` to grant web-browsing tools (plus the
        ``extract_rows_from_documents`` and ``add_canonical_name`` tools, so a row
        that browses can mine pages into structured rows and unify entity variants),
        or ``enable_run_query_tool=True`` to grant a ``run_query`` tool that can query
        and modify any registered data source. Set ``enable_nested_subagents=True`` to
        give the subagent this same tool so it can fan out its own row-wise sub-tasks;
        this does not propagate — each deeper level must set the flag again to nest
        further.

        Images, PDFs, and ordered collections that may mix them are attached to that
        row's prompt automatically. Path-backed media is not fetched; download and
        import its bytes first, or omit the column. Other binary values are rejected
        before any subagents run.

        Safe to call multiple times in parallel in one turn.

        Every subagent has a built-in ``abort_task(message: str)`` tool for
        rows it can't complete; aborted rows are recorded in
        ``_subagent_exception`` and ``output_columns`` are left unwritten.
        Do not instruct it to emit sentinel strings like ``"NOT_COMPLETED"`` —
        describe the successful output only and let it abort otherwise.

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
            schema_name: Schema containing ``table_name`` (``None`` if unqualified).
            table_name: Target table name. Used as the write-back target; per-row
                updates locate rows here via ``key_columns``.
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
                (``{% for %}``, ``{% if %}``) is available. For consistency, state
                in the instruction how missing information should be handled —
                ``abort_task`` (row fails, nothing written) or a NULL field (row
                succeeds with that field null). For JSON columns,
                extract the field or cast to an array in ``task_query`` using
                the dialect's JSON functions rather than relying on the
                template — driver materialization varies (string vs structure)
                and only structured projections iterate reliably. Example:
                ``"Classify the sentiment of: {{ review_text }}"``.
            key_columns: Columns used in the WHERE clause to locate each row in
                ``table_name`` for write-back. Must be real columns of
                ``table_name`` (not computed/joined-only), must appear in the
                ``task_query`` result, and together must form a unique, non-null
                key — one task_query row per target row.
            output_columns: One or more columns to update on ``table_name``; the
                subagent emits a value for each in a single ``submit_answer`` output.
                They need not appear in the ``task_query`` projection. All must
                already exist on ``table_name`` and must be scalar, text, or date
                columns — each value is stored as that column's type (numeric/boolean/
                date → native values; text → text). For list/nested values, target a
                text column holding a JSON string (DuckDB ``JSON`` columns work too).
                Array, struct, map, and binary columns are not valid targets.
            enable_browser_tools: If True, the per-row subagent gets web-browsing
                tools (navigate, click, type, etc.). Each row browses in its own
                isolated tabs (cookies/logins shared). A process-wide tab cap
                throttles this automatically, so fan out freely — no need to
                limit parallelism for browser load. The subagent also receives the
                ``extract_rows_from_documents`` and ``add_canonical_name`` tools
                (the document-mining + canonicalization toolchain), wired to the
                workspace connector — so a browsing row can turn pages into clean
                structured rows end to end.

                When the task hands the subagent a deep link to a results page
                on a large consumer site (Google Flights/Maps, Amazon, booking
                sites) — e.g. ``.../flights/search?tfs=...`` — it can load the
                generic landing page with no results, because the results RPC is
                gated behind in-page interaction. If that happens, have the
                subagent fall back to opening the entry page and submitting the
                search form rather than giving up on the deep link.
            enable_nested_subagents: If True, each per-row subagent additionally
                receives this ``run_subagent_for_each_row`` tool, allowing it
                to fan out further row-wise tasks of its own. The flag does not
                propagate automatically — each nested level must opt in
                explicitly.
            enable_run_query_tool: If True, the per-row subagent additionally
                receives a registry-backed ``run_query`` tool that can query
                and modify any registered data source (the subagent specifies
                ``connector_alias`` per call). Enable it for tasks where row-local
                context isn't enough:

                - **Computing a large output via SQL.** When the value is too
                  large to round-trip through ``submit_answer``, have the subagent
                  ``UPDATE`` the target column itself with ``run_query``, and set
                  ``output_columns`` to a separate small acknowledgment column for
                  ``submit_answer`` to fill. The ``task_instruction`` must give the
                  subagent the ``connector_alias``, ``table_name``, and key columns for
                  its ``WHERE``.
                - **Reads or writes beyond the row.** The subagent reads
                  auxiliary tables for context, or writes to other tables
                  (INSERTs, DDL).
        """
        try:
            return await self.execute(
                schema_name,
                table_name,
                task_query=task_query,
                task_instruction=task_instruction,
                key_columns=key_columns,
                output_columns=output_columns,
                enable_browser_tools=enable_browser_tools,
                enable_nested_subagents=enable_nested_subagents,
                enable_run_query_tool=enable_run_query_tool,
                tool_call_id=ctx.tool_call_id,
            )
        except (ValueError, TypeError, RuntimeError) as exc:
            return f"(error: {exc})"

    async def execute(
        self,
        schema_name: str | None,
        table_name: str,
        *,
        task_query: str,
        task_instruction: str,
        key_columns: list[str],
        output_columns: list[str],
        enable_browser_tools: bool = False,
        enable_nested_subagents: bool = False,
        enable_run_query_tool: bool = False,
        tool_call_id: str | None = None,
    ) -> str:
        """Run row-wise subagents without requiring an agent run context."""
        max_concurrency = self.max_concurrency
        if not output_columns:
            raise ValueError("output_columns must be a non-empty list")

        if not key_columns:
            raise ValueError("key_columns must be a non-empty list naming a unique key of the target table")

        runner = RowRunner(
            llm=self.subagent_llm,
            model_settings=self.model_settings,
            max_concurrency=max_concurrency,
            enable_browser_tools=enable_browser_tools,
            enable_run_query_tool=enable_run_query_tool,
            registry=self.registry,
            message_store=self.message_store,
            truncate_messages=enable_nested_subagents and self.message_store is not None and self.registry is not None,
        )

        select_result = await self.connector.run_query_async(task_query)
        if select_result.error is not None or select_result.df is None:
            detail = select_result.error.message if select_result.error is not None else "no dataframe returned"
            raise RuntimeError(f"failed to evaluate task_query: {detail}")

        df = select_result.df
        all_columns = [str(c) for c in df.columns]
        if not all_columns:
            raise ValueError("task_query returned no columns")

        missing_id = [c for c in key_columns if c not in all_columns]
        if missing_id:
            raise ValueError(f"key_columns not found in task_query result: {missing_id}")

        # Look up the target table's actual columns to validate output_columns and
        # decide whether to ALTER for _subagent_* columns. task_query may project
        # arbitrary computed/joined columns that don't correspond to table_name.
        qualified_target = qualified_table(schema_name, table_name)
        table_columns_result = await self.connector.run_query_async(f"SELECT * FROM {qualified_target} LIMIT 0")
        if table_columns_result.error is not None or table_columns_result.df is None:
            detail = (
                table_columns_result.error.message
                if table_columns_result.error is not None
                else "no dataframe returned"
            )
            raise RuntimeError(f"failed to inspect target table {qualified_target}: {detail}")
        table_columns = [str(c) for c in table_columns_result.df.columns]

        missing_output = [c for c in output_columns if c not in table_columns]
        if missing_output:
            raise ValueError(f"output_columns not found in table {qualified_target}: {missing_output}")

        record_type = create_column_model(self.connector.schema, schema_name, table_name, output_columns, name="Answer")

        # Validate that each key_column can address exactly one target row on
        # write-back (UPDATE ... WHERE key = value). A key that is not a real
        # target-table column can't be matched; a NULL key never matches in SQL
        # (`col = NULL` is unknown); a key duplicated across task_query rows means
        # one subagent's output would overwrite several rows. Each of these
        # silently corrupts or no-ops, so reject them up front.
        key_not_in_table = [c for c in key_columns if c not in table_columns]
        if key_not_in_table:
            raise ValueError(
                f"key_columns must be columns of {qualified_target} for write-back, "
                f"but these are not present there: {key_not_in_table}"
            )
        key_df = df[key_columns]
        if bool(key_df.isnull().to_numpy().any()):
            raise ValueError(
                "key_columns contain NULL values; a NULL key cannot locate its row "
                "for write-back. Use a non-null unique key."
            )
        if bool(key_df.duplicated().any()):
            raise ValueError(
                "key_columns are not unique across task_query rows; one subagent output "
                "would overwrite multiple rows. Project a unique key — e.g. the table's primary "
                "key, or add a row-id column before fan-out."
            )

        rows = prepare_rows(df, task_instruction)
        total = len(rows)

        # Ensure _subagent_* columns exist on the target table.
        dialect = self.connector.language
        trajectory_dtype = _JSON_TYPE_FOR_DIALECT.get(dialect, "TEXT")
        if self.store_metadata:
            for col in _INTERNAL_COLUMNS:
                if col not in table_columns:
                    dtype = trajectory_dtype if col == _COL_TRAJECTORY else "TEXT"
                    await self.connector.run_query_async(f"ALTER TABLE {qualified_target} ADD COLUMN {col} {dtype}")

        tools: list[Tool] = []
        if enable_browser_tools and isinstance(self.connector, SQLConnector):
            tools.append(
                ExtractRowsFromDocumentsTool(
                    self.connector,
                    subagent_llm=self.subagent_llm,
                    model_settings=self.model_settings,
                    max_concurrency=max_concurrency,
                    trajectory_log_dir=self.trajectory_log_dir,
                ).as_pydantic_ai_tool()
            )
            canonical_tool = AddCanonicalNameTool(
                subagent_llm=self.subagent_llm,
                model_settings=self.model_settings,
                max_concurrency=max_concurrency,
                trajectory_log_dir=self.trajectory_log_dir,
            )
            canonical_tool.attach_connector(self.connector)
            tools.append(canonical_tool.as_pydantic_ai_tool())
        if enable_nested_subagents:
            # A fresh instance keeps nested progress separate from the parent.
            tools.append(
                RunSubagentForEachRowTool(
                    self.connector,
                    registry=self.registry,
                    message_store=self.message_store,
                    subagent_llm=self.subagent_llm,
                    model_settings=self.model_settings,
                    max_concurrency=max_concurrency,
                    store_metadata=self.store_metadata,
                    trajectory_log_dir=self.trajectory_log_dir,
                ).as_pydantic_ai_tool()
            )
        call_id = uuid.uuid4().hex[:8]

        completed = 0

        # Build a SQLAlchemy table with all columns referenced in SET clauses.
        sa_col_names: set[str] = set(key_columns) | set(output_columns)
        if self.store_metadata:
            sa_col_names.update(_INTERNAL_COLUMNS)
        sa_target = sa_table(schema_name, table_name, *sa_col_names)

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
                sqlalchemy.update(sa_target)
                .where(_key_where_clause(key_columns, key_payload))
                .values(
                    {
                        sa_target.c[_COL_EXCEPTION]: exception,
                        sa_target.c[_COL_TRAJECTORY]: traj_val,
                    }
                )
            )
            res = await self.connector.run_query_async(stmt)
            if res.error is not None:
                logger.warning("Failed to write subagent metadata for %s: %s", key_payload, res.error.message)

        async def _write_row_output(key_payload: dict[str, object], output: dict[str, Any]) -> str | None:
            """Write the subagent's structured output across ``output_columns``.

            Sets every output column in one UPDATE (a field left
            ``None`` is written as NULL). Returns ``None`` on success or the
            database error message if the write failed (e.g. a value's type can't
            be stored), so the caller can record the row as failed instead of
            silently reporting success.
            """
            stmt = (
                sqlalchemy.update(sa_target)
                .where(_key_where_clause(key_columns, key_payload))
                .values({sa_target.c[c]: output[c] for c in output_columns})
            )
            res = await self.connector.run_query_async(stmt)
            if res.error is not None:
                return res.error.message
            # affected_rows != 1 means the key located the wrong number of rows:
            # 0 = the value didn't round-trip to a match (e.g. a fragile key type),
            # >1 = a non-unique key (should be caught up front, but verify). When
            # the driver doesn't report a count (None), trust the prior validation.
            if res.affected_rows is not None and res.affected_rows != 1:
                return f"write matched {res.affected_rows} rows (expected 1); key may not address a single row"
            return None

        traj_dir: Path | None = None
        if self.trajectory_log_dir is not None:
            traj_dir = self.trajectory_log_dir / call_id
            try:
                traj_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                logger.exception("Failed to create subagent trajectory dir: %s", traj_dir)
                traj_dir = None

        def _write_trajectory_file(row_idx: int, trajectory: Trajectory | None) -> None:
            if traj_dir is None or trajectory is None:
                return
            path = traj_dir / f"row-{row_idx}.md"
            try:
                path.write_text(trajectory.to_markdown(), encoding="utf-8")
            except Exception:
                logger.exception("Failed to write subagent trajectory file: %s", path)

        errors: list[str | None] = [None] * total

        async def _save_result(position: int, result: RowResult) -> None:
            nonlocal completed
            row_idx = position + 1
            key_payload = {column: rows[position].values[column] for column in key_columns}
            error = result.error
            trajectory = None
            try:
                if result.run_result is not None and (self.store_metadata or traj_dir is not None):
                    trajectory = Trajectory.from_pydantic_ai_messages(result.run_result.all_messages())
                    _write_trajectory_file(row_idx, trajectory)
                if error is None and result.run_result is not None:
                    output = result.run_result.output
                    values = {name: getattr(output, name) for name in record_type.model_fields}
                    write_error = await _write_row_output(key_payload, values)
                    if write_error is not None:
                        error = f"write-back failed: {write_error}"
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
            if self.store_metadata:
                await _save_row_metadata(
                    key_payload, error, trajectory.model_dump_json() if trajectory is not None else None
                )
            errors[position] = f"row {row_idx}: {error}" if error is not None else None
            completed += 1
            if self.on_progress is not None:
                self.on_progress(ToolProgressUpdate(completed=completed, total=total, tool_call_id=tool_call_id))
                await asyncio.sleep(0)

        if self.on_progress is not None and total > 0:
            self.on_progress(ToolProgressUpdate(completed=0, total=total, tool_call_id=tool_call_id))
        await runner.run(
            rows,
            record_type=record_type,
            on_result=_save_result,
            tools=tools,
            fanout_tool_names=frozenset({self.name}) if enable_nested_subagents else frozenset(),
            call_id=call_id,
        )
        await self.connector.refresh_schema_async()

        error_messages = [e for e in errors if e is not None]
        failed = len(error_messages)
        updated = total - failed
        summary = (
            f"Processed {total} rows from {qualified_target}; "
            f"subagent updates succeeded for {updated} rows, failed for {failed} rows."
        )
        if error_messages:
            summary += "\nSample errors:\n" + "\n".join(f"- {e}" for e in error_messages[:5])
        if self.store_metadata:
            summary += f"\nMetadata stored in columns {_COL_EXCEPTION}, {_COL_TRAJECTORY} of {qualified_target}."
        return summary

    def as_pydantic_ai_tool(self) -> Tool:
        """Return pydantic-ai Tool wrapper."""
        return Tool(self.__call__, name=self.name)
