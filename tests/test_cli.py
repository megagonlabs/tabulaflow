import re

from pytest import MonkeyPatch
from rich.highlighter import NullHighlighter
from typer import rich_utils
from typer.testing import CliRunner

import tabulaflow.cli as cli
from tabulaflow.cli import app
from tabulaflow.app.main import AppLLMServiceTier, AppLogLevel
from tabulaflow.research.cli import console


def test_root_cli_exposes_chat_options_and_research_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "A data agent for databases, files, and the web." in result.stdout
    assert "--llm-service-tier" in result.stdout
    assert "--enable-schema-cache" in result.stdout
    assert "--log-level" in result.stdout
    assert "--install-completion" not in result.stdout
    assert "--show-completion" not in result.stdout
    assert "benchmark" in result.stdout


def test_root_cli_help_only_uses_mint(monkeypatch: MonkeyPatch) -> None:
    assert getattr(rich_utils, "STYLE_METAVAR") == ""
    assert getattr(rich_utils, "STYLE_TYPES") == ""
    monkeypatch.setattr(rich_utils, "COLOR_SYSTEM", "truecolor")
    monkeypatch.setattr(rich_utils, "FORCE_TERMINAL", True)

    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    color_codes = set(re.findall(r"\x1b\[[0-9;]*?(?:3[0-9]|9[0-9]|38)[0-9;]*m", result.stdout))
    assert color_codes == {"\x1b[1;38;2;62;180;137m"}
    assert "\x1b[1;38;2;62;180;137m-p" in result.stdout
    assert not re.search(r"\x1b\[[0-9;]*m(?:TEXT|INTEGER)", result.stdout)


def test_root_cli_starts_chat_by_default(monkeypatch: MonkeyPatch) -> None:
    received: dict[str, object] = {}

    def fake_run_chat(**kwargs: object) -> None:
        received.update(kwargs)

    monkeypatch.setattr(cli, "run_chat", fake_run_chat)

    result = CliRunner().invoke(
        app,
        [
            "--llm-preset",
            "off",
            "--llm-service-tier",
            "priority",
            "--enable-schema-cache",
            "--log-level",
            "debug",
            "--output-pane-port",
            "61211",
            "--output-pane-host",
            "0.0.0.0",
            "--output-pane-public-url",
            "https://example.test/output",
        ],
    )

    assert result.exit_code == 0
    assert received == {
        "llm_preset": "off",
        "llm_service_tier": AppLLMServiceTier.PRIORITY,
        "enable_schema_cache": True,
        "log_level": AppLogLevel.DEBUG,
        "output_pane_port": 61211,
        "output_pane_host": "0.0.0.0",
        "output_pane_public_url": "https://example.test/output",
    }


def test_benchmark_cli_only_uses_explicit_colors() -> None:
    assert isinstance(console.highlighter, NullHighlighter)


def test_benchmark_download_has_no_split_option() -> None:
    result = CliRunner().invoke(app, ["benchmark", "download", "--help"])

    assert result.exit_code == 0
    assert "--split" not in result.stdout


def test_benchmark_runtime_commands_support_split_selection() -> None:
    runner = CliRunner()

    start = runner.invoke(app, ["benchmark", "start", "--help"])
    stop = runner.invoke(app, ["benchmark", "stop", "--help"])

    assert start.exit_code == 0
    assert stop.exit_code == 0
    assert "--split" in start.stdout
    assert "--split" in stop.stdout
