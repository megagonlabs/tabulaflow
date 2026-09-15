import asyncio
import time
from typing import ClassVar

from pydantic import BaseModel, Field

from tabulaflow.agents.llm import make_agent
from tabulaflow.agents.trace import Trajectory, Usage
from tabulaflow.core import SQLSchema
from tabulaflow.data import DataConnector
from tabulaflow.output.formatting import SQLDDLSchemaFormatter
from tabulaflow.research.agents import BasicAgentConfig, DirectPromptAgent
from tabulaflow.research.benchmarks import BirdSQLDatasetLoader
from tabulaflow.research.metrics import BirdSQLEx, Executable
from tabulaflow.research.observability import trace_prediction
from tabulaflow.research.pipelines import evaluate_async, execute_async, predict_async
from tabulaflow.research.types import PredQuery, SimpleNL2QTask, SimpleNL2QTaskOutput


class StructuredQueryConfig(BaseModel):
    llm: str = "openai-responses:gpt-5-mini"


class SQLPrediction(BaseModel):
    query: str = Field(min_length=1, description="The SQL query answering the question.")


class StructuredQueryAgent:
    """Generate SQL as a typed model response using the complete schema."""

    name: ClassVar[str] = "structured_query"
    task_type: ClassVar[str] = "simple"
    output_type: ClassVar[str] = "simple"
    config_cls: ClassVar[type[StructuredQueryConfig]] = StructuredQueryConfig

    def __init__(self, config: StructuredQueryConfig):
        self.config = config

    @classmethod
    async def from_config_async(cls, config: StructuredQueryConfig) -> "StructuredQueryAgent":
        return cls(config)

    @trace_prediction
    async def predict_async(self, task: SimpleNL2QTask, db_connector: DataConnector) -> SimpleNL2QTaskOutput:
        if not isinstance(db_connector.schema, SQLSchema):
            raise TypeError("StructuredQueryAgent requires a SQL database.")
        started = time.perf_counter()
        schema = SQLDDLSchemaFormatter().format(db_connector.schema, include_descriptions=True)
        agent = make_agent(
            self.config.llm,
            output_type=SQLPrediction,
            instructions=f"Answer the question with a {db_connector.language} query.\nDatabase schema:\n{schema}",
        )
        prompt = task.model_dump_json(
            include={"question", "question_instructions", "dataset_instructions", "document"},
            exclude_none=True,
        )
        response = await agent.run(prompt)
        return SimpleNL2QTaskOutput(
            **task.model_dump(),
            pred_query=PredQuery(query=response.output.query),
            usage=Usage.from_pydantic_ai_usage(response.usage, self.config.llm),
            trajectory=Trajectory.from_pydantic_ai_messages(response.all_messages()),
            inference_metrics={"latency_seconds": time.perf_counter() - started},
        )


async def main() -> None:
    dataset = await BirdSQLDatasetLoader().get_split_async("dev", databases=["california_schools"], subsample_size=3)
    llm = "openai-responses:gpt-5-mini"
    strategies = [
        (DirectPromptAgent, BasicAgentConfig(llm=llm)),
        (StructuredQueryAgent, StructuredQueryConfig(llm=llm)),
    ]
    try:
        for agent_cls, config in strategies:
            result = await predict_async(agent_cls, config, dataset, batch_size=3)
            await execute_async(result, dataset, batch_size=3)
            await evaluate_async(result, dataset, metrics=[BirdSQLEx(), Executable()], batch_size=3)
            result.to_directory(f"runs/{agent_cls.name}", eval_metrics_in_summary=["bird_sql_ex", "executable"])
            print(agent_cls.name, result.aggregated_eval_metrics)
    finally:
        await asyncio.gather(*(connector.close_async() for connector in dataset.db_connectors.values()))


if __name__ == "__main__":
    asyncio.run(main())
