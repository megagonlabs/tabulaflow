from dataclasses import dataclass, field
from pydantic_ai import Tool
from pydantic import BaseModel
from typing import ClassVar
from mintq.schema import HSQLSchema
from mintq.formatters import HSchemaFormatter
from mintq.toolhub.utils import equals_ci


class ShowTableSectionToolMetrics(BaseModel):
    error_table_not_found: int = 0
    error_section_not_found: int = 0


@dataclass
class ShowTableSectionTool:
    name: ClassVar[str] = "show_table_section"
    hschema: HSQLSchema
    formatter: HSchemaFormatter
    metrics_: ShowTableSectionToolMetrics = field(default_factory=ShowTableSectionToolMetrics)

    async def __call__(self, schema_name: str | None, table_name: str, section_name: str) -> str:
        """
        List all columns in a table section.

        Args:
            schema_name: The name of the schema to which the table belongs, or None if schema is not applicable.
            table_name: The name of the table to which the section belongs.
            section_name: The name of the section to show.
        """
        # If there is only a single schema, use it regardless of what the agent specified
        all_schema_names = [tg.schema_name for tg in self.hschema.table_groups]
        if len(set(all_schema_names)) == 1:
            schema_name = all_schema_names[0]

        tg = None
        for tg in self.hschema.table_groups:
            if equals_ci(tg.schema_name, schema_name) and (
                equals_ci(tg.name, table_name) or any(equals_ci(t, table_name) for t in tg.table_names)
            ):
                break
        if tg is None:
            self.metrics_.error_table_not_found += 1
            return f"(table {table_name} in schema {schema_name} not found)"

        section = None
        for section in tg.sections:
            if equals_ci(section.name, section_name):
                break
        if section is None:
            self.metrics_.error_section_not_found += 1
            return f"(section {section_name} not found in table {table_name} in schema {schema_name})"

        return self.formatter.format_section(section)

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
