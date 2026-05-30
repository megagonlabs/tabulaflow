"""Stress-test add_canonical_name resolve mode on the Magellan Amazon-Google dataset.

Loads tableA (Amazon, source) + tableB (Google, reference) into a DuckDB workspace,
adds a ``canonical_id`` column, runs resolve mode with ``input_column=title`` and
``reference_column=id``, and scores against matches.csv ground truth.

Usage:
    uv run scripts/test_canonical_amazon_google.py --limit 30
    uv run scripts/test_canonical_amazon_google.py --limit -1   # full 1363 source rows
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import logging
from pathlib import Path

from mintq.db_connector.sql_conn import SQLConnector
from mintq.toolhub.add_canonical_name import AddCanonicalNameTool

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "magellan" / "amazon_google"


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=30, help="Source rows to keep (-1 for all)")
    parser.add_argument(
        "--labeled-only",
        action="store_true",
        help="Keep only amazon rows present in matches.csv (positive labels)",
    )
    parser.add_argument("--db", type=str, default="/tmp/mintq_canonical_ag.duckdb")
    parser.add_argument("--llm", type=str, default="openai-responses:gpt-5-mini")
    parser.add_argument("--max-concurrency", type=int, default=100)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s | %(message)s")

    db_path = Path(args.db)
    if db_path.exists():
        db_path.unlink()
    table_a = DATA_DIR / "tableA.csv"
    table_b = DATA_DIR / "tableB.csv"
    matches = DATA_DIR / "matches.csv"
    for p in (table_a, table_b, matches):
        if not p.exists():
            raise FileNotFoundError(p)

    connector = await SQLConnector.from_url_async(
        global_id="canonical-stress-ag",
        url=f"duckdb:///{db_path}",
        db_name="workspace",
        read_only=False,
        enable_schema_caching=False,
        enable_query_caching=False,
    )

    import pandas as pd
    import sqlalchemy

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

    counts = await connector.run_query_async(sqlalchemy.text("SELECT COUNT(*) FROM amazon, (SELECT COUNT(*) AS g FROM google) g"))
    n_amazon = await connector.run_query_async(sqlalchemy.text("SELECT COUNT(*) FROM amazon"))
    n_google = await connector.run_query_async(sqlalchemy.text("SELECT COUNT(*) FROM google"))
    print(f"Loaded amazon={n_amazon.df.iloc[0, 0]} rows, google={n_google.df.iloc[0, 0]} rows")
    del counts

    tool = AddCanonicalNameTool(subagent_llm=args.llm, max_concurrency=args.max_concurrency)
    tool.attach_connector(connector)

    def _progress(c: int, t: int) -> None:
        if c == t or c % 25 == 0:
            print(f"  progress: {c}/{t}")

    tool.on_progress = _progress

    print("Running resolve…")
    summary = await tool(
        schema_name=None,
        table_name="amazon",
        canonical_column="canonical_id",
        instruction=(
            "Two products refer to the same real-world product if their titles describe the same "
            "make, model, edition, and platform. Minor differences in capitalisation, punctuation, "
            "or 'edition'/'version' wording are not material; different versions or platforms are."
        ),
        input_column="title",
        reference_schema=None,
        reference_table="google",
        reference_column="id",
    )
    print("Tool summary:", summary)

    # Score against ground truth.
    pred_res = await connector.run_query_async(sqlalchemy.text("SELECT id, canonical_id FROM amazon"))
    preds = {row.id: row.canonical_id for row in pred_res.df.itertuples()}

    truth: dict[str, str] = {}
    with matches.open() as f:
        for r in csv.DictReader(f):
            truth[r["idAmazon"]] = r["idGoogleBase"]

    tp = fp = fn = tn = 0
    examples: list[tuple[str, str, str, str]] = []
    for amazon_id, canonical_id in preds.items():
        gt = truth.get(amazon_id)
        is_match_pred = canonical_id is not None and isinstance(canonical_id, str) and canonical_id.startswith("http://www.google")
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
