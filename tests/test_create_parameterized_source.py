from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from pydantic_ai import ToolReturn

from tabulaflow.core.db_connector.db_registry import DBRegistry
from tabulaflow.core.db_connector.sql_conn import SQLConnector
from tabulaflow.core.outputs import ChoiceOption, ChoiceParameter, NumberParameter, OutputSpec, TableView, ArtifactSpec
from tabulaflow.toolhub import CreateParameterizedSourceTool, OutputResolver, OutputStore


def _text(result: ToolReturn) -> str:
    value = result.return_value
    assert isinstance(value, str)
    return value


@pytest.fixture
async def registry(tmp_path: Path) -> DBRegistry:
    connector = await SQLConnector.from_url_async(
        global_id="test-create-parameterized-source",
        url=f"duckdb:///{tmp_path / 'w.duckdb'}",
        db_name="w",
        read_only=False,
        enable_schema_caching=False,
        enable_query_caching=False,
    )
    await connector.run_query_async("CREATE TABLE orders(customer TEXT, net INT, gross INT)")
    await connector.run_query_async("INSERT INTO orders VALUES ('Acme', 10, 12), ('Globex', 7, 9)")
    r = DBRegistry()
    r.register("workspace", connector)
    return r


@pytest.mark.asyncio
async def test_create_parameterized_source_registers_parameters_and_warms_choice_grid(registry: DBRegistry) -> None:
    output_store = OutputStore(registry=registry)
    result = await CreateParameterizedSourceTool(registry, output_store)(
        "workspace",
        [
            ChoiceParameter(
                id="metric",
                label="Metric",
                choices=[ChoiceOption(id="net", label="Net"), ChoiceOption(id="gross", label="Gross")],
            )
        ],
        "SELECT SUM({% if metric == 'net' %}net{% else %}gross{% endif %}) AS value FROM orders",
    )

    assert _text(result) == dedent("""\
        [source_id=S1]
        created parameterized source S1
        default metric=net -> R1:
        |   value |
        |---------|
        |      17 |
        (1 row)
        warmed metric=gross -> R2""")
    source = output_store.get_source("S1")
    assert output_store.parameters_for_source(source)[0].id == "metric"
    assert len(output_store.get_cached_source_results("S1")) == 2

    resolved = await OutputResolver(output_store).resolve(
        OutputSpec(parameters=output_store.parameters_for_source(source), sources=[source], artifacts=[ArtifactSpec(id="S1", view=TableView(source="S1"))]),
        {"metric": "gross"},
    )
    result_id = resolved.artifacts[0].metadata_by_source["S1"].id
    payload = await output_store.get_payload(result_id)
    assert payload.df is not None
    assert payload.df.to_dict("records") == [{"value": 21}]


@pytest.mark.asyncio
async def test_create_parameterized_source_reports_empty_parameters(registry: DBRegistry) -> None:
    output_store = OutputStore(registry=registry)

    result = await CreateParameterizedSourceTool(registry, output_store)("workspace", [], "SELECT 1")

    assert _text(result) == "(error: parameters must not be empty)"


@pytest.mark.asyncio
async def test_create_parameterized_source_batches_warm_errors_and_registers_nothing(registry: DBRegistry) -> None:
    output_store = OutputStore(registry=registry)

    result = await CreateParameterizedSourceTool(registry, output_store)(
        "workspace",
        [
            ChoiceParameter(
                id="metric",
                label="Metric",
                choices=[ChoiceOption(id="bad_a", label="Bad A"), ChoiceOption(id="bad_b", label="Bad B")],
            )
        ],
        "SELECT {% if metric == 'bad_a' %}missing_a{% else %}missing_b{% endif %} FROM orders",
    )

    text = _text(result)
    assert "2 of 2 warm queries failed; source was not created" in text
    assert "metric=bad_a" in text
    assert "metric=bad_b" in text
    with pytest.raises(KeyError):
        output_store.get_source("S1")


@pytest.mark.asyncio
async def test_number_parameter_materializes_lazy_selection(registry: DBRegistry) -> None:
    output_store = OutputStore(registry=registry)
    result = await CreateParameterizedSourceTool(registry, output_store)(
        "workspace",
        [NumberParameter(id="min_net", label="Minimum net", min=0, max=20, step=1, default=8)],
        "SELECT customer FROM orders WHERE net >= {{ min_net }} ORDER BY customer",
    )
    assert "other selections will materialize lazily" in _text(result)
    source = output_store.get_source("S1")

    resolved = await OutputResolver(output_store).resolve(
        OutputSpec(parameters=output_store.parameters_for_source(source), sources=[source], artifacts=[ArtifactSpec(id="S1", view=TableView(source="S1"))]),
        {"min_net": 6},
    )

    result_id = resolved.artifacts[0].metadata_by_source["S1"].id
    payload = await output_store.get_payload(result_id)
    assert payload.df is not None
    assert payload.df.to_dict("records") == [{"customer": "Acme"}, {"customer": "Globex"}]
