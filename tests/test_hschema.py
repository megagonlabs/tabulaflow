import pytest
from mintq.metadata_synthesizer.hschema import HSchemaSynthesizer
from mintq.db_connector import SQLConnector


@pytest.mark.asyncio
async def test_hschema_synthesizer() -> None:
    sqlite_path = "data/BIRD-SQL/dev_20240627/dev_databases/european_football_2/european_football_2.sqlite"
    db_connector = await SQLConnector.from_url_async(
        "european_football_2", "async", f"sqlite+aiosqlite:///{sqlite_path}"
    )
    synthesizer = HSchemaSynthesizer(
        llm="gpt-4o",
        batch_size=10,
        temperature=0.0,
    )
    await synthesizer.run_async(db_connector)
