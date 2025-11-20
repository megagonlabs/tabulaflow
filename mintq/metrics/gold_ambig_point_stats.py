from typing import ClassVar
from mintq.schema import SimpleAmbigNL2QTaskOutput, FlatAmbigNL2QTaskOutput, StructuredAmbigNL2QTaskOutput, NumericOrNull
from mintq.metrics.base import metric_registry


@metric_registry.register
class GoldAmbigPointStats:
    name: ClassVar[str] = "gold_ambig_point_stats"
    compatible_output_types: ClassVar[list[str]] = ["ambig-simple", "ambig-flat", "ambig-structured"]

    async def compute_async(
        self, task: SimpleAmbigNL2QTaskOutput | FlatAmbigNL2QTaskOutput | StructuredAmbigNL2QTaskOutput
    ) -> dict[str, NumericOrNull]:
        return {
            "gold_num_ambig_points": len(task.gold_ambiguity_points),
            "gold_num_interpretation_comb": task.gold_num_interpretation_comb,
        }
