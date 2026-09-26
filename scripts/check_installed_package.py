"""Smoke-test an installed TabulaFlow distribution."""

import asyncio
import sqlite3
import tempfile
from importlib import import_module
from importlib.resources import files
from pathlib import Path

import duckdb
import tabulaflow
from tabulaflow.app.sample_data import SAMPLE_TABLES, materialize_sample_db
from tabulaflow.data import SQLConnector, SQLConnectorConfig


async def check_duckdb_reflection() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "reflection.duckdb"
        with duckdb.connect(str(path)) as connection:
            connection.execute("CREATE TABLE items (id INTEGER PRIMARY KEY, tags VARCHAR[])")

        connector = await SQLConnector.from_url_async(
            f"duckdb:///{path}",
            config=SQLConnectorConfig(schema_cache_mode="off"),
        )
        try:
            assert [(table.schema_name, table.name) for table in connector.schema.tables] == [("main", "items")]
            assert [column.name for column in connector.schema.tables[0].columns] == ["id", "tags"]
            assert connector.schema.tables[0].primary_key == ["id"]
        finally:
            await connector.close_async()


def main() -> None:
    for module in (
        "PIL",
        "tabulaflow.agents",
        "tabulaflow.app.tui",
        "tabulaflow.data",
        "tabulaflow.output",
        "tabulaflow.research",
    ):
        import_module(module)

    assert tabulaflow.__version__

    database = materialize_sample_db()
    with sqlite3.connect(database) as connection:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert set(SAMPLE_TABLES) <= tables

    asyncio.run(check_duckdb_reflection())

    assets = files("tabulaflow.app.pane.assets")
    assert assets.joinpath("ui", "index.html").is_file()
    assert assets.joinpath("vendor", "cytoscape", "LICENSE-dagre.txt").is_file()


if __name__ == "__main__":
    main()
