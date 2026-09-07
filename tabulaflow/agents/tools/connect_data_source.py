"""Tool for connecting an existing data source (file, connector URL, or HuggingFace)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from pydantic_ai import Tool

from tabulaflow.data.registry import DataConnectorRegistry
from tabulaflow.data.url import connect_url
from tabulaflow.data.url import is_database_file_path
from tabulaflow.data.url import strip_url_credentials
from tabulaflow.output.formatting import format_connector_summary

if TYPE_CHECKING:
    from tabulaflow.data.protocols import DataConnector

_VALID_NAME = re.compile(r"[A-Za-z0-9_]+")


class ConnectDataSourceTool:
    """Connect an existing file, connector URL, or HuggingFace dataset as a read-only source."""

    name: ClassVar = "connect_data_source"

    def __init__(self, registry: DataConnectorRegistry, data_dir: Path) -> None:
        self._registry = registry
        self._data_dir = data_dir

    async def __call__(self, source: str, alias: str) -> str:
        """Connect an existing data source as a read-only queryable source, for data that
        already exists in finished form and should be queried as-is.

        Accepts one of:
        - Local data file — a path ending in .csv, .tsv, .json, .parquet, .xlsx, or .xls.
        - Local database file — a path ending in .sqlite, .sqlite3, .db, or .duckdb.
        - Connector URL — e.g. postgresql://, mysql://, bigquery://, snowflake://,
          neo4j://, or sparql+https://.
          A source needing a password that isn't in the URL is deferred to the user.
        - HuggingFace dataset — a https://huggingface.co/datasets/<owner>/<name> URL. A
          dataset with multiple configs/subsets requires one, named as .../viewer/<subset>
          (optionally .../viewer/<subset>/<split>).

        Args:
            source: The source to connect, in one of the forms above.
            alias: The name to register the source under, used verbatim — letters, digits,
                and underscores only, and not already in use by another source.
        """
        try:
            return await self.execute(source, alias)
        except (ValueError, OSError, RuntimeError) as exc:
            return f"(error: {exc})"

    async def execute(self, source: str, alias: str) -> str:
        """Connect and register one external data source."""
        if not _VALID_NAME.fullmatch(alias):
            raise ValueError(f"invalid alias {alias!r}: use only letters, digits, and underscores")
        if self._registry.has(alias):
            raise ValueError(f"alias {alias!r} is already in use; choose a different one")

        from tabulaflow.data.loaders import is_hf_dataset_url, load_files, load_hf_dataset

        is_hf = is_hf_dataset_url(source)
        is_url = not is_hf and "://" in source
        path = os.path.expanduser(source)

        if not is_hf and not is_url and not os.path.isfile(path):
            raise FileNotFoundError(f"no such file: {source!r}; pass a local file path or a HuggingFace dataset URL")
        try:
            if is_hf:
                connector: DataConnector = await load_hf_dataset(source, display_name=alias, read_only=True)
            elif is_url:
                connector = await connect_url(source, display_name=alias, read_only=True)
            elif is_database_file_path(path):
                connector = await connect_url(path, display_name=alias, read_only=True)
            else:
                connector = await load_files(
                    global_id=f"cli+{alias}",
                    file_paths=[path],
                    display_name=alias,
                    data_dir=str(self._data_dir),
                    read_only=True,
                )
        except Exception as e:
            safe_source = strip_url_credentials(source) if is_url else source
            hint = " If it needs credentials, ask the user to connect it with /connect." if is_url else ""
            raise RuntimeError(f"failed to connect {safe_source!r}: {type(e).__name__}: {e}.{hint}") from e

        self._registry.register(alias, connector)
        summary = format_connector_summary(connector)
        return f"Connected '{alias}' ({summary}). Query it using the alias '{alias}'."

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
