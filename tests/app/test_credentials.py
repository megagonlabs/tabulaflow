from __future__ import annotations

import json
import os
import stat
from pathlib import Path

import pytest

from tabulaflow.app.config import CredentialPreference
from tabulaflow.app.credentials import (
    APIKeyStore,
    InvalidCredentialStoreError,
    activate_api_key,
    activate_vllm_connection,
    load_saved_api_keys,
)


def test_missing_store_is_empty(tmp_path: Path) -> None:
    assert APIKeyStore(tmp_path / "credentials.json").load() == {}


def test_store_round_trip_uses_owner_only_file_and_atomic_replace(tmp_path: Path) -> None:
    path = tmp_path / "credentials.json"
    store = APIKeyStore(path)
    store.save("OPENAI_API_KEY", "sk-first")
    store.save("ANTHROPIC_API_KEY", "sk-second")

    assert store.load() == {"OPENAI_API_KEY": "sk-first", "ANTHROPIC_API_KEY": "sk-second"}
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert not list(tmp_path.glob(".credentials.json.*"))


def test_invalid_store_error_does_not_expose_contents(tmp_path: Path) -> None:
    path = tmp_path / "credentials.json"
    path.write_text('{"OPENAI_API_KEY": "secret-value"}')
    store = APIKeyStore(path)
    store.save("ANTHROPIC_API_KEY", "saved")

    path.write_text('{"OPENAI_API_KEY": 123}')
    with pytest.raises(InvalidCredentialStoreError) as error:
        store.load()
    assert "secret-value" not in str(error.value)
    assert "credentials.json" in str(error.value)

    path.write_text("not json")
    with pytest.raises(InvalidCredentialStoreError):
        store.load()


def test_saved_keys_do_not_override_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = APIKeyStore(tmp_path / "credentials.json")
    store.save("OPENAI_API_KEY", "saved-openai")
    store.save("ANTHROPIC_API_KEY", "saved-anthropic")
    monkeypatch.setenv("OPENAI_API_KEY", "environment-openai")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    environment = load_saved_api_keys(store)

    assert os.environ["OPENAI_API_KEY"] == "environment-openai"
    assert os.environ["ANTHROPIC_API_KEY"] == "saved-anthropic"
    assert environment == {"OPENAI_API_KEY": "environment-openai", "ANTHROPIC_API_KEY": ""}


def test_preferred_saved_key_overrides_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    store = APIKeyStore(tmp_path / "credentials.json")
    store.save("OPENAI_API_KEY", "saved-openai")
    monkeypatch.setenv("OPENAI_API_KEY", "environment-openai")
    preferences = {"openai": CredentialPreference(source="saved", variable="OPENAI_API_KEY")}

    overridden = load_saved_api_keys(store, preferences=preferences)

    assert os.environ["OPENAI_API_KEY"] == "saved-openai"
    assert overridden == {"OPENAI_API_KEY": "environment-openai"}


def test_activate_pasted_key_persists_and_invalidates_models(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = APIKeyStore(tmp_path / "credentials.json")
    invalidated: list[bool] = []
    monkeypatch.setattr("tabulaflow.app.credentials.invalidate_model_cache", lambda: invalidated.append(True))

    activate_api_key("OPENAI_API_KEY", "  sk-pasted  ", persist=True, store=store)

    assert os.environ["OPENAI_API_KEY"] == "sk-pasted"
    assert store.get("OPENAI_API_KEY") == "sk-pasted"
    assert invalidated == [True]
    with pytest.raises(ValueError, match="cannot be empty"):
        activate_api_key("OPENAI_API_KEY", "  ", store=store)


def test_saved_store_contains_only_environment_names_and_keys(tmp_path: Path) -> None:
    path = tmp_path / "credentials.json"
    APIKeyStore(path).save("OPENAI_API_KEY", "sk-test")
    assert json.loads(path.read_text()) == {"OPENAI_API_KEY": "sk-test"}


def test_explicit_environment_key_is_not_replaced_by_saved_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = APIKeyStore(tmp_path / "credentials.json")
    store.save("VLLM_API_KEY", "saved-key")
    monkeypatch.setenv("VLLM_API_KEY", "environment-key")
    preferences = {"vllm": CredentialPreference(source="environment", variable="VLLM_API_KEY")}

    environment = load_saved_api_keys(store, preferences=preferences)

    assert os.environ["VLLM_API_KEY"] == "environment-key"
    assert environment == {"VLLM_API_KEY": "environment-key"}


def test_activate_vllm_connection_replaces_url_and_optional_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = APIKeyStore(tmp_path / "credentials.json")
    store.save("VLLM_API_KEY", "old-key")
    monkeypatch.setenv("VLLM_BASE_URL", "http://old:8000/v1")
    monkeypatch.setenv("VLLM_API_KEY", "old-key")
    monkeypatch.setattr("tabulaflow.app.credentials.invalidate_model_cache", lambda: None)

    activate_vllm_connection("http://new:8000/v1", "new-key", persist_key=True, store=store)

    assert os.environ["VLLM_BASE_URL"] == "http://new:8000/v1"
    assert os.environ["VLLM_API_KEY"] == "new-key"
    assert store.get("VLLM_API_KEY") == "new-key"

    activate_vllm_connection("http://local:8000/v1", "", persist_key=True, store=store)

    assert os.environ["VLLM_BASE_URL"] == "http://local:8000/v1"
    assert "VLLM_API_KEY" not in os.environ
    assert store.get("VLLM_API_KEY") is None
