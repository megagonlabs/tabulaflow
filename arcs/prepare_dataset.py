import argparse
from asyncio.tasks import all_tasks
import os
import json
import random
import re
from typing import cast
import itertools
import time
import sqlparse
import asyncio
from tqdm import tqdm
import pandas as pd
from tabulate import tabulate
from mintq.schema import AmbigNL2QTask, GoldAmbiguityPointFinite, GoldAmbiguityPointInfinite, GoldQuery
from mintq.datahub import get_dataset_loader

AMBIGUITY_POINT_IDS = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")


def parse_task(sql_path: str, db: str) -> AmbigNL2QTask:
    with open(sql_path, "r") as f:
        content = f.read()

    # Extract the first block of comment wrapped in /* */
    comments = re.search(r"/\*([\s\S]*?)\*/", content).group(1)
    data = json.loads(comments)

    # Extract the list of SQL queries from the .sql file
    sqls = [str(stmt).strip() for stmt in sqlparse.parse(content) if str(stmt).strip()]
    # Remove the surrounding comments
    sqls = [re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL).strip() for sql in sqls]

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
            gold_ambiguity_points.append(
                GoldAmbiguityPointInfinite(
                    id=AMBIGUITY_POINT_IDS[ap_idx],
                    ambiguity_type=ap["ambiguity"].replace("_ambiguity", ""),
                    phrase=ap["phrase"],
                    type="infinite",
                    parameter_name=ap["parameter_name"],
                    parameter_sample_values=ap["parameter_sample_values"],
                    indended_parameter_value=ap["parameter_sample_values"][0],
                    parameter_operator=ap["parameter_operator"],
                )
            )
        else:
            raise ValueError(f"Unknown ambiguity point type: {ap['type']}")

    finite_aps = [ap for ap in gold_ambiguity_points if ap.type == "finite"]
    all_indexes = list(
        itertools.product(*[range(len(ap.interpretations)) for ap in finite_aps])
    )
    assert len(all_indexes) == len(sqls)

    # all_parameter_names = [ap.parameter_name for ap in gold_ambiguity_points if ap.type == "infinite"]
    all_parameter_values = {ap.parameter_name: ap.indended_parameter_value for ap in gold_ambiguity_points if ap.type == "infinite"}

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

        gold_queries.append(
            GoldQuery(
                id=id,
                query=sql,
                parameter_names=parameter_names,
                parameter_values={k: all_parameter_values[k] for k in parameter_names},
                required_columns=required_columns[i] if required_columns and isinstance(required_columns[0], list) else required_columns,
                required_sorted=False
            )
        )


    gold_intended_query_idx = all_indexes.index(
        tuple(ap.intended_interpretation_idx for ap in finite_aps)
    )
    gold_intended_query_id = gold_queries[gold_intended_query_idx].id
    

    filename = os.path.basename(sql_path)
    assert data["qid"] == filename.replace(".sql", ""), f"QID mismatch: {data['qid']} != {filename.replace('.sql', '')}"

    assert data["generated_task"][-1] in (".", "?"), "Generated task must end with '.' or '?'"

    

    task = AmbigNL2QTask(
        qid=data["qid"],
        language="sqlite",
        db=db,
        question=data["generated_task"],
        gold_ambiguity_points=gold_ambiguity_points,
        gold_queries=gold_queries,
        gold_intended_gold_query_id=gold_intended_query_id,
        has_intended_resolution=True,
    )
    return task


async def populate_gold_exec_results(task: AmbigNL2QTask, db_connector):
    has_error = False

    params = {ap.parameter_name: ap.gold_parameter_value for ap in task.gold_ambiguity_points if ap.parameter_name}

    try:
        gold_final_exec_result = await db_connector.run_query_async(
            task.gold_final_query, parameters=params, return_df=True, timeout=10
        )
        gold_final_exec_result = gold_final_exec_result.to_dict(orient="records")
        if not gold_final_exec_result:
            print(f"[ERROR] gold_final_query returns empty result for QID {task.qid} (db: {task.db})")
            task.gold_final_exec_result = None
            has_error = True
        else:
            task.gold_final_exec_result = gold_final_exec_result
    except Exception as e:
        print(f"[ERROR] Error executing gold_final_query for QID {task.qid} (db: {task.db}): {e}")
        task.gold_final_exec_result = None
        has_error = True

    dfs = await asyncio.gather(
        *[
            db_connector.run_query_async(query, parameters=params, return_df=True, timeout=10)
            for query in task.gold_queries
        ],
        return_exceptions=True,
    )
    gold_exec_results = []
    for query, df in zip(task.gold_queries, dfs):
        if not isinstance(df, pd.DataFrame):
            print(f"[ERROR] Error executing gold_query for QID {task.qid} (db: {task.db}): {df}")
            gold_exec_results.append(None)
            has_error = True
        elif df.empty:
            print(f"[ERROR] gold_query {query} returns empty result for QID {task.qid} (db: {task.db})")
            gold_exec_results.append(None)
            has_error = True
        else:
            gold_exec_results.append(df.to_dict(orient="records"))
    task.gold_exec_results = gold_exec_results

    if has_error:
        return None
    return task


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir", default="../ambig-text2sql/dataset_v1_filtered/")
    parser.add_argument("--output_dir", default="data/ARCS/")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--batch_size", type=int, default=10)
    parser.add_argument("--check_only", action="store_true")
    args = parser.parse_args()

    random.seed(args.seed)

    t0 = time.time()
    if not args.check_only:
        dataset_loader = get_dataset_loader("ambig-text2sql")
        dataset = await dataset_loader.get_split_async("dev_0")
        print(
            f"Loaded {len(dataset.db_connectors)} databases from ambig-text2sql dev_0 set in {time.time() - t0:.2f} seconds."
        )

    # with open(os.path.join(args.input_dir, "annotated_qids.json"), "r") as f:
    #     annoated_qids = json.load(f)

    all_data = []

    for db in os.listdir(args.input_dir):
        errors = {}
        input_sql_dir = os.path.join(args.input_dir, db, "sql")
        output_sql_dir = os.path.join(args.output_dir, db, "sql")
        os.makedirs(output_sql_dir, exist_ok=True)
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

    if args.check_only:
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
        tasks = await asyncio.gather(
            *[populate_gold_exec_results(task, dataset.db_connectors[task.db]) for task in batch]
        )
        res += [task for task in tasks if task is not None]

    print("Please fix the errors and run the script again.")

    output_path = os.path.join(args.output_dir, "all_data.json")
    with open(output_path, "w") as f:
        json.dump([task.model_dump() for task in res], f, indent=2)

    print(f"{len(res)} tasks saved to {output_path}")
    print(f"Finished in {time.time() - t0:.2f} seconds.")


if __name__ == "__main__":
    asyncio.run(main())
