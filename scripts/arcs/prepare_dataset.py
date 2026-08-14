import argparse
import os
import json
import random
import re
import shutil
import itertools
import time
import sqlparse
import asyncio
from pydantic import TypeAdapter
from tabulate import tabulate
import tabulaflow
from tabulaflow.research.types import GoldQuery
from tabulaflow.research.types import AmbigNL2QTask, GoldAmbiguityPointFinite, GoldAmbiguityPointInfinite
from tabulaflow.research.benchmarks import dataset_registry
from tabulaflow.data import SQLConnector
from tabulaflow.research.utils import sort_ambiguity_points

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


def parse_task(sql_path: str, db: str) -> AmbigNL2QTask:
    with open(sql_path, "r") as f:
        content = f.read()

    # Extract the first block of comment wrapped in /* */
    comments = re.search(r"/\*([\s\S]*?)\*/", content).group(1)
    data = json.loads(comments)

    # Extract the list of SQL queries from the .sql file
    sqls = [str(stmt).strip() for stmt in sqlparse.parse(content) if str(stmt).strip()]
    # Remove comments in SQL
    sqls = [clean_sql(sql) for sql in sqls]

    gold_ambiguity_points = []
    for ap_idx, ap in enumerate(data["ambiguity_points"]):
        if ap["type"] == "finite":
            gold_ambiguity_points.append(
                GoldAmbiguityPointFinite(
                    id=AMBIGUITY_POINT_IDS[ap_idx],
                    ambiguity_type=ap["ambiguity"].replace("_ambiguity", ""),
                    phrase=ap["phrase"],
                    type="finite",
                    interpretations=ap["interpretations"],
                    intended_interpretation_idx=random.choice(range(len(ap["interpretations"]))),
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
                parameter_dtype = "int"
            elif all(isinstance(val, float) for val in ap["parameter_sample_values"]):
                parameter_dtype = "float"
            elif all(isinstance(val, str) for val in ap["parameter_sample_values"]):
                parameter_dtype = "str"
            else:
                raise ValueError(f"Unknown parameter dtype: {ap['parameter_sample_values']}")

            if ap["parameter_operator"] in (">", ">="):
                parameter_sample_operators = [">", ">="]
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
    assert len(all_indexes) == len(sqls)

    # all_parameter_names = [ap.parameter_name for ap in gold_ambiguity_points if ap.type == "infinite"]
    all_parameter_values = {
        ap.parameter_name: ap.intended_parameter_value for ap in gold_ambiguity_points if ap.type == "infinite"
    }

    required_columns = data.get("required_columns")
    if required_columns is not None:
        assert len(required_columns) > 0
        if isinstance(required_columns[0], list):
            assert len(required_columns) == len(sqls)
            assert all(len(cols) > 0 for cols in required_columns)

    gold_queries = []
    for i, (indexes, sql) in enumerate(zip(all_indexes, sqls)):
        id = "GQRY" + "".join(f"-{ap.id}.{idx}" for ap, idx in zip(finite_aps, indexes))
        parameter_names = re.findall(r":([\w_]+)", sql)
        assert all(param_name in all_parameter_values for param_name in parameter_names)

        ambiguity_resolution = {
            f"[{ap.id}] {ap.phrase}": ap.interpretations[idx] for ap, idx in zip(finite_aps, indexes)
        }
        ambiguity_resolution.update(
            {f"[{ap.id}] {ap.phrase}": f":{ap.parameter_name}" for ap in gold_ambiguity_points if ap.type == "infinite"}
        )
        ambiguity_resolution = dict(sorted(ambiguity_resolution.items()))

        gold_queries.append(
            GoldQuery(
                id=id,
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

    gold_intended_query_idx = all_indexes.index(tuple(ap.intended_interpretation_idx for ap in finite_aps))
    gold_intended_query_id = gold_queries[gold_intended_query_idx].id

    filename = os.path.basename(sql_path)
    assert data["qid"] == filename.replace(".sql", ""), f"QID mismatch: {data['qid']} != {filename.replace('.sql', '')}"

    assert data["generated_task"][-1] in (".", "?"), "Generated task must end with '.' or '?'"

    task = AmbigNL2QTask(
        qid=data["qid"],
        language="SQLite",
        db=db,
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

    res = []
    for db in DB_ORDER:
        qid2task = {task.qid: task for task in tasks if task.db == db}
        for qid in PICKED_SAMPLES[db]:
            task = qid2task.pop(qid)
            task.qid = f"{len(res) + 1:03d}"  # 3-digit number padded with zeros
            res.append(task)
        # shuffle the remaining tasks
        remaining_tasks = list(qid2task.values())
        sampler.shuffle(remaining_tasks)
        for task in remaining_tasks:
            task.qid = f"{len(res) + 1:03d}"  # 3-digit number padded with zeros
            res.append(task)

    return res


TIMEOUT_SECONDS = 120


async def populate_gold_exec_results(task: AmbigNL2QTask, db_connector: SQLConnector) -> AmbigNL2QTask | None:
    has_error = False

    exec_results = await asyncio.gather(
        *[
            db_connector.run_query_async(gq.query, parameters=gq.parameter_values, timeout=TIMEOUT_SECONDS)
            for gq in task.gold_queries
        ],
        return_exceptions=True,
    )
    for gq, exec_result in zip(task.gold_queries, exec_results):
        if isinstance(exec_result, Exception):
            print(f"[ERROR] Error executing gold_query for QID {task.qid} (db: {task.db}): {exec_result}")
            has_error = True
    if not has_error and all(exec_result.df.empty for exec_result in exec_results):
        print(f"[ERROR] All gold_queries return empty result for QID {task.qid} (db: {task.db})")
        has_error = True
    if has_error:
        return None
    for gq, exec_result in zip(task.gold_queries, exec_results):
        gq.exec_result = exec_result
    print(f"{task.qid} done")
    return AmbigNL2QTask.model_validate(task.model_dump())


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="../ambig-text2sql/dataset_v1_filtered/")
    parser.add_argument("--output_dir", default="data/ARCS/tasks/")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch_size", type=int, default=10)
    parser.add_argument("--no_exec", action="store_true")
    parser.add_argument("--max_concurrency", type=int, default=1)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    print(args)
    print()

    tabulaflow.configure()

    # If output_dir exists and is not empty, exit
    if os.path.exists(args.output_dir) and os.listdir(args.output_dir):
        if not args.overwrite:
            print(f"{args.output_dir} already exists and is not empty")
            return
        else:
            shutil.rmtree(args.output_dir)
    os.makedirs(args.output_dir, exist_ok=True)

    random.seed(args.seed)

    t0 = time.time()
    if not args.no_exec:
        dataset_loader = dataset_registry.get_class("arcs")()
        db_connectors = await dataset_loader.get_db_connectors_async("dev")
        print(f"Loaded {len(db_connectors)} databases from ARCS dev set in {time.time() - t0:.2f} seconds.")
        dbms_semaphore = asyncio.Semaphore(args.max_concurrency)
        for db_connector in db_connectors.values():
            db_connector._t_eng.db_semaphore = asyncio.Semaphore(args.max_concurrency)
            db_connector._t_eng.dbms_semaphore = dbms_semaphore

    # task_061 = parse_task(os.path.join(args.input_dir, "financial", "sql", "1101.sql"), "financial")  # 1227
    # task_061 = await populate_gold_exec_results(task_061, dataset.db_connectors["financial"])
    # print(task_061.model_dump())
    # task_061.to_directory("output/tmp/061/")
    # task_061 = AmbigNL2QTask.from_directory("output/tmp/061/")
    # print(task_061.gold_queries[0].exec_result.df)
    # exit(9)

    all_data = []
    for db in os.listdir(args.input_dir):
        errors = {}
        input_sql_dir = os.path.join(args.input_dir, db, "sql")
        qids = [fname.replace(".sql", "") for fname in os.listdir(input_sql_dir) if fname.endswith(".sql")]
        for qid in qids:
            try:
                task = parse_task(os.path.join(input_sql_dir, f"{qid}.sql"), db)
                all_data.append(task)
            except Exception as e:
                import traceback

                print(traceback.format_exc())
                errors[qid] = str(e)
        print("-" * 100)
        print(f"Database: {db}")
        print(f"Error in {len(errors)} tasks:")
        for qid, error in errors.items():
            print(f"  {qid}: {error}")
        print()

    qids = [task.qid for task in all_data]
    assert len(qids) == len(set(qids)), "Duplicate QIDs found"
    print(f"Total number of tasks: {len(all_data)}")

    all_data = sort_tasks_and_reindex(all_data, args.seed)
    print(f"Total number of tasks after sorting and reindexing: {len(all_data)}")

    # all_data = all_data[1:4]

    # Print stats for ambiguity types
    domains = sorted(set([task.db for task in all_data]))
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
    db2counts = {db: {amb: 0 for amb in ambiguities} for db in domains}
    for task in all_data:
        db = task.db
        unique_ambs = list(set([ap.ambiguity_type for ap in task.gold_ambiguity_points]))
        for amb in unique_ambs:
            db2counts[db][amb] += 1
    df = []
    for amb in ambiguities:
        counts = [db2counts[db][amb] for db in domains]
        df.append((amb.replace("_ambiguity", ""), *counts, sum(counts)))
    df.append(("#Tasks", *[len([task for task in all_data if task.db == db]) for db in domains], len(all_data)))
    print()
    print(tabulate(df, headers=["Ambiguity"] + domains + ["Total"], tablefmt="github"))

    # Print stats for number of ambiguity points
    header = ["Number of AP"] + domains + ["Total"]
    max_ap = max([len(task.gold_ambiguity_points) for task in all_data])
    df = []
    for i in range(1, max_ap + 1):
        row = (
            [f"AP{i}"]
            + [
                sum([1 for task in all_data if len(task.gold_ambiguity_points) == i and task.db == db])
                for db in domains
            ]
            + [sum([1 for task in all_data if len(task.gold_ambiguity_points) == i])]
        )
        df.append(row)
    print()
    print(tabulate(df, headers=header, tablefmt="github"))

    if args.no_exec:
        output_path = os.path.join(args.output_dir, "all_data.json")
        with open(output_path, "w") as f:
            json.dump([task.model_dump() for task in all_data], f, indent=2)
        print(f"{len(all_data)} tasks saved to {output_path}")
        print("Checking only. Exiting...")
        return

    # qids = ["1159"]
    # all_data = [task for task in all_data if task.qid in qids]

    print("Executing the queries...")
    res = []
    for i in range(0, len(all_data), args.batch_size):
        batch = all_data[i : i + args.batch_size]
        tasks = await asyncio.gather(*[populate_gold_exec_results(task, db_connectors[task.db]) for task in batch])
        res += [task for task in tasks if task is not None]

    print("Please fix the errors and run the script again.")

    output_path = os.path.join(args.output_dir, "all_tasks.json")
    with open(output_path, "w") as f:
        f.write(TypeAdapter(list[AmbigNL2QTask]).dump_json(res, indent=2).decode())

    for task in res:
        task.to_directory(os.path.join(args.output_dir, "readable", task.qid))

    print(f"{len(res)} tasks saved to {output_path}")
    print(f"Finished in {time.time() - t0:.2f} seconds.")


if __name__ == "__main__":
    asyncio.run(main())
