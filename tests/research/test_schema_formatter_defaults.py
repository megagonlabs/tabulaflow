"""Research formatter defaults, overrides, and validation without model calls."""

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, ClassVar, cast
from unittest.mock import AsyncMock, Mock

import pytest
from pydantic_ai import models

from tabulaflow.core import PropertyGraphSchema, RDFSchema, SQLSchema
from tabulaflow.data import DataConnector
from tabulaflow.output.formatting import CypherSchemaFormatter, SQLCompactSchemaFormatter, schema_formatter_registry
from tabulaflow.research.agents import (
    AmbigFlatSQLAgent,
    AmbigSimpleSQLAgent,
    AmbigStructuredSQLAgent,
    BasicAgentConfig,
    DbtAgent,
    DirectPromptAgent,
    FullSchemaAgent,
    SchemaDiscoveryAgent,
    SchemaLinkingAgent,
)
from tabulaflow.research.agents.ensemblers.agent import AgentEnsembler, AgentEnsemblerConfig
from tabulaflow.research.agents.registry import agent_registry
from tabulaflow.research.agents.utils import format_schema_for_prompt
from tabulaflow.research.benchmarks.registry import dataset_registry
from tabulaflow.research.pipelines import predict
from tabulaflow.research.pipelines.utils import validate_run_schema_formatters
from tabulaflow.research.types import GoldQuery, NL2QDataset, NL2QRunResult, SimpleNL2QTask, SimpleNL2QTaskOutput


@pytest.fixture(autouse=True)
def offline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(models, "ALLOW_MODEL_REQUESTS", False)
    monkeypatch.setattr("tabulaflow.agents.trace.compute_api_cost", lambda *args, **kwargs: 0)


@pytest.mark.parametrize(
    "agent_cls",
    [
        AmbigSimpleSQLAgent,
        AmbigFlatSQLAgent,
        AmbigStructuredSQLAgent,
        DbtAgent,
        SchemaDiscoveryAgent,
        SchemaLinkingAgent,
    ],
)
@pytest.mark.parametrize("formatter_name", [None, "sql_compact", "cypher"])
def test_sql_only_agents_resolve_and_validate_at_construction(agent_cls: type[Any], formatter_name: str | None) -> None:
    config = agent_cls.config_cls(schema_formatter=formatter_name)
    if formatter_name == "cypher":
        with pytest.raises(ValueError, match="not 'sql'"):
            agent_cls(config)
    else:
        agent = agent_cls(config)
        assert agent.formatter.name == (formatter_name or "sql_ddl")
        assert config.schema_formatter == formatter_name


def test_agent_ensembler_uses_shared_defaults_and_overrides() -> None:
    assert AgentEnsembler(AgentEnsemblerConfig(result_dirs=[])).formatter.name == "sql_ddl"
    config = AgentEnsemblerConfig(result_dirs=[], schema_formatter="sql_compact")
    assert AgentEnsembler(config).formatter.name == "sql_compact"
    with pytest.raises(ValueError, match="not 'sql'"):
        AgentEnsembler(AgentEnsemblerConfig(result_dirs=[], schema_formatter="cypher"))


async def test_schema_linking_validates_formatter_before_embedding_examples(monkeypatch: pytest.MonkeyPatch) -> None:
    embedder = Mock()
    monkeypatch.setattr("tabulaflow.research.agents.schema_linking.QuestionEmbedder", embedder)
    config = SchemaLinkingAgent.config_cls(schema_formatter="cypher", num_few_shot_examples=1)

    with pytest.raises(ValueError, match="not 'sql'"):
        await SchemaLinkingAgent.from_config_async(config, _dataset())

    embedder.assert_not_called()


def test_research_options_apply_only_to_sql_and_preserve_custom_graph_formatters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CustomGraphFormatter(CypherSchemaFormatter):
        name: ClassVar[str] = "test_research_graph"

    monkeypatch.setattr(schema_formatter_registry, "_classes", schema_formatter_registry._classes.copy())
    schema_formatter_registry.register(CustomGraphFormatter)
    config = BasicAgentConfig(
        schema_formatter="sql_compact", compact_table_families=False, formatter_max_total_columns=7
    )
    formatter = config.create_schema_formatter("sql")
    assert isinstance(formatter, SQLCompactSchemaFormatter)
    assert formatter.compact_table_families is False
    assert formatter.max_total_columns == 7

    config.schema_formatter = "test_research_graph"
    assert isinstance(config.create_schema_formatter("property_graph"), CustomGraphFormatter)


class _ModelReached(Exception):
    pass


@pytest.mark.parametrize("agent_cls", [DirectPromptAgent, FullSchemaAgent])
async def test_one_agent_formats_sql_and_graph_without_mutating_config(
    agent_cls: type[DirectPromptAgent | FullSchemaAgent], monkeypatch: pytest.MonkeyPatch
) -> None:
    prompts = []

    def capture_model(*args: Any, **kwargs: Any) -> None:
        prompts.append(kwargs["instructions"])
        raise _ModelReached

    monkeypatch.setattr(f"{agent_cls.__module__}.make_agent", capture_model)
    config = BasicAgentConfig()
    agent = agent_cls(config)
    task = SimpleNL2QTask(qid="1", db="db", question="Count rows.", gold_query=GoldQuery(query="SELECT 1"))
    for schema, language in [
        (SQLSchema(display_name="shop", tables=[]), "sqlite"),
        (PropertyGraphSchema(display_name="movies"), "cypher"),
    ]:
        connector = cast(DataConnector, SimpleNamespace(schema=schema, language=language))
        with pytest.raises(_ModelReached):
            await agent.predict_async(task, connector)
    assert "**Data source:** `shop`" in prompts[0]
    assert "Node properties:" in prompts[1]
    assert "writes cypher queries" in prompts[1]
    assert config.schema_formatter is None


@pytest.mark.parametrize("agent_cls", [DirectPromptAgent, FullSchemaAgent])
async def test_incompatible_direct_agent_override_fails_before_model_construction(
    agent_cls: type[DirectPromptAgent | FullSchemaAgent], monkeypatch: pytest.MonkeyPatch
) -> None:
    make_model = Mock()
    monkeypatch.setattr(f"{agent_cls.__module__}.make_agent", make_model)
    agent = agent_cls(BasicAgentConfig(schema_formatter="sql_ddl"))
    connector = cast(
        DataConnector, SimpleNamespace(schema=PropertyGraphSchema(display_name="movies"), language="cypher")
    )
    task = SimpleNL2QTask(qid="1", db="db", question="Count nodes.", gold_query=GoldQuery(query="RETURN 1"))
    with pytest.raises(ValueError, match="not 'property_graph'"):
        await agent.predict_async(task, connector)
    make_model.assert_not_called()


def test_research_schema_support_is_not_expanded_to_rdf() -> None:
    with pytest.raises(TypeError, match="Unsupported research schema kind"):
        format_schema_for_prompt(RDFSchema(display_name="rdf"), BasicAgentConfig())


class _FormattingAgent:
    name = "formatting_test"
    task_type = "simple"
    output_type = "simple"
    config_cls = BasicAgentConfig

    def __init__(self, config: BasicAgentConfig) -> None:
        self.config = config

    @classmethod
    async def from_config_async(cls, config: BasicAgentConfig) -> "_FormattingAgent":
        return cls(config)

    async def predict_async(self, task: SimpleNL2QTask, connector: Any) -> SimpleNL2QTaskOutput:
        rendered = format_schema_for_prompt(connector.schema, self.config)
        return SimpleNL2QTaskOutput(
            **task.model_dump(exclude={"extra_info"}), pred_query=None, extra_info={"rendered_schema": rendered}
        )


def _dataset(name: str = "mixed", *, graph_only: bool = False) -> NL2QDataset:
    schemas: dict[str, SQLSchema | PropertyGraphSchema] = {"graph": PropertyGraphSchema(display_name="movies")}
    if not graph_only:
        schemas = {"sql": SQLSchema(display_name="shop", tables=[]), **schemas}
    return NL2QDataset(
        name=name,
        split="test",
        tasks=[
            SimpleNL2QTask(qid=db, db=db, question="Count rows.", gold_query=GoldQuery(query="SELECT 1"))
            for db in schemas
        ],
        db_connectors={db: SimpleNamespace(schema=schema) for db, schema in schemas.items()},
    )


async def test_pipeline_formats_mixed_schemas_and_ignores_unused_connectors() -> None:
    config = BasicAgentConfig()
    dataset = _dataset()
    dataset.db_connectors["unused"] = object()
    result = await predict.predict_async(_FormattingAgent, config, dataset, batch_size=2, verbose=False)
    assert result.agent_config["schema_formatter"] is None
    assert config.schema_formatter is None
    schemas = {task.db: task.extra_info["rendered_schema"] for task in result.tasks}
    assert "**Data source:** `shop`" in schemas["sql"]
    assert "Node properties:" in schemas["graph"]


def test_preflight_validates_without_constructing_formatters(monkeypatch: pytest.MonkeyPatch) -> None:
    class ValidationOnlyFormatter(SQLCompactSchemaFormatter):
        name: ClassVar[str] = "test_validation_only"

        def __init__(self) -> None:
            raise AssertionError("Preflight must not construct formatters")

    monkeypatch.setattr(schema_formatter_registry, "_classes", schema_formatter_registry._classes.copy())
    schema_formatter_registry.register(ValidationOnlyFormatter)
    dataset = _dataset()
    dataset.tasks = [task for task in dataset.tasks if task.db == "sql"]

    validate_run_schema_formatters(BasicAgentConfig(schema_formatter=ValidationOnlyFormatter.name), dataset)


async def test_pipeline_validates_all_databases_before_constructing_any_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    construct = AsyncMock()
    monkeypatch.setattr(_FormattingAgent, "from_config_async", construct)
    with pytest.raises(ValueError, match="not 'property_graph'"):
        await predict.predict_async(
            _FormattingAgent, BasicAgentConfig(schema_formatter="sql_compact"), _dataset(), batch_size=1, verbose=False
        )
    construct.assert_not_called()


@pytest.mark.parametrize(
    ("dataset_name", "override", "expected"),
    [
        ("bird-sql", None, "**Data source:** `shop`"),
        ("arcs", None, "**Data source:** `shop`"),
        ("cypherbench", None, "Node properties:"),
        ("arcs", "sql_compact", "Data source: shop"),
    ],
)
async def test_cli_and_python_use_the_same_formatter_defaults(
    dataset_name: str, override: str | None, expected: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    dataset = _dataset(dataset_name, graph_only=dataset_name == "cypherbench")
    if dataset_name != "cypherbench":
        dataset.tasks = [task for task in dataset.tasks if task.db == "sql"]
    loader = SimpleNamespace(splits=["test"], get_split_async=AsyncMock(return_value=dataset))
    monkeypatch.setattr(dataset_registry, "get_class", lambda name: lambda **kwargs: loader)
    monkeypatch.setattr(agent_registry, "get_class", lambda name: _FormattingAgent)
    monkeypatch.setattr(predict, "preflight_benchmark", AsyncMock())
    monkeypatch.setattr(predict, "initialize_agent_runtime", Mock())
    monkeypatch.setattr(predict, "configure_research_observability", Mock())
    run_dir = tmp_path / "run"
    argv = ["predict", "--agent", "direct_prompting", "--dataset", dataset_name, "--output-dir", str(run_dir)]
    if override is not None:
        argv += ["--schema-formatter", override]
    monkeypatch.setattr(sys, "argv", argv)

    python_result = await predict.predict_async(
        _FormattingAgent, BasicAgentConfig(schema_formatter=override), dataset, batch_size=1, verbose=False
    )
    await predict.main_async()
    cli_result = NL2QRunResult.model_validate_json((run_dir / "result.json").read_text())
    assert cli_result.agent_config == python_result.agent_config
    assert [task.extra_info for task in cli_result.tasks] == [task.extra_info for task in python_result.tasks]
    assert all(expected in task.extra_info["rendered_schema"] for task in cli_result.tasks)
