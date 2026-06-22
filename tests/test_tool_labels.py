"""Tests for the TUI tool-step label rendering (file editor diffstat)."""

from tabulaflow.app.theme import DIFF_ADDED, DIFF_REMOVED
from tabulaflow.app.widgets import _line_diffstat, _styled_label, summarize_tool_args


class TestLineDiffstat:
    def test_pure_insert(self) -> None:
        assert _line_diffstat("a\n", "a\nb\nc\n") == (2, 0)

    def test_pure_delete(self) -> None:
        assert _line_diffstat("a\nb\nc\n", "a\n") == (0, 2)

    def test_replace(self) -> None:
        # "b" replaced by "B","c": +2 -1
        assert _line_diffstat("a\nb", "a\nB\nc") == (2, 1)

    def test_no_change(self) -> None:
        assert _line_diffstat("a\nb\n", "a\nb\n") == (0, 0)


class TestFileEditorLabel:
    def test_str_replace_diffstat(self) -> None:
        label = summarize_tool_args(
            "file_editor",
            {"command": "str_replace", "path": "models/x.sql", "old_str": "a\nb", "new_str": "a\nB\nc"},
        )
        assert label == "Edit models/x.sql +2 -1"

    def test_write_file_added_only(self) -> None:
        label = summarize_tool_args("file_editor", {"command": "write_file", "path": "s.py", "file_text": "l1\nl2\nl3"})
        assert label == "Write s.py +3"

    def test_view(self) -> None:
        assert summarize_tool_args("file_editor", {"command": "view", "path": "."}) == "View ."


class TestStyledLabel:
    def test_diffstat_colored(self) -> None:
        text = _styled_label("file_editor", "Edit x.sql +2 -1")
        styled = {text.plain[s.start : s.end]: s.style for s in text.spans}
        assert styled["+2"] == DIFF_ADDED  # added: green
        assert styled["-1"] == DIFF_REMOVED  # removed: red

    def test_non_editor_label_uniform_dim(self) -> None:
        text = _styled_label("run_query", "SELECT a - 1, b + 2")
        assert text.style == "dim"
        assert text.spans == []  # no per-token coloring

    def test_path_dash_not_reddened(self) -> None:
        # a hyphen-number in a path must not be mistaken for a removed-line count
        text = _styled_label("file_editor", "View model-2.sql")
        assert text.spans == []
