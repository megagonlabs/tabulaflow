from typing import ClassVar
from tabulaflow.research.types import (
    NL2QTaskOutput,
    SimpleAmbigNL2QTaskOutput,
    FlatAmbigNL2QTaskOutput,
    StructuredAmbigNL2QTaskOutput,
    NumericOrNull,
)
from tabulaflow.data import DataConnector
from tabulaflow.research.metrics.registry import metric_registry

AmbigTaskOutput = SimpleAmbigNL2QTaskOutput | FlatAmbigNL2QTaskOutput | StructuredAmbigNL2QTaskOutput


@metric_registry.register
class GoldAmbigPointStats:
    name: ClassVar[str] = "gold_ambig_point_stats"
    compatible_output_types: ClassVar[list[str]] = ["ambig-simple", "ambig-flat", "ambig-structured"]

    async def compute_async(
        self,
        task: NL2QTaskOutput,
        db_connector: DataConnector | None = None,
    ) -> dict[str, NumericOrNull]:
        assert isinstance(task, AmbigTaskOutput)
        return {
            "gold_num_ambig_points": len(task.gold_ambiguity_points),
            "gold_num_interpretation_comb": task.gold_num_interpretation_comb,
        }
