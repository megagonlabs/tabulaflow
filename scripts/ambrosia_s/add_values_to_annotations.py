# mypy: ignore-errors
"""
Enrich ambrosia_{few_shot_examples,test}.json with question and gold_queries from ambrosia.csv.

This script adds:
1. "question" field from CSV
2. "gold_queries" field from CSV (split by \n\n)

Validates that the number of gold_queries matches the number of gold_exec_results.
"""

from pathlib import Path
from typing import Any
import argparse
import json
import re

import pandas as pd


def load_csv_data(csv_path: Path) -> dict[str, dict[str, Any]]:
    """Load CSV and create lookup dictionary mapping qid to question and gold_queries."""
    lookup = {}

    df = pd.read_csv(csv_path)
    for idx, row in df.iterrows():
        qid = str(idx)

        question = row["question"].strip()
        gold_queries_raw = row["gold_queries"].strip()

        # Split by "\n\nselect" ignoring case
        parts = re.split(r"\n\nselect", gold_queries_raw, flags=re.IGNORECASE)

        # First part already has SELECT, rest need it added back
        gold_queries = [re.sub(r"\n\n+", "\n", parts[0].strip())]
        for part in parts[1:]:
            gold_queries.append("SELECT " + re.sub(r"\n\n+", "\n", part.strip()))

        lookup[qid] = {"question": question, "gold_queries": gold_queries}

    return lookup


def enrich_json_data(
    json_data: list[dict[str, Any]], csv_lookup: dict[str, dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Enrich JSON entries with question and gold_queries from CSV.

    Returns:
        Tuple of (enriched_data, statistics)
    """
    enriched_data = []
    stats = {"total": len(json_data), "success": 0, "missing_qid": 0, "validation_errors": []}

    for entry in json_data:
        qid = entry.get("qid")

        if qid not in csv_lookup:
            stats["missing_qid"] += 1
            raise ValueError(f"qid {qid} not found in CSV. This should not happen for ambrosia_test.json.")

        csv_data = csv_lookup[qid]

        # Validate: number of gold_queries should match gold_exec_results
        gold_exec_results = entry.pop("gold_exec_results", [])
        num_queries = len(csv_data["gold_queries"])
        num_results = len(gold_exec_results)

        if num_queries != num_results:
            error_msg = (
                f"qid {qid}: Mismatch between gold_queries ({num_queries}) and gold_exec_results ({num_results})"
            )
            stats["validation_errors"].append(error_msg)
            raise ValueError(error_msg)

        # Add question and gold_queries
        entry["question"] = csv_data["question"]
        entry["gold_queries"] = [
            {
                "id": f"GQRY-A.{i}",
                "query": gold_query,
                "parameter_names": [],
                "parameter_values": {},
                "exec_result": exec_result,
                "other_exec_results": [],
                "required_columns": None,
                "required_sorted": False,
                "extra_info": {},
            }
            for i, (gold_query, exec_result) in enumerate(zip(csv_data["gold_queries"], gold_exec_results))
        ]

        enriched_data.append(entry)
        stats["success"] += 1

    return enriched_data, stats


def main():
    parser = argparse.ArgumentParser(description="Enrich ambrosia_test.json with question and gold_queries from CSV")
    parser.add_argument(
        "--csv", type=Path, default=Path("data/ambrosia_s/ambrosia/ambrosia.csv"), help="Path to ambrosia.csv file"
    )
    parser.add_argument(
        "--input", type=Path, default=Path("data/ambrosia_s/ambrosia_test.json"), help="Path to input JSON file"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/ambrosia_s/ambrosia_test_processed.json"),
        help="Path to output enriched JSON file",
    )

    args = parser.parse_args()

    # Validate input files exist
    if not args.csv.exists():
        raise FileNotFoundError(f"CSV file not found: {args.csv}")
    if not args.input.exists():
        raise FileNotFoundError(f"Input JSON file not found: {args.input}")

    print(f"Loading CSV data from {args.csv}...")
    csv_lookup = load_csv_data(args.csv)
    print(f"  Loaded {len(csv_lookup)} entries from CSV")

    print(f"\nLoading JSON data from {args.input}...")
    with open(args.input, "r", encoding="utf-8") as f:
        json_data = json.load(f)
    print(f"  Loaded {len(json_data)} entries from JSON")

    print("\nEnriching JSON data...")
    enriched_data, stats = enrich_json_data(json_data, csv_lookup)

    print("\nWriting enriched data to", args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(enriched_data, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 80)
    print("Summary:")
    print("=" * 80)
    print(f"Total entries processed: {stats['total']}")
    print(f"Successfully enriched: {stats['success']}")
    print(f"Missing qids in CSV: {stats['missing_qid']}")
    print(f"Validation errors: {len(stats['validation_errors'])}")

    if stats["validation_errors"]:
        print("\nValidation errors:")
        for error in stats["validation_errors"]:
            print(f"  - {error}")

    print(f"\nOutput written to: {args.output}")


if __name__ == "__main__":
    main()
