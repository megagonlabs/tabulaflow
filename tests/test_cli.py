import importlib
from pathlib import Path
from types import SimpleNamespace

import pydantic_ai
from pytest import MonkeyPatch
from rich.highlighter import NullHighlighter
from rich.text import Text
from typer import rich_utils
from typer.testing import CliRunner

import tabulaflow.cli as cli
from tabulaflow.cli import app
from tabulaflow.app.config import InvalidAppConfigError
from tabulaflow.app.main import AppLLMServiceTier, AppLogLevel
from tabulaflow.app.theme import ACCENT
from tabulaflow.research.benchmarks.installation import BenchmarkInstallationError
from tabulaflow.research.cli import console


def _plain(output: str) -> str:
    return Text.from_ansi(output).plain


def test_cli_disables_pydantic_ai_banner() -> None:
    assert not pydantic_ai.BANNER_ENABLED


def test_root_cli_exposes_chat_options_and_research_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])
    output = _plain(result.stdout)

    assert result.exit_code == 0
    assert "A data agent for databases, files, and the web." in output
    assert "--llm-service-tier" in output
    assert "--enable-schema-cache" in output
    assert "--log-level" in output
    assert "--install-completion" not in output
    assert "--show-completion" not in output
    assert "benchmark" in output
    assert "examples" in output


def test_examples_cli_lists_bundled_examples() -> None:
    result = CliRunner().invoke(app, ["examples", "list"])

    assert result.exit_code == 0
    assert result.stdout.splitlines() == [
        "ambiguity-aware-queries",
        "chat-sessions",
        "compare-research-agents",
        "custom-agents",
        "data-enrichment",
        "document-extraction",
        "quick-start",
        "research-quick-start",
        "structured-outputs",
        "table-linking-agent",
        "working-with-data",
    ]


def test_examples_cli_runs_selected_example(monkeypatch: MonkeyPatch) -> None:
    called = False

    async def main() -> None:
        nonlocal called
        called = True

    module = SimpleNamespace(main=main)
    monkeypatch.setattr(importlib, "import_module", lambda name: module)

    result = CliRunner().invoke(app, ["examples", "run", "quick-start"])

    assert result.exit_code == 0
    assert called


def test_examples_cli_reports_missing_benchmark_without_traceback(monkeypatch: MonkeyPatch) -> None:
    async def main() -> None:
        raise BenchmarkInstallationError(
            "bird-sql is not downloaded.\n\nRun:\n  tabulaflow benchmark download bird-sql"
        )

    monkeypatch.setattr(importlib, "import_module", lambda name: SimpleNamespace(main=main))

    result = CliRunner().invoke(app, ["examples", "run", "research-quick-start"])

    assert result.exit_code == 1
    assert "Setup required: bird-sql is not downloaded." in result.output
    assert "Run:\n  tabulaflow benchmark download bird-sql" in result.output
    assert "Traceback" not in result.output


def test_root_cli_help_only_uses_mint() -> None:
    assert getattr(rich_utils, "STYLE_METAVAR") == ""
    assert getattr(rich_utils, "STYLE_TYPES") == ""
    assert rich_utils.STYLE_OPTION == f"bold {ACCENT}"
    assert rich_utils.STYLE_SWITCH == f"bold {ACCENT}"
    assert rich_utils.STYLE_COMMANDS_TABLE_FIRST_COLUMN == f"bold {ACCENT}"


def test_root_cli_starts_chat_by_default(monkeypatch: MonkeyPatch) -> None:
    received: dict[str, object] = {}

    def fake_run_chat(**kwargs: object) -> None:
        received.update(kwargs)

    monkeypatch.setattr(cli, "run_chat", fake_run_chat)

    result = CliRunner().invoke(
        app,
        [
            "--llm-service-tier",
            "priority",
            "--enable-schema-cache",
            "--log-level",
            "debug",
            "--browser-pane-port",
            "61211",
            "--browser-pane-host",
            "0.0.0.0",
            "--browser-pane-public-url",
            "https://example.test/output",
        ],
    )

    assert result.exit_code == 0
    assert received == {
        "llm_service_tier": AppLLMServiceTier.PRIORITY,
        "enable_schema_cache": True,
        "log_level": AppLogLevel.DEBUG,
        "browser_pane_port": 61211,
        "browser_pane_host": "0.0.0.0",
        "browser_pane_public_url": "https://example.test/output",
    }


def test_root_cli_reports_invalid_app_config_without_a_traceback(monkeypatch: MonkeyPatch) -> None:
    message = (
        "Invalid app configuration: ~/.tabulaflow/app_config.json\n"
        "llm.main.reasoning: Extra inputs are not permitted. Fix or delete the file."
    )

    def fail_to_start(**_kwargs: object) -> None:
        raise InvalidAppConfigError(message)

    monkeypatch.setattr(cli, "run_chat", fail_to_start)

    result = CliRunner().invoke(app)

    assert result.exit_code == 1
    assert result.output == f"{message}\n"
    assert "Traceback" not in result.output
    assert "\x1b[" not in result.output


def test_benchmark_cli_only_uses_explicit_colors() -> None:
    assert isinstance(console.highlighter, NullHighlighter)


def test_benchmark_download_has_no_split_option() -> None:
    result = CliRunner().invoke(app, ["benchmark", "download", "--help"])

    assert result.exit_code == 0
    assert "--split" not in _plain(result.stdout)


def test_benchmark_runtime_commands_support_split_selection() -> None:
    runner = CliRunner()

    start = runner.invoke(app, ["benchmark", "start", "--help"])
    stop = runner.invoke(app, ["benchmark", "stop", "--help"])

    assert start.exit_code == 0
    assert stop.exit_code == 0
    assert "--split" in _plain(start.stdout)
    assert "--split" in _plain(stop.stdout)


def test_benchmark_start_requires_download(monkeypatch: MonkeyPatch) -> None:
    def require() -> None:
        raise BenchmarkInstallationError("example is not downloaded.\n\nRun:\n  tabulaflow benchmark download example")

    benchmark = SimpleNamespace(installation=SimpleNamespace(require=require))
    runtime = SimpleNamespace()
    monkeypatch.setattr("tabulaflow.research.cli._get_benchmark", lambda _name: benchmark)
    monkeypatch.setattr("tabulaflow.research.cli._get_runtime", lambda _name: runtime)

    result = CliRunner().invoke(app, ["benchmark", "start", "example"])

    assert result.exit_code == 1
    assert "tabulaflow benchmark download example" in _plain(result.output)


def test_benchmark_run_defaults_to_full_split(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    received: dict[str, object] = {}

    async def fake_run_benchmark_async(*args: object) -> None:
        received["args"] = args

    monkeypatch.setattr("tabulaflow.research.cli._run_benchmark_async", fake_run_benchmark_async)

    result = CliRunner().invoke(
        app,
        ["benchmark", "run", "bird-sql", "--output-dir", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert received["args"] == ("bird-sql", "dev", None, None, None, 5, "full_schema", None, None, tmp_path)


def test_benchmark_run_supports_task_database_and_metric_selection(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    received: dict[str, object] = {}

    async def fake_run_benchmark_async(*args: object) -> None:
        received["args"] = args

    monkeypatch.setattr("tabulaflow.research.cli._run_benchmark_async", fake_run_benchmark_async)

    result = CliRunner().invoke(
        app,
        [
            "benchmark",
            "run",
            "bird-sql",
            "--qid",
            "dev_001",
            "--qid",
            "dev_002",
            "--database",
            "concert_singer",
            "--metric",
            "bird_sql_ex",
            "--metric",
            "executable",
            "--output-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert received["args"] == (
        "bird-sql",
        "dev",
        None,
        ["dev_001", "dev_002"],
        ["concert_singer"],
        5,
        "full_schema",
        None,
        ["bird_sql_ex", "executable"],
        tmp_path,
    )


def test_benchmark_run_rejects_qids_with_sample_size() -> None:
    result = CliRunner().invoke(
        app,
        ["benchmark", "run", "bird-sql", "--qid", "dev_001", "--sample-size", "5"],
    )

    assert result.exit_code == 2
    assert "cannot be combined with --qid" in _plain(result.output)


def test_benchmark_run_rejects_unknown_split() -> None:
    result = CliRunner().invoke(app, ["benchmark", "run", "bird-sql", "--split", "unknown"])

    assert result.exit_code == 2
    assert "unknown split 'unknown'" in _plain(result.output)
