"""Tool for connecting an existing data source (local file or HuggingFace) read-only."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from pydantic_ai import Tool

from tabulaflow.core.db_connector.db_registry import DBRegistry

if TYPE_CHECKING:
    from tabulaflow.core.db_connector.sql_conn import SQLConnector

_VALID_NAME = re.compile(r"[A-Za-z0-9_]+")
# Local database files connect directly (no credentials); extension -> SQLAlchemy scheme.
_DB_FILE_SCHEMES = {
    ".sqlite": "sqlite+aiosqlite",
    ".sqlite3": "sqlite+aiosqlite",
    ".db": "sqlite+aiosqlite",
    ".duckdb": "duckdb",
}


class ConnectDataSourceTool:
    """Connect an existing local file or HuggingFace dataset as a read-only source."""

    name: ClassVar = "connect_data_source"

    def __init__(self, registry: DBRegistry, data_dir: Path) -> None:
        self._registry = registry
        self._data_dir = data_dir

    async def __call__(self, source: str, alias: str) -> str:
        """Connect an existing data source as a read-only queryable source, for data that
        already exists in finished form and should be queried as-is.

        Accepts one of:
        - Local data file — a path ending in .csv, .tsv, .json, .parquet, .xlsx, or .xls.
        - Local database file — a path ending in .sqlite, .sqlite3, .db, or .duckdb.
        - HuggingFace dataset — a https://huggingface.co/datasets/<owner>/<name> URL.
          A dataset with multiple configs/subsets requires one, named in the URL as
          .../viewer/<subset> (optionally .../viewer/<subset>/<split>).

        Args:
            source: The source to connect, in one of the forms above.
            alias: The name to register the source under, used verbatim — letters, digits,
                and underscores only, and not already in use by another source.
        """
        from tabulaflow.datasources import is_hf_dataset_url, load_files, load_hf_dataset

        if not _VALID_NAME.fullmatch(alias):
            return f"(invalid alias {alias!r}: use only letters, digits, and underscores)"
        if self._registry.has(alias):
            return f"(alias {alias!r} is already in use; choose a different one)"

        is_hf = is_hf_dataset_url(source)
        path = os.path.expanduser(source)
        ext = os.path.splitext(path)[1].lower()
        if not is_hf and not os.path.isfile(path):
            return f"(no such file: {source!r}; pass a local file path or a HuggingFace dataset URL)"

        try:
            if is_hf:
                connector: SQLConnector = await load_hf_dataset(source, db_name=alias, read_only=True)
            elif ext in _DB_FILE_SCHEMES:
                from tabulaflow.core.db_connector.sql_conn import SQLConnector as _SQLConnector

                connector = await _SQLConnector.from_url_async(
                    global_id=f"cli+{alias}",
                    url=f"{_DB_FILE_SCHEMES[ext]}:///{os.path.abspath(path)}",
                    db_name=alias,
                    read_only=True,
                )
            else:
                connector = await load_files(
                    global_id=f"cli+{alias}",
                    file_paths=[path],
                    db_name=alias,
                    data_dir=str(self._data_dir),
                    read_only=True,
                )
        except Exception as e:
            return f"(failed to connect {source!r}: {type(e).__name__}: {e})"

        self._registry.register(alias, connector)
        label = f"{connector.language} SQL" if connector.language else "SQL"
        n_tables = self._table_count(connector)
        suffix = f", {n_tables} table{'s' if n_tables != 1 else ''}" if n_tables else ""
        return f"Connected '{alias}' ({label}{suffix}). Query it using the alias '{alias}'."

    @staticmethod
    def _table_count(connector: SQLConnector) -> int:
        try:
            return len(connector.schema.tables)
        except Exception:
            return 0

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
