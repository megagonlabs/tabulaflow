from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from pydantic_ai import ToolReturn

from tabulaflow.data.registry import DBRegistry
from tabulaflow.data.sql import SQLConnector
from tabulaflow.output.specs import ChoiceOption, ChoiceParameter, NumberParameter, OutputSpec, TableArtifactSpec
from tabulaflow.agents.tools import (
    CreateParameterizedSourceTool,
    OutputResolver,
    OutputStore,
    ResolvedTableArtifact,
    UnavailableArtifact,
)


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
        default metric=net:
        |   value |
        |---------|
        |      17 |
        (1 row)

        other warmed selections:
          metric=gross (1 row) — first row: value=21""")
    source = output_store.get_source("S1")
    assert output_store.source_parameters(source.id)[0].id == "metric"
    assert len(output_store.cached_parameterized_results("S1")) == 2

    resolved = await OutputResolver(output_store).resolve(
        OutputSpec(
            parameters=output_store.source_parameters(source.id),
            sources=[source],
            artifacts=[TableArtifactSpec(id="S1", source_id="S1")],
        ),
        {"metric": "gross"},
    )
    artifact = resolved.artifacts[0]
    assert isinstance(artifact, ResolvedTableArtifact)
    result_id = artifact.payload.metadata.id
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
    assert text.startswith("(error: 2 of 2 warm queries failed; source was not created\n  metric=bad_a — ")
    assert 'Referenced column "missing_a" not found' in text
    assert "\n  metric=bad_b — " in text
    assert 'Referenced column "missing_b" not found' in text
    assert text.endswith(")")
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
        OutputSpec(
            parameters=output_store.source_parameters(source.id),
            sources=[source],
            artifacts=[TableArtifactSpec(id="S1", source_id="S1")],
        ),
        {"min_net": 6},
    )

    artifact = resolved.artifacts[0]
    assert isinstance(artifact, ResolvedTableArtifact)
    result_id = artifact.payload.metadata.id
    payload = await output_store.get_payload(result_id)
    assert payload.df is not None
    assert payload.df.to_dict("records") == [{"customer": "Acme"}, {"customer": "Globex"}]


@pytest.mark.asyncio
async def test_mixed_choice_and_number_warms_choice_grid_at_number_default(registry: DBRegistry) -> None:
    output_store = OutputStore(registry=registry)
    result = await CreateParameterizedSourceTool(registry, output_store)(
        "workspace",
        [
            ChoiceParameter(
                id="metric",
                label="Metric",
                choices=[ChoiceOption(id="net", label="Net"), ChoiceOption(id="gross", label="Gross")],
            ),
            NumberParameter(id="min_value", label="Minimum value", min=0, max=20, step=1, default=8),
        ],
        """
        SELECT SUM({% if metric == 'net' %}net{% else %}gross{% endif %}) AS value
        FROM orders
        WHERE {% if metric == 'net' %}net{% else %}gross{% endif %} >= {{ min_value }}
        """,
    )

    text = _text(result)
    assert "default metric=net;min_value=8:" in text
    assert "metric=gross;min_value=8 (1 row) — first row: value=21" in text
    assert "-> R" not in text
    assert "other selections will materialize lazily" not in text
    assert len(output_store.cached_parameterized_results("S1")) == 2


@pytest.mark.asyncio
async def test_create_parameterized_source_warms_not_applicable_selection(registry: DBRegistry) -> None:
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
        """
        {% if metric == 'gross' %}{{ not_applicable('gross is not available for this source') }}{% endif %}
        SELECT SUM(net) AS value FROM orders
        """,
    )

    text = _text(result)
    assert "default metric=net:" in text
    assert "1 warmed selection not applicable" in text
    source = output_store.get_source("S1")

    resolved = await OutputResolver(output_store).resolve(
        OutputSpec(
            parameters=output_store.source_parameters(source.id),
            sources=[source],
            artifacts=[TableArtifactSpec(id="S1", source_id="S1")],
        ),
        {"metric": "gross"},
    )

    artifact = resolved.artifacts[0]
    assert isinstance(artifact, UnavailableArtifact)
    assert artifact.status == "not_applicable"
    assert artifact.reason == "gross is not available for this source"
