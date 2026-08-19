import asyncio
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    Integer,
    insert,
)
import os
from tabulaflow.data import SQLConnector, SQLConnectorConfig
from tabulaflow.research.agenthub.simple_zero_shot import SimpleZeroShotNL2Q, SimpleZeroShotNL2QConfig
from tabulaflow.research.types import GoldQuery
from tabulaflow.research.types import SimpleNL2QTask


def create_db(db_path: str) -> None:
    if os.path.exists(db_path):
        os.remove(db_path)
    engine = create_engine(f"sqlite:///{db_path}")
    metadata_obj = MetaData()

    # create city SQL table
    table_name = "city_stats"
    city_stats_table = Table(
        table_name,
        metadata_obj,
        Column("city_name", String(16), primary_key=True),
        Column("population", Integer),
        Column("country", String(16), nullable=False),
    )
    metadata_obj.create_all(engine)

    rows = [
        {"city_name": "Toronto", "population": 2930000, "country": "Canada"},
        {"city_name": "Tokyo", "population": 13960000, "country": "Japan"},
        {
            "city_name": "Chicago",
            "population": 2679000,
            "country": "United States",
        },
        {
            "city_name": "New York",
            "population": 8258000,
            "country": "United States",
        },
        {"city_name": "Seoul", "population": 9776000, "country": "South Korea"},
        {"city_name": "Busan", "population": 3334000, "country": "South Korea"},
    ]
    for row in rows:
        stmt = insert(city_stats_table).values(**row)
        with engine.begin() as connection:
            connection.execute(stmt)


async def main() -> None:
    db_path = "output/test.db"
    create_db(db_path)
    db_connector = await SQLConnector.from_url_async(
        f"sqlite:///{db_path}",
        global_id="test+city_stats",
        db_name="city_stats",
        config=SQLConnectorConfig(schema_cache_mode="off"),
    )
    model = await SimpleZeroShotNL2Q.from_config_async(
        SimpleZeroShotNL2QConfig(
            llm="openai/gpt-4.1-mini",
            schema_formatter="sql_basic",
        )
    )
    task = SimpleNL2QTask(
        qid="001",
        language="sqlite",
        db="city_stats",
        question="What is the population of Toronto?",
        gold_query=GoldQuery(query="SELECT population FROM city_stats WHERE city_name = 'Toronto';"),
    )
    output = await model.predict_async(task, db_connector)
    print(output.trajectory.to_readable())
    exec_result = await db_connector.run_query_async(output.pred_query.query)
    print(exec_result.to_readable())


if __name__ == "__main__":
    asyncio.run(main())
