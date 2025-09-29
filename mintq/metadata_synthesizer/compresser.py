import copy
import collections
from typing import Any
from mintq.schema import (
    SQLSchema,
    SQLTableSchema,
    ForeignKeySchema,
)


class SchemaCompressor:
    def _foreign_key_digest(self, fk: ForeignKeySchema, table: SQLTableSchema) -> Any:
        return (
            table.schema_name,
            table.name,
            tuple(sorted(fk.columns)),
            fk.foreign_schema_name,
            fk.foreign_table,
            tuple(sorted(fk.foreign_columns)),
        )

    def _table_digest(self, table: SQLTableSchema, full_schema: SQLSchema) -> Any:
        """
        The digest of a table includes:
        - the schema name
        - column names and data types
        - the primary key
        - the outgoing foreign keys
        - the incoming foreign keys
        """
        schema_name = table.schema_name
        columns = tuple(sorted([(c.name, c.dtype) for c in table.columns]))
        primary_key = tuple(sorted(table.primary_key))
        out_foreign_keys = tuple(sorted([self._foreign_key_digest(fk, table) for fk in table.foreign_keys]))
        in_foreign_keys = tuple(
            sorted(
                [
                    self._foreign_key_digest(fk, t)
                    for t in full_schema.tables
                    for fk in t.foreign_keys
                    if (fk.foreign_schema_name, fk.foreign_table) == (table.schema_name, table.name)
                ]
            )
        )
        return (schema_name, columns, primary_key, out_foreign_keys, in_foreign_keys)

    async def run_async(self, schema: SQLSchema) -> SQLSchema:
        schema = copy.deepcopy(schema)

        while True:
            digest2tables = collections.defaultdict(list)
            for table in schema.tables:
                digest2tables[self._table_digest(table, schema)].append(table)

            largest_group = max(digest2tables.values(), key=len)
            if len(largest_group) == 1:
                return schema

            group_name = "{" + ",".join([t.name for t in largest_group]) + "}"

            #TODO: update column stats
            new_table = largest_group[0]
            new_table.name = group_name
            new_table.original_names = [t.name for t in largest_group]

            name_mapping = {(t.schema_name, t.name): new_table.name for t in largest_group}

            new_tables = [new_table] + [t for t in schema.tables if (t.schema_name, t.name) not in name_mapping]

            for table in new_tables:
                for fk in table.foreign_keys:
                    if (fk.foreign_schema_name, fk.foreign_table) in name_mapping:
                        fk.foreign_table = name_mapping[(fk.foreign_schema_name, fk.foreign_table)]
            schema.tables = new_tables
