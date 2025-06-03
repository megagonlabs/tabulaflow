import pytest
from mintq.metadata_synthesizer.hschema import HTableSchemaSynthesizer
from mintq.db_connector import SQLAlchemyConnector


@pytest.mark.asyncio
async def test_htable_schema_synthesizer():
    sqlite_path = "data/BIRD-SQL/dev_20240627/dev_databases/european_football_2/european_football_2.sqlite"
    db_connector = await SQLAlchemyConnector.from_url_async("european_football_2", f"sqlite+aiosqlite:///{sqlite_path}")
    synthesizer = HTableSchemaSynthesizer(
        llm="gpt-4o-mini",
        batch_size=10,
        temperature=0.0,
    )

    for table in db_connector.schema.tables:
        sections = await synthesizer.build_sections(table)
        for section in sections:
            print()
            print(section)
