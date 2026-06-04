"""Flatten ARCS tasks into a single JSONL for HuggingFace upload.

Reuses ``ARCSDatasetLoader`` so the upsampling logic stays in one place: the
loader's ``test`` split already returns one ``AmbigNL2QTask`` per intended
gold query (101 raw tasks -> 311 upsampled rows).

By default, the gold SQL string (``gold_queries[*].query``) is kept only for
the first 2 unique original qids in each database (a small public sample)
and masked on the rest, so the full set of labels isn't trivially scrapeable
for LLM training. Other gold_queries fields (``exec_result``, ``id``, etc.)
are always preserved so the dataset remains useful for evaluation.

Rows are shuffled with a fixed seed before writing.

Usage:
    uv run scripts/arcs/flatten_for_hf.py --output data/ARCS/tasks.jsonl
"""

import argparse
import asyncio
import json
import random
from pathlib import Path

from tabulaflow.research.datahub.arcs import ARCSDatasetLoader


SHUFFLE_SEED = 42


def _original_qid(qid: str) -> str:
    """Strip the upsample suffix: '001-3' -> '001'."""
    return qid.rsplit("-", 1)[0]


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default="data/ARCS/", help="ARCS data directory")
    parser.add_argument("--output", default="data/ARCS/tasks.jsonl", help="Output JSONL path")
    parser.add_argument("--split", default="test", choices=["test", "test_unsampled"])
    parser.add_argument(
        "--gold-sql",
        choices=["sample", "all", "none"],
        default="sample",
        help="Which rows keep the gold SQL string. 'sample' (default): only the first "
        "--sample-per-db unique original qids per db. 'all': keep on every row. 'none': "
        "strip from every row. Other gold_queries fields (exec_result, id, ...) are always kept.",
    )
    parser.add_argument(
        "--sample-per-db",
        type=int,
        default=2,
        help="Number of unique original qids per db to keep gold SQL for (sample mode)",
    )
    args = parser.parse_args()

    loader = ARCSDatasetLoader(directory=args.directory)
    tasks = await loader.get_tasks_async(args.split)
    print(f"Loaded {len(tasks)} tasks from split '{args.split}'")

    sampled_qids: set[str] = set()
    if args.gold_sql == "sample":
        seen_per_db: dict[str, list[str]] = {}
        for task in tasks:
            oqid = _original_qid(task.qid)
            bucket = seen_per_db.setdefault(task.db, [])
            if oqid not in bucket and len(bucket) < args.sample_per_db:
                bucket.append(oqid)
        sampled_qids = {oqid for bucket in seen_per_db.values() for oqid in bucket}
        print(
            f"Keeping gold SQL for {len(sampled_qids)} original qids "
            f"({args.sample_per_db} per db across {len(seen_per_db)} dbs)"
        )

    rows: list[dict] = []
    kept_rows = 0
    for task in tasks:
        row = task.model_dump(mode="json")
        # Strip runtime-injected library config; consumers apply their own.
        row.pop("dataset_instructions", None)
        row.pop("extra_info", None)
        for gq in row.get("gold_queries", []):
            gq.pop("extra_info", None)

        keep_sql = args.gold_sql == "all" or (args.gold_sql == "sample" and _original_qid(task.qid) in sampled_qids)
        if keep_sql:
            kept_rows += 1
        else:
            for gq in row.get("gold_queries", []):
                gq["query"] = None

        rows.append(row)

    rng = random.Random(SHUFFLE_SEED)

    # Pin one row per db at the top: a randomly chosen upsample sibling of the
    # first-seen original qid in that db (e.g. "001-3" for retails). Gives the
    # HF preview one example per database upfront.
    first_qid_per_db: dict[str, str] = {}
    for task in tasks:
        first_qid_per_db.setdefault(task.db, _original_qid(task.qid))

    pinned_rows: list[dict] = []
    pinned_indices: set[int] = set()
    for db, oqid in first_qid_per_db.items():
        candidates = [(i, r) for i, r in enumerate(rows) if r["db"] == db and _original_qid(r["qid"]) == oqid]
        idx, row = rng.choice(candidates)
        pinned_rows.append(row)
        pinned_indices.add(idx)

    rest = [r for i, r in enumerate(rows) if i not in pinned_indices]
    rng.shuffle(rest)
    rows = pinned_rows + rest
    print(f"Pinned {len(pinned_rows)} intro rows: {[r['qid'] for r in pinned_rows]}")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")

    size_mb = output_path.stat().st_size / 1024 / 1024
    print(
        f"Wrote {len(rows)} shuffled rows (seed={SHUFFLE_SEED}) to {output_path} "
        f"({size_mb:.1f} MB); {kept_rows} rows retain gold SQL"
    )


if __name__ == "__main__":
    asyncio.run(main())
