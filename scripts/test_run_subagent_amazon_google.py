"""Replicate the resolve-mode test using run_subagent_for_each_row.

Validates the hypothesis: per-row LLM resolution (which is what
``add_canonical_name`` resolve mode does internally) can be expressed equivalently
via ``run_subagent_for_each_row`` with a task_query + task_instruction.

Same dataset and same 10 labeled rows as scripts/test_canonical_amazon_google.py.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import logging
from pathlib import Path

import pandas as pd
import sqlalchemy

from tabulaflow.data.config import SQLConnectorConfig
from tabulaflow.data.registry import DBRegistry
from tabulaflow.data.sql import SQLConnector
from tabulaflow.agents.tools.protocols import ToolProgressUpdate
from tabulaflow.agents.tools.run_subagent_for_each_row import RunSubagentForEachRowTool

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "magellan" / "amazon_google"

TASK_INSTRUCTION = """\
You are matching one Amazon product against the Google product catalog (table `google`,
columns: id, name, description, manufacturer, price).

Amazon product to resolve:
  title:        {{ title }}
  manufacturer: {{ manufacturer }}

Find the row in `google` that refers to the SAME real-world product. Use `run_query` to
search — try matches on `name` (the title-equivalent column) and `manufacturer`.

Identity rule: two products refer to the same product if their names describe the same make,
model, edition, and platform. Minor differences in capitalisation, punctuation, or
'edition'/'version' wording are not material; different versions or platforms ARE.

Use a three-valued judgment: SAME (commit), DIFFERENT (rule out), or UNDECIDED (insufficient
evidence). Only commit to a match on a SAME judgment.

On a SAME match: respond with the EXACT `id` column value of the matched Google row (a long
URL string like 'http://www.google.com/base/feeds/snippets/12345...'). Copy it verbatim from
the `id` column — do NOT respond with the product name or any other column. Your final
response must be ONLY this URL, nothing else.

If no candidate qualifies as SAME, call abort_task("no confident match")."""


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--labeled-only", action="store_true", default=True)
    parser.add_argument("--db", type=str, default="/tmp/tabulaflow_subagent_ag.duckdb")
    parser.add_argument("--llm", type=str, default="openai-responses:gpt-5-mini")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")

    db_path = Path(args.db)
    if db_path.exists():
        db_path.unlink()
    table_a = DATA_DIR / "tableA.csv"
    table_b = DATA_DIR / "tableB.csv"
    matches = DATA_DIR / "matches.csv"

    connector = await SQLConnector.from_url_async(
        global_id="subagent-stress-ag",
        url=f"duckdb:///{db_path}",
        db_name="workspace",
        read_only=False,
        config=SQLConnectorConfig(schema_cache_mode="off", query_cache_mode="off"),
    )

    amazon_df = pd.read_csv(table_a, encoding="latin-1")
    google_df = pd.read_csv(table_b, encoding="latin-1")
    if args.labeled_only:
        labeled = set(pd.read_csv(matches, encoding="latin-1")["idAmazon"])
        amazon_df = amazon_df[amazon_df["id"].isin(labeled)].copy()
    if args.limit >= 0:
        amazon_df = amazon_df.head(args.limit).copy()
    amazon_df["canonical_id"] = None

    await connector.write_dataframe_async(df=amazon_df, table_name="amazon", mode="replace")
    await connector.write_dataframe_async(df=google_df, table_name="google", mode="replace")
    await connector.refresh_schema_async()

    n_amazon = await connector.run_query_async(sqlalchemy.text("SELECT COUNT(*) FROM amazon"))
    n_google = await connector.run_query_async(sqlalchemy.text("SELECT COUNT(*) FROM google"))
    print(f"Loaded amazon={n_amazon.df.iloc[0, 0]} rows, google={n_google.df.iloc[0, 0]} rows")

    registry = DBRegistry()
    registry.register("workspace", connector)

    tool = RunSubagentForEachRowTool(
        connector,
        registry=registry,
        subagent_llm=args.llm,
        store_metadata=True,
    )

    def _progress(update: ToolProgressUpdate) -> None:
        print(f"  progress: {update.completed}/{update.total}")

    tool.on_progress = _progress

    print("Running run_subagent_for_each_row…")
    summary = await tool(
        schema_name=None,
        table_name="amazon",
        task_query="SELECT id, title, manufacturer FROM amazon",
        task_instruction=TASK_INSTRUCTION,
        key_columns=["id"],
        output_columns=["canonical_id"],
        enable_run_query_tool=True,
    )
    print("Tool summary:", summary)

    pred_res = await connector.run_query_async(sqlalchemy.text("SELECT id, canonical_id FROM amazon"))
    preds: dict[str, str | None] = {}
    for row in pred_res.df.itertuples():
        v = row.canonical_id
        preds[row.id] = None if (v is None or (isinstance(v, float) and pd.isna(v)) or pd.isna(v)) else str(v)

    truth: dict[str, str] = {}
    with matches.open() as f:
        for r in csv.DictReader(f):
            truth[r["idAmazon"]] = r["idGoogleBase"]

    tp = fp = fn = tn = 0
    examples: list[tuple[str, str, str, str]] = []
    for amazon_id, canonical_id in preds.items():
        gt = truth.get(amazon_id)
        is_match_pred = (
            canonical_id is not None and isinstance(canonical_id, str) and canonical_id.startswith("http://www.google")
        )
        if gt is not None:
            if is_match_pred and canonical_id == gt:
                tp += 1
            elif is_match_pred:
                fp += 1
                examples.append((amazon_id, gt, canonical_id, "wrong-match"))
            else:
                fn += 1
                examples.append((amazon_id, gt, canonical_id or "", "missed"))
        else:
            if is_match_pred:
                fp += 1
                examples.append((amazon_id, "(none)", canonical_id, "false-positive"))
            else:
                tn += 1

    total = tp + fp + fn + tn
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    print()
    print(f"Scored {total} amazon rows  TP={tp}  FP={fp}  FN={fn}  TN={tn}")
    print(f"  precision={precision:.3f}  recall={recall:.3f}  F1={f1:.3f}")
    if examples:
        print("  Sample mistakes:")
        for amazon_id, gt, got, kind in examples[:8]:
            print(f"    [{kind}] amazon={amazon_id}  gt={gt}  got={got}")


if __name__ == "__main__":
    asyncio.run(main())
