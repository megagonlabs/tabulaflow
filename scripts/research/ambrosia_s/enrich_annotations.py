"""Enrich AMBROSIA-S annotations with questions and gold SQL from the source CSV."""

import argparse
import json
import re
from pathlib import Path
from typing import Any, TypedDict

import pandas as pd


class CsvAnnotation(TypedDict):
    question: str
    gold_queries: list[str]


def split_gold_queries(value: str) -> list[str]:
    parts = re.split(r"\n\nselect", value, flags=re.IGNORECASE)
    queries = [re.sub(r"\n\n+", "\n", parts[0].strip())]
    queries.extend("SELECT " + re.sub(r"\n\n+", "\n", part.strip()) for part in parts[1:])
    return queries


def load_csv_annotations(path: Path) -> dict[str, CsvAnnotation]:
    frame = pd.read_csv(path)
    return {
        str(index): {
            "question": str(row["question"]).strip(),
            "gold_queries": split_gold_queries(str(row["gold_queries"]).strip()),
        }
        for index, row in frame.iterrows()
    }


def enrich_annotations(
    annotations: list[dict[str, Any]], csv_annotations: dict[str, CsvAnnotation]
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for annotation in annotations:
        qid = str(annotation["qid"])
        if qid not in csv_annotations:
            raise ValueError(f"qid {qid} not found in the source CSV")

        output = dict(annotation)
        exec_results = output.pop("gold_exec_results")
        source = csv_annotations[qid]
        if len(source["gold_queries"]) != len(exec_results):
            raise ValueError(
                f"qid {qid}: found {len(source['gold_queries'])} gold queries but {len(exec_results)} execution results"
            )

        output["question"] = source["question"]
        output["gold_queries"] = [
            {
                "id": f"GQRY-A.{index}",
                "query": query,
                "parameter_names": [],
                "parameter_values": {},
                "exec_result": exec_result,
                "other_exec_results": [],
                "required_columns": None,
                "required_sorted": False,
                "extra_info": {},
            }
            for index, (query, exec_result) in enumerate(zip(source["gold_queries"], exec_results, strict=True))
        ]
        enriched.append(output)
    return enriched


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich AMBROSIA-S JSON annotations from ambrosia.csv.")
    parser.add_argument("--csv", type=Path, default=Path("data/ambrosia-s/ambrosia/ambrosia.csv"))
    parser.add_argument("--input", type=Path, default=Path("data/ambrosia-s/ambrosia_test.json"))
    parser.add_argument("--output", type=Path, default=Path("data/ambrosia-s/ambrosia_test_processed.json"))
    args = parser.parse_args()

    csv_annotations = load_csv_annotations(args.csv)
    annotations = json.loads(args.input.read_text())
    if not isinstance(annotations, list):
        raise ValueError(f"Expected an array in {args.input}")

    enriched = enrich_annotations(annotations, csv_annotations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(enriched, indent=2, ensure_ascii=False) + "\n")
    print(f"Wrote {len(enriched)} annotations to {args.output}")


if __name__ == "__main__":
    main()
