import asyncio
import collections
import logging
from typing import Any, ClassVar
import pandas as pd
from pydantic import BaseModel
from tabulaflow.research.agenthub.base import BaseAgentConfig
from tabulaflow.research.agenthub.utils import instrument
from tabulaflow.research.types import SimpleNL2QTask, SimpleNL2QTaskOutput
from tabulaflow.data import SQLConnectorProtocol
from tabulaflow.research.pipelines.populate_exec_results import populate_task_async


logger = logging.getLogger(__name__)

_FLOAT_ROUND_DIGITS = 6


def _normalize_value(v: Any) -> str:
    """Convert a single cell value to a stable, comparable string.

    Handles NULL variants, float precision, and arbitrary types.
    """
    if v is None or pd.isna(v):
        return "<NULL>"
    if isinstance(v, float):
        return str(round(v, _FLOAT_ROUND_DIGITS))
    return str(v)


class MajorityEnsemblerConfig(BaseModel):
    result_dirs: list[str]
    skip_empty_results: bool = True


class MajorityEnsembler:
    name: ClassVar = "majority_ensembler"
    task_type: ClassVar = "simple"
    output_type: ClassVar = "simple"
    config_cls: ClassVar[type[BaseAgentConfig]] = MajorityEnsemblerConfig

    def __init__(self, config: MajorityEnsemblerConfig):
        self.config = config

    @classmethod
    async def from_config_async(cls, config: MajorityEnsemblerConfig) -> "MajorityEnsembler":
        return cls(config)

    @instrument
    async def ensemble_async(
        self, task: SimpleNL2QTask, db_connector: SQLConnectorProtocol, task_outputs: list[SimpleNL2QTaskOutput]
    ) -> SimpleNL2QTaskOutput:
        # Filter to outputs that have a pred_query
        candidates = [output for output in task_outputs if output.pred_query is not None]

        if not candidates:
            return task_outputs[0]

        # Populate exec results for all candidates (skips queries that already have results)
        await asyncio.gather(*[populate_task_async(output, db_connector) for output in candidates])

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
            df = df.reindex(sorted(df.columns), axis=1)
            rows = [tuple(_normalize_value(v) for v in row) for row in df.itertuples(index=False, name=None)]
            hashable = tuple(sorted(set(rows)))
            result2candidates[hashable].append(output)

        # Select the best output via majority voting
        majority_group = max(result2candidates.values(), key=len)
        best_output = majority_group[0]

        return SimpleNL2QTaskOutput(
            **task.model_dump(),
            pred_query=best_output.pred_query,
        )
