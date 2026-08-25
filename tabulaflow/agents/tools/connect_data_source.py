"""Tool for connecting an existing data source (file, database URL, or HuggingFace)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from pydantic_ai import Tool

from tabulaflow.data.registry import DBRegistry
from tabulaflow.data.url import connect_url
from tabulaflow.data.url import is_database_file_path

if TYPE_CHECKING:
    from tabulaflow.data.protocols import DBConnector

_VALID_NAME = re.compile(r"[A-Za-z0-9_]+")


class ConnectDataSourceTool:
    """Connect an existing file, database URL, or HuggingFace dataset as a read-only source."""

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
        - Database URL — e.g. postgresql://, mysql://, bigquery://, snowflake://, neo4j://.
          A source needing a password that isn't in the URL is deferred to the user.
        - HuggingFace dataset — a https://huggingface.co/datasets/<owner>/<name> URL. A
          dataset with multiple configs/subsets requires one, named as .../viewer/<subset>
          (optionally .../viewer/<subset>/<split>).

        Args:
            source: The source to connect, in one of the forms above.
            alias: The name to register the source under, used verbatim — letters, digits,
                and underscores only, and not already in use by another source.
        """
        return await self.execute(source, alias)

    async def execute(self, source: str, alias: str) -> str:
        """Connect and register one external data source."""
        from tabulaflow.data.loaders import is_hf_dataset_url, load_files, load_hf_dataset

        if not _VALID_NAME.fullmatch(alias):
            return f"(error: invalid alias {alias!r}: use only letters, digits, and underscores)"
        if self._registry.has(alias):
            return f"(error: alias {alias!r} is already in use; choose a different one)"

        is_hf = is_hf_dataset_url(source)
        is_url = not is_hf and "://" in source
        path = os.path.expanduser(source)

        if not is_hf and not is_url and not os.path.isfile(path):
            return f"(error: no such file: {source!r}; pass a local file path or a HuggingFace dataset URL)"
        try:
            if is_hf:
                connector: DBConnector = await load_hf_dataset(source, db_name=alias, read_only=True)
            elif is_url:
                connector = await connect_url(source, db_name=alias, read_only=True)
            elif is_database_file_path(path):
                connector = await connect_url(path, db_name=alias, read_only=True)
            else:
                connector = await load_files(
                    global_id=f"cli+{alias}",
                    file_paths=[path],
                    db_name=alias,
                    data_dir=str(self._data_dir),
                    read_only=True,
                )
        except Exception as e:
            hint = f" If it needs credentials, ask the user to connect it with /connect {source}" if is_url else ""
            return f"(error: failed to connect {source!r}: {type(e).__name__}: {e}.{hint})"

        self._registry.register(alias, connector)
        lang = connector.language
        label = lang if lang.lower() == "cypher" else f"{lang} SQL"
        n_tables = self._table_count(connector)
        suffix = f", {n_tables} table{'s' if n_tables != 1 else ''}" if n_tables else ""
        return f"Connected '{alias}' ({label}{suffix}). Query it using the alias '{alias}'."

    @staticmethod
    def _table_count(connector: DBConnector) -> int:
        try:
            return len(connector.schema.tables)  # type: ignore[union-attr]
        except Exception:
            return 0

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
