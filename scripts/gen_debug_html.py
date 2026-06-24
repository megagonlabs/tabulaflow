"""Regenerate debug HTML (table + chart gallery) for browser inspection.

    uv run scripts/gen_debug_html.py

Writes a sample table and the full chart gallery to ``/tmp/mintq/`` and prints
clickable ``file://`` URLs. The charts come from ``debug_chart_fixtures`` — the
same specs the TUI ``DEBUG=1`` gallery uses — so the browser output matches what
the app shows inline. Re-run after any change to ``dump.py``/``page.py`` and
refresh the open tabs.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from tabulaflow.app.debug import debug_chart_fixtures
from tabulaflow.app.render import render_chart_html, render_table_html
from tabulaflow.app.page import render_page

OUT = Path("/tmp/mintq")


def _sample_table() -> Path:
    """A small table covering text / number / bool / long-text columns."""
    df = pd.DataFrame(
        {
            "status": ["Active", "Closed", "Pending"],
            "schools": [1240, 318, 57],
            "ratio": [0.81, 0.12, 0.04],
            "is_open": [True, False, None],
            "note": ["short", "a much longer note that should truncate " * 4, "x"],
        }
    )
    path = OUT / "T_demo.html"
    render_table_html(df, path, title="Schools by status")
    return path


def _write_index(entries: list[tuple[Path, str]]) -> Path:
    """An index page linking to every render (relative hrefs, same-dir)."""
    items = "".join(f'<li><a href="{path.name}">{label}</a></li>' for path, label in entries)
    head = (
        "<style>.idx{list-style:none;padding:0;font-size:15px;line-height:2.1}"
        ".idx a{color:#3eb489;text-decoration:none}.idx a:hover{text-decoration:underline}"
        "h1{color:#e4e4e7;font-weight:600;font-size:20px}</style>"
    )
    path = OUT / "index.html"
    path.write_text(
        render_page(title="debug renders", body=f"<h1>debug renders</h1><ul class='idx'>{items}</ul>", head=head),
        encoding="utf-8",
    )
    return path


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    entries: list[tuple[Path, str]] = [(_sample_table(), "T_demo — table")]
    for _record_id, label, _query, df, spec in debug_chart_fixtures():
        path = OUT / f"V_{label}.html"
        title = spec.get("title")
        render_chart_html(df, spec, path, title=str(title) if title else label)
        entries.append((path, f"{label} — {title}" if title else label))
    index = _write_index(entries)
    print(f"index: {index}")
    for path, _label in entries:
        print(path)


if __name__ == "__main__":
    main()
