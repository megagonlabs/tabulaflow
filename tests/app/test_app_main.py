from __future__ import annotations

import os
import sys

import pytest

from tabulaflow.app.config import AppConfig, CredentialPreference, EndpointConnection, ResolvedLLMConfig
from tabulaflow.app.main import _app_agent_runtime_config, _resolve_startup_llm_config
from tabulaflow.app.tui import app as tui


@pytest.fixture(autouse=True)
def _isolate_saved_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("tabulaflow.app.credentials.load_saved_api_keys", lambda **_kwargs: {})


def test_app_disables_preprocessing_cache_regardless_of_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TABULAFLOW_PREPROCESSING_CACHE_MODE", "read_write")
    config = _app_agent_runtime_config()
    assert config.preprocessing_cache_mode == "off"
    assert config.max_llm_concurrency == 1200
    assert config.max_llm_requests_per_minute == 300


def test_resolve_startup_uses_app_config(monkeypatch: pytest.MonkeyPatch) -> None:
    import tabulaflow.app.config as app_config

    monkeypatch.setattr(app_config, "load_app_config", lambda: AppConfig(llm="off"))
    assert _resolve_startup_llm_config() == ResolvedLLMConfig("off", None)


def test_resolve_startup_without_credentials_is_off(monkeypatch: pytest.MonkeyPatch) -> None:
    import tabulaflow.app.config as app_config

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(app_config, "load_app_config", lambda: AppConfig())
    assert _resolve_startup_llm_config() == ResolvedLLMConfig(None, None)


class _FakeStdout:
    def __init__(self) -> None:
        self.value = ""
        self.flushed = False

    def isatty(self) -> bool:
        return True

    def write(self, value: str) -> int:
        self.value += value
        return len(value)

    def flush(self) -> None:
        self.flushed = True


class _FakeRunTuiApp:
    error: BaseException | None = None
    run_mouse: bool | None = None
    pane_close_args: list[bool] = []

    def __init__(self, **_kwargs: object) -> None:
        pass

    async def run_async(self, *, mouse: bool = True) -> None:
        type(self).run_mouse = mouse
        error = type(self).error
        if error is not None:
            raise error

    def _close_browser_pane(self, *, remove_artifacts: bool = False) -> None:
        type(self).pane_close_args.append(remove_artifacts)


@pytest.mark.parametrize("error", [None, RuntimeError("boom")], ids=["normal", "error"])
async def test_run_tui_restores_terminal_modes(
    error: RuntimeError | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stdout = _FakeStdout()
    _FakeRunTuiApp.error = error
    _FakeRunTuiApp.run_mouse = None
    _FakeRunTuiApp.pane_close_args = []
    monkeypatch.setattr(sys, "__stdout__", stdout)
    monkeypatch.setattr(tui, "TabulaflowApp", _FakeRunTuiApp)

    config = ResolvedLLMConfig("off", None)
    if error is None:
        await tui.run_tui(config)
    else:
        with pytest.raises(RuntimeError, match="boom"):
            await tui.run_tui(config)

    assert _FakeRunTuiApp.run_mouse is True
    assert _FakeRunTuiApp.pane_close_args == [True]
    assert stdout.value == tui._TERMINAL_MODE_RESTORE_SEQUENCE
    assert stdout.flushed is True


def test_startup_loads_saved_credentials_before_automatic_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    import tabulaflow.app.config as app_config

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(app_config, "load_app_config", lambda: AppConfig())

    def load_credentials(**_kwargs: object) -> dict[str, str]:
        monkeypatch.setenv("ANTHROPIC_API_KEY", "saved-key")
        return {}

    monkeypatch.setattr("tabulaflow.app.credentials.load_saved_api_keys", load_credentials)
    result = _resolve_startup_llm_config()
    assert result.automatic_env == "ANTHROPIC_API_KEY"


def test_startup_passes_saved_credential_preferences(monkeypatch: pytest.MonkeyPatch) -> None:
    import tabulaflow.app.config as app_config

    preference = CredentialPreference(source="saved", variable="OPENAI_API_KEY")
    monkeypatch.setattr(
        app_config,
        "load_app_config",
        lambda: AppConfig(credential_preferences={"openai": preference}),
    )
    received: list[dict[str, CredentialPreference]] = []

    def load_credentials(*, preferences: dict[str, CredentialPreference]) -> dict[str, str]:
        received.append(preferences)
        return {"OPENAI_API_KEY": "environment-key"}

    monkeypatch.setattr("tabulaflow.app.credentials.load_saved_api_keys", load_credentials)
    result = _resolve_startup_llm_config()
    assert received == [{"openai": preference}]
    assert result.credential_preferences == {"openai": preference}
    assert result.environment_variables == {"OPENAI_API_KEY": "environment-key"}


def test_startup_applies_saved_vllm_endpoint_and_preserves_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    import tabulaflow.app.config as app_config

    preference = CredentialPreference(source="saved", variable="VLLM_API_KEY")
    connection = EndpointConnection(base_url="http://saved:8000/v1", source="saved")
    monkeypatch.setattr(
        app_config,
        "load_app_config",
        lambda: AppConfig(
            credential_preferences={"vllm": preference}, endpoint_connections={"vllm": connection}
        ),
    )
    monkeypatch.setenv("VLLM_BASE_URL", "http://environment:8000/v1")
    monkeypatch.setenv("VLLM_API_KEY", "environment-key")

    def load_credentials(**_kwargs: object) -> dict[str, str]:
        monkeypatch.setenv("VLLM_API_KEY", "saved-key")
        return {"VLLM_API_KEY": "environment-key"}

    monkeypatch.setattr("tabulaflow.app.credentials.load_saved_api_keys", load_credentials)
    monkeypatch.setattr("tabulaflow.app.credentials.invalidate_model_cache", lambda: None)

    result = _resolve_startup_llm_config()

    assert os.environ["VLLM_BASE_URL"] == "http://saved:8000/v1"
    assert os.environ["VLLM_API_KEY"] == "saved-key"
    assert result.endpoint_connections == {"vllm": connection}
    assert result.environment_variables == {
        "VLLM_API_KEY": "environment-key",
        "VLLM_BASE_URL": "http://environment:8000/v1",
    }


def test_startup_saved_vllm_endpoint_does_not_reuse_environment_key(monkeypatch: pytest.MonkeyPatch) -> None:
    import tabulaflow.app.config as app_config

    connection = EndpointConnection(base_url="http://saved:8000/v1", source="saved")
    monkeypatch.setattr(
        app_config, "load_app_config", lambda: AppConfig(endpoint_connections={"vllm": connection})
    )
    monkeypatch.setenv("VLLM_BASE_URL", "http://environment:8000/v1")
    monkeypatch.setenv("VLLM_API_KEY", "environment-key")
    monkeypatch.setattr("tabulaflow.app.credentials.invalidate_model_cache", lambda: None)

    _resolve_startup_llm_config()

    assert os.environ["VLLM_BASE_URL"] == "http://saved:8000/v1"
    assert "VLLM_API_KEY" not in os.environ
