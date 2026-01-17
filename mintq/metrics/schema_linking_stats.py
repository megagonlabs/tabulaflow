from typing import ClassVar
from mintq.schema import NL2QTaskOutput
from mintq.metrics.base import metric_registry
from mintq.utils import extract_all_source_columns


@metric_registry.register
class SchemaLinkingStats:
    name: ClassVar[str] = "schema_linking_stats"
    compatible_output_types: ClassVar[list[str]] = ["simple"]

    async def compute_async(self, task: NL2QTaskOutput) -> float:
        if "linked_schema" not in task.extra_info:
            return {
                "linked_schema_p": 0.0,
                "linked_schema_r": 0.0,
                "linked_schema_f1": 0.0,
            }

        pred_linked_schema = task.extra_info["linked_schema"]
        pred_linked_schema = set((col["table_name"], col["column_name"]) for col in pred_linked_schema)
        gold_linked_schema = extract_all_source_columns(task.gold_query.query)
        gold_linked_schema = set(gold_linked_schema)

        n_overlap = len(pred_linked_schema & gold_linked_schema)
        n_pred = len(pred_linked_schema)
        n_gold = len(gold_linked_schema)

        p = n_overlap / n_pred if n_pred > 0 else 0.0
        r = n_overlap / n_gold if n_gold > 0 else 0.0
        f1 = 2 * p * r / (p + r) if p + r > 0 else 0.0
        return {
            "linked_schema_p": p,
            "linked_schema_r": r,
            "linked_schema_f1": f1,
        }
