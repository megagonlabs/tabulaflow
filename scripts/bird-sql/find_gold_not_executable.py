import asyncio
import os
from mintq.schema import NL2QRunResult
from mintq.db_connector import SQLConnector
from mintq.datahub import BirdSQLDatasetLoader


async def main() -> None:
    result_dir = "output/152_gpt-5-mini-minimal/"
    with open(os.path.join(result_dir, "result.json"), "r") as f:
        result = NL2QRunResult.model_validate_json(f.read())

    for task in result.tasks:
        if task.eval_metrics["gold_executable"] == 0.0:
            print()
            print(task.qid)
            print(task.db)

            print(f"===\n{task.gold_query.query}\n===")
            db_connector = await SQLConnector.from_url_async(
                f"bird-sql+{task.db}",
                task.db,
                "sync",
                f"sqlite:///{os.path.join('data', 'BIRD-SQL', 'dev_20240627', 'dev_databases', task.db, f'{task.db}.sqlite')}",
            )
            exec_result = await db_connector.run_query_async(task.gold_query.query)
            print(f"=== SYNC EXEC RESULT ===\n{exec_result.to_readable()}\n=== END OF SYNC EXEC RESULT ===\n")
            print(exec_result.latency_seconds)

            task.gold_query.query = BirdSQLDatasetLoader._fix_gold_query(task.gold_query.query)

            db_connector = await SQLConnector.from_url_async(
                f"bird-sql+{task.db}",
                task.db,
                "async",
                f"sqlite+aiosqlite:///{os.path.join('data', 'BIRD-SQL', 'dev_20240627', 'dev_databases', task.db, f'{task.db}.sqlite')}",
            )
            exec_result = await db_connector.run_query_async(task.gold_query.query)
            print(f"=== ASYNC EXEC RESULT ===\n{exec_result.to_readable()}\n=== END OF ASYNC EXEC RESULT ===\n")
            print(exec_result.latency_seconds)
            print()


if __name__ == "__main__":
    asyncio.run(main())
