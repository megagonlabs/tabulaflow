"""Smoke-test an installed TabulaFlow distribution."""

import sqlite3
from importlib import import_module
from importlib.resources import files

import tabulaflow
from tabulaflow.app.sample_data import SAMPLE_TABLES, materialize_sample_db


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
        tables = {
            row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
    assert set(SAMPLE_TABLES) <= tables

    assets = files("tabulaflow.app.pane.assets")
    assert assets.joinpath("ui", "index.html").is_file()
    assert assets.joinpath("vendor", "cytoscape", "LICENSE-dagre.txt").is_file()


if __name__ == "__main__":
    main()
