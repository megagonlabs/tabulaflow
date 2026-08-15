from dataclasses import dataclass

from tabulaflow.core import SQLDialect


_DIALECT_QUOTING: dict[str, tuple[str, bool]] = {
    "bigquery": ("`", False),
    "snowflake": ('"', True),
    "sqlite": ('"', False),
    "mysql": ("`", False),
    "athena": ('"', False),
    "clickhouse": ('"', False),
    "tsql": ('"', True),
}
_DEFAULT_QUOTING = ('"', True)


@dataclass(frozen=True)
class SQLQuoting:
    quote_char: str
    always_quote_columns: bool

    @classmethod
    def from_dialect(cls, dialect: SQLDialect | None) -> "SQLQuoting":
        return cls(*_DIALECT_QUOTING.get(dialect or "", _DEFAULT_QUOTING))

    def quote(self, value: str) -> str:
        return f"{self.quote_char}{value}{self.quote_char}"

    def quote_if_needed(self, value: str | None) -> str:
        if value is None:
            return "NULL"
        if " " in value or "-" in value or not value.isidentifier():
            return self.quote(value)
        return value

    def quote_column(self, name: str) -> str:
        return self.quote(name) if self.always_quote_columns else self.quote_if_needed(name)

    def qualified_table(self, table: str, schema: str | None) -> str:
        if schema is None:
            return self.quote_if_needed(table)
        return f"{self.quote_if_needed(schema)}.{self.quote_if_needed(table)}"
