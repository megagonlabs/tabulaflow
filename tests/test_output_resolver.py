import pandas as pd
import pytest

from tabulaflow.core import (
    ArtifactSpec,
    ChoiceOption,
    ChoiceParameter,
    FixedResultSource,
    NumberParameter,
    OutputSpec,
    ParameterizedSource,
    TableView,
)
from tabulaflow.core.types import ExecResult, PredQuery
from tabulaflow.toolhub import OutputResolutionError, OutputResolver, OutputStore


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
        artifacts=[ArtifactSpec(id="table", view=TableView(source="fixed"))],
    )

    resolved = await resolver.resolve(output)

    metadata = resolved.artifacts[0].metadata_by_source["fixed"]
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
        artifacts=[ArtifactSpec(id="table", view=TableView(source=source.id))],
    )

    resolved = await resolver.resolve(output, {"metric": "profit"})

    metadata = resolved.artifacts[0].metadata_by_source[source.id]
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
        artifacts=[ArtifactSpec(id="table", view=TableView(source=source.id))],
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
        artifacts=[ArtifactSpec(id="table", view=TableView(source=source.id))],
    )

    with pytest.raises(OutputResolutionError, match="has no result"):
        await resolver.resolve(output, {"metric": "profit"})


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
        artifacts=[ArtifactSpec(id="table", view=TableView(source=source.id))],
    )

    with pytest.raises(OutputResolutionError, match="has no result"):
        await resolver.resolve(output, {"min_spend": 10_000})
