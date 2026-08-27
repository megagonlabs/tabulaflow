"""Static analysis of query text used by research agents and metrics."""

import sqlglot
from sqlglot import exp
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import Scope, build_scope

_SQLGLOT_DIALECT_BY_LANGUAGE = {"postgresql": "postgres"}


def _sqlglot_dialect(language: str) -> str:
    return _SQLGLOT_DIALECT_BY_LANGUAGE.get(language, language)


def extract_all_source_columns(query: str, language: str = "sqlite") -> list[tuple[str, str]]:
    """Extract source columns referenced by a SQL query.

    Resolves aliases and traces columns through CTEs and subqueries. Returns an
    empty list when the query cannot be parsed.
    """
    dialect = _sqlglot_dialect(language)
    try:
        parsed = sqlglot.parse_one(query, dialect=dialect)
        qualified = qualify(parsed, dialect=dialect, validate_qualify_columns=False)
        root = build_scope(qualified)
    except Exception:
        try:
            parsed = sqlglot.parse_one(query)
            qualified = qualify(parsed, validate_qualify_columns=False)
            root = build_scope(qualified)
        except Exception:
            return []

    if root is None:
        return []

    def collect_columns(scope: Scope, result: list[tuple[str, str]], seen: set[tuple[str, str]]) -> None:
        for col in scope.columns:
            source = scope.sources.get(col.table)
            if isinstance(source, exp.Table):
                key = (source.name, col.name)
                if key not in seen:
                    result.append(key)
                    seen.add(key)

        for union_scope in scope.union_scopes:
            collect_columns(union_scope, result, seen)
        for cte_scope in scope.cte_scopes:
            collect_columns(cte_scope, result, seen)
        for subquery_scope in scope.subquery_scopes:
            collect_columns(subquery_scope, result, seen)
        for source in scope.sources.values():
            if isinstance(source, Scope):
                collect_columns(source, result, seen)

    result: list[tuple[str, str]] = []
    collect_columns(root, result, set())
    return result
