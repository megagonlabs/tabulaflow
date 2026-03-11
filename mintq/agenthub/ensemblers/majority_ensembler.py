import asyncio
import collections
import math
import logging
from typing import Any, ClassVar
from pydantic import BaseModel
from mintq.agenthub.base import BaseAgentConfig
from mintq.agenthub.utils import instrument
from mintq.schema import SimpleNL2QTask, SimpleNL2QTaskOutput
from mintq.db_connector import BaseSQLDBConnector
from mintq.pipelines.populate_exec_results import populate_task_async


logger = logging.getLogger(__name__)

_FLOAT_ROUND_DIGITS = 6


def _normalize_value(v: Any) -> str:
    """Convert a single cell value to a stable, comparable string.

    Handles NULL variants, float precision, and arbitrary types.
    """
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "<NULL>"
    if isinstance(v, float):
        return str(round(v, _FLOAT_ROUND_DIGITS))
    return str(v)


class MajorityEnsemblerConfig(BaseModel):
    result_dirs: list[str]


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
        self, task: SimpleNL2QTask, db_connector: BaseSQLDBConnector, task_outputs: list[SimpleNL2QTaskOutput]
    ) -> SimpleNL2QTaskOutput:
        # Filter to outputs that have a pred_query
        valid_outputs = [(idx, output) for idx, output in enumerate(task_outputs) if output.pred_query is not None]

        if not valid_outputs:
            return task_outputs[0]

        # Populate exec results for all candidates (skips queries that already have results)
        await asyncio.gather(*[populate_task_async(output, db_connector) for _, output in valid_outputs])

        # Group candidates by execution result for majority voting
        result2indices: dict[tuple[tuple[str, ...], ...], list[int]] = collections.defaultdict(list)
        for idx, output in valid_outputs:
            assert output.pred_query is not None
            exec_result = output.pred_query.exec_result
            if exec_result is None or exec_result.error is not None or exec_result.df is None:
                continue
            if exec_result.df.empty:
                continue
            # Convert DataFrame to a hashable representation for comparison.
            # Normalize: sort columns by name, round floats, and coerce NULLs
            # so that semantically identical results from different queries match.
            df = exec_result.df
            df = df.reindex(sorted(df.columns), axis=1)
            rows = [tuple(_normalize_value(v) for v in row) for row in df.itertuples(index=False, name=None)]
            hashable = tuple(sorted(set(rows)))
            result2indices[hashable].append(idx)

        # Select the best output via majority voting
        if result2indices:
            majority_group = max(result2indices.values(), key=len)
            best_idx = majority_group[0]
        else:
            # No query produced valid results; fall back to the first candidate
            best_idx = valid_outputs[0][0]

        best_output = task_outputs[best_idx]

        return SimpleNL2QTaskOutput(
            **task.model_dump(),
            pred_query=best_output.pred_query,
        )
