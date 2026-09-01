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
