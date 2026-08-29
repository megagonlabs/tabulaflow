"""Tests for the TUI tool-step label rendering (verb-led labels + diffstat)."""

from pathlib import Path

from tabulaflow.app.tui.theme import DIFF_ADDED, DIFF_REMOVED
from tabulaflow.app.tui.widgets.progress import (
    AgentProgressWidget,
    _line_diffstat,
    _styled_label,
    summarize_outcome,
    summarize_tool_args,
)
from tabulaflow.agents.chat.events import ToolCallOutcome


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

    def test_absolute_home_path_is_shortened(self) -> None:
        path = Path.home() / "projects" / "mintq" / "models" / "x.sql"
        label = summarize_tool_args(
            "file_editor",
            {"command": "str_replace", "path": str(path), "old_str": "a", "new_str": "a\nb"},
        )
        assert label == "Edit ~/projects/mintq/models/x.sql +1"

    def test_long_absolute_home_path_preserves_filename(self) -> None:
        path = Path.home() / ".tabulaflow" / "sessions" / "vtyp8l" / "scratch" / "result_patch.sql"
        label = summarize_tool_args(
            "file_editor",
            {"command": "str_replace", "path": str(path), "old_str": "a", "new_str": "a\nb"},
        )
        assert label == "Edit ~/.tabulaflow/sessions/vtyp8l/…/result_patch.sql +1"

    def test_str_replace_added_only_omits_zero_removed(self) -> None:
        label = summarize_tool_args(
            "file_editor",
            {"command": "str_replace", "path": "models/x.sql", "old_str": "a", "new_str": "a\nb"},
        )
        assert label == "Edit models/x.sql +1"

    def test_str_replace_removed_only_omits_zero_added(self) -> None:
        label = summarize_tool_args(
            "file_editor",
            {"command": "str_replace", "path": "models/x.sql", "old_str": "a\nb", "new_str": "a"},
        )
        assert label == "Edit models/x.sql -1"

    def test_str_replace_no_change_omits_diffstat(self) -> None:
        label = summarize_tool_args(
            "file_editor",
            {"command": "str_replace", "path": "models/x.sql", "old_str": "a", "new_str": "a"},
        )
        assert label == "Edit models/x.sql"

    def test_write_file_added_only(self) -> None:
        label = summarize_tool_args("file_editor", {"command": "write_file", "path": "s.py", "file_text": "l1\nl2\nl3"})
        assert label == "Write s.py +3"

    def test_write_file_empty_omits_zero_added(self) -> None:
        label = summarize_tool_args("file_editor", {"command": "write_file", "path": "s.py", "file_text": ""})
        assert label == "Write s.py"

    def test_view(self) -> None:
        assert summarize_tool_args("file_editor", {"command": "view", "path": "."}) == "View ."

    def test_view_range_includes_line_span(self) -> None:
        label = summarize_tool_args(
            "file_editor", {"command": "view", "path": "tabulaflow/app/widgets.py", "view_range": [541, 554]}
        )
        assert label == "View tabulaflow/app/widgets.py:541-554"

    def test_view_single_line_range_uses_single_line_number(self) -> None:
        label = summarize_tool_args("file_editor", {"command": "view", "path": "x.py", "view_range": [12, 12]})
        assert label == "View x.py:12"

    def test_view_invalid_range_omits_line_span(self) -> None:
        label = summarize_tool_args("file_editor", {"command": "view", "path": "x.py", "view_range": [12, -1]})
        assert label == "View x.py"


class TestApplyPatchLabel:
    def test_single_update_diffstat(self) -> None:
        label = summarize_tool_args(
            "apply_patch",
            {
                "patch": """*** Begin Patch
*** Update File: README.md
@@
-old
+new
*** End Patch"""
            },
        )
        assert label == "Edit README.md +1 -1"

    def test_add_file_diffstat(self) -> None:
        label = summarize_tool_args(
            "apply_patch",
            {
                "patch": """*** Begin Patch
*** Add File: new.txt
+one
+two
*** End Patch"""
            },
        )
        assert label == "Edit new.txt +2"

    def test_delete_file_label(self) -> None:
        label = summarize_tool_args(
            "apply_patch",
            {
                "patch": """*** Begin Patch
*** Delete File: old.txt
*** End Patch"""
            },
        )
        assert label == "Edit old.txt"

    def test_update_without_line_changes_omits_diffstat(self) -> None:
        label = summarize_tool_args(
            "apply_patch",
            {
                "patch": """*** Begin Patch
*** Update File: README.md
@@
 unchanged
*** End Patch"""
            },
        )
        assert label == "Edit README.md"

    def test_two_file_diffstats_are_aggregated(self) -> None:
        label = summarize_tool_args(
            "apply_patch",
            {
                "patch": """*** Begin Patch
*** Update File: README.md
@@
-old
+new
*** Update File: src/config.txt
@@
-mode=old
+mode=new
*** End Patch"""
            },
        )
        assert label == "Edit 2 files +2 -2"

    def test_three_or_more_files_aggregate(self) -> None:
        label = summarize_tool_args(
            "apply_patch",
            {
                "patch": """*** Begin Patch
*** Update File: a.txt
@@
-a
+A
*** Update File: b.txt
@@
-b
+B
*** Add File: c.txt
+C
*** End Patch"""
            },
        )
        assert label == "Edit 3 files +3 -2"

    def test_move_label(self) -> None:
        label = summarize_tool_args(
            "apply_patch",
            {
                "patch": """*** Begin Patch
*** Update File: old.txt
*** Move to: new.txt
@@
-old
+new
*** End Patch"""
            },
        )
        assert label == "Edit old.txt -> new.txt +1 -1"

    def test_absolute_home_paths_are_shortened(self) -> None:
        old_path = Path.home() / "project" / "old.txt"
        new_path = Path.home() / "project" / "new.txt"
        label = summarize_tool_args(
            "apply_patch",
            {
                "patch": f"""*** Begin Patch
*** Update File: {old_path}
*** Move to: {new_path}
@@
-old
+new
*** End Patch"""
            },
        )
        assert label == "Edit ~/project/old.txt -> ~/project/new.txt +1 -1"

    def test_long_absolute_home_path_preserves_filename(self) -> None:
        path = Path.home() / ".tabulaflow" / "sessions" / "vtyp8l" / "scratch" / "result_patch.sql"
        label = summarize_tool_args(
            "apply_patch",
            {
                "patch": f"""*** Begin Patch
*** Update File: {path}
@@
-old
+new
*** End Patch"""
            },
        )
        assert label == "Edit ~/.tabulaflow/sess…/result_patch.sql +1 -1"

    def test_long_filename_is_middle_truncated(self) -> None:
        path = (
            Path.home() / ".tabulaflow" / "sessions" / "vtyp8l" / "scratch" / "very_long_generated_query_filename.sql"
        )
        label = summarize_tool_args(
            "apply_patch",
            {
                "patch": f"""*** Begin Patch
*** Update File: {path}
@@
-old
+new
*** End Patch"""
            },
        )
        assert label == "Edit …/very_long_genera…uery_filename.sql +1 -1"

    def test_missing_patch_fallback(self) -> None:
        assert summarize_tool_args("apply_patch", {}) == "Edit"
        assert summarize_tool_args("apply_patch", {"patch": "not a patch"}) == "Edit"


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
        args = {"source_id": "S42", "target_alias": "dw", "target_table": "orders", "mode": "append"}
        assert summarize_tool_args("transfer_source_table", args) == "Transfer S42 to [dw] orders (append)"

    def test_browser_navigate(self) -> None:
        assert summarize_tool_args("browser_navigate", {"url": "stripe.com"}) == "Navigate stripe.com"

    def test_connect_data_source_shortens_local_path(self) -> None:
        path = Path.home() / "data" / "source.csv"
        assert summarize_tool_args("connect_data_source", {"source": str(path)}) == "Connect ~/data/source.csv"

    def test_connect_data_source_leaves_url_unchanged(self) -> None:
        url = "https://example.com/data.csv"
        assert summarize_tool_args("connect_data_source", {"source": url}) == f"Connect {url}"

    def test_execute_bash(self) -> None:
        assert summarize_tool_args("execute_bash", {"command": "pytest tests/"}) == "Run pytest tests/"

    def test_chart(self) -> None:
        spec = '{"mark": "bar", "title": "Revenue"}'
        assert summarize_tool_args("render_chart", {"vegalite_spec": spec}) == "Render Chart Revenue"

    def test_map(self) -> None:
        spec = {"title": "Store locations", "layers": [{"type": "points", "lat": "lat", "lng": "lng"}]}
        assert summarize_tool_args("render_map", {"map_spec": spec}) == "Render Map Store locations"

    def test_graph(self) -> None:
        spec = {"title": "Lineage", "edges": [{"source": "src", "target": "dst"}]}
        assert summarize_tool_args("render_graph", {"graph_spec": spec}) == "Render Graph Lineage"

    def test_unknown_tool_falls_back_to_titlecased_name(self) -> None:
        # single arg -> bare value; multiple -> key=value pairs (generic fallback)
        assert summarize_tool_args("some_new_tool", {"foo": "bar"}) == "Some new tool bar"
        assert summarize_tool_args("some_new_tool", {"a": "x", "b": "y"}) == "Some new tool a=x, b=y"


class TestStyledLabel:
    def test_diffstat_colored(self) -> None:
        text = _styled_label("file_editor", "Edit x.sql +2 -1")
        styled = {text.plain[s.start : s.end]: s.style for s in text.spans}
        assert styled["Edit"] == "bold dim"
        assert styled["+2"] == DIFF_ADDED  # added: green
        assert styled["-1"] == DIFF_REMOVED  # removed: red

    def test_apply_patch_diffstat_colored(self) -> None:
        text = _styled_label("apply_patch", "Edit x.sql +2 -1")
        styled = {text.plain[s.start : s.end]: s.style for s in text.spans}
        assert styled["Edit"] == "bold dim"
        assert styled["+2"] == DIFF_ADDED
        assert styled["-1"] == DIFF_REMOVED

    def test_diffstat_can_remain_uncolored(self) -> None:
        text = _styled_label("apply_patch", "Edit x.sql +2 -1", color_diffstat=False)
        assert text.plain == "Edit x.sql +2 -1"
        assert all(span.style in {"bold dim", "dim"} for span in text.spans)

    def test_failed_patch_diffstat_remains_uncolored(self) -> None:
        widget = AgentProgressWidget()
        widget._on_tool_start("call_1", "apply_patch", "Edit x.sql +2 -1")
        widget._on_tool_end("call_1", "apply_patch", "error")

        status, _tool_call_id, name, label = widget._steps[-1]
        text = _styled_label(name, label, color_diffstat=status == "done")

        assert status == "failed"
        assert text.plain == "Edit x.sql +2 -1 → error"
        assert all(span.style in {"bold dim", "dim"} for span in text.spans)

    def test_non_editor_label_bolds_verb_but_stays_dim(self) -> None:
        text = _styled_label("run_query", "SELECT a - 1, b + 2")
        styled = {text.plain[s.start : s.end]: s.style for s in text.spans}
        assert styled["SELECT"] == "bold dim"
        assert styled[" a - 1, b + 2"] == "dim"

    def test_path_dash_not_reddened(self) -> None:
        # a hyphen-number in a path must not be mistaken for a removed-line count
        text = _styled_label("file_editor", "View model-2.sql")
        styled = {text.plain[s.start : s.end]: s.style for s in text.spans}
        assert styled["View"] == "bold dim"
        assert styled[" model-2.sql"] == "dim"

    def test_error_outcome_not_colored(self) -> None:
        # tool failures aren't reddened — the "error" suffix stays dim like the label
        text = _styled_label("execute_bash", "Run pytest → error")
        styled = {text.plain[s.start : s.end]: s.style for s in text.spans}
        assert styled["Run"] == "bold dim"
        assert styled[" pytest → error"] == "dim"

    def test_single_word_label_bolds_verb_but_stays_dim(self) -> None:
        text = _styled_label("browser_back", "Back")
        styled = {text.plain[s.start : s.end]: s.style for s in text.spans}
        assert styled["Back"] == "bold dim"


class TestSummarizeOutcome:
    def test_plain_completion_has_no_suffix(self) -> None:
        # no "done" — completion is shown by the step's done-state, not a label
        assert summarize_outcome(None) == ""

    def test_rows_kept(self) -> None:
        assert summarize_outcome(ToolCallOutcome(count=42, unit="rows")) == "42 rows"

    def test_count_without_unit_kept(self) -> None:
        assert summarize_outcome(ToolCallOutcome(count=42)) == "42"

    def test_error_kept(self) -> None:
        assert summarize_outcome(ToolCallOutcome(error=True)) == "error"
