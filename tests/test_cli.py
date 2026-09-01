from typer.testing import CliRunner

from tabulaflow.cli import app


def test_root_cli_exposes_app_and_research_commands() -> None:
    result = CliRunner().invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "chat" in result.stdout
    assert "benchmark" in result.stdout


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
