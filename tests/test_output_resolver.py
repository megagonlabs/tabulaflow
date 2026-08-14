import pandas as pd
import pytest

from tabulaflow.core import (
    ChoiceOption,
    ChoiceParameter,
    ChartArtifactSpec,
    FixedResultSource,
    NumberParameter,
    OutputSpec,
    ParameterizedSource,
    TableArtifactSpec,
)
from tabulaflow.core.types import ExecResult, PredQuery
from tabulaflow.toolhub import OutputResolutionError, OutputResolver, OutputStore, ResolvedTableArtifact, SourceNotApplicable, UnavailableArtifact
from tabulaflow.toolhub.output_store import render_parameterized_query


async def _output_store_with_results() -> OutputStore:
    output_store = OutputStore()
    await output_store.add_fixed_result_source(
        "workspace",
        "sql",
        PredQuery(query="SELECT 1 AS a", exec_result=ExecResult(df=pd.DataFrame({"a": [1]}))),
    )
    await output_store.add_fixed_result_source(
        "workspace",
        "sql",
        PredQuery(query="SELECT 2 AS a", exec_result=ExecResult(df=pd.DataFrame({"a": [2]}))),
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
        PredQuery(query="SELECT 1 AS a", exec_result=ExecResult(df=pd.DataFrame({"a": [1]}))),
    )
    await output_store.cache_parameterized_result(
        source.id,
        "sql",
        {"metric": "profit"},
        PredQuery(query="SELECT 2 AS a", exec_result=ExecResult(df=pd.DataFrame({"a": [2]}))),
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


@pytest.mark.asyncio
async def test_parameterized_source_not_applicable_is_not_an_error() -> None:
    output_store = OutputStore()
    source = output_store.add_parameterized_source(
        "workspace",
        [ChoiceParameter(id="metric", label="Metric", choices=[ChoiceOption(id="revenue", label="Revenue"), ChoiceOption(id="orders", label="Orders")])],
        "{% if metric != 'revenue' %}{{ not_applicable('only applies to revenue') }}{% endif %} SELECT 1 AS value",
    )
    await output_store.cache_parameterized_result(
        source.id,
        "sql",
        {"metric": "revenue"},
        PredQuery(query="SELECT 1 AS value", exec_result=ExecResult(df=pd.DataFrame({"value": [1]}))),
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
        PredQuery(query="CREATE TABLE t(a INT)", exec_result=ExecResult()),
    )
    output = OutputSpec(
        sources=[FixedResultSource(id="fixed", result_id="R1")],
        artifacts=[TableArtifactSpec(id="table", source_id="fixed")],
    )

    resolved = await OutputResolver(output_store).resolve(output)

    artifact = resolved.artifacts[0]
    assert isinstance(artifact, UnavailableArtifact)
    assert artifact.status == "error"
    assert artifact.reason == "Source returned no displayable data"


@pytest.mark.asyncio
async def test_chart_artifact_without_dataframe_is_unavailable() -> None:
    output_store = OutputStore()
    await output_store.add_fixed_result_source(
        "workspace",
        "sql",
        PredQuery(query="CREATE TABLE t(a INT)", exec_result=ExecResult()),
    )
    output = OutputSpec(
        sources=[FixedResultSource(id="fixed", result_id="R1")],
        artifacts=[ChartArtifactSpec(id="chart", source_id="fixed", spec={"mark": "bar"})],
    )

    resolved = await OutputResolver(output_store).resolve(output)

    artifact = resolved.artifacts[0]
    assert isinstance(artifact, UnavailableArtifact)
    assert artifact.status == "error"
    assert artifact.reason == "Source returned no tabular data"
