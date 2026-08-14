from sqlglot import exp
import sqlglot
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import Scope, build_scope


def extract_all_source_columns(query: str, language: str = "sqlite") -> list[tuple[str, str]]:
    """
    Extracts ALL source columns used anywhere in the query (SELECT, WHERE, JOIN, ORDER BY, GROUP BY, etc.).

    Resolves table aliases and traces columns through CTEs and subqueries back to their
    original source tables.

    Args:
        query: SQL query string to analyze
        language: SQL dialect for parsing (e.g., "sqlite", "postgres", "mysql", "snowflake")

    Returns:
        List of (table_name, column_name) tuples for all source columns referenced
        in the query. Returns an empty list if the query cannot be parsed.

    Example:
        >>> query = '''
        ... WITH recent_orders AS (
        ...   SELECT o.user_id, o.total, o.order_dates
        ...   FROM orders o
        ... )
        ... SELECT u.id, ro.total
        ... FROM users u
        ... JOIN recent_orders ro ON u.id = ro.user_id
        ... '''
        >>> extract_all_source_columns(query)
        [('orders', 'user_id'), ('orders', 'total'), ('orders', 'order_dates'), ('users', 'id')]
    """
    try:
        parsed = sqlglot.parse_one(query, dialect=language)
        qualified = qualify(parsed, dialect=language, validate_qualify_columns=False)
        root = build_scope(qualified)
    except Exception:
        # Dialect-specific parsing can fail on valid SQL (e.g. Snowflake TRIM(BOTH '(' FROM ...)).
        # Fall back to permissive dialect-free parsing.
        try:
            parsed = sqlglot.parse_one(query)
            qualified = qualify(parsed, validate_qualify_columns=False)
            root = build_scope(qualified)
        except Exception:
            return []

    if root is None:
        return []

    def collect_columns(scope: Scope, result: list[tuple[str, str]], seen: set[tuple[str, str]]) -> None:
        """Recursively collect source columns from a scope and all nested scopes."""
        for col in scope.columns:
            table_alias = col.table
            col_name = col.name

            source = scope.sources.get(table_alias)
            if isinstance(source, exp.Table):
                table_name = source.name
                key = (table_name, col_name)
                if key not in seen:
                    result.append(key)
                    seen.add(key)

        # Process UNION scopes (each SELECT in a UNION/UNION ALL)
        for union_scope in scope.union_scopes:
            collect_columns(union_scope, result, seen)

        # Process CTE scopes (WITH clause definitions)
        for cte_scope in scope.cte_scopes:
            collect_columns(cte_scope, result, seen)

        # Process subquery scopes (subqueries in WHERE, HAVING, etc.)
        for subquery_scope in scope.subquery_scopes:
            collect_columns(subquery_scope, result, seen)

        # Process derived table scopes (subqueries in FROM/JOIN)
        for source in scope.sources.values():
            if isinstance(source, Scope):
                collect_columns(source, result, seen)

    result: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    collect_columns(root, result, seen)
    return result
