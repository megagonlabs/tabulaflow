"""Add a canonical name column to a table by clustering same-entity variants."""

from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

import jinja2
import sqlalchemy
from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, Tool
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.settings import ModelSettings

from tabulaflow.core.db_connector.sql_conn import SQLConnector
from tabulaflow.core.types import Trajectory
from tabulaflow.toolhub.utils import qualified_table, sa_table
from tabulaflow.toolhub.run_query import RunQueryTool
from tabulaflow.core.llm import make_agent

logger = logging.getLogger(__name__)


class _CanonicalOutput(BaseModel):
    """LLM output for the per-cluster canonical picker."""

    canonical: str = Field(description="The canonical name for the value(s) provided.")


class _DisambiguationOutput(BaseModel):
    """LLM output when multiple clusters collided on the same canonical name."""

    names: list[str] = Field(
        description=(
            "One distinct canonical name per colliding group, in the same order the groups "
            "were listed. Length must equal the number of groups."
        )
    )


class _ResolvePeersOutput(BaseModel):
    """LLM output per value: other values judged SAME entity."""

    same_as: list[str] = Field(
        description=(
            "Other values from the same column that refer to the SAME real-world entity. "
            "Only include values you are confident are SAME (not DIFFERENT, not just UNDECIDED). "
            "Exclude the input value itself."
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

# How many times to re-prompt the disambiguator with feedback before giving up.
# After max retries the tool surfaces a hard error rather than silently emit
# non-instruction-following names — caller must enrich input_column or instruction.
_MAX_DISAMBIGUATE_RETRIES = 3

# Cap on how many clusters one disambiguation call handles. Larger collision groups
# are split into sequential batches; each batch's outputs are added to ``seen``
# before the next, so cross-batch collisions are caught by the validator.
_DISAMBIGUATE_BATCH_SIZE = 20

# Cap on how many already-claimed canonicals are rendered into the prompt. The
# validator still enforces the full ``seen`` set; this only bounds prompt size
# when ``seen`` grows large (many singleton non-colliding clusters).
_DISAMBIGUATE_SEEN_SHOWN = 200

# The canonical picker — one or many cluster members, one canonical name out.
_CANONICALIZE_PROMPT = _JINJA_ENV.from_string("""\
Produce the canonical name for the value(s) below per the instruction.
Multiple values mean they all refer to the same real-world entity; pick or generate one
canonical form for them. Follow the instruction's style consistently across calls so every
canonical name has the same style. Return only the canonical string.

<instruction>
{{ instruction }}
</instruction>

{% for v in values %}<value>
{{ v }}
</value>
{% endfor %}""")

# The three-valued rule is what keeps the algorithm from silently merging under
# insufficient evidence — only SAME commits; UNDECIDED and DIFFERENT do not.
_RESOLVE_PROMPT = _JINJA_ENV.from_string("""\
Find values from {{ table_name }}.{{ input_column }} that refer to the SAME real-world entity
as the value below.

<value>
{{ value }}
</value>

<instruction>
{{ instruction }}
</instruction>

For each candidate use a three-valued judgment: SAME (commit), DIFFERENT (rule out), or
UNDECIDED (insufficient evidence). Only report SAME candidates — treat DIFFERENT and
UNDECIDED both as not included.

Use `run_query` to search {{ table_name }}.{{ input_column }} for candidate matches; you may
consult any other columns of {{ table_name }} to disambiguate. Do not include the value above itself.""")

_DISAMBIGUATE_PROMPT = _JINJA_ENV.from_string("""\
The {{ groups | length }} groups below were each judged to refer to a DISTINCT real-world entity,
but the canonical-naming step produced the same name {{ collided }} for all of them.
Produce {{ groups | length }} distinct canonical names — one per group, in the same order —
preserving the instruction's style. Each name must be:
- Distinct from the other names in your response (no duplicates among the {{ groups | length }} returned).
- NOT equal to any name in this list of already-claimed canonicals from other clusters:
  {{ seen_list }}

<instruction>
{{ instruction }}
</instruction>

{% for members in groups %}Group {{ loop.index }}: {{ members | join(", ") }}
{% endfor %}
Use `run_query` to consult {{ table_name }} for distinguishing attributes (other columns of
{{ table_name }}, joined as needed) if the member strings alone do not uniquely characterize each
group. The members above are values from {{ table_name }}.{{ input_column }}.""")


def _relevant_seen(collided: str, seen: set[str], n: int) -> list[str]:
    """Return up to ``n`` names from ``seen``, ranked by token overlap with ``collided``.

    Score = number of lowercase whitespace-tokens shared with ``collided``; ties broken
    alphabetically. Used to bound the disambiguator prompt size when ``seen`` is
    large — the validator still enforces the full ``seen`` set, so this is a
    prompt-size heuristic, not a correctness constraint.
    """
    if len(seen) <= n:
        return sorted(seen)
    tokens = set(collided.lower().split())
    scored = [(-len(tokens & set(s.lower().split())), s) for s in seen]
    scored.sort()
    return [s for _, s in scored[:n]]


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
    """Cluster same-entity variants in ``input_column`` and write one canonical name per cluster.

    Per-value SAME-judgment (with cross-row evidence via ``run_query``) builds a SAME-edge
    graph over the distinct values; connected components are the clusters; one picker call
    per cluster produces the canonical name; cross-cluster name collisions are resolved by
    an LLM-disambiguation pass that knows the already-claimed canonicals and is re-prompted
    with feedback on validation failure (no synthetic suffix fallback — if disambiguation
    fails after retries, the call returns a hard error). The value→canonical mapping is
    applied to all rows in one SQL UPDATE.

    **Guarantee:** every cluster gets a globally unique canonical name within one call.
    The validator on the disambiguation step enforces this; if the LLM cannot produce
    distinct names after retries, the call hard-fails rather than silently emitting
    duplicates. Downstream joins on ``canonical_column`` and the ``merge_duplicates``
    post-step both rely on this invariant.

    For *row-independent* transformations — per-value normalization with no cross-row
    evidence, or resolving values against a separate reference table — use
    ``run_subagent_for_each_row`` with ``task_query="SELECT DISTINCT col FROM tbl"`` and
    ``key_columns=[col]`` instead. This tool owns only the cross-row clustering case.
    """

    name: ClassVar[str] = "add_canonical_name"

    def __init__(
        self,
        *,
        subagent_llm: str = "openai-responses:gpt-5-mini",
        model_settings: ModelSettings | None = None,
        max_concurrency: int = 200,
        trajectory_log_dir: Path | None = None,
    ) -> None:
        """Initialize the tool.

        Args:
            subagent_llm: LLM identifier used by per-value and per-cluster subagents.
            model_settings: Optional pydantic-ai settings passed to subagent runs.
            max_concurrency: Maximum number of per-value subagents running
                concurrently across one call.
            trajectory_log_dir: If set, each subagent trajectory is persisted as
                ``<dir>/<call_id>/<role>-<idx>.md`` where ``role`` is one of
                ``resolve``, ``picker``, or ``disambiguate``. Useful for
                debugging clustering and disambiguation decisions.
        """
        if max_concurrency <= 0:
            raise ValueError("max_concurrency must be greater than 0")
        self.subagent_llm = subagent_llm
        self.model_settings = model_settings
        self.max_concurrency = max_concurrency
        self.trajectory_log_dir = trajectory_log_dir
        self._db_connector: SQLConnector | None = None
        # Called as ``on_progress(stage, completed, total)`` where ``stage`` is one
        # of ``"resolve"``, ``"canonicalize"``, ``"disambiguate"``. Disambiguate ticks per
        # batch and is only emitted when collisions exist.
        self.on_progress: Callable[[str, int, int], None] | None = None

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
        merge_duplicates: bool = False,
    ) -> str:
        """Cluster variants in ``input_column`` and populate ``canonical_column`` per cluster.

        Operates on ``SELECT DISTINCT input_column`` — rows sharing an ``input_column``
        value always receive the same canonical. If two distinct entities can share
        that value (e.g. two ``"John Smith"`` rows), pre-derive a discriminating column
        and pass *that* as ``input_column``.

        ``input_column`` can be the row's own identifier or a foreign attribute (e.g.
        ``"school"`` on a ``students`` table); in the latter case only the named column
        gets canonicalized, the row entity is untouched.

        Use this tool when variants of the same entity exist *within the same column* and
        need to be unified (e.g. ``"Microsoft"``, ``"MSFT"``, ``"Microsoft Corp"`` →
        ``"Microsoft Corporation"``). For per-value normalization with no cross-row
        evidence, or for matching values against a separate reference table, use
        ``run_subagent_for_each_row`` instead — pass ``task_query="SELECT DISTINCT col
        FROM tbl"`` and ``key_columns=[col]`` to keep the one-LLM-call-per-distinct-value
        property.

        Args:
            schema_name: Schema containing ``table_name``. Pass ``None`` for
                unqualified tables.
            table_name: Table containing both ``input_column`` and ``canonical_column``.
            canonical_column: Existing column to populate. Set equal to ``input_column``
                to canonicalize in place.
            instruction: What makes two values refer to the same real-world entity, plus
                any style guidance for the canonical form. If collisions are likely
                (common surface names like ``"Bob Smith"`` or ``"Acme Corp"``), include
                a rule for how the canonical should extend on collision — e.g.
                *"append a parenthetical city, like 'Bob Smith (Chicago)'"*.
            input_column: The column being canonicalized.
            merge_duplicates: After populating, collapse rows sharing a canonical into
                one via per-column coalesce (most-frequent non-null). Safe because
                every cluster gets a globally unique canonical, so the groupby
                collapses one entity at a time. **In place** — originals are lost;
                copy first if needed. Only set when ``input_column`` identifies the
                row's own entity; never on a foreign attribute.
        """
        if self._db_connector is None:
            return "(error: no workspace database connected)"

        # Shared setup: distinct source values + ensure canonical_column exists.
        distinct_values, error = await self._fetch_distinct_values(schema_name, table_name, input_column)
        if error is not None:
            return error
        if not distinct_values:
            return f"(no values to canonicalize in {qualified_table(schema_name, table_name)}.{input_column})"
        error = await self._check_canonical_column(schema_name, table_name, input_column, canonical_column)
        if error is not None:
            return error

        # Per-call trajectory directory. Best-effort: log failures and disable.
        call_id = uuid.uuid4().hex[:12]
        traj_dir: Path | None = None
        if self.trajectory_log_dir is not None:
            traj_dir = self.trajectory_log_dir / call_id
            try:
                traj_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                logger.exception("Failed to create trajectory dir: %s", traj_dir)
                traj_dir = None

        mapping, n_errors, n_clusters, cluster_error = await self._cluster_and_canonicalize(
            distinct_values, instruction, schema_name, table_name, input_column, traj_dir
        )
        if cluster_error is not None:
            return cluster_error

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
                f"{qualified_table(schema_name, table_name)}: {update_error})"
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
        qualified_target = qualified_table(schema_name, table_name)
        summary = (
            f"Canonicalized {len(distinct_values)} distinct values in {qualified_target}.{input_column} "
            f"→ {canonical_column}; {n_clusters} entity clusters formed"
        )
        if merged_row_counts is not None:
            before, after = merged_row_counts
            summary += f"; merged {before} rows → {after} in place"
        if n_errors:
            summary += f"; {n_errors} subagent failures (treated as singletons)"
        if traj_dir is not None:
            summary += f"; trajectories at {traj_dir}"
        return summary + "."

    # ------------------------------------------------------------------
    # Shared infrastructure used by the per-mode methods below.
    # ------------------------------------------------------------------

    async def _fetch_distinct_values(
        self, schema_name: str | None, table_name: str, input_column: str
    ) -> tuple[list[str], str | None]:
        """Return distinct non-null values of ``input_column`` (and an optional error message)."""
        assert self._db_connector is not None
        sa_input_table = sa_table(schema_name, table_name, input_column)
        qualified = qualified_table(schema_name, table_name)
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
        qualified = qualified_table(schema_name, table_name)
        target_sa = sa_table(schema_name, table_name)
        cols_res = await self._db_connector.run_query_async(
            sqlalchemy.select(sqlalchemy.text("*")).select_from(target_sa).limit(0)
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
        stage: str,
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
        # Emit a 0/total tick up front so the UI flips to this stage immediately,
        # rather than sitting on the previous stage's last tick until the first
        # task finishes (often a multi-second LLM call).
        if self.on_progress is not None and total > 0:
            self.on_progress(stage, 0, total)

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
                        self.on_progress(stage, completed, total)
                        await asyncio.sleep(0)

        results = await asyncio.gather(*(_wrap(v) for v in distinct_values))
        return results, n_errors

    def _write_trajectory(self, traj_dir: Path | None, name: str, result: Any) -> None:
        """Persist one subagent's pydantic-ai trajectory as ``<traj_dir>/<name>.md``."""
        if traj_dir is None:
            return
        try:
            traj = Trajectory.from_pydantic_ai_messages(result.all_messages())
            (traj_dir / f"{name}.md").write_text(traj.to_markdown(), encoding="utf-8")
        except Exception:
            logger.exception("Failed to write trajectory %s/%s.md", traj_dir, name)

    async def _cluster_and_canonicalize(
        self,
        distinct_values: list[str],
        instruction: str,
        schema_name: str | None,
        table_name: str,
        input_column: str,
        traj_dir: Path | None,
    ) -> tuple[dict[str, str], int, int, str | None]:
        """Per-value resolve-peers judgment → cluster on SAME edges → picker per cluster.

        Returns ``(mapping, n_errors, n_clusters, error_message)``. On non-None
        ``error_message`` the caller must skip the SQL UPDATE — the mapping is empty.
        """
        assert self._db_connector is not None
        run_query_pa_tool = RunQueryTool(self._db_connector).as_pydantic_ai_tool()
        qualified_target = qualified_table(schema_name, table_name)
        value_to_idx = {v: i for i, v in enumerate(distinct_values)}

        async def task(value: str) -> _ResolvePeersOutput:
            prompt = _RESOLVE_PROMPT.render(
                instruction=instruction,
                table_name=qualified_target,
                input_column=input_column,
                value=value,
            )
            subagent = make_agent(self.subagent_llm, tools=[run_query_pa_tool], output_type=_ResolvePeersOutput, model_settings=self.model_settings)
            result = await subagent.run(prompt)
            self._write_trajectory(traj_dir, f"resolve-{value_to_idx[value]:04d}", result)
            return result.output

        results, n_errors = await self._run_per_value(
            "resolve",
            distinct_values,
            task,
            on_failure=lambda v: _ResolvePeersOutput(same_as=[]),
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
        n_clusters = len(clusters)
        picker_completed = 0
        if self.on_progress is not None and n_clusters > 0:
            self.on_progress("canonicalize", 0, n_clusters)

        async def _pick_with_progress(cluster: set[str], cluster_idx: int) -> str:
            nonlocal picker_completed
            try:
                return await self._pick_canonical(cluster, instruction, traj_dir, cluster_idx)
            finally:
                picker_completed += 1
                if self.on_progress is not None:
                    self.on_progress("canonicalize", picker_completed, n_clusters)
                    await asyncio.sleep(0)

        cluster_canonicals = await asyncio.gather(
            *(_pick_with_progress(cluster, i) for i, cluster in enumerate(clusters))
        )

        # Resolve cross-cluster collisions so each cluster gets a unique canonical.
        cluster_canonicals, resolve_error = await self._resolve_collisions(
            clusters,
            cluster_canonicals,
            instruction,
            qualified_target,
            input_column,
            run_query_pa_tool,
            traj_dir,
        )
        if resolve_error is not None:
            return {}, n_errors, len(clusters), resolve_error

        mapping: dict[str, str] = {}
        for cluster, canonical in zip(clusters, cluster_canonicals):
            for v in cluster:
                mapping[v] = canonical
        return mapping, n_errors, len(clusters), None

    async def _resolve_collisions(
        self,
        clusters: list[set[str]],
        cluster_canonicals: list[str],
        instruction: str,
        qualified_table_name: str,
        input_column: str,
        run_query_pa_tool: Tool,
        traj_dir: Path | None,
    ) -> tuple[list[str], str | None]:
        """Ensure each cluster gets a globally unique canonical name.

        Each colliding group is sent to ``_disambiguate_via_llm``, which configures
        the agent with ``retries=_MAX_DISAMBIGUATE_RETRIES`` and an output validator
        that raises :class:`ModelRetry` on length/duplicate/seen violations. Groups
        with more than ``_DISAMBIGUATE_BATCH_SIZE`` clusters are split into
        sequential batches (each batch's results join ``seen`` before the next runs).
        Groups are processed in size-descending order so each call sees the latest
        ``seen``.

        Returns ``(resolved_canonicals, error_message)``. On non-None
        ``error_message`` the caller MUST NOT apply the mapping.
        """
        # Phase 1: collect collision groups. Within a group, sort cluster indices by
        # cluster size desc so the LLM sees the strongest claimant first.
        groups: dict[str, list[int]] = {}
        for i, canonical in enumerate(cluster_canonicals):
            groups.setdefault(canonical, []).append(i)
        collisions: list[tuple[str, list[int]]] = []
        for canonical, idxs in groups.items():
            if len(idxs) <= 1:
                continue
            idxs.sort(key=lambda i: len(clusters[i]), reverse=True)
            collisions.append((canonical, idxs))
        # Process groups with the most total members first.
        collisions.sort(key=lambda c: -sum(len(clusters[i]) for i in c[1]))

        resolved = list(cluster_canonicals)
        seen: set[str] = {c for c, idxs in groups.items() if len(idxs) == 1}

        # Phase 2: sequentially disambiguate each collision group, batching when large.
        total_batches = sum(
            (len(idxs) + _DISAMBIGUATE_BATCH_SIZE - 1) // _DISAMBIGUATE_BATCH_SIZE for _, idxs in collisions
        )
        batches_done = 0
        if self.on_progress is not None and total_batches > 0:
            self.on_progress("disambiguate", 0, total_batches)
        for collision_idx, (canonical, idxs) in enumerate(collisions):
            n_batches = (len(idxs) + _DISAMBIGUATE_BATCH_SIZE - 1) // _DISAMBIGUATE_BATCH_SIZE
            for batch_idx in range(n_batches):
                start = batch_idx * _DISAMBIGUATE_BATCH_SIZE
                batch_idxs = idxs[start : start + _DISAMBIGUATE_BATCH_SIZE]
                member_groups = [sorted(clusters[i], key=len, reverse=True) for i in batch_idxs]
                new_names = await self._disambiguate_via_llm(
                    collided=canonical,
                    member_groups=member_groups,
                    instruction=instruction,
                    qualified_table_name=qualified_table_name,
                    input_column=input_column,
                    run_query_pa_tool=run_query_pa_tool,
                    seen=seen,
                    traj_dir=traj_dir,
                    collision_idx=collision_idx,
                    batch_idx=batch_idx if n_batches > 1 else None,
                )
                if new_names is None:
                    return resolved, (
                        f"(error: could not produce distinct canonical names for cluster group "
                        f"{canonical!r} (batch {batch_idx + 1}/{n_batches}) after "
                        f"{_MAX_DISAMBIGUATE_RETRIES} retries. Consider providing a more "
                        f"discriminating input_column or richer instruction context so the LLM "
                        f"can distinguish the {len(idxs)} colliding clusters.)"
                    )
                for cluster_idx, name in zip(batch_idxs, new_names):
                    resolved[cluster_idx] = name
                    seen.add(name)
                batches_done += 1
                if self.on_progress is not None:
                    self.on_progress("disambiguate", batches_done, total_batches)
                    await asyncio.sleep(0)

        return resolved, None

    async def _disambiguate_via_llm(
        self,
        *,
        collided: str,
        member_groups: list[list[str]],
        instruction: str,
        qualified_table_name: str,
        input_column: str,
        run_query_pa_tool: Tool,
        seen: set[str],
        traj_dir: Path | None,
        collision_idx: int,
        batch_idx: int | None = None,
    ) -> list[str] | None:
        """Produce a distinct canonical per colliding group, with native retry-on-validation.

        The agent is configured with ``retries=_MAX_DISAMBIGUATE_RETRIES`` and an
        ``output_validator`` that checks length, internal distinctness, and
        non-membership in ``seen``. Validation failures raise :class:`ModelRetry`,
        which pydantic-ai turns into a real conversational turn re-prompting the
        model — strictly more signal than a paraphrased "this is a retry" prefix.
        ``seen`` is also rendered into the initial prompt as a static hard constraint.

        Returns the validated names list, or ``None`` if retries were exhausted
        (:class:`UnexpectedModelBehavior`) or the LLM call hit an unrecoverable error.
        """
        expected_n = len(member_groups)
        prompt = _DISAMBIGUATE_PROMPT.render(
            collided=repr(collided),
            instruction=instruction,
            groups=member_groups,
            table_name=qualified_table_name,
            input_column=input_column,
            seen_list=_relevant_seen(collided, seen, _DISAMBIGUATE_SEEN_SHOWN),
        )
        subagent: Agent[None, _DisambiguationOutput] = make_agent(self.subagent_llm, tools=[run_query_pa_tool], output_type=_DisambiguationOutput, model_settings=self.model_settings, retries=_MAX_DISAMBIGUATE_RETRIES)

        @subagent.output_validator
        def _validate(output: _DisambiguationOutput) -> _DisambiguationOutput:
            names = output.names
            if len(names) != expected_n:
                raise ModelRetry(
                    f"You returned {len(names)} names but exactly {expected_n} were required "
                    f"(one per group, in the same order). Try again."
                )
            counts: dict[str, int] = {}
            for n in names:
                counts[n] = counts.get(n, 0) + 1
            duplicates = sorted({n for n, c in counts.items() if c > 1})
            taken = sorted({n for n in names if n in seen})
            if duplicates or taken:
                problems: list[str] = []
                if duplicates:
                    problems.append(
                        f"You returned these names more than once in your response — each must be unique: {duplicates}."
                    )
                if taken:
                    problems.append(
                        f"You returned these names that are already claimed by other clusters and may not be reused: {taken}."
                    )
                raise ModelRetry(" ".join(problems))
            return output

        try:
            result = await subagent.run(prompt)
        except UnexpectedModelBehavior:
            logger.exception(
                "disambiguation exhausted %d retries for collided canonical %r",
                _MAX_DISAMBIGUATE_RETRIES,
                collided,
            )
            return None
        except Exception:
            logger.exception("disambiguation failed for collided canonical %r", collided)
            return None
        traj_name = (
            f"disambiguate-{collision_idx:04d}"
            if batch_idx is None
            else f"disambiguate-{collision_idx:04d}-batch-{batch_idx:02d}"
        )
        self._write_trajectory(traj_dir, traj_name, result)
        return result.output.names

    async def _pick_canonical(
        self,
        cluster: set[str],
        instruction: str,
        traj_dir: Path | None = None,
        cluster_idx: int = 0,
    ) -> str:
        """One LLM call per SAME-cluster to pick or generate the canonical name."""
        # Sort by length desc so a cap-truncation keeps the richest surface forms,
        # and the fallback (``members[0]``) is the longest member.
        members = sorted(cluster, key=len, reverse=True)
        if len(members) > _PICKER_MAX_MEMBERS:
            logger.info("Picker cluster has %d members; sampling %d longest", len(members), _PICKER_MAX_MEMBERS)
        prompt = _CANONICALIZE_PROMPT.render(instruction=instruction, values=members[:_PICKER_MAX_MEMBERS])
        subagent = make_agent(self.subagent_llm, output_type=_CanonicalOutput, model_settings=self.model_settings)
        try:
            result = await subagent.run(prompt)
            self._write_trajectory(traj_dir, f"picker-{cluster_idx:04d}", result)
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

            target = sa_table(schema_name, table_name, input_column, canonical_column)
            map_t = sa_table(None, mapping_table_name, "input_val", "canonical_val")
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
                    qualified_table(schema_name, table_name),
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
        qualified = qualified_table(schema_name, table_name)

        # Read the whole table.
        target_sa = sa_table(schema_name, table_name)
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
