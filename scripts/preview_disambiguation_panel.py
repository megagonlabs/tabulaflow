"""Preview the research-preview ambiguity panel in the TUI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from rich.style import Style
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from tabulaflow.app.display import build_query, build_table
from tabulaflow.app.theme import ACCENT, ACCENT_DIM, FOCUS_SURFACE, KEY_HINT, KEY_HINT_DIM


@dataclass(frozen=True)
class InterpretationChoice:
    id: str
    label: str
    description: str
    result_label: str


@dataclass(frozen=True)
class AmbiguityPoint:
    id: str
    span: str
    question: str
    choices: tuple[InterpretationChoice, ...]


@dataclass(frozen=True)
class ArtifactSpec:
    role: str
    label: str


AMBIGUITIES = (
    AmbiguityPoint(
        id="ranking",
        span="top customers",
        question="Ranking",
        choices=(
            InterpretationChoice(
                id="net_revenue",
                label="Highest net revenue",
                description="Revenue after discounts and returns",
                result_label="net revenue",
            ),
            InterpretationChoice(
                id="order_count",
                label="Most orders",
                description="Count of completed orders",
                result_label="order count",
            ),
            InterpretationChoice(
                id="gross_revenue",
                label="Highest gross revenue",
                description="Revenue before discounts and returns",
                result_label="gross revenue",
            ),
        ),
    ),
    AmbiguityPoint(
        id="period",
        span="last quarter",
        question="Time period",
        choices=(
            InterpretationChoice(
                id="completed_calendar_qtr",
                label="Last completed calendar quarter",
                description="Apr 1–Jun 30, 2026",
                result_label="last completed calendar quarter",
            ),
            InterpretationChoice(
                id="quarter_to_date",
                label="Current quarter to date",
                description="Jul 1–Jul 29, 2026",
                result_label="current quarter to date",
            ),
            InterpretationChoice(
                id="last_90_days",
                label="Last 90 days",
                description="Rolling window ending today",
                result_label="last 90 days",
            ),
        ),
    ),
)

ARTIFACTS = (
    ArtifactSpec(role="top_customers", label="Top customers"),
    ArtifactSpec(role="region_summary", label="Region summary"),
    ArtifactSpec(role="segment_breakdown", label="Segment breakdown"),
)

METRIC_COLUMNS = {
    "net_revenue": ("net_revenue_usd", [124_500, 98_200, 81_750, 77_300, 63_900]),
    "order_count": ("orders", [34, 29, 25, 22, 19]),
    "gross_revenue": ("gross_revenue_usd", [141_900, 112_400, 96_800, 88_100, 72_250]),
}

PERIOD_MULTIPLIER = {
    "completed_calendar_qtr": 1.0,
    "quarter_to_date": 0.38,
    "last_90_days": 0.92,
}

CUSTOMERS = ["Acme Corp", "Globex", "Initech", "Umbrella Group", "Stark Industries"]


class AmbiguityPanelPreview(Widget):
    DEFAULT_CSS = """
    AmbiguityPanelPreview {
        padding: 1 1;
        margin: 1 2 0 1;
        height: auto;
        background: $surface;
    }

    AmbiguityPanelPreview.-focused {
        background: $focus-surface;
    }

    AmbiguityPanelPreview .section-title {
        width: 1fr;
        height: auto;
        margin: 0 0 1 0;
    }

    AmbiguityPanelPreview .artifact-row {
        layout: horizontal;
        height: auto;
        margin: 1 0 1 0;
    }

    AmbiguityPanelPreview .artifact-bar {
        width: 1fr;
        height: auto;
        overflow-x: hidden;
        margin: 0 4 0 0;
    }

    AmbiguityPanelPreview .view-stepper {
        width: auto;
        height: auto;
    }

    """

    interpretation_cursor: reactive[int] = reactive(0, init=False)
    current_artifact: reactive[int] = reactive(0, init=False)
    result_view: reactive[int] = reactive(0, init=False)

    can_focus = True

    BINDINGS = [
        Binding("left", "prev_artifact", "Previous artifact", priority=True),
        Binding("right", "next_artifact", "Next artifact", priority=True),
        Binding("up", "cursor_move(-1)", "Previous interpretation", priority=True),
        Binding("down", "cursor_move(1)", "Next interpretation", priority=True),
        Binding("enter", "apply_interpretation", "Apply interpretation", priority=True),
        Binding("right_square_bracket", "next_view", "Next result view"),
        Binding("left_square_bracket", "prev_view", "Previous result view"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._selected = [0 for _ in AMBIGUITIES]
        self._section_title = Static(classes="section-title")
        self._view_stepper = Static(classes="view-stepper")
        self._ambiguity_content = Static(id="disambiguation-content")
        self._separator = Static()
        self._artifact_bar = Static(classes="artifact-bar")
        self._result_content = Static(id="disambiguation-result-content")
        self._mounted = False
        self._choice_hit_areas: list[tuple[int, int]] = []
        self._artifact_hit_areas: list[tuple[int, int, int]] = []

    def compose(self) -> ComposeResult:
        yield self._section_title
        yield self._ambiguity_content
        yield self._separator
        yield Horizontal(self._artifact_bar, self._view_stepper, classes="artifact-row")
        yield self._result_content

    def on_mount(self) -> None:
        self._mounted = True
        self.focus()
        self._refresh_all()

    def on_resize(self) -> None:
        self._refresh_all()

    def watch_interpretation_cursor(self) -> None:
        self._refresh_all()

    def watch_current_artifact(self) -> None:
        self._refresh_all()

    def watch_result_view(self) -> None:
        self._refresh_all()

    def watch_has_focus(self, has_focus: bool) -> None:
        self.set_class(has_focus, "-focused")
        self._refresh_all()

    @property
    def _focus_accent(self) -> str:
        return ACCENT if self.has_focus else ACCENT_DIM

    @property
    def _focus_key_hint(self) -> str:
        return KEY_HINT if self.has_focus else KEY_HINT_DIM

    def _refresh_all(self) -> None:
        if not self._mounted:
            return
        self._update_section_title()
        self._update_view_stepper()
        self._update_ambiguity_content()
        self._update_artifact_bar()
        self._update_result_content()

    def _update_section_title(self) -> None:
        hint = Text(no_wrap=True)
        hint.append("↑↓", style=self._focus_key_hint)
        hint.append(" Move · ", style="dim")
        hint.append("↵", style=self._focus_key_hint)
        hint.append(" Apply", style="dim")

        available = self._section_title.size.width or 0
        title = Text("Refine interpretation", style="bold dim")
        line = Text(no_wrap=True, overflow="crop")
        line.append_text(title)
        line.append(" " * max(1, available - title.cell_len - hint.cell_len))
        line.append_text(hint)
        self._section_title.update(line)

    def _update_view_stepper(self) -> None:
        views = ("Data", "Query")
        label = views[self.result_view]
        text = Text(no_wrap=True)
        text.append("[", style=self._focus_key_hint)
        text.append("/", style="dim")
        text.append("]", style=self._focus_key_hint)
        text.append(" Switch view · ", style="dim")
        text.append("◂ ", style=Style(bold=True, color=self._focus_accent))
        text.append(label, style=Style(bold=True, color=self._focus_accent))
        text.append(" ▸", style=Style(bold=True, color=self._focus_accent))
        self._view_stepper.update(text)

    def _update_ambiguity_content(self) -> None:
        body = self._build_ambiguity_body()
        self._ambiguity_content.update(body)
        self._separator.update(Text("─" * max(1, self._separator.size.width), style="dim"))

    def _update_artifact_bar(self) -> None:
        text = Text(no_wrap=True, overflow="crop")
        self._artifact_hit_areas = []
        col = text.cell_len

        for artifact_idx, artifact in enumerate(ARTIFACTS):
            if artifact_idx > 0:
                text.append(" ")
                col += 1
            pill = f" {artifact.label} "
            style = (
                Style(bold=True, color="black", bgcolor=self._focus_accent)
                if artifact_idx == self.current_artifact
                else Style(dim=True)
            )
            start = col
            text.append(pill, style=style)
            col += len(pill)
            self._artifact_hit_areas.append((artifact_idx, start, col))
        text.append("  ·  ", style="dim")
        text.append("←/→", style=self._focus_key_hint)
        text.append(" Switch artifact", style="dim")
        self._artifact_bar.update(text)

    def _update_result_content(self) -> None:
        result = self._build_result_renderable()
        self._result_content.update(result)

    def _build_ambiguity_body(self) -> Text:
        active_style = Style(bold=True)
        text = Text()
        self._choice_hit_areas = []
        cursor_ambiguity, cursor_choice = self._cursor_location()

        for amb_idx, ambiguity in enumerate(AMBIGUITIES):
            title = ambiguity.question
            title_style = active_style if amb_idx == cursor_ambiguity else Style(bold=True)
            text.append(title, style=title_style)
            text.append("\n")

            for choice_idx, choice in enumerate(ambiguity.choices):
                cursor = amb_idx == cursor_ambiguity and choice_idx == cursor_choice
                applied = self._selected[amb_idx] == choice_idx
                text.append("  ")
                text.append("❯ " if cursor else "  ", style=KEY_HINT if cursor and self.has_focus else KEY_HINT_DIM if cursor else "")
                text.append("● " if applied else "  ", style=self._focus_accent if applied else "")
                if applied:
                    label_style = Style(bold=True, color=self._focus_accent)
                elif cursor:
                    label_style = Style(bold=True)
                else:
                    label_style = Style()
                text.append(choice.label, style=label_style)
                if not (amb_idx == len(AMBIGUITIES) - 1 and choice_idx == len(ambiguity.choices) - 1):
                    text.append("\n")
                self._choice_hit_areas.append((amb_idx, choice_idx))
            if amb_idx < len(AMBIGUITIES) - 1:
                text.append("\n")

        return text

    def _build_result_renderable(self) -> object:
        if self.result_view == 0:
            table, _ = build_table(self._current_dataframe(), available_width=max(40, self.size.width - 4))
            return table
        return build_query(self._current_query(), lexer="sql")

    def _current_dataframe(self) -> pd.DataFrame:
        role = ARTIFACTS[self.current_artifact].role
        metric = AMBIGUITIES[0].choices[self._selected[0]].id
        period = AMBIGUITIES[1].choices[self._selected[1]].id
        metric_col, base_values = METRIC_COLUMNS[metric]
        multiplier = PERIOD_MULTIPLIER[period]
        values = [round(value * multiplier) for value in base_values]

        if role == "top_customers":
            orders = [18, 11, 9, 8, 7]
            if metric == "order_count":
                revenue = [round(v * PERIOD_MULTIPLIER[period]) for v in [92_400, 81_100, 69_200, 58_750, 51_400]]
                return pd.DataFrame({"customer": CUSTOMERS, metric_col: values, "net_revenue_usd": revenue})
            return pd.DataFrame({"customer": CUSTOMERS, metric_col: values, "orders": orders})

        if role == "region_summary":
            regions = ["North America", "Europe", "Asia Pacific", "Latin America"]
            bases = [313_000, 176_500, 121_250, 84_900]
            metric_values = [round(value * multiplier) for value in bases]
            if metric == "order_count":
                metric_values = [86, 51, 37, 24]
            return pd.DataFrame(
                {
                    "region": regions,
                    metric_col: metric_values,
                    "customers": [24, 17, 12, 9],
                    "avg_order_value_usd": [4_280, 3_910, 3_640, 3_215],
                }
            )

        segments = ["Enterprise", "Mid-market", "SMB"]
        bases = [392_800, 185_600, 117_250]
        metric_values = [round(value * multiplier) for value in bases]
        if metric == "order_count":
            metric_values = [74, 48, 29]
        total = sum(metric_values)
        return pd.DataFrame(
            {
                "segment": segments,
                metric_col: metric_values,
                "share_pct": [round(value * 100 / total, 1) for value in metric_values],
                "customers": [18, 26, 41],
            }
        )

    def _current_query(self) -> str:
        role = ARTIFACTS[self.current_artifact].role
        metric = AMBIGUITIES[0].choices[self._selected[0]].id
        period = AMBIGUITIES[1].choices[self._selected[1]].id
        metric_col, _ = METRIC_COLUMNS[metric]
        metric_expr = "COUNT(*)" if metric == "order_count" else f"SUM({metric_col})"
        period_filter = {
            "completed_calendar_qtr": "order_date >= DATE '2026-04-01' AND order_date < DATE '2026-07-01'",
            "quarter_to_date": "order_date >= DATE '2026-07-01' AND order_date <= DATE '2026-07-29'",
            "last_90_days": "order_date > DATE '2026-07-29' - INTERVAL 90 DAY AND order_date <= DATE '2026-07-29'",
        }[period]
        group_col = {
            "top_customers": "customer_name",
            "region_summary": "region",
            "segment_breakdown": "customer_segment",
        }[role]
        alias = {
            "top_customers": "customer",
            "region_summary": "region",
            "segment_breakdown": "segment",
        }[role]
        return f"""
SELECT
  {group_col} AS {alias},
  {metric_expr} AS {metric_col}
FROM orders
WHERE status = 'completed'
  AND {period_filter}
GROUP BY {group_col}
ORDER BY {metric_col} DESC
LIMIT 5
""".strip()

    def action_prev_artifact(self) -> None:
        self.current_artifact = (self.current_artifact - 1) % len(ARTIFACTS)

    def action_next_artifact(self) -> None:
        self.current_artifact = (self.current_artifact + 1) % len(ARTIFACTS)

    def action_cursor_move(self, delta: int) -> None:
        max_cursor = self._choice_count() - 1
        self.interpretation_cursor = max(0, min(max_cursor, self.interpretation_cursor + delta))

    def action_apply_interpretation(self) -> None:
        amb_idx, choice_idx = self._cursor_location()
        self._selected[amb_idx] = choice_idx
        self._refresh_all()

    def action_prev_view(self) -> None:
        self.result_view = (self.result_view - 1) % 2

    def action_next_view(self) -> None:
        self.result_view = (self.result_view + 1) % 2

    def on_click(self, event: events.Click) -> None:
        self.focus()
        if event.widget is self._ambiguity_content:
            for amb_idx, choice_idx in self._choice_hit_areas:
                row = self._choice_row(amb_idx, choice_idx)
                if event.y == row:
                    self.interpretation_cursor = self._choice_flat_index(amb_idx, choice_idx)
                    self._refresh_all()
                    event.stop()
                    return
        if event.widget is self._artifact_bar and event.y == 0:
            for artifact_idx, x0, x1 in self._artifact_hit_areas:
                if x0 <= event.x < x1:
                    self.current_artifact = artifact_idx
                    event.stop()
                    return

    def _choice_row(self, target_ambiguity: int, target_choice: int) -> int:
        row = 0
        for amb_idx, ambiguity in enumerate(AMBIGUITIES):
            row += 1
            for choice_idx, _choice in enumerate(ambiguity.choices):
                if amb_idx == target_ambiguity and choice_idx == target_choice:
                    return row
                row += 1
            if amb_idx < len(AMBIGUITIES) - 1:
                row += 1
        return -1

    def _choice_count(self) -> int:
        return sum(len(ambiguity.choices) for ambiguity in AMBIGUITIES)

    def _cursor_location(self) -> tuple[int, int]:
        cursor = self.interpretation_cursor
        for amb_idx, ambiguity in enumerate(AMBIGUITIES):
            if cursor < len(ambiguity.choices):
                return amb_idx, cursor
            cursor -= len(ambiguity.choices)
        last_ambiguity = len(AMBIGUITIES) - 1
        return last_ambiguity, len(AMBIGUITIES[last_ambiguity].choices) - 1

    def _choice_flat_index(self, target_ambiguity: int, target_choice: int) -> int:
        return sum(len(ambiguity.choices) for ambiguity in AMBIGUITIES[:target_ambiguity]) + target_choice


class DisambiguationPanelPreviewApp(App[None]):
    CSS_PATH = Path(__file__).resolve().parents[1] / "tabulaflow" / "app" / "tui.tcss"
    BINDINGS = [Binding("q", "quit", "Quit")]

    def get_css_variables(self) -> dict[str, str]:
        variables = super().get_css_variables()
        variables["focus-surface"] = FOCUS_SURFACE
        return variables

    def compose(self) -> ComposeResult:
        yield VerticalScroll(AmbiguityPanelPreview(), id="chat-log")


if __name__ == "__main__":
    DisambiguationPanelPreviewApp().run()
