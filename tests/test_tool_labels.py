"""Tests for the TUI tool-step label rendering (verb-led labels + diffstat)."""

from tabulaflow.app.theme import DIFF_ADDED, DIFF_REMOVED
from tabulaflow.app.widgets import _line_diffstat, _styled_label, summarize_outcome, summarize_tool_args
from tabulaflow.chat.events import Completed, Failed, RowsReturned


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


class TestVerbLedLabels:
    def test_query(self) -> None:
        assert summarize_tool_args("run_query", {"db_alias": "main", "query": "SELECT 1"}) == "Query [main] SELECT 1"

    def test_inspect_database(self) -> None:
        # the whole-db read has no target noun — the db tag carries it
        assert summarize_tool_args("get_db_document", {"db_alias": "main"}) == "Inspect [main]"

    def test_inspect_table_with_schema(self) -> None:
        args = {"db_alias": "main", "schema_name": "public", "table_name": "orders"}
        assert summarize_tool_args("get_table_schema", args) == "Inspect [main] public.orders"

    def test_subagent_bare_noun(self) -> None:
        args = {"db_alias": "main", "table_name": "customers"}
        assert summarize_tool_args("run_subagent_for_each_row", args) == "Subagent [main] customers"

    def test_transfer_uses_to_not_arrow(self) -> None:
        # "->" would collide with the result-metric arrow, so the target reads "to"
        args = {"record_id": "rec_42", "target_alias": "dw", "target_table": "orders", "mode": "append"}
        assert summarize_tool_args("transfer_record", args) == "Transfer rec_42 to [dw] orders (append)"

    def test_browser_navigate(self) -> None:
        assert summarize_tool_args("browser_navigate", {"url": "stripe.com"}) == "Navigate stripe.com"

    def test_execute_bash(self) -> None:
        assert summarize_tool_args("execute_bash", {"command": "pytest tests/"}) == "Run pytest tests/"

    def test_chart(self) -> None:
        spec = '{"mark": "bar", "title": "Revenue"}'
        assert summarize_tool_args("render_chart", {"vegalite_spec": spec}) == "Chart Revenue"

    def test_unknown_tool_falls_back_to_titlecased_name(self) -> None:
        # single arg -> bare value; multiple -> key=value pairs (generic fallback)
        assert summarize_tool_args("some_new_tool", {"foo": "bar"}) == "Some new tool bar"
        assert summarize_tool_args("some_new_tool", {"a": "x", "b": "y"}) == "Some new tool a=x, b=y"


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

    def test_error_outcome_reddened(self) -> None:
        text = _styled_label("execute_bash", "Run pytest → error")
        styled = {text.plain[s.start : s.end]: s.style for s in text.spans}
        assert styled["error"] == DIFF_REMOVED


class TestSummarizeOutcome:
    def test_plain_completion_has_no_suffix(self) -> None:
        # no "done" — completion is shown by the step's done-state, not a label
        assert summarize_outcome(Completed()) == ""

    def test_rows_kept(self) -> None:
        assert summarize_outcome(RowsReturned(count=42)) == "42 rows"

    def test_error_kept(self) -> None:
        assert summarize_outcome(Failed()) == "error"
