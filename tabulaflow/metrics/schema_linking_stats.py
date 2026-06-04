from typing import ClassVar
from tabulaflow.core.types import NumericOrNull, SQLSchema
from tabulaflow.research.types import NL2QTaskOutput
from tabulaflow.metrics.base import metric_registry
from tabulaflow.core.utils import extract_all_source_columns
from tabulaflow.core.db_connector import NL2QDBConnector
from tabulaflow.metrics.utils import get_final_gold_query


@metric_registry.register
class SchemaLinkingStats:
    name: ClassVar[str] = "schema_linking_stats"
    compatible_output_types: ClassVar[list[str]] = ["simple", "ambig-simple", "ambig-flat", "ambig-structured"]

    async def compute_async(
        self, task: NL2QTaskOutput, db_connector: NL2QDBConnector | None = None
    ) -> dict[str, NumericOrNull]:
        if db_connector is None:
            raise ValueError("SchemaLinkingStats requires a db_connector")

        gold_query = get_final_gold_query(task, check_exec_result=False)

        schema = db_connector.schema
        if not isinstance(schema, SQLSchema):
            raise TypeError(f"SchemaLinkingStats requires a SQL schema, got {type(schema)!r}")

        res: dict[str, NumericOrNull] = {
            "linked_percentage": len(task.extra_pred_info.linked_schema or []) / len(schema.get_all_column_refs()),
        }

        # We rely on the gold query to extract the ground-truth linked schema.
        # If the gold query is not available, we cannot compute the p/r/f1 metrics.
        if gold_query.query is None:
            res["linked_schema_p"] = None
            res["linked_schema_r"] = None
            res["linked_schema_f1"] = None
            res["perfect_linked_schema_r"] = None
            return res

        if task.extra_pred_info.linked_schema is None:
            res["linked_schema_p"] = 0.0
            res["linked_schema_r"] = 0.0
            res["linked_schema_f1"] = 0.0
            res["perfect_linked_schema_r"] = 0.0
            return res

        pred_linked_schema = set(
            (col.table_name.lower(), col.column_name.lower()) for col in task.extra_pred_info.linked_schema
        )
        gold_linked_schema = set(
            (c[0].lower(), c[1].lower())
            for c in extract_all_source_columns(gold_query.query, language=db_connector.language)
        )

        n_overlap = len(pred_linked_schema & gold_linked_schema)
        n_pred = len(pred_linked_schema)
        n_gold = len(gold_linked_schema)

        p = n_overlap / n_pred if n_pred > 0 else 0.0
        r = n_overlap / n_gold if n_gold > 0 else 0.0
        f1 = 2 * p * r / (p + r) if p + r > 0 else 0.0
        res["linked_schema_p"] = p
        res["linked_schema_r"] = r
        res["linked_schema_f1"] = f1
        res["perfect_linked_schema_r"] = float(r == 1.0)
        return res
