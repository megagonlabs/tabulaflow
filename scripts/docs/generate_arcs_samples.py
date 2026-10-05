"""Generate the compact browser bundle for the ARCS documentation examples."""

import argparse
from html import escape
import json
from pathlib import Path
import re
from typing import Any

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import SqlLexer


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "scripts/docs/data/arcs-sample-tasks.json"
OUTPUT = ROOT / "docs/assets/arcs/sample-tasks.compact.json"
POINT_KEYS = {
    "id",
    "phrase",
    "type",
    "interpretations",
    "intended_interpretation_idx",
    "parameter_name",
    "parameter_dtype",
    "parameter_sample_operators",
    "parameter_sample_values",
    "intended_parameter_operator",
    "intended_parameter_value",
}


def highlighted_sql_template(sql: str, points: list[dict[str, Any]]) -> str:
    markers: list[tuple[str, str, str]] = []
    for point in points:
        if point["type"] != "infinite":
            continue
        name = point["parameter_name"]
        operator_marker = f"__ARCS_OPERATOR_{name}__"
        value_marker = f"__ARCS_VALUE_{name}__"
        pattern = re.compile(rf"([<>=!]+)\s*:{re.escape(name)}\b")
        sql, replacements = pattern.subn(f"{operator_marker} {value_marker}", sql)
        if replacements == 0:
            raise ValueError(f"Parameter {name!r} is missing from its SQL query")
        markers.append((name, operator_marker, value_marker))

    rendered = highlight(sql, SqlLexer(), HtmlFormatter(nowrap=True)).rstrip("\n")
    for name, operator_marker, value_marker in markers:
        attribute = escape(name, quote=True)
        rendered = rendered.replace(
            f'<span class="n">{operator_marker}</span>',
            f'<span class="o" data-arcs-operator="{attribute}"></span>',
        )
        rendered = rendered.replace(
            f'<span class="n">{value_marker}</span>',
            f'<span class="mi" data-arcs-value="{attribute}"></span>',
        )
    return re.sub(r'<span class="[nwp]">(.*?)</span>', r"\1", rendered)


def compact_result(query: dict[str, Any], *, keep_all_rows: bool) -> dict[str, Any]:
    execution = query.get("exec_result") or {}
    rows = (execution.get("df") or {}).get("data") or []
    return {
        "error": execution.get("error"),
        "rows": rows if keep_all_rows else rows[:10],
        "total_rows": len(rows),
        "truncated": bool(execution.get("df_is_truncated")),
    }


def generate_bundle() -> bytes:
    source = json.loads(SOURCE.read_text())
    tasks = []
    for task in source:
        points = [
            {key: value for key, value in point.items() if key in POINT_KEYS}
            for point in task["gold_ambiguity_points"]
        ]
        queries = [
            {
                "id": query["id"],
                "sql_html": highlighted_sql_template(query["query"], points),
                "result": compact_result(query, keep_all_rows=task["qid"] == "004"),
            }
            for query in task["gold_queries"]
        ]
        tasks.append(
            {
                "qid": task["qid"],
                "db": task["db"],
                "question": task["question"],
                "gold_ambiguity_points": points,
                "gold_queries": queries,
            }
        )
    return (json.dumps(tasks, ensure_ascii=False, separators=(",", ":")) + "\n").encode()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generated = generate_bundle()
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_bytes() != generated:
            raise SystemExit(f"{OUTPUT.relative_to(ROOT)} is out of date")
        return
    OUTPUT.write_bytes(generated)


if __name__ == "__main__":
    main()
