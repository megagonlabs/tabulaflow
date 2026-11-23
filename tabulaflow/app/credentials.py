"""Local API-key persistence for the interactive application."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from tabulaflow._paths import DEFAULT_HOME_DIR
from tabulaflow.agents.runtime import invalidate_model_cache

CREDENTIALS_PATH = DEFAULT_HOME_DIR / "credentials.json"


def mask_api_key(key: str | None) -> str | None:
    """Return a masked API key suitable for display."""
    if key is None or len(key) < 12:
        return None
    return f"{key[:3]}***{key[-4:]}"


class InvalidCredentialStoreError(ValueError):
    """The credential store could not be parsed or validated."""


class APIKeyStore:
    """Persist API keys by the environment variable consumed by their provider."""

    def __init__(self, path: Path = CREDENTIALS_PATH) -> None:
        self.path = path

    def load(self) -> dict[str, str]:
        """Load saved keys without modifying process credentials."""
        try:
            with self.path.open() as file:
                values = json.load(file)
        except FileNotFoundError:
            return {}
        except (OSError, json.JSONDecodeError) as error:
            raise InvalidCredentialStoreError(self._invalid_message()) from error
        if not isinstance(values, dict) or not all(
            isinstance(name, str) and name and isinstance(key, str) and key.strip() for name, key in values.items()
        ):
            raise InvalidCredentialStoreError(self._invalid_message())
        return values

    def get(self, name: str) -> str | None:
        """Return one saved key, if present."""
        return self.load().get(name)

    def save(self, name: str, key: str) -> None:
        """Atomically save a key in an owner-only file."""
        values = self.load()
        values[name] = key
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        temporary_path = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w") as file:
                json.dump(values, file, indent=2)
                file.write("\n")
            os.replace(temporary_path, self.path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def _invalid_message(self) -> str:
        path = str(self.path).replace(str(Path.home()), "~", 1)
        return f"Invalid credential store: {path}. Fix or delete the file."


def load_saved_api_keys(store: APIKeyStore | None = None) -> None:
    """Load saved keys without overriding explicitly configured environment values."""
    credentials = store or APIKeyStore()
    for name, key in credentials.load().items():
        if not os.getenv(name, "").strip():
            os.environ[name] = key


def activate_api_key(name: str, key: str, *, persist: bool = False, store: APIKeyStore | None = None) -> None:
    """Select an API key for new model clients and optionally persist it."""
    key = key.strip()
    if not key:
        raise ValueError("API key cannot be empty")
    if persist:
        (store or APIKeyStore()).save(name, key)
    os.environ[name] = key
    invalidate_model_cache()
