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
from mintq.toolhub.utils import qualified_table as _qualified, sa_table as _sa_table
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
        schema_name: str | None,
        table_name: str,
        *,
        canonical_column: str,
        instruction: str,
        input_column: str,
        reference_schema: str | None = None,
        reference_table: str | None = None,
        reference_column: str | None = None,
        merge_duplicates: bool = False,
    ) -> str:
        """Populate ``canonical_column`` with consistent canonical values per ``instruction``.

        Operates on ``SELECT DISTINCT input_column`` — rows sharing an ``input_column``
        value always receive the same canonical. If two distinct entities can share
        that value (e.g. two ``"John Smith"`` rows), pre-derive a discriminating column
        and pass *that* as ``input_column``.

        ``input_column`` can be the row's own identifier or a foreign attribute (e.g.
        ``"school"`` on a ``students`` table); in the latter case only the named column
        gets canonicalized, the row entity is untouched.

        Mode is selected by ``reference_table``:

        - **normalize_only** (``reference_table`` is ``None``) → independent per-value
          normalization.
        - **dedup_and_normalize** (``(reference_schema, reference_table)`` equals
          ``(schema_name, table_name)``) → cluster variants AND apply one consistent
          canonical per cluster.
        - **resolve** (``reference_table`` points elsewhere) → match each value against
          the reference; on a SAME match, the matched row's ``reference_column`` value
          is written. Unmatched values keep their own value.

        Args:
            schema_name: Schema containing ``table_name``. Pass ``None`` for
                unqualified tables.
            table_name: Table containing both ``input_column`` and ``canonical_column``.
            canonical_column: Existing column to populate. Set equal to ``input_column``
                to canonicalize in place.
            instruction: How to canonicalize / what makes two values refer to the same
                entity. Style guidance belongs here.
            input_column: The column being canonicalized.
            reference_schema: Schema of ``reference_table`` (``None`` if unqualified).
                Ignored when ``reference_table`` is ``None``.
            reference_table: See modes above.
            reference_column: Column on the reference table whose value is written as
                canonical on a SAME match. Required when ``reference_table`` is set
                and points to a different table.
            merge_duplicates: After populating, collapse rows sharing a canonical into
                one via per-column coalesce (most-frequent non-null). **In place** —
                originals are lost; copy first if needed. Only set when ``input_column``
                identifies the row's own entity; never on a foreign attribute.
        """
        if self._db_connector is None:
            return "(error: no workspace database connected)"

        # Determine mode.
        if reference_table is None:
            mode: Mode = "normalize_only"
        elif reference_schema == schema_name and reference_table == table_name:
            mode = "dedup_and_normalize"
        else:
            mode = "resolve"
            if reference_column is None:
                return "(error: reference_column is required when reference_table points to another table)"

        # Shared setup: distinct source values + ensure canonical_column exists.
        distinct_values, error = await self._fetch_distinct_values(schema_name, table_name, input_column)
        if error is not None:
            return error
        if not distinct_values:
            return f"(no values to canonicalize in {_qualified(schema_name, table_name)}.{input_column})"
        error = await self._check_canonical_column(schema_name, table_name, input_column, canonical_column)
        if error is not None:
            return error

        # Dispatch to mode-specific algorithm.
        n_clusters: int | None = None
        if mode == "normalize_only":
            mapping, n_errors = await self._mode_normalize_only(distinct_values, instruction)
        elif mode == "dedup_and_normalize":
            mapping, n_errors, n_clusters = await self._mode_dedup_and_normalize(
                distinct_values, instruction, schema_name, table_name, input_column
            )
        else:
            assert reference_table is not None and reference_column is not None  # validated above
            mapping, n_errors = await self._mode_resolve(
                distinct_values,
                instruction,
                schema_name,
                table_name,
                input_column,
                reference_schema,
                reference_table,
                reference_column,
            )

        # Apply value → canonical mapping in one UPDATE.
        update_error = await self._apply_mapping(
            schema_name=schema_name,
            table_name=table_name,
            input_column=input_column,
            canonical_column=canonical_column,
            mapping=mapping,
        )
        if update_error is not None:
            return (
                f"(error: failed to write canonical_column {canonical_column} to "
                f"{_qualified(schema_name, table_name)}: {update_error})"
            )

        # Optional post-step: collapse rows sharing a canonical into one (in place).
        merged_row_counts: tuple[int, int] | None = None
        if merge_duplicates:
            merged_row_counts, merge_error = await self._merge_duplicates_inplace(
                schema_name, table_name, canonical_column
            )
            if merge_error is not None:
                return merge_error

        # Summary.
        qualified_target = _qualified(schema_name, table_name)
        summary = (
            f"Canonicalized {len(distinct_values)} distinct values in {qualified_target}.{input_column} "
            f"→ {canonical_column} (mode={mode})"
        )
        if n_clusters is not None:
            summary += f"; {n_clusters} entity clusters formed"
        if merged_row_counts is not None:
            before, after = merged_row_counts
            summary += f"; merged {before} rows → {after} in place"
        if n_errors:
            summary += f"; {n_errors} subagent failures (treated as singletons)"
        return summary + "."

    # ------------------------------------------------------------------
    # Shared infrastructure used by the per-mode methods below.
    # ------------------------------------------------------------------

    async def _fetch_distinct_values(
        self, schema_name: str | None, table_name: str, input_column: str
    ) -> tuple[list[str], str | None]:
        """Return distinct non-null values of ``input_column`` (and an optional error message)."""
        assert self._db_connector is not None
        sa_input_table = _sa_table(schema_name, table_name, input_column)
        qualified = _qualified(schema_name, table_name)
        distinct_res = await self._db_connector.run_query_async(
            sqlalchemy.select(sa_input_table.c[input_column])
            .distinct()
            .where(sa_input_table.c[input_column].is_not(None))
        )
        if distinct_res.error is not None or distinct_res.df is None:
            detail = distinct_res.error.message if distinct_res.error else "no dataframe"
            return [], f"(error: failed to read distinct values from {qualified}.{input_column}: {detail})"
        # Positional access; the result column name may be case-folded by some dialects.
        return [str(v) for v in distinct_res.df.iloc[:, 0].dropna().tolist()], None

    async def _check_canonical_column(
        self, schema_name: str | None, table_name: str, input_column: str, canonical_column: str
    ) -> str | None:
        """Verify ``canonical_column`` exists on the target; the tool does not create it."""
        assert self._db_connector is not None
        qualified = _qualified(schema_name, table_name)
        cols_res = await self._db_connector.run_query_async(
            sqlalchemy.select(_sa_table(schema_name, table_name, input_column)).limit(0)
        )
        if cols_res.error is not None or cols_res.df is None:
            detail = cols_res.error.message if cols_res.error else "no dataframe"
            return f"(error: failed to inspect {qualified}: {detail})"
        if canonical_column not in [str(c) for c in cols_res.df.columns]:
            return (
                f"(error: canonical_column {canonical_column!r} does not exist on {qualified}; "
                f"create it first — e.g. ALTER TABLE {qualified} ADD COLUMN {canonical_column} TEXT)"
            )
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
        schema_name: str | None,
        table_name: str,
        input_column: str,
    ) -> tuple[dict[str, str], int, int]:
        """Per-value SAME-peer judgment → cluster on SAME edges → picker per cluster."""
        assert self._db_connector is not None
        run_query_pa_tool = RunQueryTool(self._db_connector).as_pydantic_ai_tool()
        qualified_target = _qualified(schema_name, table_name)

        async def task(value: str) -> _SelfPeersOutput:
            prompt = _SELF_PROMPT.render(
                instruction=instruction,
                table_name=qualified_target,
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
        schema_name: str | None,
        table_name: str,
        input_column: str,
        reference_schema: str | None,
        reference_table: str,
        reference_column: str,
    ) -> tuple[dict[str, str], int]:
        """Resolve each value against the reference table; write matched value or raw fallback."""
        assert self._db_connector is not None
        run_query_pa_tool = RunQueryTool(self._db_connector).as_pydantic_ai_tool()
        qualified_target = _qualified(schema_name, table_name)
        qualified_reference = _qualified(reference_schema, reference_table)

        async def task(value: str) -> _OtherMatchOutput:
            prompt = _OTHER_PROMPT.render(
                instruction=instruction,
                table_name=qualified_target,
                input_column=input_column,
                reference_table=qualified_reference,
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
        schema_name: str | None,
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

            target = _sa_table(schema_name, table_name, input_column, canonical_column)
            map_t = _sa_table(None, mapping_table_name, "input_val", "canonical_val")
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
                    _qualified(schema_name, table_name),
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

    async def _merge_duplicates_inplace(
        self, schema_name: str | None, table_name: str, canonical_column: str
    ) -> tuple[tuple[int, int] | None, str | None]:
        """Collapse rows sharing a canonical into one via per-column coalesce.

        For each non-canonical column the merged row keeps the most-frequent non-null
        value (tie → first). The table is replaced in place.

        Returns ``((rows_before, rows_after), None)`` on success, or ``(None, error_msg)``.
        """
        import pandas as pd

        assert self._db_connector is not None
        qualified = _qualified(schema_name, table_name)

        # Read the whole table.
        target_sa = _sa_table(schema_name, table_name)
        select_stmt = sqlalchemy.select(sqlalchemy.text("*")).select_from(target_sa)
        res = await self._db_connector.run_query_async(select_stmt)
        if res.error is not None or res.df is None:
            detail = res.error.message if res.error else "no dataframe"
            return None, f"(error: failed to read {qualified} for merge_duplicates: {detail})"
        df = res.df
        if df.empty:
            return (0, 0), None
        if canonical_column not in df.columns:
            return None, f"(error: canonical_column {canonical_column!r} not found in {qualified})"

        rows_before = len(df)
        other_cols = [c for c in df.columns if c != canonical_column]
        if not other_cols:
            merged = df.drop_duplicates(subset=[canonical_column]).reset_index(drop=True)
        else:

            def _coalesce(series: pd.Series) -> Any:
                non_null = series.dropna()
                if non_null.empty:
                    return None
                return non_null.value_counts().index[0]

            merged = df.groupby(canonical_column, as_index=False, dropna=False).agg({c: _coalesce for c in other_cols})
        rows_after = len(merged)

        # Write back in place — schema and table go to write_dataframe_async separately.
        try:
            await self._db_connector.write_dataframe_async(
                df=merged, table_name=table_name, schema_name=schema_name, mode="replace"
            )
        except ValueError as e:
            return None, f"(error: failed to write merged {qualified}: {e})"
        return (rows_before, rows_after), None

    def as_pydantic_ai_tool(self) -> Tool:
        """Return pydantic-ai Tool wrapper."""
        return Tool(self.__call__, name=self.name)
