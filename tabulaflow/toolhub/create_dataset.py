"""Tool for creating a new empty writable dataset and registering it."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import ClassVar

from pydantic_ai import Tool

from tabulaflow.core.db_connector.db_registry import DBRegistry
from tabulaflow.core.db_connector.sql_conn import SQLConnector

_VALID_NAME = re.compile(r"[A-Za-z0-9_]+")


class CreateDatasetTool:
    """Create a new empty writable DuckDB dataset and register it as a queryable source."""

    name: ClassVar = "create_dataset"

    def __init__(self, registry: DBRegistry, dataset_dir: Path) -> None:
        self._registry = registry
        self._dataset_dir = dataset_dir

    async def __call__(self, name: str) -> str:
        """Create a new empty writable dataset that you build up with run_query (CREATE
        TABLE / INSERT) — for consolidating scattered files into one table or accumulating
        computed results. The dataset is a first-class source you can query and keep adding
        to across the conversation.

        Args:
            name: The dataset's name, used verbatim as its alias — letters, digits, and
                underscores only, and not already in use by another source.
        """
        if not _VALID_NAME.fullmatch(name):
            return f"(invalid name {name!r}: use only letters, digits, and underscores)"
        if self._registry.has(name):
            return f"(name {name!r} is already in use; choose a different one)"

        db_path = self._dataset_dir / f"{name}.duckdb"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        connector = await SQLConnector.from_url_async(
            global_id=f"cli+{name}",
            url=f"duckdb:///{os.path.abspath(db_path)}",
            db_name=name,
            read_only=False,
            # Mutable store: a cached schema would go stale as the agent adds tables/rows.
            enable_schema_caching=False,
            enable_query_caching=False,
        )
        self._registry.register(name, connector)
        return f"Created writable dataset '{name}' (DuckDB SQL). Populate and query it with run_query using db_alias='{name}'."

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
