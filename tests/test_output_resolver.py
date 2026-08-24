from collections.abc import Mapping

from jinja2.exceptions import SecurityError
import pandas as pd
import pytest

from tabulaflow.output.specs import (
    ChoiceOption,
    ChoiceParameter,
    ChartArtifactSpec,
    FixedResultSource,
    GraphArtifactSpec,
    MapArtifactSpec,
    NumberParameter,
    OutputSpec,
    ParameterizedSource,
    TableArtifactSpec,
)
from tabulaflow.core import ExecResult
from tabulaflow.output.resolver import (
    OutputResolutionError,
    OutputResolver,
    ResolvedGraphArtifact,
    ResolvedMapArtifact,
    ResolvedTableArtifact,
    UnavailableArtifact,
)
from tabulaflow.output.store import (
    OutputStore,
    ResultPayload,
    SourceNotApplicable,
    SourceResolutionError,
    render_parameterized_query,
)


async def _output_store_with_results() -> OutputStore:
    output_store = OutputStore()
    await output_store.add_fixed_result_source(
        "workspace",
        "sql",
        "SELECT 1 AS a",
        ExecResult(df=pd.DataFrame({"a": [1]})),
    )
    await output_store.add_fixed_result_source(
        "workspace",
        "sql",
        "SELECT 2 AS a",
        ExecResult(df=pd.DataFrame({"a": [2]})),
    )
    return output_store


def _parameters() -> list[ChoiceParameter | NumberParameter]:
    return [
        ChoiceParameter(
            id="metric",
            label="Metric",
            choices=[ChoiceOption(id="revenue", label="Revenue"), ChoiceOption(id="profit", label="Profit")],
        ),
        NumberParameter(id="min_spend", label="Minimum spend", min=0, max=100_000, step=5_000, default=10_000),
    ]


@pytest.mark.asyncio
async def test_fixed_source_resolves_output_artifact() -> None:
    output_store = await _output_store_with_results()
    resolver = OutputResolver(output_store)
    output = OutputSpec(
        sources=[FixedResultSource(id="fixed", result_id="R1")],
        artifacts=[TableArtifactSpec(id="table", source_id="fixed")],
    )

    resolved = await resolver.resolve(output)

    artifact = resolved.artifacts[0]
    assert isinstance(artifact, ResolvedTableArtifact)
    metadata = artifact.payload.metadata
    assert resolved.selection == {}
    assert metadata.id == "R1"
    assert metadata.db_alias == "workspace"
    assert metadata.query == "SELECT 1 AS a"
    assert metadata.row_count == 1
    assert metadata.columns == ["a"]


@pytest.mark.asyncio
async def test_parameterized_source_resolves_by_projected_selection() -> None:
    output_store = OutputStore()
    source = output_store.add_parameterized_source(
        "workspace",
        [
            ChoiceParameter(
                id="metric",
                label="Metric",
                choices=[ChoiceOption(id="revenue", label="Revenue"), ChoiceOption(id="profit", label="Profit")],
            )
        ],
        "SELECT {{ metric }}",
    )
    await output_store.cache_parameterized_result(
        source.id,
        "sql",
        {"metric": "revenue"},
        "SELECT 1 AS a",
        ExecResult(df=pd.DataFrame({"a": [1]})),
    )
    await output_store.cache_parameterized_result(
        source.id,
        "sql",
        {"metric": "profit"},
        "SELECT 2 AS a",
        ExecResult(df=pd.DataFrame({"a": [2]})),
    )
    resolver = OutputResolver(output_store)
    output = OutputSpec(
        parameters=_parameters(),
        sources=[source],
        artifacts=[TableArtifactSpec(id="table", source_id=source.id)],
    )

    resolved = await resolver.resolve(output, {"metric": "profit"})

    artifact = resolved.artifacts[0]
    assert isinstance(artifact, ResolvedTableArtifact)
    metadata = artifact.payload.metadata
    assert resolved.selection == {"metric": "profit", "min_spend": 10_000}
    assert metadata.id == "R2"
    assert isinstance(output.sources[0], ParameterizedSource)


@pytest.mark.asyncio
async def test_parameterized_source_rejects_invalid_choice() -> None:
    output_store = await _output_store_with_results()
    resolver = OutputResolver(output_store)
    source = output_store.add_parameterized_source(
        "workspace",
        [
            ChoiceParameter(
                id="metric",
                label="Metric",
                choices=[ChoiceOption(id="revenue", label="Revenue"), ChoiceOption(id="profit", label="Profit")],
            )
        ],
        "SELECT 1",
    )
    output = OutputSpec(
        parameters=_parameters(),
        sources=[source],
        artifacts=[TableArtifactSpec(id="table", source_id=source.id)],
    )

    with pytest.raises(OutputResolutionError, match="not a valid choice"):
        await resolver.resolve(output, {"metric": "count"})


@pytest.mark.asyncio
async def test_parameterized_source_reports_unavailable_selection() -> None:
    output_store = await _output_store_with_results()
    resolver = OutputResolver(output_store)
    source = output_store.add_parameterized_source(
        "workspace",
        [
            ChoiceParameter(
                id="metric",
                label="Metric",
                choices=[ChoiceOption(id="revenue", label="Revenue"), ChoiceOption(id="profit", label="Profit")],
            )
        ],
        "SELECT 1",
    )
    output = OutputSpec(
        parameters=_parameters(),
        sources=[source],
        artifacts=[TableArtifactSpec(id="table", source_id=source.id)],
    )

    resolved = await resolver.resolve(output, {"metric": "profit"})

    artifact = resolved.artifacts[0]
    assert isinstance(artifact, UnavailableArtifact)
    assert "has no result" in artifact.reason


@pytest.mark.asyncio
async def test_parameterized_source_without_cache_errors_until_materialization_exists() -> None:
    output_store = await _output_store_with_results()
    resolver = OutputResolver(output_store)
    source = output_store.add_parameterized_source(
        "workspace",
        [NumberParameter(id="min_spend", label="Minimum spend", min=0, max=100_000, step=5_000, default=10_000)],
        "SELECT 1",
    )
    output = OutputSpec(
        parameters=_parameters(),
        sources=[source],
        artifacts=[TableArtifactSpec(id="table", source_id=source.id)],
    )

    resolved = await resolver.resolve(output, {"min_spend": 10_000})

    artifact = resolved.artifacts[0]
    assert isinstance(artifact, UnavailableArtifact)
    assert "has no result" in artifact.reason


@pytest.mark.asyncio
async def test_unavailable_artifact_does_not_hide_siblings() -> None:
    output_store = await _output_store_with_results()
    missing = output_store.add_parameterized_source(
        "workspace",
        [
            ChoiceParameter(
                id="metric",
                label="Metric",
                choices=[ChoiceOption(id="revenue", label="Revenue"), ChoiceOption(id="profit", label="Profit")],
            )
        ],
        "SELECT 1",
    )
    output = OutputSpec(
        parameters=_parameters(),
        sources=[FixedResultSource(id="fixed", result_id="R1"), missing],
        artifacts=[
            TableArtifactSpec(id="fixed", source_id="fixed"),
            TableArtifactSpec(id="missing", source_id=missing.id),
        ],
    )

    resolved = await OutputResolver(output_store).resolve(output, {"metric": "profit"})

    first, second = resolved.artifacts
    assert isinstance(first, ResolvedTableArtifact)
    assert first.payload.metadata.id == "R1"
    assert isinstance(second, UnavailableArtifact)
    assert "has no result" in second.reason


def test_parameterized_query_can_declare_not_applicable() -> None:
    with pytest.raises(SourceNotApplicable, match="only applies to revenue"):
        render_parameterized_query(
            "{% if metric != 'revenue' %}{{ not_applicable('only applies to revenue') }}{% endif %} SELECT 1",
            {"metric": "orders"},
        )


def test_parameterized_query_blocks_unsafe_attribute_access() -> None:
    with pytest.raises(SecurityError, match="unsafe"):
        render_parameterized_query("{{ cycler.__init__.__globals__ }}", {})


@pytest.mark.asyncio
async def test_parameterized_source_not_applicable_is_not_an_error() -> None:
    output_store = OutputStore()
    source = output_store.add_parameterized_source(
        "workspace",
        [
            ChoiceParameter(
                id="metric",
                label="Metric",
                choices=[ChoiceOption(id="revenue", label="Revenue"), ChoiceOption(id="orders", label="Orders")],
            )
        ],
        "{% if metric != 'revenue' %}{{ not_applicable('only applies to revenue') }}{% endif %} SELECT 1 AS value",
    )
    await output_store.cache_parameterized_result(
        source.id,
        "sql",
        {"metric": "revenue"},
        "SELECT 1 AS value",
        ExecResult(df=pd.DataFrame({"value": [1]})),
    )
    output = OutputSpec(
        parameters=output_store.source_parameters(source.id),
        sources=[source],
        artifacts=[TableArtifactSpec(id="table", source_id=source.id)],
    )

    resolved = await OutputResolver(output_store).resolve(output, {"metric": "orders"})

    artifact = resolved.artifacts[0]
    assert isinstance(artifact, UnavailableArtifact)
    assert artifact.status == "not_applicable"
    assert artifact.reason == "only applies to revenue"


@pytest.mark.asyncio
async def test_table_artifact_without_displayable_payload_is_unavailable() -> None:
    output_store = OutputStore()
    await output_store.add_fixed_result_source(
        "workspace",
        "sql",
        "CREATE TABLE t(a INT)",
        ExecResult(),
    )
    output = OutputSpec(
        sources=[FixedResultSource(id="fixed", result_id="R1")],
        artifacts=[TableArtifactSpec(id="table", source_id="fixed")],
    )

    resolved = await OutputResolver(output_store).resolve(output)

    artifact = resolved.artifacts[0]
    assert isinstance(artifact, UnavailableArtifact)
    assert artifact.status == "no_data"
    assert artifact.reason == "Statement executed successfully but returned no displayable data"


@pytest.mark.asyncio
async def test_table_artifact_without_displayable_payload_reports_affected_rows() -> None:
    output_store = OutputStore()
    await output_store.add_fixed_result_source(
        "workspace",
        "sql",
        "UPDATE t SET a = 1",
        ExecResult(affected_rows=3),
    )
    output = OutputSpec(
        sources=[FixedResultSource(id="fixed", result_id="R1")],
        artifacts=[TableArtifactSpec(id="table", source_id="fixed")],
    )

    resolved = await OutputResolver(output_store).resolve(output)

    artifact = resolved.artifacts[0]
    assert isinstance(artifact, UnavailableArtifact)
    assert artifact.status == "no_data"
    assert artifact.reason == "Statement executed successfully, affected 3 rows, and returned no displayable data"


@pytest.mark.asyncio
async def test_chart_artifact_without_dataframe_is_unavailable() -> None:
    output_store = OutputStore()
    await output_store.add_fixed_result_source(
        "workspace",
        "sql",
        "CREATE TABLE t(a INT)",
        ExecResult(),
    )
    output = OutputSpec(
        sources=[FixedResultSource(id="fixed", result_id="R1")],
        artifacts=[ChartArtifactSpec(id="chart", source_id="fixed", spec={"mark": "bar"})],
    )

    resolved = await OutputResolver(output_store).resolve(output)

    artifact = resolved.artifacts[0]
    assert isinstance(artifact, UnavailableArtifact)
    assert artifact.status == "no_data"
    assert artifact.reason == "Source returned no tabular data"


@pytest.mark.asyncio
async def test_invalid_artifact_specs_do_not_abort_other_artifacts() -> None:
    output_store = OutputStore()
    await output_store.add_fixed_result_source(
        "workspace",
        "sql",
        "SELECT 1 AS value",
        ExecResult(df=pd.DataFrame({"value": [1]})),
    )
    source = FixedResultSource(id="fixed", result_id="R1")
    output = OutputSpec(
        sources=[source],
        artifacts=[
            ChartArtifactSpec(
                id="chart",
                source_id=source.id,
                spec={"mark": "bar", "encoding": {"x": {"field": "missing"}}},
            ),
            MapArtifactSpec(
                id="map",
                source_ids=[source.id],
                spec={"layers": [{"type": "points", "source_id": source.id, "lat": "missing", "lng": "value"}]},
            ),
            GraphArtifactSpec(
                id="graph",
                source_ids=[source.id],
                spec={
                    "nodes": [{"source_id": source.id, "id": "missing"}],
                    "edges": [{"source_id": source.id, "source": "missing", "target": "value"}],
                },
            ),
            TableArtifactSpec(id="table", source_id=source.id),
        ],
    )

    resolved = await OutputResolver(output_store).resolve(output)

    assert [type(artifact) for artifact in resolved.artifacts] == [
        UnavailableArtifact,
        UnavailableArtifact,
        UnavailableArtifact,
        ResolvedTableArtifact,
    ]


@pytest.mark.asyncio
async def test_map_and_graph_specs_resolve_against_source_data() -> None:
    output_store = OutputStore()
    await output_store.add_fixed_result_source(
        "workspace",
        "sql",
        "SELECT * FROM places",
        ExecResult(df=pd.DataFrame({"id": ["a"], "lat": [1.0], "lng": [2.0], "target": ["a"]})),
    )
    source = FixedResultSource(id="fixed", result_id="R1")
    output = OutputSpec(
        sources=[source],
        artifacts=[
            MapArtifactSpec(
                id="map",
                source_ids=[source.id],
                spec={"layers": [{"type": "points", "source_id": source.id, "lat": "lat", "lng": "lng"}]},
            ),
            GraphArtifactSpec(
                id="graph",
                source_ids=[source.id],
                spec={
                    "nodes": [{"source_id": source.id, "id": "id"}],
                    "edges": [{"source_id": source.id, "source": "id", "target": "target"}],
                },
            ),
        ],
    )

    resolved = await OutputResolver(output_store).resolve(output)

    map_artifact, graph_artifact = resolved.artifacts
    assert isinstance(map_artifact, ResolvedMapArtifact)
    assert map_artifact.spec == {"layers": [{"type": "points", "source_id": source.id, "lat": "lat", "lng": "lng"}]}
    assert isinstance(graph_artifact, ResolvedGraphArtifact)
    assert [node.id for node in graph_artifact.graph.nodes] == ["a"]


@pytest.mark.asyncio
async def test_map_and_graph_resolve_parameterized_selection() -> None:
    output_store = OutputStore()
    parameter = ChoiceParameter(
        id="period",
        label="Period",
        choices=[ChoiceOption(id="q1", label="Q1"), ChoiceOption(id="q2", label="Q2")],
    )
    source = output_store.add_parameterized_source("workspace", [parameter], "SELECT 1")
    for period, node_id, lat in (("q1", "a", 1.0), ("q2", "b", 2.0)):
        await output_store.cache_parameterized_result(
            source.id,
            "sql",
            {"period": period},
            "SELECT 1",
            ExecResult(df=pd.DataFrame({"id": [node_id], "lat": [lat], "lng": [3.0]})),
        )
    output = OutputSpec(
        parameters=[parameter],
        sources=[source],
        artifacts=[
            MapArtifactSpec(
                id="map",
                source_ids=[source.id],
                spec={"layers": [{"type": "points", "source_id": source.id, "lat": "lat", "lng": "lng"}]},
            ),
            GraphArtifactSpec(
                id="graph",
                source_ids=[source.id],
                spec={"nodes": [{"source_id": source.id, "id": "id"}]},
            ),
        ],
    )

    resolved = await OutputResolver(output_store).resolve(output, {"period": "q2"})

    map_artifact, graph_artifact = resolved.artifacts
    assert isinstance(map_artifact, ResolvedMapArtifact)
    assert map_artifact.payload_by_source[source.id].metadata.source_selection == {"period": "q2"}
    assert isinstance(graph_artifact, ResolvedGraphArtifact)
    assert [node.id for node in graph_artifact.graph.nodes] == ["b"]


@pytest.mark.asyncio
async def test_artifact_wrapper_and_nested_source_ids_must_match() -> None:
    output_store = OutputStore()
    await output_store.add_fixed_result_source(
        "workspace",
        "sql",
        "SELECT 1 AS value",
        ExecResult(df=pd.DataFrame({"value": [1], "lat": [1], "lng": [2]})),
    )
    await output_store.add_fixed_result_source(
        "workspace",
        "sql",
        "SELECT 2 AS value",
        ExecResult(df=pd.DataFrame({"value": [2], "lat": [3], "lng": [4]})),
    )
    output = OutputSpec(
        sources=[FixedResultSource(id="first", result_id="R1"), FixedResultSource(id="second", result_id="R2")],
        artifacts=[
            MapArtifactSpec(
                id="map",
                source_ids=["first"],
                spec={"layers": [{"type": "points", "source_id": "second", "lat": "lat", "lng": "lng"}]},
            )
        ],
    )

    with pytest.raises(OutputResolutionError, match="do not match"):
        await OutputResolver(output_store).resolve(output)


@pytest.mark.asyncio
async def test_source_failure_is_reused_across_artifacts() -> None:
    class FailingOutputStore(OutputStore):
        def __init__(self) -> None:
            super().__init__()
            self.resolve_count = 0

        async def resolve_source(self, source_id: str, selection: Mapping[str, object] | None = None) -> ResultPayload:
            self.resolve_count += 1
            raise SourceResolutionError("query failed")

    output_store = FailingOutputStore()
    source = output_store.add_parameterized_source("workspace", [], "SELECT 1")
    output = OutputSpec(
        sources=[source],
        artifacts=[
            TableArtifactSpec(id="first", source_id=source.id),
            TableArtifactSpec(id="second", source_id=source.id),
        ],
    )

    resolved = await OutputResolver(output_store).resolve(output)

    assert output_store.resolve_count == 1
    assert all(isinstance(artifact, UnavailableArtifact) for artifact in resolved.artifacts)


@pytest.mark.asyncio
async def test_unexpected_source_value_error_is_not_hidden() -> None:
    class BrokenOutputStore(OutputStore):
        async def resolve_source(self, source_id: str, selection: Mapping[str, object] | None = None) -> ResultPayload:
            raise ValueError("programming bug")

    output_store = BrokenOutputStore()
    source = output_store.add_parameterized_source("workspace", [], "SELECT 1")
    output = OutputSpec(sources=[source], artifacts=[TableArtifactSpec(id="table", source_id=source.id)])

    with pytest.raises(ValueError, match="programming bug"):
        await OutputResolver(output_store).resolve(output)
