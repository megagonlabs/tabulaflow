from tabulaflow.app.tui.spinner import tool_arrow_spinner
from tabulaflow.app.tui.widgets.chat import SpinnerWidget
from tabulaflow.app.tui.widgets.progress import AgentProgressWidget


def test_tool_arrow_spinner_matches_preview_style() -> None:
    spinner = tool_arrow_spinner()

    assert spinner.name == "toolArrow"
    assert spinner.frames == ["·", "›", "→", "›"]
    assert spinner.interval == 180


def test_all_activity_spinners_use_tool_arrow_style() -> None:
    simple = SpinnerWidget()
    progress = AgentProgressWidget()
    progress._on_tool_start("call-1", "run_query", "Query customers")
    progress.render()

    assert simple._spinner.name == "toolArrow"
    assert progress._status_spinner.name == "toolArrow"
    assert progress._tool_spinners["call-1"].name == "toolArrow"
