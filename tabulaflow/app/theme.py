"""Visual tokens shared by the terminal and browser surfaces."""

from __future__ import annotations

from pygments.style import Style as PygmentsStyle
from pygments.token import Token

ACCENT = "#5FAF87"  # mint

# Project repository — shown in the TUI banner and browser output pane.
GITHUB_SLUG = "megagonlabs/tabulaflow"
GITHUB_URL = f"https://github.com/{GITHUB_SLUG}"

CODE_TEXT = "#B4B8D2"
CODE_COMMENT = "#8A8A8A"
CODE_KEYWORD = "#57A5E2"
CODE_FUNCTION = "#78DCE8"
CODE_STRING = "#7EC193"
CODE_NUMBER = "#C792EA"
CODE_TYPE = "#FFC473"

SQL_QUERY_LEXER_ALIASES = frozenset(
    {
        "bigquery",
        "duckdb",
        "mariadb",
        "mssql",
        "mysql",
        "oracle",
        "plpgsql",
        "postgres",
        "postgresql",
        "psql",
        "redshift",
        "snowflake",
        "sql",
        "sql-server",
        "sqlite",
        "sqlite3",
        "t-sql",
        "tsql",
    }
)


def normalize_query_lexer(lexer: str | None) -> str:
    """Normalize query lexer names used by app rendering paths."""
    normalized = (lexer or "sql").strip().lower()
    if not normalized:
        return "sql"
    if normalized in SQL_QUERY_LEXER_ALIASES:
        return "sql"
    return normalized


class TabulaflowPygmentsStyle(PygmentsStyle):  # type: ignore[misc]
    """Shared Pygments syntax theme."""

    background_color = None
    styles = {
        Token.Text: CODE_TEXT,
        Token.Comment: CODE_COMMENT,
        Token.Error: CODE_TEXT,
        Token.Generic: CODE_TEXT,
        Token.Keyword: CODE_KEYWORD,
        Token.Keyword.Constant: CODE_STRING,
        Token.Keyword.Namespace: CODE_KEYWORD,
        Token.Literal.Number: CODE_NUMBER,
        Token.Literal.String: CODE_STRING,
        Token.Literal.String.Doc: f"italic {CODE_STRING}",
        Token.Literal.String.Double: CODE_STRING,
        Token.Name: CODE_TEXT,
        Token.Name.Builtin: CODE_TYPE,
        Token.Name.Builtin.Pseudo: CODE_TEXT,
        Token.Name.Class: CODE_TYPE,
        Token.Name.Decorator: CODE_KEYWORD,
        Token.Name.Exception: CODE_TEXT,
        Token.Name.Function: CODE_FUNCTION,
        Token.Name.Function.Magic: CODE_FUNCTION,
        Token.Name.Namespace: CODE_TEXT,
        Token.Name.Variable: CODE_TEXT,
        Token.Operator: CODE_TEXT,
        Token.Operator.Word: CODE_KEYWORD,
        Token.Punctuation: CODE_TEXT,
        Token.Literal.Scalar.Plain: CODE_TEXT,
        Token.Whitespace: "",
    }
