import asyncio
import collections
from typing import ClassVar
from pydantic import BaseModel
from tabulaflow.research.observability import trace_prediction
from tabulaflow.research.agents.ensemblers.utils import execution_result_key
from tabulaflow.research.types import SimpleNL2QTask, SimpleNL2QTaskOutput
from tabulaflow.data import SQLConnectorProtocol
from tabulaflow.research.query_execution import populate_query_exec_result


class MajorityEnsemblerConfig(BaseModel):
    result_dirs: list[str]
    skip_empty_results: bool = True


class MajorityEnsembler:
    name: ClassVar[str] = "majority"

    def __init__(self, config: MajorityEnsemblerConfig):
        self.config = config

    @trace_prediction
    async def ensemble_async(
        self, task: SimpleNL2QTask, db_connector: SQLConnectorProtocol, task_outputs: list[SimpleNL2QTaskOutput]
    ) -> SimpleNL2QTaskOutput:
        # Filter to outputs that have a pred_query
        candidates = [output for output in task_outputs if output.pred_query is not None]

        if not candidates:
            return task_outputs[0]

        await asyncio.gather(
            *(
                populate_query_exec_result(output.pred_query, db_connector)
                for output in candidates
                if output.pred_query is not None
            )
        )

        # Filter out candidates with execution errors
        candidates = [
            output
            for output in candidates
            if output.pred_query.exec_result.df is not None  # type: ignore[union-attr]
        ]
        # Optionally also filter out candidates with empty results
        if self.config.skip_empty_results:
            candidates = [
                output
                for output in candidates
                if not output.pred_query.exec_result.df.empty  # type: ignore[union-attr]
            ]

        if len(candidates) <= 1:
            best = candidates[0] if candidates else task_outputs[0]
            return SimpleNL2QTaskOutput(**task.model_dump(), pred_query=best.pred_query)

        # Group candidates by execution result for majority voting
        result2candidates: dict[tuple[tuple[str, ...], ...], list[SimpleNL2QTaskOutput]] = collections.defaultdict(list)
        for output in candidates:
            assert output.pred_query is not None and output.pred_query.exec_result is not None
            df = output.pred_query.exec_result.df
            assert df is not None
            result2candidates[execution_result_key(df)].append(output)

        # Select the best output via majority voting
        majority_group = max(result2candidates.values(), key=len)
        best_output = majority_group[0]

        return SimpleNL2QTaskOutput(
            **task.model_dump(),
            pred_query=best_output.pred_query,
        )
