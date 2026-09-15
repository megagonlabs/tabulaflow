"""Database enum choices constrain extraction and enrichment before writes."""

from pathlib import Path

import duckdb
import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse, RetryPromptPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from tabulaflow.agents.tools import ExtractRowsFromDocumentsTool, RunSubagentForEachRowTool
from tabulaflow.data import SQLConnector
from tabulaflow.data.config import SQLConnectorConfig


@pytest.mark.parametrize("operation", ["extraction", "enrichment"])
async def test_tools_retry_invalid_enum_before_writing(tmp_path: Path, operation: str) -> None:
    path = tmp_path / "tickets.duckdb"
    raw = duckdb.connect(str(path))
    raw.execute("CREATE TABLE tickets (id INTEGER, category ENUM ('billing', 'account', 'technical'))")
    if operation == "enrichment":
        raw.execute("INSERT INTO tickets (id) VALUES (1)")
    raw.commit()
    raw.close()

    calls = 0

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal calls
        calls += 1
        tool = info.output_tools[0]
        schema = tool.parameters_json_schema
        if operation == "extraction":
            schema = schema["$defs"]["ExtractedEntity"]
        assert schema["properties"]["category"]["anyOf"][0]["enum"] == ["billing", "account", "technical"]
        if calls == 2:
            assert any(isinstance(part, RetryPromptPart) for message in messages for part in message.parts)
        category = "unknown" if calls == 1 else "billing"
        answer: dict[str, object] = (
            {"entities": [{"category": category}]} if operation == "extraction" else {"category": category}
        )
        return ModelResponse(parts=[ToolCallPart(tool.name, answer)])

    connector = await SQLConnector.from_url_async(
        f"duckdb:///{path}",
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", sql_query_cache_mode="off"),
    )
    try:
        model = FunctionModel(respond)
        if operation == "extraction":
            summary = await ExtractRowsFromDocumentsTool(connector, subagent_llm=model).execute(
                None,
                "tickets",
                task_query="SELECT 'I was charged twice.' AS content",
                task_instruction="Classify the support ticket.",
                output_columns=["category"],
            )
            assert "Extracted 1 entities" in summary
        else:
            summary = await RunSubagentForEachRowTool(connector, subagent_llm=model).execute(
                None,
                "tickets",
                task_query="SELECT id FROM tickets",
                task_instruction="Classify the support ticket: I was charged twice.",
                key_columns=["id"],
                output_columns=["category"],
            )
            assert "succeeded for 1 rows, failed for 0 rows" in summary
        assert calls == 2
        result = await connector.run_query_async("SELECT category FROM tickets")
        assert result.error is None and result.df is not None
        assert result.df.to_dict("records") == [{"category": "billing"}]

    finally:
        await connector.close_async()
