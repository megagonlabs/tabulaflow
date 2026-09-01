import argparse
import asyncio
import itertools
import json
import random
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Literal, cast

import sqlparse
from pydantic import TypeAdapter
from tabulate import tabulate

from tabulaflow.data import SQLConnector
from tabulaflow.research.ambiguity import sort_ambiguity_points
from tabulaflow.research.benchmarks.arcs import ARCSDatasetLoader
from tabulaflow.research.types import (
    AmbigNL2QTask,
    GoldAmbiguityPoint,
    GoldAmbiguityPointFinite,
    GoldAmbiguityPointInfinite,
    GoldQuery,
)

AMBIGUITY_POINT_IDS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def clean_sql(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL).strip()
    lines = sql.split("\n")
    res = []
    for line in lines:
        if "--" in line:
            line = line.split("--")[0]
        line = line.strip()
        if line:
            res.append(line)
    return "\n".join(res)


def parse_task(sql_path: Path, database: str, rng: random.Random) -> AmbigNL2QTask:
    content = sql_path.read_text()

    match = re.search(r"/\*([\s\S]*?)\*/", content)
    if match is None:
        raise ValueError(f"Missing metadata comment in {sql_path}")
    comments = match.group(1)
    data = json.loads(comments)

    sqls = [str(stmt).strip() for stmt in sqlparse.parse(content) if str(stmt).strip()]
    sqls = [clean_sql(sql) for sql in sqls]

    gold_ambiguity_points: list[GoldAmbiguityPoint] = []
    for ap_idx, ap in enumerate(data["ambiguity_points"]):
        if ap["type"] == "finite":
            gold_ambiguity_points.append(
                GoldAmbiguityPointFinite(
                    id=AMBIGUITY_POINT_IDS[ap_idx],
                    ambiguity_type=ap["ambiguity"].replace("_ambiguity", ""),
                    phrase=ap["phrase"],
                    type="finite",
                    interpretations=ap["interpretations"],
                    intended_interpretation_idx=rng.randrange(len(ap["interpretations"])),
                )
            )
        elif ap["type"] == "infinite":
            parameter_name = ap["parameter_name"]
            parameter_operator = ap["parameter_operator"]
            s = f"{parameter_operator} :{parameter_name}"
            allowed_sql_ids_no_parameter = ap.get("allowed_sql_ids_no_parameter", [])
            for i, sql in enumerate(sqls):
                if f":{parameter_name}" not in sql and i not in allowed_sql_ids_no_parameter:
                    raise ValueError(f"parameter {parameter_name} not found in SQL {i}")
                if s not in sql and i not in allowed_sql_ids_no_parameter and not ap.get("no_check", False):
                    raise ValueError(f"substring {s} not found in SQL {i}")

            if all(isinstance(val, int) for val in ap["parameter_sample_values"]):
                parameter_dtype: Literal["int", "float", "str"] = "int"
            elif all(isinstance(val, float) for val in ap["parameter_sample_values"]):
                parameter_dtype = "float"
            elif all(isinstance(val, str) for val in ap["parameter_sample_values"]):
                parameter_dtype = "str"
            else:
                raise ValueError(f"Unknown parameter dtype: {ap['parameter_sample_values']}")

            if ap["parameter_operator"] in (">", ">="):
                parameter_sample_operators: list[Literal["<", ">", "<=", ">=", "=", "<>"]] = [">", ">="]
            elif ap["parameter_operator"] in ("<", "<="):
                parameter_sample_operators = ["<", "<="]
            else:
                raise ValueError(f"Unknown parameter operator: {ap['parameter_operator']}")

            gold_ambiguity_points.append(
                GoldAmbiguityPointInfinite(
                    id=AMBIGUITY_POINT_IDS[ap_idx],
                    ambiguity_type=ap["ambiguity"].replace("_ambiguity", ""),
                    phrase=ap["phrase"],
                    type="infinite",
                    parameter_name=ap["parameter_name"],
                    parameter_dtype=parameter_dtype,
                    parameter_sample_operators=parameter_sample_operators,
                    parameter_sample_values=ap["parameter_sample_values"],
                    intended_parameter_operator=ap["parameter_operator"],
                    intended_parameter_value=ap["parameter_sample_values"][0],
                )
            )
        else:
            raise ValueError(f"Unknown ambiguity point type: {ap['type']}")

    finite_aps = [ap for ap in gold_ambiguity_points if ap.type == "finite"]
    all_indexes = list(itertools.product(*[range(len(ap.interpretations)) for ap in finite_aps]))
    if len(all_indexes) != len(sqls):
        raise ValueError(f"Expected {len(all_indexes)} SQL variants in {sql_path}, found {len(sqls)}")

    all_parameter_values = {
        ap.parameter_name: ap.intended_parameter_value for ap in gold_ambiguity_points if ap.type == "infinite"
    }

    required_columns = data.get("required_columns")
    if required_columns is not None:
        if not required_columns:
            raise ValueError(f"required_columns is empty in {sql_path}")
        if isinstance(required_columns[0], list):
            if len(required_columns) != len(sqls) or any(not columns for columns in required_columns):
                raise ValueError(f"Invalid per-query required_columns in {sql_path}")

    gold_queries = []
    for i, (indexes, sql) in enumerate(zip(all_indexes, sqls, strict=True)):
        query_id = "GQRY" + "".join(f"-{ap.id}.{idx}" for ap, idx in zip(finite_aps, indexes, strict=True))
        parameter_names = re.findall(r":([\w_]+)", sql)
        unknown_parameters = set(parameter_names) - all_parameter_values.keys()
        if unknown_parameters:
            raise ValueError(f"Unknown SQL parameters in {sql_path}: {sorted(unknown_parameters)}")

        ambiguity_resolution = {
            f"[{ap.id}] {ap.phrase}": ap.interpretations[idx] for ap, idx in zip(finite_aps, indexes, strict=True)
        }
        ambiguity_resolution.update(
            {f"[{ap.id}] {ap.phrase}": f":{ap.parameter_name}" for ap in gold_ambiguity_points if ap.type == "infinite"}
        )
        ambiguity_resolution = dict(sorted(ambiguity_resolution.items()))

        gold_queries.append(
            GoldQuery(
                id=query_id,
                query=sql,
                parameter_names=parameter_names,
                parameter_values={k: all_parameter_values[k] for k in parameter_names},
                required_columns=required_columns[i]
                if required_columns and isinstance(required_columns[0], list)
                else required_columns,
                required_sorted=False,
                extra_info={"ambiguity_resolution": ambiguity_resolution},
            )
        )

    intended_indexes = tuple(cast(int, ap.intended_interpretation_idx) for ap in finite_aps)
    gold_intended_query_idx = all_indexes.index(intended_indexes)
    gold_intended_query_id = gold_queries[gold_intended_query_idx].id

    if data["qid"] != sql_path.stem:
        raise ValueError(f"QID mismatch in {sql_path}: {data['qid']} != {sql_path.stem}")
    if not data["generated_task"].endswith((".", "?")):
        raise ValueError(f"Generated task must end with punctuation in {sql_path}")

    task = AmbigNL2QTask(
        qid=data["qid"],
        db=database,
        question=data["generated_task"],
        gold_ambiguity_points=gold_ambiguity_points,
        gold_queries=gold_queries,
        gold_intended_query_id=gold_intended_query_id,
        has_intended_resolution=True,
    )
    return sort_ambiguity_points(task)


DB_ORDER = ["retails", "professional_basketball", "github_repos", "financial", "codebase_community", "student_club"]

PICKED_SAMPLES = {
    "retails": ["0543", "0711", "0576", "0606", "0579"],
    "professional_basketball": ["0796", "0791"],
    "github_repos": ["0537", "0371", "0512"],
    "financial": ["1212", "1090", "1159"],
    "codebase_community": ["0169", "0047"],
    "student_club": ["0238", "0182", "0191"],
}

DB_NAME_MAPPING = {
    "github_repos_date": "github_repos",
}


def sort_tasks_and_reindex(tasks: list[AmbigNL2QTask], seed: int = 42) -> list[AmbigNL2QTask]:
    sampler = random.Random(seed)
    for task in tasks:
        if task.db in DB_NAME_MAPPING:
            task.db = DB_NAME_MAPPING[task.db]

    unknown_databases = {task.db for task in tasks} - set(DB_ORDER)
    if unknown_databases:
        raise ValueError(f"Unknown databases: {sorted(unknown_databases)}")

    res: list[AmbigNL2QTask] = []
    for db in DB_ORDER:
        qid2task = {task.qid: task for task in tasks if task.db == db}
        for qid in PICKED_SAMPLES[db]:
            task = qid2task.pop(qid)
            task.qid = f"{len(res) + 1:03d}"
            res.append(task)
        remaining_tasks = list(qid2task.values())
        sampler.shuffle(remaining_tasks)
        for task in remaining_tasks:
            task.qid = f"{len(res) + 1:03d}"
            res.append(task)

    return res


TIMEOUT_SECONDS = 120


async def populate_gold_exec_results(task: AmbigNL2QTask, db_connector: SQLConnector) -> AmbigNL2QTask | None:
    has_error = False
    if any(query.query is None for query in task.gold_queries):
        raise ValueError(f"Task {task.qid} contains a gold query without SQL")

    exec_results = await asyncio.gather(
        *[
            db_connector.run_query_async(
                cast(str, gq.query),
                parameters=gq.parameter_values,
                timeout=TIMEOUT_SECONDS,
            )
            for gq in task.gold_queries
        ],
        return_exceptions=True,
    )
    for gq, exec_result in zip(task.gold_queries, exec_results):
        if isinstance(exec_result, BaseException):
            print(f"[ERROR] Error executing gold_query for QID {task.qid} (db: {task.db}): {exec_result}")
            has_error = True
    successful_results = [result for result in exec_results if not isinstance(result, BaseException)]
    if not has_error and all(result.df is None or result.df.empty for result in successful_results):
        print(f"[ERROR] All gold_queries return empty result for QID {task.qid} (db: {task.db})")
        has_error = True
    if has_error:
        return None
    for gq, exec_result in zip(task.gold_queries, successful_results, strict=True):
        gq.exec_result = exec_result
    print(f"{task.qid} done")
    return AmbigNL2QTask.model_validate(task.model_dump())


def load_tasks(input_dir: Path, rng: random.Random) -> list[AmbigNL2QTask]:
    tasks = []
    for database_dir in sorted(path for path in input_dir.iterdir() if path.is_dir()):
        sql_dir = database_dir / "sql"
        if not sql_dir.is_dir():
            raise FileNotFoundError(f"SQL directory not found: {sql_dir}")
        for sql_path in sorted(sql_dir.glob("*.sql")):
            tasks.append(parse_task(sql_path, database_dir.name, rng))

    qids = [task.qid for task in tasks]
    if len(qids) != len(set(qids)):
        raise ValueError("Duplicate QIDs found")
    return tasks


def print_task_stats(tasks: list[AmbigNL2QTask]) -> None:
    domains = sorted({task.db for task in tasks})
    ambiguities = [
        "semantic_column",
        "semantic_table",
        "semantic_value",
        "semantic_computation",
        "syntactic_column",
        "syntactic_table",
        "syntactic_value",
        "syntactic_computation",
    ]
    counts = {database: {ambiguity: 0 for ambiguity in ambiguities} for database in domains}
    for task in tasks:
        for ambiguity in {point.ambiguity_type for point in task.gold_ambiguity_points}:
            counts[task.db][ambiguity] += 1

    rows = [
        (
            ambiguity,
            *(counts[database][ambiguity] for database in domains),
            sum(counts[db][ambiguity] for db in domains),
        )
        for ambiguity in ambiguities
    ]
    rows.append(("#Tasks", *(sum(task.db == database for task in tasks) for database in domains), len(tasks)))
    print(tabulate(rows, headers=["Ambiguity", *domains, "Total"], tablefmt="github"))

    max_points = max(len(task.gold_ambiguity_points) for task in tasks)
    point_rows = [
        [
            f"AP{count}",
            *(
                sum(len(task.gold_ambiguity_points) == count and task.db == database for task in tasks)
                for database in domains
            ),
            sum(len(task.gold_ambiguity_points) == count for task in tasks),
        ]
        for count in range(1, max_points + 1)
    ]
    print()
    print(tabulate(point_rows, headers=["Number of AP", *domains, "Total"], tablefmt="github"))


def validate_output_directory(output_dir: Path, overwrite: bool) -> None:
    if output_dir.exists() and not output_dir.is_dir():
        raise NotADirectoryError(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(f"Output directory is not empty: {output_dir}; pass --overwrite to replace it")


def staging_directory(output_dir: Path) -> Path:
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=f".{output_dir.name}-", dir=output_dir.parent))


def publish_directory(staging_dir: Path, output_dir: Path) -> None:
    if not output_dir.exists():
        staging_dir.replace(output_dir)
        return

    backup_dir = Path(tempfile.mkdtemp(prefix=f".{output_dir.name}-backup-", dir=output_dir.parent))
    backup_dir.rmdir()
    output_dir.replace(backup_dir)
    try:
        staging_dir.replace(output_dir)
    except BaseException:
        backup_dir.replace(output_dir)
        raise
    shutil.rmtree(backup_dir)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Build the ARCS benchmark dataset from annotated SQL files.")
    parser.add_argument("--input-dir", type=Path, default=Path("../ambig-text2sql/dataset_v1_filtered"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/ARCS/tasks"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--no-exec", action="store_true")
    parser.add_argument("--max-concurrency", type=int, default=1)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    if args.max_concurrency < 1:
        parser.error("--max-concurrency must be positive")
    validate_output_directory(args.output_dir, args.overwrite)

    started_at = time.perf_counter()
    tasks = sort_tasks_and_reindex(load_tasks(args.input_dir, random.Random(args.seed)), args.seed)
    print(f"Loaded and reindexed {len(tasks)} tasks")
    print_task_stats(tasks)

    if args.no_exec:
        staging_dir = staging_directory(args.output_dir)
        try:
            (staging_dir / "all_data.json").write_text(
                json.dumps([task.model_dump() for task in tasks], indent=2) + "\n"
            )
            publish_directory(staging_dir, args.output_dir)
        except BaseException:
            shutil.rmtree(staging_dir, ignore_errors=True)
            raise
        print(f"Wrote {len(tasks)} tasks to {args.output_dir / 'all_data.json'}")
        return

    dataset_loader = ARCSDatasetLoader(max_concurrency=args.max_concurrency)
    db_connectors = await dataset_loader.get_db_connectors_async("test_unsampled")

    print("Executing gold queries")
    completed: list[AmbigNL2QTask] = []
    for start in range(0, len(tasks), args.batch_size):
        batch = tasks[start : start + args.batch_size]
        results = await asyncio.gather(*(populate_gold_exec_results(task, db_connectors[task.db]) for task in batch))
        completed.extend(task for task in results if task is not None)
    if len(completed) != len(tasks):
        raise RuntimeError(f"Gold-query execution failed for {len(tasks) - len(completed)} tasks")

    staging_dir = staging_directory(args.output_dir)
    try:
        (staging_dir / "all_tasks.json").write_bytes(TypeAdapter(list[AmbigNL2QTask]).dump_json(completed, indent=2))
        for task in completed:
            task.to_directory(str(staging_dir / "readable" / task.qid))
        publish_directory(staging_dir, args.output_dir)
    except BaseException:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise

    print(f"Wrote {len(completed)} tasks to {args.output_dir / 'all_tasks.json'}")
    print(f"Finished in {time.perf_counter() - started_at:.2f} seconds")


if __name__ == "__main__":
    asyncio.run(main())
