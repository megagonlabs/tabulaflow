"""Static analysis of query text used by research agents and metrics."""

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.normalize_identifiers import normalize_identifiers
from sqlglot.optimizer.scope import Scope, build_scope

_SQLGLOT_DIALECT_BY_LANGUAGE = {"postgresql": "postgres"}


def sqlglot_dialect(language: str) -> str:
    """Return the SQLGlot dialect name for a query language."""
    return _SQLGLOT_DIALECT_BY_LANGUAGE.get(language, language)


def extract_all_source_columns(query: str, language: str = "sqlite") -> list[tuple[str, str]]:
    """Extract source columns referenced by a SQL query.

    Resolves aliases and traces columns through CTEs and subqueries. Returns an
    empty list when the query cannot be parsed.
    """
    dialect = sqlglot_dialect(language)
    try:
        parsed = normalize_identifiers(sqlglot.parse_one(query, dialect=dialect), dialect=dialect)
        root = build_scope(parsed)
    except Exception:
        try:
            root = build_scope(normalize_identifiers(sqlglot.parse_one(query)))
        except Exception:
            return []

    if root is None:
        return []

    result: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for scope in root.traverse():
        physical_sources = [source for source in scope.sources.values() if isinstance(source, exp.Table)]
        for column in scope.find_all(exp.Column):
            source: exp.Table | Scope | None = None
            if column.table:
                current: Scope | None = scope
                while current is not None:
                    source = current.sources.get(column.table)
                    if source is not None:
                        break
                    current = current.parent
            elif len(physical_sources) == 1:
                source = physical_sources[0]

            if isinstance(source, exp.Table):
                key = (source.name, column.name)
                if key not in seen:
                    result.append(key)
                    seen.add(key)
    return result
