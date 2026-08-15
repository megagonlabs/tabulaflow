from tabulaflow.core import SQLSchema, SQLTableSchema


def select_tables_for_formatting(
    schema: SQLSchema,
    max_total_columns: int | None,
) -> list[tuple[SQLTableSchema, int]]:
    if max_total_columns is None or not schema.tables:
        return [(table, 0) for table in schema.tables]

    quota = max(1, max_total_columns // len(schema.tables))
    required_by_table: dict[tuple[str | None, str], set[str]] = {
        (table.schema_name, table.name): set(table.primary_key) for table in schema.tables
    }
    for table in schema.tables:
        required_by_table[(table.schema_name, table.name)].update(
            column_name for foreign_key in table.foreign_keys for column_name in foreign_key.columns
        )
        for foreign_key in table.foreign_keys:
            target = (foreign_key.foreign_schema_name, foreign_key.foreign_table)
            if target in required_by_table:
                required_by_table[target].update(foreign_key.foreign_columns)

    selected_tables = []
    for table in schema.tables:
        if len(table.columns) <= quota:
            selected_tables.append((table, 0))
            continue

        required = required_by_table[(table.schema_name, table.name)]
        ordinary = [column.name for column in table.columns if column.name not in required]
        selected_names = required | set(ordinary[: max(0, quota - len(required))])
        selected = table.select_columns(list(selected_names), include_primary_key=False)
        omitted_column_count = len(table.columns) - len(selected.columns)
        selected_tables.append((selected, omitted_column_count))

    return selected_tables
