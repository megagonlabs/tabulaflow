"""Tool for creating a new writable dataset on the host's behalf."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import ClassVar

from pydantic_ai import Tool

# Host callback: given a requested name, create + register a writable dataset and
# return its actual alias (sanitized, suffixed on collision). Supplied by the app.
CreateDatasetFn = Callable[[str], Awaitable[str]]


class CreateDatasetTool:
    """Create a new empty writable dataset and register it as a queryable source."""

    name: ClassVar = "create_dataset"

    def __init__(self, create_dataset_fn: CreateDatasetFn) -> None:
        self._fn = create_dataset_fn

    async def _run(self, name: str) -> str:
        """Create a new empty writable dataset that you build up with run_query (CREATE
        TABLE / INSERT) — for consolidating scattered files into one table or accumulating
        computed results. The dataset is a first-class source: queryable by its alias and
        shown in the data explorer, and you can keep adding to it across the conversation.
        Returns the dataset's alias (may be suffixed if the name is taken).

        Args:
            name: A short descriptive name for the dataset (e.g. "experiment_results").
        """
        alias = await self._fn(name)
        return (
            f"Created writable dataset '{alias}'. Populate it with run_query using "
            f"db_alias='{alias}' (e.g. CREATE TABLE ... AS SELECT * FROM "
            f"read_csv_auto('output/**/*.csv', union_by_name=true), or INSERT INTO ...). "
            f"It is now visible in the data explorer."
        )

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self._run, name=self.name)
