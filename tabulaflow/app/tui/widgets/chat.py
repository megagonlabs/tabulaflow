"""Basic widgets in the terminal conversation stream."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.text import Text

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static

from tabulaflow.app.theme import ACCENT
from tabulaflow.app.tui.spinner import tool_arrow_spinner
from tabulaflow.app.tui.theme import MESSAGE_SURFACE

if TYPE_CHECKING:
    from rich.console import RenderableType


class BannerWidget(Widget):
    """Displays the welcome banner: the wordmark art above a text block.

    The two parts are separate widgets so the project information and welcome text
    render from a single ``Text`` and are therefore selectable, while the
    half-block art — which has no meaningful text to copy — is left as its own,
    non-selectable widget.
    """

    DEFAULT_CSS = """
    BannerWidget {
        height: auto;
        margin: 2 3;
    }
    BannerWidget > Static {
        height: auto;
    }
    """

    def compose(self) -> ComposeResult:
        from tabulaflow.app.tui.banner import build_banner_text

        yield Static(classes="banner-art")
        yield Static(build_banner_text())

    def on_mount(self) -> None:
        from tabulaflow.app.tui.banner import build_wordmark

        # Carve the wordmark's empty halves with the art widget's *own* effective
        # background so they read as transparent against the chat log, whatever
        # the theme resolves it to.
        art = self.query_one(".banner-art", Static)
        surface = art.background_colors[0].hex
        art.update(build_wordmark(surface))


class UserMessage(Static):
    """Displays a user input message."""

    DEFAULT_CSS = f"""
    UserMessage {{
        margin: 1 2 1 0;
        padding: 0 1;
        border-left: heavy {ACCENT};
        background: {MESSAGE_SURFACE};
    }}
    """

    def __init__(self, text: str) -> None:
        super().__init__(Text(text))


class SystemMessage(Static):
    """Displays system/command output.

    Coerces a plain ``str`` to a Rich ``Text`` so markup is always parsed by Rich,
    never by Textual's own (differently-resolving) markup — keeping colors consistent
    with the rest of the app, which builds Rich renderables throughout."""

    DEFAULT_CSS = """
    SystemMessage {
        padding: 0 1;
    }
    """

    def __init__(self, content: "RenderableType") -> None:
        super().__init__(Text.from_markup(content) if isinstance(content, str) else content)


class SpinnerWidget(Widget):
    """Simple animated spinner with a label."""

    DEFAULT_CSS = """
    SpinnerWidget {
        padding: 0 1;
        height: auto;
    }
    """

    def __init__(self, label: str = "Loading...") -> None:
        super().__init__()
        self._label = label
        self._spinner = tool_arrow_spinner(Text(label, style="dim"), style="dim")

    def update_label(self, label: str) -> None:
        self._label = label
        self._spinner.text = Text(label, style="dim")

    def on_mount(self) -> None:
        self.set_interval(1 / 12, self.refresh)

    def render(self) -> RenderableType:
        return self._spinner


# Keys handled by the prefix/grouping logic or too noisy to show in a step label.
_NOISE_ARG_KEYS = frozenset({"connector_alias", "refresh", "tab", "tool_call_id"})

# A git-style diffstat token (``+5`` / ``-2``) preceded by whitespace, so a path
# like ``model-2.sql`` is not mistaken for a removed-line count.
