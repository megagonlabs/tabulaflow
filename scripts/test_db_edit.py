import asyncio
from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    Integer,
    select,
    insert,
    inspect,
)
import os
from mintq.db_connector import SQLConnector
from mintq.modelhub import SimpleZeroShotNL2Q
from mintq.schema import SimpleNL2QTask
from mintq.formatters import SQLDefaultSchemaFormatter
from mintq.utils import format_trajectory


def create_db(db_path: str):
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
    return engine


async def main():
    os.environ["MINTQ_CACHE_ENABLED"] = "0"
    db_path = "output/test.db"
    db_connector = await SQLConnector.from_url_async(
        "test+city_stats",
        "city_stats",
        "sync",
        f"sqlite:///{db_path}",
    )
    model = SimpleZeroShotNL2Q(
        llm="openai/gpt-4.1-mini",
        schema_formatter=SQLDefaultSchemaFormatter(),
    )
    task = SimpleNL2QTask(
        qid="001",
        language="sqlite",
        db="city_stats",
        question="What is the population of Toronto?",
    )
    output = await model.predict_async(task, db_connector)
    print(format_trajectory(output.trajectory))  # or print(output.pred_query)
    result = await db_connector.run_query_async(output.pred_query)
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
