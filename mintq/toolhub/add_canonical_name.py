"""Add a canonical name column to a table — normalize_only, dedup_and_normalize, or resolve."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from typing import Any, ClassVar, Literal

import jinja2
import sqlalchemy
from pydantic import BaseModel, Field
from pydantic_ai import Agent, Tool
from pydantic_ai.settings import ModelSettings

from mintq.db_connector.sql_conn import SQLConnector
from mintq.toolhub.run_query import RunQueryTool

logger = logging.getLogger(__name__)

Mode = Literal["normalize_only", "dedup_and_normalize", "resolve"]


class _CanonicalOutput(BaseModel):
    """LLM output for normalize_only mode and the per-cluster canonical picker."""

    canonical: str = Field(description="The canonical name for the value(s) provided.")


class _SelfPeersOutput(BaseModel):
    """LLM output for dedup_and_normalize mode: other values judged SAME entity."""

    same_as: list[str] = Field(
        description=(
            "Other values from the same column that refer to the SAME real-world entity. "
            "Only include values you are confident are SAME (not DIFFERENT, not just UNDECIDED). "
            "Exclude the input value itself."
        )
    )


class _OtherMatchOutput(BaseModel):
    """LLM output for resolve mode: the matched reference value or null."""

    match: str | None = Field(
        description=(
            "The matched reference row's value to write as canonical, or null if no confident match. "
            "Only commit to a match when the evidence supports SAME."
        )
    )


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_JINJA_ENV = jinja2.Environment(undefined=jinja2.StrictUndefined)

# Cap on how many cluster members the picker LLM sees in one call. Real same-entity
# clusters are typically small (2–20). A runaway cluster (over-confident SAME chains)
# would otherwise inflate prompt size unbounded — sample the richest members instead.
_PICKER_MAX_MEMBERS = 100

# Used for normalize_only mode (one value) and the canonical picker (one or many cluster members).
_CANONICALIZE_PROMPT = _JINJA_ENV.from_string("""\
Produce the canonical name for the value(s) below per the instruction.
Multiple values mean they all refer to the same real-world entity; pick or generate one
canonical form for them. Follow the instruction's style consistently across calls so every
canonical name has the same style. Return only the canonical string.

Instruction: {{ instruction }}

Values:
{% for v in values %}- {{ v }}
{% endfor %}""")

# The three-valued rule is what keeps the algorithm from silently merging under
# insufficient evidence — only SAME commits; UNDECIDED and DIFFERENT do not.
_SELF_PROMPT = _JINJA_ENV.from_string("""\
Find values from {{ table_name }}.{{ input_column }} that refer to the SAME real-world entity
as {{ value }}.

Identity rule: {{ instruction }}

For each candidate use a three-valued judgment: SAME (commit), DIFFERENT (rule out), or
UNDECIDED (insufficient evidence). Only report SAME candidates — treat DIFFERENT and
UNDECIDED both as not included.

Use `run_query` to search {{ table_name }}.{{ input_column }} for candidate matches; you may
consult any other columns of {{ table_name }} to disambiguate. Do not include {{ value }} itself.""")

_OTHER_PROMPT = _JINJA_ENV.from_string("""\
Resolve {{ value }} from {{ table_name }}.{{ input_column }} against {{ reference_table }} —
find the row in {{ reference_table }} that refers to the SAME real-world entity.

Identity rule: {{ instruction }}

Use a three-valued judgment: SAME (commit to the match), DIFFERENT (rule out), or UNDECIDED
(insufficient evidence). Only return a matched value on a SAME judgment; otherwise return null.

Use `run_query` to search {{ reference_table }} (consult any of its columns).
On a SAME match, return the matched row's {{ reference_column }} value.""")


def _connected_components(nodes: list[str], edges: dict[str, set[str]]) -> list[set[str]]:
    """Find connected components from a symmetric adjacency map."""
    visited: set[str] = set()
    components: list[set[str]] = []
    for start in nodes:
        if start in visited:
            continue
        component: set[str] = set()
        stack = [start]
        while stack:
            n = stack.pop()
            if n in visited:
                continue
            visited.add(n)
            component.add(n)
            for neighbor in edges.get(n, ()):
                if neighbor not in visited:
                    stack.append(neighbor)
        components.append(component)
    return components


def _sa_table(name: str, *columns: str) -> sqlalchemy.TableClause:
    """Build a SQLAlchemy table clause from a possibly schema-qualified name.

    Splitting on a single ``.`` lets SQLAlchemy emit dialect-correct quoting via
    its ``schema`` argument, rather than us hand-building ``"schema"."table"``.
    """
    sa_cols: list[sqlalchemy.ColumnClause[Any]] = [sqlalchemy.column(c) for c in columns]
    if "." in name:
        schema, _, tbl = name.rpartition(".")
        return sqlalchemy.table(tbl, *sa_cols, schema=schema)
    return sqlalchemy.table(name, *sa_cols)


def _add_text_column_ddl(table_name: str, column_name: str) -> sqlalchemy.TextClause:
    """Build an ``ALTER TABLE … ADD COLUMN <name> TEXT`` statement.

    SQLAlchemy core has no high-level ``ALTER … ADD COLUMN`` builder (alembic owns
    that), so we render text with double-quote escaping. Correct for the dialects
    in use here (DuckDB / Postgres / SQLite / Snowflake) — MySQL would need
    backticks.
    """

    def q(name: str) -> str:
        return '"' + name.replace('"', '""') + '"'

    quoted_table = ".".join(q(p) for p in table_name.split("."))
    return sqlalchemy.text(f"ALTER TABLE {quoted_table} ADD COLUMN {q(column_name)} TEXT")


class AddCanonicalNameTool:
    """Add a canonical name column to a table — three modes via ``reference_table``.

    - **normalize_only** (``reference_table`` is ``None``): per-value normalization with
      no cross-row evidence. The LLM rewrites each distinct value per ``instruction``
      (lowercasing, expanding abbreviations, stripping suffixes).
    - **dedup_and_normalize** (``reference_table == table_name``): clusters variants
      that refer to the same real-world entity AND applies one consistent canonical
      name per cluster. Uses per-value SAME-judgment to build the cluster graph and
      one picker call per cluster.
    - **resolve** (``reference_table`` is another table): each distinct value is
      matched against ``reference_table``; on a SAME match, the matched row's
      ``reference_column`` value is written as the canonical. Unmatched values keep
      their own value.

    The algorithm operates on ``SELECT DISTINCT input_column`` and applies the
    resulting value→canonical mapping back to all rows in one SQL UPDATE.
    """

    name: ClassVar[str] = "add_canonical_name"

    def __init__(
        self,
        *,
        subagent_llm: str = "openai-responses:gpt-5-mini",
        model_settings: ModelSettings | None = None,
        max_concurrency: int = 200,
    ) -> None:
        """Initialize the tool.

        Args:
            subagent_llm: LLM identifier used by per-value and per-cluster subagents.
            model_settings: Optional pydantic-ai settings passed to subagent runs.
            max_concurrency: Maximum number of per-value subagents running
                concurrently across one call.
        """
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be greater than 0")
        self.subagent_llm = subagent_llm
        self.model_settings = model_settings
        self.max_concurrency = max_concurrency
        self._db_connector: SQLConnector | None = None
        self.on_progress: Callable[[int, int], None] | None = None

    def attach_connector(self, connector: SQLConnector) -> None:
        """Bind the workspace connector after construction (mirrors QueryHistory)."""
        self._db_connector = connector

    async def __call__(
        self,
        table_name: str,
        *,
        canonical_column: str,
        instruction: str,
        input_column: str,
        reference_table: str | None = None,
        reference_column: str | None = None,
    ) -> str:
        """Add ``canonical_column`` to ``table_name`` with consistent canonical values.

        Use this tool to standardize a column whose values are noisy variants of the
        same underlying entities — product names, school names, brand names, person
        names. Behavior is selected by ``reference_table``:

        - **normalize_only** (``reference_table`` is ``None``) → normalize each
          distinct value per ``instruction`` (lowercasing, expanding abbreviations,
          stripping packaging/unit suffixes). Use when the noise is purely formatting.
        - **dedup_and_normalize** (``reference_table = table_name``) → cluster
          variants within the table AND apply one consistent canonical name per
          cluster. Use when the column has multiple surface forms of the same
          entities.
        - **resolve** (``reference_table`` = another table) → resolve each value
          into the reference table's vocabulary. The reference table is treated as
          a clean catalog; on a confident match, the matched row's
          ``reference_column`` value is written. Use for semantic joins (n:1) and
          for canonicalizing against an authoritative source.

        **Implicit grouping by ``input_column``.** The tool operates on
        ``SELECT DISTINCT input_column``, so rows that share an exact ``input_column``
        value are automatically treated as the same entity and always receive the same
        canonical, regardless of differences in other columns. If two genuinely distinct
        entities can share an ``input_column`` value (e.g. two people both named
        ``"John Smith"``), pre-derive a discriminating column and pass *that* as
        ``input_column`` instead.

        Args:
            table_name: Table to add the canonical column to. The column is
                appended if it does not already exist.
            canonical_column: Name of the new column to populate. Created with type
                TEXT if missing. Set equal to ``input_column`` to canonicalize in
                place.
            instruction: Natural-language description of how to canonicalize and
                what makes two values refer to the same entity. Style guidance
                (e.g. "always use the official institution name; expand
                abbreviations") goes here.
            input_column: The column whose values are being canonicalized.
            reference_table: ``None`` for normalize_only, the same table for
                dedup_and_normalize, or another table for resolve. Default ``None``.
            reference_column: The reference table column whose value gets written
                as canonical when a match is found. **Required** in resolve mode
                (e.g. ``reference_column="school_id"`` to write a key, or
                ``reference_column="school"`` when matching on the same column
                name). Ignored in normalize_only / dedup_and_normalize modes.
        """
        if self._db_connector is None:
            return "(error: no workspace database connected)"

        # Determine mode.
        if reference_table is None:
            mode: Mode = "normalize_only"
        elif reference_table == table_name:
            mode = "dedup_and_normalize"
        else:
            mode = "resolve"
            if reference_column is None:
                return "(error: reference_column is required when reference_table points to another table)"

        # Shared setup: distinct source values + ensure canonical_column exists.
        distinct_values, error = await self._fetch_distinct_values(table_name, input_column)
        if error is not None:
            return error
        if not distinct_values:
            return f"(no values to canonicalize in {table_name}.{input_column})"
        error = await self._ensure_canonical_column(table_name, input_column, canonical_column)
        if error is not None:
            return error

        # Dispatch to mode-specific algorithm.
        n_clusters: int | None = None
        if mode == "normalize_only":
            mapping, n_errors = await self._mode_normalize_only(distinct_values, instruction)
        elif mode == "dedup_and_normalize":
            mapping, n_errors, n_clusters = await self._mode_dedup_and_normalize(
                distinct_values, instruction, table_name, input_column
            )
        else:
            assert reference_table is not None and reference_column is not None  # validated above
            mapping, n_errors = await self._mode_resolve(
                distinct_values, instruction, table_name, input_column, reference_table, reference_column
            )

        # Apply value → canonical mapping in one UPDATE.
        update_error = await self._apply_mapping(
            table_name=table_name,
            input_column=input_column,
            canonical_column=canonical_column,
            mapping=mapping,
        )
        if update_error is not None:
            return f"(error: failed to write canonical_column {canonical_column} to {table_name}: {update_error})"

        # Summary.
        summary = (
            f"Canonicalized {len(distinct_values)} distinct values in {table_name}.{input_column} "
            f"→ {canonical_column} (mode={mode})"
        )
        if n_clusters is not None:
            summary += f"; {n_clusters} entity clusters formed"
        if n_errors:
            summary += f"; {n_errors} subagent failures (treated as singletons)"
        return summary + "."

    # ------------------------------------------------------------------
    # Shared infrastructure used by the per-mode methods below.
    # ------------------------------------------------------------------

    async def _fetch_distinct_values(self, table_name: str, input_column: str) -> tuple[list[str], str | None]:
        """Return distinct non-null values of ``input_column`` (and an optional error message)."""
        assert self._db_connector is not None
        sa_input_table = _sa_table(table_name, input_column)
        distinct_res = await self._db_connector.run_query_async(
            sqlalchemy.select(sa_input_table.c[input_column])
            .distinct()
            .where(sa_input_table.c[input_column].is_not(None))
        )
        if distinct_res.error is not None or distinct_res.df is None:
            detail = distinct_res.error.message if distinct_res.error else "no dataframe"
            return [], f"(error: failed to read distinct values from {table_name}.{input_column}: {detail})"
        # Positional access; the result column name may be case-folded by some dialects.
        return [str(v) for v in distinct_res.df.iloc[:, 0].dropna().tolist()], None

    async def _ensure_canonical_column(self, table_name: str, input_column: str, canonical_column: str) -> str | None:
        """Ensure ``canonical_column`` exists on ``table_name``; ALTER TABLE if missing."""
        assert self._db_connector is not None
        cols_res = await self._db_connector.run_query_async(
            sqlalchemy.select(_sa_table(table_name, input_column)).limit(0)
        )
        if cols_res.error is not None or cols_res.df is None:
            detail = cols_res.error.message if cols_res.error else "no dataframe"
            return f"(error: failed to inspect {table_name}: {detail})"
        if canonical_column in [str(c) for c in cols_res.df.columns]:
            return None
        alter_res = await self._db_connector.run_query_async(_add_text_column_ddl(table_name, canonical_column))
        if alter_res.error is not None:
            return f"(error: failed to add column {canonical_column} to {table_name}: {alter_res.error.message})"
        return None

    async def _run_per_value(
        self,
        distinct_values: list[str],
        task: Callable[[str], Any],
        on_failure: Callable[[str], Any],
    ) -> tuple[list[Any], int]:
        """Run ``task`` per distinct value concurrently with progress + cancellation handling.

        ``on_failure(value)`` provides the fallback result when ``task(value)`` raises a
        non-cancellation Exception. Returns ``(results, n_errors)``.
        """
        semaphore = asyncio.Semaphore(self.max_concurrency)
        total = len(distinct_values)
        completed = 0
        n_errors = 0

        async def _wrap(value: str) -> Any:
            nonlocal completed, n_errors
            cancelled = False
            try:
                async with semaphore:
                    return await task(value)
            except asyncio.CancelledError:
                cancelled = True
                raise
            except Exception:
                logger.exception("subagent failed for value %r", value)
                n_errors += 1
                return on_failure(value)
            finally:
                # Skip on cancellation — counting cancelled tasks misleads progress,
                # and awaiting in a finally during cancel can re-raise out of teardown.
                if not cancelled:
                    completed += 1
                    if self.on_progress is not None:
                        self.on_progress(completed, total)
                        await asyncio.sleep(0)

        results = await asyncio.gather(*(_wrap(v) for v in distinct_values))
        return results, n_errors

    # ------------------------------------------------------------------
    # Per-mode algorithms. Each owns its prompt, output type, failure
    # default, and mapping construction.
    # ------------------------------------------------------------------

    async def _mode_normalize_only(self, distinct_values: list[str], instruction: str) -> tuple[dict[str, str], int]:
        """Normalize each distinct value via the picker (each value as a singleton cluster).

        ``_pick_canonical`` has its own longest-member fallback on failure, so ``n_errors``
        from ``_run_per_value`` is effectively always 0 here; failures are still logged.
        """

        async def task(value: str) -> str:
            return await self._pick_canonical({value}, instruction)

        results, n_errors = await self._run_per_value(distinct_values, task, on_failure=lambda v: v)
        return dict(zip(distinct_values, results)), n_errors

    async def _mode_dedup_and_normalize(
        self,
        distinct_values: list[str],
        instruction: str,
        table_name: str,
        input_column: str,
    ) -> tuple[dict[str, str], int, int]:
        """Per-value SAME-peer judgment → cluster on SAME edges → picker per cluster."""
        assert self._db_connector is not None
        run_query_pa_tool = RunQueryTool(self._db_connector).as_pydantic_ai_tool()

        async def task(value: str) -> _SelfPeersOutput:
            prompt = _SELF_PROMPT.render(
                instruction=instruction,
                table_name=table_name,
                input_column=input_column,
                value=value,
            )
            subagent = Agent(
                model=self.subagent_llm,
                tools=[run_query_pa_tool],
                output_type=_SelfPeersOutput,
                model_settings=self.model_settings,
            )
            result = await subagent.run(prompt)
            return result.output

        results, n_errors = await self._run_per_value(
            distinct_values,
            task,
            on_failure=lambda v: _SelfPeersOutput(same_as=[]),
        )

        # Build symmetric SAME-edge graph; find connected components.
        value_set = set(distinct_values)
        edges: dict[str, set[str]] = {v: set() for v in distinct_values}
        for v, r in zip(distinct_values, results):
            for peer in r.same_as:
                p = str(peer)
                if p == v or p not in value_set:
                    continue
                edges[v].add(p)
                edges[p].add(v)
        clusters = _connected_components(distinct_values, edges)

        # One picker call per cluster — shared canonical across all members.
        cluster_canonicals = await asyncio.gather(*(self._pick_canonical(cluster, instruction) for cluster in clusters))
        mapping: dict[str, str] = {}
        for cluster, canonical in zip(clusters, cluster_canonicals):
            for v in cluster:
                mapping[v] = canonical
        return mapping, n_errors, len(clusters)

    async def _mode_resolve(
        self,
        distinct_values: list[str],
        instruction: str,
        table_name: str,
        input_column: str,
        reference_table: str,
        reference_column: str,
    ) -> tuple[dict[str, str], int]:
        """Resolve each value against ``reference_table``; write matched value or raw fallback."""
        assert self._db_connector is not None
        run_query_pa_tool = RunQueryTool(self._db_connector).as_pydantic_ai_tool()

        async def task(value: str) -> _OtherMatchOutput:
            prompt = _OTHER_PROMPT.render(
                instruction=instruction,
                table_name=table_name,
                input_column=input_column,
                reference_table=reference_table,
                reference_column=reference_column,
                value=value,
            )
            subagent = Agent(
                model=self.subagent_llm,
                tools=[run_query_pa_tool],
                output_type=_OtherMatchOutput,
                model_settings=self.model_settings,
            )
            result = await subagent.run(prompt)
            return result.output

        results, n_errors = await self._run_per_value(
            distinct_values,
            task,
            on_failure=lambda v: _OtherMatchOutput(match=None),
        )
        mapping = {v: (r.match if r.match is not None else v) for v, r in zip(distinct_values, results)}
        return mapping, n_errors

    async def _pick_canonical(self, cluster: set[str], instruction: str) -> str:
        """One LLM call per SAME-cluster to pick or generate the canonical name."""
        # Sort by length desc so a cap-truncation keeps the richest surface forms,
        # and the fallback (``members[0]``) is the longest member.
        members = sorted(cluster, key=len, reverse=True)
        if len(members) > _PICKER_MAX_MEMBERS:
            logger.info("Picker cluster has %d members; sampling %d longest", len(members), _PICKER_MAX_MEMBERS)
        prompt = _CANONICALIZE_PROMPT.render(instruction=instruction, values=members[:_PICKER_MAX_MEMBERS])
        subagent = Agent(
            model=self.subagent_llm,
            output_type=_CanonicalOutput,
            model_settings=self.model_settings,
        )
        try:
            result = await subagent.run(prompt)
            return result.output.canonical
        except Exception:
            logger.exception("picker failed for cluster %r", members)
            return members[0]  # fallback: use the first member

    async def _apply_mapping(
        self,
        *,
        table_name: str,
        input_column: str,
        canonical_column: str,
        mapping: dict[str, str],
    ) -> str | None:
        """Apply value → canonical mapping via a temp mapping table + JOIN UPDATE.

        Scales as O(M + N) — M target rows, N mapping entries — independent of
        statement size, so mappings into the tens of thousands stay tractable.
        SQLAlchemy emits dialect-correct JOIN-UPDATE (``UPDATE … FROM …`` on
        DuckDB / Postgres, ``UPDATE … JOIN …`` on MySQL).

        Returns ``None`` on success, or the error message if the UPDATE failed.
        """
        import pandas as pd

        assert self._db_connector is not None
        if not mapping:
            return None

        # Throwaway mapping table; unique name avoids collisions with concurrent calls.
        mapping_table_name = f"_canonical_mapping_{uuid.uuid4().hex[:12]}"
        try:
            mapping_df = pd.DataFrame(list(mapping.items()), columns=["input_val", "canonical_val"])
            await self._db_connector.write_dataframe_async(df=mapping_df, table_name=mapping_table_name, mode="replace")

            target = _sa_table(table_name, input_column, canonical_column)
            map_t = _sa_table(mapping_table_name, "input_val", "canonical_val")
            stmt = (
                sqlalchemy.update(target)
                .values({target.c[canonical_column]: map_t.c.canonical_val})
                .where(target.c[input_column] == map_t.c.input_val)
            )
            result = await self._db_connector.run_query_async(stmt)
            if result.error is not None:
                logger.warning(
                    "UPDATE for canonical_column %s on %s failed: %s",
                    canonical_column,
                    table_name,
                    result.error.message,
                )
                return result.error.message
            return None
        finally:
            # Best-effort cleanup of the mapping table.
            try:
                await self._db_connector.run_query_async(
                    sqlalchemy.text(f'DROP TABLE IF EXISTS "{mapping_table_name}"')
                )
            except Exception:
                logger.exception("Failed to drop mapping table %s", mapping_table_name)

    def as_pydantic_ai_tool(self) -> Tool:
        """Return pydantic-ai Tool wrapper."""
        return Tool(self.__call__, name=self.name)
