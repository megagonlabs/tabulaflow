"""Tool for connecting an existing data source (file, connector URL, or HuggingFace)."""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path
from typing import ClassVar

from pydantic_ai import Tool

from tabulaflow.data.registry import DataConnectorRegistry
from tabulaflow.data.config import DataSourceConnectorConfigs
from tabulaflow.data.catalog import (
    DEFAULT_DATA_SOURCE_DEFINITIONS,
    DataSourceDefinition,
    resolve_data_source_definition,
)
from tabulaflow.data.connect import connect_data_source, redact_url_password
from tabulaflow.output.formatting import format_connector_summary

_VALID_NAME = re.compile(r"[A-Za-z0-9_]+")


class ConnectDataSourceTool:
    """Connect an existing file, connector URL, or HuggingFace dataset as a read-only source."""

    name: ClassVar = "connect_data_source"

    def __init__(
        self,
        registry: DataConnectorRegistry,
        data_dir: Path,
        *,
        definitions: Sequence[DataSourceDefinition] = DEFAULT_DATA_SOURCE_DEFINITIONS,
        configs: DataSourceConnectorConfigs | None = None,
    ) -> None:
        self._registry = registry
        self._data_dir = data_dir
        self._definitions = tuple(definitions)
        self._configs = configs

    async def __call__(self, source: str, alias: str) -> str:
        """Connect an existing data source as a read-only queryable source, for data that
        already exists in finished form and should be queried as-is.

        Accepts one of:
        - Curated source — for example ``wikidata``.
        - Local data file — a path ending in .csv, .tsv, .json, .parquet, .xlsx, or .xls.
        - Local database file — a path ending in .sqlite, .sqlite3, .db, or .duckdb.
        - Connector URL — e.g. postgresql://, mysql://, bigquery://, snowflake://,
          neo4j+s://, bolt://, or sparql+https://. For Neo4j, preserve the exact
          deployment-provided scheme because it determines routing, TLS, and
          certificate verification.
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

        try:
            connector = await connect_data_source(
                source,
                display_name=alias,
                definitions=self._definitions,
                data_dir=self._data_dir,
                read_only=True,
                configs=self._configs,
            )
        except Exception as e:
            is_url = "://" in source
            safe_source = redact_url_password(source) if is_url else source
            raise RuntimeError(f"failed to connect {safe_source!r}: {type(e).__name__}: {e}") from e

        self._registry.register(alias, connector)
        summary = format_connector_summary(connector)
        definition = resolve_data_source_definition(source, self._definitions)
        if definition is not None:
            return (
                f"Connected '{alias}' ({summary}). Query it using the alias '{alias}'.\n\n"
                f"{definition.description.strip()}\n\nUse get_data_source_document for complete source documentation."
            )
        return f"Connected '{alias}' ({summary}). Query it using the alias '{alias}'."

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
