import pytest
from mintq.metadata_synthesizer.hschema import HSchemaSynthesizer
from mintq.db_connector import SQLAlchemyConnector


@pytest.mark.asyncio
async def test_hschema_synthesizer():
    sqlite_path = "data/BIRD-SQL/dev_20240627/dev_databases/european_football_2/european_football_2.sqlite"
    db_connector = await SQLAlchemyConnector.from_url_async("european_football_2", f"sqlite+aiosqlite:///{sqlite_path}")
    synthesizer = HSchemaSynthesizer(
        llm="gpt-4o",
        batch_size=10,
        temperature=0.0,
    )
    await synthesizer.run(db_connector)
