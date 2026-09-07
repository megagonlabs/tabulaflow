"""Spider 2.0-DBT evaluation metric.

Compares tables in the predicted DuckDB (after ``dbt run``) against a gold
DuckDB, using the ``condition_tabs``, ``condition_cols``, and ``ignore_orders``
from the evaluation spec stored in ``DbtTaskOutput.gold_tables``.

Adapted from ``data/Spider2/spider2-dbt/evaluation_suite/eval_utils.py``.
"""

import logging
import math
import os
from typing import Any, ClassVar

import duckdb
import pandas as pd

from tabulaflow.data import DataConnector
from tabulaflow.research.metrics.registry import metric_registry
from tabulaflow.research.types import DbtTaskOutput, NL2QTaskOutput, NumericOrNull

logger = logging.getLogger(__name__)


def _compare_pandas_table(
    pred: pd.DataFrame,
    gold: pd.DataFrame,
    condition_cols: list[int],
    ignore_order: bool,
) -> bool:
    tolerance = 1e-2

    def vectors_match(v1: list[Any], v2: list[Any], ignore_order_: bool = False) -> bool:
        try:
            if ignore_order_:
                v1 = sorted(v1, key=lambda x: (x is None, str(x), isinstance(x, (int, float))))
                v2 = sorted(v2, key=lambda x: (x is None, str(x), isinstance(x, (int, float))))
            if len(v1) != len(v2):
                return False
            for a, b in zip(v1, v2):
                if pd.isna(a) and pd.isna(b):
                    continue
                elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
                    if not math.isclose(float(a), float(b), abs_tol=tolerance):
                        return False
                elif a != b:
                    return False
            return True
        except Exception:
            return False

    gold_cols = gold.iloc[:, condition_cols] if condition_cols else gold
    t_gold_list = gold_cols.transpose().values.tolist()
    t_pred_list = pred.transpose().values.tolist()

    for gold_vec in t_gold_list:
        if not any(vectors_match(gold_vec, pred_vec, ignore_order_=ignore_order) for pred_vec in t_pred_list):
            return False
    return True


def _read_duckdb_table(db_path: str, table_name: str) -> pd.DataFrame:
    con = duckdb.connect(database=db_path, read_only=True)
    try:
        return con.execute(f"SELECT * FROM {table_name}").fetchdf()
    finally:
        con.close()


@metric_registry.register
class Spider2DuckdbMatch:
    name: ClassVar[str] = "spider2_duckdb_match"
    compatible_output_types: ClassVar[list[str]] = ["dbt"]

    async def compute_async(self, task: NL2QTaskOutput, db_connector: DataConnector | None = None) -> NumericOrNull:
        assert isinstance(task, DbtTaskOutput)
        if not task.gold_db_path or not os.path.exists(task.gold_db_path):
            raise ValueError(f"No gold DuckDB for {task.qid}")

        if not task.gold_tables:
            raise ValueError(f"No gold_tables specified for {task.qid}")

        if not task.pred_db_path or not os.path.exists(task.pred_db_path):
            logger.info("No predicted DuckDB for %s", task.qid)
            return 0.0

        try:
            for gt in task.gold_tables:
                try:
                    pred_df = _read_duckdb_table(task.pred_db_path, gt.table_name)
                except Exception:
                    return 0.0

                gold_df = _read_duckdb_table(task.gold_db_path, gt.table_name)
                if not _compare_pandas_table(
                    pred_df,
                    gold_df,
                    condition_cols=gt.required_columns,
                    ignore_order=not gt.required_sorted,
                ):
                    return 0.0

            return 1.0
        except Exception as e:
            logger.warning("Error evaluating %s: %s", task.qid, e)
            return 0.0
