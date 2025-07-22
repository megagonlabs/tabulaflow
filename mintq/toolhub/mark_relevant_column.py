from dataclasses import dataclass, field
from pydantic_ai import Tool
from pydantic import BaseModel
import copy
from typing import ClassVar
from mintq.schema import HSQLSchema, HTableGroup, HTableSection, HColumnGroup
from mintq.toolhub.utils import equals_ci


class MarkRelevantColumnToolMetrics(BaseModel):
    error_table_not_found: int = 0
    error_column_not_found: int = 0


def locate_path(
    hschema: HSQLSchema, schema_name: str, table_name: str, column_name: str
) -> tuple[HTableGroup, HTableSection, HColumnGroup]:
    column_name = column_name.strip('"')

    table_group = None
    for tg in hschema.table_groups:
        if equals_ci(tg.schema_name, schema_name) and (
            equals_ci(tg.name, table_name) or any(equals_ci(t, table_name) for t in tg.table_names)
        ):
            table_group = tg
            break
    if table_group is None:
        raise ValueError(f"(table {table_name} in schema {schema_name} not found)")

    section = None
    column_group = None
    for sec in table_group.sections:
        for cg in sec.column_groups:
            if equals_ci(cg.name, column_name) or any(equals_ci(c, column_name) for c in cg.column_names):
                section = sec
                column_group = cg
                break
    if column_group is None:
        raise ValueError(f"(column {column_name} not found in table {table_name} in schema {schema_name})")

    return table_group, section, column_group


def create_path(
    hschema: HSQLSchema, table_group: HTableGroup, section: HTableSection, column_group: HColumnGroup
) -> list[HTableGroup | HTableSection | HColumnGroup]:
    if not any(
        tg.schema_name == table_group.schema_name and tg.name == table_group.name for tg in hschema.table_groups
    ):
        hschema.table_groups.append(
            HTableGroup(
                name=table_group.name,
                description=table_group.description,
                table_names=table_group.table_names,
                schema_name=table_group.schema_name,
                primary_key=table_group.primary_key,
                foreign_keys=table_group.foreign_keys,
                sections=[],
            )
        )

    trg_table_group = next(
        tg for tg in hschema.table_groups if tg.schema_name == table_group.schema_name and tg.name == table_group.name
    )

    if not any(sec.name == section.name for sec in trg_table_group.sections):
        trg_table_group.sections.append(
            HTableSection(
                name=section.name,
                description=section.description,
                column_groups=[],
            )
        )

    trg_section = next(sec for sec in trg_table_group.sections if sec.name == section.name)

    if not any(cg.name == column_group.name for cg in trg_section.column_groups):
        trg_column_group = copy.deepcopy(column_group)
        trg_section.column_groups.append(trg_column_group)

    return [trg_table_group, trg_section, trg_column_group]


@dataclass
class MarkRelevantColumnTool:
    name: ClassVar[str] = "mark_relevant_column"
    hschema: HSQLSchema
    relevant_hschema: HSQLSchema | None = None
    metrics_: MarkRelevantColumnToolMetrics = field(default_factory=MarkRelevantColumnToolMetrics)

    async def __call__(self, schema_name: str | None, table_name: str, column_name: str) -> str:
        """
        Mark a column as relevant to the query.

        Args:
            schema_name: The name of the schema to which the table belongs, or None if schema is not applicable.
            table_name: The name of the table to which the column belongs.
            column_name: The name of the column to mark as relevant.
        """
        # If there is only a single schema, use it regardless of what the agent specified
        all_schema_names = [tg.schema_name for tg in self.hschema.table_groups]
        if len(set(all_schema_names)) == 1:
            schema_name = all_schema_names[0]

        try:
            src_table_group, src_section, src_column_group = locate_path(
                self.hschema, schema_name, table_name, column_name
            )
        except ValueError as e:
            if "(column" in str(e):
                self.metrics_.error_column_not_found += 1
                return str(e)
            elif "(table" in str(e):
                self.metrics_.error_table_not_found += 1
                return str(e)
            else:
                raise e

        if self.relevant_hschema is None:
            self.relevant_hschema = HSQLSchema(name=self.hschema.name, table_groups=[])

        create_path(self.relevant_hschema, src_table_group, src_section, src_column_group)

        return "Relevant column marked."

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
